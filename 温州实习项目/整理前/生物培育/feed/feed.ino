#include <SoftwareSerial.h>
#include <OneWire.h>
#include <DallasTemperature.h>

/*  
 * 电机控制类 - 封装版
 * 功能：控制电机旋转固定圈数，支持编码器反馈
 */

class MotorController {
private:
  // 引脚定义
  const int MOTOR_PWM_PIN;
  const int MOTOR_DIR_PIN;
  const int ENCODER_A_PIN;
  const int ENCODER_B_PIN;
  
  // 参数设置
  const int DEFAULT_SPEED;
  const int ENCODER_PPR;
  const float TARGET_REVOLUTIONS;
  const unsigned long COOLDOWN_PERIOD = 3000; // 冷却时间5分钟(毫秒)
  
  // 状态变量
  volatile long encoderCount;
  bool motorRunning;
  bool lastEncoderState;
  unsigned long lastCompleteTime; // 上次完成时间戳
  bool isInCooldown; // 是否在冷却期内
  
  // 静态实例指针，用于中断服务函数访问
  static MotorController* instance;
  
  // 静态中断服务函数
  static void updateEncoderStatic() {
    if (instance != nullptr) {
      instance->updateEncoder();
    }
  }
  
  // 实际的编码器更新函数
  void updateEncoder() {
    bool currentAState = digitalRead(ENCODER_A_PIN);
    
    if (currentAState != lastEncoderState) {
      bool bState = digitalRead(ENCODER_B_PIN);
      
      // 根据A相和B相的相对状态判断方向
      if (currentAState == bState) {
        encoderCount++;
      } else {
        encoderCount--;
      }
      
      lastEncoderState = currentAState;
    }
  }
  
public:
  // 构造函数
  MotorController(
    int pwmPin = 6,//5
    int dirPin = 7,//6
    int encoderAPin = 3,//2
    int encoderBPin = 5,//4
    int speed = 41, // 使用原代码中的默认速度
    int encoderPPR = 265, // 使用原代码中的编码器脉冲数
    float targetRevs = 1
  ) : 
    MOTOR_PWM_PIN(pwmPin),
    MOTOR_DIR_PIN(dirPin),
    ENCODER_A_PIN(encoderAPin),
    ENCODER_B_PIN(encoderBPin),
    DEFAULT_SPEED(speed),
    ENCODER_PPR(encoderPPR),
    TARGET_REVOLUTIONS(targetRevs),
    encoderCount(0),
    motorRunning(false),
    lastEncoderState(false),
    lastCompleteTime(0),
    isInCooldown(false)
  {}
  
  // 初始化函数
  void begin() {
    // 设置静态实例指针
    instance = this;
    
    // 初始化电机控制引脚
    pinMode(MOTOR_PWM_PIN, OUTPUT);
    pinMode(MOTOR_DIR_PIN, OUTPUT);
    
    // 初始化编码器引脚
    pinMode(ENCODER_A_PIN, INPUT_PULLUP);
    pinMode(ENCODER_B_PIN, INPUT_PULLUP);
    
    // 设置编码器中断
    attachInterrupt(digitalPinToInterrupt(ENCODER_A_PIN), updateEncoderStatic, CHANGE);
    
    // 初始状态
    stopMotor(false); // 静默停止，避免不必要的输出
    lastEncoderState = digitalRead(ENCODER_A_PIN);
  }
  
  // 启动电机旋转固定圈数
  void startMotor(bool printStatus = true) {
    if (!motorRunning) {
      // 设置电机方向为正转
      digitalWrite(MOTOR_DIR_PIN, HIGH);
      
      // 重置编码器计数
      resetEncoder();
      
      // 启动电机
      analogWrite(MOTOR_PWM_PIN, DEFAULT_SPEED);
      motorRunning = true;
      
      if (printStatus) {
        Serial.println("电机启动 - 旋转1圈后将自动停止");
      }
    }
  }
  
