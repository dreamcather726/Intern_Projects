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

// 定义测试指令数组（16个）
byte command1[] = {0x55, 0x01, 0x03, 0x01, 0xFF};    // 55 01 03 01 FF

byte command2[] = {0xA0, 0x0A, 0x02, 0x00, 0xFF};    // 关闭一号补光灯
byte command3[] = {0xA0, 0x0B, 0x01, 0x00, 0xFF};    // 打开二号补光灯
byte command4[] = {0xA0, 0x0B, 0x02, 0x00, 0xFF};    // 关闭二号补光灯
byte command5[] = {0xA0, 0x0C, 0x05, 0x00, 0xFF};    // 打开三号补光灯
byte command6[] = {0xA0, 0x0C, 0x06, 0x00, 0xFF};    // 关闭三号补光灯
byte command7[] = {0xA0, 0x0D, 0x01, 0x00, 0xFF};    // 打开全部灯光
byte command8[] = {0xA0, 0x0C, 0x02, 0x00, 0xFF};    // 关闭全部灯光

byte command9[] = {0xA0, 0x0E, 0x01, 0x00, 0xFF};    // 打开一号通风系统
byte command10[] = {0xA0, 0x0E, 0x02, 0x00, 0xFF};   // 关闭一号通风系统
byte command11[] = {0xA0, 0x0E, 0x03, 0x00, 0xFF};   // 打开二号通风系统
byte command12[] = {0xA0, 0x0E, 0x04, 0x00, 0xFF};   // 关闭二号通风系统
byte command13[] = {0xA0, 0x0E, 0x05, 0x00, 0xFF};   // 打开三号通风系统
byte command14[] = {0xA0, 0x0E, 0x06, 0x00, 0xFF};   // 关闭三号通风系统
byte command15[] = {0xA0, 0x09, 0x01, 0x00, 0xFF};   // 打开全部通风设备
byte command16[] = {0xA0, 0x09, 0x02, 0x00, 0xFF};   // 关闭全部通风设备


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
  Serial.println("01-10: 测试指令1-10（16进制输入）");
  Serial.println("0B-10: 测试指令11-16（16进制输入）");
  
  Serial.println("请输入16进制指令编号(01-10)发送对应指令...");
}

// 将字符转换为16进制数字
byte hexCharToByte(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'A' && c <= 'F') return 10 + c - 'A';
  if (c >= 'a' && c <= 'f') return 10 + c - 'a';
  return 0xFF; // 无效字符
}

// 将两个十六进制字符转换为一个字节
byte hexToByte(char high, char low) {
  byte highNibble = hexCharToByte(high);
  byte lowNibble = hexCharToByte(low);
  if (highNibble == 0xFF || lowNibble == 0xFF) return 0xFF; // 无效输入
  return (highNibble << 4) | lowNibble;
}

void loop() {
  // 检查是否有串口数据可读（至少需要两个字符表示16进制数）
  if (Serial.available() >= 2) {
    // 读取两个字符作为16进制数
    char high = Serial.read();
    char low = Serial.read();
    
    // 转换为字节值
    byte cmdNum = hexToByte(high, low);
    
    // 处理1-16的指令
    switch (cmdNum) {
      case 0x01:
        sendCommand(command1, sizeof(command1), "测试指令1");
        break;
      case 0x02:
        sendCommand(command2, sizeof(command2), "测试指令2");
        break;
      case 0x03:
        sendCommand(command3, sizeof(command3), "测试指令3");
        break;
      case 0x04:
        sendCommand(command4, sizeof(command4), "测试指令4");
        break;
      case 0x05:
        sendCommand(command5, sizeof(command5), "测试指令5");
        break;
      case 0x06:
        sendCommand(command6, sizeof(command6), "测试指令6");
        break;
      case 0x07:
        sendCommand(command7, sizeof(command7), "测试指令7");
        break;
      case 0x08:
        sendCommand(command8, sizeof(command8), "测试指令8");
        break;
      case 0x09:
        sendCommand(command9, sizeof(command9), "测试指令9");
        break;
      case 0x0A:
        sendCommand(command10, sizeof(command10), "测试指令10");
        break;
      case 0x0B:
        sendCommand(command11, sizeof(command11), "测试指令11");
        break;
      case 0x0C:
        sendCommand(command12, sizeof(command12), "测试指令12");
        break;
      case 0x0D:
        sendCommand(command13, sizeof(command13), "测试指令13");
        break;
      case 0x0E:
        sendCommand(command14, sizeof(command14), "测试指令14");
        break;
      case 0x0F:
        sendCommand(command15, sizeof(command15), "测试指令15");
        break;
      case 0x10:
        sendCommand(command16, sizeof(command16), "测试指令16");
        break;
      default:
        Serial.print("无效的16进制指令: 0x");
        Serial.print(high);
        Serial.println(low);
        Serial.println("请输入01-10之间的16进制数");
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
    
  }
  softSerial.write(command, length);
  Serial.write(command, length);
  Serial.println();
  Serial.println("指令通过软件串口发送完成");
}