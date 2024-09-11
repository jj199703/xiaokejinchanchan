import cv2
import numpy as np
import keyboard
import os
import ctypes
from PIL import ImageGrab, Image
import time
import sys

# 初始化全局变量
dragging = False
resizing = False
region = [300, 300, 200, 100]  # 初始截图区域 (x, y, width, height)
start_point = None
selected_corner = None
done = False
saved_region = None  # 用于保存按 Enter 键后选择的截图区域
scale_percent = 80  # 缩放比例 80%

# 检查管理员权限
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# 截取屏幕截图
def capture_full_screenshot():
    screenshot = ImageGrab.grab()  # 获取整个屏幕的截图
    screenshot_np = np.array(screenshot)
    return cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2BGR)

# 缩放图像
def resize_image(image, scale_percent):
    width = int(image.shape[1] * scale_percent / 100)
    height = int(image.shape[0] * scale_percent / 100)
    dim = (width, height)
    return cv2.resize(image, dim, interpolation=cv2.INTER_AREA)

# 恢复缩放后的坐标到原始分辨率
def restore_to_original_scale(region, scale_percent):
    x, y, width, height = region
    scale_factor = 100 / scale_percent
    x_real = int(x * scale_factor)
    y_real = int(y * scale_factor)
    width_real = int(width * scale_factor)
    height_real = int(height * scale_factor)
    return (x_real, y_real, width_real, height_real)

# 截取指定区域的截图
def capture_screenshot(region):
    left, top, width, height = region
    right = left + width
    bottom = top + height
    screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))  # 截取指定区域
    return screenshot

# 分割截图并保存图片
def split_and_save_image(screenshot, save_folder):
    img_width, img_height = screenshot.size
    part_width = img_width // 5  # 将整个图片宽度平均分成5部分
    part_height = img_height  # 保持整个图片的高度

    # 确保保存目录存在
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    # 获取当前时间戳，用作文件名的一部分，确保唯一性
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # 保存生成的5张图片的路径
    saved_images = []

    # 逐个分割并保存
    for i in range(5):
        left = i * part_width
        right = left + part_width
        top = 0
        bottom = part_height

        # 确保不超过原图宽度
        if right > img_width:
            right = img_width

        # 裁剪图片
        cropped_image = screenshot.crop((left, top, right, bottom))

        # 保存图片，使用时间戳和序号作为文件名
        save_path = os.path.join(save_folder, f'part_{timestamp}_{i + 1}.png')
        cropped_image.save(save_path)
        saved_images.append(save_path)  # 添加到已保存的图片列表
        print(f"保存分割图片: {save_path}")

    # 调用缩进处理
    process_images(saved_images)

# 对刚分割的图片进行缩进处理
def process_images(image_paths):
    for file_path in image_paths:
        try:
            # 打开图片
            img = Image.open(file_path)

            # 获取当前图片尺寸
            width, height = img.size

            # 计算新的裁剪区域，缩进10像素
            left = 10
            top = 10
            right = width - 10
            bottom = height - 10

            # 裁剪图片
            cropped_img = img.crop((left, top, right, bottom))

            # 保存图片，覆盖原文件
            cropped_img.save(file_path)
            print(f"处理并保存图片: {file_path}")

        except Exception as e:
            print(f"处理文件 {file_path} 时发生错误: {e}")

# 鼠标回调函数
def mouse_callback(event, x, y, flags, param):
    global region, dragging, resizing, start_point, selected_corner, done

    if done:
        return

    if event == cv2.EVENT_LBUTTONDOWN:
        if region[0] <= x <= region[0] + region[2] and region[1] <= y <= region[1] + region[3]:
            # 开始拖动
            dragging = True
            start_point = (x, y)
        elif abs(x - (region[0] + region[2])) <= 10 and abs(y - (region[1] + region[3])) <= 10:
            # 开始调整大小（右下角）
            resizing = True
            start_point = (x, y)

    elif event == cv2.EVENT_MOUSEMOVE:
        if dragging:
            dx = x - start_point[0]
            dy = y - start_point[1]
            region[0] += dx
            region[1] += dy
            start_point = (x, y)
        elif resizing:
            region[2] = x - region[0]
            region[3] = y - region[1]

    elif event == cv2.EVENT_LBUTTONUP:
        dragging = False
        resizing = False

# 调整和保存截图区域
def adjust_and_capture_region():
    global done, saved_region, scale_percent

    screenshot = capture_full_screenshot()  # 获取一次全屏截图
    resized_screenshot = resize_image(screenshot, scale_percent)  # 缩放截图
    cv2.namedWindow('Adjust Region')
    cv2.setMouseCallback('Adjust Region', mouse_callback)

    while True:
        resized_screenshot_copy = resized_screenshot.copy()  # 在缩放后的截图副本上绘制绿色框
        # 绘制绿色框
        cv2.rectangle(resized_screenshot_copy, (region[0], region[1]), (region[0] + region[2], region[1] + region[3]), (0, 255, 0), 2)
        cv2.imshow('Adjust Region', resized_screenshot_copy)

        key = cv2.waitKey(1) & 0xFF

        if key == 13:  # 按下回车键确认区域并退出
            done = True
            saved_region = restore_to_original_scale(region, scale_percent)  # 将当前选中的区域转换回原始分辨率
            cv2.destroyAllWindows()
            print(f"截图区域已保存: x={saved_region[0]}, y={saved_region[1]}, 宽度={saved_region[2]}, 高度={saved_region[3]}")
            return

        elif key == 27:  # 按下 'Esc' 键退出程序
            cv2.destroyAllWindows()
            break

# 进行截图和分割操作
def capture_and_split():
    global saved_region
    if saved_region is None:
        print("请先按 Enter 键保存截图区域！")
        return

    screenshot = capture_screenshot(saved_region)

    # 分割并保存图片到888文件夹
    save_folder = os.path.join(os.getcwd(), '888')  # 保存到程序运行目录下的888文件夹
    split_and_save_image(screenshot, save_folder)

# 主函数
def main():
    global region
    print("按 'Enter' 键保存截图位置，按 'D' 或 'C' 键进行截图和分割操作，按 'Esc' 键退出程序")

    # 调整并保存截图区域
    adjust_and_capture_region()

    # 全局监听 'D' 键进行截图和分割
    keyboard.add_hotkey('D', capture_and_split)

    # 全局监听 'C' 键进行截图和分割
    keyboard.add_hotkey('C', capture_and_split)

    # 等待 'Esc' 键退出
    keyboard.wait('Esc')
    print("程序结束")

# 检查是否具有管理员权限
if __name__ == "__main__":
    if is_admin():
        main()
    else:
        # 如果没有管理员权限，则以管理员模式重新运行脚本
        print("正在尝试以管理员权限重新运行脚本...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
