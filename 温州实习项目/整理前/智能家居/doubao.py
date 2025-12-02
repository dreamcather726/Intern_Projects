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
 
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QWidget, QStatusBar
from PyQt5.QtGui import QPixmap, QFont, QPainter, QBrush, QConicalGradient, QPen, QColor
from PyQt5.QtCore import QThread, QObject, pyqtSignal, Qt, QTimer, QRectF
import PyQt5.uic as uic
# 假设GaugeWidget和blinker相关类已正确实现
from ybp import GaugeWidget
from blinker import Device, ButtonWidget, NumberWidget

device = Device("f9094bf7c991")
hum2_threshold = 50  # 浴室湿度阈值
msg = ""
light_status = 0
temp1 = 0
hum1 = 0
temp2 = 0
hum2 = 0
smoke = 0
light_num = 0  # 灯光模式编号

# 回调函数：通用消息处理器
async def general_message_handler(msg):
    print(f"[BLINKER消息] 收到数据: {msg}")
    if 'fromDevice' in msg:
        from_device = msg['fromDevice']
        print(f"来自设备: {from_device}")
        if 'data' in msg:
            for key, value in msg['data'].items():
                print(f"  数据项: {key} = {value}")
    return msg

# 串口参数
VOICE_PORT = 'com23'
VOICE_BAUD_RATE = 9600
VOICE_TIMEOUT = 1

LORA_PORT = 'COM16'
LORA_BAUD_RATE = 115200
LORA_TIMEOUT = 1

DISPLAY_MODE4K = False
auto_fan = False
auto_door = False
blink_door = False
blink_hood = False
blink_fan = False
blink_window = False
blink_curtain = False

# 图片路径
IMG_PATH = r"E:\Arduinoproject\智能家居\PIC"
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

# 全局串口对象
voice_ser = None
lora_ser = None
send_lora_Times = 3
is_sending = False

# 问询设备配置
inquiry_device_ids = [2, 3, 4]
asktime = 10000
devices_asktime = asktime * (len(inquiry_device_ids) + 1)
xiaozhi_asktime = 20000
internet_asktime = 3000
temp = ["", ""]

def get_current_connected_wifi():
    try:
        result = subprocess.check_output(
            ["iwgetid", "-r"],
            stderr=subprocess.STDOUT,
            text=True
        ).strip()
        if not result:
            print("未检测到当前连接的WiFi")
            return None
        current_ssid = result
    except Exception as e:
        print(f"获取SSID时出错：{str(e)}")
        return None

    wifi_config_path = "/etc/wpa_supplicant/wpa_supplicant.conf"
    try:
        with open(wifi_config_path, 'r') as f:
            lines = f.readlines()
            current_psk = None
            in_target_network = False
            for line in lines:
                line = line.strip()
                if line.startswith('network='):
                    in_target_network = False
                elif line.startswith('ssid='):
                    ssid = line.split('=', 1)[1].strip('"')
                    if ssid == current_ssid:
                        in_target_network = True
                elif in_target_network and line.startswith('psk='):
                    current_psk = line.split('=', 1)[1].strip('"')
                    break
            if current_psk:
                return current_ssid, current_psk
            else:
                print(f"未找到 {current_ssid} 的密码")
                return None
    except Exception as e:
        print(f"读取配置文件时出错：{str(e)}")
        return None

# LoRa指令发送
def send_lora_command(device_id, node_id, action):
    global lora_ser, is_sending
    while is_sending:
        time.sleep(0.1)
    is_sending = True
    try:
        if not lora_ser or not lora_ser.is_open:
            print("[错误] LoRa串口未初始化")
            return
        header1 = 0x55
        header2 = 0xAA
        checksum = 0xFF
        command = bytes([header1, header2, device_id, node_id, action, checksum])
        if (device_id == 0x01 and 0x0F <= node_id <= 0x13) or \
           (device_id == 0x02 and 0x01 <= node_id <= 0x08) or \
           (device_id == 0x03 and 0x01 <= node_id <= 0x02) or \
           (device_id == 0x04 and 0x01 <= node_id <= 0x02):
            send_lora_Times = 2
        else:
            send_lora_Times = 3
        for attempt in range(send_lora_Times):
            lora_ser.write(command)
            hex_string = ' '.join(f'{b:02x}' for b in command)
            print(f"-> LoRa发送 (第{attempt+1}次): {hex_string}")
            time.sleep(0.6)
        time.sleep(0.2)
    except Exception as e:
        print(f"[错误] LoRa发送失败: {e}")
    finally:
        is_sending = False

def send_inquiry_frame(device_id=0x01):
    global lora_ser, is_sending
    while is_sending:
        time.sleep(0.1)
    is_sending = True
    try:
        if not lora_ser or not lora_ser.is_open:
            print("[错误] LoRa串口未打开")
            return
        inquiry_frame = bytes([0xFE, device_id, 0xFF])
        lora_ser.write(inquiry_frame)
        hex_string = ' '.join(f'{b:02x}' for b in inquiry_frame)
        print(f"-> 发送问询帧: {hex_string} (设备ID: {device_id})")
    except Exception as e:
        print(f"[错误] 发送问询帧失败: {e}")
    finally:
        is_sending = False