  // 停止电机
  void stopMotor(bool printStatus = true) {
    analogWrite(MOTOR_PWM_PIN, 0);
    motorRunning = false;
    if (printStatus) {
      Serial.println("电机已停止");
    }
  }
  
  // 获取当前旋转圈数
  float getRevolutions() {
    noInterrupts();// 禁用中断，确保计数准确
    long count = encoderCount;
    interrupts();// 启用中断
    
    return (float)abs(count) / ENCODER_PPR;
  }
  
  // 获取编码器计数
  long getEncoderCount() {
    noInterrupts();
    long count = encoderCount;
    interrupts();
    return count;
  }
  
  // 重置编码器计数
  void resetEncoder() {
    noInterrupts();
    encoderCount = 0;
    interrupts();
  }
  
  // 检查电机是否正在运行
  bool isRunning() {
    return motorRunning;
  }
  
  // 更新函数 - 应在loop()中定期调用
  bool update(bool printCompleteStatus = true) {
    // 更新冷却状态
    unsigned long currentTime = millis();
    if (isInCooldown && (currentTime - lastCompleteTime >= COOLDOWN_PERIOD)) {
      isInCooldown = false;
    }
    
    // 检查是否达到目标圈数
    if (motorRunning) {
      float currentRevolutions = getRevolutions();
      
      if (currentRevolutions >= TARGET_REVOLUTIONS) {
        stopMotor(printCompleteStatus);
         
        // 设置完成时间和冷却状态
        lastCompleteTime = currentTime;
        isInCooldown = true;
        return true;  // 返回true表示动作完成
      }
    }
    return false;  // 返回false表示动作未完成或未开始
  }
  
  // 检查是否可以启动电机（不在冷却期内）
  bool canStart() {
    return !isInCooldown && !motorRunning;
  }
  
  // 获取剩余冷却时间（毫秒）
  unsigned long getRemainingCooldown() {
    if (!isInCooldown) return 0;
    
    unsigned long currentTime = millis();
    unsigned long elapsed = currentTime - lastCompleteTime;
    
    if (elapsed >= COOLDOWN_PERIOD) {
      isInCooldown = false; // 更新状态
      return 0;
    }
    
    return COOLDOWN_PERIOD - elapsed;
  }
  
  // 获取冷却状态
  bool getCooldownStatus() {
    return isInCooldown;
  }
};

// 静态成员初始化
MotorController* MotorController::instance = nullptr;

// 传感器引脚定义
#define TEMP_DS18B20_PIN A0     // DS18B20温度传感器的数据引脚  2号改到A0
#define PH_PIN A2        // pH值传感器的模拟输入引脚

// 电机和编码器相关引脚已在MotorController类中定义
// 编码器相关常量已在MotorController类中定义
// LoRa通信引脚定义
#define Lora_RX 9      // LoRa模块接收引脚
#define Lorx_TX 10      // LoRa模块发送引脚
// 参数定义
#define PH_OFFSET 0.00        // pH值偏差补偿值
#define TEMP_OFFSET 0.00      // 水温偏差补偿值
 

// 电机速度已在MotorController类构造函数中设置为80

#define DEVICE_ID 1          // 设备ID (十进制) - 1号水培柜
                              // 设备号对照表：
                              // 1号水培柜：12 (0x0C)
                              // 2号水培柜：13 (0x0D)
                              // 3号水培柜：14 (0x0E)

// 指令说明
// A0 0C 01 00 FF  - 正转水培一号
// A0 0C 01 01 FF  - 反转水培一号
// A0 0C 00 00 FF  - 停止水培一号

// 功能ID定义
#define Servo_ID 0x01         // 电机功能ID

// 全局变量定义
// ========== PH校准参数区域 ==========
float phOffset = 3.4;     // PH值校准偏移量
float phValue = 0.0;      // 当前PH值
float waterTemp = 0;        // 水温
static int dataCount = 0;   // 数据包计数
float currentRevolutions;

