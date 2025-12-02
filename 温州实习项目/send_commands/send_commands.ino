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

// 定义指令数组
byte autoSprayCommand[] = {0x55, 0x01, 0x03, 0x01, 0xFF};    // 自动喷淋
byte autoLightCommand[] = {0x55, 0x02, 0x03, 0x01, 0xFF};     // 自动补光
byte openAllLightsCommand[] = {0x55, 0x02, 0x02, 0x01, 0xFF}; // 
byte closeAllLightsCommand[] = {0x55, 0x02, 0x02, 0x00, 0xFF}; // 
byte closeAllLightsCommand1[] = {0x55, 0x02, 0xFF, 0x01, 0xFF}; //

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
 
  Serial.println("请输入指令编号发送对应指令...");
}

void loop() {
  // 检查是否有串口数据可读
  if (Serial.available() > 0) {
    char command = Serial.read();
    
    switch (command) {
      case '1':
        sendCommand(autoSprayCommand, sizeof(autoSprayCommand), "自动喷淋");
        break;
      case '2':
        sendCommand(autoLightCommand, sizeof(autoLightCommand), "自动补光");
        break;
      case '3':
        sendCommand(openAllLightsCommand, sizeof(openAllLightsCommand), "打开全部灯光");
        break;
      case '4':
        sendCommand(closeAllLightsCommand, sizeof(closeAllLightsCommand), "关闭全部灯光");
        break;
      case '5':
        sendCommand(closeAllLightsCommand1, sizeof(closeAllLightsCommand1), "关闭全部灯光");
        break;
      default:
        Serial.println("无效指令，请输入1-5之间的数字");
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