# 串口数据处理线程
class SerialWorker(QObject):
    data_received = pyqtSignal(str)
    data_voice_data = pyqtSignal(int, int, int)
    data_json = pyqtSignal(float, float, float, float, float, int, int, str)

    def __init__(self, port, baud_rate, timeout):
        super().__init__()
        self.port = port
        self._is_running = True
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.ser = None
        self.cached_living_tmp = 25.0
        self.cached_living_hum = 50.0
        self.cached_ba_tmp = 26.0
        self.cached_ba_hum = 55.0
        self.cached_smoke = 0.0
        self.cached_door_status = 0
        self.cached_hood_status = 0
        self.cached_MP3_name_status = 0
        self.last_update_time = time.time()

    def stop(self):
        self._is_running = False
        print("串口线程停止信号已发送")

    def send_data(self, data):
        global lora_ser, is_sending
        while is_sending:
            time.sleep(0.1)
        is_sending = True
        try:
            if lora_ser and lora_ser.is_open:
                for attempt in range(3):
                    lora_ser.write(data)
                    hex_string = ' '.join(f'{b:02x}' for b in data)
                    print(f"-> LoRa发送 (第{attempt+1}次): {hex_string}")
                    time.sleep(1)
                lora_ser.flush()
        except Exception as e:
            print(f"[发送] 错误: {str(e)}")
        finally:
            is_sending = False

    def handle_json_data(self, data):
        if isinstance(data, bytes):
            data = data.decode('utf-8', errors='ignore')
        if '{' in data and '}' in data:
            self._process_json_data(data)
        else:
            print(f"[JSON] 无效格式: {data}")

    def _process_json_data(self, json_buffer):
        global temp1, hum1, temp2, hum2, auto_fan
        try:
            json_data = json.loads(json_buffer)
            living_tmp = json_data.get("l_tmp", self.cached_living_tmp)
            living_hum = json_data.get("l_hum", self.cached_living_hum)
            ba_tmp = json_data.get("b_tmp", self.cached_ba_tmp)
            ba_hum = json_data.get("b_hum", self.cached_ba_hum)
            smoke = json_data.get("smoke", self.cached_smoke)
            door_status = json_data.get("door_status", self.cached_door_status)
            hood_status = json_data.get("hood_status", self.cached_hood_status)
            MP3_Name = json_data.get("MP3_Name", self.cached_MP3_name_status)

            self.cached_living_tmp = float(living_tmp)
            self.cached_living_hum = float(living_hum)
            self.cached_ba_tmp = float(ba_tmp)
            self.cached_ba_hum = float(ba_hum)
            self.cached_smoke = float(smoke)
            self.cached_door_status = int(door_status)
            self.cached_hood_status = int(hood_status)
            self.cached_MP3_name_status = str(MP3_Name)

            temp1 = living_tmp
            hum1 = living_hum
            temp2 = ba_tmp
            hum2 = ba_hum

            if auto_fan:
                if hum2 > hum2_threshold:
                    send_lora_command(0x02, 0x0F, 0x00)
                    print("浴室风扇自动开启")
                else:
                    send_lora_command(0x02, 0x11, 0x00)
                    print("浴室风扇自动关闭")

            self.data_json.emit(
                float(living_tmp), float(living_hum), float(ba_tmp),
                float(ba_hum), float(smoke), int(door_status),
                int(hood_status), str(MP3_Name)
            )
        except json.JSONDecodeError as e:
            print(f"[JSON] 解析失败: {e}")
        except Exception as e:
            print(f"[JSON] 处理错误: {e}")
        self.json_buffer = ""

    def handle_Voice_data(self, data):
        try:
            if not data.strip():
                return
            clean_data = data.strip().replace(' ', '')
            if len(clean_data) % 2 != 0 or not re.match(r'^[0-9a-fA-F]+$', clean_data):
                print(f"[语音] 无效格式: {data}")
                return
            hex_bytes = [int(clean_data[i:i+2], 16) for i in range(0, len(clean_data), 2)]
            if len(hex_bytes) >= 5 and hex_bytes[0] == 0x55:
                device_id = hex_bytes[2] if len(hex_bytes) > 2 else 0
                node = hex_bytes[3] if len(hex_bytes) > 3 else 0
                command = 0
                send_lora_command(device_id, node, command)
                self.data_voice_data.emit(device_id, node, command)
            else:
                print(f"[语音] 无效指令帧: {hex_bytes}")
        except Exception as e:
            print(f"[语音] 处理错误: {e}")

    def run(self):
        print("串口监听线程启动")
        while self._is_running:
            try:
                if voice_ser and voice_ser.is_open:
                    raw_data = voice_ser.read(6)
                    if raw_data:
                        hex_data = ' '.join(f'{b:02x}' for b in raw_data)
                        print(f"<- 语音接收: {hex_data}")
                        self.handle_Voice_data(hex_data)
                time.sleep(0.01)
            except Exception as e:
                print(f"[串口] 错误: {e}")
                time.sleep(2)

            try:
                if lora_ser and lora_ser.is_open:
                    if not hasattr(self, 'json_buffer'):
                        self.json_buffer = b''
                        self.is_collecting_json = False
                        self.json_start_time = time.time()
                    raw_data = lora_ser.readline(64)
                    if raw_data:
                        for byte in raw_data:
                            if byte == ord('{'):
                                self.is_collecting_json = True
                                self.json_buffer = b'{'
                                self.json_start_time = time.time()
                            elif byte == ord('}') and self.is_collecting_json:
                                self.json_buffer += b'}'
                                try:
                                    json_str = self.json_buffer.decode('utf-8', errors='ignore').strip()
                                    self.handle_json_data(json_str)
                                except Exception as e:
                                    print(f"[JSON] 处理错误: {e}")
                                self.json_buffer = b''
                                self.is_collecting_json = False
                            elif self.is_collecting_json:
                                self.json_buffer += bytes([byte])
            except Exception as e:
                print(f"[LoRa] 处理错误: {e}")
                self.json_buffer = b''
                self.is_collecting_json = False
                time.sleep(0.1)

