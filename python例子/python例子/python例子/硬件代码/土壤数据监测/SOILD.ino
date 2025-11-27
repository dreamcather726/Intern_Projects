#include <SoftwareSerial.h>
#include <ModbusMaster.h>

// 定义串口引脚
#define RX_PIN 10
#define TX_PIN 11

// 创建软件串口实例
SoftwareSerial modbusSerial(RX_PIN, TX_PIN);

// 创建ModbusMaster实例
ModbusMaster node;

// 传感器配置
const uint8_t SLAVE_ADDRESS = 1; // 传感器的Modbus地址
const long BAUD_RATE = 4800; // 波特率

void setup() {
  Serial.begin(9600); // 打开串口监视器
  modbusSerial.begin(BAUD_RATE);
  
  // 配置ModbusMaster
  node.begin(SLAVE_ADDRESS, modbusSerial);
}

void loop() {
  uint16_t data[4];

  // 请求读取保持寄存器
  uint8_t result = node.readHoldingRegisters(0, 4);

  if (result == node.ku8MBSuccess) {
    for (uint8_t i = 0; i < 4; i++) {
      data[i] = node.getResponseBuffer(i);
    }

    float moisture = data[0] / 10.0;
    
    int16_t temp_raw = data[1];
    float temperature = (temp_raw > 32767) ? ((float)(temp_raw - 65536) / 10.0) : ((float)temp_raw / 10.0);
    
    float conductivity = data[2];
    float ph = data[3] / 10.0;

    Serial.println("----------------------------------------");
    Serial.print("时间: ");
    Serial.println(getCurrentTime());
    Serial.print("土壤水分: ");
    Serial.print(moisture, 1);
    Serial.println(" %");
    Serial.print("土壤温度: ");
    Serial.print(temperature, 1);
    Serial.println(" °C");
    Serial.print("土壤电导率: ");
    Serial.print(conductivity);
    Serial.println(" μS/cm");
    Serial.print("土壤PH值: ");
    Serial.print(ph, 1);
    Serial.println();
    Serial.println("----------------------------------------");
  } else {
    Serial.print("Failed to read holding registers! Error code: ");
    Serial.println(result);
  }

  delay(500); // 等待5秒后进行下一次读取
}

String getCurrentTime() {
  // 这里可以添加获取当前时间的功能，例如使用RTC模块
  return "2023-10-01 12:34:56"; // 示例时间
}