// 创建电机控制器实例
MotorController motorController; // 使用默认参数初始化

// 初始化软件串口用于LoRa通信
SoftwareSerial loraSerial(Lora_RX, Lorx_TX);

// 初始化OneWire对象用于DS18B20温度传感器通信
OneWire oneWire(TEMP_DS18B20_PIN);
DallasTemperature sensors(&oneWire);

/**
 * 初始化函数
 * 配置串口、传感器和引脚模式
 */
// 编码器相关函数已在MotorController类中实现

void setup() {
  // 初始化串口通信
  Serial.begin(9600);      // 调试串口
  loraSerial.begin(115200);  // LoRa模块串口
  sensors.begin();        // 初始化温度传感器
  // 设置pH传感器引脚为输入模式
  pinMode(PH_PIN, INPUT);
  // 初始化电机控制器（会自动设置电机和编码器引脚）
  motorController.begin();
  delay(1000);
}

/**
 * 主循环函数
 * 处理LoRa指令、读取传感器数据并更新显示
 */
void loop() {
  // 确保监听LoRa串口
  loraSerial.listen(); 
  // 检查LoRa串口是否有数据
  if (loraSerial.available()) {
    // 读取第一个字节，检查是否是起始标志
    byte startByte = loraSerial.read();
     
    // 处理B0查询指令
    if (startByte == 0xB0) {
      byte nextByte = loraSerial.read();
      // 检查设备ID是否匹配
      if (nextByte == DEVICE_ID) {
        // 发送传感器数据
        sendWaterData(phValue, waterTemp);            
      }
    }
    // 处理A0控制指令
    else if (startByte == 0xA0) {
        
      byte buffer[4]; // 已读取第一个字节，还需读取4个字节
      int remainingBytes = loraSerial.readBytes(buffer, 4);
      // 检查是否成功读取完整数据包
      if (remainingBytes == 4) {
        // 构建完整的5字节数据包
        byte fullPacket[5] = {0xA0, buffer[0], buffer[1], buffer[2], buffer[3]};//A0 0C 01 00 FF
        byte action = fullPacket[2];   // 动作代码
        byte value = fullPacket[3];    // 值
        byte endByte = fullPacket[4];  // 帧尾
        // 验证节点ID（同时支持十进制和十六进制设备ID）
        
        if (fullPacket[1] == DEVICE_ID) {
          // 检查帧尾是否为FF
          if (endByte == 0xFF) {
            // 根据动作代码执行相应操作
            controlMotor(1, 1);                   
          } 
        } 
      } 
    }
    clearSerialBuffer();
   
  }
 
  // 周期性读取传感器数据
  readPhValue();                 // 读取pH值
  waterTemp = readWaterTempValue();   // 读取水温
  
  
  // 使用MotorController更新电机状态
  bool motorComplete = motorController.update(false); // 静默更新，不打印完成信息
  if (motorComplete) {
    currentRevolutions = motorController.getRevolutions();
    Serial.print("电机旋转完成，实际转动圈数：");
    Serial.println(currentRevolutions, 2);
    Serial.println("电机自动停止");
  }
  
  // 如果电机正在运行，实时打印当前圈数
  if (motorController.isRunning()) {
    currentRevolutions = motorController.getRevolutions();
    static unsigned long lastPrintTime = 0;
    unsigned long currentTime = millis();
    
    // 每500毫秒打印一次当前圈数
    if (currentTime - lastPrintTime >= 500) {
      Serial.print("当前转动圈数：");
      Serial.println(currentRevolutions, 2);
      lastPrintTime = currentTime;
    }
  } 
}

