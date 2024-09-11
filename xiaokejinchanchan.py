import os
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import pyautogui
import threading
import time
import json
import win32api
import win32con
from pynput import keyboard
import ctypes, sys

# 获取当前脚本运行的目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# JSON 文件和卡牌图片文件夹路径
json_file_path = os.path.join(current_dir, 'file_name_to_display.json')  # JSON 文件路径
folder_path = os.path.join(current_dir, 'yundingkapai')  # 卡牌图片文件夹路径

# 检查是否以管理员模式运行
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# 如果不是管理员模式，重新启动并申请管理员权限
if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
    sys.exit()

# 全局变量
running = False  # 抓牌线程是否在运行
grabbing_thread = None  # 抓牌线程对象
speed = 0.01  # 抓取速度
match_confidence = 0.85  # 匹配度
selected_cards = []  # 用户选择的卡牌
paused = False  # 暂停状态
click_positions = []  # 用于检测重复点击的位置
last_check_time = time.time()  # 用于重复点击的时间控制
config_file_path = os.path.join(current_dir, "config.json")  # 配置文件路径
selected_cards_text = None  # 用于显示已选中卡牌的文本框

# 加载映射表
def load_file_name_to_display(json_file):
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        messagebox.showerror("加载错误", f"无法加载 JSON 文件：{e}")
        sys.exit()

# 加载卡牌配置
def load_cards_by_level(folder_path):
    cards_by_level = {1: [], 2: [], 3: [], 4: [], 5: []}
    if not os.path.exists(folder_path):
        messagebox.showerror("错误", f"文件夹 {folder_path} 不存在")
        return cards_by_level

    for filename in os.listdir(folder_path):
        if filename.endswith('.png') and filename[0].isdigit():
            try:
                level = int(filename[0])  # 获取文件名中的卡牌等级
                if level in cards_by_level:
                    cards_by_level[level].append(filename)
            except ValueError as e:
                print(f"跳过文件 {filename}，无法解析卡牌等级：{e}")
        else:
            print(f"跳过文件 {filename}，因为格式不正确")

    return cards_by_level

# 保存配置
def save_config():
    global selected_cards
    try:
        with open(config_file_path, 'w') as config_file:
            json.dump(selected_cards, config_file)
        print("卡牌选择已保存!")
    except Exception as e:
        messagebox.showerror("保存失败", f"保存配置时出现错误: {e}")

# 加载配置
def load_config():
    global selected_cards
    try:
        if os.path.exists(config_file_path):
            with open(config_file_path, 'r') as config_file:
                selected_cards = json.load(config_file)

            # 使用 JSON 映射将文件名转换为中文名
            file_name_to_display = load_file_name_to_display(json_file_path)
            translated_selected_cards = [
                file_name_to_display.get(os.path.basename(card_path), os.path.basename(card_path))
                for card_path in selected_cards
            ]

            print(f"加载卡牌选择成功: {translated_selected_cards}")
        else:
            print("没有找到配置文件，使用默认设置")
    except Exception as e:
        print(f"加载配置时出现错误: {e}")
        selected_cards = []

# 更新卡牌标签
def update_selected_cards_label(file_name_to_display):
    global selected_cards_text
    selected_cards_text.config(state=tk.NORMAL)  # 解锁编辑状态
    selected_cards_text.delete(1.0, tk.END)  # 清除之前的内容

    selected_cards_text.insert(tk.END, "当前抓取列表：\n", "normal")
    sorted_cards = sorted(selected_cards, key=lambda card: int(os.path.basename(card)[0]))

    for card_path in sorted_cards:
        card_name = file_name_to_display.get(os.path.basename(card_path), os.path.basename(card_path))
        level = int(os.path.basename(card_path)[0])

        if level == 1:
            selected_cards_text.insert(tk.END, f"[{card_name}] ", "gray")
        elif level == 2:
            selected_cards_text.insert(tk.END, f"[{card_name}] ", "green")
        elif level == 3:
            selected_cards_text.insert(tk.END, f"[{card_name}] ", "blue")
        elif level == 4:
            selected_cards_text.insert(tk.END, f"[{card_name}] ", "purple")
        elif level == 5:
            selected_cards_text.insert(tk.END, f"[{card_name}] ", "orange")

    selected_cards_text.config(state=tk.DISABLED)  # 禁止编辑和选中

