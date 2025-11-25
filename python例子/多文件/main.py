from platform import node
import sys
import os
from datetime import datetime, timezone, timedelta
import turtle
import serial
import json
import time
import subprocess
import re
import requests
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QWidget
from PyQt5.QtGui import QPixmap, QFont, QPainter, QBrush, QConicalGradient, QPen, QColor
from PyQt5.QtCore import QThread, QObject, pyqtSignal, Qt, QTimer, QRectF
import PyQt5.uic as uic
from ybp import GaugeWidget
from Serial import SerialWorker
DISPLAY_MODE4K=False ##是否显示4K图片
##图片路径
IMG_PATH = r"PIC"
BACKGROUND_IMAGE = os.path.join(IMG_PATH, "background.jpg")
AUTO_ON_IMAGE = os.path.join(IMG_PATH, "auto_on.png")
AUTO_OFF_IMAGE = os.path.join(IMG_PATH, "auto_off.png")
HOOD_ON_IMAGE = os.path.join(IMG_PATH, "hood_on.png")
HOOD_OFF_IMAGE = os.path.join(IMG_PATH, "hood_off.png")
DOOR_ON_IMAGE = os.path.join(IMG_PATH, "door_on.png")
DOOR_OFF_IMAGE = os.path.join(IMG_PATH, "door_off.png")
LIGHT_ON_IMAGE = os.path.join(IMG_PATH, "light_on.png")
LIGHT_OFF_IMAGE = os.path.join(IMG_PATH, "light_off.png")
ON_IMAGE = os.path.join(IMG_PATH, "on.png")
OFF_IMAGE = os.path.join(IMG_PATH, "off.png")
PINOT_IMAGE = os.path.join(IMG_PATH, "pinot.png")
PLAY_IMAGE = os.path.join(IMG_PATH, "play.png")
STOP_IMAGE = os.path.join(IMG_PATH, "stop.png")
WINDOW_ON_IMAGE = os.path.join(IMG_PATH, "window_on.png")
WINDOW_OFF_IMAGE = os.path.join(IMG_PATH, "window_off.png")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.serialworker = None
        uic.loadUi("main.ui", self)
        self.set_background_image()
        self.init_gauges()##初始化仪表盘
        self.init_labels()##初始化标签
        self.Load_pics()##加载所有图片  
        self.serialworker = SerialWorker()#创建串口线程
        self.serialworker.VoiceCommand.connect(self.updata_VoiceCommand)#连接串口信号到更新标签槽函数
        self.serialworker.SensorData.connect(self.updata_SensorData)#连接串口信号到更新标签槽函数
        self.serialworker.start()#启动串口线程
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
            time.sleep(0.1)
    def Load_pics(self):
        """加载所有图片"""
        self.Load_pic(self.curtain_status, OFF_IMAGE)
        self.Load_pic(self.master_light_status, LIGHT_OFF_IMAGE)
        self.Load_pic(self.music_status, STOP_IMAGE)
        self.Load_pic(self.secondroom_light_status, LIGHT_OFF_IMAGE)
        self.Load_pic(self.kitchen_hood_status, HOOD_OFF_IMAGE)
        self.Load_pic(self.hood_status, OFF_IMAGE)
        self.Load_pic(self.kitchen_light_status, LIGHT_OFF_IMAGE)
        self.Load_pic(self.living_window_status, WINDOW_OFF_IMAGE)
        self.Load_pic(self.living_light_status, LIGHT_OFF_IMAGE)
        self.Load_pic(self.study_desk_status,  OFF_IMAGE)
        self.Load_pic(self.window_status,  OFF_IMAGE)
        self.Load_pic(self.study_light_status, LIGHT_OFF_IMAGE)
        self.Load_pic(self.bathroom_light_status, LIGHT_OFF_IMAGE)
        self.Load_pic(self.door_status, DOOR_OFF_IMAGE)
        self.Load_pic(self.auto_door_status, AUTO_OFF_IMAGE)
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
        """初始化所有仪表盘"""
        # 基础参数
        big_gauge_width = 7 # 大仪表盘宽度
        default_width =108 # 默认宽度
        default_height = 108 # 默认高度
        gauges_config = [
            # 温度仪表盘
            {
                'name': 'temp1_gauge',
                'min_val': 0.0,
                'max_val': 60.0,
                'colors': [QColor(255, 253, 209),  QColor(255,0,0),QColor(255,100,0)], ##'colors': [QColor(1, 253, 209), QColor(25,234,255), QColor(85,255,243)], 
                'width': default_width,
                'height': default_height,
                'x': 59,
                'y': 248,
                'gauge_width': big_gauge_width,
                'initial_value': 60
            },
            # 温度仪表盘
            {
                'name': 'hum1_gauge',
                'min_val': 0.0,
                'max_val': 100.0,
                'colors': [QColor(1, 253, 209),QColor(85,255,243), QColor(25,234,255)], 
                'width': default_width,
                'height': default_height,
                'x': 201,
                'y': 248,
                'gauge_width': big_gauge_width,
                'initial_value': 100
            },
            # 温度仪表盘
            {
                'name': 'temp2_gauge',
                'min_val': 0.0,
                'max_val': 60.0,
                'colors': [QColor(255, 253, 209),  QColor(255,0,0),QColor(255,100,0)], ##'colors': [QColor(1, 253, 209), QColor(25,234,255), QColor(85,255,243)], 
                'width': default_width,
                'height': default_height,
                'x': 364,
                'y': 248,
                'gauge_width': big_gauge_width,
                'initial_value': 60
            },
            # 温度仪表盘
            {
                'name': 'hum2_gauge',
                'min_val': 0.0,
                'max_val': 100.0,
                'colors': [QColor(1, 253, 209),QColor(85,255,243), QColor(25,234,255)], 
                'width': default_width,
                'height': default_height,
                'x': 364+142,
                'y': 248,
                'gauge_width': big_gauge_width,
                'initial_value': 100
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
        """更新语音指令"""
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
