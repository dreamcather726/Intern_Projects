from platform import node
import sys
import os
from datetime import datetime, timezone, timedelta
from tkinter import ON
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
import json


### 语音输入串口参数
VOICE_PORT = 'com23'    # 连接语音模块的串口 '/dev/ttyAMA4' 
VOICE_BAUD_RATE = 9600  # 语音模块的波特率
VOICE_TIMEOUT  = 1 

LORA_PORT = 'com16'      # 连接LoRa模块的串口  '/dev/ttyAMA0'  
LORA_BAUD_RATE = 115200  # LoRa模块的波特率https://github.com/dreamcather726/Intern_Projects

LORA_TIMEOUT  = 1 

DISPLAY_MODE4K=True ##是否显示4K图片
asktime=3000  # 询问设备数据的时间间隔，默认5秒
light_threshold=500  # 自动照明的阈值，默认500lux
auto_mode_flag=False  # 自动照明模式

##图片路径
IMG_PATH = r"PIC"
BACKGROUND_IMAGE = os.path.join(IMG_PATH, "background.jpg")
FAN_ON_IMAGE = os.path.join(IMG_PATH, "fan_on.png")
FAN_OFF_IMAGE = os.path.join(IMG_PATH, "fan_off.png")
LIGHT_MODE_ON = os.path.join(IMG_PATH, "light_mode_on.png")
LIGHT_MODE_OFF = os.path.join(IMG_PATH, "light_mode_off.png")
LIGHT_ON = os.path.join(IMG_PATH, "light_on.png")
LIGHT_OFF = os.path.join(IMG_PATH, "light_off.png")
ON_IMAGE = os.path.join(IMG_PATH, "on.png")
OFF_IMAGE = os.path.join(IMG_PATH, "off.png")
WIFI_ON_IMAGE = os.path.join(IMG_PATH, "wifi_on.png")
WIFI_OFF_IMAGE = os.path.join(IMG_PATH, "wifi_off.png")



# --- 全局串口对象 ---
# 在程序启动时初始化，供全局调用
voice_ser = None  # 语音输入串口实例
lora_ser = None     # LoRa串口实例
send_lora_Times=3 # 发送LoRa指令的次数，默认3次
is_sending = False  # 全局变量，用于标识当前是否正在发送数据

# 创建一个长度为8的数组，用于保存设备数据
device_data = [None] * 1  # 每个元素将存储一个设备的数据字典

# 设备号数组，定义需要依次发送问询帧的设备ID
DEVICE_IDS = [1,15]  # 可根据实际设备数量和ID进行调整


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
        header = 0xA0  # 固定的帧头
        # 计算位
        checksum =0xFF
        # 将所有部分打包成一个bytes对象
        command = bytes([header, device_id, node_id, action, checksum])
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

