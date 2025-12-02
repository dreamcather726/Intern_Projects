// 补光系统控制程序 - 接收A0格式控制指令的Arduino程序
#include <SoftwareSerial.h>

// 设备和引脚定义
#define DEVICE_ID 7  // 设备ID：补光系统
#define BAUD_RATE 115200  // 串口波特率
#define lora_rx 9  // 定义LORA接收引脚
#define lora_tx 10  // 定义LORA发送引脚

// 定义4个继电器引脚
#define relay1_PIN 5  // 继电器1引脚
#define relay2_PIN 6  // 继电器2引脚
#define relay3_PIN 7  // 继电器3引脚
#define relay4_PIN 8  // 继电器4引脚

byte command = 100;  // 存储接收到的指令
byte command_data = 0;  // 存储指令数据
SoftwareSerial loraSerial(lora_rx, lora_tx);  // 创建LORA串口对象
void setup() {
  // 初始化串口通信
  Serial.begin(BAUD_RATE);
  loraSerial.begin(BAUD_RATE);  // 初始化LORA串口
  // 初始化继电器引脚为输出模式
  pinMode(relay1_PIN, OUTPUT);
  pinMode(relay2_PIN, OUTPUT);
  pinMode(relay3_PIN, OUTPUT);
  pinMode(relay4_PIN, OUTPUT);
  
  // 初始化继电器为低电平（关闭状态）
  digitalWrite(relay1_PIN, LOW);
  digitalWrite(relay2_PIN, LOW);
  digitalWrite(relay3_PIN, LOW);
  digitalWrite(relay4_PIN, LOW);

  Serial.println("补光系统启动，等待接收指令...");
  Serial.println("支持的指令格式: A0 设备号 对应动作 数据 FF");
  Serial.print("当前设备ID: ");
  Serial.println(DEVICE_ID);
}

void loop() {
  // 接收并解析指令
  if (loraSerial.available()) {
    // 读取第一个字节（帧头）
    byte header = loraSerial.read();
    
    // 检查是否为A0帧头
    if (header == 0xA0) {
      Serial.println("检测到帧头A0，开始接收指令");
      byte buffer[4];
      int remainingBytes = loraSerial.readBytes(buffer, 4); // 读取剩余的4字节数据包
      // 读取剩余的4个字节
      byte device_id = buffer[0];
      byte action = buffer[1];
      byte data = buffer[2];
      byte frame_end = buffer[3];
      
      // 打印接收到的完整指令
      Serial.print("接收到完整指令: A0 ");
      printHex(device_id); Serial.print(" ");
      printHex(action); Serial.print(" ");
      printHex(data); Serial.print(" ");
      printHex(frame_end);
      Serial.println();
      // 验证设备ID和帧尾
      if (device_id == DEVICE_ID) {
        Serial.println("设备ID匹配");
        
        if (frame_end == 0xFF) {
          Serial.println("帧尾FF验证通过，指令有效");
          
          // 设置命令和数据
          command = action;
          command_data = data;
          
          Serial.print("指令解析成功 - 动作: ");
          printHex(command);
          Serial.print(", 数据: ");
          printHex(command_data);
          Serial.println();
        } else {
          Serial.println("错误：帧尾不是FF，指令无效");
        }
      }else if (device_id == 0x57) {
        if (frame_end == 0xFF) {
          if (data == 0x01) {
            digitalWrite(relay1_PIN, HIGH);
            digitalWrite(relay2_PIN, HIGH);
            digitalWrite(relay3_PIN, HIGH);
            digitalWrite(relay4_PIN, HIGH);
            Serial.println("执行指令: 打开全部灯光");
          } else {
             digitalWrite(relay1_PIN, LOW);
            digitalWrite(relay2_PIN, LOW);
            digitalWrite(relay3_PIN, LOW);
            digitalWrite(relay4_PIN, LOW);
            Serial.println("执行指令: 关闭全部灯光");
          }
        } else {
          Serial.println("错误：帧尾不是FF，指令无效");
        }
      }else if (device_id == 0x66) {
        if (frame_end == 0xFF) {
          if (data == 0x01) {
            digitalWrite(relay1_PIN, HIGH);
            digitalWrite(relay2_PIN, HIGH);
            digitalWrite(relay3_PIN, HIGH);
            digitalWrite(relay4_PIN, HIGH);
            Serial.println("执行指令: 打开全部设备(补光LED)");
          } else {
             digitalWrite(relay1_PIN, LOW);
            digitalWrite(relay2_PIN, LOW);
            digitalWrite(relay3_PIN, LOW);
            digitalWrite(relay4_PIN, LOW);
            Serial.println("执行指令: 关闭全部设备(补光LED)");
          }
        } else {
          Serial.println("错误：帧尾不是FF，指令无效");
        }
      }else {
        Serial.print("错误：设备ID不匹配，期望 ");
        printHex(DEVICE_ID);
        Serial.print("，收到 ");
        printHex(device_id);
        Serial.println();
      }
    } else {
      // 不是A0帧头，记录并继续等待
      Serial.print("收到非A0帧头: ");
      printHex(header);
      Serial.println("，忽略");
    }
  }
  
  // 执行接收到的指令
  if (command !=100) {
    executeCommand(command, command_data);
    // 重置命令，等待下一个指令
    command = 100;
  }
  
  // 短暂延时，避免过度占用CPU
  delay(10);
}

void executeCommand(byte cmd, byte data) {
  Serial.print("开始执行指令: ");
  printHex(cmd);
  Serial.print(" 动作: ");
  printHex(data);
  Serial.println();
  
  // 根据不同的指令执行相应的操作
  switch(cmd) {
    case 0x00://全部控制指令（控制所有4个继电器同时动作）
      if(data == 0){//关闭所有继电器
        digitalWrite(relay1_PIN, LOW);
        digitalWrite(relay2_PIN, LOW);
        digitalWrite(relay3_PIN, LOW);
        digitalWrite(relay4_PIN, LOW);
        Serial.println("执行指令: 关闭所有补光LED");
      }else{//打开所有继电器        
        digitalWrite(relay1_PIN, HIGH);
        digitalWrite(relay2_PIN, HIGH);
        digitalWrite(relay3_PIN, HIGH);
        digitalWrite(relay4_PIN, HIGH);
        Serial.println("执行指令: 开启所有补光LED");
      }      
      break;
    case 0x01: // 控制单个继电器（兼容指令）
      if(data == 0){//关闭所有继电器
        digitalWrite(relay1_PIN, LOW);
        digitalWrite(relay2_PIN, LOW);
        digitalWrite(relay3_PIN, LOW);
        digitalWrite(relay4_PIN, LOW);
        Serial.println("执行指令: 关闭所有补光LED");
      }else{//开启所有继电器
        digitalWrite(relay1_PIN, HIGH);
        digitalWrite(relay2_PIN, HIGH);
        digitalWrite(relay3_PIN, HIGH);
        digitalWrite(relay4_PIN, HIGH);
        Serial.println("执行指令: 开启所有补光LED");
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