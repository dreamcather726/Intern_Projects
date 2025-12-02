/*
 * 智能家居系统 - 客厅节点 (Arduino ID: 0x04)
 * 
 * 接线说明:
 * 
 * LoRa模块:
 *   LoRa TX  -> Arduino D11
 *   LoRa RX  -> Arduino D12
 *   LoRa VCC -> 3.3V
 *   LoRa GND -> GND
 * 
 * 窗户舵机1:
 *   SIGNAL   -> Arduino D2
 *   VCC      -> 5V
 *   GND      -> GND
 * 
 * 窗户舵机2:
 *   SIGNAL   -> Arduino D3
 *   VCC      -> 5V
 *   GND      -> GND
 * 
 * 客厅温湿度传感器 (DHT11):
 *   DATA     -> Arduino D5
 *   VCC      -> 5V
 *   GND      -> GND
 * 
 * 卫生间温湿度传感器 (DHT11):
 *   DATA     -> Arduino D6
 *   VCC      -> 5V
 *   GND      -> GND
 * 
 * OLED显示屏 (SH1106 128x64):
 *   SCL      -> Arduino A5
 *   SDA      -> Arduino A4
 *   VCC      -> 5V
 *   GND      -> GND
 * 
 * 电源说明:
 *   Arduino供电: 7-12V DC
 *   舵机供电: 5V (大功率舵机建议使用外部电源)
 *   传感器: 5V
 * 
 * 功能:
 *   - 客厅窗户控制 (双舵机)
 *   - 客厅温湿度监测
 *   - 卫生间温湿度监测
 *   - OLED实时数据显示
 *   - 响应上位机数据请求
 */

#include <SoftwareSerial.h>
#include <Servo.h>
#include <U8x8lib.h>  // OLED显示库
#include <DHT.h>
#include <Wire.h>     // I2C通信库（OLED依赖）
#include <ArduinoJson.h>  // JSON解析库
#define LORA_RX_PIN  7
#define LORA_TX_PIN  8
#define LORA_BAUD_RATE 115200
SoftwareSerial loraSerial(LORA_RX_PIN, LORA_TX_PIN);

#define NODE_ID 0x04  // 客厅节点

// 窗户舵机引脚
const int PIN_SERVO_1 = 2;
const int PIN_SERVO_2 = 3;

// 温湿度传感器引脚
const int PIN_DHT_LIVING_ROOM = 5;    // 客厅温湿度
const int PIN_DHT_BATHROOM = 6;       // 卫生间温湿度

// OLED显示屏配置 - 如果默认地址不工作，可以尝试其他地址
// 常见地址：0x3C, 0x3D, 0x3E, 0x3F
U8X8_SSD1306_128X64_NONAME_HW_I2C u8g2(U8X8_PIN_NONE);
 

// 创建对象
Servo servo1;
Servo servo2;
DHT dht_living_room(PIN_DHT_LIVING_ROOM, DHT11);
DHT dht_bathroom(PIN_DHT_BATHROOM, DHT11);

// 窗户状态
const int WINDOW_OPEN_ANGLE_1 = 180;
const int WINDOW_CLOSE_ANGLE_1 = 0;
const int WINDOW_OPEN_ANGLE_2 = 0;
const int WINDOW_CLOSE_ANGLE_2 = 180;
bool is_window_open = false;

// 温湿度数据
float living_room_temp = 0.0;
float living_room_humidity = 0.0;
float bathroom_temp = 0.0;
float bathroom_humidity = 0.0;

// MP3和烟雾数据
String current_mp3_name = "000";
float current_smoke_value = 0.0;

// 定时器
unsigned long last_sensor_read_time = 0;
const long SENSOR_READ_INTERVAL = 5000;

// 临时变量用于存储接收的JSON字符串
String json_buffer = "";
const unsigned long JSON_TIMEOUT = 1000;  // JSON数据接收超时时间
unsigned long json_start_time = 0;        // JSON数据开始接收时间

void setup() {
  Serial.begin(115200);
  loraSerial.begin(LORA_BAUD_RATE);
  
  Serial.println(F("Living Room Node Booting... (ID: 0x04)"));

  // 初始化舵机
  servo1.attach(PIN_SERVO_1);
  servo2.attach(PIN_SERVO_2);
  controlWindow(false); // 初始关闭窗户

  // 初始化温湿度传感器
  dht_living_room.begin();
  dht_bathroom.begin();
  
  // 初始化OLED显示屏
  u8g2.begin();
  
 
  u8g2.setContrast(200);  // 调整OLED亮度（0-255）
  u8g2.setFont(u8x8_font_artossans8_u);
  u8g2.clearDisplay();  // 清空屏幕
 
 
}

