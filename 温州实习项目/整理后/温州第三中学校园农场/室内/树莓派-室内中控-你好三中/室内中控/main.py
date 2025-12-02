import os
import sys
from tkinter import OFF, ON
import serial
import time
import json
import csv
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget
from PyQt5.QtGui import QPixmap, QFont, QColor
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.uic import loadUi
from ybp import GaugeWidget
import subprocess
import re
import os
import platform
# 全局变量表示自动模式的开关
global_auto_sprinkler = False  # 喷淋系统自动模式
global_auto_light = False      # 补光系统自动模式
global_auto_light1 = False     # 补光1系统自动模式
threshold_soil_moisture=50     # 土壤水分阈值（%）
# aarduino发送数据格式是   // 
# 室内土培(设备4，5，6)数据测试4,25.6,23.5,234,6.8
# 树莓派向室内发送的数据格式是 SS,1,0.0,0.0,0.0,0.0,0,2,0.0,0.0,0.0,0.0,0,3,0,PP
# 室内（设备8）测试数据 15,10.5,81,100.9,3589.2,5
# 水培柜（设备12，13，14）测试数据 12,10.5,23.5

from datetime import datetime, timezone, timedelta
# -------------------------- 配置参数 --------------------------
# 图片路径宏定义
PIC_DIR = r"pic" # 树莓/home/pi/Desktop/AI_Indoor/ai/pic     windows E:\Arduino project\智慧室内2.0\pic
BACKGROUND_IMAGE = os.path.join(PIC_DIR, "background.jpg")
OPEN_IMAGE = os.path.join(PIC_DIR, "open.png")
DOWN_IMAGE = os.path.join(PIC_DIR, "down.png")
OFF_IMAGE = os.path.join(PIC_DIR, "off.png")
ON_IMAGE = os.path.join(PIC_DIR, "on.png")
ON1_IMAGE = os.path.join(PIC_DIR, "on.png")
FL_OFF_IMAGE = os.path.join(PIC_DIR, "fl_off.png")
FL_ON_IMAGE = os.path.join(PIC_DIR, "fl_on.png")
FEED_OFF_IMAGE = os.path.join(PIC_DIR, "feed_off.png")
FEED_ON_IMAGE = os.path.join(PIC_DIR, "feed_on.png")
LIGHT_ON_IMAGE = os.path.join(PIC_DIR, "light_on.png")
LIGHT_OFF_IMAGE = os.path.join(PIC_DIR, "light_off.png")
WIFI_OFF_IMAGE = os.path.join(PIC_DIR, "wifi_off.png")
WIFI_ON_IMAGE = os.path.join(PIC_DIR, "wifi_on.png")



times=3
# 串口配置（需与Arduino的SEND_BAUD一致，端口根据实际情况调整）
SERIAL_PORT ='/dev/ttyAMA0' # 树莓派硬件串口'/dev/ttyAMA0'
BAUD_RATE = 115200            # 与Arduino的SEND_BAUD=115200保持一致
TIMEOUT = 1                   # 串口读取超时时间（秒）
INQUIRY_INTERVAL = 5000       # 问询帧发送间隔（毫秒）

XIAOZHI_SERIAL_PORT = '/dev/ttyAMA4'  # 小助手数据接收串口，根据实际情况调整
XIAOZHI_BAUD_RATE = 9600    # 小助手串口的波特率
XIAOZHI_TIMEOUT = 1           # 小助手串口读取超时时间（秒）

def send_control_command(device_id, action, data, send_times=times):
    """
    发送控制命令到设备 - 使用主应用中的serial_thread发送，避免串口资源冲突
    
    Args:
        device_id: 设备ID
        action: 动作码
        data: 数据值
        send_times: 重复发送次数，默认为1次
    
    Returns:
        bool: 发送是否成功
    """
    # 构造命令格式: A0 + 设备ID + 动作 + 数据 + FF
    command = bytearray([
        0xA0,       # 帧头
        device_id,  # 设备ID
        action,     # 动作码
        data,       # 数据值
        0xFF        # 帧尾
    ])
    
    # 打印发送的命令
    hex_command = ' '.join([f"{b:02X}" for b in command])
    print(f"[{time.strftime('%H:%M:%S')}] 准备发送命令: {hex_command} 到设备 {device_id}")
    
    # 尝试通过主应用的serial_thread发送命令
    try:
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        main_app = None
        
        # 查找主应用实例
        for widget in app.topLevelWidgets():
            if hasattr(widget, 'serial_thread'):
                main_app = widget
                break
        
        if main_app and main_app.serial_thread and hasattr(main_app.serial_thread, 'ser') and main_app.serial_thread.ser and main_app.serial_thread.ser.is_open:
            # 暂停其他数据处理，避免命令发送时的数据干扰
            main_app.pause_other_data = True
            
            try:
                # 获取主应用的串口连接
                ser = main_app.serial_thread.ser
                
                # 先清空接收缓冲区，避免残留数据干扰
                ser.flushInput()
                
                # 重复发送指定次数的命令
                for i in range(send_times):
                    # 发送命令
                    ser.write(command)
                    ser.flush()  # 确保数据被发送
                    print(f"[{time.strftime('%H:%M:%S')}] 通过主应用serial_thread发送命令第 {i+1}/{send_times} 次")
                    # 等待一段时间
                    time.sleep(1)  # 使用time.sleep，适用于任何线程
                
                return True
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] 通过主应用serial_thread发送命令时出错: {e}")
                return False
            finally:
                # 恢复其他数据处理
                main_app.pause_other_data = False
        else:
            # 如果找不到主应用的serial_thread，尝试临时创建串口连接（备用方案）
            print(f"[{time.strftime('%H:%M:%S')}] 找不到可用的主应用serial_thread，尝试使用临时串口连接")
            
            ser = None
            try:
                # 打开临时串口连接
                ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
                if ser.is_open:
                    # 先清空接收缓冲区
                    ser.flushInput()
                    
                    # 重复发送指定次数的命令
                    for i in range(send_times):
                        ser.write(command)
                        ser.flush()
                        print(f"[{time.strftime('%H:%M:%S')}] 通过临时串口连接发送命令第 {i+1}/{send_times} 次")
                        time.sleep(1)
                    
                    return True
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] 无法打开临时串口连接")
                    return False
            except serial.SerialException as e:
                error_msg = f"[{time.strftime('%H:%M:%S')}] 打开临时串口 {SERIAL_PORT} 失败: {e}"
                print(error_msg)
                
                # 根据错误类型提供建议
                if "拒绝访问" in str(e) or "PermissionError" in str(e):
                    print(f"[{time.strftime('%H:%M:%S')}] 错误建议: 请检查串口 {SERIAL_PORT} 是否已被其他程序占用")
                    print(f"[{time.strftime('%H:%M:%S')}] 错误建议: 请确保程序以管理员权限运行")
                elif "找不到" in str(e) or "不存在" in str(e):
                    print(f"[{time.strftime('%H:%M:%S')}] 错误建议: 请检查串口 {SERIAL_PORT} 是否正确连接")
                
                return False
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] 临时串口操作时发生未预期的错误: {e}")
                return False
            finally:
                # 确保关闭临时串口连接
                if ser and ser.is_open:
                    ser.close()
                    print(f"[{time.strftime('%H:%M:%S')}] 临时串口 {SERIAL_PORT} 已关闭")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 发送命令过程中发生错误: {e}")
        return False
