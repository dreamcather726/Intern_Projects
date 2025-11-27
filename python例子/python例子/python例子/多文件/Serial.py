import serial
import time
import json
from PyQt5.QtCore import QThread, QObject, pyqtSignal, Qt, QTimer, QRectF
from PyQt5.QtGui import QColor
import re
### 语音输入串口参数
VOICE_PORT = 'COM23'    # 连接语音模块的串口
VOICE_BAUD_RATE = 9600  # 语音模块的波特率
VOICE_TIMEOUT  = 1 

LORA_PORT = 'COM16'      # 连接LoRa模块的串口
LORA_BAUD_RATE = 115200  # LoRa模块的波特率
LORA_TIMEOUT  = 1 
# --- 全局串口对象 ---
inquiry_device_ids = [1, 3, 5, 7, 9]  # 示例：只问询ID为1,3,5,7,9的设备
AskTime=3000  # 每个设备的问询间隔
devices_asktime=AskTime*len(inquiry_device_ids)   # 每轮设备询问的时间间隔
Frame_Header=[0x55,0xAA]# 帧头
Frame_Tail=[0x00,0xff]# 帧尾

class SerialWorker(QThread):
    """
    串口工作线程类，负责在后台线程中处理串口通信。
    主要功能：
    1. 与语音模块和LoRa模块进行数据交换
    2. 处理设备数据的接收和解析
    3. 管理设备数据的缓存和更新
    """
    VoiceCommand = pyqtSignal(int,int)  # 发送语音指令数据给主线程
    SensorData = pyqtSignal(str)  # 发送传感器数据给主线程
    def __init__(self, parent=None):

        super().__init__(parent)
        self.voice_ser = None  # 语音输入串口实例
        self.lora_ser = None     # LoRa串口实例
        self._is_running = True
        self.is_sending = False  # 用于标识当前是否正在发送数据
        self.inquiry_device_ids = inquiry_device_ids  # 问询设备ID数组（可自定义）
        self.AskTime=AskTime  # get设备数据的时间间隔，默认3秒
        self.devices_asktime=devices_asktime  # 每轮设备询问的时间间隔，默认4秒
 
        self.inquiry_timer = QTimer(self)
        self.inquiry_timer.timeout.connect(self.send_inquiry)        
        self.inquiry_timer.start(devices_asktime)  # 30000毫秒 = 30秒
        self.send_inquiry()
        print(f"问询定时器已启动，每{devices_asktime/1000}秒发送一轮设备问询帧")    


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
        self.device_timer.start(AskTime)
    def send_next_inquiry(self):
        """发送下一个设备的问询帧"""
        # 检查是否还有设备需要发送
        if self.current_device_index < len(inquiry_device_ids):
            device_id = inquiry_device_ids[self.current_device_index]  # 从预定义的设备ID数组中获取
            self.send_inquiry_frame(device_id=device_id)
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
    def send_inquiry_frame(self,device_id=0x01):
        """
        发送问询帧到LoRa模块
        
        Args:
            device_id (int): 目标设备ID，默认为0x01
        """
     
        
        # 检查当前是否正在发送数据，如果是则等待
        while self.is_sending:
            print("[信息] 当前有数据正在发送，等待发送完成...")
            time.sleep(0.3)
        
        # 设置发送状态为正在发送
        self.is_sending = True
        try:
            # 检查LoRa串口是否已初始化并打开
            if not self.lora_ser or not self.lora_ser.is_open:
                print("[错误] LoRa串口未初始化或未打开，无法发送问询帧")
                return
            
            # 构建问询帧，格式: AA 设备号 FF
            inquiry_frame = bytes([0xBB, device_id, 0xFF])
            
            # 发送问询帧
            self.lora_ser.write(inquiry_frame)
            hex_string = ' '.join(f'{b:02x}' for b in inquiry_frame)
            print(f"-> 发送问询帧: {hex_string.upper()} (设备ID: {device_id})")
            
        except Exception as e:
            print(f"[错误] 发送问询帧失败: {e}")
        finally:
            # 无论是否发生异常，都设置发送状态为未发送
            self.is_sending = False  
    def receive_complete_frameHEX(self,ser):   
        """
        接收完整帧数据，从帧头开始直到帧尾结束
        
        Returns:
            bytes: 完整的帧数据，如果超时或出错则返回None
        """
        try:
            frame_buffer = []
            start_time = time.time()
            timeout = 2.0  # 2秒超时
            
            # 读取帧头检测
            byte_data = ser.read(len(Frame_Header))

            if byte_data and byte_data[0] == Frame_Header[0]:  # 检测到帧头
                if byte_data:
                        for byte in byte_data:
                            frame_buffer.append(byte) 
                print(f"[帧接收] 检测到帧头 {Frame_Header[0]:02x}")
                
                # 继续接收帧数据直到检测到帧尾或超时
                while time.time() - start_time < timeout:
                    if ser.in_waiting > 0:
                        byte_data = ser.read(len(Frame_Tail))
                        if byte_data:
                            for byte in byte_data:
                                frame_buffer.append(byte)   
                            # 检查是否到达帧尾
                            if byte_data[-1] == Frame_Tail[-1]:
                                # print(f"[帧接收] 检测到帧尾 {Frame_Tail[-1]:02x}，完整帧接收完成")
                                return bytes(frame_buffer)
                    time.sleep(0.01)
                
                # 超时处理
                print(f"[帧接收] 超时未检测到帧尾，已接收数据: {['0x{:02X}'.format(b) for b in frame_buffer]}")
                return None
            
            return None
            
        except Exception as e:
            print(f"[错误] 接收完整帧数据时发生异常: {e}")
            return None
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
            
            # 检查是否符合指令格式 (55 aa 01 00 FF)
            # 指令格式: [帧头1, 设备ID, 指令1, 指令2, 校验和]
            if len(hex_bytes) >= 5 and hex_bytes[0] == Frame_Header[0]:### 检查帧头是否匹配根据定义的帧头添加条件
                device_id = hex_bytes[2] if len(hex_bytes) > 2 else 0
                command = hex_bytes[3] if len(hex_bytes) > 4 else 0
                # 先更新界面显示，再发送指令（更好的用户体验）
                self.VoiceCommand.emit(device_id, command)
                # 短暂延迟确保界面更新完成
                time.sleep(0.05)
                self.send_lora_command(device_id, command,interval_time=0.5)
                
                # print(f"[处理] 有效语音指令帧: 设备ID={device_id}, 指令={command}")    
            else:
                print(f"[处理] 不是有效的语音指令帧格式")
                print(f"  接收到的字节: {['0x{:02X}'.format(b) for b in hex_bytes]}")
                
        except Exception as e:
            print(f"[错误] 处理语音指令数据时发生异常: {e}")
    def send_lora_command(self,device_id, action,send_lora_Times=3,interval_time=0.3):
        """
        构建并发送LoRa指令。
        指令格式: [帧头, 设备ID, 节点ID, 动作, 校验和]
        参数:
        device_id: 设备ID
        action: 动作指令
        send_lora_Times: 发送次数，默认3次
        interval_time: 每次发送间隔时间，默认0.3秒
        """

        command=[]
        # 检查当前是否正在发送数据，如果是则等待
        while self.is_sending:
            print("[信息] 当前有数据正在发送，等待发送完成...")
            time.sleep(0.1)
        
        # 设置发送状态为正在发送
        self.is_sending = True
        
        try:
            # 检查LoRa串口是否已初始化并打开
            if not self.lora_ser or not self.lora_ser.is_open:
                print("[错误] LoRa串口未初始化或未打开")
                return
            # 添加帧头
            for i in range(len(Frame_Header)):
                command.append(Frame_Header[i])
            command.append(device_id)
 
            command.append(action)
             # 添加帧尾
            for i in range(len(Frame_Tail)):
                command.append(Frame_Tail[i])
             
        
            # 将所有部分打包成一个bytes对象
            command = bytes(command)

            # print(f"发送指令: {command}")
            # 为了提高无线通信的可靠性，同一指令连续发送3次
            for attempt in range(send_lora_Times):
                self.lora_ser.write(command)
                # 为了方便调试，将发送的字节指令以十六进制格式打印出来
                hex_string = ' '.join(f'{b:02x}' for b in command)
                print(f"-> LoRa发送 (第{attempt+1}次): {hex_string.upper()}")
                time.sleep(interval_time)  # 每次发送后短暂延时
            
            # 3次发送完成后，再延时一小段时间，确保LoRa模块有时间处理和切换收发状态
            time.sleep(0.2)
        except Exception as e:
            print(f"[严重错误] LoRa发送失败: {e}")
        finally:
            # 无论是否发生异常，都设置发送状态为未发送
            self.is_sending = False
    
    def receive_complete_frameJSON(self,ser):   
        """
        接收完整JSON数据,从{开始直到}结束
        
        Returns:
        str: 完整的JSON数据字符串.如果未完成则返回None
        """
        try:
            frame_data = ""
            start_time = time.time()
            timeout = 2  # 2秒超时
            
            # 等待并检测JSON开始标记
            while time.time() - start_time < timeout:
                if ser.in_waiting > 0:
                    data = ser.read(1)
                    if data == b'{':
                        frame_data += data.decode('utf-8')
                        # print("[JSON接收] 检测到JSON开始标记 '{'")
                        break
                time.sleep(0.01)
            
            # 如果没有检测到{，返回None
            if not frame_data:
                return None
            
            # 继续读取直到检测到JSON结束标记}
            brace_count = 1  # 已经有一个{
            while time.time() - start_time < timeout:
                if ser.in_waiting > 0:
                    data = ser.read(1)
                    char = data.decode('utf-8')# 解码为字符串
                    frame_data += char
                    
                    # 统计大括号数量
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        
                    # 当所有大括号都匹配完成时
                    if brace_count == 0:
                        # print("[JSON接收] 检测到JSON结束标记 '}'，完整JSON接收完成")
                        return frame_data
                time.sleep(0.01)
            
            # 超时处理
            print(f"[JSON接收] 超时未检测到完整的JSON数据，已接收数据: {frame_data}")
            return None
            
        except Exception as e:
            print(f"[错误] 接收完整JSON帧时发生异常: {e}")
            return None
    
   
            
        except json.JSONDecodeError as e:
            print(f"[JSON处理错误] JSON解析失败: {e}")
            print(f"[JSON处理错误] 原始数据: {data}")
        except Exception as e:
            print(f"[JSON处理错误] 处理JSON数据时发生异常: {e}")
    def run(self):
        """在后台线程中打开串口"""
        try:
            self.voice_ser = serial.Serial(VOICE_PORT, VOICE_BAUD_RATE, timeout=VOICE_TIMEOUT)
            print(f"成功打开语音识别串口 {VOICE_PORT}")
            
        except serial.SerialException as e:
            print(f"[警告] 无法打开语音识别串口 {VOICE_PORT}: {e}")

        try:
            self.lora_ser = serial.Serial(LORA_PORT, LORA_BAUD_RATE, timeout=LORA_TIMEOUT)
            print(f"成功打开LoRa串口 {LORA_PORT}")
            
        except serial.SerialException as e:
            print(f"[警告] 无法打开LoRa串口 {LORA_PORT}: {e}")
        print("后台串口监听线程已启动。")
 
        while self._is_running:
            try:
                ##监听语言识别的串口
                if self.voice_ser and self.voice_ser.is_open:
                    if self.voice_ser.in_waiting > 0:
                      
                        frame_data = self.receive_complete_frameHEX(self.voice_ser)    
                        if frame_data:
                            # 将字节数据转换为十六进制字符串格式
                            hex_data = ' '.join(f'{b:02x}' for b in frame_data)
                            print(f"<- 语音识别串口接收 (完整帧): {hex_data.upper()}")
                            # 传递数据给处理函数
                            self.handle_Voice_data(hex_data)
                # 短暂休眠以减少CPU占用
                time.sleep(0.01)
            except serial.SerialException as e:
                print(f"[严重错误] 后台线程发生未知错误: {e}")
                # 发生错误时短暂休眠，避免刷屏
                time.sleep(2)
            except Exception as e:
                print(f"[错误] 处理串口数据时发生异常: {e}")
                time.sleep(0.3)
            try:
                ##监听LoRa识别的串口
                if self.lora_ser and self.lora_ser.is_open:
                    if self.lora_ser.in_waiting > 0:    
                        frame_data = self.receive_complete_frameJSON(self.lora_ser)    
                        if frame_data:
                            print(f"<- LoRa串口接收原始: {frame_data}")
                            self.SensorData.emit(frame_data)
                # 短暂休眠以减少CPU占用
                time.sleep(0.01)
            except serial.SerialException as e:
                print(f"[严重错误] 后台线程发生未知错误: {e}")
                # 发生错误时短暂休眠，避免刷屏
                time.sleep(2)
            except Exception as e:
                print(f"[错误] 处理串口数据时发生异常: {e}")
                time.sleep(0.3)
