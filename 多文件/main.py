"""
智能家居控制界面主程序
基于PyQt5开发的图形界面，用于显示和控制智能家居设备状态
包含温度湿度仪表盘、设备状态显示、串口通信等功能
"""

import sys
import os
import json
import time
import subprocess
import re
import requests
from datetime import datetime, timezone, timedelta

# PyQt5 GUI框架相关导入
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QWidget
from PyQt5.QtGui import QPixmap, QFont, QPainter, QBrush, QConicalGradient, QPen, QColor
from PyQt5.QtCore import QThread, QObject, pyqtSignal, Qt, QTimer, QRectF
import PyQt5.uic as uic

# 自定义模块导入
from ybp import GaugeWidget  # 仪表盘组件
from Serial import SerialWorker  # 串口通信工作线程

# 显示模式配置
DISPLAY_MODE4K = False  # 是否显示4K图片模式：True为3840x2160，False为1280x800

# 图片路径配置常量
IMG_PATH = r"PIC"  # 图片资源文件夹路径

# 图片文件路径常量定义
BACKGROUND_IMAGE = os.path.join(IMG_PATH, "background.jpg")  # 背景图片
AUTO_ON_IMAGE = os.path.join(IMG_PATH, "auto_on.png")       # 自动模式开启图标
AUTO_OFF_IMAGE = os.path.join(IMG_PATH, "auto_off.png")     # 自动模式关闭图标
HOOD_ON_IMAGE = os.path.join(IMG_PATH, "hood_on.png")       # 抽油烟机开启图标
HOOD_OFF_IMAGE = os.path.join(IMG_PATH, "hood_off.png")     # 抽油烟机关闭图标
DOOR_ON_IMAGE = os.path.join(IMG_PATH, "door_on.png")       # 门开启图标
DOOR_OFF_IMAGE = os.path.join(IMG_PATH, "door_off.png")     # 门关闭图标
LIGHT_ON_IMAGE = os.path.join(IMG_PATH, "light_on.png")     # 灯开启图标
LIGHT_OFF_IMAGE = os.path.join(IMG_PATH, "light_off.png")   # 灯关闭图标
ON_IMAGE = os.path.join(IMG_PATH, "on.png")                 # 通用开启图标
OFF_IMAGE = os.path.join(IMG_PATH, "off.png")               # 通用关闭图标
PINOT_IMAGE = os.path.join(IMG_PATH, "pinot.png")           # 指针图标
PLAY_IMAGE = os.path.join(IMG_PATH, "play.png")             # 播放图标
STOP_IMAGE = os.path.join(IMG_PATH, "stop.png")             # 停止图标
WINDOW_ON_IMAGE = os.path.join(IMG_PATH, "window_on.png")   # 窗户开启图标
WINDOW_OFF_IMAGE = os.path.join(IMG_PATH, "window_off.png") # 窗户关闭图标

