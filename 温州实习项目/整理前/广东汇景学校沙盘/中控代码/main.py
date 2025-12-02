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

# ### 语音输入串口参数
# VOICE_PORT = '/dev/ttyAMA4'    # 连接语音模块的串口
# VOICE_BAUD_RATE = 9600  # 语音模块的波特率
# VOICE_TIMEOUT  = 1 
# LORA_PORT = '/dev/ttyAMA0'      # 连接LoRa模块的串口
# LORA_BAUD_RATE = 115200  # LoRa模块的波特率
# LORA_TIMEOUT  = 1 
# DISPLAY_MODE4K=False ##是否显示4K图片
# ##图片路径
# IMG_PATH = r"/home/pi/Desktop/shaipan/PIC"
# BACKGROUND_IMAGE = os.path.join(IMG_PATH, "background.jpg")






## 语音输入串口参数
VOICE_PORT = 'com23'    # 连接语音模块的串口
VOICE_BAUD_RATE = 9600  # 语音模块的波特率
VOICE_TIMEOUT  = 1 
LORA_PORT = 'com16'      # 连接LoRa模块的串口
LORA_BAUD_RATE = 115200  # LoRa模块的波特率
LORA_TIMEOUT  = 1 
DISPLAY_MODE4K=False ##是否显示4K图片
##图片路径
IMG_PATH = r"校园沙盘整理版\中控代码\PIC"
BACKGROUND_IMAGE = os.path.join(IMG_PATH, "background.jpg")
    # UI文件路径，方便修改
UI_FILE_PATH = r"校园沙盘整理版\中控代码\main.ui"
# --- 全局串口对象 ---
# 在程序启动时初始化，供全局调用
voice_ser = None  # 语音输入串口实例
lora_ser = None     # LoRa串口实例
send_lora_Times=3 # 发送LoRa指令的次数，默认3次
is_sending = False  # 全局变量，用于标识当前是否正在发送数据

# 问询设备ID数组（可自定义）
# 用户可以在这里自定义需要问询的设备ID，不需要按序排列
inquiry_device_ids = [1, 3, 5, 7, 9]  # 示例：只问询ID为1,3,5,7,9的设备
asktime=1000  # get设备数据的时间间隔，默认3秒
devices_asktime=asktime*(len(inquiry_device_ids)+1)  # 每轮设备询问的时间间隔，默认4秒
weather_asktime=10000  # 天气询问的时间间隔，默认30秒
ON=0x01  ##打开灯光，小车
OFF=0x02 ##关闭灯光，小车

MUSIC_STAGE=0x01             ##音乐播放器
COLORFUL_LIGHT=0x02        ##神经网络灯带
ENVIRONMENT_MP3=0x03           ##环境传感器
ROAD_LIGHT=0x04      ##路灯
WEAYHER_TIME=0x05 ##天气时间
RADIO_STAGE=0x06             ##收音机
DOOR=0x07             ##门
ALL_LIGHT=0x08       ## 所有灯光
FLOOR_LIGHT=0x09      ##楼层灯
CAR=0x10             ##小车

chewei_status = ["车位","有车","空位"]
weizhi_status = ["未知","校园大门","养正楼","植物园","车库" ,"停车场","垃圾分类","气象站","操场","育贤楼"]
months = {'Jan': '1', 'Feb': '2', 'Mar': '3', 'Apr': '4', 'May': '5', 'Jun': '6', 'Jul': '7', 'Aug': '8', 'Sep': '9', 'Oct': '10', 'Nov': '11', 'Dec': '12'}
weathers = ["晴","阴","多云","阵雨","小雨","中雨","大雨","暴雨","小雪","中雪","大雪","暴雪","雨夹雪","雾","雷阵雨","冻雨"]
CHEWEI_FLAG=0x01    #   车位状态
PLYER_COUNT_FLAG=0x02  ## 操场人数
CAR_FLAG=0x03        ## 小车状态
# ================== LoRa指令发送 ==================

def send_lora_command(data1, data2,times=3,delaytime=0.5):
    """
    构建并发送LoRa指令。
    指令格式: [帧头, 设备ID, 节点ID, 动作, 校验和]
    """
    global lora_ser, is_sending
    
    # 检查当前是否正在发送数据，如果是则等待
    while is_sending:
        print("[信息] 当前有数据正在发送，等待发送完成...")
        time.sleep(0.1)
    
    # 设置发送状态为正在发送
    is_sending = True
    
    try:
        # 检查LoRa串口是否已初始化并打开
        if not lora_ser or not lora_ser.is_open:
            print("[错误] LoRa串口未初始化或未打开")
            return
        
        # --- 构建指令字节串 ---
        header = bytes([0xFE, 0x06, 0x90, 0x90, 0x1F,0x00])  # 固定的帧头 0xFE, 0x06, 0x90, 0x90, 0x1F, 0x00
        # 计算校验和
        checksum = 0xFF
        # 将所有部分连接成一个bytes对象
        command = header + bytes([data1, data2, checksum])
        print(f"发送指令: {command}")
        # 为了提高无线通信的可靠性，同一指令连续发送3次
        for attempt in range(times):
            lora_ser.write(command)
            # 为了方便调试，将发送的字节指令以十六进制格式打印出来
            hex_string = ' '.join(f'{b:02x}' for b in command)
            print(f"-> LoRa发送 (第{attempt+1}次): {hex_string}")
            time.sleep(delaytime)  # 每次发送后短暂延时
        
        # 3次发送完成后，再延时一小段时间，确保LoRa模块有时间处理和切换收发状态
        time.sleep(0.2)
    except Exception as e:
        print(f"[严重错误] LoRa发送失败: {e}")
    finally:
        # 无论是否发生异常，都设置发送状态为未发送
        is_sending = False

