#include <U8x8lib.h>  // OLED显示库
#include <Wire.h>     // I2C通信库（OLED依赖）

// -------------------------- 硬件引脚定义 --------------------------
#define LIQUID_LEVEL_PIN 13  // 液位传感器引脚（输入）
#define DEVICE_ID 0x0B  // 水箱设备ID
#define SEND_BAUD 115200  // 发送波特率（需与接收端一致）

// LoRa通信引脚定义
#define LORA_RX 9  // LoRa接收引脚
#define LORA_TX 10 // LoRa发送引脚

// 软件串口库用于LoRa通信
#include <SoftwareSerial.h>
SoftwareSerial loraSerial(LORA_RX, LORA_TX);  // 创建LoRa软件串口

// OLED初始化 - 适配SSD1306 128x64屏幕，I2C默认地址0x3C
U8X8_SSD1306_128X64_NONAME_HW_I2C u8x8(U8X8_PIN_NONE);

int level_state;  // 水位状态（数字）
String level_str; // 水位状态（文本）
static int dataCount = 0;  // 数据包计数

void setup() {
  // 1. 初始化硬件串口（用于调试）
  Serial.begin(SEND_BAUD);
  
  // 2. 初始化LoRa软件串口
  loraSerial.begin(SEND_BAUD);
  
  // 3. 初始化引脚模式
  pinMode(LIQUID_LEVEL_PIN, INPUT);  // 液位传感器设为输入
  
  // 4. 初始化OLED
  if (!u8x8.begin()) {
    Serial.println("ERROR: OLED初始化失败！");
    while (1);  // 初始化失败则停止
  }
  u8x8.setContrast(200);  // 调整OLED亮度（0-255）
  u8x8.setFont(u8x8_font_chroma48medium8_r);  // 设置显示字体
  u8x8.clearDisplay();  // 清空屏幕

}

void loop() {
  // 1. 读取液位传感器信号
  level_state = digitalRead(LIQUID_LEVEL_PIN);  // 读取电平（LOW/HIGH）
  
  // 2. 更新水位状态文本
  if (level_state == LOW) {
    level_str = "HIGH";  // HIGH=高水位
  } else {
    level_str = "LOW ";  // LOW=低水位（空格用于对齐显示）
  }
  
  // 3. 更新OLED显示
  updateDisplay();
  
  // 4. 检查是否有指令到达（通过LoRa串口接收指令）
  if (loraSerial.available() > 0) {
    // 读取接收到的数据
    byte Startbyte = loraSerial.read();
    Serial.print("接收到字节: 0x");
    Serial.println(Startbyte, HEX);
    if(Startbyte==0XB0){
      byte Nextbyte = loraSerial.read();
      Serial.print("接收到字节: 0x");
      Serial.println(Nextbyte, HEX);
      if(Nextbyte==DEVICE_ID){
        sendSensorData();    // 发送传感器数据
      }
    }
    
    // 清空串口接收缓冲区
    while (loraSerial.available() > 0) {
      loraSerial.read();
    }
  }
  
  delay(10);
}

// 更新OLED显示
void updateDisplay() {
  if (level_state == LOW) {
    level_str = "HIGH";          // HIGH=高水位（需根据传感器实际特性调整）
    u8x8.drawString(5, 4, "NORMOL");  
    
   
  } else {
    level_str = "LOW ";          // LOW=低水位（空格用于对齐显示）
  
    u8x8.drawString(5, 4, " LOW  ");
    
  
  }

}

void sendSensorData() {
  // 数据格式：设备码,水箱状态（逗号分隔，便于接收端解析）
  String sendData = String(DEVICE_ID) + "," 
                  + String(level_state);
  
  // 通过LoRa发送数据（末尾加换行符，接收端可按行读取）
  loraSerial.println(sendData);
  
  // 调试信息输出到硬件串口
  Serial.print("通过LoRa发送数据: ");
  Serial.println(sendData);

}
