from ast import Num
from math import e
from pickle import STOP
from platform import node
import sys
import os
from datetime import datetime, timezone, timedelta
from tkinter import OFF
from tracemalloc import stop
import turtle
import serial
import json
import time
import subprocess
import re
import asyncio
 
 
# from bs4 import BeautifulSoup
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QWidget
from PyQt5.QtGui import QPixmap, QFont, QPainter, QBrush, QConicalGradient, QPen, QColor
from PyQt5.QtCore import QThread, QObject, pyqtSignal, Qt, QTimer, QRectF
import PyQt5.uic as uic
from ybp import GaugeWidget
from blinker import Device, ButtonWidget, NumberWidget

device = Device("00032fd64076")##
hum2_threshold=50 ##浴室湿度阈值
msg = ""
light_status = 0
temp1=0
hum1=0
temp2=0
hum2=0
smoke=0
# 回调函数
light_num=0
async def general_message_handler(msg):
    """通用消息处理器 - 捕获所有消息"""
    print(f"[BLINKER消息] 收到数据: {msg}")
    # 可以在这里添加消息过滤逻辑
    if 'fromDevice' in msg:
        from_device = msg['fromDevice']
        print(f"来自设备: {from_device}")
        
        if 'data' in msg:
            for key, value in msg['data'].items():
                print(f"  数据项: {key} = {value}")
    
    # 这里可以添加具体的处理逻辑
    return msg  # 返回消息供其他处理使用


### 语音输入串口参数
VOICE_PORT = '/dev/ttyAMA4'    # 连接语音模块的串口
VOICE_BAUD_RATE = 9600  # 语音模块的波特率
VOICE_TIMEOUT  = 1 

LORA_PORT = '/dev/ttyAMA0'      # 连接LoRa模块的串口
LORA_BAUD_RATE = 115200  # LoRa模块的波特率

LORA_TIMEOUT  = 1 

DISPLAY_MODE4K=False ##是否显示4K图片

auto_fan=False ##是否自动排风
auto_door=False ##是否自动门禁
blink_door=False ##是否闪烁门
blink_hood=False ##是否闪烁 Hood
blink_fan=False ##是否闪烁 排风
blink_window=False ##是否闪烁 窗户
blink_curtain=False ##是否闪烁 窗帘


##图片路径
IMG_PATH = r"/home/pi/aihome/PIC"
BACKGROUND_IMAGE = os.path.join(IMG_PATH, "background.png")
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
WIFI_ON_IMAGE = os.path.join(IMG_PATH, "wifi_on.png")
WIFI_OFF_IMAGE = os.path.join(IMG_PATH, "wifi_off.png")

# --- 全局串口对象 ---
# 在程序启动时初始化，供全局调用
voice_ser = None  # 语音输入串口实例
lora_ser = None     # LoRa串口实例
send_lora_Times=3 # 发送LoRa指令的次数，默认3次
is_sending = False  # 全局变量，用于标识当前是否正在发送数据

# 问询设备ID数组（可自定义）
# 用户可以在这里自定义需要问询的设备ID，不需要按序排列
inquiry_device_ids = [2,3,4]  # 示例：只问询ID为1,3,5,7,9的设备
asktime=10000  # get设备数据的时间间隔，默认3秒
devices_asktime=asktime*(len(inquiry_device_ids)+1)  # 每轮设备询问的时间间隔，默认4秒
xiaozhi_asktime=20000  # 小智询问的时间间隔，默认3秒
internet_asktime=3000  # 互联网询问的时间间隔，默认60秒
temp=["",""]

