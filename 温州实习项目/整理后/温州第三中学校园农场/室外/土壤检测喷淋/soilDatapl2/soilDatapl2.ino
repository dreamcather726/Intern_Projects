/*
 * 土壤数据采集与控制程序
 * 功能：读取Modbus土壤传感器数据并接收/执行控制指令
 * 版本：1.0
 * 作者：室内农场项目组
 */

#include <SoftwareSerial.h>
#include <ModbusMaster.h>

// ========== 引脚定义区域 ==========
#define MODBUS_RX     12    // 软件串口接收引脚
#define MODBUS_TX     11    // 软件串口发送引脚
#define RELAY_PIN     5     // 继电器控制引脚（设备四）

// ========== 设备配置区域 ==========
#define DEVICE_ID     2   // 设备ID（室外设备为1，2）

// ========== 通信配置区域 ==========
#define SEND_BAUD     115200  // 硬件串口波特率（与上位机通信）
const uint8_t MB_SLAVE_ADDR = 1;   // 土壤传感器Modbus从站地址
const long MB_BAUD_RATE = 4800;    // Modbus通信波特率
const uint16_t READ_INTERVAL = 1500; // 读取间隔（1.5秒）
const unsigned long RELAY_ON_TIME = 25000; // 继电器开启时间（5秒）

// ========== 对象定义区域 ==========
SoftwareSerial modbusSerial(MODBUS_RX, MODBUS_TX); // Modbus软件串口实例
ModbusMaster mbNode;                               // Modbus主站实例

// ========== 数据变量区域 ==========
// 传感器数据
float soilMoisture = 0.0;  // 土壤水分（%）
float soilTemp = 0.0;      // 土壤温度（℃）
float soilEC = 0.0;        // 土壤电导率（μS/cm）
float soilPH = 0.0;        // 土壤PH值

// 指令相关变量
byte header = 0;           // 帧头
byte command = 100;        // 命令（100表示无命令）
byte command_data = 0;     // 命令数据

// ========== 初始化函数 ==========
void setup() {
  // 初始化硬件串口（用于与上位机通信）
  Serial.begin(SEND_BAUD);
  
  // 初始化Modbus通信
  modbusSerial.begin(MB_BAUD_RATE);
  mbNode.begin(MB_SLAVE_ADDR, modbusSerial);

  // 初始化继电器引脚
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);  // 初始状态为关闭
  
  // 初始化完成提示（可根据需要启用）
  // Serial.println("设备初始化完成，准备就绪");
}

// ========== 主循环函数 ==========
void loop() {
  readSoilSensor();    // 读取Modbus传感器数据
  
  // 处理串口接收数据
  if (Serial.available() > 0) {
    // 读取并打印接收到的字节（调试用）
    
    
    processSerialData();
  }
  
  // 短暂延时，降低CPU占用
  delay(10);
}

// ========== 功能函数区域 ==========

/**
 * 处理串口接收的数据
 * 解析不同类型的指令帧并执行相应操作
 */
void processSerialData() {
  // 读取帧头
  byte receivedByte = Serial.read();
  // Serial.print("接收到字节: 0x");
  // Serial.println(receivedByte, HEX);
  
  // 根据帧头类型处理不同指令
  if (receivedByte == 0XDD) {
    // Serial.println("BB帧头：控制指令");
    // B0帧头：发送数据请求
    handleDataRequest();
  } 
  else if (receivedByte == 0x55) {
    // A0帧头：控制指令
    // Serial.println("A0帧头：控制指令");
    handleControlCommand();
  }
  
  // 清理串口缓冲区，确保下次通信干净
  clearSerialBuffer();
}

/**
 * 处理数据请求帧（B0帧）
 * 验证设备ID并发送传感器数据
 */
void handleDataRequest() {
  if (Serial.available() > 0) {
    byte requestedDeviceId = Serial.read();
    // 只响应当前设备的请求
    if (requestedDeviceId == DEVICE_ID) {
      sendSensorData();
    }
  }
}

/**
 * 处理控制指令帧（A0帧）
 * 解析指令数据并执行相应控制操作
 */
void handleControlCommand() {
  
  if (Serial.available() >= 5) {
    byte buffer[5]; 
    int bytesRead = Serial.readBytes(buffer, 5);
    
    // 解析数据包各部分
    byte command = buffer[3];
    Serial.print("接收到指令: 0x");
    Serial.println(command, HEX);
    executeCommand(command);
    
    
  }
}

/**
 * 激活继电器操作
 * 打开继电器，保持指定时间后关闭，并定期清理串口缓冲区
 */
void activateRelay() {
  // 打开继电器
  digitalWrite(RELAY_PIN, HIGH);
  
  // 记录开始时间，实现延时控制
  unsigned long startTime = millis();
  while (millis() - startTime < RELAY_ON_TIME) {
    // 等待期间定期检查并清空串口缓冲区，避免数据堆积
    if (Serial.available() > 0) {
      clearSerialBuffer();
    }
    // 短暂延时，避免CPU占用过高 
    delay(100);
  }
  
  // 关闭继电器
  digitalWrite(RELAY_PIN, LOW);
  
  // 操作完成后再次清理缓冲区
  clearSerialBuffer();
}

