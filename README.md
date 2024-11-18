# xiaokejinchanchan
金铲铲/云顶之弈自动抓牌
仅供学习交流，切勿进行实际游戏行为！


云顶的牌库是在1600*900下截的图


金铲铲的是MUMU模拟器，机型设置为iPad模式，1920*1080最大化窗口模式进行游戏截的图


在代码19行可以修改你要识别的卡牌文件夹


folder_path = os.path.join(current_dir, 'chanchankapai')  # 卡牌图片文件夹路径


切勿拿去倒卖盈利，产生的一切法律后果本人概不负责！


S13赛季请下载S13文件夹，采用OCR识别方案
用到的库
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
F1一键梭哈
HOME开始抓牌
END/暂停/恢复
F12完全停止
手动选择需要识别的窗口