# 网络连接状态全局变量
network_connected = False  # 网络连接状态标志
network_stable = False  # 网络稳定状态标志
network_check_count = 0  # 网络检查计数
NETWORK_STABLE_THRESHOLD = 3  # 网络稳定阈值，连续3次检查成功认为网络稳定
def get_current_connected_wifi():
    """获取当前已连接的WiFi账号（SSID）和密码"""
    # 1. 获取当前连接的SSID
    try:
        # 执行iwgetid命令，获取当前连接的SSID
        result = subprocess.check_output(
            ["iwgetid", "-r"],  # -r参数直接返回SSID
            stderr=subprocess.STDOUT,
            text=True
        ).strip()
        
        if not result:
            print("未检测到当前连接的WiFi")
            return None
        
        current_ssid = result
        print(f"当前连接的WiFi账号（SSID）: {current_ssid}")
        
    except subprocess.CalledProcessError:
        print("执行命令失败，可能未连接WiFi或无权限")
        return None
    except Exception as e:
        print(f"获取SSID时出错：{str(e)}")
        return None

    # 2. 从配置文件中匹配该SSID的密码
    wifi_config_path = "/etc/wpa_supplicant/wpa_supplicant.conf"
    try:
        with open(wifi_config_path, 'r') as f:
            lines = f.readlines()
            
            current_psk = None
            in_target_network = False  # 标记是否在当前SSID对应的配置块中
            
            for line in lines:
                line = line.strip()
                # 找到当前SSID对应的配置块
                if line.startswith('network='):
                    in_target_network = False  # 重置标记，进入新配置块
                # 检查当前配置块的SSID是否匹配
                elif line.startswith('ssid='):
                    ssid = line.split('=', 1)[1].strip('"')
                    if ssid == current_ssid:
                        in_target_network = True  # 匹配到当前SSID，开始找密码
                # 在匹配的配置块中提取密码
                elif in_target_network and line.startswith('psk='):
                    current_psk = line.split('=', 1)[1].strip('"')
                    break  # 找到密码后退出循环
            
            if current_psk:
                print(f"当前连接的WiFi密码: {current_psk}")
                return  current_ssid,current_psk
                     
                
            else:
                print(f"未在配置文件中找到 {current_ssid} 的密码（可能配置文件被修改过）")
                return None
                
    except FileNotFoundError:
        print(f"错误：未找到配置文件 {wifi_config_path}")
        return None
    except PermissionError:
        print(f"错误：权限不足，请使用 sudo 运行脚本")
        return None
    except Exception as e:
        print(f"读取配置文件时出错：{str(e)}")
        return None

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
        header1 = 0x55  # 固定的帧头
        header2 = 0xAA  # 固定的帧头
        # 计算位
        checksum =0xFF
        # 将所有部分打包成一个bytes对象
        command = bytes([header1, header2, device_id, node_id, action, checksum])
        print(f"发送指令: {command}")
        # 为了提高无线通信的可靠性，同一指令连续发送3次
        if(device_id==0x01 and node_id<=0x13 and node_id>=0x0F) or (device_id==0x02 and node_id<=0x08 and node_id>=0x01) or (device_id==0x03 and node_id>=0x01 and node_id<=0x02) or (device_id==0x04 and node_id>=0x01 and node_id<=0x02):
            send_lora_Times=2        
        else:
            send_lora_Times=3
        print(f"发送次数: {send_lora_Times}")
        for attempt in range(send_lora_Times):
            lora_ser.write(command)
            # 为了方便调试，将发送的字节指令以十六进制格式打印出来
            hex_string = ' '.join(f'{b:02x}' for b in command)
            print(f"-> LoRa发送 (第{attempt+1}次): {hex_string}")
            time.sleep(0.6)  # 每次发送后短暂延时
        
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
        inquiry_frame = bytes([0xFE, device_id, 0xFF])
        
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
        data_received = pyqtSignal(str)   # 发送设备数据给主线程
        data_voice_data = pyqtSignal(int,int,int)  # 发送语音指令数据给主线程
        data_json = pyqtSignal(float,float,float,float,float,int,int,str)  # 发送JSON数据给主线程
    
        def handle_json_data(self,data):
            """
            处理从run方法传递来的完整JSON数据
            现在data已经是一个完整的JSON字符串，不需要再次收集
            """
            # print(f"[JSON] 进入handle_json_data，接收到数据: {data}")
            
            # 确保data是字符串类型
            if isinstance(data, bytes):
                data = data.decode('utf-8', errors='ignore')
            
            # 验证数据是否为有效的JSON格式（包含开始和结束括号）
            if '{' in data and '}' in data:

                self._process_json_data(data)
            else:
                print(f"[JSON] 警告: 接收到的数据不是有效的JSON格式: {data}")
        def _process_json_data(self, json_buffer):
            """
            处理完整的JSON数据，重置状态并解析数据
            """
            global temp1,hum1,temp2,hum2,auto_fan
            # print(f"[JSON] 处理JSON数据: {json_buffer}")
            # 解析JSON数据
            try:
                json_data = json.loads(json_buffer)
                living_tmp=json_data.get("l_tmp")
                living_hum=json_data.get("l_hum")
                ba_tmp=json_data.get("b_tmp")
                ba_hum=json_data.get("b_hum")
                smoke=json_data.get("smoke")
                door_status=json_data.get("door_status")
                hood_status=json_data.get("hood_status")
                MP3_Name=json_data.get("MP3_Name")
                
                # 检查是否有烟雾数据
                smoke_changed = False
                if smoke is None:
                    # print("[JSON] 警告: JSON数据中缺少烟雾数据，使用缓存数据")
                    new_smoke = self.cached_smoke
                else:
                    new_smoke = float(smoke)
                    if abs(new_smoke - self.cached_smoke) > 0.01:
                        smoke_changed = True
                        self.cached_smoke = new_smoke
                smoke = new_smoke
                    
                if door_status is None:
                    # print("[JSON] 警告: JSON数据中缺少门状态数据，使用缓存数据")
                    door_status = self.cached_door_status
                else:
                    self.cached_door_status = int(door_status)
                    
                if living_tmp is None:
                    # print("[JSON] 警告: JSON数据中缺少温湿度数据，使用缓存数据")
                    living_tmp = self.cached_living_tmp
                    living_hum = self.cached_living_hum
                    ba_tmp = self.cached_ba_tmp
                    ba_hum = self.cached_ba_hum
                    
                else:
                    self.cached_living_tmp = float(living_tmp)
                    self.cached_living_hum = float(living_hum)
                    self.cached_ba_tmp = float(ba_tmp)
                    self.cached_ba_hum = float(ba_hum)
                    
                if hood_status is None:
                    print("[JSON] 警告: JSON数据中缺少油烟机状态数据，使用缓存数据")
                    hood_status = self.cached_hood_status
                else:
                    self.cached_hood_status = int(hood_status)
                    
                # 检查MP3状态数据
                mp3_changed = False
                if MP3_Name is None:
                    print("[JSON] 警告: JSON数据中缺少MP3状态数据，使用缓存数据")
                    new_mp3 = self.cached_MP3_name_status
                else:
                    new_mp3 = str(MP3_Name)
                    if new_mp3 != self.cached_MP3_name_status:
                        mp3_changed = True
                        self.cached_MP3_name_status = new_mp3
                MP3_Name = new_mp3
                
                
                temp1=living_tmp
                hum1=living_hum
                temp2=ba_tmp
                hum2=ba_hum

                if auto_fan:
                    if hum2>hum2_threshold:
                        send_lora_command(0x02, 0x0F, 0x00)
                        self.Load_pic(self.bathroom_fan_label, ON_IMAGE)
                        print("浴室风扇已开启")
                    else:
                        send_lora_command(0x02, 0x11, 0x00)
                        self.Load_pic(self.bathroom_fan_label, OFF_IMAGE)
                        print("浴室风扇已关闭")
                
                # print(f"[JSON] 解析JSON数据: 客厅温度: {living_tmp}, 客厅湿度: {living_hum}, 浴室温度: {ba_tmp}, 浴室湿度: {ba_hum}")
                self.data_json.emit(float(living_tmp), float(living_hum), float(ba_tmp), float(ba_hum), float(smoke),int(door_status),int(hood_status),str(MP3_Name))
 
                # 如果MP3或烟雾数据有变化，发送到Arduino
                if smoke_changed or mp3_changed:
                    data_to_send = {
                        "MP3_Name": MP3_Name,
                        "smoke": smoke
                    }
                    json_message = json.dumps(data_to_send)
                    self.send_data(json_message.encode('utf-8'))
                    print(f"[LoRa] 已发送更新的MP3和烟雾数据: {json_message}")
            except json.JSONDecodeError as e:
                print(f"[JSON] 解析JSON数据失败: {e}，使用缓存数据")
                
            except Exception as e:
                print(f"[JSON] 处理JSON数据时发生未知错误: {e}，使用缓存数据")
                 
            # 清空缓冲区
            self.json_buffer = ""
        
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
                
                # 检查是否符合指令格式 (55 01 01 00 FF)
                # 指令格式: [帧头1, 设备ID, 指令1, 指令2, 校验和]
                if len(hex_bytes) >= 5 and hex_bytes[0] == 0x55:
                    device_id = hex_bytes[2] if len(hex_bytes) > 2 else 0
                    node = hex_bytes[3] if len(hex_bytes) > 3 else 0
                    command =0
                    print("[处理] 有效语音指令帧")
                    send_lora_command(device_id,node,command)##转发lora指令
                    self.data_voice_data.emit(device_id,node,command)
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
            # 初始化数据缓存变量，保存最后一次成功的温湿度数据
            self.cached_living_tmp = 25.0  # 默认客厅温度
            self.cached_living_hum = 50.0  # 默认客厅湿度
            self.cached_ba_tmp = 26.0      # 默认浴室温度
            self.cached_ba_hum = 55.0      # 默认浴室湿度
            self.cached_smoke = 0.0        # 默认烟雾值
            self.cached_door_status = 0    # 默认门状态（0关闭，1打开）
            self.cached_hood_status = 0    # 默认油烟机状态（0关闭，1打开）
            self.cached_MP3_name_status = 0    # 默认MP3状态（0关闭，1打开）
            self.last_update_time = time.time()  # 最后更新时间
        def stop(self):
            """设置停止标志位"""
            self._is_running = False
            print("已向后台线程发送停止信号...")
            
        def send_data(self, data):
            """通过LoRa串口发送数据
            
            Args:
                data: 要发送的数据（字节类型）
            """
            global lora_ser, is_sending
            while is_sending:
                print("[信息] 当前有数据正在发送，等待发送完成...")
                time.sleep(0.1)
            
            # 设置发送状态为正在发送
            is_sending = True
            try:
                if lora_ser and lora_ser.is_open and  is_sending:
                    is_sending = False
                    
                    for attempt in range(3):
                        lora_ser.write(data)
                        # 为了方便调试，将发送的字节指令以十六进制格式打印出来
                        hex_string = ' '.join(f'{b:02x}' for b in data)
                        print(f"-> LoRa发送 (第{attempt+1}次): {hex_string}")
                        time.sleep(1)  # 每次发送后短暂延时
                    
                    lora_ser.flush()
                    print(f"[发送] 已通过线程发送数据: {data.decode('utf-8', errors='ignore').strip()}")
                else:
                    print("[发送] LoRa串口未打开，无法发送数据")
            except Exception as e:
                
                print(f"[发送] 发送数据时发生错误: {str(e)}")
            finally:
                # 发送完成后，重置发送状态
                is_sending = False
           
        def run(self):
            """在后台线程中打开串口"""
            print("后台串口监听线程已启动。")
            while self._is_running:
                try:
                    ##监听语言识别的串口
                    if voice_ser and voice_ser.is_open:
                        # 直接读取原始字节数据，不进行UTF-8解码
                        raw_data = voice_ser.read(6)
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
                        # 初始化接收缓冲区（如果不存在）
                        if not hasattr(self, 'json_buffer'):
                            self.json_buffer = b''
                            self.is_collecting_json = False
                        
                        # 初始化接收时间记录（如果不存在）
                        if not hasattr(self, 'json_start_time'):
                            self.json_start_time = time.time()
                        
                        # 读取更多字节数据，而不是只读1个字节
                        raw_data = lora_ser.readline(64)  # 一次读取最多64个字节
                        if raw_data:
                            # 遍历每个字节
                            for byte in raw_data:
                                if byte == ord('{'):
                                    # 开始接收JSON数据
                                    self.is_collecting_json = True
                                    self.json_buffer = b'{'
                                    self.json_start_time = time.time()
                                    
                                elif byte == ord('}') and self.is_collecting_json:
                                    # 只有在正在收集JSON数据时遇到}才处理
                                    self.json_buffer += b'}'
                                    # 处理完整的JSON字符串
                                    try:
                                        json_str = self.json_buffer.decode('utf-8', errors='ignore').strip()
                                         
                                        self.handle_json_data(json_str)
                                    except Exception as e:
                                        print(f"[JSON] 处理JSON数据时出错: {e}")
                                    # 重置缓冲区
                                    self.json_buffer = b''
                                    self.is_collecting_json = False
                                elif self.is_collecting_json:
                                    # 正在收集JSON数据中间部分（包括嵌套的大括号）
                                    self.json_buffer += bytes([byte])
                               
                                # 如果不在收集状态且遇到}，直接忽略
                except Exception as e:
                    print(f"[错误] 处理控制指令数据时发生异常: {e}")
                    # 发生错误时重置缓冲区状态
                    self.json_buffer = b''
                    self.is_collecting_json = False
                    time.sleep(0.1)     