# 使用 pyautogui 进行卡牌匹配
def match_card(card_path):
    try:
        location = pyautogui.locateOnScreen(card_path, confidence=match_confidence)
        return location
    except Exception:
        return None

# 使用 win32api 进行鼠标点击
def click_card(card_center):
    x, y = card_center
    try:
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, x, y, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, x, y, 0, 0)
        print(f"点击位置：{card_center}")
    except Exception as e:
        print(f"鼠标点击出错: {e}")

# 恢复脚本
def resume_script():
    global paused
    if paused:
        print("恢复抓牌")
        paused = False

# 停止脚本并提示用户如何恢复
def stop_script():
    global paused
    paused = True
    print("脚本已暂停，按 D 键或 Home 键继续抓牌。")

# 启动或恢复抓牌
def toggle_grabbing():
    global running, grabbing_thread
    if not running:
        print("启动抓牌")
        running = True
        grabbing_thread = threading.Thread(target=start_grabbing)
        grabbing_thread.start()
    elif paused:
        resume_script()

# 停止抓牌（F12）
def force_stop_grabbing():
    global running
    if running:
        print("F12 键按下，抓牌已强制停止")
        running = False

# 记录1秒内的点击位置，检查是否有重复点击
def check_repeated_clicks(click_positions):
    position_set = set()
    for pos in click_positions:
        if pos in position_set:
            return True  # 找到重复位置
        position_set.add(pos)
    return False

# 抓牌线程的主逻辑
def start_grabbing():
    global running, paused, speed, selected_cards, click_positions, last_check_time
    if not selected_cards:
        messagebox.showinfo("提示", "没有选中任何卡牌")
        running = False
        return

    last_output_time = time.time()

    while running:
        if not paused:
            card_matched = False
            for card_path in selected_cards:
                card_location = match_card(card_path)
                if card_location:
                    card_center = pyautogui.center(card_location)
                    click_card(card_center)
                    click_positions.append(card_center)
                    card_matched = True

                    if time.time() - last_check_time >= 2:
                        if check_repeated_clicks(click_positions):
                            print("检测到重复点击，脚本已暂停。按 D 键或 Home 键继续抓牌。")
                            stop_script()
                            click_positions = []
                            break
                        last_check_time = time.time()

                    time.sleep(speed)

            if time.time() - last_output_time >= 5:
                print("正在运行...")
                last_output_time = time.time()

        time.sleep(0.1)

# 处理图片点击事件，选中或取消选中复选框
def handle_image_click(checkbox, file_name_to_display):
    display_name = file_name_to_display.get(os.path.basename(checkbox.card_path), checkbox.card_path)

    if checkbox.var.get():
        checkbox.var.set(False)
        if checkbox.card_path in selected_cards:
            selected_cards.remove(checkbox.card_path)
            print(f"取消选中卡牌: {display_name}")

    else:
        checkbox.var.set(True)
        if checkbox.card_path not in selected_cards:
            selected_cards.append(checkbox.card_path)
            print(f"选中卡牌: {display_name}")

    update_selected_cards_label(file_name_to_display)

# 创建卡牌选择页面
def create_card_selection_page(notebook, file_name_to_display):
    cards_by_level = load_cards_by_level(folder_path)

    for level in range(1, 6):
        level_frame = ttk.Frame(notebook)
        notebook.add(level_frame, text=f"{level} 级卡牌")

        row, col = 0, 0
        for card in cards_by_level[level]:
            card_frame = tk.Frame(level_frame)
            card_frame.grid(row=row, column=col, padx=5, pady=5)

            img_path = os.path.join(folder_path, card)
            img = Image.open(img_path)
            img.thumbnail((80, 80))
            img_tk = ImageTk.PhotoImage(img)

            img_label = tk.Label(card_frame, image=img_tk)
            img_label.image = img_tk
            img_label.pack()

            display_name = file_name_to_display.get(card, card.split('.')[0][1:])
            var = tk.BooleanVar()
            checkbox = tk.Checkbutton(card_frame, text=display_name, variable=var, wraplength=80)
            checkbox.pack(anchor="w")
            checkbox.var = var
            checkbox.card_path = img_path

            if any(selected_card.endswith(os.path.basename(img_path)) for selected_card in selected_cards):
                checkbox.var.set(True)

            checkbox.config(command=lambda cb=checkbox: handle_image_click(cb, file_name_to_display))
            img_label.bind("<Button-1>", lambda e, cb=checkbox: handle_image_click(cb, file_name_to_display))

            col += 1
            if col >= 4:
                col = 0
                row += 1

