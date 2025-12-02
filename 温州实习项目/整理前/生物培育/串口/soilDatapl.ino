// 串口数据处理样例程序 - 接收A0格式控制指令
#include <SoftwareSerial.h>

// 基本定义
#define DEVICE_ID 8  // 设备ID
#define BAUD_RATE 115200  // 串口波特率
#define RX_PIN 9  // 接收引脚
#define TX_PIN 10  // 发送引脚

// 指令存储变量
byte received_command = 100;  // 存储接收到的指令
byte received_data = 0;       // 存储指令数据

// 创建串口对象
SoftwareSerial mySerial(RX_PIN, TX_PIN);

void setup() {
  // 初始化串口通信
  Serial.begin(BAUD_RATE);       // 调试串口
  mySerial.begin(BAUD_RATE);     // 数据通信串口
  
  Serial.println("串口处理样例启动，等待接收指令...");
  Serial.println("支持的指令格式: A0 设备号 动作 数据 FF");
  Serial.print("当前设备ID: ");
  Serial.println(DEVICE_ID);
}

void loop() {
  // 串口数据接收和处理的核心逻辑
  if (mySerial.available()) {
    // 读取第一个字节（帧头）
    byte header = mySerial.read();
    
    // 帧格式验证：检查帧头
    if (header == 0xA0) {
      Serial.println("检测到帧头A0，开始接收指令");
      
      // 读取剩余的4字节数据
      byte buffer[4];
      int bytes_read = mySerial.readBytes(buffer, 4);
      
      // 确保接收到了完整的数据包
      if (bytes_read == 4) {
        byte device_id = buffer[0];
        byte action = buffer[1];
        byte data = buffer[2];
        byte frame_end = buffer[3];
        
        // 打印接收到的完整指令（调试用）
        Serial.print("接收到完整指令: A0 ");
        printHex(device_id); Serial.print(" ");
        printHex(action); Serial.print(" ");
        printHex(data); Serial.print(" ");
        printHex(frame_end);
        Serial.println();
        
        // 指令验证：检查设备ID和帧尾
        if (device_id == DEVICE_ID && frame_end == 0xFF) {
          Serial.println("指令验证通过，设备ID匹配且帧尾正确");
          
          // 存储有效的指令和数据
          received_command = action;
          received_data = data;
          
          Serial.print("指令解析成功 - 动作: ");
          printHex(received_command);
          Serial.print(", 数据: ");
          printHex(received_data);
          Serial.println();
        } else {
          // 指令验证失败
          if (device_id != DEVICE_ID) {
            Serial.print("错误：设备ID不匹配，期望 ");
            printHex(DEVICE_ID);
            Serial.print("，收到 ");
            printHex(device_id);
            Serial.println();
          }
          if (frame_end != 0xFF) {
            Serial.println("错误：帧尾不是FF，指令无效");
          }
        }
      } else {
        Serial.println("错误：未收到完整的数据包");
      }
    } else {
      // 非A0帧头，忽略
      Serial.print("收到非A0帧头: ");
      printHex(header);
      Serial.println("，忽略");
    }
  }
  
  // 处理接收到的有效指令
  if (received_command != 100) {
    processCommand(received_command, received_data);
    // 重置命令状态，等待下一个指令
    received_command = 100;
  }
  
  // 短暂延时，避免过度占用CPU
  delay(10);
}

// 指令处理函数（只保留一个基础处理示例）
void processCommand(byte cmd, byte data) {
  Serial.print("开始处理指令: ");
  printHex(cmd);
  Serial.print(", 数据: ");
  printHex(data);
  Serial.println();
  
  // 简单的指令处理示例
  switch(cmd) {
    case 0x00: // 基础控制指令示例
      if(data == 0x00) {
        Serial.println("执行操作: 关闭设备");
        // 这里添加实际的设备控制代码
      } else if(data == 0x01) {
        Serial.println("执行操作: 开启设备");
        // 这里添加实际的设备控制代码
      }
      break;
      
    default:
      Serial.print("未知指令: ");
      printHex(cmd);
      Serial.println("，忽略");
      break;
  }
}

// 辅助函数：以2位十六进制格式打印字节
void printHex(byte val) {
  if (val < 16) Serial.print("0");
  Serial.print(val, HEX);
}