# Blinker处理线程（核心修改部分）
class BlinkerWorker(QObject):
    blinker_msg_signal = pyqtSignal(str, str)
    connect_status_signal = pyqtSignal(bool, str)  # 连接状态信号

    def __init__(self):
        super().__init__()
        self._is_running = True
        self.blinker_loop = None
        self.device = None
        self.is_connected = False  # 连接状态标记
        self.retry_interval = 5  # 重试间隔（秒）
        self.blinker_temp1 = 0
        self.blinker_temp2 = 0
        self.blinker_hum1 = 0
        self.blinker_hum2 = 0
        self.blinker_smoke = 0
        self.cached_living_tmp = 0
        self.cached_living_hum = 0
        self.cached_ba_tmp = 0
        self.cached_ba_hum = 0
        self.cached_smoke = 0
        self.device_states = {
            "led01": "off", "led02": "off", "led03": "off", "fan01": "off",
            "fan02": "off", "wind01": "off", "wind02": "off", "door": "off"
        }

    def stop(self):
        self._is_running = False
        self.is_connected = False
        if self.blinker_loop and not self.blinker_loop.is_closed():
            self.blinker_loop.stop()
        print("Blinker线程已停止")

    def tr_data(self, temp1, hum1, tmp2, hum2, smoke):
        self.blinker_temp1 = temp1
        self.blinker_hum1 = hum1
        self.blinker_temp2 = tmp2
        self.blinker_hum2 = hum2
        self.blinker_smoke = smoke
        self.cached_living_tmp = temp1
        self.cached_living_hum = hum1
        self.cached_ba_tmp = tmp2
        self.cached_ba_hum = hum2
        self.cached_smoke = smoke
        self.send_data_to_app()

    def send_data_to_app(self):
        if hasattr(self, 'device') and self.device and self.is_connected:
            try:
                if self.blinker_loop and not self.blinker_loop.is_closed():
                    async def send_data():
                        try:
                            await self.device.sendRtData("temp01", lambda: self.cached_living_tmp)
                            await self.device.sendRtData("hum01", lambda: self.cached_living_hum)
                            await self.device.sendRtData("temp02", lambda: self.cached_ba_tmp)
                            await self.device.sendRtData("hum02", lambda: self.cached_ba_hum)
                        except Exception as e:
                            print(f"[Blinker] 数据发送失败: {e}")
                    asyncio.run_coroutine_threadsafe(send_data(), self.blinker_loop)
            except Exception as e:
                print(f"[Blinker] 发送错误: {e}")

    def update_device_state(self, control_key, state):
        if control_key in self.device_states:
            self.device_states[control_key] = state

    async def connect_blinker(self):
        """尝试连接Blinker服务器"""
        try:
            if not self.device:
                self.device = Device("f9094bf7c991", heartbeat_func=self.heartbeat_func)
                # 初始化控件
                self.led01_key = self.device.addWidget(ButtonWidget('led01'))
                self.led02_key = self.device.addWidget(ButtonWidget('led02'))
                self.led03_key = self.device.addWidget(ButtonWidget('led03'))
                self.led04_key = self.device.addWidget(ButtonWidget('led04'))
                self.led05_key = self.device.addWidget(ButtonWidget('led05'))
                self.fan01_key = self.device.addWidget(ButtonWidget('fan01'))
                self.fan02_key = self.device.addWidget(ButtonWidget('fan02'))
                self.wind01_key = self.device.addWidget(ButtonWidget('wind01'))
                self.wind02_key = self.device.addWidget(ButtonWidget('wind02'))
                self.wind03_key = self.device.addWidget(ButtonWidget('wind03'))
                self.door_key = self.device.addWidget(ButtonWidget('door'))
                self.light_change_key = self.device.addWidget(ButtonWidget('led10'))
                self.desk_up_key = self.device.addWidget(ButtonWidget('desk01'))
                self.desk_down_key = self.device.addWidget(ButtonWidget('desk02'))
                self.desk_stop_key = self.device.addWidget(ButtonWidget('desk03'))
                self.mp3_start_key = self.device.addWidget(ButtonWidget('mp301'))
                self.mp3_stop_key = self.device.addWidget(ButtonWidget('mp302'))
                self.mp3_play_key = self.device.addWidget(ButtonWidget('mp303'))
                self.mp3_pause_key = self.device.addWidget(ButtonWidget('mp304'))
                self.mp3_prev_key = self.device.addWidget(ButtonWidget('mp310'))
                self.mp3_next_key = self.device.addWidget(ButtonWidget('mp311'))
                self.mp3_volume_up_key = self.device.addWidget(ButtonWidget('jia'))
                self.mp3_volume_down_key = self.device.addWidget(ButtonWidget('jian'))

                self.temp1_num = self.device.addWidget(NumberWidget('temp01'))
                self.hum1_num = self.device.addWidget(NumberWidget('hum01'))
                self.temp2_num = self.device.addWidget(NumberWidget('temp02'))
                self.hum2_num = self.device.addWidget(NumberWidget('hum02'))
                self.smoke_num = self.device.addWidget(NumberWidget('smoke'))

                # 绑定回调
                self.led01_key.func = self.led01_key_handler
                self.led02_key.func = self.led02_key_handler
                self.led03_key.func = self.led03_key_handler
                self.led04_key.func = self.led04_key_handler
                self.led05_key.func = self.led05_key_handler
                self.fan01_key.func = self.fan01_key_handler
                self.fan02_key.func = self.fan02_key_handler
                self.wind01_key.func = self.wind01_key_handler
                self.wind02_key.func = self.wind02_key_handler
                self.wind03_key.func = self.wind03_key_handler
                self.door_key.func = self.door_key_handler
                self.light_change_key.func = self.light_change_key_handler
                self.desk_up_key.func = self.desk_up_key_handler
                self.desk_down_key.func = self.desk_down_key_handler
                self.desk_stop_key.func = self.desk_stop_key_handler
                self.mp3_start_key.func = self.mp3_start_key_handler
                self.mp3_stop_key.func = self.mp3_stop_key_handler
                self.mp3_play_key.func = self.mp3_play_key_handler
                self.mp3_pause_key.func = self.mp3_pause_key_handler
                self.mp3_prev_key.func = self.mp3_prev_key_handler
                self.mp3_next_key.func = self.mp3_next_key_handler
                self.mp3_volume_up_key.func = self.mp3_volume_up_key_handler
                self.mp3_volume_down_key.func = self.mp3_volume_down_key_handler

            await self.device.run()
            return True
        except Exception as e:
            print(f"[Blinker] 连接失败: {e}")
            return False

    async def connection_loop(self):
        """连接重试循环"""
        while self._is_running and not self.is_connected:
            self.connect_status_signal.emit(False, f"尝试连接Blinker...（{self.retry_interval}秒后重试）")
            success = await self.connect_blinker()
            if success:
                self.is_connected = True
                self.connect_status_signal.emit(True, "Blinker连接成功")
                print("Blinker连接成功，停止重试")
                break
            else:
                await asyncio.sleep(self.retry_interval)

    def heartbeat_func(self, msg):
        """心跳回调：确认连接成功"""
        self.is_connected = True
        print(f"[Blinker] 心跳确认: {msg}")
        try:
            asyncio.run_coroutine_threadsafe(
                self._update_heartbeat_data(), self.blinker_loop
            )
        except Exception as e:
            print(f"[Blinker] 心跳数据更新失败: {e}")

    async def _update_heartbeat_data(self):
        """心跳时更新数据"""
        await self.temp1_num.value(self.cached_living_tmp).update()
        await self.hum1_num.value(self.cached_living_hum).update()
        await self.temp2_num.value(self.cached_ba_tmp).update()
        await self.hum2_num.value(self.cached_ba_hum).update()
        await self.smoke_num.value(self.cached_smoke).update()

    # 设备控制回调（与原逻辑一致）
    async def led01_key_handler(self, msg):
        if msg['led01'] == 'on':
            self.blinker_msg_signal.emit("led01", "on")
            await self.led01_key.turn('on').color('#FF8C00').text('主卧灯光打开').update()
        elif msg['led01'] == 'off':
            self.blinker_msg_signal.emit("led01", "off")
            await self.led01_key.turn('off').color('#101010').text('主卧灯光已关闭').update()

    async def led02_key_handler(self, msg):
        if msg['led02'] == 'on':
            self.blinker_msg_signal.emit("led02", "on")
            await self.led02_key.turn('on').color('#FF8C00').text('次卧灯光打开').update()
        elif msg['led02'] == 'off':
            self.blinker_msg_signal.emit("led02", "off")
            await self.led02_key.turn('off').color('#101010').text('次卧灯光已关闭').update()

    async def led03_key_handler(self, msg):
        if msg['led03'] == 'on':
            self.blinker_msg_signal.emit("led03", "on")
            await self.led03_key.turn('on').color('#FF8C00').text('客厅灯光打开').update()
        elif msg['led03'] == 'off':
            self.blinker_msg_signal.emit("led03", "off")
            await self.led03_key.turn('off').color('#101010').text('客厅灯光已关闭').update()

    async def led04_key_handler(self, msg):
        if msg['led04'] == 'on':
            self.blinker_msg_signal.emit("led04", "on")
            await self.led04_key.turn('on').color('#FF8C00').text('书房灯光打开').update()
        elif msg['led04'] == 'off':
            self.blinker_msg_signal.emit("led04", "off")
            await self.led04_key.turn('off').color('#101010').text('书房灯光已关闭').update()

    async def led05_key_handler(self, msg):
        if msg['led05'] == 'on':
            self.blinker_msg_signal.emit("led05", "on")
            await self.led05_key.turn('on').color('#FF8C00').text('卫生间灯光打开').update()
        elif msg['led05'] == 'off':
            self.blinker_msg_signal.emit("led05", "off")
            await self.led05_key.turn('off').color('#101010').text('卫生间灯光已关闭').update()

    async def fan01_key_handler(self, msg):
        if msg['fan01'] == 'on':
            self.blinker_msg_signal.emit("fan01", "on")
            await self.fan01_key.turn('on').color('#FF8C00').text('油烟机打开').update()
        elif msg['fan01'] == 'off':
            self.blinker_msg_signal.emit("fan01", "off")
            await self.fan01_key.turn('off').color('#101010').text('油烟机已关闭').update()
        elif msg['fan01'] == 'pressup':
            self.blinker_msg_signal.emit("fan01", "auto")
            await self.fan01_key.turn('auto').color('#FF8C00').text('自动油烟机').update()

    async def fan02_key_handler(self, msg):
        if msg['fan02'] == 'on':
            self.blinker_msg_signal.emit("fan02", "on")
            await self.fan02_key.turn('on').color('#FF8C00').text('排风扇打开').update()
        elif msg['fan02'] == 'off':
            self.blinker_msg_signal.emit("fan02", "off")
            await self.fan02_key.turn('off').color('#101010').text('排风扇已关闭').update()
        elif msg['fan02'] == 'pressup':
            self.blinker_msg_signal.emit("fan02", "auto")
            await self.fan02_key.turn('auto').color('#FF8C00').text('自动排风扇').update()

    async def wind01_key_handler(self, msg):
        if msg['wind01'] == 'on':
            self.blinker_msg_signal.emit("wind01", "on")
            await self.wind01_key.turn('on').color('#FF8C00').text('主卧窗帘打开').update()
        elif msg['wind01'] == 'off':
            self.blinker_msg_signal.emit("wind01", "off")
            await self.wind01_key.turn('off').color('#101010').text('主卧窗帘已关闭').update()

    async def wind02_key_handler(self, msg):
        if msg['wind02'] == 'on':
            self.blinker_msg_signal.emit("wind02", "on")
            await self.wind02_key.turn('on').color('#FF8C00').text('次卧窗帘打开').update()
        elif msg['wind02'] == 'off':
            self.blinker_msg_signal.emit("wind02", "off")
            await self.wind02_key.turn('off').color('#101010').text('次卧窗帘已关闭').update()

    async def wind03_key_handler(self, msg):
        if msg['wind03'] == 'on':
            self.blinker_msg_signal.emit("wind03", "on")
            await self.wind03_key.turn('on').color('#FF8C00').text('客厅窗帘打开').update()
        elif msg['wind03'] == 'off':
            self.blinker_msg_signal.emit("wind03", "off")
            await self.wind03_key.turn('off').color('#101010').text('客厅窗帘已关闭').update()

    async def door_key_handler(self, msg):
        if msg['door'] == 'on':
            self.blinker_msg_signal.emit("door", "on")
            await self.door_key.turn('on').color('#FF8C00').text('门打开').update()
        elif msg['door'] == 'off':
            self.blinker_msg_signal.emit("door", "off")
            await self.door_key.turn('off').color('#101010').text('门已关闭').update()
        elif msg['door'] == 'pressup':
            self.blinker_msg_signal.emit("door", "auto")
            await self.door_key.turn('auto').color('#FF8C00').text('自动门').update()

    async def desk_up_key_handler(self, msg):
        if msg['desk01'] == 'tap':
            self.blinker_msg_signal.emit("desk01", "tap")

    async def desk_down_key_handler(self, msg):
        if msg['desk02'] == 'tap':
            self.blinker_msg_signal.emit("desk02", "tap")

    async def desk_stop_key_handler(self, msg):
        if msg['desk03'] == 'tap':
            self.blinker_msg_signal.emit("desk03", "tap")

    async def mp3_start_key_handler(self, msg):
        if msg['mp301'] == 'tap':
            self.blinker_msg_signal.emit("mp301", "tap")

    async def mp3_stop_key_handler(self, msg):
        if msg['mp302'] == 'tap':
            self.blinker_msg_signal.emit("mp302", "tap")

    async def mp3_play_key_handler(self, msg):
        if msg['mp303'] == 'tap':
            self.blinker_msg_signal.emit("mp303", "tap")

    async def mp3_pause_key_handler(self, msg):
        if msg['mp304'] == 'tap':
            self.blinker_msg_signal.emit("mp304", "tap")

    async def mp3_prev_key_handler(self, msg):
        if msg['mp310'] == 'tap':
            self.blinker_msg_signal.emit("mp310", "tap")

    async def mp3_next_key_handler(self, msg):
        if msg['mp311'] == 'tap':
            self.blinker_msg_signal.emit("mp311", "tap")

    async def mp3_volume_up_key_handler(self, msg):
        if msg['jia'] == 'tap':
            self.blinker_msg_signal.emit("jia", "tap")

    async def mp3_volume_down_key_handler(self, msg):
        if msg['jian'] == 'tap':
            self.blinker_msg_signal.emit("jian", "tap")

    async def light_change_key_handler(self, msg):
        global light_num
        if msg['led10'] == 'tap' and light_num == 0:
            self.blinker_msg_signal.emit("led10", "breath")
            await self.light_change_key.turn('tap').color('#FF8C00').text('呼吸灯').update()
            light_num = 1
        elif msg['led10'] == 'tap' and light_num == 1:
            self.blinker_msg_signal.emit("led10", "water")
            await self.light_change_key.turn('tap').color('#111111').text('流水灯').update()
            light_num = 2
        elif msg['led10'] == 'tap' and light_num == 2:
            self.blinker_msg_signal.emit("led10", "red")
            await self.light_change_key.turn('tap').color('#FF0000').text('红').update()
            light_num = 3
        elif msg['led10'] == 'tap' and light_num == 3:
            self.blinker_msg_signal.emit("led10", "orange")
            await self.light_change_key.turn('tap').color('#FFA500').text('橙').update()
            light_num = 4
        elif msg['led10'] == 'tap' and light_num == 4:
            self.blinker_msg_signal.emit("led10", "yellow")
            await self.light_change_key.turn('tap').color('#FFFF00').text('黄').update()
            light_num = 5
        elif msg['led10'] == 'tap' and light_num == 5:
            self.blinker_msg_signal.emit("led10", "green")
            await self.light_change_key.turn('tap').color('#00FF00').text('绿').update()
            light_num = 6
        elif msg['led10'] == 'tap' and light_num == 6:
            self.blinker_msg_signal.emit("led10", "blue")
            await self.light_change_key.turn('tap').color('#0000FF').text('蓝').update()
            light_num = 7
        elif msg['led10'] == 'tap' and light_num == 7:
            self.blinker_msg_signal.emit("led10", "indigo")
            await self.light_change_key.turn('tap').color('#4B0082').text('靛').update()
            light_num = 8
        elif msg['led10'] == 'tap' and light_num == 8:
            self.blinker_msg_signal.emit("led10", "violet")
            await self.light_change_key.turn('tap').color('#9400D3').text('紫').update()
            light_num = 0
        elif msg['led10'] == 'pressup':
            self.blinker_msg_signal.emit("led10", "close")
            await self.light_change_key.turn('tap').color('#101010').text('关闭全部灯').update()
            light_num = 0

    def run(self):
        """启动Blinker线程"""
        print("Blinker后台线程启动")
        try:
            self.blinker_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.blinker_loop)
            self.blinker_loop.run_until_complete(self.connection_loop())
            if self.is_connected and self._is_running:
                self.blinker_loop.run_forever()
        except Exception as e:
            print(f"[Blinker] 线程异常: {e}")
        finally:
            if self.blinker_loop and not self.blinker_loop.is_closed():
                self.blinker_loop.close()