/**
 * 读取土壤传感器数据
 * 通过Modbus协议从传感器获取数据并解析
 */
void readSoilSensor() {
  uint16_t modbusData[4] = {0};
  
  // 读取Modbus寄存器（寄存器0~3）
  uint8_t result = mbNode.readHoldingRegisters(0, 4);
  
  if (result == mbNode.ku8MBSuccess) {
    // 成功读取，解析数据并转换为物理值
    soilMoisture = mbNode.getResponseBuffer(0) / 10.0;  // 水分（%）
    
    // 温度处理（考虑负数情况，使用补码转换）
    int16_t tempRaw = mbNode.getResponseBuffer(1);
    soilTemp = (tempRaw >= 32768) ? (tempRaw - 65536) / 10.0 : tempRaw / 10.0;
    
    soilEC = mbNode.getResponseBuffer(2);             // 电导率（μS/cm）
    soilPH = mbNode.getResponseBuffer(3) / 10.0;      // PH值
  } else {
    // 读取失败，填充无效值作为错误标记
    soilMoisture = -1.0;
    soilTemp = -1.0;
    soilEC = -1;
    soilPH = -1.0;
  }
  delay(100);
}

/**
 * 发送传感器数据给上位机
 * 按照指定格式打包并发送数据
 */
void sendSensorData() {
  // 数据格式：设备码,温度,水分,电导率,PH（逗号分隔）
  String sendData = String(DEVICE_ID) + "," +
                    String(soilTemp, 1) + "," +
                    String(soilMoisture, 1) + "," +
                    String(soilEC, 0) + "," +
                    String(soilPH, 1)+","+
                    String(0);
  
  // 发送数据（末尾加换行符，便于接收端按行读取）
  Serial.println(sendData);
  
  // 确保数据完全发送并清理缓冲区
  clearSerialBuffer();
}

/**
 * 清理串口缓冲区
 * 等待发送完成，短暂延时后清空接收缓冲区
 */
void clearSerialBuffer() {
  // 等待发送缓冲区数据发送完成
  Serial.flush();
  
  // 短暂延时确保所有响应数据都已到达
  delay(50);
  
  // 清空接收缓冲区中可能存在的残留数据
  while (Serial.available() > 0) {
    Serial.read(); // 读取并丢弃所有可用字节
  }
}

/**
 * 执行命令函数
 * 根据命令代码执行相应操作
 * 注：当前被注释掉，通过handleControlCommand直接处理
 */
void executeCommand(byte cmd) {
  // 根据不同的指令执行相应的操作
  switch (cmd) {
    Serial.println("接收到指令: cmd");
    Serial.println(cmd);
    case 1: // 全部控制指令
        Serial.println("打开全部控制指令");
        activateRelay();
        // 操作完成后再次清理缓冲区
        clearSerialBuffer();
      break;
    case 2: // 关闭全部喷淋系统
        // 关闭继电器
        Serial.println("关闭全部喷淋系统");
        digitalWrite(RELAY_PIN, LOW);
        // 操作完成后再次清理缓冲区
        clearSerialBuffer();
      break;
    case 5: // 打开一号喷淋系统
        // 打开继电器
        if(DEVICE_ID == 1){
          activateRelay();
          
        }
        // 操作完成后再次清理缓冲区
        clearSerialBuffer();
      break;
    case 6: // 关闭一号喷淋系统
        // 关闭继电器
       if(DEVICE_ID == 1){
          digitalWrite(RELAY_PIN, LOW);
          Serial.println("关闭一号喷淋系统");
        }
        // 操作完成后再次清理缓冲区
        clearSerialBuffer();
      break;
    case 7: // 打开二号喷淋系统
        // 打开继电器
        if(DEVICE_ID == 2){
          activateRelay();
          Serial.println("打开二号喷淋系统");
        }
        
        // 操作完成后再次清理缓冲区
        clearSerialBuffer();
      break;
    case 8: // 关闭二号喷淋系统 
        // 关闭继电器
       if(DEVICE_ID == 2){
          Serial.println("关闭二号喷淋系统");
          digitalWrite(RELAY_PIN, LOW);
        }
        // 操作完成后再次清理缓冲区
        clearSerialBuffer();
      break;
    default:
      // 未识别的命令，不执行任何操作
      break;
    
  }
  
  // 指令执行完毕后清理串口缓冲区
  clearSerialBuffer();
}

/**
 * 辅助函数：以2位十六进制格式打印字节
 * 用于调试时格式化显示数据
 */
void printHex(byte val) {
  if (val < 16) Serial.print("0");
  Serial.print(val, HEX);
}