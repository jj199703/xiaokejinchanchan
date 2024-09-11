import os
from PIL import Image, ImageTk
import imagehash
from tkinter import filedialog, messagebox, Tk, Canvas, Scrollbar, Frame, Button
import tkinter as tk
from datetime import datetime

# 计算图像的感知哈希值（pHash）
def calculate_phash(image_path):
    image = Image.open(image_path)
    phash = imagehash.phash(image)
    return phash

# 比较两个哈希值，返回汉明距离
def hamming_distance(hash1, hash2):
    return hash1 - hash2

# 获取文件的修改时间，返回时间戳
def get_file_modification_time(file_path):
    return os.path.getmtime(file_path)

# 扫描文件夹并检测相似图片，确保处理所有相似图片链
def process_folder(folder_path, similarity_threshold=10):
    images = []
    hashes = []

    # 获取文件夹内的所有图片文件
    for filename in os.listdir(folder_path):
        if filename.endswith(('.png', '.jpg', '.jpeg')):
            image_path = os.path.join(folder_path, filename)
            phash = calculate_phash(image_path)
            images.append(image_path)
            hashes.append(phash)

    # 存储相似图片组（每组包含相似的图片链）
    similar_image_groups = []

    # 标记已处理的图片
    processed_images = set()

    # 比较所有图片之间的相似度
    for i in range(len(hashes)):
        if images[i] in processed_images:
            continue
        current_group = [images[i]]
        processed_images.add(images[i])

        for j in range(i + 1, len(hashes)):
            distance = hamming_distance(hashes[i], hashes[j])
            if distance < similarity_threshold:
                current_group.append(images[j])
                processed_images.add(images[j])

        if len(current_group) > 1:
            similar_image_groups.append(current_group)

    return similar_image_groups

# 在GUI中展示相似图片的缩略图
def display_similar_images(similar_image_groups, root):
    # 创建一个可滚动的框架
    canvas = Canvas(root)
    scrollbar = Scrollbar(root, orient="vertical", command=canvas.yview)
    scrollable_frame = Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    row = 0
    delete_candidates = []  # 用于存储要删除的图片

    # 展示每组相似图片
    for group in similar_image_groups:
        group = sorted(group, key=get_file_modification_time, reverse=True)  # 按修改时间排序，最新的在前
        latest_image = group[0]  # 保留最新的图片
        for image_path in group[1:]:
            # 打开图片并创建缩略图
            image1 = Image.open(latest_image).resize((75, 75))  # 缩小缩略图大小以便显示更多
            image2 = Image.open(image_path).resize((75, 75))

            img1_thumbnail = ImageTk.PhotoImage(image1)
            img2_thumbnail = ImageTk.PhotoImage(image2)

            # 在界面中展示图片和相似度
            label1 = tk.Label(scrollable_frame, image=img1_thumbnail)
            label1.image = img1_thumbnail  # 这一步很重要，避免图片被垃圾回收
            label1.grid(row=row, column=0, padx=10, pady=5)

            label2 = tk.Label(scrollable_frame, image=img2_thumbnail)
            label2.image = img2_thumbnail  # 同样避免垃圾回收
            label2.grid(row=row, column=1, padx=10, pady=5)

            mod_time1 = datetime.fromtimestamp(get_file_modification_time(latest_image)).strftime('%Y-%m-%d %H:%M:%S')
            mod_time2 = datetime.fromtimestamp(get_file_modification_time(image_path)).strftime('%Y-%m-%d %H:%M:%S')

            label_text = tk.Label(scrollable_frame, text=f"保留: {latest_image} ({mod_time1})\n删除: {image_path} ({mod_time2})")
            label_text.grid(row=row, column=2, padx=10, pady=5)

            # 将需要删除的图片加入待删除列表
            delete_candidates.append(image_path)
            row += 1

    # 布局滚动区域
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # 创建删除按钮
    delete_button = Button(root, text="一键删除", command=lambda: confirm_and_delete(delete_candidates))
    delete_button.pack(pady=20)

# 确认并删除图片
def confirm_and_delete(delete_candidates):
    if messagebox.askyesno("确认删除", f"确定要删除 {len(delete_candidates)} 张图片吗？"):
        for image in delete_candidates:
            try:
                os.remove(image)
                print(f"已删除图片: {image}")
            except Exception as e:
                print(f"删除失败: {image}, 错误: {e}")
        messagebox.showinfo("完成", f"已删除 {len(delete_candidates)} 张图片。")
    else:
        print("删除操作已取消。")

# GUI 选择文件夹并处理
def select_folder_and_process(root):
    folder_path = filedialog.askdirectory(title="选择图片文件夹")
    if folder_path:
        similar_image_groups = process_folder(folder_path)
        if similar_image_groups:
            display_similar_images(similar_image_groups, root)
        else:
            messagebox.showinfo("完成", "没有找到相似的图片。")

# 创建 GUI
def create_gui():
    root = Tk()
    root.title("图片相似度检测")
    root.geometry("800x600")  # 设置窗口大小

    select_button = tk.Button(root, text="选择图片文件夹并检测相似图片", command=lambda: select_folder_and_process(root))
    select_button.pack(pady=20)

    root.mainloop()

if __name__ == "__main__":
    create_gui()
