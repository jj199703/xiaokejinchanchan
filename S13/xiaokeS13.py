import os
import json
import numpy as np
import tkinter as tk
from tkinter import ttk
from paddleocr import PaddleOCR
import threading
import win32gui
import time
from PIL import Image, ImageTk
from pyautogui import screenshot, moveTo, mouseDown, mouseUp
import keyboard

# 获取当前脚本目录
def get_current_directory():
    return os.path.dirname(os.path.abspath(__file__))

# 保存当前选择的英雄到配置文件
def save_selected_heroes(selected_heroes):
    config_path = os.path.join(get_current_directory(), 'selected_heroes.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(selected_heroes, f)

# 加载配置文件中的英雄
def load_selected_heroes():
    config_path = os.path.join(get_current_directory(), 'selected_heroes.json')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# 初始化 PaddleOCR
ocr = PaddleOCR(use_angle_cls=False, lang="ch", use_gpu=False, show_log=False)

# 定义全局变量
stop_detection = False
paused = False
window_choice = None
checkbox_vars = {}
selected_heroes = []
images = {}
detection_thread = None
hwnd = None
current_heroes_label = None

# 点击次数记录
click_count = {}
shuffling_thread = None

# 获取 JSON 数据
def load_json_data():
    config_path = os.path.join(get_current_directory(), 'hero.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# 获取所有窗口
def list_windows():
    def enum_windows(hwnd, results):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
            results.append((win32gui.GetWindowText(hwnd), hwnd))

    window_list = []
    win32gui.EnumWindows(enum_windows, window_list)
    return window_list

# 获取窗口位置
def get_window_rect(hwnd):
    if hwnd:
        return win32gui.GetWindowRect(hwnd)
    return None

# 持续检测并抓取英雄函数
def ocr_hero_buy():
    global stop_detection, paused, selected_heroes

    while not stop_detection:
        if paused:
            time.sleep(0.1)  # 暂停状态下稍微休眠
            continue

        rect = get_window_rect(hwnd)
        if not rect:
            print("未找到指定的游戏窗口")
            break

        StartLeft, StartTop, right, bottom = rect
        width = right - StartLeft
        height = bottom - StartTop

        # 截图并裁剪区域
        image = screenshot(region=(StartLeft, StartTop, width, height))
        left_crop = image.width * 0.2
        right_crop = image.width * 0.1
        bottom_crop = image.height * 0.95
        cropped_image = image.crop((int(left_crop), int(bottom_crop), image.width - int(right_crop), image.height))

        # OCR 识别
        image_np = np.array(cropped_image)
        result = ocr.ocr(image_np, cls=False)

        recognized_texts = []
        for line in result:
            if line:
                for word in line:
                    recognized_text = word[1][0]
                    # 只保留中文字符
                    recognized_text = ''.join(filter(lambda ch: u'\u4e00' <= ch <= u'\u9fff', recognized_text))
                    if recognized_text:
                        recognized_texts.append(recognized_text)
                        # 检测目标英雄，进行点击操作
                        if recognized_text in selected_heroes:
                            x, y = word[0][0][0] + StartLeft + int(left_crop), word[0][0][1] + StartTop + int(bottom_crop)
                            print(f"检测到目标英雄: '{recognized_text}', 准备抓牌...")
                            print(f"点击坐标: ({x}, {y})")

                            # 使用 pyautogui 进行点击操作
                            moveTo(x, y)  # 移动到目标位置
                            time.sleep(0.01)  # 等待0.01秒
                            mouseDown()  # 按下鼠标左键
                            time.sleep(0.01)  # 按下后等待0.05秒
                            mouseUp()  # 释放鼠标左键

                            # 记录点击次数
                            position_key = (x, y)  # 创建一个坐标元组作为字典的key
                            if position_key not in click_count:
                                click_count[position_key] = 0
                            click_count[position_key] += 1

                            # 检查点击次数是否超过3次
                            if click_count[position_key] > 2:
                                print(f"位置 {position_key} 点击超过3次，自动暂停脚本。")
                                toggle_pause()  # 调用暂停函数
                                # 在暂停后重置点击计数
                                click_count[position_key] = 0  # 重置点击次数

        # 只有在未暂停状态下输出当前未检测到英雄的信息
        if recognized_texts:
            print(f"识别到: {' '.join(recognized_texts)}")
        elif not paused:  # 只有在未暂停时才输出未检测到英雄的信息
            print("当前未检测到英雄")

        time.sleep(0.33)

# 更新当前抓取的英雄列表
def update_current_heroes():
    current_heroes = [hero for hero, var in checkbox_vars.items() if var.get()]
    if current_heroes_label:  # 确保 current_heroes_label 被定义
        current_heroes_label.config(text="当前抓取的英雄: " + ', '.join(current_heroes))

# 更新窗口选择下拉框
def update_window_choice():
    global hwnd
    windows = list_windows()
    window_names = [name for name, _ in windows]
    window_choice['values'] = window_names
    if hwnd is not None:
        current_window_name = win32gui.GetWindowText(hwnd)
        if current_window_name in window_names:
            window_choice.set(current_window_name)  # 选中当前窗口
        else:
            window_choice.set("")  # 清空选择

# 选择窗口时更新窗口信息
def on_window_selected(event):
    global hwnd
    selected_window_name = window_choice.get()
    if selected_window_name:
        hwnd = next((hwnd for name, hwnd in list_windows() if name == selected_window_name), None)

# 持续检测的启动函数
def start_detection():
    global stop_detection, paused, detection_thread
    if hwnd is None:
        print("未选择窗口，无法开始检测。")
        return
    stop_detection = False
    paused = False
    detection_thread = threading.Thread(target=ocr_hero_buy)
    detection_thread.start()
    print("开始持续检测屏幕中的目标")

# 停止检测
def stop_detection_func():
    global stop_detection, detection_thread
    stop_detection = True
    if detection_thread is not None:
        detection_thread.join()
    print("检测已停止")

# 暂停和恢复检测
def toggle_pause():
    global paused
    paused = not paused
    if paused:
        print("检测已暂停。按 HOME 键继续检测，或者再次按 END 键解除暂停。")
    else:
        print("恢复检测...")

# 取消所有勾选的英雄
def uncheck_all():
    for var in checkbox_vars.values():
        var.set(False)
    update_current_heroes()

# F1 键梭哈功能
def shuffling():
    global stop_detection, paused, shuffling_thread
    stop_detection = False
    paused = False
    print("开始梭哈...")

    while not stop_detection:
        if paused:
            time.sleep(0.1)
            continue

        rect = get_window_rect(hwnd)
        if not rect:
            print("未找到指定的游戏窗口")
            break

        StartLeft, StartTop, right, bottom = rect
        width = right - StartLeft
        height = bottom - StartTop

        # 截图并裁剪区域
        image = screenshot(region=(StartLeft, StartTop, width, height))
        left_crop = image.width * 0.2
        right_crop = image.width * 0.1
        bottom_crop = image.height * 0.95
        cropped_image = image.crop((int(left_crop), int(bottom_crop), image.width - int(right_crop), image.height))

        # OCR 识别
        image_np = np.array(cropped_image)
        result = ocr.ocr(image_np, cls=False)

        found_hero = False
        for line in result:
            if line:
                for word in line:
                    recognized_text = word[1][0]
                    # 只保留中文字符
                    recognized_text = ''.join(filter(lambda ch: u'\u4e00' <= ch <= u'\u9fff', recognized_text))
                    if recognized_text in selected_heroes:
                        found_hero = True
                        x, y = word[0][0][0] + StartLeft + int(left_crop), word[0][0][1] + StartTop + int(bottom_crop)
                        print(f"检测到目标英雄: '{recognized_text}', 准备抓牌...")
                        print(f"点击坐标: ({x}, {y})")

                        # 使用 pyautogui 进行点击操作
                        moveTo(x, y)  # 移动到目标位置
                        time.sleep(0.01)  # 等待0.01秒
                        mouseDown()  # 按下鼠标左键
                        time.sleep(0.05)  # 按下后等待0.05秒
                        mouseUp()  # 释放鼠标左键
                        break  # 找到目标英雄后跳出循环

        if not found_hero:
            print("未检测到目标英雄，按下 D 键刷新卡牌...")

        time.sleep(0.2)  # 每 0.2 秒进行一次识别

# 停止梭哈功能
def stop_shuffling():
    global stop_detection
    stop_detection = True
    print("停止梭哈模式")

# 绑定键盘热键
keyboard.add_hotkey('home', start_detection)  # 开始持续检测
keyboard.add_hotkey('end', toggle_pause)  # 按下 End 键暂停/恢复
keyboard.add_hotkey('f1', lambda: threading.Thread(target=shuffling).start())  # F1 键触发梭哈功能
keyboard.add_hotkey('ctrl+u', uncheck_all)  # Ctrl+U 取消所有勾选
keyboard.add_hotkey('f12', stop_detection_func)  # 停止检测并关闭程序

# 创建 UI 界面
def create_ui():
    global root, window_choice, checkbox_vars, selected_heroes, hwnd, current_heroes_label
    root = tk.Tk()
    root.title("请选择游戏窗口")

    # 加载 JSON 数据和图片路径
    data = load_json_data()
    hero_image_path = os.path.join(get_current_directory(), 'hero')

    # 创建 Notebook（分页容器）
    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True)

    for cost, heroes in data.items():
        frame = tk.Frame(notebook)
        notebook.add(frame, text=f"{cost}英雄")

        row_count = 0
        column_count = 0
        for hero in heroes:
            hero_frame = tk.Frame(frame)

            # 加载英雄图片
            image_path = os.path.join(hero_image_path, f"{hero}.jpg")
            if os.path.exists(image_path):
                image = Image.open(image_path).resize((50, 50), Image.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                images[hero] = photo  # 保存引用
            else:
                photo = None

            # 创建复选框
            var = tk.BooleanVar()
            checkbox = tk.Checkbutton(hero_frame, text=hero, variable=var, font=("Segoe UI", 12))
            checkbox.pack()

            # 图片标签和点击事件
            if photo:
                label = tk.Label(hero_frame, image=photo)
                label.image = photo  # 保存引用
                label.pack()
                label.bind("<Button-1>", lambda e, v=var: v.set(1 - v.get()))

            hero_frame.grid(row=row_count, column=column_count, padx=5, pady=5)
            checkbox_vars[hero] = var

            # 绑定复选框变化事件
            var.trace_add("write", lambda *args, hero=hero: update_current_heroes())

            column_count += 1
            if column_count >= 4:
                column_count = 0
                row_count += 1

    # 添加提示标签
    label = tk.Label(root, text="请选择游戏窗口:", font=("Segoe UI", 12))
    label.pack(pady=5)

    # 选择窗口
    window_choice = ttk.Combobox(root, state='readonly')
    window_choice.pack(pady=10)
    window_choice.bind("<<ComboboxSelected>>", on_window_selected)

    # 功能按键介绍
    key_info_label = tk.Label(root, text="功能按键: [HOME] 开始抓牌 | [END] 暂停/恢复 | [F1] 梭哈 | [CTRL+U] 全部取消 | [F12] 退出", font=("Segoe UI", 10), wraplength=600)
    key_info_label.pack(pady=5)

    # 加载窗口列表
    update_window_choice()

    # 加载上次保存的英雄配置
    selected_heroes = load_selected_heroes()
    for hero, var in checkbox_vars.items():
        if hero in selected_heroes:
            var.set(True)

    # 现在定义 current_heroes_label
    global current_heroes_label
    current_heroes_label = tk.Label(root, text="当前抓取的英雄: " + ', '.join(selected_heroes), font=("Segoe UI", 12), wraplength=400)
    current_heroes_label.pack(pady=10)

    # 开始按钮
    def start_button_click():
        global hwnd
        hwnd = next((hwnd for name, hwnd in list_windows() if name == window_choice.get()), None)
        selected_heroes.clear()
        selected_heroes.extend([hero for hero, var in checkbox_vars.items() if var.get()])
        save_selected_heroes(selected_heroes)
        update_current_heroes()
        if selected_heroes:
            start_detection()
        else:
            print("请至少选择一个英雄！")

    button = tk.Button(root, text="开始抓牌[HOME]", command=start_button_click)
    button.pack()

    # 窗口关闭事件处理
    def on_closing():
        stop_detection_func()
        root.destroy()
        print("程序已完全关闭")
        os._exit(0)

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    create_ui()