def send_inquiry_frame(device_id=0x0F):
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
        inquiry_frame = bytes([0xB0, device_id])
        
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
        data_received = pyqtSignal(float,float,int,int,float,float)   # 发送设备数据给主线程
        data_voice_data = pyqtSignal(int,int,int)  # 发送语音指令数据给主线程
        data_json = pyqtSignal(str,str)  # 发送JSON数据给主线程
        change_wifi = pyqtSignal(int)  # 发送WiFi信息给主线程
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
                print(f"[处理] 转换后的字节: {hex_bytes}")
                # 检查是否符合指令格式 (55 01 01 00 FF)
                # 指令格式: [帧头1, 设备ID, 指令1, 指令2, 校验和]
                if len(hex_bytes) >= 5 and hex_bytes[0] == 0xA0:
                    device_id = hex_bytes[1] if len(hex_bytes) > 2 else 0
                    node = hex_bytes[2] if len(hex_bytes) > 3 else 0
                    command = hex_bytes[3] if len(hex_bytes) > 4 else 0
                    send_lora_command(device_id,node,command)#发送指令
                    self.data_voice_data.emit(device_id,node,command)
                else:
                    print(f"[处理] 不是有效的语音指令帧格式")
                    #print(f"  接收到的字节: {['0x{:02X}'.format(b) for b in hex_bytes]}")
                    
            except Exception as e:
                print(f"[错误] 处理语音指令数据时发生异常: {e}")

        def handle_sensor_data(self, data):
            """
            处理从传感器串口接收到的数据，支持识别JSON格式数据
            当接收到{时，丢弃数字数据直到收到}，避免数据交叉污染
            """
            # 初始化JSON接收相关变量（如果不存在）
            if not hasattr(self, 'json_buffer'):
                self.json_buffer = ""
                self.is_collecting_json = False
            
            # 先将bytes数据解码为字符串（如果是bytes类型）
            if isinstance(data, bytes):
                data = data.decode('utf-8', errors='ignore')
            
            # 检查是否正在收集JSON数据
            if self.is_collecting_json:
                # 继续添加数据到缓冲区
                self.json_buffer += data
                # 检查是否收到结束标志
                if '}' in self.json_buffer:
                    # 找到结束标志的位置
                    end_pos = self.json_buffer.find('}')
                    # 截取完整的JSON数据
                    self.json_buffer = self.json_buffer[:end_pos + 1]
                    # 处理完整的JSON数据
                    # print(f"[JSON] 完整JSON数据: {self.json_buffer}")
                    self._process_json_data()
                return
            
            # 检查是否开始新的JSON数据
            if '{' in data:
                # 找到开始标志的位置
                start_pos = data.find('{')
                # 开始收集JSON数据
                self.json_buffer = data[start_pos:]
                self.is_collecting_json = True
                
                # 检查同一数据中是否同时包含结束标志
                if '}' in self.json_buffer:
                    end_pos = self.json_buffer.find('}')
                    self.json_buffer = self.json_buffer[:end_pos + 1]
                    # 只有收到完整的JSON数据才处理
                    print(f"[JSON] 完整JSON数据: {self.json_buffer}")
                    self._process_json_data()
                # 否则继续收集，直到收到结束标志
              #  print("[JSON] 已开始收集JSON数据，等待结束标志")
                return
                
            # 如果不包含JSON数据且不在收集JSON数据，处理传感器数据
            try:
                # 确保数据是字符串类型
                if isinstance(data, bytes):
                    data = data.decode('utf-8', errors='ignore')
                # 解析数据，提取温度、湿度、光照、CO2、uv、PM2.5、PM10
                # 移除可能的空格、换行符等非数字字符
                clean_data = data.strip().replace(' ', '')
                # 将逗号分隔的字符串转换为整数列表，添加错误处理
                sensor_values = []
                for x in clean_data.split(','):
                    try:
                        if x.strip():
                            sensor_values.append(int(x.strip()))
                    except ValueError:
                        print(f"[警告] 无法转换为整数: '{x}'")
                # 检查是否有7个有效值
                if len(sensor_values) == 7:
                    # 解析每个值
                    temperature = sensor_values[1]  # 温度转换为摄氏度
                    humidity = sensor_values[2]    # 湿度转换为%
                    light = sensor_values[4]             # 光照值
                    pm25 = sensor_values[3]             # PM2.5值 
                    uv = sensor_values[5]             # uv值
                    weather =  sensor_values[6]             # 天气值
                    print(f"温度: {temperature}, 湿度: {humidity}, 光照: {light} , PM2.5: {pm25}, uv: {uv}, 天气: {weather}")
                    
                    # 解析数据，将数据发送给主线程
                    self.data_received.emit(temperature, humidity, light, pm25, uv, weather)
                else:
                    print(f"[警告] 收到的数据格式不正确，预期7个传感器值，实际收到{len(sensor_values)}个: {sensor_values}")
            except ValueError as e:
                print(f"[错误] 解析传感器数据时发生异常: {e}")
                return
            except Exception as e:
                print(f"[错误] 处理传感器数据时发生异常: {e}")
                return
                
        def _process_json_data(self):
            """
            处理完整的JSON数据，重置状态并解析数据
            """
            # 重置收集状态
            self.is_collecting_json = False
            # print(f"[JSON] 接收到完整JSON数据: {self.json_buffer}")
            
            # 预处理JSON数据：过滤掉所有数字字符
            filtered_json_buffer = ''.join([char for char in self.json_buffer if not char.isdigit()])
            # print(f"[JSON] 预处理后的数据: {filtered_json_buffer}")
            
            # 解析JSON数据
            try:
                json_data = json.loads(filtered_json_buffer)
                role=json_data.get("role")
                content=json_data.get("content")
                
                # 检查是否有event字段，且值为wifi_get
                if json_data.get("event") == "wifi_get":
                    print("收到WiFi获取请求")
                    # 获取当前WiFi信息
                    ssid, password = get_current_connected_wifi()
                    print(f"当前连接的WiFi信息: SSID={ssid}, Password={password}")
                    # 构建WiFi信息JSON响应
                    wifi_response = {
                        "ssid": ssid ,
                        "password": password
                    }
                    
                    wifi_json_str = json.dumps(wifi_response) + '\n'
                    lora_ser.write(wifi_json_str.encode('utf-8'))
                    # 正确地发出信号，而不是尝试调用setText方法
                    self.change_wifi.emit(ssid)
                    print(f"发送WiFi信息: {wifi_json_str}")
                    return
                if json_data.get("event") == "wifi_set":                  
                    self.change_wifi.emit(1)
                    
                    return
                
                print(f"role: {role}, content: {content}")
                self.data_json.emit(role, content)
                # 处理JSON数据的逻辑可以在这里添加
            except json.JSONDecodeError as e:
                print(f"[JSON] 解析JSON数据失败: {e}")
            # 清空缓冲区
            self.json_buffer = ""
        
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
        def run(self):
            """在后台线程中打开串口"""
            print("后台串口监听线程已启动。")
            while self._is_running:
                try:
                    ##监听语言识别的串口
                    if voice_ser and voice_ser.is_open:
                        # 初始化接收缓冲区（如果不存在）
                        if not hasattr(self, 'voice_buffer'):
                            self.voice_buffer = bytearray()
                        
                        # 读取可用的字节
                        if voice_ser.in_waiting > 0:
                            # 读取所有可用字节
                            new_data = voice_ser.read(voice_ser.in_waiting)
                            # 将新数据添加到缓冲区
                            self.voice_buffer.extend(new_data)
                            #print(new_data)#
                            print(f"[原始数据] 接收到 {len(new_data)} 字节")
                            
                            # 检查缓冲区中是否包含帧尾（FF）
                            while b'\xFF' in self.voice_buffer:
                                # 找到第一个帧尾的位置
                                frame_end_pos = self.voice_buffer.find(b'\xFF') + 1
                                if frame_end_pos > 1:  # 确保至少有一个字节
                                    # 提取完整帧
                                    frame_data = self.voice_buffer[:frame_end_pos]
                                    # 从缓冲区移除已处理的帧
                                    self.voice_buffer = self.voice_buffer[frame_end_pos:]
                                    
                                    # 将完整帧数据转换为十六进制字符串格式
                                    hex_data = ' '.join(f'{b:02x}' for b in frame_data)
                                    print(f"<- 串口接收 (完整帧): {hex_data}")
                                    # 传递完整帧数据给处理函数
                                    self.handle_Voice_data(hex_data)
                                else:
                                    # 如果只有FF字节，清空缓冲区
                                    self.voice_buffer.clear()
                                    break
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
                            
                            self.is_collecting_json = False
                        if lora_ser.in_waiting > 0:
                           raw_first=lora_ser.read(1)  # 一次读取一行
                            
                           if raw_first==b'{':
                                # 初始化接收缓冲区
                                raw_data = b'{'  # 包含开始的{字符
                                self.is_collecting_json = True
                                end_pos = lora_ser.read(1)
                                while True:
                                    if end_pos == b'}':
                                        break
                                    raw_data += end_pos
                                    end_pos = lora_ser.read(1)
                                raw_data += end_pos  # 包含结束的}字符
                                # 当收到完整的JSON数据后，再发送给处理函数
                                self.handle_sensor_data(raw_data)
                                # 清空缓冲区，准备接收下一个数据
                                raw_data = b''
                             ##接收到传感器数据    
                        else:
                            raw_data=lora_ser.readline()
                            if raw_data:
                                self.handle_sensor_data(raw_data)
                except Exception as e:
                    print(f"[错误] 处理控制指令数据时发生异常: {e}")
                    # 发生错误时重置缓冲区状态
                   
                    self.is_collecting_json = False
                    time.sleep(0.1)     