# ================== WiFi凭据处理 ==================
def get_current_wifi_info():
    """获取当前连接的WiFi名称和密码"""
    try:
        # 检查是否为Linux系统
        if platform.system() != 'Linux':
            print("警告: 此脚本专为Linux系统(如树莓派)设计")
            
        # 获取当前连接的WiFi名称
        ssid = None
        try:
            # 方法1: 使用iwgetid获取当前SSID
            result = subprocess.check_output(
                ['iwgetid', '-r'],
                stderr=subprocess.DEVNULL,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'
            )
            ssid = result.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            # 方法2: 尝试使用iw命令
            try:
                result = subprocess.check_output(
                    ['iw', 'dev'],
                    stderr=subprocess.DEVNULL,
                    universal_newlines=True,
                    encoding='utf-8',
                    errors='replace'
                )
                # 解析输出找到当前连接的SSID
                for line in result.split('\n'):
                    if 'ssid' in line:
                        ssid = line.split('ssid')[1].strip()
                        break
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        
        if not ssid:
            return None, "未连接到任何WiFi网络"
        
        # 获取密码
        password = "未找到密码"
        
        # 从wpa_supplicant.conf获取密码
        wpa_supplicant_path = '/etc/wpa_supplicant/wpa_supplicant.conf'
        if os.path.exists(wpa_supplicant_path):
            try:
                with open(wpa_supplicant_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                    
                    # 查找指定SSID的配置块
                    ssid_pattern = re.compile(r'network=\{[^{]*ssid="' + re.escape(ssid) + r'"[^{}]*\}', re.DOTALL)
                    match = ssid_pattern.search(content)
                    
                    if match:
                        network_block = match.group(0)
                        # 提取密码
                        psk_match = re.search(r'psk="([^"]+)"', network_block)
                        if psk_match:
                            password = psk_match.group(1)
                        # 检查是否是无密码网络
                        elif 'key_mgmt=NONE' in network_block:
                            password = "无密码"
            except Exception:
                pass
        
        # 尝试使用nmcli获取密码（如果NetworkManager可用）
        if password == "未找到密码":
            try:
                result = subprocess.check_output(
                    ['nmcli', '-s', '-g', '802-11-wireless-security.psk', 'connection', 'show', f'"{ssid}"'],
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    encoding='utf-8',
                    errors='replace'
                )
                nmcli_password = result.strip()
                if nmcli_password:
                    password = nmcli_password
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        
        return ssid, password
        
    except Exception as e:
        return None, f"获取WiFi信息时出错: {e}"
# 传感器数据接收线程
class SerialReceiveThread(QThread):
    # 定义信号，用于将接收到的数据发送到主线程
    data_received = pyqtSignal(int, float, float, float, float, int)  # device_id, soil_temp, soil_moisture, soil_ec, soil_ph, relay_state
    # 定义水箱数据信号
    water_tank_data_received = pyqtSignal(int, int)  # 设备ID, 水箱状态
    # 定义水培柜数据信号
    hydroponic_data_received = pyqtSignal(int, float, float, int)  # 设备ID, pH值, 水温, 液位状态
    # 定义室内环境传感器数据信号
    indoor_env_data_received = pyqtSignal(int, float, float, float, float, float)  # 设备ID, 温度, 湿度, pm2.5, 光照强度, 紫外线强度
    # 定义室外数据信号
    outdoor_data_received = pyqtSignal(dict)  # 发送解析后的室外数据字典
    # 定义WiFi事件信号
    wifi_event_received = pyqtSignal(str)  # 发送WiFi事件类型（如"connect"）
    # 定义WiFi SSID信号
    
    
    def __init__(self, port, baud_rate, timeout):
        super().__init__()
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.ser = None
        self.running = False
        # 定义室外数据协议帧头和帧尾
        self.FRAME_HEADER = "SS"
        self.FRAME_TAIL = "PP"
        
    def run(self):
        # 初始化串口
        try:
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=self.timeout)
            print(f"串口初始化成功! 端口：{self.port}，波特率：{self.baud_rate}")
            print("开始接收传感器数据...")
            self.running = True
            
            while self.running:
                # 检查是否有数据可读
                if self.ser.inWaiting() > 0:
                    # 读取一行数据（Arduino用Serial.println发送，末尾带换行符）
                    try:
                        line = self.ser.readline().decode('utf-8').strip()
                        
                        # 跳过空行
                        if not line:
                            continue

                        # 尝试解析JSON格式数据
                        try:
                            json_data = json.loads(line)
                            # 检查是否为WiFi相关事件
                            if isinstance(json_data, dict) and 'event' in json_data:
                                event = json_data['event']
                                if event == 'wifi_get':                                       
                                    # 处理控制命令事件
                                        # 初始化实例变量
                                        
                                        if not hasattr(self, 'wifi_set'):
                                            self.wifi_set = False
                                        
                                        # 获取当前WiFi信息
                                        # ssid, password = get_current_wifi_info()
                                        ssid, password = get_current_wifi_info()

                                        # 将WiFi信息组成JSON数据包
                                        wifi_info = {
                                            "ssid": str(ssid),
                                            "password": str(password),
                                        }
                                        # 转换为JSON字符串
                                        json_data = json.dumps(wifi_info)
                                        
                                        # 参考send_control_command函数模式，使用主应用的serial_thread发送WiFi信息
                                        from PyQt5.QtWidgets import QApplication
                                        app = QApplication.instance()
                                        main_app = None
                                        for widget in app.topLevelWidgets():
                                            if hasattr(widget, 'serial_thread'):
                                                main_app = widget
                                                break
                                        
                                        if main_app:
                                            main_app.pause_other_data = True
                                            try:
                                                if main_app.serial_thread and main_app.serial_thread.ser and main_app.serial_thread.ser.is_open:
                                                    if self.wifi_set is False:
                                                    # 发送WiFi信息
                                                        print(f"[{time.strftime('%H:%M:%S')}] 要发送的WiFi信息: {self.wifi_set}")
                                                        main_app.serial_thread.ser.write((json_data + "\n").encode('utf-8'))
                                                        print(f"[{time.strftime('%H:%M:%S')}] 已通过SERIAL_PORT串口发送WiFi信息")
                                                else:
                                                    print(f"[{time.strftime('%H:%M:%S')}] SERIAL_PORT串口未打开，无法发送WiFi信息")
                                            except Exception as e:
                                                print(f"[{time.strftime('%H:%M:%S')}] 通过SERIAL_PORT发送WiFi信息时出错: {e}")
                                            finally:
                                                main_app.pause_other_data = False
                                                
                                        else:
                                            print(f"[{time.strftime('%H:%M:%S')}] 无法找到主应用实例，无法通过SERIAL_PORT发送WiFi信息")
                                elif event == 'wifi_set':
                                    self.wifi_set = True
                                    self.wifi_event_received.emit(event)
                                    print(f"[{time.strftime('%H:%M:%S')}] WiFi设置已完成: {self.wifi_set}")
                                else:
                                    print(f"[{time.strftime('%H:%M:%S')}] 未知事件类型: {event}")
                        except json.JSONDecodeError:
                            # 不是JSON格式或解析失败，继续处理其他格式
                            pass

                        # 按逗号拆分数据
                        data_parts = line.split(',')
                        
                        
                        # 判断数据是否为5个字段（土壤传感器数据格式）
                        # 4,25.6,23.5,234,6.8 (5,6)
                        if len(data_parts) == 5:
                            try:
                                # 解析每个字段
                                device_id = int(data_parts[0])    # 设备ID（区分机器）
                                soil_temp = float(data_parts[1])     # 土壤温度（℃）
                                soil_moisture = float(data_parts[2])  # 土壤水分（%）

                                
                                    
                                soil_ec = float(data_parts[3])       # 土壤电导率（μS/cm）
                                soil_ph = float(data_parts[4])       # 土壤PH值
                                 
                                # 解析继电器状态（第6个字段，如果存在则解析，否则默认为0）
                                relay_state = int(data_parts[5]) if len(data_parts) == 6 else 0

                                # 处理传感器读取错误的情况（Arduino错误时返回-1）
                                if soil_moisture < 0 or soil_temp < 0 or soil_ec < 0 or soil_ph < 0:
                                    print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id} | 传感器读取错误")
                                    print(f"  原始数据：{line}")
                                    continue
                                if device_id in [4,5,6]:
                                # 打印接收到的数据
                                    print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id} 数据：温度={soil_temp}℃, 湿度={soil_moisture}%, EC={soil_ec}μS/cm, PH={soil_ph}")
                                else:
                                    print(f"[{time.strftime('%H:%M:%S')}] 设备ID不匹配土壤传感器设备：{device_id}")
                                    continue
                                # 发送信号到主线程
                                self.data_received.emit(device_id, soil_temp, soil_moisture, soil_ec, soil_ph, relay_state)

                            except ValueError:
                                print(f"[{time.strftime('%H:%M:%S')}] 数据格式错误（非数字）：{line}")
                        # 判断数据是否为2个字段（水箱数据格式：设备码,水位数据）
                        # 10,1 11,0
                        elif len(data_parts) == 2:
                            try:
                                # 解析每个字段
                                device_id = int(data_parts[0])    # 设备ID（水箱设备）
                                water_tank_state = int(data_parts[1])  # 水箱状态
                                if device_id in [10,11]:
                                    # 打印接收到的数据
                                    print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id} 水箱数据：{'低水位' if water_tank_state == 1 else '高水位'}")
                                else:
                                    print(f"[{time.strftime('%H:%M:%S')}] 设备ID不匹配水箱设备：{device_id}")
                                    continue
                                # 发送信号到主线程
                                self.water_tank_data_received.emit(device_id, water_tank_state)

                            except ValueError:
                                print(f"[{time.strftime('%H:%M:%S')}] 水箱数据格式错误（非数字）：{line}")
                        # 判断数据是否为4个字段（水培柜数据格式：设备号,ph值,水温,液位状态）
                        # 12,7.0,25.0,1 (13,7,15,0) (14,8,47,1)
                        elif len(data_parts) == 4:
                            try:
                                # 解析每个字段
                                device_id = int(data_parts[0])    # 设备ID（水培柜设备为12、13、14）
                                ph_value = float(data_parts[1])   # pH值
                                water_temp = float(data_parts[2]) # 水温
                                water_level = int(data_parts[3])  # 液位状态（0=充足，1=缺水）
                                  
                                # 检查是否为水培柜设备（设备ID为12、13或14）
                                if device_id in [12, 13, 14]:
                                    # 打印接收到的数据
                                    print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id} 水培柜数据：pH={ph_value}，水温={water_temp}℃，液位={'充足' if water_level == 0 else '缺水'}")
                                    
                                    # 发送信号到主线程
                                    self.hydroponic_data_received.emit(device_id, ph_value, water_temp, water_level)
                                else:
                                    print(f"[{time.strftime('%H:%M:%S')}] 设备ID不匹配水培柜设备：{device_id}")
                                  
                            except ValueError:
                                print(f"[{time.strftime('%H:%M:%S')}] 水培柜数据格式错误（非数字）：{line}")
                        # 判断数据是否为6个字段（室内环境传感器数据格式：设备号,温度,湿度,pm2.5,光照强度,紫外线强度）
                        # 8,10.5,81,100.9,3589.2,5
                        elif len(data_parts) == 6:
                            try:
                                # 解析每个字段
                                device_id = int(data_parts[0])    # 设备ID（室内环境传感器）
                                temperature = float(data_parts[1]) # 温度（℃）
                                humidity = float(data_parts[2])    # 湿度（%）
                                pm25 = float(data_parts[3])        # PM2.5（μg/m³）
                                light = float(data_parts[4])       # 光照强度（lux）
                                uv = float(data_parts[5])          # 紫外线强度（μW/cm²）
                                if device_id == 15:
                                # 打印接收到的数据
                                    print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id} 室内环境数据：温度={temperature}℃, 湿度={humidity}%, PM2.5={pm25}μg/m³, 光照={light}lux, 紫外线={uv}μW/cm²")
                                else:
                                    print(f"[{time.strftime('%H:%M:%S')}] 设备ID不匹配室内环境传感器设备：{device_id}")
                                    continue
                                # 发送信号到主线程
                            
                                self.indoor_env_data_received.emit(device_id, temperature, humidity, pm25, light, uv)
                                
                            except ValueError:
                                print(f"[{time.strftime('%H:%M:%S')}] 室内环境数据格式错误（非数字）：{line}")

                        # 检查是否为室外数据格式：以SS开头，以PP结尾
                        elif line.startswith(self.FRAME_HEADER) and line.endswith(self.FRAME_TAIL):
                            # 去掉帧头和帧尾
                            data_content = line[len(self.FRAME_HEADER):-len(self.FRAME_TAIL)].strip()
                            # 按逗号拆分数据
                            data_parts = data_content.split(',')
                            
                            if len(data_parts) >= 16:  # 确保有足够的数据元素
                                try:
                                    # 解析数据 - 跳过第一个元素'SS'
                                    outdoor_data = {
                                        'area1': {
                                            'device_id': int(data_parts[1]),
                                            'temp': float(data_parts[2]),
                                            'humidity': float(data_parts[3]),
                                            'ph': float(data_parts[4]),
                                            'ec': float(data_parts[5]),
                                            'relay_state': int(data_parts[6])
                                        },
                                        'area2': {
                                            'device_id': int(data_parts[7]),
                                            'temp': float(data_parts[8]),
                                            'humidity': float(data_parts[9]),
                                            'ph': float(data_parts[10]),
                                            'ec': float(data_parts[11]),
                                            'relay_state': int(data_parts[12])
                                        },
                                        'water_tank': {
                                            'device_id': int(data_parts[13]),
                                            'state': int(data_parts[14])
                                        }
                                    }
                                    
                                    # 打印接收到的室外数据
                                    print(f"[{time.strftime('%H:%M:%S')}] 接收到室外数据:")
                                    print(f"  区域1: 温度={outdoor_data['area1']['temp']}℃, 湿度={outdoor_data['area1']['humidity']}%, "
                                          f"pH={outdoor_data['area1']['ph']}, EC={outdoor_data['area1']['ec']}μS/cm, 继电器={outdoor_data['area1']['relay_state']}")
                                    print(f"  区域2: 温度={outdoor_data['area2']['temp']}℃, 湿度={outdoor_data['area2']['humidity']}%, "
                                          f"pH={outdoor_data['area2']['ph']}, EC={outdoor_data['area2']['ec']}μS/cm, 继电器={outdoor_data['area2']['relay_state']}")
                                    print(f"  水箱: 状态={outdoor_data['water_tank']['state']}")
                                    
                                    # 发送信号到主线程
                                    self.outdoor_data_received.emit(outdoor_data)
                                    
                                except ValueError:
                                    print(f"[{time.strftime('%H:%M:%S')}] 室外数据格式错误（非数字）：{line}")
                    except UnicodeDecodeError:
                        print(f"[{time.strftime('%H:%M:%S')}] 数据解码错误")

                # 每秒检查10次数据，避免占用过多CPU资源
                self.msleep(150)
                
        except Exception as e:
            print(f"串口初始化失败! 原因：{e}")
            print("提示:1. 检查端口是否正确; 2. 确认Arduino已连接; 3. 关闭占用串口的程序")
        
    def stop(self):
        self.running = False
        self.wait()
        if self.ser and self.ser.isOpen():
            self.ser.close()
            print("串口已关闭")
    