# 主窗口
class MainWindow(QMainWindow):
    def __init__(self, blinker_worker=None):
        super().__init__()
        uic.loadUi('E:\Arduinoproject\智能家居\main.ui', self)
        self.blinker_worker = blinker_worker
        self.set_background_image()
        self.init_inquiry_timer()
        self.init_labels()
        self.init_gauges()
        self.Load_pics()
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.check_internet_connection)
        self.time_timer.start(internet_asktime)
        self.statusBar().showMessage("系统启动中...")
        if self.blinker_worker:
            self.blinker_worker.connect_status_signal.connect(self.update_connect_status)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
        elif event.key() == Qt.Key_Q:
            self.close()
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def check_internet_connection(self):
        try:
            import platform
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["ping", "-n", "1", "-w", "1000", "www.baidu.com"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
            else:
                result = subprocess.run(
                    ["ping", "-c", "1", "-W", "1", "www.baidu.com"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
            if result.returncode == 0:
                self.Load_pic(self.wifi_status, WIFI_ON_IMAGE)
            else:
                self.Load_pic(self.wifi_status, WIFI_OFF_IMAGE)
        except Exception as e:
            print(f"检查网络连接错误: {str(e)}")

    def set_background_image(self):
        image_path = BACKGROUND_IMAGE
        try:
            pixmap = QPixmap(image_path)
            self.background_label = QLabel(self)
            if DISPLAY_MODE4K:
                self.image_width = 3840
                self.image_height = 2160
            else:
                self.image_width = 1280
                self.image_height = 800
            self.resize(self.image_width, self.image_height)
            scaled_pixmap = pixmap.scaled(
                self.image_width, self.image_height,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.background_label.setGeometry(0, 0, self.image_width, self.image_height)
            self.background_label.setPixmap(scaled_pixmap)
            self.background_label.setAlignment(Qt.AlignCenter)
            self.background_label.lower()
        except Exception as e:
            print(f"设置背景图片出错: {e}")

    def init_inquiry_timer(self):
        self.inquiry_timer = QTimer(self)
        self.inquiry_timer.timeout.connect(self.send_inquiry)
        self.inquiry_timer.start(devices_asktime)
        print(f"问询定时器启动，间隔{devices_asktime/1000}秒")
        self.send_inquiry()

    def send_inquiry(self):
        self.current_device_index = 0
        if hasattr(self, 'device_timer'):
            self.device_timer.stop()
        self.device_timer = QTimer(self)
        self.device_timer.timeout.connect(self.send_next_inquiry)
        self.send_next_inquiry()
        self.device_timer.start(asktime)

    def send_next_inquiry(self):
        if self.current_device_index < len(inquiry_device_ids):
            device_id = inquiry_device_ids[self.current_device_index]
            send_inquiry_frame(device_id=device_id)
            self.current_device_index += 1
        else:
            self.device_timer.stop()
            print("本轮设备问询完成")
            if not self.inquiry_timer.isActive():
                self.inquiry_timer.start(devices_asktime)

    def init_label(self, label, initial_value, font=12, color="rgb(186,128,0)"):
        label.setText(str(initial_value))
        label.setFont(QFont("SimHei", font, QFont.Bold))
        label.setStyleSheet(f"color: {color};")
        label.setAlignment(Qt.AlignCenter)
        label.raise_()

    def init_labels(self):
        self.init_label(self.temp1_label, "88℃", font=7, color="black")
        self.init_label(self.hum1_label, "88.8%", font=7, color="black")
        self.init_label(self.temp2_label, "88℃", font=7, color="black")
        self.init_label(self.hum2_label, "88.8%", font=7, color="black")
        self.init_label(self.living_light_label, "关闭", font=9, color="black")
        self.init_label(self.kitchen_smoke_label, "8888", font=9, color="black")
        self.init_label(self.hostroom_curtain_label, "关闭", font=9, color="black")
        self.init_label(self.hostroom_light_label, "关闭", font=9, color="black")
        self.init_label(self.music_name_label, "001", font=9, color="black")
        self.init_label(self.secound_curtain_label, "关闭", font=9, color="black")
        self.init_label(self.secound_light_label, "关闭", font=9, color="black")
        self.init_label(self.study_desk_label, "正常", font=9, color="black")
        self.init_label(self.study_light_label, "关闭", font=9, color="black")

    def Load_pic(self, Label, pic_path):
        if Label is not None:
            self.pic_set = QPixmap(pic_path)
            self.pic_set = self.pic_set.scaled(
                Label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            Label.setPixmap(self.pic_set)
            time.sleep(0.1)

    def Load_pics(self):
        self.Load_pic(self.living_window_label, OFF_IMAGE)
        self.Load_pic(self.bathroom_fan_label, OFF_IMAGE)
        self.Load_pic(self.door_label, OFF_IMAGE)
        self.Load_pic(self.autodoor_label, AUTO_OFF_IMAGE)
        self.Load_pic(self.kitchen_hood_label, OFF_IMAGE)
        self.Load_pic(self.music_label, STOP_IMAGE)
        self.Load_pic(self.wifi_status, WIFI_OFF_IMAGE)

    def ask_xiaozhi_network(self):
        try:
            ask_data = {"event": "ask"}
            ask_json_str = json.dumps(ask_data) + '\n'
            if hasattr(self, 'xiaozhi_timer') and self.xiaozhi_timer is not None:
                self.xiaozhi_timer.stop()
            lora_ser.write(ask_json_str.encode('utf-8'))
            print(f"发送问询帧到小智: {ask_json_str.strip()}")
            self.init_label(self.xiaozhi_status, "小智未连接", "gray")
            if hasattr(self, 'xiaozhi_timer') and self.xiaozhi_timer is not None:
                self.xiaozhi_timer.start(xiaozhi_asktime)
        except Exception as e:
            print(f"发送问询时出错: {str(e)}")

    def init_gauge(self, name, min_val, max_val, colors, width, height, x, y, gauge_width=20,
                   start_angle=None, total_angle=None, initial_value=0):
        gauge = GaugeWidget(self, min_value=min_val, max_value=max_val, colors=colors, gauge_width=gauge_width)
        gauge.setGeometry(x, y, width, height)
        if start_angle is not None:
            gauge.setStartAngle(start_angle)
        if total_angle is not None:
            gauge.setTotalAngle(total_angle)
        gauge.setValue(initial_value)
        gauge.raise_()
        setattr(self, name, gauge)
        return gauge

    def init_gauges(self):
        big_gauge_width = 7
        default_width = 108
        default_height = 108
        gauges_config = [
            {
                'name': 'temp1_gauge',
                'min_val': 0.0,
                'max_val': 60.0,
                'colors': [QColor(255, 253, 209), QColor(255, 0, 0), QColor(255, 100, 0)],
                'width': default_width,
                'height': default_height,
                'x': 57,
                'y': 278,
                'gauge_width': big_gauge_width,
                'initial_value': 60
            },
            {
                'name': 'hum1_gauge',
                'min_val': 0.0,
                'max_val': 100.0,
                'colors': [QColor(1, 253, 209), QColor(85, 255, 243), QColor(25, 234, 255)],
                'width': default_width,
                'height': default_height,
                'x': 199,
                'y': 278,
                'gauge_width': big_gauge_width,
                'initial_value': 100
            },
            {
                'name': 'temp2_gauge',
                'min_val': 0.0,
                'max_val': 60.0,
                'colors': [QColor(255, 253, 209), QColor(255, 0, 0), QColor(255, 100, 0)],
                'width': default_width,
                'height': default_height,
                'x': 661,
                'y': 278,
                'gauge_width': big_gauge_width,
                'initial_value': 60
            },
            {
                'name': 'hum2_gauge',
                'min_val': 0.0,
                'max_val': 100.0,
                'colors': [QColor(1, 253, 209), QColor(85, 255, 243), QColor(25, 234, 255)],
                'width': default_width,
                'height': default_height,
                'x': 661 + 142,
                'y': 278,
                'gauge_width': big_gauge_width,
                'initial_value': 100
            }
        ]
        for config in gauges_config:
            self.init_gauge(** config)

    def update_display(self, data):
        print(f"数据更新: {data}")

    def update_voice_display(self, device_id, node, command):
        global auto_fan, auto_door
        if device_id == 0x01:
            if node == 0x01:
                print("打开主卧灯光")
                self.init_label(self.hostroom_light_label, "开启", font=9, color="black")
            elif node == 0x02:
                print("关闭主卧灯光")
                self.init_label(self.hostroom_light_label, "关闭", font=9, color="black")
            elif node == 0x03:
                print("打开次卧灯光")
                self.init_label(self.secound_light_label, "开启", font=9, color="black")
            elif node == 0x04:
                print("关闭次卧灯光")
                self.init_label(self.secound_light_label, "关闭", font=9, color="black")
            elif node == 0x05:
                print("打开客厅灯光")
                self.init_label(self.living_light_label, "开启", font=9, color="black")
            elif node == 0x06:
                print("关闭客厅灯光")
                self.init_label(self.living_light_label, "关闭", font=9, color="black")
            elif node == 0x09:
                print("打开书房灯光")
                self.init_label(self.study_light_label, "开启", font=9, color="black")
            elif node == 0x0A:
                print("关闭书房灯光")
                self.init_label(self.study_light_label, "关闭", font=9, color="black")
            elif node == 0x0D:
                print("打开全部灯光")
                self.init_label(self.hostroom_light_label, "开启", font=9, color="black")
                self.init_label(self.secound_light_label, "开启", font=9, color="black")
                self.init_label(self.living_light_label, "开启", font=9, color="black")
                self.init_label(self.study_light_label, "开启", font=9, color="black")
            elif node == 0x0E:
                print("关闭全部灯光")
                self.init_label(self.hostroom_light_label, "关闭", font=9, color="black")
                self.init_label(self.secound_light_label, "关闭", font=9, color="black")
                self.init_label(self.living_light_label, "关闭", font=9, color="black")
                self.init_label(self.study_light_label, "关闭", font=9, color="black")
        elif device_id == 0x02:
            if node == 0x01:
                print("MP3播放")
                self.init_label(self.music_name_label, "播放", font=9, color="black")
                self.Load_pic(self.music_label, PLAY_IMAGE)
            elif node == 0x02:
                print("暂停mp3")
                self.init_label(self.music_name_label, "暂停", font=9, color="black")
                self.Load_pic(self.music_label, STOP_IMAGE)
            elif node == 0x0F:
                print("打开排风")
                auto_fan = False
                self.Load_pic(self.bathroom_fan_label, ON_IMAGE)
            elif node == 0x11:
                print("关闭排风")
                auto_fan = False
                self.Load_pic(self.bathroom_fan_label, OFF_IMAGE)
        elif device_id == 0x03:
            if node == 0x03:
                print("打开门")
                auto_door = False
                self.Load_pic(self.door_label, ON_IMAGE)
                self.Load_pic(self.autodoor_label, AUTO_OFF_IMAGE)
            elif node == 0x04:
                print("关闭门")
                auto_door = False
                self.Load_pic(self.door_label, OFF_IMAGE)
                self.Load_pic(self.autodoor_label, AUTO_OFF_IMAGE)
        elif device_id == 0x04:
            if node == 0x01:
                print("打开窗户")
                self.Load_pic(self.living_window_label, ON_IMAGE)
            elif node == 0x02:
                print("关闭窗户")
                self.Load_pic(self.living_window_label, OFF_IMAGE)

    def update_xiaozhi_display(self, living_tmp, living_hum, ba_tmp, ba_hum, smoke, door_status, hood_status, MP3_Name):
        print(f"JSON数据: 客厅温度: {living_tmp}, 湿度: {living_hum}, 浴室温度: {ba_tmp}, 湿度: {ba_hum}")
        if door_status == 0:
            self.Load_pic(self.door_label, OFF_IMAGE)
        else:
            self.Load_pic(self.door_label, ON_IMAGE)
        if hood_status == 0:
            self.Load_pic(self.kitchen_hood_label, OFF_IMAGE)
        else:
            self.Load_pic(self.kitchen_hood_label, ON_IMAGE)
        self.init_label(self.kitchen_smoke_label, f"{smoke}", font=9, color="black")
        self.init_label(self.temp1_label, f"{living_tmp}℃", font=7, color="black")
        self.init_label(self.hum1_label, f"{living_hum}%", font=7, color="black")
        self.init_label(self.temp2_label, f"{ba_tmp}℃", font=7, color="black")
        self.init_label(self.hum2_label, f"{ba_hum}%", font=7, color="black")
        self.init_label(self.music_name_label, f"{MP3_Name}", font=9, color="black")
        if hasattr(self, 'blinker_worker') and self.blinker_worker:
            try:
                self.blinker_worker.tr_data(living_tmp, living_hum, ba_tmp, ba_hum, smoke)
            except Exception as e:
                print(f"发送数据到Blinker错误: {e}")

    def handle_blinker_message(self, control_key, command):
        print(f"Blinker指令: {control_key}, {command}")
        if control_key == "led01":
            if command == "on":
                send_lora_command(0x01, 0x01, 0x00)
                self.init_label(self.hostroom_light_label, "开启", font=9, color="black")
            elif command == "off":
                send_lora_command(0x01, 0x02, 0x00)
                self.init_label(self.hostroom_light_label, "关闭", font=9, color="black")
        elif control_key == "led02":
            if command == "on":
                send_lora_command(0x01, 0x03, 0x00)
                self.init_label(self.secound_light_label, "开启", font=9, color="black")
            elif command == "off":
                send_lora_command(0x01, 0x04, 0x00)
                self.init_label(self.secound_light_label, "关闭", font=9, color="black")
        elif control_key == "fan01":
            if command == "on":
                send_lora_command(0x03, 0x06, 0x00)
                self.Load_pic(self.kitchen_hood_label, ON_IMAGE)
            elif command == "off":
                send_lora_command(0x03, 0x07, 0x00)
                self.Load_pic(self.kitchen_hood_label, OFF_IMAGE)
        # 其他设备控制逻辑与原代码一致...

    def update_connect_status(self, success, msg):
        """更新Blinker连接状态到状态栏"""
        self.statusBar().showMessage(f"Blinker状态: {msg}")

# 主程序入口
def main():
    global voice_ser, lora_ser
    serial_worker = None
    worker_thread = None
    blinker_worker = None
    blinker_thread = None
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("校园沙盘控制系统")

        print("初始化串口...")
        try:
            voice_ser = serial.Serial(VOICE_PORT, VOICE_BAUD_RATE, timeout=VOICE_TIMEOUT)
            print(f"成功打开语音串口 {VOICE_PORT}")
        except serial.SerialException as e:
            print(f"警告: 无法打开语音串口 {VOICE_PORT}: {e}")

        try:
            lora_ser = serial.Serial(LORA_PORT, LORA_BAUD_RATE, timeout=LORA_TIMEOUT)
            print(f"成功打开LoRa串口 {LORA_PORT}")
        except serial.SerialException as e:
            print(f"警告: 无法打开LoRa串口 {LORA_PORT}: {e}")

        serial_worker = SerialWorker(VOICE_PORT, VOICE_BAUD_RATE, VOICE_TIMEOUT)
        worker_thread = QThread()
        blinker_worker = BlinkerWorker()
        blinker_thread = QThread()

        main_window = MainWindow(blinker_worker)

        serial_worker.moveToThread(worker_thread)
        blinker_worker.moveToThread(blinker_thread)

        worker_thread.started.connect(serial_worker.run)
        blinker_thread.started.connect(blinker_worker.run)

        serial_worker.data_received.connect(main_window.update_display)
        serial_worker.data_voice_data.connect(main_window.update_voice_display)
        serial_worker.data_json.connect(main_window.update_xiaozhi_display)
        blinker_worker.blinker_msg_signal.connect(main_window.handle_blinker_message)

        worker_thread.start()
        blinker_thread.start()

        main_window.show()
        print("系统启动完成")
        sys.exit(app.exec_())
    except Exception as e:
        print(f"程序异常: {e}")
    finally:
        if serial_worker:
            serial_worker.stop()
        if worker_thread and worker_thread.isRunning():
            worker_thread.quit()
            worker_thread.wait()
        if blinker_worker:
            blinker_worker.stop()
        if blinker_thread and blinker_thread.isRunning():
            blinker_thread.quit()
            blinker_thread.wait()
        if voice_ser and voice_ser.is_open:
            voice_ser.close()
            print(f"关闭语音串口 {VOICE_PORT}")
        if lora_ser and lora_ser.is_open:
            lora_ser.close()
            print(f"关闭LoRa串口 {LORA_PORT}")
        print("程序退出")

if __name__ == '__main__':
    main()