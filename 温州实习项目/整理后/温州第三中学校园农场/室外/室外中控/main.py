from platform import node
import sys
import os
import csv
from pathlib import Path
from datetime import datetime, timezone, timedelta
from tkinter import OFF
import turtle
import serial
import json
import time
import subprocess
import re
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QWidget
from PyQt5.QtGui import QPixmap, QFont, QPainter, QBrush, QConicalGradient, QPen, QColor
from PyQt5.QtCore import QThread, QObject, pyqtSignal, Qt, QTimer, QRectF
import PyQt5.uic as uic
from ybp import GaugeWidget


### 语音输入串口参数
VOICE_PORT = '/dev/ttyAMA4'    # 连接语音模块的串口
LORA_PORT = '/dev/ttyAMA0'      # 连接LoRa模块的串口
VOICE_BAUD_RATE = 9600  # 语音模块的波特率
LORA_BAUD_RATE = 115200  # LoRa模块的波特率
VOICE_TIMEOUT  = 1 
LORA_TIMEOUT  = 1 

DISPLAY_MODE4K=True ##是否显示4K图片
asktime=15000  # 询问设备数据的时间间隔，改为30秒


IMG_PATH = r"/home/pi/Desktop/SmartFamer/pic"
BACKGROUND_IMAGE = os.path.join(IMG_PATH, "background.jpg")
OPEN_IMAGE = os.path.join(IMG_PATH, "open.png")
DOWN_IMAGE = os.path.join(IMG_PATH, "down.png")
OFF_IMAGE = os.path.join(IMG_PATH, "off.png")
ON_IMAGE = os.path.join(IMG_PATH, "on.png")
# --- 全局串口对象 ---
# 在程序启动时初始化，供全局调用
voice_ser = None  # 语音输入串口实例
lora_ser = None     # LoRa串口实例
send_lora_Times=3 # 发送LoRa指令的次数，默认3次
is_sending = False  # 全局变量，用于标识当前是否正在发送数据

# 创建一个长度为8的数组，用于保存设备数据
devices_data = [None] * 3  # 初始化为全零，每个元素将存储一个设备的数据字典
mode_state=False  # 设备1模式状态

# ================== 常量定义 ==================
SOIL_MOISTURE_THRESHOLD = 50  # 土壤湿度阈值，低于此值打开喷淋系统
SPRAY_OFF_DELAY_MS = 25000  # 喷淋系统图标显示延迟关闭时间，单位毫秒

# ================== LoRa指令发送 ==================
def send_lora_command(device_id, node_id, action):
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
        header = 0x55  # 固定的帧头
        # 计算位
        checksum =0xFF
        # 将所有部分打包成一个bytes对象
        command = bytes([header,0xAA,device_id, node_id, action, checksum])
        print(f"发送指令: {command}")
        # 为了提高无线通信的可靠性，同一指令连续发送3次
        for attempt in range(send_lora_Times):
            lora_ser.write(command)
            # 为了方便调试，将发送的字节指令以十六进制格式打印出来
            hex_string = ' '.join(f'{b:02x}' for b in command)
            print(f"-> LoRa发送 (第{attempt+1}次): {hex_string}")
            time.sleep(0.3)  # 每次发送后短暂延时
        
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
        time.sleep(0.5)
    
    # 设置发送状态为正在发送
    is_sending = True
    
    try:
        # 检查LoRa串口是否已初始化并打开
        if not lora_ser or not lora_ser.is_open:
            print("[错误] LoRa串口未初始化或未打开，无法发送问询帧")
            return
        
        # 构建问询帧，格式: AA 设备号 FF
        inquiry_frame = bytes([0xDD, device_id])
        
        # 发送问询帧
        lora_ser.write(inquiry_frame)
        hex_string = ' '.join(f'{b:02x}' for b in inquiry_frame)
        print(f"-> 发送问询帧: {hex_string} (设备ID: {device_id})")
        time.sleep(1)  # 等待发送完成
    except Exception as e:
        print(f"[错误] 发送问询帧失败: {e}")
    finally:
        # 无论是否发生异常，都设置发送状态为未发送
        is_sending = False