class MainWindow(QMainWindow):
    """
    智能家居控制主窗口类
    继承自QMainWindow，负责管理整个应用程序的界面和功能
    """
    
    def __init__(self):
        """
        主窗口初始化函数
        负责加载UI文件、初始化组件、启动串口通信线程
        """
        super().__init__()
        self.serialworker = None  # 串口工作线程实例，初始为None
        
        # 加载UI文件，从UI文件夹加载main.ui界面设计文件
        uic.loadUi("UI\main.ui", self)
        
        # 初始化各个组件
        self.set_background_image()    # 设置背景图片
        self.init_gauges()             # 初始化温度湿度仪表盘
        self.init_labels()             # 初始化数据显示标签
        self.Load_pics()               # 加载所有设备状态图标
        
        # 创建并启动串口通信线程
        self.serialworker = SerialWorker()  # 创建串口工作线程实例
        # 连接串口信号到对应的槽函数
        self.serialworker.VoiceCommand.connect(self.updata_VoiceCommand)  # 语音指令信号
        self.serialworker.SensorData.connect(self.updata_SensorData)      # 传感器数据信号
        self.serialworker.start()  # 启动串口通信线程
    def init_label(self, label, initial_value, color="rgb(186,128,0)"):
        """初始化标签显示"""
        # 设置文字内容
        label.setText(str(initial_value))
        
        # 设置文字样式
        label.setFont(QFont("SimHei", 12, QFont.Bold))  # 字体、大小、加粗
        label.setStyleSheet(f"color: {color};")  # 文字颜色   
        
        # 设置文字对齐方式
        label.setAlignment(Qt.AlignCenter)        
        # 确保文字显示在背景上方
        label.raise_()
    def init_labels(self):
        """初始化所有标签"""
        self.init_label(self.temp1_label, "88℃")
        self.init_label(self.hum1_label, "88.8%") 
        self.init_label(self.temp2_label, "88℃")
        self.init_label(self.hum2_label, "88.8%") 
    def Load_pic(self,Label,pic_path):
        if Label is not None:
            self.pic_set = QPixmap(pic_path)
            self.pic_set = self.pic_set.scaled(
                Label.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )
            Label.setPixmap(self.pic_set)
    def Load_pics(self):
        """加载所有图片"""
        # 图片加载配置字典：{控件对象: 图片路径}
        pic_configs = {
            self.curtain_status: OFF_IMAGE,
            self.master_light_status: LIGHT_OFF_IMAGE,
            self.music_status: STOP_IMAGE,
            self.secondroom_light_status: LIGHT_OFF_IMAGE,
            self.kitchen_hood_status: HOOD_OFF_IMAGE,
            self.hood_status: OFF_IMAGE,
            self.kitchen_light_status: LIGHT_OFF_IMAGE,
            self.living_window_status: WINDOW_OFF_IMAGE,
            self.living_light_status: LIGHT_OFF_IMAGE,
            self.study_desk_status: OFF_IMAGE,
            self.window_status: OFF_IMAGE,
            self.study_light_status: LIGHT_OFF_IMAGE,
            self.bathroom_light_status: LIGHT_OFF_IMAGE,
            self.door_status: DOOR_OFF_IMAGE,
            self.auto_door_status: AUTO_OFF_IMAGE
        }
        
        # 使用循环批量加载图片
        for label, image_path in pic_configs.items():
            self.Load_pic(label, image_path)
    def keyPressEvent(self, event):
        """处理键盘事件"""
        if event.key() == Qt.Key_Escape:
            # ESC键：退出全屏显示（无论当前是否在全屏模式）
            if self.isFullScreen():
                self.showNormal()
                print("已退出全屏显示")
        elif event.key() == Qt.Key_Q:
            # Q键：退出程序
            print("用户按Q键退出程序")
            self.close()
        else:
            super().keyPressEvent(event)   
    def mouseDoubleClickEvent(self, event):
        """处理鼠标双击事件，切换全屏模式"""
        if self.isFullScreen():
            self.showNormal()            
        else:
            self.showFullScreen()      
    def set_background_image(self):
        # 保持原有的背景图片显示逻辑不变
        image_path = BACKGROUND_IMAGE           
        try:
            pixmap = QPixmap(image_path)
            self.background_label = QLabel(self)
            if DISPLAY_MODE4K:
                self.image_width = 3840  # 3840，1920
                self.image_height = 2160  # 2160，1080
            else:
                self.image_width = 1280  # 3840，1920
                self.image_height = 800  # 2160，1080
            self.resize(self.image_width, self.image_height)
            
            scaled_pixmap = pixmap.scaled(
                self.image_width, 
                self.image_height, 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            )            
            self.background_label.setGeometry(0, 0, self.image_width, self.image_height)
            self.background_label.setPixmap(scaled_pixmap)
            self.background_label.setAlignment(Qt.AlignCenter)
            self.background_label.lower()
        except Exception as e:
            print(f"设置背景图片出错: {e}")    
    def init_gauges(self):
        """
        初始化所有仪表盘组件
        创建4个仪表盘分别显示两个位置的温度和湿度数据
        """
        # 仪表盘基础参数配置
        big_gauge_width = 7    # 仪表盘指针宽度（像素）
        default_width = 108    # 仪表盘默认宽度（像素）
        default_height = 108   # 仪表盘默认高度（像素）
        
        # 仪表盘配置列表，每个字典代表一个仪表盘的配置参数
        gauges_config = [
            # 第一个温度仪表盘（位置1温度）
            {
                'name': 'temp1_gauge',      # 仪表盘属性名称，将作为self.temp1_gauge访问
                'min_val': 0.0,             # 仪表盘最小值（摄氏度）
                'max_val': 60.0,            # 仪表盘最大值（摄氏度）
                'colors': [QColor(255, 253, 209), QColor(255,0,0), QColor(255,100,0)],  # 渐变颜色：浅黄->红色->橙红
                'width': default_width,     # 仪表盘宽度
                'height': default_height,    # 仪表盘高度
                'x': 59,                    # 仪表盘在窗口中的X坐标（像素）
                'y': 248,                   # 仪表盘在窗口中的Y坐标（像素）
                'gauge_width': big_gauge_width,  # 仪表盘指针宽度
                'initial_value': 60         # 初始显示值（摄氏度）
            },
            # 第一个湿度仪表盘（位置1湿度）
            {
                'name': 'hum1_gauge',       # 仪表盘属性名称
                'min_val': 0.0,              # 最小值（百分比）
                'max_val': 100.0,           # 最大值（百分比）
                'colors': [QColor(1, 253, 209), QColor(85,255,243), QColor(25,234,255)],  # 渐变颜色：青绿->浅蓝->蓝色
                'width': default_width,     # 仪表盘宽度
                'height': default_height,    # 仪表盘高度
                'x': 201,                   # X坐标
                'y': 248,                   # Y坐标
                'gauge_width': big_gauge_width,  # 指针宽度
                'initial_value': 100        # 初始显示值（百分比）
            },
            # 第二个温度仪表盘（位置2温度）
            {
                'name': 'temp2_gauge',      # 仪表盘属性名称
                'min_val': 0.0,             # 最小值（摄氏度）
                'max_val': 60.0,            # 最大值（摄氏度）
                'colors': [QColor(255, 253, 209), QColor(255,0,0), QColor(255,100,0)],  # 渐变颜色
                'width': default_width,     # 仪表盘宽度
                'height': default_height,    # 仪表盘高度
                'x': 364,                   # X坐标
                'y': 248,                   # Y坐标
                'gauge_width': big_gauge_width,  # 指针宽度
                'initial_value': 60         # 初始显示值（摄氏度）
            },
            # 第二个湿度仪表盘（位置2湿度）
            {
                'name': 'hum2_gauge',       # 仪表盘属性名称
                'min_val': 0.0,              # 最小值（百分比）
                'max_val': 100.0,           # 最大值（百分比）
                'colors': [QColor(1, 253, 209), QColor(85,255,243), QColor(25,234,255)],  # 渐变颜色
                'width': default_width,     # 仪表盘宽度
                'height': default_height,    # 仪表盘高度
                'x': 364+142,               # X坐标（364 + 142像素偏移）
                'y': 248,                   # Y坐标
                'gauge_width': big_gauge_width,  # 指针宽度
                'initial_value': 100        # 初始显示值（百分比）
            }
        ]
        
        # 批量创建仪表盘
        for config in gauges_config:
            self.init_gauge(**config)
    def init_gauge(self, name, min_val, max_val, colors, width, height, x, y, gauge_width=20, 
                   start_angle=None, total_angle=None, initial_value=0):
        """初始化单个仪表盘
        
        Args:
            name: 仪表盘名称，将作为self的属性名
            min_val: 最小值
            max_val: 最大值
            colors: 颜色列表
            width: 宽度
            height: 高度
            x: x坐标
            y: y坐标
            gauge_width: 仪表盘宽度
            start_angle: 起始角度（可选）
            total_angle: 总角度（可选）
            initial_value: 初始值
        """
        # 创建仪表盘
        gauge = GaugeWidget(self, min_value=min_val, max_value=max_val, colors=colors, gauge_width=gauge_width)
        # 设置位置和大小
        gauge.setGeometry(x, y, width, height)
        
        # 如果提供了自定义角度，则设置
        if start_angle is not None:
            gauge.setStartAngle(start_angle)
        if total_angle is not None:
            gauge.setTotalAngle(total_angle)
        
        # 设置初始值
        gauge.setValue(initial_value)
        # 确保在顶层显示
        gauge.raise_()
        
        # 将仪表盘保存为实例属性
        setattr(self, name, gauge)
        return gauge    
    def updata_VoiceCommand(self,device_id, command):
        """
        更新语音指令显示区域
        
        在窗口左上角显示当前接收到的语音指令或传感器数据
        
        Args:
            device_id (str): 设备标识符
            command (str): 要显示的指令文本内容
        """
        print(f"[主程序收到的数据] 有效语音指令帧: 设备ID={device_id}, 指令={command}")    
    def updata_SensorData(self,data):
        """更新传感器数据"""
        print(f"[主程序收到的数据] 有效传感器数据帧: {data}")       
        # 解析传感器数据
        try:
            sensor_data = json.loads(data)
            # 更新温度仪表盘
            if 'temp1' in sensor_data:
                self.temp1_gauge.setValue(float(sensor_data['temp1']))
            if 'hum1' in sensor_data:
                self.hum1_gauge.setValue(float(sensor_data['hum1']))
            if 'temp2' in sensor_data:
                self.temp2_gauge.setValue(float(sensor_data['temp2']))
            if 'hum2' in sensor_data:
                self.hum2_gauge.setValue(float(sensor_data['hum2']))
        except json.JSONDecodeError:
            print("传感器数据解析错误")
if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