void controlMotor(int state, int direction) {
  // 使用MotorController控制电机
  if (state == 0) {
    // 停止电机
    motorController.stopMotor();
    Serial.println("电机停止指令");
  } else {
    // 检查是否可以启动电机（不在冷却期内）
    if (motorController.canStart()) {
      // 启动电机旋转1圈
      motorController.startMotor();
      Serial.println("接收到电机转动指令，开始旋转1圈");
      Serial.println("目标圈数：1.0");
    } else {
      // 在冷却期内，不执行电机启动
      unsigned long remainingCooldown = motorController.getRemainingCooldown();
      float minutes = remainingCooldown / 60000.0;
      float seconds = (remainingCooldown % 60000) / 1000.0;
      Serial.print("电机在冷却期内，剩余时间约 ");
      Serial.print(minutes, 0);
      Serial.print("分");
      Serial.print(seconds, 0);
      Serial.println("秒");
    }
  }
}

void readPhValue() {
  // 多次采样取平均值，提高精度
  int sum = 0;
  for (int i = 0; i < 10; i++) {
    sum += analogRead(PH_PIN);
    
  }
  
  // 计算平均ADC值
  int adcValue = sum / 10;

  
  // 转换为电压
  float voltage = adcValue * (5.0 / 1024.0);
 
  
  // 基础pH值计算
  float basePh = 7.0 + (voltage - 2.5) / 0.198;
 
  
  // 应用偏移量
  phValue = basePh + phOffset;
  
  // 确保PH值在合理范围内
  if (phValue < 0.0) phValue = 0.0;
  if (phValue > 14.0) phValue = 14.0;
 
}
float getTemp(){  
  //returns the temperature from one DS18S20 in DEG Celsius

  byte data[12];
  byte addr[8];

  if ( !oneWire.search(addr)) { 
      //no more sensors on chain, reset search
      oneWire.reset_search();
      return -1000;
  }

  if ( OneWire::crc8( addr, 7) != addr[7]) {
      // Serial.println("CRC is not valid!");
      return -1000;
  }

  if ( addr[0] != 0x10 && addr[0] != 0x28) {
      // Serial.print("Device is not recognized");
      return -1000;
  }

  oneWire.reset();
  oneWire.select(addr);
  oneWire.write(0x44,1); // start conversion, with parasite power on at the end

  byte present = oneWire.reset();
  oneWire.select(addr);    
  oneWire.write(0xBE); // Read Scratchpad

  
  for (int i = 0; i < 9; i++) { // we need 9 bytes
    data[i] = oneWire.read();
  }
  
  oneWire.reset_search();
  
  byte MSB = data[1];
  byte LSB = data[0];

  float tempRead = ((MSB << 8) | LSB); //using two's compliment
  float TemperatureSum = tempRead / 16;
   
  return TemperatureSum;
  
}
float readWaterTempValue() {
  float temp = getTemp();
  // 确保温度值有效，并应用温度补偿
  if (temp > -50 && temp < 100) {  // 有效温度范围检查
    return temp + TEMP_OFFSET;     // 应用温度补偿
  }
  return 0;  // 无效温度返回0
}
void sendWaterData(float pHValue, float tempValue) {
  // 数据格式：设备码,pH值,温度值（逗号分隔，便于接收端解析）
  // 示例：12,6.8,25.5（设备ID=12，pH=6.8，温度=25.5°C）
  String sendData = String(DEVICE_ID) + ","             
                  + String(int(pHValue)) + ","  // pH值（2位小数）
                  + String(int(tempValue));
                    
  // 通过LoRa串口发送数据（末尾加换行符，接收端可按行读取）
  loraSerial.println(sendData);
  clearSerialBuffer();
}


void printHex(byte value) {
  if (value < 16) {
    Serial.print("0");
  }
  Serial.print(value, HEX);
}
// 电机启动功能已在MotorController类的startMotor()方法中实现
void clearSerialBuffer() {
  // lora数据发送完成
  loraSerial.flush();
  
  // 短暂延时确保所有响应数据都已到达
  
  
  // 清空接收缓冲区中可能存在的残留数据
  while (loraSerial.available() > 0) {
    loraSerial.read(); // 读取并丢弃所有可用字节
  }
}