# 创建抓牌速度与匹配度调节页面
def create_speed_and_confidence_control_page(notebook):
    frame = ttk.Frame(notebook)
    notebook.add(frame, text="抓牌速度与匹配度")

    tk.Label(frame, text="调整抓牌速度 (秒):").pack(pady=10)
    speed_scale = tk.Scale(frame, from_=0.01, to=1.0, orient=tk.HORIZONTAL, resolution=0.01)
    speed_scale.set(speed)
    speed_scale.pack()

    def update_speed(val):
        global speed
        speed = float(val)

    speed_scale.config(command=update_speed)

    tk.Label(frame, text="调整卡牌匹配度 (0.1 - 1.0):").pack(pady=10)
    confidence_scale = tk.Scale(frame, from_=0.1, to=1.0, orient=tk.HORIZONTAL, resolution=0.01)
    confidence_scale.set(match_confidence)
    confidence_scale.pack()

    def update_confidence(val):
        global match_confidence
        match_confidence = float(val)

    confidence_scale.config(command=update_confidence)

# 捕获窗口关闭事件
def on_closing():
    global running, grabbing_thread
    if messagebox.askokcancel("退出", "你确定要退出吗?"):
        running = False
        if grabbing_thread and grabbing_thread.is_alive():
            grabbing_thread.join()
        root.destroy()

# 全局键盘监听器
def on_press(key):
    try:
        if key.char == 'd':
            toggle_grabbing()
    except AttributeError:
        if key == keyboard.Key.home:
            toggle_grabbing()
        elif key == keyboard.Key.f12:
            force_stop_grabbing()

# 键盘监听线程
def start_keyboard_listener():
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

# 创建主界面
def create_gui():
    global root, selected_cards_text
    root = tk.Tk()
    root.title("小柯自动抓牌")

    root.protocol("WM_DELETE_WINDOW", on_closing)

    notebook = ttk.Notebook(root)
    notebook.pack(padx=10, pady=10, fill="both", expand=True)

    file_name_to_display = load_file_name_to_display(json_file_path)

    load_config()
    create_speed_and_confidence_control_page(notebook)
    create_card_selection_page(notebook, file_name_to_display)

    selected_cards_text = tk.Text(root, height=4, wrap=tk.WORD)
    selected_cards_text.pack(padx=10, pady=10, fill="x")
    selected_cards_text.tag_configure("gray", foreground="gray")
    selected_cards_text.tag_configure("green", foreground="green")
    selected_cards_text.tag_configure("blue", foreground="blue")
    selected_cards_text.tag_configure("purple", foreground="purple")
    selected_cards_text.tag_configure("orange", foreground="orange")
    selected_cards_text.config(state=tk.DISABLED)

    update_selected_cards_label(file_name_to_display)

    start_button = tk.Button(root, text="开始抓牌[HOME]", command=toggle_grabbing)
    start_button.pack(side=tk.LEFT, padx=20, pady=10)

    stop_button = tk.Button(root, text="停止抓牌[F12]", command=stop_script)
    stop_button.pack(side=tk.LEFT, padx=20, pady=10)

    save_button = tk.Button(root, text="保存配置", command=save_config)
    save_button.pack(side=tk.LEFT, padx=20, pady=10)

    start_keyboard_listener()
    root.mainloop()

if __name__ == "__main__":
    try:
        create_gui()
    except Exception as e:
        messagebox.showerror("错误", f"发生未处理的异常：{e}")
        print(f"发生未处理的异常：{e}")
