// 室内农场3.0 - 指令发送程序
// 用于发送自动指令到控制系统

#include <SoftwareSerial.h>

// 定义串口通信参数
#define SERIAL_BAUD 9600

// 定义软件串口引脚
#define SOFT_RX_PIN 7  // 接收引脚
#define SOFT_TX_PIN 8  // 发送引脚

// 创建软件串口对象
SoftwareSerial softSerial(SOFT_RX_PIN, SOFT_TX_PIN);

 

 

// 定义用户提供的新指令数组
byte cmd_warm[] = {0x55, 0xAA, 0x01, 0x0F, 0x00, 0xFF};        // 调暖一些
byte cmd_cool[] = {0x55, 0xAA, 0x01, 0x11, 0x00, 0xFF};        // 调冷一些
byte cmd_brighten[] = {0x55, 0xAA, 0x01, 0x12, 0x00, 0xFF};    // 亮度调亮
byte cmd_darken[] = {0x55, 0xAA, 0x01, 0x13, 0x00, 0xFF};      // 亮度调暗
byte cmd_breathing_light_on[] = {0x55, 0xAA, 0x01, 0x14, 0x00, 0xFF};  // 打开呼吸灯
byte cmd_running_light_on[] = {0x55, 0xAA, 0x01, 0x15, 0x00, 0xFF};    // 打开流水灯
byte cmd_set_red[] = {0x55, 0xAA, 0x01, 0x16, 0x00, 0xFF};     // 设置为红色
byte cmd_set_orange[] = {0x55, 0xAA, 0x01, 0x17, 0x00, 0xFF};  // 设置为橙色
byte cmd_set_yellow[] = {0x55, 0xAA, 0x01, 0x18, 0x00, 0xFF};  // 设置为黄色
byte cmd_set_green[] = {0x55, 0xAA, 0x01, 0x19, 0x00, 0xFF};   // 设置为绿色
byte cmd_set_cyan[] = {0x55, 0xAA, 0x01, 0x1A, 0x00, 0xFF};    // 设置为青色
byte cmd_set_blue[] = {0x55, 0xAA, 0x01, 0x1B, 0x00, 0xFF};    // 设置为蓝色
byte cmd_set_purple[] = {0x55, 0xAA, 0x01, 0x1C, 0x00, 0xFF};  // 设置为紫色
 

void setup() {
  // 初始化硬件串口（用于调试和用户输入）
  Serial.begin(SERIAL_BAUD);
  while (!Serial) {
    ; // 等待串口连接
  }
  
  // 初始化软件串口（用于发送指令）
  softSerial.begin(SERIAL_BAUD);
  
  Serial.println("室内农场3.0 - 指令发送程序（软件串口版）");
  Serial.println("可用指令：");
  Serial.println("1 - 调暖一些");
  Serial.println("2 - 调冷一些");
  Serial.println("3 - 亮度调亮");
  Serial.println("4 - 亮度调暗");
  Serial.println("5 - 打开呼吸灯");
  Serial.println("6 - 打开流水灯");
  Serial.println("7 - 设置为红色");
  Serial.println("8 - 设置为橙色");
  Serial.println("9 - 设置为黄色");
  Serial.println("10 - 设置为绿色");
  Serial.println("11 - 设置为青色");
  Serial.println("12 - 设置为蓝色");
  Serial.println("13 - 设置为紫色");
  Serial.println("请输入指令编号发送对应指令...");
}

void loop() {
  // 检查是否有串口数据可读
  if (Serial.available() > 0) {
    // 读取用户输入（支持1-2位数字）
    String input = Serial.readStringUntil('\n');
    input.trim();
    int command = input.toInt();
    
    switch (command) {
      // 用户提供的新指令
      case 1:
        sendCommand(cmd_warm, sizeof(cmd_warm), "调暖一些 (0x55 AA 01 0F 00 FF)");
        break;
      case 2:
        sendCommand(cmd_cool, sizeof(cmd_cool), "调冷一些 (0x55 AA 01 11 00 FF)");
        break;
      case 3:
        sendCommand(cmd_brighten, sizeof(cmd_brighten), "亮度调亮 (0x55 AA 01 12 00 FF)");
        break;
      case 4:
        sendCommand(cmd_darken, sizeof(cmd_darken), "亮度调暗 (0x55 AA 01 13 00 FF)");
        break;
      case 5:
        sendCommand(cmd_breathing_light_on, sizeof(cmd_breathing_light_on), "打开呼吸灯 (0x55 AA 01 14 00 FF)");
        break;
      case 6:
        sendCommand(cmd_running_light_on, sizeof(cmd_running_light_on), "打开流水灯 (0x55 AA 01 15 00 FF)");
        break;
      case 7:
        sendCommand(cmd_set_red, sizeof(cmd_set_red), "设置为红色 (0x55 AA 01 16 00 FF)");
        break;
      case 8:
        sendCommand(cmd_set_orange, sizeof(cmd_set_orange), "设置为橙色 (0x55 AA 01 17 00 FF)");
        break;
      case 9:
        sendCommand(cmd_set_yellow, sizeof(cmd_set_yellow), "设置为黄色 (0x55 AA 01 18 00 FF)");
        break;
      case 10:
        sendCommand(cmd_set_green, sizeof(cmd_set_green), "设置为绿色 (0x55 AA 01 19 00 FF)");
        break;
      case 11:
        sendCommand(cmd_set_cyan, sizeof(cmd_set_cyan), "设置为青色 (0x55 AA 01 1A 00 FF)");
        break;
      case 12:
        sendCommand(cmd_set_blue, sizeof(cmd_set_blue), "设置为蓝色 (0x55 AA 01 1B 00 FF)");
        break;
      case 13:
        sendCommand(cmd_set_purple, sizeof(cmd_set_purple), "设置为紫色 (0x55 AA 01 1C 00 FF)");
        break;
      
      default:
        Serial.println("无效指令，请输入1-13之间的指令编号...");
        break;
    }
  }
}

// 发送指令的函数
void sendCommand(byte command[], int length, String commandName) {
  Serial.print("发送指令: ");
  Serial.println(commandName);
  
  // 显示发送的字节
  Serial.print("指令字节: ");
  for (int i = 0; i < length; i++) {
    Serial.print("0x");
    if (command[i] < 0x10) Serial.print("0"); // 确保两位数显示
    Serial.print(command[i], HEX);
    Serial.print(" ");
    
    // 通过软件串口发送指令
    softSerial.write(command[i]);
  }
  Serial.println();
  Serial.println("指令通过软件串口发送完成");
}