void loop() {
  loraSerial.listen(); 
  // 处理LoRa指令
  if (loraSerial.available()) {
    byte startByte = loraSerial.read();
    
    // 检查是否为JSON数据开始
    if (startByte == '{') {
      // 开始接收JSON数据
       
      json_buffer = "{";
      json_start_time = millis();  // 记录开始时间
      
      // 继续接收JSON数据直到找到结束符或超时
      while (loraSerial.available() && (millis() - json_start_time < JSON_TIMEOUT)) {
        char c = loraSerial.read();
        json_buffer += c;
        
        if (c == '}') {
          // 完整JSON数据已接收
          break;
        }
      }
      
      // 尝试解析JSON数据
      DynamicJsonDocument doc(64);
      DeserializationError error = deserializeJson(doc, json_buffer);
      
      if (!error) {
        // 提取MP3名称
        
        if (doc.containsKey("MP3_Name")) {
          current_mp3_name = String(mp3_name);
        } else {
          current_mp3_name = "000";
        }
        
        // 提取烟雾浓度
        if (doc.containsKey("smoke")) {
          current_smoke_value = doc["smoke"];
        } else {
          current_smoke_value = 0.0;
        }
        
        // 打印调试信息
        Serial.print("Received MP3: ");
        Serial.println(current_mp3_name);
        Serial.print("Received Smoke: ");
        Serial.println(current_smoke_value, 1);
        
        // 更新OLED显示
        updateDisplay();
      } else {
        // JSON解析失败
        Serial.print("JSON parse error: ");
        Serial.println(error.c_str());
        Serial.print("Received data: ");
        Serial.println(json_buffer);
      }
      
      // 清空JSON缓冲区
      json_buffer = "";
    } 
    // 检查是否为传统指令
    else if (startByte == 0x55) {
      // 处理命令指令
      byte buffer[5];
      int bytesRead = loraSerial.readBytes(buffer, 5);
      if (bytesRead == 5 && buffer[0] == 0xAA && buffer[4] == 0xFF) {
        byte device_type = buffer[1];
        byte action = buffer[2];
        
        // 处理窗户指令(04)和所有设备指令(05)
        if (device_type == 0x04 || device_type == 0x05) {
          processLivingRoomCommand(device_type, action);
        }
      }
    } else if (startByte == 0xFE) {
      // 处理JSON数据请求
      byte nextbyte = loraSerial.read();
      if (nextbyte == NODE_ID) {
        byte lastbyte = loraSerial.read();
        if (lastbyte == 0xFF) {
          SendTemperatureData();
        }
      }
    }
    while (loraSerial.available()) {
      byte discard = loraSerial.read();
    }
  }
  
 
 
  
  // 定期读取传感器
  if (millis() - last_sensor_read_time >= SENSOR_READ_INTERVAL) {
    readSensors();
    updateDisplay();
    last_sensor_read_time = millis();
    
  }
  
  delay(10);
}

void processLivingRoomCommand(byte device_type, byte action) {
  Serial.print("Living Room Command - Action: 0x");
  Serial.println(action, HEX);
  
  switch (action) {
    case 0x01: controlWindow(true); break;   // 打开窗户
    case 0x02: controlWindow(false); break;  // 关闭窗户
  }
}

// 窗户控制函数
void controlWindow(bool open) {
  if (open) {
    if (!is_window_open) {
      servo1.write(WINDOW_OPEN_ANGLE_1);
      servo2.write(WINDOW_OPEN_ANGLE_2);
      is_window_open = true;
      Serial.println("Window OPENED");
    }
  } else {
    if (is_window_open) {
      servo1.write(WINDOW_CLOSE_ANGLE_1);
      servo2.write(WINDOW_CLOSE_ANGLE_2);
      is_window_open = false;
      Serial.println("Window CLOSED");
    }
  }
  
}

// 传感器读取函数
void readSensors() {
  // 读取客厅温湿度
  living_room_humidity = dht_living_room.readHumidity();
  living_room_temp = dht_living_room.readTemperature();
  
  if (isnan(living_room_humidity) || isnan(living_room_temp)) {
    living_room_humidity = 0;
    living_room_temp = 0;
    Serial.println("Failed to read living room DHT sensor!");
  }  

  // 读取卫生间温湿度
  bathroom_humidity = dht_bathroom.readHumidity();
  bathroom_temp = dht_bathroom.readTemperature();
  
  if (isnan(bathroom_humidity) || isnan(bathroom_temp)) {
    bathroom_humidity = 0;
    bathroom_temp = 0;
    Serial.println("Failed to read bathroom DHT sensor!");
  }  

   
}

// OLED显示更新
void updateDisplay() {
        // 使用sprintf格式化环境数据并显示在OLED上
    char buffer[20];
    
    // 显示温度
    sprintf(buffer, "L_T:%d C", (int)living_room_temp);
    u8g2.drawString(0, 0, buffer);
   
    // 显示湿度
    sprintf(buffer, "L_H:%d %", (int)living_room_humidity);
    u8g2.drawString(9, 0, buffer);
   
    // 显示光照强度
    sprintf(buffer, "B_T:%d C", (int)bathroom_temp);
    u8g2.drawString(0, 2, buffer);
   
    // 显示土壤湿度
    sprintf(buffer, "B_H:%d %", (int)bathroom_humidity);
    u8g2.drawString(9, 2, buffer);

    // 显示土壤湿度
    sprintf(buffer, "M:%s   ", current_mp3_name.c_str());
    u8g2.drawString(0, 4, buffer);
   
    // 显示烟雾浓度
    sprintf(buffer, "S:%d   ", (int)current_smoke_value);
    u8g2.drawString(0, 6, buffer);
 
 
}

// JSON请求处理函数 - 修改版
void SendTemperatureData() {
  // 将温湿度数据转换为字符串
  String livingTemp = String(living_room_temp, 1);
  String livingHum = String(living_room_humidity, 1);
  String bathroomTemp = String(bathroom_temp, 1);
  String bathroomHum = String(bathroom_humidity, 1);
  
  // 构建JSON字符串
  String jsonData = "{\"l_tmp\":" + livingTemp + ",\"l_hum\":" + livingHum + ",\"b_tmp\":" + bathroomTemp + ",\"b_hum\":" + bathroomHum + "}";
  
  // 将JSON数据发送到上位机
  loraSerial.print(jsonData);
  
  // 打印到调试串口
  Serial.println("JSON Data Sent: " + jsonData);
}

 