def send_inquiry_frame(device_id=0x01):
    """
    发送问询帧到LoRa模块
    
    Args:
        device_id (int): 目标设备ID，默认为0x01
    """
    global lora_ser, is_sending
    
    # 检查当前是否正在发送数据，如果是则等待
    while is_sending:
        print("[信息] 当前有数据正在发送，等待发送完成...")
        time.sleep(0.1)
    
    # 设置发送状态为正在发送
    is_sending = True
    
    try:
        # 检查LoRa串口是否已初始化并打开
        if not lora_ser or not lora_ser.is_open:
            print("[错误] LoRa串口未初始化或未打开，无法发送问询帧")
            return
        
        # 构建问询帧，格式: AA 设备号 FF
        inquiry_frame = bytes([0xAA, device_id, 0xFF])
        
        # 发送问询帧
        lora_ser.write(inquiry_frame)
        hex_string = ' '.join(f'{b:02x}' for b in inquiry_frame)
        print(f"-> 发送问询帧: {hex_string} (设备ID: {device_id})")
         
    except Exception as e:
        print(f"[错误] 发送问询帧失败: {e}")
    finally:
        # 无论是否发生异常，都设置发送状态为未发送
        is_sending = False
##处理串口识别到的数据
class SerialWorker(QObject):
        """用于在后台线程中处理串口通信"""
        # 定义信号，用于向主窗口发送数据
        data_received = pyqtSignal(int, int, str)   # 发送设备数据给主线程
        data_voice_data = pyqtSignal(int,int)  # 发送语音指令数据给主线程
        env_data = pyqtSignal(int, int, float, int, float, int, int)  # 发送环境数据给主线程
        
        def handle_Voice_data(self, data):
            """
            处理从语言识别串口接收到的数据，数据格式为十六进制格式(55 AA 01 01 00 FF)
            
            Args:
                data (str): 接收到的串口数据
            """
            try:
                # 检查是否有内容
                if not data.strip():
                    return
                
                # 尝试清理数据并提取十六进制值
                # 移除可能的空格、换行符等非十六进制字符
                clean_data = data.strip().replace(' ', '')
                
                # 检查数据是否为有效的十六进制格式
                if len(clean_data) % 2 != 0 or not re.match(r'^[0-9a-fA-F]+$', clean_data):
                    print(f"[处理] 不是有效的十六进制格式: {data}")
                    return
                
                # 将十六进制字符串转换为字节列表
                hex_bytes = []
                for i in range(0, len(clean_data), 2):
                    hex_bytes.append(int(clean_data[i:i+2], 16))
                
                 
                # 指令格式: [帧头1, 帧头2, 数据1, 数据2, 额外数据, 校验和]
                if len(hex_bytes) >= 6 and hex_bytes[0] == 0x55 and hex_bytes[1] == 0xAA and hex_bytes[5] == 0xFF:
                    # 使用索引2和3作为数据1和数据2
                    data1 = hex_bytes[3] 
                    data2 = hex_bytes[4]                    
                    self.data_voice_data.emit(data1,data2)### 更新ui显示
                    ##处理并发送对应的指令
                else:
                    print(f"[处理] 不是有效的语音指令帧格式")
                    print(f"  接收到的字节: {['0x{:02X}'.format(b) for b in hex_bytes]}")
                    
            except Exception as e:
                print(f"[错误] 处理语音指令数据时发生异常: {e}")

        def __init__(self, port, baud_rate, timeout):
            super().__init__()
            self.port = port
            self._is_running = True
            self.baud_rate = baud_rate
            self.timeout = timeout
            self.ser = None
        def stop(self):
            """设置停止标志位"""
            self._is_running = False
            print("已向后台线程发送停止信号...")
        def handle_Lora_data(self, data):
            """
            处理从LoRa模块接收到的数据，数据格式为十六进制格式(FE 06 90 1F 00 0B 00 01 02 03 04 EF)
            
            Args:
                data (list): 接收到的串口数据
            """
            print(f"[处理2] 接收到的字节: {['0x{:02X}'.format(b) for b in data]}")
            
            if len(data) == 11 and data[5] ==0x0B:   
                print(f"[处理] 是有效的车位状态帧格式")
                for i in range(7,10):
                    chewei= i-6 # 计算车位编号，下标7对应车位1，8对应2，9对应3
                    if data[i]>0 and  data[i] <3:
                        print(f"车位{chewei}状态:{chewei_status[data[i]]}")
                        self.data_received.emit(CHEWEI_FLAG,chewei,chewei_status[data[i]])
            if len(data) >= 8 and data[5] ==0x0C:
                print(f"[处理] 是有效的人数格式")
                self.data_received.emit(PLYER_COUNT_FLAG,0,str(data[7])+" 人")
            if len(data) >= 8 and data[5] ==0x10:
                print(f"[处理] 是有效的小车位置格式")
                if data[7]>=1 and data[7] <= 11:
                    self.data_received.emit(CAR_FLAG,0,weizhi_status[data[7]])
            if len(data)  >= 15 and data[5] ==0x03:
                print(f"[处理] 是有效的环境数据格式")
                flag = 0
                temp=data[8]
                hum = data[7]
                pm25 = (data[10] << 8) | data[9] 
                pm25 = pm25/10.0
                light = data[11] 
                windspeed = data[12] / 10
                uv = data[13]
                weather = data[14]
                flag = flag+1

                if flag == 1:
                    flag == 0
                    print(f"温度:{temp}℃,湿度:{hum}%,PM2.5:{pm25}μg/m³,光照:{light}lux,风速:{windspeed}m/s,UV:{uv},天气:{weather}")
                    self.env_data.emit(temp,hum,pm25,light,windspeed,uv,weather)
                else:
                    print("接收数据异常")
                if data[len(data)-1] == 0x0A:
                    print("门已打开")
                    print("打开门（新指令格式）")
                    send_lora_command(0x10,0x01,3,1)
            elif len(data) >= 15 and data[0]==0xFE and data[1]==0x06 and data[2]==0x90 and data[3]==0x90 and data[4]==0x1F and data[5]==0x0B and data[14]==0x0A:
                    print("打开门（新指令格式）")
                    send_lora_command(0x10,0x01,3,1)
                    
                    print("发送指令完成")
            if data[0]==0x55 and data[1]==0x01 and data[2]==0x00 and data[3]==0x0A:
                    print("打开门")
                    send_lora_command(0x10,0x01,3,1)
                                      
                    print("发送指令完成")
           
        
            time.sleep(0.1)
        def run(self):
            """在后台线程中打开串口"""
            print("后台串口监听线程已启动。")
            while self._is_running:
                try:
                    ##监听语言识别的串口
                    if voice_ser and voice_ser.is_open:
                        # 直接读取原始字节数据，不进行UTF-8解码
                        if voice_ser.in_waiting > 0:  # 检查是否有数据可读  
                            raw_data = voice_ser.read(6)
                            ##
                            if raw_data:
                                # 将原始字节数据转换为十六进制字符串格式
                                hex_data = ' '.join(f'{b:02x}' for b in raw_data)
                                print(f"<- 串口接收 (原始字节): {hex_data}")
                                # 直接传递原始数据的十六进制表示给处理函数
                                self.handle_Voice_data(hex_data)
                    # 短暂休眠以减少CPU占用
                    time.sleep(0.01)
                except serial.SerialException as e:
                    print(f"[严重错误] 后台线程发生未知错误: {e}")
                    # 发生错误时短暂休眠，避免刷屏
                    time.sleep(2)
                except Exception as e:
                    print(f"[错误] 处理串口数据时发生异常: {e}")
                    time.sleep(0.1)
                #监听lora指令的串口
                try:
                    ##监听控制指令的串口
                    if lora_ser and lora_ser.is_open:
                        if lora_ser.in_waiting > 0:  # 检查是否有数据可读  
                            data = list(lora_ser.readline())  # 读取一行数据，并去除行尾的换行符  
                            #print(f"[处理1] 接收到的字节: {['0x{:02X}'.format(b) for b in data]}")
                            ##清空接收缓冲区
                            lora_ser.reset_input_buffer()
                            if  data[0]==0xFE and data[1]==0x06 and data[2]==0x90 and data[4]==0x1f:
                                print(f"[处理] 是有效格式")
                                self.handle_Lora_data(data) 
                    
                          
                except Exception as e:
                    print(f"[错误] 处理控制指令数据时发生异常: {e}")
                    # 发生错误时重置缓冲区状态
                    self.json_buffer = b''
                    self.is_collecting_json = False
                    time.sleep(0.1)     