class BlinkerWorker(QObject):
    """用于在后台线程中运行blinker设备，通过信号传递消息到主线程"""
    # 步骤1：定义传递Blinker消息的信号（参数为[device, command]列表）
    blinker_msg_signal = pyqtSignal(str,str)
    # 定义Blinker连接状态信号
    blinker_connected_signal = pyqtSignal(bool)
     
    def __init__(self):
        super().__init__()
        self._is_running = True
        self.blinker_loop = None
        self.blinker_temp1 = 0
        self.blinker_temp2 = 0
        self.blinker_hum1 = 0
        self.blinker_hum2 = 0
        self.blinker_smoke = 0
        
        # Blinker连接状态
        self.blinker_connected = False
        self.blinker_connection_attempts = 0
        self.max_connection_attempts = 10  # 最大连接尝试次数
        
        # 添加数据缓存，用于存储最新的传感器数据
        self.cached_living_tmp = 0
        self.cached_living_hum = 0
        self.cached_ba_tmp = 0
        self.cached_ba_hum = 0
        self.cached_smoke = 0
        
        # 添加设备状态缓存，用于存储设备开关状态
        self.device_states = {
            "led01": "off",      # 主机房间灯
            "led02": "off",      # 次卧灯光
            "led03": "off",      # 客厅灯光
            "fan01": "off",      # 厨房Hood
            "fan02": "off",      # 浴室风扇
            "wind01": "off",     # 客厅窗口
            "wind02": "off",     # 次卧窗帘
            "door": "off"        # 门
        }

    def tr_data(self,temp1,hum1,tmp2,hum2,smoke):
        self.blinker_temp1=temp1
        self.blinker_hum1=hum1
        self.blinker_temp2=tmp2
        self.blinker_hum2=hum2
        self.blinker_smoke=smoke
        
        # 更新缓存数据
        self.cached_living_tmp = temp1
        self.cached_living_hum = hum1
        self.cached_ba_tmp = tmp2
        self.cached_ba_hum = hum2
        self.cached_smoke = smoke
        
        print('传输室外参数')
        print(temp1,hum1,tmp2,hum2,smoke)
        
        # 立即发送数据更新到App
        self.send_data_to_app()

    def stop(self):
        """停止blinker设备"""
        self._is_running = False
        print("已向Blinker后台线程发送停止信号...")
 
        
    def send_data_to_app(self):
        """主动发送数据更新到App"""
        if hasattr(self, 'device') and self.device:
            try:
                # 使用异步方式发送数据
                if self.blinker_loop and not self.blinker_loop.is_closed():
                    async def send_data():
                        try:
                            # 为每个数据创建可调用的函数
                            def get_temp01():
                                return self.cached_living_tmp
                            def get_hum01():
                                return self.cached_living_hum
                            def get_temp02():
                                return self.cached_ba_tmp
                            def get_hum02():
                                return self.cached_ba_hum
                            
                            await self.device.sendRtData("temp01", get_temp01)
                            await self.device.sendRtData("hum01", get_hum01)
                            await self.device.sendRtData("temp02", get_temp02)
                            await self.device.sendRtData("hum02", get_hum02)
                            # 减少频繁的日志打印
                            # print(f"主动发送数据到App: 客厅温度{self.cached_living_tmp}°C, 客厅湿度{self.cached_living_hum}%, 浴室温度{self.cached_ba_tmp}°C, 浴室湿度{self.cached_ba_hum}%")
                        except Exception as e:
                            print(f"发送数据到App时出错: {e}")
                    
                    # 在Blinker事件循环中异步执行
                    asyncio.run_coroutine_threadsafe(send_data(), self.blinker_loop)
            except Exception as e:
                print(f"调用发送数据方法时出错: {e}")

    def update_device_state(self, control_key, state):
        """更新设备状态并发送到App"""
        if control_key in self.device_states:
            self.device_states[control_key] = state
            # 发送状态更新到App
            for key, value in self.device_states.items():
             print(f"设备状态: {key} -> {value}")     

    def run(self):
        """在后台线程中运行Blinker事件循环（不阻塞主线程）"""
        print("Blinker后台设备线程已启动。")
        try:
            # 创建独立事件循环供Blinker使用
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.blinker_loop = loop  # 存储引用，用于后续异步调用
            
            async def heartbeat_func(msg):
                """心跳函数，用于保持连接"""
                print("Heartbeat received msg: {0}".format(msg))
                
                # 心跳成功表示连接正常
                if not self.blinker_connected:
                    self.blinker_connected = True
                    self.blinker_connection_attempts = 0
                    print("✓ Blinker服务器连接成功！")
                    # 发送连接成功信号
                    self.blinker_connected_signal.emit(True)
                 
                await temp1_num.value(self.cached_living_tmp).update()
                await hum1_num.value(self.cached_living_hum).update()
                await temp2_num.value(self.cached_ba_tmp).update()
                await hum2_num.value(self.cached_ba_hum).update()
                await smoke_num.value(self.cached_smoke).update()
                print(f"缓存数据: 客厅温度{self.cached_living_tmp}°C, 客厅湿度{self.cached_living_hum}%, 浴室温度{self.cached_ba_tmp}°C, 浴室湿度{self.cached_ba_hum}%, 烟雾{self.cached_smoke}")
            
            # 创建设备实例，设置实时数据处理函数
            device = Device("f9094bf7c991", heartbeat_func=heartbeat_func)
            self.device = device  # 存储设备引用
            
            # 添加连接错误处理
            async def connection_error_handler():
                """处理连接错误"""
                if not self.blinker_connected:
                    self.blinker_connection_attempts += 1
                    if self.blinker_connection_attempts >= self.max_connection_attempts:
                        print("⚠️ Blinker服务器连接失败，已达到最大尝试次数")
                        self.blinker_connected_signal.emit(False)
                    else:
                        print(f"⏳ 尝试连接Blinker服务器... ({self.blinker_connection_attempts}/{self.max_connection_attempts})")
                        # 等待3秒后重试
                        await asyncio.sleep(3)
                        # 重新尝试连接
                        await device.run()
            led01_key = device.addWidget(ButtonWidget('led01'))  # 主卧开关
            led02_key = device.addWidget(ButtonWidget('led02'))  # 次卧开关
            led03_key = device.addWidget(ButtonWidget('led03'))  # 客厅开关
            led04_key = device.addWidget(ButtonWidget('led04'))  # 次卧开关
            led05_key = device.addWidget(ButtonWidget('led05'))  # 客厅开关
            fan01_key = device.addWidget(ButtonWidget('fan01'))  # 油烟机开关
            fan02_key = device.addWidget(ButtonWidget('fan02'))  # 客厅风扇开关
            wind01_key = device.addWidget(ButtonWidget('wind01'))  # 主卧窗帘开关
            wind02_key = device.addWidget(ButtonWidget('wind02'))  # 次卧窗帘开关
            wind03_key = device.addWidget(ButtonWidget('wind03'))  # 客厅窗帘开关
            door_key = device.addWidget(ButtonWidget('door'))  # 门开关
             
            light_change_key = device.addWidget(ButtonWidget('led10'))  # 灯光颜色
            
            desk_up_key = device.addWidget(ButtonWidget('desk01'))  #  desk_up
            desk_down_key = device.addWidget(ButtonWidget('desk02'))  #  desk_down
            desk_stop_key = device.addWidget(ButtonWidget('desk03'))  #  desk_stop
            mp3_start_key = device.addWidget(ButtonWidget('mp301'))  #  mp3_start
            mp3_stop_key = device.addWidget(ButtonWidget('mp302'))  #  mp3_stop
            mp3_play_key = device.addWidget(ButtonWidget('mp303'))  #  mp3_play
            mp3_pause_key = device.addWidget(ButtonWidget('mp304'))  #  mp3_pause
            mp3_prev_key = device.addWidget(ButtonWidget('mp310'))  #  mp3_prev
            mp3_next_key = device.addWidget(ButtonWidget('mp311'))  #  mp3_next
            mp3_volume_up_key = device.addWidget(ButtonWidget('jia'))  #  mp3_volume_up
            mp3_volume_down_key = device.addWidget(ButtonWidget('jian'))  #  mp3_volume_down


            temp1_num = device.addWidget(NumberWidget('temp01'))  # 室外温度
            hum1_num = device.addWidget(NumberWidget('hum01'))  # 室外湿度
            temp2_num = device.addWidget(NumberWidget('temp02'))  # 室外PM2.5
            hum2_num = device.addWidget(NumberWidget('hum02'))  # 室外紫外线
            smoke_num = device.addWidget(NumberWidget('smoke'))  # 室外风速

            async def led01_key_handler(msg):
                print(f"收到: {msg}")
                if msg['led01']=='on':    
                    self.blinker_msg_signal.emit("led01","on")
                    await led01_key.turn('on').color('#FF8C00').text('主卧灯光打开').update()
                elif msg['led01']=='off':    
                    self.blinker_msg_signal.emit("led01","off")
                    await led01_key.turn('off').color('#101010').text('主卧灯光已关闭').update()
            async def led02_key_handler(msg):
                if msg['led02']=='on':                
                    self.blinker_msg_signal.emit("led02","on")
                    await led02_key.turn('on').color('#FF8C00').text('次卧灯光打开').update()
                elif msg['led02']=='off':                    
                    self.blinker_msg_signal.emit("led02","off")
                    await led02_key.turn('off').color('#101010').text('次卧灯光已关闭').update()
            async def led03_key_handler(msg):
                if msg['led03']=='on':                
                    self.blinker_msg_signal.emit("led03","on")
                    await led03_key.turn('on').color('#FF8C00').text('客厅灯光打开').update()
                elif msg['led03']=='off':                    
                    self.blinker_msg_signal.emit("led03","off")
                    await led03_key.turn('off').color('#101010').text('客厅灯光已关闭').update()     
            async def led04_key_handler(msg):
                if msg['led04']=='on':                
                    self.blinker_msg_signal.emit("led04","on")
                    await led04_key.turn('on').color('#FF8C00').text('书房灯光打开').update()
                elif msg['led04']=='off':                    
                    self.blinker_msg_signal.emit("led04","off")
                    await led04_key.turn('off').color('#101010').text('书房灯光已关闭').update()
            async def led05_key_handler(msg):
                if msg['led05']=='on':                
                    self.blinker_msg_signal.emit("led05","on")
                    await led05_key.turn('on').color('#FF8C00').text('卫生间灯光打开').update()
                elif msg['led05']=='off':                    
                    self.blinker_msg_signal.emit("led05","off")
                    await led05_key.turn('off').color('#101010').text('卫生间灯光已关闭').update()
            async def fan01_key_handler(msg):
                if msg['fan01']=='on':                
                    self.blinker_msg_signal.emit("fan01","on")
                    await fan01_key.turn('on').color('#FF8C00').text('油烟机打开').update()
                elif msg['fan01']=='off':                    
                    self.blinker_msg_signal.emit("fan01","off")
                    await fan01_key.turn('off').color('#101010').text('油烟机已关闭').update()
                elif msg['fan01']=='pressup':                    
                    self.blinker_msg_signal.emit("fan01","auto")
                    await fan01_key.turn('auto').color('#FF8C00').text('自动油烟机').update()
            async def fan02_key_handler(msg):
                if msg['fan02']=='on':                
                    self.blinker_msg_signal.emit("fan02","on")
                    await fan02_key.turn('on').color('#FF8C00').text('排风扇打开').update()
                elif msg['fan02']=='off':                    
                    self.blinker_msg_signal.emit("fan02","off")
                    await fan02_key.turn('off').color('#101010').text('排风扇已关闭').update()
                elif msg['fan02']=='pressup':                    
                    self.blinker_msg_signal.emit("fan02","auto")
                    await fan02_key.turn('auto').color('#FF8C00').text('自动排风扇').update()
            async def wind01_key_handler(msg):
                if msg['wind01']=='on':                
                    self.blinker_msg_signal.emit("wind01","on")
                    await wind01_key.turn('on').color('#FF8C00').text('主卧窗帘打开').update()
                elif msg['wind01']=='off':                    
                    self.blinker_msg_signal.emit("wind01","off")
                    await wind01_key.turn('off').color('#101010').text('主卧窗帘已关闭').update()
                
            async def wind02_key_handler(msg):
                if msg['wind02']=='on':                
                    self.blinker_msg_signal.emit("wind02","on")
                    await wind02_key.turn('on').color('#FF8C00').text('次卧窗帘打开').update()
                elif msg['wind02']=='off':                    
                    self.blinker_msg_signal.emit("wind02","off")
                    await wind02_key.turn('off').color('#101010').text('次卧窗帘已关闭').update()
            async def wind03_key_handler(msg):
                if msg['wind03']=='on':             
                    self.blinker_msg_signal.emit("wind03","on")
                    await wind03_key.turn('on').color('#FF8C00').text('客厅窗户打开').update()
                elif msg['wind03']=='off':                    
                    self.blinker_msg_signal.emit("wind03","off")
                    await wind03_key.turn('off').color('#101010').text('客厅窗户已关闭').update()
            async def door_key_handler(msg):
                if msg['door']=='on':                
                    self.blinker_msg_signal.emit("door","on")
                    await door_key.turn('on').color('#FF8C00').text('门打开').update()
                elif msg['door']=='off':                    
                    self.blinker_msg_signal.emit("door","off")
                    await door_key.turn('off').color('#101010').text('门已关闭').update()
                elif msg['door']=='pressup':                    
                    self.blinker_msg_signal.emit("door","auto")
                    await door_key.turn('auto').color('#FF8C00').text('自动门').update()

            async def desk_up_key_handler(msg):
                if msg['desk01']=='tap':                
                    self.blinker_msg_signal.emit("desk01","tap")

            async def desk_down_key_handler(msg):
                if msg['desk02']=='tap':                
                    self.blinker_msg_signal.emit("desk02","tap")
            async def desk_stop_key_handler(msg):
                if msg['desk03']=='tap':                
                    self.blinker_msg_signal.emit("desk03","tap")
            async def mp3_start_key_handler(msg):
                if msg['mp301']=='tap':                
                    self.blinker_msg_signal.emit("mp301","tap")
            async def mp3_stop_key_handler(msg):
                if msg['mp302']=='tap':                
                    self.blinker_msg_signal.emit("mp302","tap")
            async def mp3_play_key_handler(msg):
                if msg['mp303']=='tap':                
                    self.blinker_msg_signal.emit("mp303","tap")
            async def mp3_pause_key_handler(msg):
                if msg['mp304']=='tap':                
                    self.blinker_msg_signal.emit("mp304","tap")

            async def mp3_prev_key_handler(msg):
                if msg['mp310']=='tap':                
                    self.blinker_msg_signal.emit("mp310","tap")

            async def mp3_next_key_handler(msg):
                if msg['mp311']=='tap':                
                    self.blinker_msg_signal.emit("mp311","tap")

            async def mp3_volume_up_key_handler(msg):
                if msg['jia']=='tap':                
                    self.blinker_msg_signal.emit("jia","tap")
            async def mp3_volume_down_key_handler(msg):
                if msg['jian']=='tap':                
                    self.blinker_msg_signal.emit("jian","tap")
            async def light_change_key_handler(msg):
                global light_num
                if msg['led10']=='tap' and light_num==0:                

                    self.blinker_msg_signal.emit("led10","breath")
                    await light_change_key.turn('tap').color('#FF8C00').text('呼吸灯').update()
                    light_num=1
                elif msg['led10']=='tap' and light_num==1:                      
                    self.blinker_msg_signal.emit("led10","water")
                    await light_change_key.turn('tap').color('#111111').text('流水灯').update()
                    light_num=2
                elif msg['led10']=='tap' and light_num==2:                
                    self.blinker_msg_signal.emit("led10","red")
                    await light_change_key.turn('tap').color('#FF0000').text('红').update()
                    light_num=3
                elif msg['led10']=='tap' and light_num==3:                
                    self.blinker_msg_signal.emit("led10","orange")
                    await light_change_key.turn('tap').color('#FFA500').text('橙').update()
                    light_num=4
                elif msg['led10']=='tap' and light_num==4:                
                    self.blinker_msg_signal.emit("led10","yellow")
                    await light_change_key.turn('tap').color('#FFFF00').text('黄').update()
                    light_num=5
                elif msg['led10']=='tap' and light_num==5:                
                    self.blinker_msg_signal.emit("led10","green")
                    await light_change_key.turn('tap').color('#00FF00').text('绿').update()
                    light_num=6
                elif msg['led10']=='tap' and light_num==6:                
                    self.blinker_msg_signal.emit("led10","blue")
                    await light_change_key.turn('tap').color('#0000FF').text('蓝').update()
                    light_num=7
                elif msg['led10']=='tap' and light_num==7:                
                    self.blinker_msg_signal.emit("led10","indigo")
                    await light_change_key.turn('tap').color('#4B0082').text('靛').update()
                    light_num=8
                elif msg['led10']=='tap' and light_num==8:                
                    self.blinker_msg_signal.emit("led10","violet")
                    await light_change_key.turn('tap').color('#9400D3').text('紫').update()
                    light_num=0
                elif msg['led10']=='pressup' :                
                    self.blinker_msg_signal.emit("led10","close")
                    await light_change_key.turn('tap').color('#101010').text('关闭全部灯').update()
                    light_num=0

            light_change_key.func = light_change_key_handler
            desk_up_key.func = desk_up_key_handler
            desk_down_key.func = desk_down_key_handler
            desk_stop_key.func = desk_stop_key_handler
            mp3_start_key.func = mp3_start_key_handler
            mp3_stop_key.func = mp3_stop_key_handler
            mp3_play_key.func = mp3_play_key_handler
            mp3_pause_key.func = mp3_pause_key_handler
            mp3_prev_key.func = mp3_prev_key_handler
            mp3_next_key.func = mp3_next_key_handler
            mp3_volume_up_key.func = mp3_volume_up_key_handler
            mp3_volume_down_key.func = mp3_volume_down_key_handler
            
            led01_key.func= led01_key_handler
            led02_key.func = led02_key_handler
            led03_key.func = led03_key_handler
            led04_key.func = led04_key_handler
            led05_key.func = led05_key_handler
            fan01_key.func = fan01_key_handler
            fan02_key.func = fan02_key_handler
            wind01_key.func = wind01_key_handler
            wind02_key.func = wind02_key_handler
            wind03_key.func = wind03_key_handler
            door_key.func = door_key_handler
            # 启动Blinker设备（WebSocket连接）
            self.blinker_loop.create_task(device.run())
            
            # 添加连接错误处理任务
            self.blinker_loop.create_task(connection_error_handler())
            
            # 运行事件循环
            self.blinker_loop.run_forever()
        except Exception as e:
            print(f"[严重错误] Blinker设备运行失败: {e}")
            # 发送连接失败信号
            self.blinker_connected_signal.emit(False)
        finally:
            if self.blinker_loop and not self.blinker_loop.is_closed():
                self.blinker_loop.close()
            print("Blinker后台设备线程已停止。")

