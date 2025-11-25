import logging
import random
import time
import asyncio
import sys
from blinker import Device, ButtonWidget, NumberWidget
from blinker.errors import BlinkerHttpException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# 替换为 App 中绑定的设备 ID（必须正确！）
# 请确保在 Blinker App 中已正确配置此设备
DEVICE_NAME = "f9094bf7c991"  

# 模拟传感器数据存储
sensor_data = {
    "temp01": 25.0,  # 客厅温度
    "hum01": 50.0,   # 客厅湿度
    "temp02": 26.0,  # 浴室温度
    "hum02": 60.0,   # 浴室湿度
}

# 定义要更新的控件
temp_widget = NumberWidget(key="temp01")
hum_widget = NumberWidget(key="hum01")

# 重试连接参数
MAX_RETRIES = 3
RETRY_DELAY = 5

def create_device():
    """创建设备实例，带重试机制"""
    for attempt in range(MAX_RETRIES):
        try:
            device = Device(DEVICE_NAME)
            logging.info(f"设备创建成功，尝试 {attempt + 1}/{MAX_RETRIES}")
            return device
        except Exception as e:
            logging.error(f"设备创建失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                logging.info(f"等待 {RETRY_DELAY} 秒后重试...")
                time.sleep(RETRY_DELAY)
            else:
                logging.error("所有重试均失败，无法创建设备")
                return None
    
device = create_device()
if device is None:
    logging.error("无法启动程序：设备初始化失败")
    sys.exit(1)

async def on_device_ready():
    """设备就绪时的回调函数"""
    logging.info(f"设备 {DEVICE_NAME} 连接成功，开始更新控件...")
    try:
        # 更新初始数据到App
        await temp_widget.update(sensor_data["temp01"])
        await hum_widget.update(sensor_data["hum01"])
        logging.info("已发送初始数据到App")
        
        # 启动定时数据更新任务
        start_periodic_update()
        
    except Exception as e:
        logging.error(f"更新失败：{e}")

async def realtime_func(keys):
    """实时数据请求处理函数 - 当App请求实时数据时调用"""
    logging.info(f"收到实时数据请求，keys: {keys}")
    try:
        for key in keys:
            if key in sensor_data:
                await device.sendRtData(key, sensor_data[key])
                logging.info(f"发送实时数据 {key}: {sensor_data[key]}")
            else:
                # 对于未知的键，返回默认数据
                await device.sendRtData(key, 0)
                logging.warning(f"未知的数据键: {key}")
    except Exception as e:
        logging.error(f"处理实时数据请求失败：{e}")

def update_sensor_data():
    """模拟传感器数据更新"""
    # 模拟真实环境下的数据变化
    sensor_data["temp01"] += random.uniform(-0.5, 0.5)
    sensor_data["hum01"] += random.uniform(-2.0, 2.0)
    sensor_data["temp02"] += random.uniform(-0.3, 0.3)
    sensor_data["hum02"] += random.uniform(-1.0, 1.0)
    
    # 保持数据在合理范围内
    sensor_data["temp01"] = max(15.0, min(35.0, sensor_data["temp01"]))
    sensor_data["hum01"] = max(20.0, min(80.0, sensor_data["hum01"]))
    sensor_data["temp02"] = max(15.0, min(35.0, sensor_data["temp02"]))
    sensor_data["hum02"] = max(20.0, min(80.0, sensor_data["hum02"]))
    
    return sensor_data.copy()

async def periodic_update():
    """定时更新数据到App"""
    while True:
        try:
            # 更新传感器数据
            current_data = update_sensor_data()
            
            # 发送到App
            await temp_widget.update(current_data["temp01"])
            await hum_widget.update(current_data["hum01"])
            
            logging.info(f"定时更新: temp01={current_data['temp01']:.1f}°C, hum01={current_data['hum01']:.1f}%")
            
            # 等待30秒后再次更新
            await asyncio.sleep(30)
            
        except Exception as e:
            logging.error(f"定时更新失败：{e}")
            await asyncio.sleep(5)  # 出错后等待5秒再试

def start_periodic_update():
    """启动定时更新任务"""
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(periodic_update())
        logging.info("定时更新任务已启动")
    except Exception as e:
        logging.error(f"启动定时任务失败：{e}")

# 设置设备回调函数
device.ready_func = on_device_ready
device.realtime_func = realtime_func

async def safe_device_run():
    """安全的设备运行函数，带异常处理和重试"""
    for attempt in range(MAX_RETRIES):
        try:
            logging.info(f"尝试连接到 Blinker 服务器 (尝试 {attempt + 1}/{MAX_RETRIES})...")
            await device.run()
            break
        except BlinkerHttpException as e:
            error_msg = str(e)
            if "502" in error_msg:
                logging.warning(f"502 错误：服务器暂时不可用 (尝试 {attempt + 1}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES - 1:
                    logging.info(f"等待 {RETRY_DELAY} 秒后重试...")
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    logging.error("多次 502 错误，服务器可能暂时不可用，请稍后重试")
                    break
            elif "401" in error_msg or "403" in error_msg:
                logging.error(f"认证错误：{error_msg}")
                logging.error("请检查设备 ID 和授权设置")
                break
            else:
                logging.error(f"HTTP 错误：{error_msg}")
                break
        except Exception as e:
            logging.error(f"设备运行错误：{e}")
            if attempt < MAX_RETRIES - 1:
                logging.info(f"等待 {RETRY_DELAY} 秒后重试...")
                await asyncio.sleep(RETRY_DELAY)
            else:
                logging.error("所有重试均失败")
                break

async def main():
    """主函数"""
    logging.info(f"启动智能家居设备 {DEVICE_NAME}...")
    logging.info("正在连接到 Blinker 云端...")
    
    try:
        await safe_device_run()
    except KeyboardInterrupt:
        logging.info("用户中断程序")
    except Exception as e:
        logging.error(f"程序运行异常：{e}")
    finally:
        logging.info("程序结束")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("程序终止")
    except Exception as e:
        logging.error(f"启动程序时出错：{e}")