##主线程窗口
class MainWindow(QMainWindow):

    
    ##初始化主线程窗口，处理和更新ui显示
    def __init__(self):
        super().__init__()     
        try:
            uic.loadUi(UI_FILE_PATH, self)##加载UI文件
        except Exception as e:
            print(f"[错误] 加载UI文件时发生异常: {e}")
            return
            # 初始化天气显示
        self.init_weather_display()
        self.set_background_image()##设置背景图片        
        self.init_time_display()##初始化时间显示        
        # self.init_inquiry_timer()##初始化问询定时器
        self.init_labels()##初始化标签
        # 初始化future_weather列表
        self.future_weather = []
        # 初始获取天气数据
        self.get_weather_data()
        ##全屏显示
        self.showFullScreen()  # 启动即全屏显示
    def init_time_display(self):
        """初始化时间显示"""
        # 设置标签样式
        self.clock.setFont(QFont("SimSun", 20, QFont.Bold))
        self.clock.setStyleSheet("color: black;")
        self.clock.setAlignment(Qt.AlignCenter)
        self.clock.raise_()
        
        # 初始化时间计时器，每秒更新一次时间
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)  # 每秒更新一次
        
        # 立即更新一次时间
        self.update_time()
    def init_weather_display(self):
        """初始化天气显示"""
        # 设置标签样式
        # 立即获取一次天气数据
        self.get_weather_data()
        self.weather.setFont(QFont("SimSun", 20, QFont.Bold))
        self.weather.setStyleSheet("color: black;")
        self.weather.setAlignment(Qt.AlignCenter)
        self.weather.raise_()
        print("初始化天气显示")
        # 初始化天气计时器，每60秒更新一次天气数据
        self.weather_timer = QTimer(self)
        self.weather_timer.timeout.connect(self.get_weather_data)
        self.weather_timer.start(weather_asktime)  # 每30秒更新一次天气
    def update_time(self):
        """更新时间显示"""
        # 设置时区为UTC+8（北京时间）
        beijing_tz = timezone(timedelta(hours=8))
        now = datetime.now(beijing_tz)
        
        # 格式化星期，以便中文显示
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        weekday_str = weekdays[now.weekday()]

        # 格式化日期和时间字符串，包含年月日、星期和时分秒
        time_str = f"{now.year}年{now.month}月{now.day}日 {weekday_str} {now.strftime('%H:%M:%S')}"
        
        self.clock.setText(time_str)
        self.clock.adjustSize() # 自动调整标签大小以适应内容               
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
            # 设置centralwidget为透明背景
            self.centralwidget.setStyleSheet("background-color: transparent;")
            
            pixmap = QPixmap(image_path)
            # 创建背景label，并设置为MainWindow的直接子部件，而不是centralwidget的子部件
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
                Qt.IgnoreAspectRatio, 
                Qt.SmoothTransformation
            )            
            
            # 设置背景label的几何属性，使其覆盖整个窗口
            self.background_label.setGeometry(0, 0, self.image_width, self.image_height)
            self.background_label.setPixmap(scaled_pixmap)
            self.background_label.setAlignment(Qt.AlignCenter)
            self.background_label.setStyleSheet("background-color: transparent;")
            
            # 确保背景label在最底层
            self.background_label.lower()
            
            # 确保centralwidget在背景label之上
            self.centralwidget.raise_()
            
        except Exception as e:
            print(f"设置背景图片出错: {e}")    
    def init_inquiry_timer(self):
        """初始化问询定时器，每隔一段时间启动一轮设备问询"""
        self.inquiry_timer = QTimer(self)
        self.inquiry_timer.timeout.connect(self.send_inquiry)
        # 设置为每30秒启动一轮新的问询，避免过于频繁
        self.inquiry_timer.start(devices_asktime)  # 30000毫秒 = 30秒
        print(f"问询定时器已启动，每{devices_asktime/1000}秒发送一轮设备问询帧")    
        ##立即开始
        self.send_inquiry()
    def send_inquiry(self):
        """发送问询帧到所有设备，使用非阻塞方式"""
        # 使用计数器跟踪当前要发送的设备ID
        self.current_device_index = 0
        # 如果已经存在设备定时器，先停止它
        if hasattr(self, 'device_timer'):
            self.device_timer.stop()
        # 启动设备发送定时器
        self.device_timer = QTimer(self)
        self.device_timer.timeout.connect(self.send_next_inquiry)
        # 立即发送第一个设备的问询帧
        self.send_next_inquiry()
        # 设置定时器间隔，确保设备之间有足够的间隔
        self.device_timer.start(asktime)
    def send_next_inquiry(self):
        """发送下一个设备的问询帧"""
        # 检查是否还有设备需要发送
        if self.current_device_index < len(inquiry_device_ids):
            device_id = inquiry_device_ids[self.current_device_index]  # 从预定义的设备ID数组中获取
            send_inquiry_frame(device_id=device_id)
            print(f"发送问询帧到设备 {device_id}")
            # 增加索引
            self.current_device_index += 1
        else:
            # 所有设备都已发送，停止设备定时器
            self.device_timer.stop()
            print("完成本轮设备问询")
            # 重新启动问询定时器，等待下一轮问询
            self.inquiry_timer.start(devices_asktime)      
    def init_label(self, label, initial_value, color="rgb(186,128,0)"):
        """初始化标签显示"""
        # 设置文字内容
        label.setText(str(initial_value))
        
        # 设置文字样式
        label.setFont(QFont("SimSun", 12, QFont.Bold))  # 字体、大小、加粗
        label.setStyleSheet(f"color: {color};")  # 文字颜色   
        
        # 设置文字对齐方式
        label.setAlignment(Qt.AlignCenter)        
        # 确保文字显示在背景上方
        label.raise_()
    def init_labels(self):
        """初始化所有标签"""
        ##初始化气象站标签
        # 初始化温度标签
        self.init_label(self.temp_label, "88℃")
        # 初始化湿度标签
        self.init_label(self.humidity_label, "88.8%") 
        # 初始化PM2.5标签
        self.init_label(self.pm25_label, "26")
        # 初始化光照标签
        self.init_label(self.light_label, "888lux")
        # 初始化紫外线标签
        self.init_label(self.uv_label, "88")
        # 初始化风速标签
        self.init_label(self.windspeed_label, "8m/s")
        # 初始化天气标签
        self.init_label(self.weather_label, "晴")        
        # 初始化大门和灯光设备标签
        self.init_label(self.door_label, "关闭")  # 校园大门
        self.init_label(self.music_stage_label, "停止播放")  # 校园音乐台
        self.init_label(self.radio_station_label, "停止播放")  # 校园广播站
        self.init_label(self.sports_field_label, "0人")  # 运动场人数
        self.init_label(self.parking1_label, "空位")  # 智慧一号停车库
        self.init_label(self.parking2_label, "空位")  # 智慧二号停车库
        self.init_label(self.parking3_label, "空位")  # 智慧三号停车库
        self.init_label(self.driverless_car_label, "停车状态")  # 无人驾驶小车
        self.init_label(self.colorful_light_label, "关闭")  # 炫彩灯带
        self.init_label(self.streetlight1_label, "关闭")  # 校园一号路灯
        self.init_label(self.streetlight2_label, "关闭")  # 校园二号路灯
        self.init_label(self.canteen_dorm_light_label, "关闭")  # 食堂/宿舍灯光        
        self.init_label(self.cultural_center_light_label, "关闭")  # 文体中心灯光        
        self.init_label(self.huizhi_hall_light_label, "关闭")  # 汇智厅灯光        
        self.init_label(self.admin_building_light_label, "关闭")  # 行政楼灯光       
        self.init_label(self.yuxian_building_light_label, "关闭")  # 育贤楼灯光
        self.init_label(self.yangzheng_building_light_label, "关闭")  # 养正楼灯光
    def gettime(self):
        self.time = time.asctime(time.localtime(time.time()))
        result_time = re.split(r' ', self.time)  # 正则
        if len(result_time) == 6:
            self.year = int(result_time[5])%100
            self.month =  int(months['%s' % result_time[1]])
            self.day = int(result_time[3])
            self.curTime = result_time[4]
        elif len(result_time) == 5:
            self.year = int(result_time[4])%100
            self.month = int(months['%s' % result_time[1]])
            self.day = int(result_time[2])
            self.curTime = result_time[3]
        result_hour=re.split(r':', self.curTime)
        self.hour=int(result_hour[0])
        self.minute=int(result_hour[1])
        self.second=int(result_hour[2])
    ##获取天气数据
    def get_weather_data(self):
        url = 'https://www.weather.com.cn/weather/101280201.shtml'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
        
        try:
            # 获取网页内容并处理编码，避免乱码
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'utf-8'  # 确保正确解码
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 初始化数据结构
            self.future_weather = []
            
            # 获取天气预报信息（今天和明天）
            weather_items = soup.find_all('li', class_='sky')
            
            # 只处理前2天的数据（今天和明天）
            for i, item in enumerate(weather_items):
                if i >= 2:  # 只取今天和明天
                    break
                
                try:
                    # 获取日期
                    date = item.find('h1').get_text().strip()
                    
                    # 获取天气状况
                    weather_condition = item.find('p', class_='wea').get_text().strip()
                    
                    # 获取温度信息
                    temperature = item.find('p', class_='tem').get_text().strip()
                    
                    # 添加到future_weather列表
                    self.future_weather.append([date, weather_condition, temperature])
                    
                     
                    
                except Exception as e:
                    print(f"处理天气数据项时出错: {e}")
            
            # 更新UI显示
            if len(self.future_weather) >= 1:
                # 今天天气信息
                today_date, today_weather, today_temp = self.future_weather[0]
                
                
                # 更新天气标签
                if hasattr(self, 'weather'):
                    weather_text = f"今日：{today_weather} {today_temp}"
                    if len(self.future_weather) >= 2:
                        # 如果有明天的数据，也显示出来
                        tomorrow_date, tomorrow_weather, tomorrow_temp = self.future_weather[1]
                        weather_text += f"  明日:{tomorrow_weather} {tomorrow_temp}"
                    self.weather.setText(weather_text)
                    self.weather.adjustSize()
                    
        except Exception as e:
            print(f"获取天气数据出错: {e}")
            # 出错时显示默认值
            if hasattr(self, 'weather'):
                self.weather.setText("数据获取中...")
                self.weather.adjustSize()

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
        self.Load_pic(self.temp_pic, "temp.png")
        self.Load_pic(self.humidity_pic, "humidity.png")
        self.Load_pic(self.light_pic, "light.png")
        self.Load_pic(self.sound_pic, "sound.png")
        self.Load_pic(self.co2_pic, "co2.png")
        self.Load_pic(self.pm25_pic, "pm25.png")
        self.Load_pic(self.pm10_pic, "pm10.png")
 
    def update_env_display(self, temp,hum,pm25,light,windspeed,uv,weather):
        self.temp_label.setText(str(temp)+" ℃")
        self.windspeed_label.setText(str(windspeed)+" m/s")
        self.humidity_label.setText(str(hum)+" %")
        self.pm25_label.setText(str(pm25)+" ug/m3")
        if light == 1:
            self.light_label.setText("充足")
        elif light == 0:
            self.light_label.setText("稀少")
        if weather == 1:
            self.weather_label.setText("雨")
        elif weather == 0:
            self.weather_label.setText("晴")
        if uv == 1:
            self.uv_label.setText("强")
        elif uv == 0:
            self.uv_label.setText("弱")
    def update_display(self,flag,data1,data2):
        """接收并处理SerialWorker发送的数据,同时从全局device_data数组中获取完整数据进行显示"""        
        if flag == CHEWEI_FLAG:
            print(f"更新车位{data1}状态为{data2}")
            if data1 == 1:
                self.parking1_label.setText(data2)
            elif data1 == 2:
                self.parking2_label.setText(data2)
            elif data1 == 3:
                self.parking3_label.setText(data2)
        elif flag == PLYER_COUNT_FLAG:
            print(f"更新操场人数为{data2}")
            self.sports_field_label.setText(data2)
        elif flag == CAR_FLAG:
            print(f"更新小车状态为{data2}")
            self.driverless_car_label.setText(data2)

                
    def update_voice_display(self, data1,data2):
        """接收并处理SerialWorker发送的语音指令数据"""
        print(f"主线程语音指令数据: 数据1: 0x{data1:02X}, 数据2: 0x{data2:02X}")
        if data1 == ALL_LIGHT:
            if data2 == ON:
                print("开启所有灯光")
                send_lora_command(ALL_LIGHT,data2)
                self.init_label(self.colorful_light_label, "炫彩灯")  # 炫彩灯带
                self.init_label(self.streetlight1_label, "开启")  # 校园一号路灯
                self.init_label(self.streetlight2_label, "开启")  # 校园二号路灯
                self.init_label(self.canteen_dorm_light_label, "开启")  # 食堂/宿舍灯光        
                self.init_label(self.cultural_center_light_label, "开启")  # 文体中心灯光        
                self.init_label(self.huizhi_hall_light_label, "开启")  # 汇智厅灯光        
                self.init_label(self.admin_building_light_label, "开启")  # 行政楼灯光       
                self.init_label(self.yuxian_building_light_label, "开启")  # 育贤楼灯光
                self.init_label(self.yangzheng_building_light_label, "开启")  # 养正楼灯光
            elif data2 == OFF:
                print("关闭所有灯光")
                send_lora_command(ALL_LIGHT,data2)
                self.init_label(self.colorful_light_label, "关闭")  # 炫彩灯带
                self.init_label(self.streetlight1_label, "关闭")  # 校园一号路灯
                self.init_label(self.streetlight2_label, "关闭")  # 校园二号路灯
                self.init_label(self.canteen_dorm_light_label, "关闭")  # 食堂/宿舍灯光        
                self.init_label(self.cultural_center_light_label, "关闭")  # 文体中心灯光        
                self.init_label(self.huizhi_hall_light_label, "关闭")  # 汇智厅灯光        
                self.init_label(self.admin_building_light_label, "关闭")  # 行政楼灯光       
                self.init_label(self.yuxian_building_light_label, "关闭")  # 育贤楼灯光
                self.init_label(self.yangzheng_building_light_label, "关闭")  # 养正楼灯光
        elif data1 == CAR:
            if data2 == ON:
                print("开启小车")
                send_lora_command(CAR,data2)
                self.init_label(self.driverless_car_label, "开启状态")  # 小车
            elif data2 == OFF:
                print("闭小车")
                send_lora_command(CAR,data2)

                self.init_label(self.driverless_car_label, "停止状态")  # 小车
        elif data1 == ROAD_LIGHT:
            if data2 == ON:
                print("同时打开一号和二号路灯")
                send_lora_command(ROAD_LIGHT,data2)                
                self.init_label(self.streetlight1_label, "开启")  # 校园一号路灯
                self.init_label(self.streetlight2_label, "开启")  # 校园二号路灯               
            elif data2 == OFF:
                print("关闭所有灯光")
                send_lora_command(ROAD_LIGHT,data2)               
                self.init_label(self.streetlight1_label, "关闭")  # 校园一号路灯
                self.init_label(self.streetlight2_label, "关闭")  # 校园二号路灯
            elif data2 ==0X03:
                print("打开自动照明")
                send_lora_command(ROAD_LIGHT,data2)                
                self.init_label(self.streetlight1_label, "自动照明")  # 自动照明
                self.init_label(self.streetlight2_label, "自动照明")  # 自动照明
            elif data2 ==0X04:
                print("关闭自动照明")
                send_lora_command(ROAD_LIGHT,data2)                 
                self.init_label(self.streetlight1_label, "关闭自动照明")  # 关闭自动照明
                self.init_label(self.streetlight2_label, "关闭自动照明")  # 关闭自动照明
            elif data2 ==0X05:
                print("打开一号照明路灯")
                send_lora_command(ROAD_LIGHT,data2)                
                self.init_label(self.streetlight1_label, "开启")  # 打开一号照明路灯
            elif data2 ==0X06:
                print("关闭一号照明路灯")
                send_lora_command(ROAD_LIGHT,data2)                
                self.init_label(self.streetlight1_label, "关闭")  # 关闭一号照明路灯
            elif data2 ==0X07:
                print("打开二号照明路灯")
                send_lora_command(ROAD_LIGHT,data2)                
                self.init_label(self.streetlight2_label, "开启")  # 开启二号照明
            elif data2 ==0X08:
                print("关闭二号照明路灯")
                send_lora_command(ROAD_LIGHT,data2)                
                self.init_label(self.streetlight2_label, "关闭")  # 关闭二号照明
        elif data1 == DOOR:
            if data2 == ON:
                print("开启门")
                send_lora_command(DOOR,data2)                
                self.init_label(self.door_label, "开启")  # 开启门
            elif data2 == OFF:
                print("关闭门")
                send_lora_command(DOOR,data2)                
                self.init_label(self.door_label, "关闭")  # 关闭门
        elif data1 == FLOOR_LIGHT:
            if data2 == 0x01:
                print("开启文体中心灯光")
                send_lora_command(FLOOR_LIGHT,data2)                
                self.init_label(self.cultural_center_light_label, "开启")  # 开启文体中心灯光
            elif data2 == 0X02:
                print("关闭文体中心灯光")
                send_lora_command(FLOOR_LIGHT,data2)                
                self.init_label(self.cultural_center_light_label, "关闭")  # 关闭文体中心灯光

            elif data2 == 0X03:
                print("开启汇智楼灯光")
                send_lora_command(FLOOR_LIGHT,data2)                
                self.init_label(self.huizhi_hall_light_label, "开启")  # 开启汇智楼灯光
            elif data2 == 0X04:
                print("关闭汇智楼灯光")
                send_lora_command(FLOOR_LIGHT,data2)                
                self.init_label(self.huizhi_hall_light_label, "关闭")  # 关闭汇智楼灯光

            elif data2 == 0X05:
                print("开启行政楼灯光")
                send_lora_command(FLOOR_LIGHT,data2)                
                self.init_label(self.admin_building_light_label, "开启")  # 开启行政楼灯光
            elif data2 == 0X06:
                print("关闭行政楼灯光")
                send_lora_command(FLOOR_LIGHT,data2)                
                self.init_label(self.admin_building_light_label, "关闭")  # 关闭行政楼灯光

            elif data2 == 0X07:
                print("开启育贤楼灯光")
                send_lora_command(FLOOR_LIGHT,data2)                
                self.init_label(self.yuxian_building_light_label, "开启")  # 开启育贤楼灯光
            elif data2 == 0X08:
                print("关闭育贤楼灯光")
                send_lora_command(FLOOR_LIGHT,data2)                
                self.init_label(self.yuxian_building_light_label, "关闭")  # 关闭育贤楼灯光

            elif data2 == 0X09:
                print("开启食堂/宿舍灯光")
                send_lora_command(FLOOR_LIGHT,data2)                
                self.init_label(self.canteen_dorm_light_label, "开启")  # 开启食堂/宿舍灯光
            elif data2 == 0X0A:
                print("关闭食堂/宿舍灯光")
                send_lora_command(FLOOR_LIGHT,data2)                
                self.init_label(self.canteen_dorm_light_label, "关闭")  # 关闭食堂/宿舍灯光 

            elif data2 == 0X0B:
                print("打开养正楼灯光")
                send_lora_command(FLOOR_LIGHT,data2)                
                self.init_label(self.yangzheng_building_light_label, "开启")  # 开启养正楼灯光                
            elif data2 == 0X0C:
                print("关闭所有灯光")
                send_lora_command(FLOOR_LIGHT,data2)                
                self.init_label(self.yangzheng_building_light_label, "关闭")  # 关闭所有灯光
        elif data1 == COLORFUL_LIGHT:
            if data2 == 0X0A:
                print("开启神经网络灯带")
                send_lora_command(COLORFUL_LIGHT,data2)                
                self.init_label(self.colorful_light_label, "开启")  # 开启神经网络灯带
            elif data2 == 0X0B:
                print("关闭神经网络灯带")
                send_lora_command(COLORFUL_LIGHT,data2)                
                self.init_label(self.colorful_light_label, "关闭")  # 关闭神经网络灯带
            elif data2 == 0X09:
                print("流水灯光")
                send_lora_command(COLORFUL_LIGHT,data2)                
                self.init_label(self.colorful_light_label, "流水")  # 流水灯光
            elif data2 == 0X08:
                print("呼吸灯光")
                send_lora_command(COLORFUL_LIGHT,data2)                
                self.init_label(self.colorful_light_label, "呼吸")  # 呼吸灯光
            elif data2 ==0x01:
                print("红色灯")
                send_lora_command(COLORFUL_LIGHT,data2)                
                self.init_label(self.colorful_light_label, "红色")  # 红色灯
            elif data2 ==0x02:
                print("橙色灯")
                send_lora_command(COLORFUL_LIGHT,data2)                
                self.init_label(self.colorful_light_label, "橙色")  # 橙色灯
            elif data2 ==0x03:
                print("黄色灯")
                send_lora_command(COLORFUL_LIGHT,data2)                
                self.init_label(self.colorful_light_label, "黄色")  # 黄色灯    
            elif data2 ==0x04:
                print("绿色灯")
                send_lora_command(COLORFUL_LIGHT,data2)                
                self.init_label(self.colorful_light_label, "绿色")  # 绿色灯
            elif data2 ==0x05:
                print("青色灯")
                send_lora_command(COLORFUL_LIGHT,data2)                
                self.init_label(self.colorful_light_label, "青色")  # 青色灯
            elif data2 ==0x06:
                print("蓝色灯")
                send_lora_command(COLORFUL_LIGHT,data2)                
                self.init_label(self.colorful_light_label, "蓝色")  # 蓝色灯
            elif data2 ==0x07:
                print("紫色灯")
                send_lora_command(COLORFUL_LIGHT,data2)                
                self.init_label(self.colorful_light_label, "紫色")  # 紫色灯
        elif data1 == ENVIRONMENT_MP3:
            if data2 == 0X05:
                print("播报当前环境数据")
                send_lora_command(ENVIRONMENT_MP3,data2,times=1)    
                
            elif data2 == 0X02:
                print("播报当前温度")
                send_lora_command(ENVIRONMENT_MP3,data2,times=1)    

            elif data2 == 0X01:
                print("播报当前湿度")
                send_lora_command(ENVIRONMENT_MP3,data2,times=1)    
            
            elif data2 == 0X06:
                print("播报当前风速")
                send_lora_command(ENVIRONMENT_MP3,data2,times=1)    
            elif data2 == 0X03:
                print("播报当前PM2.5")
                send_lora_command(ENVIRONMENT_MP3,data2,times=1)    
            elif data2 == 0X07:
                print("播报当前UV")
                send_lora_command(ENVIRONMENT_MP3,data2,times=1)    
            elif data2 == 0X08:
                print("播报当前光照")
                send_lora_command(ENVIRONMENT_MP3,data2,times=1)                    
            elif data2 == 0X09:
                print("播报当前天气")
                send_lora_command(ENVIRONMENT_MP3,data2,times=1)    
        elif data1 == MUSIC_STAGE:
            if data2 == 0X01:
                print("播放音乐")
                send_lora_command(MUSIC_STAGE,data2,times=1)   
                 
            elif data2 == 0X06:
                    print("暂停音乐")
                    send_lora_command(MUSIC_STAGE,data2,times=1)        
            elif data2 == 0X07:
                    print("继续播放音乐")
                    send_lora_command(MUSIC_STAGE,data2,times=1)    
            elif data2 == 0X0B:
                    print("关闭音乐")
                    send_lora_command(MUSIC_STAGE,data2,times=1)    
            elif data2 == 0X03:
                    print("上一曲")
                    send_lora_command(MUSIC_STAGE,data2,times=1)  
            elif data2 == 0X02:
                    print("下一曲")
                    send_lora_command(MUSIC_STAGE,data2,times=1)    
            elif data2 == 0X04:
                    print("提高音量")
                    send_lora_command(MUSIC_STAGE,data2,times=1)  
            elif data2 == 0X05:
                    print("降低音量")
                    send_lora_command(MUSIC_STAGE,data2,times=1)    
            elif data2 == 0X09:
                    print("调整到最小音量")
                    send_lora_command(MUSIC_STAGE,data2,times=1)    
            elif data2 == 0X0A:
                    print("调整到中等音量")
                    send_lora_command(MUSIC_STAGE,data2,times=1)    
            elif data2 == 0X08:
                    print("调整到最大音量")
                    send_lora_command(MUSIC_STAGE,data2,times=1)    
        elif data1 == RADIO_STAGE:
            if data2 == 0X01:
                print("上课铃声")
                send_lora_command(RADIO_STAGE,data2)
                self.init_label(self.radio_station_label, "上课铃声")  # 上课铃声  
            elif data2 == 0X02:
                print("下课铃声")
                send_lora_command(RADIO_STAGE,data2)
                self.init_label(self.radio_station_label, "下课铃声")  # 下课铃声  
            elif data2 == 0X03:
                print("出操")
                send_lora_command(RADIO_STAGE,data2)    
                self.init_label(self.radio_station_label, "出操")  # 出操  
            elif data2 == 0X04:
                print("课间铃")
                send_lora_command(RADIO_STAGE,data2)    
                self.init_label(self.radio_station_label, "课间铃")  # 课间铃  
            elif data2 == 0X05:
                print("校园简历")
                send_lora_command(RADIO_STAGE,data2)    
                self.init_label(self.radio_station_label, "校园简历")  # 校园简历  
            elif data2 == 0X06:
                print("插播")
                send_lora_command(RADIO_STAGE,data2)    
                self.init_label(self.radio_station_label, "插播")  # 插播  
            elif data2 == 0X07:
                print("停止")
                send_lora_command(RADIO_STAGE,data2)    
                self.init_label(self.radio_station_label, "停止")  # 停止  
            elif data2 == 0X08:
                print("眼保健操")
                send_lora_command(RADIO_STAGE,data2)    
                self.init_label(self.radio_station_label, "眼保健操")  # 眼保健操  
        elif data1 == WEAYHER_TIME:
            if data2 == 0X01:##
                print("播报时间")
                self.gettime()
                print(f"正在发送的天气数据[0xFE, 0x06, 0x90, 0x90, 0x1F, 0x00, 0x05, {self.month}, {self.day}, {self.hour}, {self.minute}, {self.second}, {self.year}, 0x01, 0xFF]")
                lora_ser.write([0xFE, 0x06, 0x90, 0x90, 0x1F, 0x00, 0x05, self.month, self.day, self.hour, self.minute, self.second, self.year, 0x01, 0xFF])
      
            elif data2 == 0X02:
                print("播报天气")
                self.get_weather_data()         
                print(self.future_weather[0][1])
                parts = self.future_weather[0][1].split('转')
                tq= [0,0]
                for index ,tiqi in enumerate(parts):
                    for i in range(0,15):
                        if tiqi in weathers[i]:
                            tq[index] = i

                
                qiwen=re.findall(r'\d+',str(self.future_weather[0][2]))
                tianqi=[int(tq[0]),int(tq[1])]
                qw=int(qiwen[0])+30
                for i in range(0,1):
                    print(f"正在发送的天气数据[0xFE, 0x06, 0x90, 0x90, 0x1F,0x00, 0x0F,{tianqi[0]}, {tianqi[1]}, {qw}, 0, 0xFF]")
                    lora_ser.write([0xFE, 0x06, 0x90, 0x90, 0x1F,0x00, 0x0F,tianqi[0], tianqi[1], qw, 0, 0xFF])
                    time.sleep(0.2)
            
               
    
                 
            