##处理串口识别到的数据
class SerialWorker(QObject):
        """用于在后台线程中处理串口通信"""
        # 定义信号，用于向主窗口发送数据
        data_received = pyqtSignal(str)   # 发送设备数据给主线程
        data_voice_data = pyqtSignal(int,int,int)  # 发送语音指令数据给主线程
        data_received_lora = pyqtSignal(str)  # 发送传感器数据给主线程，只传递整行字符串
        
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
                
                # 检查是否符合指令格式 (55 AA 04  04 01 FF)
                # 只需要获取第5个数据（索引4）
                if len(hex_bytes) >= 5 and hex_bytes[0] == 0x55:
                    # 确保至少有5个数据才能访问索引4
                    if len(hex_bytes) > 4:
                        fifth_data = hex_bytes[4]  # 获取第5个数据
                        # 发送第5个数据，保留原有参数结构但只使用第一个位置
                        
                        send_lora_command(0x04, 0x04, fifth_data)
                        lora_ser.write(bytes([hex_bytes[0], hex_bytes[1], hex_bytes[2], hex_bytes[3], hex_bytes[4]]))#转发指令
                        self.data_voice_data.emit(fifth_data, 0, 0)
                else:
                    print(f"[处理] 不是有效的语音指令帧格式")
                    print(f"  接收到的字节: {['0x{:02X}'.format(b) for b in hex_bytes]}")
                    #清空接收缓冲区
                    lora_ser.reset_input_buffer()
                    
                    
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
            """停止线程"""
            self._is_running = False
            
        def handle_B0_command(self, command):
            """处理接收到的B0 01命令"""
            global devices_data
            try:
                print(devices_data)
                
                # 构建指定格式的数据包
                packet_parts = ["SS"]
                
                # 遍历2个土壤传感器设备（设备1和设备2）
                for target_device_id in [1, 2]:
                    # 查找对应设备ID的数据
                    device = None
                    for d in devices_data:
                        if d is not None and d.get('device_id') == target_device_id:
                            device = d
                            break
                    
                    if device is not None:
                        # 有有效设备数据
                        packet_parts.extend([
                            str(device.get('device_id', target_device_id)),
                            f"{device.get('soil_moisture', 0.0):.1f}",
                            f"{device.get('soil_temp', 0.0):.1f}",
                            
                            
                            f"{device.get('soil_ph', 0.0):.1f}",
                            f"{device.get('soil_ec', 0.0):.1f}",
                            str(device.get('relay_state', 0))
                        ])
                    else:
                        # 无设备数据，填充默认值
                        packet_parts.extend([str(target_device_id), "0.0", "0.0", "0.0", "0.0", "0"])
                
                packet_parts.append("3")  # 固定值3
                packet_parts.append("0")  # 固定值0
                packet_parts.append("PP")  # 结束标记
                
                # 组合成最终数据包
                packet = ",".join(packet_parts)
                print(f"构建的数据包: {packet}")
            
                for i in range(3):
                    lora_ser.write(bytes(packet, 'utf-8'))
                    time.sleep(1)  # 每次发送后短暂延时
                time.sleep(0.5)  # 每次发送后短暂延时
                
                # 这里可以添加发送数据包的代码
                # send_packet(packet)
                
            except Exception as e:
                print(f"处理B0命令时出错: {e}")
            print("已向后台线程发送停止信号...")
        def run(self):
            """在后台线程中打开串口"""
            print("后台串口监听线程已启动。")
            while self._is_running:
                try:
                    ##监听语音识别的串口
                    if voice_ser and voice_ser.is_open:
                        # 直接读取原始字节数据，不进行UTF-8解码
                        raw_data = voice_ser.readline()
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
                        # 首先检查是否有足够的字节可读
                        if lora_ser.in_waiting >= 2:
                            # 读取两个字节的原始数据
                            data = lora_ser.read(2)
                            
                            # 检查是否是B0 01命令（十六进制格式）
                            if data == bytes([0xB0, 0x01]):
                                # 打印接收到的十六进制命令
                                print(f"<- 串口接收到命令: B0 01")
                                # 执行处理B0 01命令的函数
                                self.handle_B0_command("B0 01")
                                continue
                            else:
                                # 如果不是B0 01命令，将读取的字节放回缓冲区
                                lora_ser.write(data)
                        
                        # 常规文本数据处理
                        line = lora_ser.readline().decode('utf-8', errors='ignore').strip()
                        # 跳过空行
                        if not line:
                            continue
                        
                        # 打印接收到的传感器数据（横向紧凑格式）
                        print(f"<- 串口接收传感器数据: {line}")
                        # 处理传感器数据
                        #发送数据到main.py
                        self.data_received_lora.emit(line)
                                               
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
        uic.loadUi('/home/pi/Desktop/SmartFamer/main.ui', self)##加载UI文件

        self.set_background_image()##设置背景图片        
        self.init_time_display()##初始化时间显示        
        self.init_inquiry_timer()##初始化问询定时器
        
        self.Load_pics()
        
        self.init_all_labels()  # 初始化所有标签
        self.init_gauges()  # 初始化仪表盘
        # 创建存储三个设备的传感器数据数组
        devices_data = [
            {   # 设备一
                'device_id': 1,
                'soil_moisture': 0.0,
                'soil_temp': 0.0,
                'soil_ec': 0.0,
                'soil_ph': 0.0,
                'relay_state': 0
            },
            {   # 设备二
                'device_id': 2,
                'soil_moisture': 0.0,
                'soil_temp': 0.0,
                'soil_ec': 0.0,
                'soil_ph': 0.0,
                'relay_state': 0
            },
            {   # 设备三
                'device_id': 3,
                'water_tank_state': 0,  # 水箱状态: 0=正常, 1=缺水
            }
        ]
    
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
        
        self.label_clock.setText(time_str)
        self.label_clock.adjustSize() # 自动调整标签大小以适应内容               
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
                self.image_width = 1920  # 3840，1920
                self.image_height = 1080  # 2160，1080
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
    def init_label(self, label, initial_value, color="white"):
        # 设置文字内容
        label.setText(str(initial_value))
        
        # 设置文字样式
        label.setFont(QFont("SimHei", 30, QFont.Bold))  # 字体、大小、加粗
        label.setStyleSheet(f"color: {color};")  # 文字颜色   
        
        # 设置文字对齐方式
        label.setAlignment(Qt.AlignCenter)        
        # 确保文字显示在背景上方
        label.raise_()    
    
    def init_all_labels(self):
        """初始化所有需要的标签"""
        # 假设UI文件中有这些标签：label_hum(湿度), label_tmp(温度), label_pres(气压)
        self.init_label(self.label_tmp, "88.8℃")  # 温度初始值
        self.init_label(self.label_hum, "88.8%")   # 湿度初始值       
        self.init_label(self.label_ph1, "88.8")  # ph1初始值
        self.init_label(self.label_ele, "88.8")  # 电导率初始值

        self.init_label(self.label_tmp_2, "88.8℃")  # 温度初始值
        self.init_label(self.label_hum_2, "88.8%")   # 湿度初始值       
        self.init_label(self.label_ph1_2, "88.8")  # ph1初始值
        self.init_label(self.label_ele_2, "88.8")  # 电导率初始值
                
        # 为标签设置不同的字体颜色
        self.init_label(self.label_on, "自动模式", "gray")  # 设置为灰色，表示手动模式
        self.init_label(self.label_water, "水位正常", "cyan")  # 设置为绿色
        # 在label_auto中加载图片
        
        
        # 默认显示label_auto并设置为手动模式
        
        
    def Load_pic(self,label,image_path):
        try:
            pixmap = QPixmap(image_path)
            label.setPixmap(pixmap.scaled(
                label.size(), 
                Qt.KeepAspectRatio, 
                Qt.SmoothTransformation
            ))
            label.raise_()
        except Exception as e:
            print(f"加载图片到标签出错: {e}")
    def Load_pics(self):
        self.Load_pic(self.label_auto,DOWN_IMAGE)
        self.Load_pic(self.label_pl1,DOWN_IMAGE)
        self.Load_pic(self.label_pl2,DOWN_IMAGE)
        self.Load_pic(self.label_on1,OFF_IMAGE)
        self.Load_pic(self.label_on2,OFF_IMAGE)
               
    def init_time_display(self):
        """初始化时间显示"""
        # 设置标签样式
        self.label_clock.setFont(QFont("SimHei", 60, QFont.Bold))
        self.label_clock.setStyleSheet("color: cyan;")
        self.label_clock.setAlignment(Qt.AlignCenter)
        self.label_clock.raise_()
        
        # 初始化计时器，每秒更新一次时间
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)  # 1000毫秒 = 1秒
        
        # 立即更新一次时间
        self.update_time()        
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
        
        self.label_clock.setText(time_str)
        self.label_clock.adjustSize() # 自动调整标签大小以适应内容        
    
    def update_sensor_data(self, tmp=None, ele=None, ph1=None, tmp_2=None, ele_2=None, ph1_2=None, hum=None, hum_2=None, relay_state_1=None, relay_state_2=None):
        """更新传感器数据显示"""
        # 更新第一个区域的传感器数据
        print(f"更新传感器数据：tmp={tmp} ,hum={hum}, ph1={ph1}, ele={ele},  relay_state_1={relay_state_1},tmp_2={tmp_2}, ele_2={ele_2}, ph1_2={ph1_2}, hum_2={hum_2}, relay_state_2={relay_state_2}")
        if hum is not None:
            self.label_tmp.setText(f"{hum}℃")
            self.temp_gauge.setValue(hum)  # 更新温度仪表盘
        if tmp is not None:
            self.label_hum.setText(f"{tmp}%")
            self.hum_gauge.setValue(tmp)  # 更新湿度仪表盘
            # 自动模式下，根据湿度控制喷淋状态
            if mode_state:
                if tmp < 50:
                    # 切换label_pl1的图片为open
                    ## 打开1号淋系统
                    send_lora_command(0x04, 0x04, 0x05)
                    self.Load_pic(self.label_pl1,OPEN_IMAGE)
                    self.Load_pic(self.label_on1,ON_IMAGE)
                else:
                    # 自动模式下，否则切换回默认图片
                    ## 关闭1号淋系统
                    send_lora_command(0x04, 0x04, 0x06)
                    self.Load_pic(self.label_on1,OFF_IMAGE)
                    self.Load_pic(self.label_pl1,DOWN_IMAGE)
        # 根据继电器状态控制label_on1的图片
        if relay_state_1 is not None:
            if relay_state_1 == 1:
                self.Load_pic(self.label_on1,ON_IMAGE)
                self.Load_pic(self.label_pl1,OPEN_IMAGE)
                self.spray1_state = 1  # 1号喷淋系统打开
            else:
                self.Load_pic(self.label_on1,OFF_IMAGE)
                self.Load_pic(self.label_pl1,DOWN_IMAGE)
                self.spray1_state = 0  # 1号喷淋系统关闭
            
            # 保存1号设备的数据到CSV文件
        if tmp is not None or ph1 is not None or ele is not None:

                print(f"保存1号设备数据：tmp={tmp}, hum={hum}, ph1={ph1}, ele={ele}, relay_state_1={relay_state_1}")
                self.save_sensor_data(1, tmp, hum, ph1, ele, self.spray1_state)
        if ph1 is not None:
            self.label_ph1.setText(f"{ph1}")
            self.ph1_gauge.setValue(ph1)  # 更新pH值仪表盘
        if ele is not None:
            self.label_ele.setText(f"{ele}")
            self.ele_gauge.setValue(ele)  # 更新电导率仪表盘  
        # 更新第二个区域的传感器数据
        if hum_2 is not None:
            self.label_tmp_2.setText(f"{hum_2}℃")
            self.temp2_gauge.setValue(hum_2)  # 更新第二个区域温度仪表盘
        if tmp_2 is not None:
            self.label_hum_2.setText(f"{tmp_2}%")
            self.hum2_gauge.setValue(tmp_2)  # 更新第二个区域湿度仪表盘
            # 自动模式下，根据湿度控制喷淋状态
            if mode_state:
                if tmp_2 < 50:
                    # 切换label_pl2的图片为open
                    ## 打开2号淋系统
                    send_lora_command(0x04, 0x04, 0x07)
                    self.Load_pic(self.label_pl2,OPEN_IMAGE)
                    self.Load_pic(self.label_on2,ON_IMAGE)

                else:
                    # 自动模式下，否则切换回默认图片
                    ## 关闭2号淋系统
                    send_lora_command(0x04, 0x04, 0x08)
                    self.Load_pic(self.label_on2,OFF_IMAGE)
                    self.Load_pic(self.label_pl2,DOWN_IMAGE)
        # 根据继电器状态控制label_on2的图片
        if relay_state_2 is not None:
            if relay_state_2 == 1:
                self.Load_pic(self.label_on2,ON_IMAGE)
                self.Load_pic(self.label_pl2,OPEN_IMAGE)
                self.spray2_state = 1  # 2号喷淋系统打开
            else:
                self.Load_pic(self.label_on2,OFF_IMAGE)
                self.Load_pic(self.label_pl2,DOWN_IMAGE)
                self.spray2_state = 0  # 2号喷淋系统关闭
            
            # 保存2号设备的数据到CSV文件
            if tmp_2 is not None or ph1_2 is not None or ele_2 is not None:
                print(f"保存2号设备数据：tmp_2={tmp_2}, hum_2={hum_2}, ph1_2={ph1_2}, ele_2={ele_2}, relay_state_2={relay_state_2}")
                self.save_sensor_data(2, tmp_2, hum_2, ph1_2, ele_2, self.spray2_state)
        if ph1_2 is not None:
            self.label_ph1_2.setText(f"{ph1_2}")
            self.ph2_gauge.setValue(ph1_2)  # 更新第二个区域pH值仪表盘
        if ele_2 is not None:
            self.label_ele_2.setText(f"{ele_2}")
            self.ele2_gauge.setValue(ele_2)  # 更新第二个区域电导率仪表盘                    
    
    def create_data_folders(self):
        """创建用于保存数据的文件夹结构"""
        # 要创建的主文件夹
        main_folders = ["1号土壤数据", "2号土壤数据"]
        
        for folder in main_folders:
            # 创建主文件夹
            main_path = Path(folder)
            main_path.mkdir(exist_ok=True)
            
            # 获取当前年月
            current_date = datetime.now()
            year_month = current_date.strftime("%Y-%m")
            
            # 创建年月子文件夹
            year_month_path = main_path / year_month
            year_month_path.mkdir(exist_ok=True)
            
            # 生成每日CSV文件（如果不存在）
            day = current_date.strftime("%m%d")  # 格式如0917
            csv_file = year_month_path / f"{day}.csv"
            
            # 检查文件是否已存在，不存在则创建并写入表头
            if not csv_file.exists():
                with open(csv_file, mode='w', newline='', encoding='utf-8-sig') as file:
                    writer = csv.writer(file)
                    # Write header
                    writer.writerow(["Time", "Soil_Temperature(°C)", "Soil_Moisture(%)", "pH", "Conductivity(μS/cm)", "Spray_State(0/1)"])
    
    def save_sensor_data(self, device_id, temperature, moisture, ph, conductivity, spray_state):
        """Store sensor data by device ID"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据] 开始保存设备 {device_id} 的传感器数据...")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据] 数据内容: 温度={temperature}°C, 湿度={moisture}%, pH={ph}, 电导率={conductivity}μS/cm, 喷淋状态={spray_state}")
        
        # 主文件夹路径（树莓派路径）
        main_folder = "/home/pi/Desktop/SmartFamer"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据] 主文件夹: {main_folder}")
        
        # Get current date information
        current_date = datetime.now()
        year_month = current_date.strftime("%Y-%m")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据] 当前年月: {year_month}")
        
        # Build folder path: main_folder/DeviceID/year-month
        folder_path = Path(main_folder) / f"Device_{device_id}" / year_month
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据] 文件夹路径: {folder_path}")
        
        # Create folder if it doesn't exist
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据] 成功创建文件夹结构: {folder_path}")
        except PermissionError as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据-错误] 创建文件夹时权限错误: {e}")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据-错误] 权限信息: 当前用户={os.getlogin()}, 当前目录权限={os.access('.', os.W_OK)}")
            return
        except IOError as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据-错误] 创建文件夹时IO错误: {e}")
            return
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据-错误] 创建文件夹时发生未知错误: {e}")
            return
        
        # Create file by date
        file_name = f"{current_date.strftime('%Y-%m-%d')}.csv"
        csv_file = folder_path / file_name
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据] CSV文件路径: {csv_file}")
        
        # Get current time
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据] 当前时间: {current_time}")
        
        # Write data
        try:
            # Check if file exists, create and write header if not
            file_exists = csv_file.exists()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据] 文件是否存在: {file_exists}")
            
            with open(csv_file, mode='a', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                # If new file, write header
                if not file_exists:
                    writer.writerow(["Time", "Device_ID", "Temperature(°C)", "Moisture(%)", "PH", "Conductivity(μS/cm)", "Spray_State"])
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据] 成功写入文件头部")
                # Write data row
                writer.writerow([current_time, device_id, temperature, moisture, ph, conductivity, spray_state])
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据] 成功写入数据行")
        except PermissionError as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据-严重错误] 文件写入权限错误: {e}")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据-严重错误] 文件路径: {csv_file}")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据-严重错误] 父目录权限: {os.access(folder_path, os.W_OK)}")
        except IOError as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据-严重错误] 文件IO错误: {e}")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据-严重错误] 文件写入时发生未知错误: {e}")
            import traceback
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [保存数据-严重错误] 详细错误堆栈: {traceback.format_exc()}")

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        # 停止传感器数据串口接收线程
        if hasattr(self, 'serial_thread'):
            self.serial_thread.stop()
        
        # 停止语音识别数据串口接收线程
        if hasattr(self, 'voice_thread'):
            self.voice_thread.stop()

        # 接受关闭事件
        event.accept()
    
    def init_gauges(self):
        """初始化仪表盘"""
        # 为第一个区域的温度创建仪表盘
        # 创建渐变颜色列表（红到绿）
        temp_colors = [QColor(255, 0, 0), QColor(255, 255, 0), QColor(0, 255, 0)]
        # 创建温度仪表盘，范围0-100摄氏度
        self.temp_gauge = GaugeWidget(self, min_value=0.0, max_value=60.0, colors=temp_colors)
        # 设置仪表盘大小和位置
        self.temp_gauge.setGeometry(275, 775, 300, 300)
        # 设置仪表盘的值（示例值）
        self.temp_gauge.setValue(30)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.temp_gauge.raise_()

        # 为第二个区域的湿度创建仪表盘
        hum_colors = [QColor(255, 0, 0), QColor(255, 255, 0), QColor(0, 255, 0)]
        # 创建湿度仪表盘，范围0-100%
        self.hum_gauge = GaugeWidget(self, min_value=0.0, max_value=100.0, colors=hum_colors)
        # 设置仪表盘大小和位置
        self.hum_gauge.setGeometry(735, 775, 300, 300)
        # 设置仪表盘的值（示例值）
        self.hum_gauge.setValue(50)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.hum_gauge.raise_() 

        # 为第二个区域的湿度创建仪表盘
        ph1_colors = [QColor(255, 0, 0), QColor(255, 255, 0), QColor(0, 255, 0)]
        # 创建湿度仪表盘，范围0-100%
        self.ph1_gauge = GaugeWidget(self, min_value=0.0, max_value=14.0, colors=ph1_colors)
        # 设置仪表盘大小和位置
        self.ph1_gauge.setGeometry(1195, 775, 300, 300)
        # 设置仪表盘的值（示例值）
        self.ph1_gauge.setValue(7)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.ph1_gauge.raise_()

        # 为第二个区域的湿度创建仪表盘
        ele_colors = [QColor(255, 0, 0), QColor(255, 255, 0), QColor(0, 255, 0)]
        # 创建湿度仪表盘，范围0-100%
        self.ele_gauge = GaugeWidget(self, min_value=0.0, max_value=20000.0, colors=ele_colors)
        # 设置仪表盘大小和位置
        self.ele_gauge.setGeometry(1607, 755, 335, 335)
        # 设置仪表盘的总角度为280度
        self.ele_gauge.setTotalAngle(290)
        # 设置仪表盘的起始角度为180度（从底部开始）
        self.ele_gauge.setStartAngle(235)
        # 设置仪表盘的值（示例值）
        self.ele_gauge.setValue(10000)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.ele_gauge.raise_()
        """初始化仪表盘"""
        # 为第二个区域的温度创建仪表盘
        # 创建渐变颜色列表（红到绿）
        temp2_colors = [QColor(255, 0, 0), QColor(255, 255, 0), QColor(0, 255, 0)]
        # 创建温度仪表盘，范围0-100摄氏度
        self.temp2_gauge = GaugeWidget(self, min_value=0.0, max_value=60.0, colors=temp2_colors)
        # 设置仪表盘大小和位置
        self.temp2_gauge.setGeometry(275, 1365, 300, 300)
        # 设置仪表盘的值（示例值）
        self.temp2_gauge.setValue(30)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.temp2_gauge.raise_()

        # 为第二个区域的湿度创建仪表盘
        hum2_colors = [QColor(255, 0, 0), QColor(255, 255, 0), QColor(0, 255, 0)]
        # 创建湿度仪表盘，范围0-100%
        self.hum2_gauge = GaugeWidget(self, min_value=0.0, max_value=100.0, colors=hum2_colors)
        # 设置仪表盘大小和位置
        self.hum2_gauge.setGeometry(735, 1365, 300, 300) 
        # 设置仪表盘的值（示例值）
        self.hum2_gauge.setValue(50)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.hum2_gauge.raise_() 

        # 为第二个区域的湿度创建仪表盘
        ph2_colors = [QColor(255, 0, 0), QColor(255, 255, 0), QColor(0, 255, 0)]
        # 创建湿度仪表盘，范围0-100%
        self.ph2_gauge = GaugeWidget(self, min_value=0.0, max_value=14.0, colors=ph2_colors)
        # 设置仪表盘大小和位置
        self.ph2_gauge.setGeometry(1195, 1365, 300, 300)
        # 设置仪表盘的值（示例值）
        self.ph2_gauge.setValue(7)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.ph2_gauge.raise_()

        # 为第二个区域的湿度创建仪表盘
        ele2_colors = [QColor(255, 0, 0), QColor(255, 255, 0), QColor(0, 255, 0)]
        # 创建湿度仪表盘，范围0-100%
        self.ele2_gauge = GaugeWidget(self, min_value=0.0, max_value=20000.0, colors=ele2_colors)
        # 设置仪表盘大小和位置
        self.ele2_gauge.setGeometry(1607, 1345, 335, 335)
        # 设置仪表盘的总角度为280度
        self.ele2_gauge.setTotalAngle(290)
        # 设置仪表盘的起始角度为180度（从底部开始）
        self.ele2_gauge.setStartAngle(235)
        # 设置仪表盘的值（示例值）
        self.ele2_gauge.setValue(10000)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.ele2_gauge.raise_()            

    def init_inquiry_timer(self):
        """初始化问询定时器，每2秒发送一次问询帧"""
        self.inquiry_timer = QTimer(self)
        self.inquiry_timer.timeout.connect(self.send_inquiry)
        self.inquiry_timer.start(asktime)  # 5000毫秒 = 5秒
        print(f"问询定时器已启动，每{asktime/1000}秒发送一次问询帧")
    
    def send_inquiry(self):
        """发送问询帧到所有设备，使用非阻塞方式"""
        # 使用计数器跟踪当前要发送的设备ID
        self.current_device_index = 0
        # 启动设备发送定时器
        self.device_timer = QTimer(self)
        self.device_timer.timeout.connect(self.send_next_inquiry)
        self.device_timer.start(100)  # 立即开始发送第一个设备
    
    def send_next_inquiry(self):
        """发送下一个设备的问询帧"""
        # 检查是否还有设备需要发送
        global devices_data
        if self.current_device_index < len(devices_data):
            device_id = self.current_device_index + 1  # 设备ID从1开始
            send_inquiry_frame(device_id=device_id)
            print(f"发送问询帧到设备 {device_id}")
            # 增加索引
            self.current_device_index += 1
            # 设置下一次发送的延时为1秒
            self.device_timer.setInterval(asktime)
        else:
            # 所有设备都已发送，停止定时器
            self.device_timer.stop()
            print("完成所有设备问询帧发送")
        
    def update_display(self, data):
        """接收并处理SerialWorker发送的数据,同时从全局devices_data数组中获取完整数据进行显示"""
        # print(f"主线程设备数据数组: {data}")# 全局变量devices_data，用于存储所有设备数据
        print(f"数据数组: {devices_data}")
        
    
    def update_voice_display(self, device_id,node,command):
        """接收并处理SerialWorker发送的语音指令数据""" 
        global mode_state
        if device_id==1:
            print(f"打开全部喷淋")
            self.schedule_spray_off(1)  # 延迟5秒关闭一号喷淋系统图标
            self.schedule_spray_off(2)  # 延迟5秒关闭二号喷淋系统图标
            self.Load_pic(self.label_pl1,OPEN_IMAGE)
            self.Load_pic(self.label_pl2,OPEN_IMAGE)
            self.Load_pic(self.label_on1,ON_IMAGE)
            self.Load_pic(self.label_on2,ON_IMAGE)
            
        elif device_id==2:
            print(f"关闭全部喷淋")
             
            self.Load_pic(self.label_pl1,DOWN_IMAGE)
            self.Load_pic(self.label_pl2,DOWN_IMAGE)
            self.Load_pic(self.label_on1,OFF_IMAGE)
            self.Load_pic(self.label_on2,OFF_IMAGE)
        elif device_id==3:
            print(f"打开自动喷淋")
            mode_state=True
            self.Load_pic(self.label_auto,OPEN_IMAGE)
            self.init_label(self.label_on, "自动模式", "cyan") 
        elif device_id==4:
            print(f"关闭自动喷淋")
            mode_state=False
            self.Load_pic(self.label_auto,DOWN_IMAGE)
            self.init_label(self.label_on, "自动模式", "gray") 
        elif device_id==5:
            print(f"打开一号喷淋系统")
            self.Load_pic(self.label_pl1,OPEN_IMAGE)
            self.Load_pic(self.label_on1,ON_IMAGE)
            # 调用定时关闭函数，延迟5秒后关闭图标显示
            self.schedule_spray_off(1)  # 参数1表示一号喷淋系统
        elif device_id==6:
            print(f"关闭一号喷淋系统")
            self.Load_pic(self.label_pl1,DOWN_IMAGE)
            self.Load_pic(self.label_on1,OFF_IMAGE)
        elif device_id==7:
            print(f"打开二号喷淋系统")
            self.Load_pic(self.label_pl2,OPEN_IMAGE)
            self.Load_pic(self.label_on2,ON_IMAGE)
            # 调用定时关闭函数，延迟25秒后关闭图标显示
            self.schedule_spray_off(2)  # 参数2表示二号喷淋系统
        elif device_id==8:
            print(f"关闭二号喷淋系统")
            self.Load_pic(self.label_pl2,DOWN_IMAGE)
            self.Load_pic(self.label_on2,OFF_IMAGE)
        else:
            print(f"未知指令")
        
    def schedule_spray_off(self, spray_number, delay_ms=SPRAY_OFF_DELAY_MS):
        """通用定时关闭喷淋系统图标的函数
        
        Args:
            spray_number: 喷淋系统编号，1表示一号喷淋，2表示二号喷淋
            delay_ms: 延迟时间，单位毫秒，默认使用常量定义的延迟时间
        """
        def close_spray_icon():
            if spray_number == 1:
                print(f"[{time.strftime('%H:%M:%S')}] 定时关闭一号喷淋系统图标显示")
                self.Load_pic(self.label_pl1, DOWN_IMAGE)
                self.Load_pic(self.label_on1, OFF_IMAGE)
            elif spray_number == 2:
                print(f"[{time.strftime('%H:%M:%S')}] 定时关闭二号喷淋系统图标显示")
                self.Load_pic(self.label_pl2, DOWN_IMAGE)
                self.Load_pic(self.label_on2, OFF_IMAGE)
        
        # 设置定时器
        QTimer.singleShot(delay_ms, close_spray_icon)
        
    def update_lora_display(self, line):
        """接收并处理SerialWorker发送的传感器数据"""            
        # 空数据直接返回
        if not line:
            return
            
        # 清理数据：过滤掉控制字符和非ASCII字符
        # 使用正则表达式保留数字、小数点、逗号和负号
        import re
        cleaned_line = re.sub(r'[^\d.,-]', '', line)
        
        # 按逗号拆分数据
        data_parts = cleaned_line.split(',')
        
        # 判断数据是否为7个字段（土壤传感器数据格式）
        if len(data_parts) == 6:
            try:
                # 解析每个字段
                device_id = int(data_parts[0])    # 设备ID（区分机器）
                soil_moisture = float(data_parts[1])  # 土壤水分（%）
                soil_temp = float(data_parts[2])     # 土壤温度（℃）
                soil_ec = float(data_parts[3])       # 土壤电导率（μS/cm）
                soil_ph = float(data_parts[4])       # 土壤PH值
                relay_state = int(data_parts[5])     # 继电器状态

                # 处理传感器读取错误的情况（Arduino错误时返回-1）
                if soil_moisture < 0 or soil_temp < 0 or soil_ec < 0 or soil_ph < 0:
                    print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id} | 传感器读取错误")
                    print(f"  原始数据：{line}")
                    return  # 跳过错误数据

                # 打印接收到的数据
                print(f" 设备{device_id} 数据：{soil_moisture},{soil_temp},{soil_ec},{soil_ph},{relay_state}")
                
                # 更新设备数据列表
                for i, device in enumerate(devices_data):
                    # 检查设备是否已初始化，如果未初始化则创建新的设备字典
                    if device is None:
                        # 创建新的设备字典，使用当前检测到的设备ID
                        devices_data[i] = {'device_id': device_id, 'soil_moisture': 0, 'soil_temp': 0, 
                                          'soil_ec': 0, 'soil_ph': 0, 'relay_state': 0}
                        # 更新device变量以引用新创建的字典
                        device = devices_data[i]
                    
                    # 安全检查：确保device不为None再访问其属性
                    if device is not None and device['device_id'] == device_id:
                        device['soil_moisture'] = soil_moisture
                        device['soil_temp'] = soil_temp
                        device['soil_ec'] = soil_ec
                        device['soil_ph'] = soil_ph
                        device['relay_state'] = relay_state
                        break
                
                # 根据设备ID更新对应的传感器数据,并自动控制喷淋系统
                if device_id == 1:
                    # 更新第一个区域的传感器数据,并自动控制喷淋系统
                    self.update_sensor_data(
                        tmp=soil_temp, 
                        ele=soil_ec, 
                        ph1=soil_ph, 
                        hum=soil_moisture,
                        relay_state_1=relay_state
                    )
                    if mode_state:
                        if soil_moisture < SOIL_MOISTURE_THRESHOLD:
                            lora_ser.write(b"55 AA 04 04 05 FF\n")#55 AA 04 04 05 FF 打开1号喷淋系统
                        else:
                            lora_ser.write(b"55 AA 04 04 06 FF\n")#55 AA 04 04 04 FF 关闭1号喷淋系统
                elif device_id == 2:
                    # 更新第二个区域的传感器数据,并自动控制喷淋系统
                    self.update_sensor_data(
                        tmp_2=soil_temp, 
                        ele_2=soil_ec, 
                        ph1_2=soil_ph, 
                        hum_2=soil_moisture,
                        relay_state_2=relay_state
                    )
                    if mode_state:
                        if soil_moisture < SOIL_MOISTURE_THRESHOLD:
                            lora_ser.write(b"55 AA 04 04 07 FF\n")#55 AA 04 04 05 FF 打开2号喷淋系统
                        else:
                            lora_ser.write(b"55 AA 04 04 08 FF\n")#55 AA 04 04 04 FF 关闭2号喷淋系统
                    
                    
            except ValueError as e:
                print(f"[{time.strftime('%H:%M:%S')}] 数据格式错误（非数字）：{line}, 错误: {e}")
        # 判断数据是否为2个字段（水箱数据格式：设备码,水箱）
        elif len(data_parts) == 2:
            try:
                # 解析每个字段
                device_id = int(data_parts[0])    # 设备ID（水箱设备为3）
                 
                water_tank_state = int(data_parts[1])  # 水箱状态
                 
                if device_id == 3:
                    # 更新第二个区域的传感器数据
                    self.handle_water_tank_data(
                        device_id=device_id,
                        water_tank_state=water_tank_state,   
                    )
                # 打印接收到的数据
                print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id} {'低水位' if water_tank_state == 1 else '高水位'}")
                
                # 这里可以添加水箱数据的处理逻辑
                
            except ValueError as e:
                print(f"[{time.strftime('%H:%M:%S')}] 水箱数据格式错误（非数字）：{line}, 错误: {e}")
        else:
            print(f"[{time.strftime('%H:%M:%S')}] 未知数据格式，字段数: {len(data_parts)}，数据: {line}")
    def handle_water_tank_data(self, device_id, water_tank_state):
        """处理接收到的水箱数据"""
        # 检查是否暂停其他数据接收
        
        if device_id == 3:  # 确保是水箱设备
            # 更新devices_data数组中对应设备的数据
            device_found = False
            for i, device in enumerate(devices_data):
                if device is not None and device['device_id'] == device_id:
                    device['water_tank_state'] = water_tank_state
                    device_found = True
                    break
            
            # 如果未找到设备，初始化设备数据
            if not device_found:
                # 查找第一个None位置或设备ID为3的位置
                for i in range(len(devices_data)):
                    if devices_data[i] is None or (isinstance(devices_data[i], dict) and devices_data[i]['device_id'] == device_id):
                        devices_data[i] = {'device_id': device_id, 'water_tank_state': water_tank_state}
                        break
            
            # 水箱状态：1表示水位低，0表示水位正常
            # 水箱状态：1表示水位低，0表示水位正常
            if water_tank_state == 1:
                self.label_water.setText("缺水")
                self.label_water.setStyleSheet("color: red;")
                print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id} 水箱状态：缺水")
            else:
                self.label_water.setText("水位正常")
                self.label_water.setStyleSheet("color: cyan;")
                print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id} 水箱状态：正常")        

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
        serial_worker.data_received_lora.connect(main_window.update_lora_display)
        
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