##主线程窗口
class MainWindow(QMainWindow):
    ##初始化主线程窗口，处理和更新ui显示
    def __init__(self, blinker_worker=None):
        super().__init__()        
        uic.loadUi('main.ui', self)##加载UI文件
        self.blinker_worker = blinker_worker  # 存储blinker_worker引用
        
        # 初始化基础UI
        self.set_background_image()##设置背景图片        
        self.init_labels()##初始化标签
        self.init_gauges()##初始化仪表盘
        self.Load_pics()##加载所有图片
        
        # 立即进行一次网络检查
        print("正在检查网络连接...")
        self.check_internet_connection()
        
        # 等待网络稳定后再启动Blinker连接
        self.wait_for_network_stable()
        
        # 网络稳定后启动Blinker连接，并等待连接成功
        if network_stable:
            print("网络已稳定，开始连接Blinker服务器...")
            # 等待Blinker服务器连接成功后再启动其他功能
            self.wait_for_blinker_connection()
        else:
            # 如果网络不稳定，直接启动其他功能
            print("网络不稳定，直接启动其他功能")
            self.init_inquiry_timer()
        
        # 启动网络检查定时器
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.check_internet_connection)
        self.time_timer.start(internet_asktime)  # 3000毫秒 = 3秒
        
        self.showFullScreen()
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
    def check_internet_connection(self):
        """判断树莓派是否联上网络，并检查网络稳定性
        
        Returns:
            bool: True表示已联网，False表示未联网
        """
        global network_connected, network_stable, network_check_count, NETWORK_STABLE_THRESHOLD
        
        try:
            # 使用ping命令检查是否能连接到百度服务器
            # -c 1: 发送1个ping包
            # -W 1: 超时时间1秒
     
            # 根据操作系统使用不同的ping参数
            import platform
            if platform.system() == "Windows":
                # Windows参数: -n 1(1个包), -w 1000(1000毫秒超时)
                result = subprocess.run(
                    ["ping", "-n", "1", "-w", "1000", "www.baidu.com"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            else:
                # Linux/Unix参数: -c 1(1个包), -W 1(1秒超时)
                result = subprocess.run(
                    ["ping", "-c", "1", "-W", "1", "www.baidu.com"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            
            # 检查网络连接状态
            current_connected = (result.returncode == 0)
            
            # 更新UI显示
            if current_connected:
                self.Load_pic(self.wifi_status, WIFI_ON_IMAGE)
                print("✓ 网络连接正常")
            else:
                self.Load_pic(self.wifi_status, WIFI_OFF_IMAGE)
                print("✗ 网络连接失败")
            
            # 更新网络连接状态
            network_connected = current_connected
            
            # 检查网络稳定性
            if current_connected:
                network_check_count += 1
                if network_check_count >= NETWORK_STABLE_THRESHOLD:
                    if not network_stable:
                        network_stable = True
                        print(f"✓ 网络已稳定 (连续{network_check_count}次检查成功)")
            else:
                # 网络断开，重置计数和稳定状态
                network_check_count = 0
                network_stable = False
                print("✗ 网络不稳定，重置检查计数")
            
            return current_connected
             
        except Exception as e:
            print(f"检查网络连接时出错: {str(e)}")
            # 出错时认为网络连接失败
            network_connected = False
            network_stable = False
            network_check_count = 0
            self.Load_pic(self.wifi_status, WIFI_OFF_IMAGE)
            return False
    
    def wait_for_blinker_connection(self):
        """等待Blinker服务器连接成功后再继续执行程序"""
        
        print("等待Blinker服务器连接...")
        
        # 创建等待定时器
        wait_timer = QTimer(self)
        wait_timer.setSingleShot(False)  # 重复执行
        
        # 设置最大等待时间（5分钟）
        max_wait_time = 5 * 60 * 1000  # 5分钟，单位毫秒
        start_time = time.time() * 1000  # 当前时间，单位毫秒
        
        # Blinker连接状态
        self.blinker_connected = False
        
        def check_blinker_connection():
            nonlocal start_time
            current_time = time.time() * 1000
            
            # 检查是否超时
            if current_time - start_time > max_wait_time:
                print("⚠️ Blinker服务器连接等待超时，继续执行程序")
                wait_timer.stop()
                # 即使超时也继续执行程序
                self.init_inquiry_timer()
                return
            
            # 检查Blinker连接状态
            if self.blinker_worker and self.blinker_worker.blinker_connected:
                print("✓ Blinker服务器连接成功，继续执行程序")
                self.blinker_connected = True
                wait_timer.stop()
                # 连接成功后启动其他功能
                self.init_inquiry_timer()
            else:
                # 显示等待状态
                elapsed_seconds = int((current_time - start_time) / 1000)
                print(f"⏳ 等待Blinker服务器连接中... ({elapsed_seconds}秒)")
        
        # 连接定时器信号
        wait_timer.timeout.connect(check_blinker_connection)
        
        # 连接Blinker连接状态信号
        if self.blinker_worker:
            self.blinker_worker.blinker_connected_signal.connect(
                lambda connected: setattr(self, 'blinker_connected', connected)
            )
        
        # 立即开始第一次检查
        check_blinker_connection()
        
        # 设置检查间隔（3秒）
        wait_timer.start(3000)  # 3秒检查一次
    
    def wait_for_network_stable(self):
        """等待网络稳定后再继续执行程序"""
        global network_stable, network_connected
        
        print("等待网络稳定...")
        
        # 创建等待定时器
        wait_timer = QTimer(self)
        wait_timer.setSingleShot(False)  # 重复执行
        
        # 设置最大等待时间（5分钟）
        max_wait_time = 5 * 60 * 1000  # 5分钟，单位毫秒
        start_time = time.time() * 1000  # 当前时间，单位毫秒
        
        def check_network():
            nonlocal start_time
            current_time = time.time() * 1000
            
            # 检查是否超时
            if current_time - start_time > max_wait_time:
                print("⚠️ 网络等待超时，继续执行程序（网络可能不稳定）")
                wait_timer.stop()
                return
            
            # 执行网络检查
            self.check_internet_connection()
            
            # 检查网络是否稳定
            if network_stable:
                print("✓ 网络已稳定，继续执行程序")
                wait_timer.stop()
            else:
                # 显示等待状态
                elapsed_seconds = int((current_time - start_time) / 1000)
                print(f"⏳ 等待网络稳定中... ({elapsed_seconds}秒)")
        
        # 连接定时器信号
        wait_timer.timeout.connect(check_network)
        
        # 立即开始第一次检查
        check_network()
        
        # 设置检查间隔（3秒）
        wait_timer.start(3000)  # 3秒检查一次
       
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
        # 设置定时器间隔为5000毫秒（5秒），确保设备之间有足够的间隔
        self.device_timer.start(asktime)
    def send_next_inquiry(self):
        """发送下一个设备的问询帧"""
        # 检查是否还有设备需要发送
        if self.current_device_index < len(inquiry_device_ids):
            device_id = inquiry_device_ids[self.current_device_index]  # 从预定义的设备ID数组中获取
            send_inquiry_frame(device_id=device_id)
            # print(f"发送问询帧到设备 {device_id}")
            # 增加索引
            self.current_device_index += 1
        else:
            # 所有设备都已发送，停止设备定时器
            self.device_timer.stop()
            print("完成本轮设备问询")
            # 确保主问询定时器仍在运行，以便定期启动下一轮问询
            if not self.inquiry_timer.isActive():
                self.inquiry_timer.start(devices_asktime)
                print(f"重新启动主问询定时器，间隔{devices_asktime/1000}秒")       
    def init_label(self, label, initial_value, font=12, color="rgb(186,128,0)"):
        """初始化标签显示"""
        # 设置文字内容
        label.setText(str(initial_value))
        
        # 设置文字样式
        label.setFont(QFont("SimHei", font, QFont.Bold))  # 字体、大小、加粗
        label.setStyleSheet(f"color: {color};")  # 文字颜色   
        
        # 设置文字对齐方式
        label.setAlignment(Qt.AlignCenter)        
        # 确保文字显示在背景上方
        label.raise_()
    def init_labels(self):
        """初始化所有标签"""
        self.init_label(self.temp1_label, "88℃", font=10, color="black")
        self.init_label(self.hum1_label, "88.8%", font=10, color="black") 
        self.init_label(self.temp2_label, "88℃", font=10, color="black")
        self.init_label(self.hum2_label, "88.8%", font=10, color="black") 
        self.init_label(self.living_light_label, "关闭", font=12, color="black")
        self.init_label(self.kitchen_smoke_label, "8888", font=12, color="black")
        self.init_label(self.hostroom_curtain_label, "关闭", font=12, color="black")
        self.init_label(self.hostroom_light_label, "关闭", font=12, color="black")
        self.init_label(self.music_name_label, "001", font=12, color="black")
        self.init_label(self.secound_curtain_label, "关闭", font=12, color="black")
        self.init_label(self.secound_light_label, "关闭", font=12, color="black")
        self.init_label(self.study_desk_label, "正常", font=12, color="black")
        self.init_label(self.study_light_label, "关闭", font=12, color="black")
       
       # 初始化大门和灯光设备标签
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
        self.Load_pic(self.living_window_label, OFF_IMAGE)
        self.Load_pic(self.bathroom_fan_label, OFF_IMAGE)
        self.Load_pic(self.door_label, OFF_IMAGE)
        self.Load_pic(self.autodoor_label, AUTO_OFF_IMAGE)
        self.Load_pic(self.kitchen_hood_label, OFF_IMAGE)
        self.Load_pic(self.music_label, STOP_IMAGE)
        self.Load_pic(self.wifi_status, WIFI_OFF_IMAGE)
    def ask_xiaozhi_network(self):
        """问询小智是否联网，发送{"event":"ask"}"""
        
        try:
            # 构建问询JSON数据
            ask_data = {"event": "ask"}
            ask_json_str = json.dumps(ask_data) + '\n'
            
            # 确保定时器停止，避免重复发送
            if hasattr(self, 'xiaozhi_timer') and self.xiaozhi_timer is not None:
                self.xiaozhi_timer.stop()
          
            # 使用实例调用send_data方法
                
            lora_ser.write(ask_json_str.encode('utf-8'))
            print(f"发送问询帧到小智: {ask_json_str.strip()}")

            self.init_label(self.xiaozhi_status, "小智未连接", "gray")
            
            # 重新启动定时器，设置为1秒间隔
            if hasattr(self, 'xiaozhi_timer') and self.xiaozhi_timer is not None:
                self.xiaozhi_timer.start(xiaozhi_asktime)  # 1000毫秒 = 1秒

            

                
        except Exception as e:
            print(f"发送问询时出错: {str(e)}")   
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
                'x': 57,##59
                'y': 278,#248
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
                'x': 199,
                'y': 278,
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
                'x': 661,
                'y': 278,
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
                'x': 661+142,
                'y': 278,
                'gauge_width': big_gauge_width,
                'initial_value': 100
            }
           
        ]
        
        # 批量创建仪表盘
        for config in gauges_config:
            self.init_gauge(**config)
    def update_display(self, data):
        """接收并处理SerialWorker发送的数据,同时从全局device_data数组中获取完整数据进行显示"""

        print(f"数据数组: {device_data}")            
    def update_voice_display(self, device_id,node,command):
        """接收并处理SerialWorker发送的语音指令数据"""  
        global auto_fan,auto_door
        if device_id == 0x01:
            if node == 0x01:## 打开主卧灯光
                print("打开主卧灯光")
                self.init_label(self.hostroom_light_label, "开启", font=9, color="black")
            elif node == 0x02:## 关闭主卧灯光
                print("关闭主卧灯光")
                self.init_label(self.hostroom_light_label, "关闭", font=9, color="black")
            elif node == 0x03:## 打开次卧灯光
                print("打开次卧灯光")
                self.init_label(self.secound_light_label, "开启", font=9, color="black")
            elif node == 0x04:## 关闭次卧灯光
                print("关闭次卧灯光")
                self.init_label(self.secound_light_label, "关闭", font=9, color="black")
            elif node == 0x05:## 打开客厅灯光
                print("打开客厅灯光")
                self.init_label(self.living_light_label, "开启", font=9, color="black")
            elif node == 0x06:## 关闭客厅灯光
                print("关闭客厅灯光")
                self.init_label(self.living_light_label, "关闭", font=9, color="black")
             
             
            elif node == 0x09:## 打开书房灯光
                print("打开书房灯光")
                self.init_label(self.study_light_label, "开启", font=9, color="black")
            elif node == 0x0A:## 关闭书房灯光
                print("关闭书房灯光")
                self.init_label(self.study_light_label, "关闭", font=9, color="black")
             

            elif node == 0x0D:## 打开全部灯光
                print("打开全部灯光")
                self.init_label(self.hostroom_light_label, "开启", font=9, color="black")
                self.init_label(self.secound_light_label, "开启", font=9, color="black")
                self.init_label(self.living_light_label, "开启", font=9, color="black")
                self.init_label(self.study_light_label, "开启", font=9, color="black")
                
            elif node == 0x0E:## 关闭全部灯光
                print("关闭全部灯光")   
                self.init_label(self.hostroom_light_label, "关闭", font=9, color="black")
                self.init_label(self.secound_light_label, "关闭", font=9, color="black")
                self.init_label(self.living_light_label, "关闭", font=9, color="black")
                self.init_label(self.study_light_label, "关闭", font=9, color="black")
                 
             
            elif node == 0x0F:## 调节成暖色灯
                print("调节成暖色灯")
            elif node == 0x11:## 调节成冷色灯   
                print("调节成冷色灯")            
            elif node == 0x12:## 亮度调高
                print("亮度调高")                
            elif node == 0x13:## 亮度调低
                print("亮度调低")                
            elif node == 0x14:## 呼吸灯
                print("呼吸灯")
            elif node == 0x15:## 流水灯
                print("流水灯")
            elif node == 0x16:## 红色
                print("红色")
            elif node == 0x17:## 橙色
                print("橙色")
            elif node == 0x18:## 黄色
                print("黄色")
            elif node == 0x19:## 绿色
                print("绿色")
            elif node == 0x1A:## 青色
                print("青色")
            elif node == 0x1B:## 蓝色
                print("蓝色")
            elif node == 0x1C:##紫色
                print("紫色")
        elif device_id == 0x02:
            if node == 0x01:## MP3播放
                print("MP3播放")
                self.init_label(self.music_name_label, "播放", font=9, color="black")
                self.Load_pic(self.music_label, PLAY_IMAGE)
            elif node == 0x02:## 暂停mp3
                print("暂停mp3")
                self.init_label(self.music_name_label, "暂停", font=9, color="black")
                self.Load_pic(self.music_label, STOP_IMAGE)
            elif node == 0x03:## 继续播放
                print("继续播放")
                self.init_label(self.music_name_label, "播放", font=9, color="black")
                self.Load_pic(self.music_label, PLAY_IMAGE)
            elif node == 0x04:## 停止播放
                print("停止播放")
                self.init_label(self.music_name_label, "停止", font=9, color="black")
                self.Load_pic(self.music_label, STOP_IMAGE)
            elif node == 0x05:## 播放下一首
                print("播放下一首")
                self.init_label(self.music_name_label, "播放下一首", font=9, color="black")
                self.Load_pic(self.music_label, PLAY_IMAGE)
                time.sleep(1)
                self.init_label(self.music_name_label, "播放", font=9, color="black")
            elif node == 0x06:## 播放上一首
                print("播放上一首")
                self.init_label(self.music_name_label, "播放上一首", font=9, color="black")
                self.Load_pic(self.music_label, PLAY_IMAGE)
                time.sleep(1)
                self.init_label(self.music_name_label, "播放", font=9, color="black")
            elif node == 0x07:## 音量调高
                print("音量调高")
            elif node == 0x08:## 音量调低
                print("音量调低")
            elif node == 0x09:## 最高音量
                print("最高音量")
            elif node == 0x0A:## 静音
                print("静音")
            elif node == 0x0B:## 中等音量
                print("中等音量")
            elif node == 0x0C:## 调高书桌
                print("调高书桌")
                self.init_label(self.study_desk_label, "升高", font=9, color="black")
                time.sleep(1)
                self.init_label(self.study_desk_label, "高", font=9, color="black")
            elif node == 0x0D:## 调低书桌
                print("调低书桌")
                self.init_label(self.study_desk_label, "降低", font=9, color="black")
                time.sleep(1)
                self.init_label(self.study_desk_label, "低", font=9, color="black")
            elif node == 0x0E:## 停止书桌
                print("停止书桌")   
                self.init_label(self.study_desk_label, "停止", font=9, color="black")
            elif node == 0x0F:## 打开排风
                print("打开排风")
                auto_fan=False
                self.Load_pic(self.bathroom_fan_label, ON_IMAGE)

            elif node == 0x11:## 关闭排风
                print("关闭排风")
                auto_fan=False
                self.Load_pic(self.bathroom_fan_label, OFF_IMAGE)
            elif node == 0x12:## 自动排风               
                print("自动排风")
                auto_fan=True
                 
            elif node == 0x12:##拉开次卧窗帘
                print("拉开次卧窗帘")
                self.Load_pic(self.secound_curtain_label, ON_IMAGE)
            elif node == 0x13:## 关闭次卧窗帘
                print("关闭次卧窗帘")
                self.Load_pic(self.secound_curtain_label, OFF_IMAGE)
        elif device_id == 0x03:
            if node == 0x01:## 打开主卧窗帘
                print("打开主卧窗帘")
                self.Load_pic(self.hostroom_light_label, ON_IMAGE)
            elif node == 0x02:## 关闭主卧窗帘
                print("关闭主卧窗帘")
                self.Load_pic(self.hostroom_light_label, OFF_IMAGE)
            elif node == 0x03:## 打开门
                print("打开门")
                auto_door=False
                self.Load_pic(self.door_label, ON_IMAGE)
                self.Load_pic(self.autodoor_label, OFF_IMAGE)
            elif node == 0x04:## 关闭门
                print("关闭门")
                auto_door=False
                self.Load_pic(self.door_label, OFF_IMAGE)
                self.Load_pic(self.autodoor_label, OFF_IMAGE)
            elif node == 0x05:## 自动门禁
                auto_door=True
                print("自动门禁")
                self.Load_pic(self.autodoor_label, ON_IMAGE)
            elif node == 0x06:## 打开油烟机
                print("打开油烟机")
                self.Load_pic(self.kitchen_hood_label, ON_IMAGE)
            elif node == 0x07:## 关闭油烟机
                print("关闭油烟机")
                self.Load_pic(self.kitchen_hood_label, OFF_IMAGE)
            elif node == 0x08:## 自动油烟机
                print("自动油烟机")
        elif device_id == 0x04:
            if node == 0x01:##打开窗户
                print("打开窗户")
                self.Load_pic(self.living_window_label, ON_IMAGE)
            elif node == 0x02:## 关闭窗户
                print("关闭窗户")
                self.Load_pic(self.living_window_label, OFF_IMAGE)
            
         
        # print(f"主线程语音指令数据: 设备ID: 0x{device_id:02X}, 节点: 0x{node:02X}, 指令: 0x{command:02X}")
    def update_xiaozhi_display(self,living_tmp,living_hum,ba_tmp,ba_hum,smoke,door_status,hood_status,MP3_Name):
        """接收并处理SerialWorker发送的JSON数据"""
        print(f"主线程JSON数据: 客厅温度: {living_tmp}, 客厅湿度: {living_hum}, 浴室温度: {ba_tmp}, 浴室湿度: {ba_hum}, 烟雾: {smoke}, 门状态: {door_status}, 油烟机状态: {hood_status}, MP3播放名字是: {MP3_Name}")
        if door_status == 0:
            self.Load_pic(self.door_label, OFF_IMAGE)
        else:
            self.Load_pic(self.door_label, ON_IMAGE)
        if hood_status == 0:
            self.Load_pic(self.kitchen_hood_label, OFF_IMAGE)
        else:
            self.Load_pic(self.kitchen_hood_label, ON_IMAGE)
        
        self.init_label(self.kitchen_smoke_label,f"{smoke}", font=9, color="black")
        self.init_label(self.temp1_label, f"{living_tmp}℃", font=7, color="black")
        self.init_label(self.hum1_label, f"{living_hum}%", font=7, color="black")
        self.init_label(self.temp2_label, f"{ba_tmp}℃", font=7, color="black")
        self.init_label(self.hum2_label, f"{ba_hum}%", font=7, color="black")
        self.init_label(self.music_name_label, f"{MP3_Name}", font=9, color="black")
        
        # 将传感器数据传递给BlinkerWorker，上传到App
        if hasattr(self, 'blinker_worker') and self.blinker_worker:
            try:
                self.blinker_worker.tr_data(living_tmp, living_hum, ba_tmp, ba_hum, smoke)
                print(f"已发送传感器数据到Blinker: 客厅温度{living_tmp}°C, 客厅湿度{living_hum}%, 浴室温度{ba_tmp}°C, 浴室湿度{ba_hum}%, 烟雾{smoke}")
            except Exception as e:
                print(f"发送传感器数据到Blinker时出错: {e}")
        
    def handle_blinker_message(self,control_key,command): 
        """接收并处理BlinkerWorker发送的消息"""
        print(f"主线程Blinker消息: {control_key},{command}")
        control_key = control_key
        command = command
        print(f"主线程Blinker消息:   控件: {control_key}, 指令: {command}")
        
        # 处理不同设备的按钮消息
        if control_key == "led01":           
            if command == "on":
                # 更新UI为打开状态                
                send_lora_command(0x01, 0x01, 0x00)
                self.init_label(self.hostroom_light_label, "开启", font=9, color="black")
                print("主机房间灯已开启")                    
            elif command == "off":
                    send_lora_command(0x01, 0x02, 0x00)
                    self.init_label(self.hostroom_light_label, "关闭", font=9, color="black")
                    print("主机房间灯已关闭")
        elif control_key == "led02":
            if command == "on":
                # 更新UI为打开状态                
                    send_lora_command(0x01, 0x03, 0x00)
                    self.init_label(self.secound_light_label, "开启", font=9, color="black")
                    print("次卧灯光已开启")                   
            elif command == "off":
                    send_lora_command(0x01, 0x04, 0x00)
                    self.init_label(self.secound_light_label, "关闭", font=9, color="black")
                    print("次卧灯光已关闭")
                    
        elif control_key == "led03":
            if command == "on":
                # 更新UI为打开状态
                    send_lora_command(0x01, 0x05, 0x00)
                    self.init_label(self.living_light_label, "开启", font=9, color="black")
                    print("客厅灯光已开启")
            elif command == "off":
                    send_lora_command(0x01, 0x06, 0x00)
                    self.init_label(self.living_light_label, "关闭", font=9, color="black")
                    print("客厅灯光已关闭")
        elif control_key == "led04":
            if command == "on":
                # 更新UI为打开状态
                    send_lora_command(0x01, 0x09, 0x00)
                    self.init_label(self.study_light_label, "开启", font=9, color="black")
                    print("书房灯光已开启")                   
            elif command == "off":
                    send_lora_command(0x01, 0x0A, 0x00)
                    self.init_label(self.study_light_label, "关闭", font=9, color="black")
                    print("书房灯光已关闭")
        elif control_key == "led05":
            if command == "on":
                # 更新UI为打开状态
                    send_lora_command(0x01, 0x0B, 0x00)
                   
                    print("卫生间灯光已开启")
            elif command == "off":
                    send_lora_command(0x01, 0x0C, 0x00)
                     
                    print("卫生间灯光已关闭")
                   
        elif control_key == "led10":           
            if command == "breath":  
                send_lora_command(0x01, 0x14, 0x00)                    
                print("开启呼吸灯") 
            elif command == "water":               
                  send_lora_command(0x01, 0x15, 0x00)                    
                  print("流水灯")
            elif command == "red":               
                  send_lora_command(0x01, 0x16, 0x00)                    
                  print("红色灯")
            elif command == "orange":               
                  send_lora_command(0x01, 0x17, 0x00)                    
                  print("橙色灯")
            elif command == "yellow":               
                  send_lora_command(0x01, 0x18, 0x00)                    
                  print("黄色灯")
            elif command == "green":               
                  send_lora_command(0x01, 0x19, 0x00)                    
                  print("绿色灯")
            elif command == "blue":               
                  send_lora_command(0x01, 0x1A, 0x00)                    
                  print("蓝色灯")
            elif command == "indigo":               
                  send_lora_command(0x01, 0x1B, 0x00)                    
                  print("靛蓝色灯")
            elif command == "violet":               
                  send_lora_command(0x01, 0x1C, 0x00)                    
                  print("紫色灯")
            elif command == "close":               
                  send_lora_command(0x01, 0x0E, 0x00)                    
                  print("关闭全部灯")
                                      
        elif control_key == "fan01":
            if command == "on":                 
                    send_lora_command(0x03, 0x06, 0x00)
                    self.Load_pic(self.kitchen_hood_label, ON_IMAGE)
                    print("厨房 Hood 已开启")
                   
            elif command == "off":
                   
                    send_lora_command(0x03, 0x07, 0x00)
                    self.Load_pic(self.kitchen_hood_label, OFF_IMAGE)
                    print("厨房 Hood 已关闭")
            elif command == "auto":
                    send_lora_command(0x03, 0x08, 0x00)
                    
                    print("厨房 Hood 已自动")
                   
        elif control_key == "fan02":
            global auto_fan
            if command == "on":
                    auto_fan=False
                    send_lora_command(0x02, 0x0F, 0x00)
                    self.Load_pic(self.bathroom_fan_label, ON_IMAGE)
                    print("浴室风扇已开启")
                    
            elif command == "off": 
                    auto_fan=False                 
                    send_lora_command(0x02, 0x11, 0x00)
                    self.Load_pic(self.bathroom_fan_label, OFF_IMAGE)
                    print("浴室风扇已关闭")    
            elif command == "auto":
                    send_lora_command(0x02, 0x12, 0x00)
                    auto_fan=True
                    print("浴室风扇已自动")
                    
        elif control_key == "wind01":
            if command == "on":
                    send_lora_command(0x03, 0x01, 0x00)
                    self.init_label(self.hostroom_curtain_label, "开启", font=9, color="black")
                    print("主卧窗帘已开启")
            elif command == "off":
                    send_lora_command(0x03, 0x02, 0x00)
                    self.init_label(self.hostroom_curtain_label, "关闭", font=9, color="black")
                    print("主卧窗帘已关闭")
                
        elif control_key == "wind02":
            if command == "on":
               
                    send_lora_command(0x02, 0x13, 0x00)
                    self.Load_pic(self.secound_curtain_label, ON_IMAGE)
                    print("次卧窗帘已开启")
                    
            elif command == "off":
                    send_lora_command(0x02, 0x14, 0x00)
                    self.Load_pic(self.secound_curtain_label, OFF_IMAGE)
                    print("次卧窗帘已关闭")

        elif control_key == "wind03":
            if command == "on":
                    send_lora_command(0x04, 0x01, 0x00)
                    self.Load_pic(self.living_window_label, ON_IMAGE)
                    print("客厅窗口已开启")
            elif command == "off":
                    send_lora_command(0x04, 0x02, 0x00)
                    self.Load_pic(self.living_window_label, OFF_IMAGE)
                    print("客厅窗口已关闭")
        elif control_key == "desk01":
            if command == "tap":
                 
                    send_lora_command(0x02, 0x0C, 0x00)
                    self.init_label(self.study_desk_label, "上升", font=9, color="black")
                    print("书桌已上升")
        elif control_key == "desk02":
            if command == "tap":
               
                send_lora_command(0x02, 0x0D, 0x00)
                self.init_label(self.study_desk_label, "下降", font=9, color="black")
                print("书桌已下降")
        elif control_key == "desk03":
            if command == "tap":
                    send_lora_command(0x02, 0x0E, 0x00)
                    self.init_label(self.study_desk_label, "停止", font=9, color="black")
                    print("书桌已停止")
        elif control_key == "door":
            if command == "on":
                    send_lora_command(0x03, 0x03, 0x00)
                    self.Load_pic(self.door_label, ON_IMAGE)
                    self.Load_pic(self.autodoor_label, AUTO_OFF_IMAGE)
                    print("门已开启")
            elif command == "off":
                    send_lora_command(0x03, 0x04, 0x00)
                    self.Load_pic(self.door_label, OFF_IMAGE)
                    self.Load_pic(self.autodoor_label, AUTO_OFF_IMAGE)
                    print("门已关闭")
            elif command == "auto":
                    send_lora_command(0x03, 0x05, 0x00)
                    self.Load_pic(self.autodoor_label, AUTO_ON_IMAGE)
                    print("门已自动")
                    
        elif control_key == "mp301":
            if command == "tap":
                if self.music_label.pixmap() != PLAY_IMAGE:
                    send_lora_command(0x02, 0x01, 0x00)
                    self.Load_pic(self.music_label, PLAY_IMAGE)
                    print("音乐已开启")
        elif control_key == "mp302":
            if command == "tap":
                if self.music_label.pixmap() != STOP_IMAGE:
                    send_lora_command(0x02, 0x02, 0x00)
                    self.Load_pic(self.music_label, STOP_IMAGE)
                    print("音乐已关闭")
        elif control_key == "mp303":
            if command == "tap":
                if self.music_label.pixmap() != PLAY_IMAGE:
                    send_lora_command(0x02, 0x03, 0x00)
                    self.Load_pic(self.music_label, PLAY_IMAGE)
                    print("继续播放")
        elif control_key == "mp304":
            if command == "tap":
                if self.music_label.pixmap() != STOP_IMAGE:
                    send_lora_command(0x02, 0x04, 0x00)
                    self.Load_pic(self.music_label, STOP_IMAGE)
                    print("暂停播放")
        elif control_key == "jia":
            if command == "tap":
                    send_lora_command(0x02, 0x07, 0x00)
                    print("加音量")
        elif control_key == "jian":
            if command == "tap":
                    send_lora_command(0x02, 0x08, 0x00)
                    print("减音量")
        elif control_key == "mp310":
            if command == "tap":
                    send_lora_command(0x02, 0x06, 0x00)
                    print("上一首")
        elif control_key == "mp311":
            if command == "tap":
                    send_lora_command(0x02, 0x05, 0x00)
                    print("下一首")
        
        
        
                
                    
                     
           

         
           

# ================== 主程序入口 ==================
def main():
    """主函数"""
  
    global voice_ser, lora_ser
    
    # 初始化变量，避免finally块中访问未定义变量
    serial_worker = None
    worker_thread = None
    blinker_worker = None
    blinker_thread = None
    
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
        
        # 4. 创建并启动BlinkerWorker线程
        blinker_worker = BlinkerWorker()
        blinker_thread = QThread()
        
        # 创建主窗口
        main_window = MainWindow(blinker_worker)
        
        # 将workers移动到线程中
        serial_worker.moveToThread(worker_thread)
        blinker_worker.moveToThread(blinker_thread)
        
        # 连接信号和槽
        worker_thread.started.connect(serial_worker.run)
        blinker_thread.started.connect(blinker_worker.run)
        
        # 连接SerialWorker的数据信号到MainWindow的显示槽
        serial_worker.data_received.connect(main_window.update_display)
        serial_worker.data_voice_data.connect(main_window.update_voice_display)
        serial_worker.data_json.connect(main_window.update_xiaozhi_display)
        blinker_worker.blinker_msg_signal.connect(main_window.handle_blinker_message)
         
        
        # 启动线程
        worker_thread.start()
        blinker_thread.start()
        
        main_window.show()
        print("串口监听和Blinker设备已启动，请按Ctrl+C停止程序...")       
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
        
        # 停止Blinker工作线程
        if blinker_worker is not None:
            try:
                blinker_worker.stop()
            except Exception as e:
                print(f"停止Blinker工作线程时出错: {e}")
        
        if blinker_thread is not None and blinker_thread.isRunning():
            try:
                blinker_thread.quit()
                blinker_thread.wait()
                print("Blinker后台线程已停止")
            except Exception as e:
                print(f"停止Blinker线程时出错: {e}")
        
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