class BackgroundImageApp(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("main.ui", self)  # 加载UI文件
        
        self.setWindowTitle('图片背景演示')

        self.set_background_image()  # 设置背景图片
        self.init_time_display()
        self.init_all_labels()  # 初始化所有标签
        self.init_gauges()  # 初始化仪表盘
        self.load_image_to_label()
        # 初始化模式状态（默认手动模式）
        self.is_auto_mode = False
        
        # 添加标志变量，用于控制是否暂停其他数据接收
        self.pause_other_data = False
        # 添加标志变量，用于控制是否允许发送问询帧
        self.allow_inquiry = True  # 默认为True，表示允许发送问询帧
        
        # 初始化串口接收线程
        self.init_serial()
        
        # 初始化定时器，用于持续发送询问帧
        self.init_inquiry_timer()
        
        # 已移除模拟数据生成，只使用串口接收的数据
        # self.init_sensor_test()
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.check_internet_connection)
        self.time_timer.start(3000)  # 3000毫秒 = 3秒

        # 启动问询小智是否联网的定时器
        self.xiaozhi_timer = QTimer(self)
        self.xiaozhi_timer.timeout.connect(self.ask_xiaozhi_network)
        self.xiaozhi_timer.start(30000)  # 30000毫秒 = 30秒
        print("问询小智定时器已启动，每30秒发送一次问询")
        # 初始化数据保存相关变量
        self.spray1_state = 0  # 1号喷淋系统状态，0表示关闭，1表示打开
        self.spray2_state = 0  # 2号喷淋系统状态，0表示关闭，1表示打开
        
        # 创建存储三个设备的传感器数据数组
        self.devices_data = [
            {   # 室内设备一
                'device_id': 4,
                'soil_moisture': 0.0,
                'soil_temp': 0.0,
                'soil_ec': 0.0,
                'soil_ph': 0.0,
                'relay_state': 0
            },
            {   # 室内设备二
                'device_id': 5,
                'soil_moisture': 0.0,
                'soil_temp': 0.0,
                'soil_ec': 0.0,
                'soil_ph': 0.0,
                'relay_state': 0
            },
            {   # 室内设备三
                'device_id': 6,
                'soil_moisture': 0.0,
                'soil_temp': 0.0,
                'soil_ec': 0.0,
                'soil_ph': 0.0,
                'relay_state': 0
            },
        ]
        
        # 创建水培柜设备数据存储结构
        self.hydroponic_data = {
            12: {'ph_value': 0.0, 'water_temp': 0.0, 'water_level': 0},
            13: {'ph_value': 0.0, 'water_temp': 0.0, 'water_level': 0},
            14: {'ph_value': 0.0, 'water_temp': 0.0, 'water_level': 0}
        }
        self.waterbox_data = {
            
            10: {'water_tank_state': 0, 'device_id': 10},
            11: {'water_tank_state': 0, 'device_id': 11}
        }
        
        # 创建室内环境传感器数据存储结构
        self.indoor_env_data = {
            # 可以根据实际设备ID添加对应的初始数据
            15: {'temperature': 0.0, 'humidity': 0.0, 'pm25': 0.0, 'light': 0.0, 'uv': 0.0}
        }
        # 创建数据保存文件夹
        self.create_data_folders()
        
        self.showFullScreen()  # 全屏显示（按需开启）
        
        # 添加键盘事件来切换模式（仅作示例）
        self.setFocusPolicy(Qt.StrongFocus)
    def ask_xiaozhi_network(self):
        """问询小智是否联网，发送{\"event\":\"ask\"}"""
        
        try:
            # 构建问询JSON数据
            ask_data = {"event": "ask"}
            ask_json_str = json.dumps(ask_data) + '\n'
            
            # 检查serial_thread是否存在并可用
            if hasattr(self, 'serial_thread') and self.serial_thread is not None and hasattr(self.serial_thread, 'ser') and self.serial_thread.ser is not None and self.serial_thread.ser.is_open:
                # 通过serial_thread.ser发送数据
                self.serial_thread.ser.write(ask_json_str.encode('utf-8'))
                self.serial_thread.ser.flush()  # 确保数据被发送
                self.init_label(self.wifi, "小智未连接", "gray")
                print(f"已发送问询: {ask_json_str.strip()}")
            else:
                print("serial_thread未初始化或串口未打开，无法发送问询")
                
        except Exception as e:
            print(f"发送问询时出错: {str(e)}")

    def check_internet_connection(self):
        """判断树莓派是否联上网络
        
        Returns:
            bool: True表示已联网，False表示未联网
        """
        try:
            # 使用ping命令检查是否能连接到Google DNS服务器
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
            # 打印命令输出（调试用）
 
   
            if result.returncode == 0:
                self.Load_pic(self.wifi_status, WIFI_ON_IMAGE)
          
            else:
                self.Load_pic(self.wifi_status, WIFI_OFF_IMAGE)
           
            # 如果返回码为0，表示ping成功，已联网
             
        except Exception as e:
            print(f"检查网络连接时出错: {str(e)}")
      
    def init_inquiry_timer(self):
        """
        初始化询问帧发送定时器
        定时检查并发送询问帧，避免与其他指令冲突
        """
        # 导入QtCore的QTimer
        from PyQt5.QtCore import QTimer
        
        # 创建定时器
        self.inquiry_timer = QTimer(self)
        
        # 连接定时器超时信号到发送询问帧的槽函数
        self.inquiry_timer.timeout.connect(self.check_and_send_inquiry)
        
        # 设置定时器间隔（毫秒），使用全局定义的间隔时间
        self.inquiry_interval = INQUIRY_INTERVAL
        
        # 启动定时器
        self.inquiry_timer.start(self.inquiry_interval)
        print("询问帧发送定时器已启动，间隔时间：{}秒".format(self.inquiry_interval / 1000))
        
    def check_and_send_inquiry(self):
        """
        检查是否可以发送询问帧，并在条件允许时发送
        仅当没有其他指令发送时才发送询问帧
        """
        # 检查是否正在发送其他指令（通过检查pause_other_data标志）
        if self.pause_other_data:
            # 如果正在发送其他指令，则不发送询问帧
            print("当前正在发送其他指令，跳过询问帧发送")
            return
        
        # 检查是否允许发送询问帧
        if not self.allow_inquiry:
            # 如果不允许发送询问帧，则跳过
            # print("询问帧发送已被禁止，跳过发送操作")
            return
        
        # 发送询问帧
        try:
            print("开始发送设备询问帧...")
            self.send_inquiry_frames_to_devices()
        except Exception as e:
            print(f"发送询问帧时出错: {str(e)}")
            
    def keyPressEvent(self, event):
        """键盘事件处理 - 仅作演示用"""
        if event.key() == Qt.Key_Escape:
            self.showNormal()  # 恢复到正常窗口模式
            print("已退出全屏显示")

    def send_inquiry_frames_to_devices(self):
        """
        依次向指定设备发送问询帧
        设备列表: [4, 5, 6, 12, 13, 14, 15]
        
        返回:
            bool: 全部发送完成返回True
        """
        # 检查是否允许发送问询帧
        if not self.allow_inquiry:
            print(f"[{time.strftime('%H:%M:%S')}] 问询帧发送已被禁止，跳过发送操作")
            return False
        
        # 检查是否已经有问询过程在进行中
        if hasattr(self, 'is_inquiry_running') and self.is_inquiry_running:
            print(f"[{time.strftime('%H:%M:%S')}] 已有问询过程在进行中，跳过新的问询")
            return False
        
        # 设置标志，表示问询过程开始
        self.is_inquiry_running = True
        
        # 定义需要问询的设备ID列表
        self.device_list = [1,4, 5, 6,10,11, 12, 13, 14, 15]
        self.current_device_index = 0
        
        # 开始定时器方式发送问询帧
        self.send_next_inquiry_frame()
        return True
    
    def send_next_inquiry_frame(self):
        """
        使用定时器机制依次发送问询帧
        """
        try:
            # 检查是否还有设备需要发送
            if self.current_device_index < len(self.device_list):
                device_id = self.device_list[self.current_device_index]
                
                # 调用send_inquiry_frame函数发送问询帧
                success = self.send_inquiry_frame(device_id)
                
                # 输出发送结果
                if success:
                    print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id}问询帧发送成功")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id}问询帧发送失败")
                
                # 更新索引，准备发送下一个设备
                self.current_device_index += 1
                
                # 设置INQUIRY_INTERVAL毫秒后继续发送下一个设备的问询帧
                QTimer.singleShot(INQUIRY_INTERVAL, self.send_next_inquiry_frame)
            else:
                # 所有设备问询完成，重置标志
                print(f"[{time.strftime('%H:%M:%S')}] 所有设备问询帧发送完成")
                self.is_inquiry_running = False
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] 发送问询帧时出错: {str(e)}")
            # 出错时也重置标志，避免一直阻塞
            self.is_inquiry_running = False

   
        
    def send_inquiry_frame(self, device_id):
        """
        发送问询帧到指定设备，设备收到后会发送传感器数据
        问询帧格式: B0 设备号 (十六进制)
        
        参数:
            device_id: 设备ID (整数)
            
        返回:
            bool: 发送成功返回True,否则返回False
        """
        try:
            # 验证设备ID是否为有效的整数
            if not isinstance(device_id, int) or device_id < 0 or device_id > 255:
                print(f"[{time.strftime('%H:%M:%S')}] 无效的设备ID: {device_id},设备ID应为0-255之间的整数")
                return False
            
            # 构造问询帧 (B0 + 设备号)
            raw_packet = bytes([0xB0, device_id])
            
            # 检查串口是否可用
            if not (self.serial_thread and self.serial_thread.ser and self.serial_thread.ser.isOpen()):
                # print(f"[{time.strftime('%H:%M:%S')}] 串口未初始化或已关闭，无法发送问询帧")
                return False
            
            # 发送问询帧
            self.serial_thread.ser.write(raw_packet)
            # print(f"[{time.strftime('%H:%M:%S')}] 已发送问询帧到设备{device_id}: B0 {device_id}")
            
            return True
            
        except Exception as e:
            # print(f"[{time.strftime('%H:%M:%S')}] 发送问询帧失败: {str(e)}")
            return False     
    def handle_wifi_event(self, event):
        """
        处理从小智线程接收到的WiFi事件
        
        Args:
            event: WiFi事件类型（如"connect"）
        """
        self.init_label(self.wifi, "小智已连接", "white")
    def init_serial(self):
        """初始化串口接收线程"""
        # 创建传感器数据串口接收线程
        self.serial_thread = SerialReceiveThread(SERIAL_PORT, BAUD_RATE, TIMEOUT)
        # 连接信号和槽
        self.serial_thread.data_received.connect(self.handle_serial_data)
        self.serial_thread.water_tank_data_received.connect(self.handle_water_tank_data)
        self.serial_thread.hydroponic_data_received.connect(self.handle_hydroponic_data)
        self.serial_thread.indoor_env_data_received.connect(self.handle_indoor_env_data)
        # 添加室外数据接收信号连接
        self.serial_thread.outdoor_data_received.connect(self.handle_outdoor_data)
        # 添加WiFi事件接收信号连接
        self.serial_thread.wifi_event_received.connect(self.handle_wifi_event)
        # 启动线程
        self.serial_thread.start()

        # 初始化小智线程
        self.xiaozhi_thread = XiaoZhiThread(XIAOZHI_SERIAL_PORT, XIAOZHI_BAUD_RATE, XIAOZHI_TIMEOUT)
        # 连接信号
        self.xiaozhi_thread.json_data_received.connect(self.handle_xiaozhi_data)
        # 连接图片更新信号
        self.xiaozhi_thread.update_image_signal.connect(self.handle_image_update)
        # 启动线程
        self.xiaozhi_thread.start()    
    
    def handle_xiaozhi_data(self, json_data):
        """
        处理从小智线程接收到的JSON数据
        
        Args:
            json_data: 解析后的JSON对象数据
        """
        try:
            print(f"[{time.strftime('%H:%M:%S')}] 主线程收到小智数据: {json_data}")
            
            # 根据事件类型处理数据
            if 'event' in json_data:
                event = json_data['event']
                
                # 这里可以根据需要添加更多事件处理逻辑
                # 例如更新UI、存储数据等
                
                # 示例：处理聊天消息
                if event == 'chat_message':
                    message = json_data['content']
                    # 可以在这里更新聊天界面或处理消息
                    print(f"[{time.strftime('%H:%M:%S')}] 收到聊天消息: {message}")
                    
                # 示例：处理设备状态更新
                elif event in ['spray_system', 'fertilizer_system', 'soil_light', 'hydro_light','auto_control']:
                    device_id = json_data.get('device_id')
                    state = json_data.get('state')
                    print(f"[{time.strftime('%H:%M:%S')}] 设备状态更新 - 事件: {event}, 设备ID: {device_id}, 状态: {state}")
                    # 可以在这里更新UI上的设备状态显示
                    
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] 处理小智数据时出错: {e}")
            
    def handle_hydroponic_data(self, device_id, ph_value, water_temp, water_level):
        """处理接收到的水培柜数据"""
        # 检查是否暂停其他数据接收
        if self.pause_other_data:
            return
        
        # 更新水培柜数据存储
        if device_id in self.hydroponic_data:
            self.hydroponic_data[device_id]['ph_value'] = ph_value
            self.hydroponic_data[device_id]['water_temp'] = water_temp
            self.hydroponic_data[device_id]['water_level'] = water_level  # 更新液位状态
            
            # 调用保存水培柜数据的函数
            self.save_hydroponic_data(device_id, ph_value, water_temp, water_level)
            
            # 尝试更新UI上对应的标签（如果存在）
            try:
                # 根据设备ID更新对应的pH值和水温标签
                if device_id == 12:
                    if hasattr(self, 'spph1'):
                        self.spph1.setText(f"{ph_value:.1f}")
                    if hasattr(self, 'sptmp1'):
                        self.sptmp1.setText(f"{water_temp:.1f}℃")                        
                        self.sptmp1.setText(f"{water_temp:.1f}℃")
                elif device_id == 13:
                    if hasattr(self, 'spph2'):
                        self.spph2.setText(f"{ph_value:.1f}")
                    if hasattr(self, 'sptmp2'):
                        self.sptmp2.setText(f"{water_temp:.1f}℃")
                elif device_id == 14:
                    if hasattr(self, 'spph3'):
                        self.spph3.setText(f"{ph_value:.1f}")
                    if hasattr(self, 'sptmp3'):
                        self.sptmp3.setText(f"{water_temp:.1f}℃")
                
                # 打印更新信息
                print(f"[{time.strftime('%H:%M:%S')}] 水培柜设备{device_id}数据更新: pH={ph_value:.1f}, 水温={water_temp:.1f}℃, 液位={'充足' if water_level == 1 else '缺水'}")
            except Exception as e:
                print(f"更新水培柜设备{device_id}数据时出错: {str(e)}")
    
    def handle_indoor_env_data(self, device_id, temperature, humidity, pm25, light, uv):
        """处理接收到的室内环境传感器数据"""
        global global_auto_light, global_auto_light1
        # 检查是否暂停其他数据接收
        if self.pause_other_data:
            return
        
        try:
            # 添加类型检查和转换，确保所有值都是数值类型
            device_id = int(device_id)
            temperature = float(temperature)
            humidity = float(humidity)
            pm25 = float(pm25)
            light = float(light)
            uv = float(uv)
            
            # 初始化新设备的数据结构（如果设备ID不存在）
            if device_id not in self.indoor_env_data:
                self.indoor_env_data[device_id] = {
                    'temperature': 0.0,
                    'humidity': 0.0,
                    'pm25': 0.0,
                    'light': 0.0,
                    'uv': 0.0
                }
            print(f"[{time.strftime('%H:%M:%S')}] 室内环境数据更新 - 设备ID:{global_auto_light} or {global_auto_light1}")
            # 更新室内环境数据
            if global_auto_light==True or global_auto_light1==True:
                if light>2000:
                    # 确保对象存在再调用
                        send_control_command( 0x57 ,0x00, 0x01)
                        print('打开自动补光')
                        self.Load_pic(self.light1, LIGHT_ON_IMAGE)     
                        self.Load_pic(self.light1_off, ON_IMAGE)

                        self.Load_pic(self.light2, LIGHT_ON_IMAGE)     
                        self.Load_pic(self.light2_off, ON_IMAGE)

                        self.Load_pic(self.light3, LIGHT_ON_IMAGE)     
                        self.Load_pic(self.light3_off, ON_IMAGE)

                        self.Load_pic(self.light4, LIGHT_ON_IMAGE)     
                        self.Load_pic(self.light4_off, ON_IMAGE)

                        self.Load_pic(self.light5, LIGHT_ON_IMAGE)     
                        self.Load_pic(self.light5_off, ON_IMAGE)

                        self.Load_pic(self.light6, LIGHT_ON_IMAGE)     
                        self.Load_pic(self.light6_off, ON_IMAGE)
                else:
                        print('关闭补光')
                        send_control_command( 0x57 ,0x00, 0x00)
                        self.Load_pic(self.light1, LIGHT_OFF_IMAGE)     
                        self.Load_pic(self.light1_off, OFF_IMAGE)

                        self.Load_pic(self.light2, LIGHT_OFF_IMAGE)     
                        self.Load_pic(self.light2_off, OFF_IMAGE)

                        self.Load_pic(self.light3, LIGHT_OFF_IMAGE)     
                        self.Load_pic(self.light3_off, OFF_IMAGE)

                        self.Load_pic(self.light4, LIGHT_OFF_IMAGE)     
                        self.Load_pic(self.light4_off, OFF_IMAGE)

                        self.Load_pic(self.light5, LIGHT_OFF_IMAGE)     
                        self.Load_pic(self.light5_off, OFF_IMAGE)

                        self.Load_pic(self.light6, LIGHT_OFF_IMAGE)     
                        self.Load_pic(self.light6_off, OFF_IMAGE)
            self.indoor_env_data[device_id]['temperature'] = temperature
            # 更新室内温度标签数据
            if hasattr(self, 'indoor_tmp'):
                self.indoor_tmp.setText(f"{temperature:.1f}℃")
            if hasattr(self,  'temp6_gauge'):
               self.temp6_gauge.setValue(temperature)
            self.indoor_env_data[device_id]['humidity'] = humidity
            # 更新室内湿度标签数据
            if hasattr(self, 'indoor_hum'):
                self.indoor_hum.setText(f"{humidity:.1f}%")
            if hasattr(self, 'hum6_gauge'):
                self.hum6_gauge.setValue(humidity)
            self.indoor_env_data[device_id]['pm25'] = pm25
            # 更新室内PM2.5标签数据
            if hasattr(self, 'indoor_PM25'):
                self.indoor_PM25.setText(f"{pm25:.1f}")
            if hasattr(self, 'pm25_gauge'):
                self.pm25_gauge.setValue(pm25)
            self.indoor_env_data[device_id]['light'] = light
            # 更新室内光照标签数据
            if hasattr(self, 'indoor_light'):
                if light > 2047:
                    self.indoor_light.setText("弱")
                else:
                    self.indoor_light.setText("强")
                
            if hasattr(self, 'light_gauge') and light <= 4095:  # 确保光照值有效
                self.light_gauge.setValue(4095-light)
            self.indoor_env_data[device_id]['uv'] = uv
            if hasattr(self, 'indoor_uv'):
                self.indoor_uv.setText(f"{uv:.1f}")
            if hasattr(self, 'UV_gauge'):
                self.UV_gauge.setValue(uv)
            

            # 调用保存室内环境数据的函数，添加异常捕获
            try:
                self.save_indoor_env_data(device_id, temperature, humidity, pm25, light, uv)
            except Exception as save_error:
                print(f"保存室内环境数据时出错: {str(save_error)}")
            
              
        except Exception as e:
            print(f"处理室内环境数据时出错: {str(e)}")
            # 打印更详细的错误信息，包括数据类型
            print(f"数据类型检查 - device_id: {type(device_id)}, temperature: {type(temperature)}, "
                  f"humidity: {type(humidity)}, pm25: {type(pm25)}, light: {type(light)}, uv: {type(uv)}")
    
    def handle_water_tank_data(self, device_id, water_tank_state):
        """处理接收到的水箱数据"""
        
        # 检查是否暂停其他数据接收
        if self.pause_other_data:
            return
        
        if device_id == 10:  # 主水箱设备
            # 更新waterbox_data中对应设备的数据
            if device_id in self.waterbox_data:
                self.waterbox_data[device_id]['water_tank_state'] = water_tank_state
            
            # 水箱状态：1表示水位低，0表示水位正常
            if water_tank_state == 1:
                self.sw1.setText("缺水")
                self.sw1.setStyleSheet("color: red;")
                print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id} 水箱状态：缺水")
            else:
                self.sw1.setText("水位正常")
                self.sw1.setStyleSheet("color: cyan;")
                print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id} 水箱状态：正常")
        elif device_id == 11:  # 额外水箱设备1
            # 更新waterbox_data中对应设备的数据
            if device_id in self.waterbox_data:
                self.waterbox_data[device_id]['water_tank_state'] = water_tank_state
            
            # 水箱状态：1表示水位低，0表示水位正常
            if water_tank_state == 1:
                self.sw2.setText("缺水")
                self.sw2.setStyleSheet("color: red;")
                print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id} 水箱状态：缺水")
            else:
                self.sw2.setText("水位正常")
                self.sw2.setStyleSheet("color: cyan;")
                print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id} 水箱状态：正常")
                
    def handle_outdoor_data(self, outdoor_data):
        """处理接收到的室外数据"""
        # 检查是否暂停其他数据接收
        # SS,1,30,30,30,10000,1,2,10,30,30,10000,1,3,1,PP   测试数据
        if self.pause_other_data:
            return
        
        try:
            # 提取室外的区域1和区域2数据
            area1_data = outdoor_data.get('area1', {})
            area2_data = outdoor_data.get('area2', {})
            
            # 更新室外区域1的数据
            if area1_data:
                # 这里可以根据需要更新UI或保存数据
                print(f"处理室外区域1数据: 设备ID={area1_data.get('device_id')}, 温度={area1_data.get('temp')}, "
                      f"湿度={area1_data.get('humidity')}, pH={area1_data.get('ph')}, EC={area1_data.get('ec')}, "
                      f"继电器状态={area1_data.get('relay_state')}")
                
                # 更新区域1的仪表盘数据
                if hasattr(self, 'temp1_gauge'):
                    self.temp1_gauge.setValue(float(area1_data.get('temp', 0.0)))
                if hasattr(self,'tmp1'):
                    self.tmp1.setText(str(area1_data.get('temp', 0.0))+'℃')

                if hasattr(self, 'hum1_gauge'):
                    self.hum1_gauge.setValue(float(area1_data.get('humidity', 0.0)))
                    if hasattr(self,'hum1'):
                        self.hum1.setText(str(area1_data.get('humidity', 0.0))+'%')
                if hasattr(self, 'ph1_gauge'):
                    self.ph1_gauge.setValue(float(area1_data.get('ph', 0.0)))
                    if hasattr(self,'ph1'):
                        self.ph1.setText(str(area1_data.get('ph', 0.0)))
                if hasattr(self, 'ele1_gauge'):
                    self.ele1_gauge.setValue(float(area1_data.get('ec', 0.0)))
                    if hasattr(self,'ele1'):
                        self.ele1.setText(str(area1_data.get('ec', 0)))

            # 更新室外区域2的数据
            if area2_data:
                # 这里可以根据需要更新UI或保存数据
                print(f"处理室外区域2数据: 设备ID={area2_data.get('device_id')}, 温度={area2_data.get('temp')}, "
                      f"湿度={area2_data.get('humidity')}, pH={area2_data.get('ph')}, EC={area2_data.get('ec')}, "
                      f"继电器状态={area2_data.get('relay_state')}")
                
                # 更新区域2的仪表盘数据
                if hasattr(self, 'temp2_gauge'):
                    self.temp2_gauge.setValue(float(area2_data.get('temp', 0.0)))
                    if hasattr(self,'tmp2'):
                        self.tmp2.setText(str(area2_data.get('temp', 0.0))+'℃')
                if hasattr(self, 'hum2_gauge'):
                    self.hum2_gauge.setValue(float(area2_data.get('humidity', 0.0)))
                    if hasattr(self,'hum2'):
                        self.hum2.setText(str(area2_data.get('humidity', 0.0))+'%')
                if hasattr(self, 'ph2_gauge'):
                    self.ph2_gauge.setValue(float(area2_data.get('ph', 0.0)))
                    if hasattr(self,'ph2'):
                        self.ph2.setText(str(area2_data.get('ph', 0.0)))
                if hasattr(self, 'ele2_gauge'):
                    self.ele2_gauge.setValue(float(area2_data.get('ec')))
                    if hasattr(self,'ele2'):
                        self.ele2.setText(str(int(area2_data.get('ec'))))        
        except Exception as e:
            print(f"处理室外数据时出错: {str(e)}")
                        
    def handle_serial_data(self, device_id, soil_temp, soil_moisture, soil_ec, soil_ph, relay_state):
        """处理接收到的串口数据"""
        # 检查是否暂停其他数据接收
        if self.pause_other_data:
            return
        
        # 更新devices_data数组中对应设备的数据
        for device in self.devices_data:
            if device['device_id'] == device_id:
                device['soil_temp'] = soil_temp
                device['soil_moisture'] = soil_moisture
                device['soil_ec'] = soil_ec
                device['soil_ph'] = soil_ph
                device['relay_state'] = relay_state
                break       
        # 根据设备ID更新对应的传感器数据
        if device_id == 4:            
            # 更新第一个区域的传感器数据（设备4对应区域1）
            if hasattr(self, 'temp3_gauge'):
                self.temp3_gauge.setValue(float(soil_temp))
                if hasattr(self,'tmp3'):
                    self.tmp3.setText(str(soil_temp)+'℃')
            if hasattr(self, 'hum3_gauge'):
                self.hum3_gauge.setValue(float(soil_moisture))
                if hasattr(self,'hum3'):
                    self.hum3.setText(str(soil_moisture)+'%')
            if hasattr(self, 'ph3_gauge'):
                self.ph3_gauge.setValue(float(soil_ph))
                if hasattr(self,'ph3'):
                    self.ph3.setText(str(soil_ph))
            if hasattr(self, 'ele3_gauge'):
                self.ele3_gauge.setValue(float(soil_ec))
                if hasattr(self,'ele3'):
                    self.ele3.setText(str(soil_ec))   
            try:
                self.save_sensor_data(device_id, soil_temp, soil_moisture, soil_ph, soil_ec, int(relay_state))
            except Exception as e:
                print(f"保存设备{device_id}数据时出错: {str(e)}")
            print(f"global_auto_sprinkler: {global_auto_sprinkler}")
            if global_auto_sprinkler is True:   
                if float(soil_moisture) < threshold_soil_moisture:                                        
                    # 土壤湿度低于阈值，打开喷淋系统
                    print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id}土壤湿度{soil_moisture}%低于阈值{threshold_soil_moisture}%，自动开启喷淋系统")
                    send_control_command(device_id, 0x00, 0x01) #打开喷淋系统
                    #ui 更新
                    self.Load_pic(self.pl1,OPEN_IMAGE)
                    self.Load_pic(self.pl1_off,ON_IMAGE)
                else:
                    # 土壤湿度高于阈值，关闭喷淋系统
                    print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id}土壤湿度{soil_moisture}%高于阈值{threshold_soil_moisture}%，自动关闭喷淋系统")
                    send_control_command(device_id+3, 0x00, 0x00) #关闭喷淋系统
                    self.Load_pic(self.pl1,DOWN_IMAGE)
                    self.Load_pic(self.pl1_off,OFF_IMAGE)    
            
        elif device_id == 5:
            # 更新第二个区域的传感器数据（设备5对应区域2）
            if hasattr(self, 'temp4_gauge'):
                self.temp4_gauge.setValue(float(soil_temp))
                if hasattr(self,'tmp4'):
                    self.tmp4.setText(str(soil_temp)+'℃')
            if hasattr(self, 'hum4_gauge'):
                self.hum4_gauge.setValue(float(soil_moisture))
                if hasattr(self,'hum4'):
                    self.hum4.setText(str(soil_moisture)+'%')
            if hasattr(self, 'ph4_gauge'):
                self.ph4_gauge.setValue(float(soil_ph))
                if hasattr(self,'ph4'):
                    self.ph4.setText(str(soil_ph))
            if hasattr(self, 'ele4_gauge'):
                self.ele4_gauge.setValue(float(soil_ec))
                if hasattr(self,'ele4'):
                    self.ele4.setText(str(soil_ec))   
            try:
                self.save_sensor_data(device_id, soil_temp, soil_moisture, soil_ph, soil_ec, int(relay_state))
            except Exception as e:
                print(f"保存设备{device_id}数据时出错: {str(e)}")
            # 自动控制逻辑
            if global_auto_sprinkler is True:   
                if float(soil_moisture) < threshold_soil_moisture:                                        
                    # 土壤湿度低于阈值，打开喷淋系统
                    print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id}土壤湿度{soil_moisture}%低于阈值{threshold_soil_moisture}%，自动开启喷淋系统")
                    send_control_command(device_id, 0x00, 0x01) #打开喷淋系统
                    #ui 更新
                    self.Load_pic(self.pl2,OPEN_IMAGE)
                    self.Load_pic(self.pl2_off,ON_IMAGE)
                else:
                    # 土壤湿度高于阈值，关闭喷淋系统
                    print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id}土壤湿度{soil_moisture}%高于阈值{threshold_soil_moisture}%，自动关闭喷淋系统")
                    send_control_command(device_id, 0x00, 0x00) #关闭喷淋系统
                    self.Load_pic(self.pl2,DOWN_IMAGE)
                    self.Load_pic(self.pl2_off,OFF_IMAGE)
                    
        elif device_id == 6:
            # 更新第三个区域的传感器数据（设备6对应区域3）
            if hasattr(self, 'temp5_gauge'):
                self.temp5_gauge.setValue(float(soil_temp))
                if hasattr(self,'tmp5'):
                    self.tmp5.setText(str(soil_temp)+'℃')
            if hasattr(self, 'hum5_gauge'):
                self.hum5_gauge.setValue(float(soil_moisture))
                if hasattr(self,'hum5'):
                    self.hum5.setText(str(soil_moisture)+'%')
            if hasattr(self, 'ph5_gauge'):
                self.ph5_gauge.setValue(float(soil_ph))
                if hasattr(self,'ph5'):
                    self.ph5.setText(str(soil_ph))
            if hasattr(self, 'ele5_gauge'):
                self.ele5_gauge.setValue(float(soil_ec))
                if hasattr(self,'ele5'):
                    self.ele5.setText(str(soil_ec))   
            try:
                self.save_sensor_data(device_id, soil_temp, soil_moisture, soil_ph, soil_ec, int(relay_state))
            except Exception as e:
                print(f"保存设备{device_id}数据时出错: {str(e)}")
            # 自动控制逻辑
            if global_auto_sprinkler is True:
                if float(soil_moisture) < threshold_soil_moisture:
                    print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id}土壤湿度{soil_moisture}%低于阈值{threshold_soil_moisture}%，自动开启喷淋系统")
                    send_control_command(device_id, 0x00, 0x01) #打开喷淋系统
                    #ui 更新
                    self.Load_pic(self.pl3,OPEN_IMAGE)
                    self.Load_pic(self.pl3_off,ON_IMAGE)
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] 设备{device_id}土壤湿度{soil_moisture}%高于阈值{threshold_soil_moisture}%，自动关闭喷淋系统")
                    send_control_command(device_id, 0x00, 0x00) #关闭喷淋系统
                    self.Load_pic(self.pl3,DOWN_IMAGE)
                    self.Load_pic(self.pl3_off,OFF_IMAGE)
                    
    def set_background_image(self):
        # 保持原有的背景图片显示逻辑不变
        image_path = BACKGROUND_IMAGE           
        try:
            pixmap = QPixmap(image_path)
            self.background_label = QLabel(self)
            
            self.image_width = 3840  # 3840，1920
            self.image_height = 2160  # 2160，1080
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
        label.setFont(QFont("SimHei", 20, QFont.Bold))  # 字体、大小、加粗
        label.setStyleSheet(f"color: {color};")  # 文字颜色   
        
        # 设置文字对齐方式
        label.setAlignment(Qt.AlignCenter)        
        # 确保文字显示在背景上方
        label.raise_()
    
    def init_all_labels(self):
        """初始化所有需要的标签"""
        # 假设UI文件中有这些标签：label_hum(湿度), label_tmp(温度), label_pres(气压)
        self.init_label(self.tmp1, "88.8℃")  # 温度初始值
        self.init_label(self.hum1, "88.8%")   # 湿度初始值       
        self.init_label(self.ph1, "88.8")  # ph1初始值
        self.init_label(self.ele1, "88.8")  # 电导率初始值

        self.init_label(self.tmp2, "88.8℃")  # 温度初始值
        self.init_label(self.hum2, "88.8%")   # 湿度初始值       
        self.init_label(self.ph2, "88.8")  # ph1初始值
        self.init_label(self.ele2, "88.8")  # 电导率初始值

        self.init_label(self.tmp3, "88.8℃")  # 温度初始值
        self.init_label(self.hum3, "88.8%")   # 湿度初始值       
        self.init_label(self.ph3, "88.8")  # ph1初始值
        self.init_label(self.ele3, "88.8")  # 电导率初始值

        self.init_label(self.tmp4, "88.8℃")  # 温度初始值
        self.init_label(self.hum4, "88.8%")   # 湿度初始值       
        self.init_label(self.ph4, "88.8")  # ph1初始值
        self.init_label(self.ele4, "88.8")  # 电导率初始值

        self.init_label(self.tmp5, "88.8℃")  # 温度初始值
        self.init_label(self.hum5, "88.8%")   # 湿度初始值       
        self.init_label(self.ph5, "88.8")  # ph1初始值
        self.init_label(self.ele5, "88.8")  # 电导率初始值
        font_size=15
        self.init_label(self.sptmp1, "88.8℃")  # 温度初始值
        self.init_label(self.spph1, "88.8%")   # 湿度初始值
        self.spph1.setFont(QFont("SimHei", font_size, QFont.Bold))
        self.sptmp1.setFont(QFont("SimHei", font_size, QFont.Bold))

        self.init_label(self.sptmp2, "88.8℃")  # ph1初始值
        self.init_label(self.spph2, "88.8")  # 电导率初始值
        self.spph2.setFont(QFont("SimHei", font_size, QFont.Bold))
        self.sptmp2.setFont(QFont("SimHei", font_size, QFont.Bold))

        self.init_label(self.sptmp3, "888℃")  # ph1初始值
        self.init_label(self.spph3, "888")  # 电导率初始值
        self.spph3.setFont(QFont("SimHei", font_size, QFont.Bold))
        self.sptmp3.setFont(QFont("SimHei", font_size, QFont.Bold)) 

        self.init_label(self.sw1, "水位正常","cyan")  # ph1初始值
        self.init_label(self.sw2, "水位正常","cyan")  # 电导率初始值
        #室内环境监测
        self.init_label(self.indoor_tmp, "88℃")  
        self.init_label(self.indoor_hum, "88.8%") 
        self.init_label(self.indoor_PM25, "888")  
        self.init_label(self.indoor_light, "强")  
        self.init_label(self.indoor_uv, "888")   
        self.init_label(self.wifi, "小智未连接", "gray")       


     # 尝试加载图片
   
    def load_image_to_label(self):
   
        image_paths = {
            'open': OPEN_IMAGE,
            'down': DOWN_IMAGE,
            
            'off': OFF_IMAGE,
            'on': ON_IMAGE,
            'off1': OFF_IMAGE,
            
            'on1': ON1_IMAGE,

            'fl_off': FL_OFF_IMAGE,
            'fl_on': FL_ON_IMAGE,
            'feed_off': FEED_OFF_IMAGE,
            'feed_on': FEED_ON_IMAGE,
            'light_off': LIGHT_OFF_IMAGE,
            'light_on': LIGHT_ON_IMAGE,
            'wifi_off': WIFI_OFF_IMAGE,
            'wifi_on': WIFI_ON_IMAGE,
        }
        # 初始化所有图片
        self.Load_pic(self.wifi_status,image_paths['wifi_off'])
        self.Load_pic(self.auto_pl,image_paths['down'])
        self.init_label(self.auto_pl_off, "自动模式","gray")  
        self.Load_pic(self.pl1,image_paths['down'])
        self.Load_pic(self.pl1_off,image_paths['off'])

        self.Load_pic(self.pl2,image_paths['down'])
        self.Load_pic(self.pl2_off,image_paths['off'])

        self.Load_pic(self.pl3,image_paths['down'])
        self.Load_pic(self.pl3_off,image_paths['off'])
        # 加载室内喂食系统图片
        self.Load_pic(self.feed1,image_paths['feed_off'])
        self.Load_pic(self.feed1_off,image_paths['off'])

        self.Load_pic(self.feed2,image_paths['feed_off'])
        self.Load_pic(self.feed2_off,image_paths['off'])

        self.Load_pic(self.feed3,image_paths['feed_off'])
        self.Load_pic(self.feed3_off,image_paths['off'])
        # 加载室内补光系统图片
        self.Load_pic(self.auto_light,image_paths['light_off'])
        self.init_label(self.auto_light_off, "自动模式","gray")  

        self.Load_pic(self.light1,image_paths['light_off'])
        self.Load_pic(self.light1_off,image_paths['off'])

        self.Load_pic(self.light2,image_paths['light_off'])
        self.Load_pic(self.light2_off,image_paths['off'])

        self.Load_pic(self.light3,image_paths['light_off'])
        self.Load_pic(self.light3_off,image_paths['off'])
        # 加载室外补光系统图片
        self.Load_pic(self.auto1_light,image_paths['light_off'])
        self.init_label(self.auto1_light_off, "自动模式","gray")  

        self.Load_pic(self.light4,image_paths['light_off'])
        self.Load_pic(self.light4_off,image_paths['off'])

        self.Load_pic(self.light5,image_paths['light_off'])
        self.Load_pic(self.light5_off,image_paths['off'])

        self.Load_pic(self.light6,image_paths['light_off'])
        self.Load_pic(self.light6_off,image_paths['off'])
        #加载室外施肥系统
        self.Load_pic(self.fl1,image_paths['fl_off'])
        self.Load_pic(self.fl1_off,image_paths['off'])

        self.Load_pic(self.fl2,image_paths['fl_off'])
        self.Load_pic(self.fl2_off,image_paths['off'])

        self.Load_pic(self.fl3,image_paths['fl_off'])
        self.Load_pic(self.fl3_off,image_paths['off'])

    def handle_image_update(self, label_name, image_path):
        """
        更新指定标签的图片，更新对应的自动模式状态
        
        Args:
            label_name: 标签名称字符串
            image_path: 图片路径
        """
        global global_auto_sprinkler, global_auto_light, global_auto_light1
        
        try:
            # 通过名称获取对应的标签对象
            label = getattr(self, label_name, None)
            print(f"label_name: {label_name}, image_path: {image_path}")
            
            # 处理自动模式标签
            if label_name in ['auto_pl_off','auto_light_off','auto1_light_off']:
                if label is not None:
                    self.init_label(label, "自动模式", image_path)
                    # 根据颜色值设置对应设备的自动模式全局变量
                    # 当颜色为gray时关闭自动模式，其他情况（如cyan）时打开自动模式
                    is_auto_enabled = image_path.lower() != "gray"
                    
                    if label_name == 'auto_pl_off':
                        global_auto_sprinkler = is_auto_enabled
                        print(f"global_auto_sprinkler_handleimage: {global_auto_sprinkler}")
                    elif label_name == 'auto_light_off':
                        global_auto_light = is_auto_enabled
                        print(f"global_auto_light_handleimage: {global_auto_light}")        
                    elif label_name == 'auto1_light_off':
                        global_auto_light1 = is_auto_enabled
                        print(f"global_auto_light1_handleimage: {global_auto_light1}") 
            else:
                if label is not None:
                    self.Load_pic(label, image_path)
                    
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] 警告: 找不到标签对象 {label_name} 用于加载图片")
            
               
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] 更新图片失败: {e}")
            
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
            # 如果是喂食系统的开启图片，1秒后自动切换回关闭状态
            if 'feed_on' in pic_path:
                # 创建一个一次性定时器
                timer = QTimer(self)
                timer.setSingleShot(True)
                timer.timeout.connect(lambda: self.Load_pic(Label, FEED_OFF_IMAGE))
                timer.start(1000)  # 1000毫秒 = 1秒
            elif 'fl_on' in pic_path:
                # 创建一个一次性定时器
                timer = QTimer(self)
                timer.setSingleShot(True)
                timer.timeout.connect(lambda: self.Load_pic(Label, FL_OFF_IMAGE))
                timer.start(1000)  # 1000毫秒 = 1秒
            elif 'on1' in pic_path:
                # 创建一个一次性定时器
                timer = QTimer(self)
                timer.setSingleShot(True)
                timer.timeout.connect(lambda: self.Load_pic(Label, OFF_IMAGE))
                timer.start(1000)  # 1000毫秒 = 1秒
            
            
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
               
    def create_data_folders(self):
        """创建用于保存数据的文件夹结构"""
        # 要创建的主文件夹，包括设备4、5、6
        main_folders = ["1号土壤数据", "2号土壤数据", "3号土壤数据"]
        
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
                    # 写入表头
                    writer.writerow(["当前时间", "土壤温度(°C)", "土壤湿度(%)", "pH值", "电导率(μS/cm)", "喷淋状态(0/1)"])
    
    def save_sensor_data(self, device_id, temperature, moisture, ph, conductivity, spray_state):
        """保存传感器数据到CSV文件"""
        # 获取当前日期信息
        current_date = datetime.now()
        year_month = current_date.strftime("%Y-%m")
        day = current_date.strftime("%m%d")
        
        # 设备ID映射：将设备4-6的数据保存到1-3号土壤数据文件夹
        folder_id = device_id
        if device_id == 4:
            folder_id = 1
        elif device_id == 5:
            folder_id = 2
        elif device_id == 6:
            folder_id = 3
        
        # 根据映射后的ID确定文件夹
        folder_name = f"{folder_id}号土壤数据"
        
        # 构建统一的主文件夹路径，所有数据都放在"室内农场数据"文件夹下
        main_folder = "室内农场数据"
        csv_file = Path("/home/pi/Desktop/") / main_folder / folder_name / year_month / f"{day}.csv"
        
        # 获取当前时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 检查文件是否存在，不存在则创建
        if not csv_file.exists():
            # 创建文件夹结构
            try:
                # 确保目录存在
                csv_file.parent.mkdir(parents=True, exist_ok=True)
                # 创建文件并写入表头
                with open(csv_file, mode='w', newline='', encoding='utf-8-sig') as file:
                    writer = csv.writer(file)
                    # 写入表头
                    writer.writerow(["当前时间", "土壤温度(°C)", "土壤湿度(%)", "pH值", "电导率(μS/cm)", "喷淋状态(0/1)"])
                print(f"已创建新的数据文件: {csv_file}")
                print(f"主文件夹路径: {main_folder}")
            except Exception as e:
                print(f"创建数据文件{csv_file}时出错: {e}")
                return
        
        # 写入数据
        try:
            with open(csv_file, mode='a', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                # 写入数据行
                writer.writerow([current_time, temperature, moisture, ph, conductivity, spray_state])
                # 添加调试信息，显示原始设备ID和映射后的文件夹ID
                print(f"数据已成功保存 - 设备{device_id}→文件夹{folder_id}: {csv_file}")
                print(f"所有数据已集中保存在 '{main_folder}' 主文件夹中")
                print(f"数据内容: {current_time}, {temperature}℃, {moisture}%, {ph}, {conductivity}μS/cm, {spray_state}")
        except Exception as e:
            print(f"保存数据到{csv_file}时出错: {e}")
    
    def save_hydroponic_data(self, device_id, ph_value, water_temp, water_level):
        """保存水培柜数据到CSV文件"""
        # 获取当前日期信息
        current_date = datetime.now()
        year_month = current_date.strftime("%Y-%m")
        day = current_date.strftime("%m%d")
        
        # 设备ID映射：将设备12-14映射为1-3号水培柜
        folder_id = device_id - 11  # 12→1, 13→2, 14→3
        folder_name = f"{folder_id}号水培柜数据"
        
        # 构建统一的主文件夹路径，所有数据都放在"室内农场数据"文件夹下
        main_folder = "室内农场数据"
        csv_file = Path("/home/pi/Desktop/") / main_folder / folder_name / year_month / f"{day}.csv"
        
        # 获取当前时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 检查文件是否存在，不存在则创建
        if not csv_file.exists():
            # 创建文件夹结构
            try:
                # 确保目录存在
                csv_file.parent.mkdir(parents=True, exist_ok=True)
                # 创建文件并写入表头
                with open(csv_file, mode='w', newline='', encoding='utf-8-sig') as file:
                    writer = csv.writer(file)
                    # 写入表头
                    writer.writerow(["当前时间", "pH值", "水温(°C)", "液位状态(0=充足,1=缺水)"])
                print(f"已创建新的水培柜数据文件: {csv_file}")
                print(f"主文件夹路径: {main_folder}")
            except Exception as e:
                print(f"创建水培柜数据文件{csv_file}时出错: {e}")
                return
        
        # 写入数据
        try:
            with open(csv_file, mode='a', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                # 写入数据行
                writer.writerow([current_time, ph_value, water_temp, water_level])
                # 添加调试信息
                print(f"水培柜数据已成功保存 - 设备{device_id}→文件夹{folder_id}: {csv_file}")
                print(f"所有数据已集中保存在 '{main_folder}' 主文件夹中")
                print(f"数据内容: {current_time}, pH={ph_value}, 水温={water_temp}℃, 液位={water_level}")
        except Exception as e:
            print(f"保存水培柜数据到{csv_file}时出错: {e}")
    
    def save_indoor_env_data(self, device_id, temperature, humidity, pm25, light, uv):
        """保存室内环境数据到CSV文件"""
        # 获取当前日期信息
        current_date = datetime.now()
        year_month = current_date.strftime("%Y-%m")
        day = current_date.strftime("%m%d")
        
        # 固定文件夹名称为"室内环境数据"
        folder_name = "室内环境数据"
        
        # 构建统一的主文件夹路径，所有数据都放在"室内农场数据"文件夹下
        main_folder = "室内农场数据"
        csv_file = Path(main_folder) / folder_name / year_month / f"{day}.csv"
        
        # 获取当前时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 检查文件是否存在，不存在则创建
        if not csv_file.exists():
            # 创建文件夹结构
            try:
                # 确保目录存在
                csv_file.parent.mkdir(parents=True, exist_ok=True)
                # 创建文件并写入表头
                with open(csv_file, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    # 写入表头
                    writer.writerow(["当前时间", "室内温度(°C)", "室内湿度(%)", "PM2.5", "光照强度", "紫外线强度"])
                print(f"已创建新的室内环境数据文件: {csv_file}")
                print(f"主文件夹路径: {main_folder}")
            except Exception as e:
                print(f"创建室内环境数据文件{csv_file}时出错: {e}")
                return
        
        # 写入数据
        try:
            with open(csv_file, mode='a', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                # 写入数据行
                writer.writerow([current_time, temperature, humidity, pm25, light, uv])
                # 添加调试信息
                print(f"室内环境数据已成功保存 - 设备{device_id}: {csv_file}")
                print(f"所有数据已集中保存在 '{main_folder}' 主文件夹中")
                print(f"数据内容: {current_time}, 温度={temperature}℃, 湿度={humidity}%, PM2.5={pm25}, 光照={light}, 紫外线={uv}")
        except Exception as e:
            print(f"保存室内环境数据到{csv_file}时出错: {e}")

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        # 停止传感器数据串口接收线程
        if hasattr(self, 'serial_thread'):
            self.serial_thread.stop()
        
        # 停止语音识别数据串口接收线程
        if hasattr(self, 'voice_thread'):
            self.voice_thread.stop()
            
        # 停止室外数据接收线程
        if hasattr(self, 'outdoor_thread'):
            self.outdoor_thread.stop()

        # 接受关闭事件
        event.accept()
   
    def init_gauges(self):
        """初始化仪表盘"""
        big_gauge_width = 20
        width=220
        Y_1=505
        Y_2=805
        Y_3=1245
        Y_4=1540
        Y_5=1835
        # 为第一个区域的温度创建仪表盘 1-1
        # 创建渐变颜色列表（红到绿）
        temp_colors = [QColor(0, 255, 255), QColor(0, 255, 255), QColor(0, 255, 255)]
        # 创建温度仪表盘，范围0-100摄氏度
        self.temp1_gauge = GaugeWidget(self, min_value=0.0, max_value=60.0, colors=temp_colors, gauge_width=big_gauge_width)
        # 设置仪表盘大小和位置
        self.temp1_gauge.setGeometry(207, Y_1, width, width)
        # 设置仪表盘的值（示例值）
        self.temp1_gauge.setValue(60)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.temp1_gauge.raise_()

        # 为第一个区域的湿度创建仪表盘1-2
        hum_colors = [QColor(135,206,250), QColor(0,191,255), QColor(30,144,255)]
        # 创建湿度仪表盘，范围0-100%
        self.hum1_gauge = GaugeWidget(self, min_value=0.0, max_value=100.0, colors=hum_colors, gauge_width=big_gauge_width)
        # 设置仪表盘大小和位置
        self.hum1_gauge.setGeometry(528-36, Y_1, width, width)
        # 设置仪表盘的值（示例值）
        self.hum1_gauge.setValue(100)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.hum1_gauge.raise_() 

        # 为第一个区域的pH值创建仪表盘1-3
        ph_colors = [QColor(0,191,255), QColor(255,255,0), QColor(220,20,60)]
        # 创建pH值仪表盘，范围0-14
        self.ph1_gauge = GaugeWidget(self, min_value=0.0, max_value=14.0, colors=ph_colors, gauge_width=big_gauge_width)
        # 设置仪表盘大小和位置
        self.ph1_gauge.setGeometry(813-36, Y_1, width, width)
        # 设置仪表盘的值（示例值）
        self.ph1_gauge.setValue(14)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.ph1_gauge.raise_()

        # 为第一个区域的电导率创建仪表盘1-4
        ele_colors = [QColor(135,206,250), QColor(0,100,0), QColor(0,250,154)]
        # 创建电导率仪表盘，范围0-20000
        self.ele1_gauge = GaugeWidget(self, min_value=0.0, max_value=20000.0, colors=ele_colors, gauge_width=25)
        # 设置仪表盘大小和位置
        self.ele1_gauge.setGeometry(1076-36, 498, 230, 230)
        # 设置仪表盘的总角度为280度
        self.ele1_gauge.setTotalAngle(290)
        # 设置仪表盘的起始角度为180度（从底部开始）
        self.ele1_gauge.setStartAngle(235)
        ## 设置仪表盘的值（示例值）
        self.ele1_gauge.setValue(20000)

        # 为第二个区域的温度创建仪表盘 2-1
        # 创建温度仪表盘，范围0-100摄氏度
        self.temp2_gauge = GaugeWidget(self, min_value=0.0, max_value=60.0, colors=temp_colors, gauge_width=big_gauge_width)
        # 设置仪表盘大小和位置
        self.temp2_gauge.setGeometry(207, Y_2, width, width)
        # 设置仪表盘的值（示例值）
        self.temp2_gauge.setValue(60)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.temp2_gauge.raise_()

        # 为第二个区域的湿度创建仪表盘2-2
        # 创建湿度仪表盘，范围0-100%
        self.hum2_gauge = GaugeWidget(self, min_value=0.0, max_value=100.0, colors=hum_colors, gauge_width=big_gauge_width)
        # 设置仪表盘大小和位置
        self.hum2_gauge.setGeometry(528-36, Y_2, width, width)
        # 设置仪表盘的值（示例值）
        self.hum2_gauge.setValue(100)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.hum2_gauge.raise_() 

        # 为第二个区域的pH值创建仪表盘2-3
        # 创建pH值仪表盘，范围0-14
        self.ph2_gauge = GaugeWidget(self, min_value=0.0, max_value=14.0, colors=ph_colors, gauge_width=big_gauge_width)
        # 设置仪表盘大小和位置
        self.ph2_gauge.setGeometry(813-36, Y_2, width, width)
        # 设置仪表盘的值（示例值）
        self.ph2_gauge.setValue(14)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.ph2_gauge.raise_()

        # 为第二个区域的电导率创建仪表盘 2-4
        # 创建电导率仪表盘，范围0-20000
        self.ele2_gauge = GaugeWidget(self, min_value=0.0, max_value=20000.0, colors=ele_colors, gauge_width=27)
        # 设置仪表盘大小和位置
        self.ele2_gauge.setGeometry(1076-36, 798, 230, 230)
        # 设置仪表盘的总角度为280度
        self.ele2_gauge.setTotalAngle(290)
        # 设置仪表盘的起始角度为180度（从底部开始）
        self.ele2_gauge.setStartAngle(235)
        ## 设置仪表盘的值（示例值）
        self.ele2_gauge.setValue(20000)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.ele2_gauge.raise_()

        # 为第3个区域的温度创建仪表盘 3-1
        # 创建温度仪表盘，范围0-100摄氏度
        self.temp3_gauge = GaugeWidget(self, min_value=0.0, max_value=60.0, colors=temp_colors, gauge_width=big_gauge_width)
        # 设置仪表盘大小和位置
        self.temp3_gauge.setGeometry(207, Y_3, width, width)
        # 设置仪表盘的值（示例值）
        self.temp3_gauge.setValue(60)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.temp3_gauge.raise_()

        # 为第3个区域的湿度创建仪表盘3-2
        # 创建湿度仪表盘，范围0-100%
        self.hum3_gauge = GaugeWidget(self, min_value=0.0, max_value=100.0, colors=hum_colors, gauge_width=big_gauge_width)
        # 设置仪表盘大小和位置
        self.hum3_gauge.setGeometry(528-36, Y_3, width, width)
        # 设置仪表盘的值（示例值）
        self.hum3_gauge.setValue(100)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.hum3_gauge.raise_() 

        # 为第3个区域的pH值创建仪表盘3-3
        ph_colors = [QColor(0,191,255), QColor(255,255,0), QColor(220,20,60)]
        # 创建pH值仪表盘，范围0-14
        self.ph3_gauge = GaugeWidget(self, min_value=0.0, max_value=14.0, colors=ph_colors, gauge_width=big_gauge_width)
        # 设置仪表盘大小和位置
        self.ph3_gauge.setGeometry(813-36, Y_3, width, width)
        # 设置仪表盘的值（示例值）
        self.ph3_gauge.setValue(14)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.ph3_gauge.raise_()

        # 为第3个区域的电导率创建仪表盘3-4
        # 创建电导率仪表盘，范围0-20000
        self.ele3_gauge = GaugeWidget(self, min_value=0.0, max_value=20000.0, colors=ele_colors, gauge_width=27)
        # 设置仪表盘大小和位置
        self.ele3_gauge.setGeometry(1076-36, 1238, 230, 230)
        # 设置仪表盘的总角度为280度
        self.ele3_gauge.setTotalAngle(290)
        # 设置仪表盘的起始角度为180度（从底部开始）
        self.ele3_gauge.setStartAngle(235)
        ## 设置仪表盘的值（示例值）
        self.ele3_gauge.setValue(20000)

        # 为第4个区域的温度创建仪表盘 4-1
        # 创建温度仪表盘，范围0-100摄氏度
        self.temp4_gauge = GaugeWidget(self, min_value=0.0, max_value=60.0, colors=temp_colors, gauge_width=big_gauge_width)
        # 设置仪表盘大小和位置
        self.temp4_gauge.setGeometry(207, Y_4, width, width)
        # 设置仪表盘的值（示例值）
        self.temp4_gauge.setValue(60)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.temp4_gauge.raise_()

        # 为第4个区域的湿度创建仪表盘4-2
        # 创建湿度仪表盘，范围0-100%
        self.hum4_gauge = GaugeWidget(self, min_value=0.0, max_value=100.0, colors=hum_colors, gauge_width=big_gauge_width)
        # 设置仪表盘大小和位置
        self.hum4_gauge.setGeometry(528-36, Y_4, width, width)
        # 设置仪表盘的值（示例值）
        self.hum4_gauge.setValue(100)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.hum4_gauge.raise_() 

        # 为第4个区域的pH值创建仪表盘4-3
        # 创建pH值仪表盘，范围0-14
        self.ph4_gauge = GaugeWidget(self, min_value=0.0, max_value=14.0, colors=ph_colors, gauge_width=big_gauge_width)
        # 设置仪表盘大小和位置
        self.ph4_gauge.setGeometry(813-36, Y_4, width, width)
        # 设置仪表盘的值（示例值）
        self.ph4_gauge.setValue(14)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.ph4_gauge.raise_()

        # 为第4个区域的电导率创建仪表盘 4-4
        # 创建电导率仪表盘，范围0-20000
        self.ele4_gauge = GaugeWidget(self, min_value=0.0, max_value=20000.0, colors=ele_colors, gauge_width=27)
        # 设置仪表盘大小和位置
        self.ele4_gauge.setGeometry(1076-36,1533, 230, 230)
        # 设置仪表盘的总角度为280度
        self.ele4_gauge.setTotalAngle(290)
        # 设置仪表盘的起始角度为180度（从底部开始）
        self.ele4_gauge.setStartAngle(235)
        ## 设置仪表盘的值（示例值）
        self.ele4_gauge.setValue(20000)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.ele4_gauge.raise_()
         # 为第5个区域的温度创建仪表盘 5-1
        # 创建温度仪表盘，范围0-100摄氏度
        self.temp5_gauge = GaugeWidget(self, min_value=0.0, max_value=60.0, colors=temp_colors, gauge_width=big_gauge_width)
        # 设置仪表盘大小和位置
        self.temp5_gauge.setGeometry(207, Y_5, width, width)
        # 设置仪表盘的值（示例值）
        self.temp5_gauge.setValue(60)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.temp5_gauge.raise_()

        # 为第5个区域的湿度创建仪表盘5-2
        # 创建湿度仪表盘，范围0-100%
        self.hum5_gauge = GaugeWidget(self, min_value=0.0, max_value=100.0, colors=hum_colors, gauge_width=big_gauge_width)
        # 设置仪表盘大小和位置
        self.hum5_gauge.setGeometry(528-36, Y_5, width, width)
        # 设置仪表盘的值（示例值）
        self.hum5_gauge.setValue(100)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.hum5_gauge.raise_() 

        # 为第5个区域的pH值创建仪表盘5-3
        # 创建pH值仪表盘，范围0-14
        self.ph5_gauge = GaugeWidget(self, min_value=0.0, max_value=14.0, colors=ph_colors, gauge_width=big_gauge_width)
        # 设置仪表盘大小和位置
        self.ph5_gauge.setGeometry(813-36, Y_5, width, width)
        # 设置仪表盘的值（示例值）
        self.ph5_gauge.setValue(14)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.ph5_gauge.raise_()

        # 为第5个区域的电导率创建仪表盘 5-4
        # 创建电导率仪表盘，范围0-20000
        self.ele5_gauge = GaugeWidget(self, min_value=0.0, max_value=20000.0, colors=ele_colors, gauge_width=27)
        # 设置仪表盘大小和位置
        self.ele5_gauge.setGeometry(1076-36,1828, 230, 230)
        # 设置仪表盘的总角度为280度
        self.ele5_gauge.setTotalAngle(290)
        # 设置仪表盘的起始角度为180度（从底部开始）
        self.ele5_gauge.setStartAngle(235)
        ## 设置仪表盘的值（示例值）
        self.ele5_gauge.setValue(20000)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.ele5_gauge.raise_()

        Y_6=922
        width=200
        # 为第6个区域的温度创建仪表盘 6-1
        # 创建温度仪表盘，范围0-100摄氏度
        self.temp6_gauge = GaugeWidget(self, min_value=0.0, max_value=60.0, colors=temp_colors, gauge_width=big_gauge_width)
        # 设置仪表盘大小和位置
        self.temp6_gauge.setGeometry(2486-36, Y_6, width, width)
        # 设置仪表盘的值（示例值）
        self.temp6_gauge.setValue(60)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.temp6_gauge.raise_()
        # 设置第6个区域的Y坐标
       
        # 为第6个区域的湿度创建仪表盘6-2
        # 创建湿度仪表盘，范围0-100%
        self.hum6_gauge = GaugeWidget(self, min_value=0.0, max_value=100.0, colors=hum_colors, gauge_width=big_gauge_width)
        # 设置仪表盘大小和位置
        self.hum6_gauge.setGeometry(2715-36, Y_6, width, width)
        # 设置仪表盘的值（示例值）
        self.hum6_gauge.setValue(100)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.hum6_gauge.raise_() 

        # 为第6个区域的pM2.5值创建仪表盘6-3
        # 创建pM2.5值仪表盘，范围0-14
        self.pm25_gauge = GaugeWidget(self, min_value=0.0, max_value=200, colors=ph_colors, gauge_width=big_gauge_width)
        # 设置仪表盘大小和位置
        self.pm25_gauge.setGeometry(2944-36, Y_6, width, width)
        # 设置仪表盘的值（示例值）
        self.pm25_gauge.setValue(14)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.pm25_gauge.raise_()

        # 为第6个区域的电导率创建仪表盘 6-4
        # 创建电导率仪表盘，范围0-20000
        light_colors =[QColor(0,191,255), QColor(255,255,0), QColor(220,20,60)]
        self.light_gauge = GaugeWidget(self, min_value=0.0, max_value=4095, colors=light_colors, gauge_width=27)
        # 设置仪表盘大小和位置
        self.light_gauge.setGeometry(3160-36,919, 218, 218)
        # 设置仪表盘的总角度为280度
        self.light_gauge.setTotalAngle(290)
        # 设置仪表盘的起始角度为180度（从底部开始）
        self.light_gauge.setStartAngle(235)
        ## 设置仪表盘的值（示例值）
        self.light_gauge.setValue(100)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.light_gauge.raise_()
        # 为第6个区域的电导率创建仪表盘 6-5
        # 创建电导率仪表盘，范围0-20000
        uv_colors = [QColor(0,191,255), QColor(255,255,0), QColor(220,20,60)]
        self.UV_gauge = GaugeWidget(self, min_value=0.0, max_value=10, colors=uv_colors, gauge_width=27)
        # 设置仪表盘大小和位置
        self.UV_gauge.setGeometry(3388-36,919, 218, 218)
        # 设置仪表盘的总角度为280度
        self.UV_gauge.setTotalAngle(290)
        # 设置仪表盘的起始角度为180度（从底部开始）
        self.UV_gauge.setStartAngle(235)
        ## 设置仪表盘的值（示例值）
        self.UV_gauge.setValue(10)
        # 将仪表盘置于顶层，确保在背景图片之上
        self.UV_gauge.raise_()
    

class XiaoZhiThread(SerialReceiveThread):
    # 添加信号，用于将解析后的JSON数据发送到主线程
    json_data_received = pyqtSignal(dict)  # 发送解析后的JSON对象
    # 新增信号用于UI更新
    update_image_signal = pyqtSignal(str, str)  # 参数: label_name, image_path
    
    def __init__(self, port, baudrate, timeout):
        super().__init__(port, baudrate, timeout)
    
    def parse_multiple_json_objects(self, text):
        """
        解析多个连续的JSON对象
        
        Args:
            text: 包含多个JSON对象的文本
            
        Returns:
            list: 解析后的JSON对象列表
        """
        objects = []
        current = ""
        brace_count = 0
        in_string = False
        escape = False
        
        for char in text:
            current += char
            
            if escape:
                escape = False
                continue
            
            if char == '\\':
                escape = True
            elif char == '"':
                in_string = not in_string
            elif not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # 尝试解析当前JSON对象
                        try:
                            obj = json.loads(current)
                            objects.append(obj)
                            current = ""
                        except json.JSONDecodeError:
                            # 如果解析失败，继续累积字符
                            pass
        
        return objects
    
    def handle_event(self, data):
        """
        处理不同类型的事件
        
        Args:
            data: 事件数据
        """
        event = data['event']
        print(f"[{time.strftime('%H:%M:%S')}] 小智线程收到事件: {event}")
        if event == 'spray_system':
            print(f"[{time.strftime('%H:%M:%S')}] 小智线程收到喷淋系统事件: {data}")
            if 'device_id' in data and 'state' in data:
                if data['device_id'] is not None:
                    if data['state'] == True:
                        print(f"[{time.strftime('%H:%M:%S')}] 设备ID {data['device_id']} 喷淋系统已开启")
                        # 发送打开喷淋的命令: A0 01 01 01 FF    
                        send_control_command(data['device_id']+3, 0x00, 0x01)
                        # 发出信号，让主线程更新UI
                        self.update_image_signal.emit(f"pl{data['device_id']}", OPEN_IMAGE)
                        self.update_image_signal.emit(f"pl{data['device_id']}_off", ON_IMAGE)
                        
                    else:
                        print(f"[{time.strftime('%H:%M:%S')}] 设备ID {data['device_id']} 喷淋系统已关闭")
                        # 发送关闭喷淋的命令: A0 01 01 00 FF    
                        send_control_command(data['device_id']+3, 0x00, 0x00)
                        # 发出信号，让主线程更新UI
                        self.update_image_signal.emit(f"pl{data['device_id']}", DOWN_IMAGE)
                        self.update_image_signal.emit(f"pl{data['device_id']}_off", OFF_IMAGE)
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] 未指定设备ID")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] 未指定状态")        
        elif event == 'fertilizer_system':
            if 'device_id' in data and 'state' in data:
                if data['device_id'] is not None:
                    if data['state'] == True:
                        print(f"[{time.strftime('%H:%M:%S')}] 设备ID {data['device_id']} 肥料系统已开启")
                        # 发送肥料系统的控制命令
                        send_control_command(data['device_id']+15, 0x00, 0x01)
                        # 发出信号，让主线程更新UI
                        self.update_image_signal.emit(f"fl{data['device_id']}", FL_ON_IMAGE)
                        self.update_image_signal.emit(f"fl{data['device_id']}_off", ON1_IMAGE)
                        time.sleep(0.95)
                        self.update_image_signal.emit(f"fl{data['device_id']}_off", OFF_IMAGE)
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] 未指定设备ID")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] 未指定状态")
        elif event == 'soil_light':
            if 'device_id' in data and 'state' in data:
                if data['device_id'] is not None:
                    if data['state'] == True:
                        print(f"[{time.strftime('%H:%M:%S')}] 设备ID {data['device_id']} 土壤光系统已开启")
                        # 土壤灯控制命令
                        send_control_command(data['device_id']+6, 0x00, 0x01)
                        # 发出信号，让主线程更新UI
                        self.update_image_signal.emit(f"light{data['device_id']+3}", LIGHT_ON_IMAGE)
                        self.update_image_signal.emit(f"light{data['device_id']+3}_off", ON_IMAGE)
                    else:
                        print(f"[{time.strftime('%H:%M:%S')}] 设备ID {data['device_id']} 土壤光系统已关闭")
                        send_control_command(data['device_id']+6, 0x00, 0x00)
                        # 发出信号，让主线程更新UI
                        self.update_image_signal.emit(f"light{data['device_id']+3}", LIGHT_OFF_IMAGE)
                        self.update_image_signal.emit(f"light{data['device_id']+3}_off", OFF_IMAGE)
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] 未指定设备ID")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] 未指定状态")       
        elif event == 'hydro_light':
            if 'device_id' in data and 'state' in data:
                if data['device_id'] is not None:
                    if data['state'] == True:
                        print(f"[{time.strftime('%H:%M:%S')}] 设备ID {data['device_id']} 水培系统已开启")
                        # 水培灯控制命令
                        send_control_command(data['device_id']+11, 0x02, 0x01)
                        self.update_image_signal.emit(f"light{data['device_id']}", LIGHT_ON_IMAGE)
                        self.update_image_signal.emit(f"light{data['device_id']}_off", ON_IMAGE)
                        self.ser.reset_input_buffer()
                    else:
                        print(f"[{time.strftime('%H:%M:%S')}] 设备ID {data['device_id']} 水培系统已关闭")
                        send_control_command(data['device_id']+11, 0x02, 0x00)
                        self.update_image_signal.emit(f"light{data['device_id']}", LIGHT_OFF_IMAGE)
                        self.update_image_signal.emit(f"light{data['device_id']}_off", OFF_IMAGE)
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] 未指定设备ID")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] 未指定状态")
        elif event == 'feeding_system':
            if 'device_id' in data and 'state' in data:
                if data['device_id'] is not None:
                    if data['state'] == True:
                        print(f"[{time.strftime('%H:%M:%S')}] 设备ID {data['device_id']} 投喂系统已开启")
                        # 投喂系统控制命令
                        send_control_command(data['device_id']+11, 0x01, 0x01)
                        self.update_image_signal.emit(f"feed{data['device_id']}", FEED_ON_IMAGE)
                        self.update_image_signal.emit(f"feed{data['device_id']}_off", ON1_IMAGE)
                        time.sleep(0.95)
                        self.update_image_signal.emit(f"feed{data['device_id']}_off", OFF_IMAGE)
                        self.ser.reset_input_buffer()
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] 未指定设备ID")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] 未指定状态")            
        elif event == 'auto_control':
            
            if 'device_id' in data and 'state' in data:
                if data['device_id'] is not None:
                    if data['state'] == True:                       
                        # 自动控制命令  
                       
                        if data['device_id'] == 1:
                            self.update_image_signal.emit(f"auto_pl", OPEN_IMAGE)
                            self.update_image_signal.emit(f"auto_pl_off", "Cyan")                                                      
                            print(f"[{time.strftime('%H:%M:%S')}]喷淋自动控制已开启")
                            
                        elif data['device_id'] == 2:
                            self.update_image_signal.emit(f"auto_light", LIGHT_ON_IMAGE)
                            self.update_image_signal.emit(f"auto_light_off", "Cyan")
                            print(f"[{time.strftime('%H:%M:%S')}]水培补光自动控制已开启")
                        elif data['device_id'] == 3:
                            self.update_image_signal.emit(f"auto1_light", LIGHT_ON_IMAGE)
                            self.update_image_signal.emit(f"auto1_light_off", "Cyan")
                            print(f"[{time.strftime('%H:%M:%S')}]土培补光自动控制已开启")
                            
                    else:
                        if data['device_id'] == 1:
                            self.update_image_signal.emit(f"auto_pl", DOWN_IMAGE)
                            self.update_image_signal.emit(f"auto_pl_off", "Cyan") 
                            print(f"[{time.strftime('%H:%M:%S')}]喷淋自动控制已关闭")
                            
                        elif data['device_id'] == 2:
                            self.update_image_signal.emit(f"auto_light", LIGHT_OFF_IMAGE)
                            self.update_image_signal.emit(f"auto_light_off", "Cyan")
                            print(f"[{time.strftime('%H:%M:%S')}]水培补光自动控制已关闭")
                        elif data['device_id'] == 3:
                            self.update_image_signal.emit(f"auto1_light", LIGHT_OFF_IMAGE)
                            self.update_image_signal.emit(f"auto1_light_off", "Cyan")
                            print(f"[{time.strftime('%H:%M:%S')}]土培补光自动控制已关闭")
                        
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] 未指定设备ID")
            else:
                print(f"[{time.strftime('%H:%M:%S')}] 未指定状态")       
        elif event == 'temperature':
            send_control_command(15, 0x01, 0x00)
            print(f"[{time.strftime('%H:%M:%S')}] 室内温度系统")
        elif event == 'humidity':
            send_control_command(15, 0x02, 0x00)
            print(f"[{time.strftime('%H:%M:%S')}] 室内湿度系统")
        elif event == 'uv':
            send_control_command(15, 0x03, 0x00)
            print(f"[{time.strftime('%H:%M:%S')}] 室内紫外线系统")
        elif event == 'light_intensity':
            send_control_command(15, 0x04, 0x00)
            print(f"[{time.strftime('%H:%M:%S')}] 室内补光灯系统")
        elif event == 'pm25':
            send_control_command(15, 0x06, 0x00)
            print(f"[{time.strftime('%H:%M:%S')}] 室内PM2.5系统")
        elif event == 'weather_condition':
            send_control_command(15, 0x05, 0x00)
            print(f"[{time.strftime('%H:%M:%S')}] 室内天气条件系统")
        elif event == 'environment':
            send_control_command(15, 0x07, 0x00)
            print(f"[{time.strftime('%H:%M:%S')}] 室内环境系统")
        elif event == 'chat_message':
            if 'content' in data:
                print(f"[{time.strftime('%H:%M:%S')}] 聊天消息: {data['content']}")
    def handle_event_a0(self, data):    
        # 处理A0格式事件
        device_id = data['device_id']
        action_code = data['action_code']
        data_value = data['data_value']
        # 构建控制命令
        command = bytearray([0xA0, device_id, action_code, data_value, 0xFF])
        
        # 发送命令到串口
        send_control_command(device_id, action_code, data_value)
        #喷淋事件
        if device_id in [4,5,6]:     
              
            if  data_value == 0x01:                
                self.update_image_signal.emit(f"pl{data['device_id']-3}", OPEN_IMAGE)
                self.update_image_signal.emit(f"pl{data['device_id']-3}_off", ON_IMAGE)
                
                print(f"[{time.strftime('%H:%M:%S')}] 喷淋事件开启: {data} 设备号: {device_id}")
                
                # 添加定时器，15秒后自动关闭喷淋
                from PyQt5.QtCore import QTimer
                
                def auto_off_spray():
                    print(f"[{time.strftime('%H:%M:%S')}] 设备ID {device_id} 喷淋系统定时关闭（15秒超时）")
                    # 发送关闭喷淋的命令
                    send_control_command(device_id, 0x00, 0x00)
                    # 更新喷淋UI状态
                    self.update_image_signal.emit(f"pl{data['device_id']-3}", DOWN_IMAGE)
                    self.update_image_signal.emit(f"pl{data['device_id']-3}_off", OFF_IMAGE)
                
                # 创建一次性定时器，15秒后执行自动关闭
                timer = QTimer(self)
                timer.setSingleShot(True)
                timer.timeout.connect(auto_off_spray)
                timer.start(15000)  # 15000毫秒 = 15秒
            elif data_value == 0x00:
                self.update_image_signal.emit(f"pl{data['device_id']-3}", DOWN_IMAGE)
                self.update_image_signal.emit(f"pl{data['device_id']-3}_off", OFF_IMAGE)
                print(f"[{time.strftime('%H:%M:%S')}] 喷淋事件关闭: {data} 设备号: {device_id}")
        #喂食事件
        elif device_id in [12,13,14]:
            #水培
            if action_code == 0x01:
                #水培喂食事件
                self.update_image_signal.emit(f"feed{data['device_id']-11}", FEED_ON_IMAGE)
                self.update_image_signal.emit(f"feed{data['device_id']-11}_off", ON1_IMAGE)                
                time.sleep(0.95)
                self.update_image_signal.emit(f"feed{data['device_id']-11}_off", OFF_IMAGE)
                print(f"[{time.strftime('%H:%M:%S')}] 水培喂食事件开启: {data} 设备号: {device_id}")
            elif action_code == 0x02:
                #水培补光
                if data_value == 0x01:
                    self.update_image_signal.emit(f"light{data['device_id']-11}", LIGHT_ON_IMAGE)
                    self.update_image_signal.emit(f"light{data['device_id']-11}_off", ON_IMAGE)
                    print(f"[{time.strftime('%H:%M:%S')}] 水培补光灯事件开启: {data} 设备号: {device_id}")
                elif data_value == 0x00:
                    self.update_image_signal.emit(f"light{data['device_id']-11}", LIGHT_OFF_IMAGE)
                    self.update_image_signal.emit(f"light{data['device_id']-11}_off", OFF_IMAGE)
                    print(f"[{time.strftime('%H:%M:%S')}] 水培补光灯事件关闭: {data} 设备号: {device_id}")              
        #土壤补光
        elif device_id in [7,8,9]:
            #土壤补光灯事件
            if data_value == 0x01:
                self.update_image_signal.emit(f"light{data['device_id']-3}", LIGHT_ON_IMAGE)
                self.update_image_signal.emit(f"light{data['device_id']-3}_off", ON_IMAGE)
                print(f"[{time.strftime('%H:%M:%S')}] 土壤补光灯事件开启: {data} 设备号: {device_id}")
            elif data_value == 0x00:
                self.update_image_signal.emit(f"light{data['device_id']-3}", LIGHT_OFF_IMAGE)
                self.update_image_signal.emit(f"light{data['device_id']-3}_off", OFF_IMAGE)
                print(f"[{time.strftime('%H:%M:%S')}] 土壤补光灯事件关闭: {data} 设备号: {device_id}")              
        #施肥事件
        elif device_id in [16,17,18]:
            
            self.update_image_signal.emit(f"fl{data['device_id']-15}", FL_ON_IMAGE)
            self.update_image_signal.emit(f"fl{data['device_id']-15}_off", ON1_IMAGE)
            time.sleep(0.95)
            self.update_image_signal.emit(f"fl{data['device_id']-15}_off", OFF_IMAGE)
        #自动喷淋事件
        elif device_id == 85:
            if data_value == 0x00:
                #关闭喷淋自动控制
                global global_auto_pl
                global_auto_pl = False
                print(global_auto_pl)
                self.update_image_signal.emit(f"auto_pl", DOWN_IMAGE)
                self.update_image_signal.emit(f"auto_pl_off", "gray")                                                      
                print(f"[{time.strftime('%H:%M:%S')}]喷淋自动控制已关闭")
            elif data_value == 0x01:
                #打开喷淋自动控制
                
                global_auto_pl = True
                print(global_auto_pl)
                self.update_image_signal.emit(f"auto_pl", OPEN_IMAGE)
                self.update_image_signal.emit(f"auto_pl_off", "cyan")                                                      
                print(f"[{time.strftime('%H:%M:%S')}]喷淋自动控制已开启")
        #自动补光事件
        elif device_id == 86:
                #打开自动补光
                if data_value == 0x01:
                    #打开自动补光
                    global global_auto_light
                    global_auto_light = True
                    
                    self.update_image_signal.emit(f"auto_light", LIGHT_ON_IMAGE)
                    self.update_image_signal.emit(f"auto_light_off", "cyan")
                    self.update_image_signal.emit(f"auto1_light", LIGHT_ON_IMAGE)
                    self.update_image_signal.emit(f"auto1_light_off", "cyan")
                    print(f"[{time.strftime('%H:%M:%S')}]补光自动控制已开启")
                elif data_value == 0x00:
                    #关闭自动补光
                 
                    global_auto_light = False
                   
                    self.update_image_signal.emit(f"auto_light", LIGHT_OFF_IMAGE)
                    self.update_image_signal.emit(f"auto_light_off", "gray")
                    self.update_image_signal.emit(f"auto1_light", LIGHT_OFF_IMAGE)
                    self.update_image_signal.emit(f"auto1_light_off", "gray")
                    print(f"[{time.strftime('%H:%M:%S')}]补光自动控制已关闭")
        #全部灯光事件
        elif device_id == 87:
                if data_value == 0x01:   
                    # 使用循环发送水培补光命令
                    # 更新所有灯光UI状态
                    for i in range(1, 7):
                        self.update_image_signal.emit(f"light{i}", LIGHT_ON_IMAGE)
                        self.update_image_signal.emit(f"light{i}_off", ON_IMAGE)
                    print(f"[{time.strftime('%H:%M:%S')}] 打开全部灯光")
                elif data_value == 0x00:
                    for i in range(1, 7):
                        self.update_image_signal.emit(f"light{i}", LIGHT_OFF_IMAGE)
                        self.update_image_signal.emit(f"light{i}_off", OFF_IMAGE)
                    print(f"[{time.strftime('%H:%M:%S')}] 关闭全部灯光")
        #全部施肥事件
        elif device_id == 88:
            if data_value == 0x00:
                #打开全部施肥
                # 更新施肥UI状态
                for i in range(1, 4):
                    self.update_image_signal.emit(f"fl{i}", FL_ON_IMAGE)
                    self.update_image_signal.emit(f"fl{i}_off", ON1_IMAGE)
                time.sleep(1)
                # 关闭施肥UI状态
                for i in range(1, 4):
                    self.update_image_signal.emit(f"fl{i}_off", OFF_IMAGE)
                print(f"[{time.strftime('%H:%M:%S')}]打开全部施肥")
        #全部喂食事件
        elif device_id == 89:
            if data_value == 0x00:
                #打开全部喂食
                # 更新喂食UI状态
                for i in range(1, 4):
                    self.update_image_signal.emit(f"feed{i}", FEED_ON_IMAGE)
                    self.update_image_signal.emit(f"feed{i}_off", ON1_IMAGE)
                time.sleep(1)
                # 关闭喂食UI状态
                for i in range(1, 4):
                    self.update_image_signal.emit(f"feed{i}_off", OFF_IMAGE)
                print(f"[{time.strftime('%H:%M:%S')}]打开全部喂食")
        #全部事件
        elif device_id == 102:
            if data_value == 0x01:
                #打开全部事                
                # 更新灯光UI状态
                for i in range(1, 7):
                    self.update_image_signal.emit(f"light{i}", LIGHT_ON_IMAGE)
                    self.update_image_signal.emit(f"light{i}_off", ON_IMAGE)
                # 更新施肥UI状态
                for i in range(1, 4):
                    self.update_image_signal.emit(f"fl{i}", FL_ON_IMAGE)
                    self.update_image_signal.emit(f"fl{i}_off", ON1_IMAGE)
                time.sleep(1)
                for i in range(1, 4):
                    self.update_image_signal.emit(f"fl{i}_off", OFF_IMAGE)
                # 更新喂食UI状态
                for i in range(1, 4):
                    self.update_image_signal.emit(f"feed{i}", FEED_ON_IMAGE)
                    self.update_image_signal.emit(f"feed{i}_off", ON1_IMAGE)
                time.sleep(1)
                for i in range(1, 4):
                    self.update_image_signal.emit(f"feed{i}_off", OFF_IMAGE)
                # 更新喷淋UI状态
                for i in range(1, 4):
                    self.update_image_signal.emit(f"pl{i}", OPEN_IMAGE)
                    self.update_image_signal.emit(f"pl{i}_off", ON1_IMAGE)
                
                # 设置15秒后关闭3个喷淋的UI显示
                print(f"[{time.strftime('%H:%M:%S')}] 将在15秒后关闭3个喷淋UI显示")
                from PyQt5.QtCore import QTimer
                def close_pl_ui():
                    for i in range(1, 4):
                        self.update_image_signal.emit(f"pl{i}", DOWN_IMAGE)
                        self.update_image_signal.emit(f"pl{i}_off", OFF_IMAGE)
                    print(f"[{time.strftime('%H:%M:%S')}] 15秒定时关闭3个喷淋UI显示完成")
                QTimer.singleShot(15000, close_pl_ui)
                    
                print(f"[{time.strftime('%H:%M:%S')}] 打开全部事件")
            elif data_value == 0x00:
                #关闭全部事件 
                
                # 更新灯光UI状态
                for i in range(1, 7):
                    self.update_image_signal.emit(f"light{i}", LIGHT_OFF_IMAGE)
                    self.update_image_signal.emit(f"light{i}_off", OFF_IMAGE)
                for i in range(1, 4):
                    self.update_image_signal.emit(f"pl{i}", DOWN_IMAGE)
                    self.update_image_signal.emit(f"pl{i}_off", OFF_IMAGE)
                    
                global_auto_light = False          
                global_auto_pl = False      
                self.update_image_signal.emit(f"auto_light", LIGHT_OFF_IMAGE)
                self.update_image_signal.emit(f"auto_light_off", "gray")
                self.update_image_signal.emit(f"auto1_light", LIGHT_OFF_IMAGE)
                self.update_image_signal.emit(f"auto1_light_off", "gray")                
                self.update_image_signal.emit(f"auto_pl", DOWN_IMAGE)
                self.update_image_signal.emit(f"auto_pl_off", "gray")                                                       
                               
                print(f"[{time.strftime('%H:%M:%S')}] 关闭全部事件")
         
            

        print(f"[{time.strftime('%H:%M:%S')}] 发送A0命令: {command.hex().upper()}")
        
    def run(self):
        # 初始化串口
        try:
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=self.timeout)
            print(f"[{time.strftime('%H:%M:%S')}] 小智串口初始化成功! 端口：{self.port}，波特率：{self.baud_rate}")
            print(f"[{time.strftime('%H:%M:%S')}] 开始接收JSON数据和A0格式数据...")
            self.running = True
            
            # 用于存储不完整的JSON数据
            json_buffer = ""
            
            # 用于存储不完整的A0帧数据
            a0_buffer = bytearray()
            
            # 事件去重机制 - 存储最近处理的事件信息
            last_event_info = {}
            debounce_time = 0.5  # 防抖时间，单位秒
            
            while self.running:
                # 检查是否有数据可读
                if self.ser.inWaiting() > 0:
                    # 读取一行数据
                    try:
                        raw_data = self.ser.read(self.ser.inWaiting())
                        
                        # 如果有数据才处理
                        if raw_data:
                            # 检查是否包含A0帧头
                            if 0xA0 in raw_data:
                                # 处理A0帧格式数据
                                a0_buffer.extend(raw_data)
                                
                                # 尝试解析A0格式帧
                                while True:
                                    # 寻找A0帧头
                                    frame_start = a0_buffer.find(0xA0)
                                    if frame_start == -1:
                                        # 没有找到帧头，跳出循环
                                        break
                                    
                                    # 寻找FF帧尾
                                    frame_end = a0_buffer.find(0xFF, frame_start)
                                    if frame_end == -1:
                                        # 没有找到帧尾，跳出循环
                                        break
                                    
                                    # 提取完整帧
                                    frame = a0_buffer[frame_start:frame_end+1]
                                    
                                    # 移除已处理的帧数据
                                    a0_buffer = a0_buffer[frame_end+1:]
                                    
                                    # 验证帧的最小长度（至少包含帧头和帧尾）
                                    if len(frame) >= 5:
                                        # 解析帧内容
                                        device_id = frame[1] if len(frame) > 1 else 0
                                        action_code = frame[2] if len(frame) > 2 else 0
                                        data_value = frame[3] if len(frame) > 3 else 0
                                        
                                        # 打印解析结果
                                        # print(f"[{time.strftime('%H:%M:%S')}] 解析到A0格式帧: 帧头=0x{frame[0]:02X}, 设备ID=0x{device_id:02X}, 动作码=0x{action_code:02X}, 数据值=0x{data_value:02X}, 帧尾=0x{frame[-1]:02X}")
                                        
                                        # 可以在这里处理A0格式的数据，例如发送信号到主线程
                                        # 构建一个事件字典
                                        a0_event = {                                            
                                            'device_id': device_id,
                                            'action_code': action_code,
                                            'data_value': data_value,                                            
                                        }
                                        print(f"[{time.strftime('%H:%M:%S')}] 处理A0事件: {a0_event}")
                                        self.handle_event_a0(a0_event)
                                        # # 发送信号到主线程
                                        # self.json_data_received.emit(a0_event)
                                
                            # 尝试处理JSON数据
                            try:
                                # 解码数据
                                json_data = raw_data.decode('utf-8', errors='replace').strip()
                                # 将新数据添加到缓冲区
                                json_buffer += json_data
                                
                                # 尝试解析缓冲区中的数据
                                objects = self.parse_multiple_json_objects(json_buffer)
                                
                                # 处理成功解析的对象
                                if objects:
                                    # 只处理最后一个对象（最新的事件）
                                    if len(objects) > 0:
                                        # 取最后一个对象作为要处理的事件
                                        obj = objects[-1]
                                        
                                        # 打印解析后的数据
                                        print(f"[{time.strftime('%H:%M:%S')}] 小智线程接收到数据: {obj}")
                                        
                                        # 发送信号到主线程
                                        self.json_data_received.emit(obj)
                                        
                                        # 处理不同类型的事件，使用防抖机制
                                        if 'event' in obj:
                                            event_type = obj['event']
                                            current_time = time.time()
                                            
                                            # 构建事件标识键
                                            event_key = event_type
                                            if 'device_id' in obj:
                                                event_key += f"_{obj['device_id']}"
                                            
                                            # 检查是否需要处理该事件（防抖）
                                            if event_key not in last_event_info or \
                                               (current_time - last_event_info[event_key]) > debounce_time:
                                                self.handle_event(obj)
                                                # 更新事件处理时间
                                                last_event_info[event_key] = current_time
                                    
                                    # 清空缓冲区，只保留未处理的部分
                                    # 由于我们只处理了最后一个对象，这里可以简化为清空整个缓冲区
                                    # 因为即使前面有未处理的对象，它们也会被忽略
                                    json_buffer = ""
                                    
                                # 如果缓冲区过大且长时间未解析成功，清空缓冲区
                                if len(json_buffer) > 1000:
                                    print(f"[{time.strftime('%H:%M:%S')}] 小智线程警告: JSON缓冲区过大且无法解析，清空缓冲区")
                                    json_buffer = ""
                                    
                            except Exception as e:
                                print(f"[{time.strftime('%H:%M:%S')}] 小智线程处理JSON数据时出错: {e}")
                    except Exception as e:
                        print(f"[{time.strftime('%H:%M:%S')}] 小智线程读取数据时出错: {e}")
                
                # 短暂休眠避免CPU占用过高
                self.msleep(100)
                
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] 小智串口初始化失败! 原因：{e}")
            print("提示:1. 检查端口是否正确; 2. 确认设备已连接; 3. 关闭占用串口的程序")

if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    window = BackgroundImageApp()
    window.show()
    sys.exit(app.exec_())