##主线程窗口
class MainWindow(QMainWindow):
    ##初始化主线程窗口，处理和更新ui显示
    def __init__(self):
        super().__init__()        
        uic.loadUi('E:\Arduinoproject\Project\生物培育\main.ui', self)##加载UI文件

        self.set_background_image()##设置背景图片        
        self.init_time_display()##初始化时间显示        
        self.init_inquiry_timer()##初始化问询定时器
        self.init_gauges()##初始化仪表盘
        self.init_labels()##初始化标签
        self.Load_pics()##加载所有图片
        self.showFullScreen()  
        ##启动一个定时器，用于更新时间显示
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.check_internet_connection)
        self.time_timer.start(3000)  # 3000毫秒 = 3秒
        
        # 启动问询小智是否联网的定时器
        self.xiaozhi_timer = QTimer(self)
        self.xiaozhi_timer.timeout.connect(self.ask_xiaozhi_network)
        self.xiaozhi_timer.start(30000)  # 30000毫秒 = 30秒
        print("问询小智定时器已启动，每30秒发送一次问询")
        
        # 添加标志位，用于标识是否正在进行设备问询
        self.is_inquiring = False
    def check_internet_connection(self):
        """判断树莓派是否联上网络
        
        Returns:
            bool: True表示已联网，False表示未联网
        """
        try:
            # 使用ping命令检查是否能连接到Google DNS服务器
            # -c 1: 发送1个ping包
            # -W 1: 超时时间1秒
            print(f"开始检查网络连接")
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "1", "www.baidu.com"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            # 打印命令输出（调试用）
 
            # print(f"ping命令输出: {result.stdout}")
            if result.returncode == 0:
                self.Load_pic(self.wifi_status, WIFI_ON_IMAGE)
                print("已联网")
            else:
                self.Load_pic(self.wifi_status, WIFI_OFF_IMAGE)
                print("未联网")
            # 如果返回码为0，表示ping成功，已联网
             
        except Exception as e:
            print(f"检查网络连接时出错: {str(e)}")
             

    def init_time_display(self):
        """初始化时间显示"""
        # 设置标签样式
        self.clock.setFont(QFont("SimHei", 60, QFont.Bold))
        self.clock.setStyleSheet("color: cyan;")
        self.clock.setAlignment(Qt.AlignCenter)
        self.clock.raise_()
        
        # 初始化计时器，每秒更新一次时间
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)  # 5000毫秒 = 5秒
        
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
            pixmap = QPixmap(image_path)
            self.background_label = QLabel(self)
            if DISPLAY_MODE4K:
                self.image_width = 3840  # 3840，1920
                self.image_height = 2160  # 2160，1080
                # self.showFullScreen()
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
    def init_inquiry_timer(self):
        """初始化问询定时器，每2秒发送一次问询帧"""
        self.inquiry_timer = QTimer(self)
        self.inquiry_timer.timeout.connect(self.send_inquiry)
        self.inquiry_timer.start(asktime)  # 5000毫秒 = 5秒
        print(f"问询定时器已启动，每{asktime/1000}秒发送一次问询帧")    
    def send_inquiry(self):
        """发送问询帧到所有设备，使用非阻塞方式"""
        # 只有在上一轮问询完成后才开始新的一轮
        if not self.is_inquiring:
            self.is_inquiring = True
            # 使用计数器跟踪当前要发送的设备ID
            self.current_device_index = 0
            # 使用预定义的设备ID数组
            self.devices_to_query = DEVICE_IDS
            # 启动设备发送定时器
            self.device_timer = QTimer(self)
            self.device_timer.timeout.connect(self.send_next_inquiry)
            self.device_timer.start(100)  # 立即开始发送第一个设备    
        # else:
        #     print("上一轮设备问询尚未完成，跳过本次触发")
    def send_next_inquiry(self):
        """发送下一个设备的问询帧"""
        # 检查是否还有设备需要发送
        if self.current_device_index < len(self.devices_to_query):
            device_id = self.devices_to_query[self.current_device_index]  # 从设备ID数组中获取设备ID
            send_inquiry_frame(device_id=device_id)
            print(f"发送问询帧到设备 {device_id}")
            # 增加索引
            self.current_device_index += 1
            # 设置下一次发送的延时
            self.device_timer.setInterval(asktime)
        else:
            # 所有设备都已发送，停止定时器
            self.device_timer.stop()
            print("完成所有设备问询帧发送")
            # 设置标志位，表示问询已完成
            self.is_inquiring = False
            print("完成所有设备问询帧发送")
    def init_label(self, label, initial_value, color="white"):
        """初始化标签显示"""
        # 设置文字内容
        label.setText(str(initial_value))
        
        # 设置文字样式
        label.setFont(QFont("SimHei", 30, QFont.Bold))  # 字体、大小、加粗
        label.setStyleSheet(f"color: {color};")  # 文字颜色   
        
        # 设置文字对齐方式
        label.setAlignment(Qt.AlignCenter)        
        # 确保文字显示在背景上方
        label.raise_()
    def init_labels(self):
        """初始化所有标签"""
        # 初始化温度标签
        self.init_label(self.temp_label, "88.8℃", "white")
        # 初始化湿度标签
        self.init_label(self.humidity_label, "88.8%", "white")
        # 初始化PM2.5标签
        self.init_label(self.pm25_label, "88.88", "white")
        # 初始化光照标签
        self.init_label(self.light_label, "8888", "white")
        # 初始化紫外线标签
        self.init_label(self.uv_label, "88.8", "white")
        # 初始化天气标签
        self.init_label(self.weather_label, "晴", "white")
        
        # 初始化LUX标签
        self.init_label(self.LUX, "LUX", "white")
        # 初始化自动关闭标签
        self.init_label(self.auto_off, "自动模式", "gray")

        self.init_label(self.wifi, "小智未连接", "gray")

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
        self.Load_pic(self.light_mode, LIGHT_MODE_OFF)
        self.Load_pic(self.fish_light, LIGHT_OFF)
        self.Load_pic(self.fish_light_mode, OFF_IMAGE)
        self.Load_pic(self.light1, LIGHT_OFF)
        self.Load_pic(self.light1_mode, OFF_IMAGE)
        self.Load_pic(self.light2, LIGHT_OFF)
        self.Load_pic(self.light2_mode, OFF_IMAGE)
        self.Load_pic(self.light3, LIGHT_OFF)
        self.Load_pic(self.light3_mode, OFF_IMAGE)
        self.Load_pic(self.fan1, FAN_OFF_IMAGE)
        self.Load_pic(self.fan1_mode, OFF_IMAGE)
        self.Load_pic(self.fan2, FAN_OFF_IMAGE)
        self.Load_pic(self.fan2_mode, OFF_IMAGE)
        self.Load_pic(self.fan3, FAN_OFF_IMAGE)
        self.Load_pic(self.fan3_mode, OFF_IMAGE)
        self.Load_pic(self.wifi_status, WIFI_OFF_IMAGE)
    
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
        big_gauge_width = 30 # 大仪表盘宽度
        default_width =310 # 默认宽度
        default_height = 310 # 默认高度

        bigger_gauge_width = 36 # 大仪表盘宽度
        sepeciail_width =335 # 默认宽度
        sepeciail_height = 335 # 默认高度
        start_angle = 237   # 起始角度 (3点钟方向为0度，顺时针增加)
        total_angle = 295   # 总共跨越的角度 (从225度到-45度)

        X_pos = 1890 # 仪表盘X坐标
        Y_pos = 610 # 仪表盘Y坐标
        Y_pos2=1070
        # 仪表盘配置数据
        gauges_config = [
            # 温度仪表盘
            {
                'name': 'temp1_gauge',
                'min_val': 0.0,
                'max_val': 60.0,
                'colors': [QColor(1, 253, 209), QColor(25,234,255), QColor(85,255,243)], 
                'width': default_width,
                'height': default_height,
                'x': 1900,
                'y': Y_pos,
                'gauge_width': big_gauge_width,
                'initial_value': 60
            },
            # 湿度仪表盘
            {
                'name': 'hum1_gauge',
                'min_val': 0.0,
                'max_val': 100.0,
                'colors': [QColor(36,201,255), QColor(61,127,255)], #（36,201,255）（61,127,255）
                
                'width': default_width,
                'height': default_height,
                'x': 1900+600,
                'y': Y_pos,
                'gauge_width': big_gauge_width,
                'initial_value': 100
            },
            # PM2.5仪表盘
            {
                'name': 'pm25_gauge',
                'min_val': 0.0,
                'max_val': 200.0,
                'colors': [QColor(249,100,0), QColor(253,218,101), QColor(50,196,255)], #（249,100,0）（253,218,101）（50,196,255）
                
                'width': default_width,
                'height': default_height,
                'x': 1900+600+610,
                'y': Y_pos,
                'gauge_width': big_gauge_width,
                'initial_value': 200
            },
            # 光强仪表盘（有特殊配置）
            {
                'name': 'light_gauge',
                'min_val': 0.0,
                'max_val': 4096.0,
                'colors': [QColor(80,191,255), QColor(93,229,255), QColor(92,255,183)], #（80,191,255）（93,229,255）（92,255,183）
                
                'width': sepeciail_width,
                'height': sepeciail_height,
                'x': X_pos-5,
                'y': Y_pos2, 
                'gauge_width': bigger_gauge_width,
                'start_angle': start_angle,
                'total_angle': total_angle,
                'initial_value': 4096
            },
            # uv仪表盘
            {
                'name': 'uv_gauge',
                'min_val': 0.0,
                'max_val': 10.0,
                'colors': [QColor(249,100,0), QColor(253,218,101), QColor(50,196,255)], #（249,100,0）（253,218,101）（50,196,255）
                
                'width': sepeciail_width,
                'height': sepeciail_height,
                'x': X_pos+600,
                'y': Y_pos2,
                'gauge_width': bigger_gauge_width,
                'start_angle': start_angle,
                'total_angle': total_angle,
                'initial_value': 10
            },
            # 天气仪表盘
            {
                'name': 'weather_gauge',
                'min_val': 0.0,
                'max_val': 100.0,
                'colors': [QColor(80,191,255), QColor(93,229,255), QColor(92,255,183)], #（80,191,255）（93,229,255）（92,255,183）
                
                'width': sepeciail_width,
                'height': sepeciail_height,
                'x': X_pos+600+610,
                'y': Y_pos2,
                'gauge_width': bigger_gauge_width,
                'start_angle': start_angle,
                'total_angle': total_angle,
                'initial_value': 100
            }
        ]
        
        # 批量创建仪表盘
        for config in gauges_config:
            self.init_gauge(**config)

       
        
    def update_display(self, temperature,humidity,light,pm25,uv,weather):
        """更新所有仪表盘显示"""
    
        # 更新温度仪表盘
        self.temp_label.setText(f"{temperature:.1f}°C")
        self.temp1_gauge.setValue(temperature)
        # 更新湿度仪表盘
        self.humidity_label.setText(f"{humidity:.1f}%")
        self.hum1_gauge.setValue(humidity)
        # 更新PM2.5仪表盘
        self.pm25_label.setText(f"{pm25:.1f}")
        self.pm25_gauge.setValue(pm25)
        # 更新光强仪表盘
        self.light_label.setText(f"{light:.1f}")
        self.light_gauge.setValue(light)
        # 更新uv仪表盘
        # 自定义映射函数，将值从一个范围映射到另一个范围
        def map_value(value, in_min, in_max, out_min, out_max):
            return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min
        
        uv_mapped = map_value(uv, 0, 1024, 0, 10)  # 映射uv值到0-10范围
        self.uv_label.setText(f"{uv_mapped:.0f}")
        self.uv_gauge.setValue(uv_mapped)
        
        # 更新天气仪表盘
        if weather==0:
            self.weather_label.setText("雨")
        else:
            self.weather_label.setText("晴")

        print("自动控制状态:", auto_mode_flag)
        if auto_mode_flag:##自动照明
            # 自动控制逻辑
            # 例如，根据温度和湿度调整灯光和空调
            if light > light_threshold:
                send_lora_command(0x0D, 0x01, 0x00)  # 打开一号补光灯
                self.Load_pic(self.light1, LIGHT_ON)
                self.Load_pic(self.light1_mode, ON_IMAGE)
                self.Load_pic(self.light2, LIGHT_ON)
                self.Load_pic(self.light2_mode, ON_IMAGE)
                self.Load_pic(self.light3, LIGHT_ON)
                self.Load_pic(self.light3_mode, ON_IMAGE)
                self.Load_pic(self.fish_light, LIGHT_ON)
                self.Load_pic(self.fish_light_mode, ON_IMAGE)
                 
            else:
                send_lora_command(0x0D, 0x02, 0x00)  # 关闭一号补光灯
                self.Load_pic(self.light1, LIGHT_OFF)
                self.Load_pic(self.light1_mode, OFF_IMAGE)
                self.Load_pic(self.light2, LIGHT_OFF)
                self.Load_pic(self.light2_mode, OFF_IMAGE)
                self.Load_pic(self.light3, LIGHT_OFF)
                self.Load_pic(self.light3_mode, OFF_IMAGE)
                self.Load_pic(self.fish_light, LIGHT_OFF)
                self.Load_pic(self.fish_light_mode, OFF_IMAGE)
        
           
    
                
    def update_voice_display(self, device_id,node,command):
        """接收并处理SerialWorker发送的语音指令数据"""
        global auto_mode_flag
        print(f"主线程语音指令数据: 设备ID: 0x{device_id:02X}, 节点: 0x{node:02X}, 指令: 0x{command:02X}")
        
        if device_id==0x0C:##灯光控制
            # 处理灯光控制指令
            if node == 0x01:  # 打开一号补光灯
                print("[灯光控制] 打开一号补光灯")
                self.Load_pic(self.light1, LIGHT_ON)
                self.Load_pic(self.light1_mode, ON_IMAGE)
                   
            elif node == 0x02:  # 关闭一号补光灯
                print("[灯光控制] 关闭一号补光灯")
                # 更新UI图片显示
                 
                self.Load_pic(self.light1, LIGHT_OFF)
                self.Load_pic(self.light1_mode, OFF_IMAGE)
                     
            elif node == 0x03:  # 打开二号补光灯
                print("[灯光控制] 打开二号补光灯")
                # 更新UI图片显示
                self.Load_pic(self.light2, LIGHT_ON)
                self.Load_pic(self.light2_mode, ON_IMAGE)
            elif node == 0x04:  # 关闭二号补光灯
                print("[灯光控制] 关闭二号补光灯")
                # 更新UI图片显示
                self.Load_pic(self.light2, LIGHT_OFF)
                self.Load_pic(self.light2_mode, OFF_IMAGE)  
                    
            elif node == 0x05:  # 打开三号补光灯
                print("[灯光控制] 打开三号补光灯")
                # 更新UI图片显示
                self.Load_pic(self.light3, LIGHT_ON)
                self.Load_pic(self.light3_mode, ON_IMAGE)
                print("[灯光控制] 打开三号补光灯")
                # 更新UI图片显示
                self.Load_pic(self.light3, LIGHT_ON)
                self.Load_pic(self.light3_mode, ON_IMAGE)
            elif node == 0x06:  # 关闭三号补光灯
                print("[灯光控制] 关闭三号补光灯")
                # 更新UI图片显示
                self.Load_pic(self.light3, LIGHT_OFF)
                self.Load_pic(self.light3_mode, OFF_IMAGE)  
            elif node == 0x07:  # 打开鱼缸灯
                print("[灯光控制] 打开鱼缸灯")
                # 更新UI图片显示
                self.Load_pic(self.fish_light, LIGHT_ON)
                self.Load_pic(self.fish_light_mode, ON_IMAGE)
            elif node == 0x08:  # 关闭鱼缸灯
                print("[灯光控制] 关闭鱼缸灯")
                # 更新UI图片显示
                self.Load_pic(self.fish_light, LIGHT_OFF)
                
                self.Load_pic(self.fish_light_mode, OFF_IMAGE)  
            else:
                print(f"[灯光控制] 未知指令: 0x{command:02X}")
        elif device_id==0x0D:##全部灯光控制
            # 处理鱼缸控制指令
            if node == 0x01:  # 打开鱼缸                
                # 更新UI图片显示
                self.Load_pic(self.light1, LIGHT_ON)
                self.Load_pic(self.light1_mode, ON_IMAGE)
                self.Load_pic(self.light2, LIGHT_ON)
                self.Load_pic(self.light2_mode, ON_IMAGE)
                self.Load_pic(self.light3, LIGHT_ON)
                self.Load_pic(self.light3_mode, ON_IMAGE)
                self.Load_pic(self.fish_light, LIGHT_ON)
                self.Load_pic(self.fish_light_mode, ON_IMAGE)
            elif node == 0x02:  # 关闭鱼缸                
                # 更新UI图片显示
                self.Load_pic(self.light1, LIGHT_OFF)
                self.Load_pic(self.light1_mode, OFF_IMAGE)
                self.Load_pic(self.light2, LIGHT_OFF)
                self.Load_pic(self.light2_mode, OFF_IMAGE)
                self.Load_pic(self.light3, LIGHT_OFF)
                self.Load_pic(self.light3_mode, OFF_IMAGE)
                self.Load_pic(self.fish_light, LIGHT_OFF)
                self.Load_pic(self.fish_light_mode, OFF_IMAGE)
            else:
                print(f"[灯光控制] 未知指令: 0x{command:02X}")
        elif device_id==0x0E:##风扇控制
            if node == 0x01:  # 打开一号通风系统
                print(f"[通风控制] 打开一号通风系统")
                self.Load_pic(self.fan1, FAN_ON_IMAGE)
                self.Load_pic(self.fan1_mode, ON_IMAGE)
            elif node == 0x02:  # 关闭一号通风系统
                print(f"[通风控制] 关闭一号通风系统")
                self.Load_pic(self.fan1, FAN_OFF_IMAGE)
                self.Load_pic(self.fan1_mode, OFF_IMAGE)
            elif node == 0x03:  # 打开二号通风系统
                print(f"[通风控制] 打开二号通风系统")
                self.Load_pic(self.fan2, FAN_ON_IMAGE)
                self.Load_pic(self.fan2_mode, ON_IMAGE)
            elif node == 0x04:  # 关闭二号通风系统
                print(f"[通风控制] 关闭二号通风系统")
                self.Load_pic(self.fan2, FAN_OFF_IMAGE)
                self.Load_pic(self.fan2_mode, OFF_IMAGE)
            elif node == 0x05:  # 打开三号通风系统
                print(f"[通风控制] 打开三号通风系统")
                self.Load_pic(self.fan3, FAN_ON_IMAGE)
                self.Load_pic(self.fan3_mode, ON_IMAGE)
            elif node == 0x06:  # 关闭三号通风系统
                print(f"[通风控制] 关闭三号通风系统")
                self.Load_pic(self.fan3, FAN_OFF_IMAGE)
                self.Load_pic(self.fan3_mode, OFF_IMAGE)
            else:
                print(f"[通风控制] 未知指令: 0x{node:02X}")
        elif device_id==0x09:##全部通风设备控制
            if node == 0x01:  # 打开全部通风设备
                print(f"[通风控制] 打开全部通风设备")
                self.Load_pic(self.fan1, FAN_ON_IMAGE)
                self.Load_pic(self.fan2, FAN_ON_IMAGE)
                self.Load_pic(self.fan3, FAN_ON_IMAGE)
                self.Load_pic(self.fan1_mode, ON_IMAGE)
                self.Load_pic(self.fan2_mode, ON_IMAGE)
                self.Load_pic(self.fan3_mode, ON_IMAGE)
            elif node == 0x02:  # 关闭全部通风设备
                print(f"[通风控制] 关闭全部通风设备")
                self.Load_pic(self.fan1, FAN_OFF_IMAGE)
                self.Load_pic(self.fan2, FAN_OFF_IMAGE)
                self.Load_pic(self.fan3, FAN_OFF_IMAGE)
                self.Load_pic(self.fan1_mode, OFF_IMAGE)
                self.Load_pic(self.fan2_mode, OFF_IMAGE)
                self.Load_pic(self.fan3_mode, OFF_IMAGE)
            else:
                print(f"[全部通风控制] 未知指令: 0x{node:02X}")
        elif device_id==0x0A:##自动照明控制
            if node == 0x01:  # 打开自动照明
                auto_mode_flag=True
                print(f"[自动照明] 打开自动照明")
                self.Load_pic(self.light_mode, LIGHT_MODE_ON)
                self.init_label(self.auto_off, "自动模式", "cyan")
            elif node == 0x02:  # 关闭自动照明
                auto_mode_flag=False
                print(f"[自动照明] 关闭自动照明")
                self.Load_pic(self.light_mode, LIGHT_MODE_OFF)
                self.init_label(self.auto_off, "自动模式", "gray")
            else:
                print(f"[自动照明] 未知指令: 0x{node:02X}")
        elif device_id==0x0B:##全部设备控制
            if node == 0x01:  # 打开所有设备
                print(f"[全部设备] 打开所有设备")
                # 打开所有灯光
                self.Load_pic(self.light1, LIGHT_ON)
                self.Load_pic(self.light1_mode, ON_IMAGE)
                self.Load_pic(self.light2, LIGHT_ON)
                self.Load_pic(self.light2_mode, ON_IMAGE)
                self.Load_pic(self.light3, LIGHT_ON)
                self.Load_pic(self.light3_mode, ON_IMAGE)
                self.Load_pic(self.fish_light, LIGHT_ON)
                self.Load_pic(self.fish_light_mode, ON_IMAGE)
                # 打开所有通风设备
                self.Load_pic(self.fan1, FAN_ON_IMAGE)
                self.Load_pic(self.fan1_mode, ON_IMAGE)
                self.Load_pic(self.fan2, FAN_ON_IMAGE)
                self.Load_pic(self.fan2_mode, ON_IMAGE)
                self.Load_pic(self.fan3, FAN_ON_IMAGE)
                self.Load_pic(self.fan3_mode, ON_IMAGE)
         
            elif node == 0x02:  # 关闭所有设备
                print(f"[全部设备] 关闭所有设备")
                # 关闭所有灯光
                self.Load_pic(self.light1, LIGHT_OFF)
                self.Load_pic(self.light1_mode, OFF_IMAGE)
                self.Load_pic(self.light2, LIGHT_OFF)
                self.Load_pic(self.light2_mode, OFF_IMAGE)
                self.Load_pic(self.light3, LIGHT_OFF)
                self.Load_pic(self.light3_mode, OFF_IMAGE)
                self.Load_pic(self.fish_light, LIGHT_OFF)
                self.Load_pic(self.fish_light_mode, OFF_IMAGE)
                # 关闭所有通风设备
                self.Load_pic(self.fan1, FAN_OFF_IMAGE)
                self.Load_pic(self.fan1_mode, OFF_IMAGE)
                self.Load_pic(self.fan2, FAN_OFF_IMAGE)
                self.Load_pic(self.fan2_mode, OFF_IMAGE)
                self.Load_pic(self.fan3, FAN_OFF_IMAGE)
                self.Load_pic(self.fan3_mode, OFF_IMAGE)
                 
            else:
                print(f"[全部设备] 未知指令: 0x{node:02X}")
            
    def update_xiaozhi_display(self, role, content):
        print(f"[小助手] {role}: {content}")
        self.init_label(self.wifi, "小智已连接", "white")
        if role=="user":
            self.init_label(self.user, content, "white")
        if role=="assistant":
            self.init_label(self.assistant, content, "white")
            
    def change_wifi(self, ssid):
        self.init_label(self.wifi, "小智已连接", "white")
        
    def ask_xiaozhi_network(self):
        """问询小智是否联网，发送{\"event\":\"ask\"}"""
        global lora_ser
        try:
            # 构建问询JSON数据
            ask_data = {"event": "ask"}
            ask_json_str = json.dumps(ask_data) + '\n'
            
            # 检查LoRa串口是否已初始化并打开
            if lora_ser and lora_ser.is_open:
                lora_ser.write(ask_json_str.encode('utf-8'))
                self.init_label(self.wifi, "小智未连接", "gray")
                print(f"已发送问询: {ask_json_str.strip()}")
            else:
                print("LoRa串口未初始化或未打开，无法发送问询")
                
        except Exception as e:
            print(f"发送问询时出错: {str(e)}")

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
        serial_worker.data_json.connect(main_window.update_xiaozhi_display)
        serial_worker.change_wifi.connect(main_window.change_wifi)
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