# ================== 主程序入口 ==================
def main():
    """主函数"""
    global voice_ser, lora_ser
    
    # 初始化变量，避免finally块中访问未定义变量
    serial_worker = None
    worker_thread = None
    
    try:
        # 创建Qt应用程序实例
        app = QApplication(sys.argv)
        app.setApplicationName("校园沙盘控制系统")
        
        # 初始化串口
        print("正在初始化串口...")
        # 1. 尝试打开语音识别模块串口
        try:
            voice_ser = serial.Serial(VOICE_PORT, VOICE_BAUD_RATE, timeout=VOICE_TIMEOUT)
            print(f"成功打开语音识别串口 {VOICE_PORT}")
            
        except serial.SerialException as e:
            print(f"[警告] 无法打开语音识别串口 {VOICE_PORT}: {e}")
            # 仅记录警告，不中断程序
        
        # 2. 尝试打开LoRa模块串口
        try:
            lora_ser = serial.Serial(LORA_PORT, LORA_BAUD_RATE, timeout=LORA_TIMEOUT)
            print(f"成功打开LoRa串口 {LORA_PORT}")
            
        except serial.SerialException as e:
            print(f"[警告] 无法打开LoRa串口 {LORA_PORT}: {e}")
            # 仅记录警告，不中断程序
        
        # 3. 创建并启动SerialWorker线程        
        serial_worker = SerialWorker(VOICE_PORT, VOICE_BAUD_RATE, VOICE_TIMEOUT)
        worker_thread = QThread()
        
        # 创建主窗口
        main_window = MainWindow()
        
        # 将worker移动到线程中
        serial_worker.moveToThread(worker_thread)
        
        # 连接信号和槽
        worker_thread.started.connect(serial_worker.run)
        # 连接SerialWorker的数据信号到MainWindow的显示槽
        serial_worker.data_received.connect(main_window.update_display)
        serial_worker.data_voice_data.connect(main_window.update_voice_display)
        serial_worker.env_data.connect(main_window.update_env_display)
        
        # 启动线程，这将触发started信号并调用serial_worker.run()
        worker_thread.start()
        main_window.show()
        print("串口监听已开始，请按Ctrl+C停止程序...")       
        # 运行应用程序主循环
        sys.exit(app.exec_())   
    except Exception as e:
        print(f"[严重错误] 程序发生异常: {e}")
    finally:
        # 停止工作线程
        if serial_worker is not None:
            try:
                serial_worker.stop()
            except Exception as e:
                print(f"停止工作线程时出错: {e}")
        
        if worker_thread is not None and worker_thread.isRunning():
            try:
                worker_thread.quit()
                worker_thread.wait()
                print("后台线程已停止")
            except Exception as e:
                print(f"停止线程时出错: {e}")
        
        # 关闭串口
        if voice_ser and voice_ser.is_open:
            try:
                voice_ser.close()
                print(f"已关闭语音输入串口 {VOICE_PORT}")
            except Exception as e:
                print(f"关闭语音串口时出错: {e}")
                
        if lora_ser and lora_ser.is_open:
            try:
                lora_ser.close()
                print(f"已关闭LoRa串口 {LORA_PORT}")
            except Exception as e:
                print(f"关闭LoRa串口时出错: {e}")
        
        print("程序已安全退出")


if __name__ == '__main__':
    
    main()