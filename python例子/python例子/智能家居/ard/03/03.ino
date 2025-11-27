/*
 * 智能家居系统 - 安防节点 (Arduino ID: 0x03)
 * 
 * 接线说明:
 * 
 * LoRa模块:
 *   LoRa TX  -> Arduino D7
 *   LoRa RX  -> Arduino D8
 *   LoRa VCC -> 3.3V
 *   LoRa GND -> GND
 * 
 * 主卧窗帘电机 (L298N驱动):
 *   IN1      -> Arduino D5
 *   IN2      -> Arduino D6
 *   ENA      -> 不接(使用跳线帽使能)
 *   +12V     -> 外部12V电源正极
 *   GND      -> 外部12V电源负极 & Arduino GND
 * 
 * 门锁舵机:
 *   SIGNAL   -> Arduino D3
 *   VCC      -> 5V
 *   GND      -> GND
 * 
 * 厨房油烟机电机 (L298N驱动):
 *   IN1      -> Arduino D11
 *   IN2      -> Arduino D12
 *   ENA      -> 不接(使用跳线帽使能)
 *   +12V     -> 外部12V电源正极
 *   GND      -> 外部12V电源负极 & Arduino GND
 * 
 * 蜂鸣器:
 *   +        -> Arduino D9
 *   -        -> GND
 * 
 * 烟雾传感器 (MQ-2):
 *   A0       -> Arduino A0
 *   VCC      -> 5V
 *   GND      -> GND
 *   DO       -> 不接(使用模拟输出)
 * 
 * PIR人体传感器:
 *   OUT      -> Arduino D2
 *   VCC      -> 5V
 *   GND      -> GND
 * 
 * 电源说明:
 *   Arduino供电: 7-12V DC
 *   电机驱动: 外部12V电源
 *   传感器: 5V
 * 
 * 功能:
 *   - 主卧窗帘控制
 *   - 门锁控制 (手动+自动PIR感应)
 *   - 厨房油烟机控制 (手动+自动烟雾检测)
 *   - 烟雾检测报警
 *   - 人体感应自动门禁
 */
#include <SoftwareSerial.h>
#include <Servo.h>

#define LORA_RX_PIN 7
#define LORA_TX_PIN 8
#define LORA_BAUD_RATE 115200
SoftwareSerial loraSerial(LORA_RX_PIN, LORA_TX_PIN);

#define NODE_ID 0x03  // 安防节点

// 主卧窗帘引脚
const int PIN_MASTER_CURTAIN_IN1 = 5;
const int PIN_MASTER_CURTAIN_IN2 = 6;

// 门锁舵机引脚
const int PIN_DOOR_SERVO = 3;

// 油烟机引脚
const int PIN_FAN_MOTOR_IN1 = 11;
const int PIN_FAN_MOTOR_IN2 = 12;
const int PIN_BUZZER = 9;

// 烟雾传感器引脚
const int PIN_SMOKE_SENSOR_A = A1;

// PIR人体传感器引脚
const int PIN_PIR_SENSOR = 2;

// 创建对象
Servo doorServo;

// 状态变量
enum CurtainState { CURTAIN_IDLE, CURTAIN_OPENING, CURTAIN_CLOSING };
CurtainState curtain_state = CURTAIN_IDLE;
unsigned long curtain_start_time = 0;
const unsigned long CURTAIN_TRAVEL_TIME = 1000;

// 门锁状态
const int DOOR_OPEN_ANGLE = 0;
const int DOOR_CLOSED_ANGLE = 90;
bool is_door_auto_mode = false;
bool door_state = false; // 门状态：false为关闭，true为打开
bool is_door_opened_by_pir = false;
unsigned long door_opened_time = 0;
unsigned long last_pir_trigger_time = 0;
const unsigned long DOOR_AUTO_CLOSE_TIME = 2000; // 2秒后自动关门

// 油烟机状态
bool is_fan_auto_mode = false;
bool is_fan_on = false;
const int SMOKE_THRESHOLD = 500; // 烟雾阈值

// PIR状态
bool last_pir_state = false;
bool current_pir_triggered = false;

// 烟雾传感器数据
int smoke_value = 0;

void setup() {
  Serial.begin(115200);
  loraSerial.begin(LORA_BAUD_RATE);
  
  Serial.println(F("Security Node Booting... (ID: 0x03)"));

  // 初始化引脚
  pinMode(PIN_MASTER_CURTAIN_IN1, OUTPUT);
  pinMode(PIN_MASTER_CURTAIN_IN2, OUTPUT);
  pinMode(PIN_FAN_MOTOR_IN1, OUTPUT);
  pinMode(PIN_FAN_MOTOR_IN2, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_PIR_SENSOR, INPUT);
  
  // 初始化舵机
  doorServo.attach(PIN_DOOR_SERVO);
  doorServo.write(DOOR_CLOSED_ANGLE);
  
  // 初始状态
  stopCurtain();
  stopFan();
  noTone(PIN_BUZZER);
  door_state = false; // 初始门状态为关闭
  
  Serial.println(F("Setup Complete."));
}

void loop() {
 
  loraSerial.listen(); 
  // 处理LoRa指令
  if (loraSerial.available()) {
    byte startByte = loraSerial.read();
    if (startByte== 0x55) {
      byte buffer[5];
      Serial.println("Start Reading Bytes");
      loraSerial.readBytes(buffer, 5);
      if (buffer[0] == 0xAA && buffer[4] == 0xFF) {
        byte device_type = buffer[1];
        byte action = buffer[2];
        
        // 处理窗户指令(04)和所有设备指令(05)
        if (device_type == 0x03 || device_type == 0x05) {
          processSecurityCommand(device_type, action);
        }
      }
    }else if (startByte== 0xFE) {
      byte nextbyte=loraSerial.read();
      if (nextbyte==NODE_ID){
        byte lastbyte=loraSerial.read();
        if (lastbyte==0xFF){
          // 处理JSON数据请求
          sendSmokeData();
        }
      }
    }
    while (loraSerial.available()){
      loraSerial.read();
 
    }
  }
  smoke_value = analogRead(PIN_SMOKE_SENSOR_A);
  
  // 自动化处理
  handleCurtainAutoStop();
  handleDoorAutoMode();
  handleSmokeDetection();
  
  // 读取烟雾传感器值
  
  
  delay(10);
}

void processSecurityCommand(byte device_type, byte action) {
  Serial.print("Security Command - Action: 0x");
  Serial.println(action, HEX);
  
  // 接收到任何控制指令时，退出自动模式
  if (action != 0x05 && action != 0x08) { // 排除自动模式指令本身
    if (is_door_auto_mode) {
      is_door_auto_mode = false;
      Serial.println("Door Auto Mode OFF (Manual control detected)");
    }
    if (is_fan_auto_mode) {
      is_fan_auto_mode = false;
      Serial.println("Fan Auto Mode OFF (Manual control detected)");
    }
  }
  
  switch (action) {
    // 主卧窗帘控制
    case 0x01: controlMasterCurtain(true); break;   // 拉开主卧窗帘
    case 0x02: controlMasterCurtain(false); break;  // 关闭主卧窗帘
    
    // 门锁控制
    case 0x03: controlDoor(true); break;            // 开门
    case 0x04: controlDoor(false); break;           // 关门
    case 0x05: setDoorAutoMode(true); break;        // 自动门禁
    
    // 油烟机控制
    case 0x06: controlKitchenFan(true); break;      // 打开油烟机
    case 0x07: controlKitchenFan(false); break;     // 关闭油烟机
    case 0x08: setFanAutoMode(true); break;         // 自动油烟机
  }
}



// 发送烟雾数据
void sendSmokeData() {
  
  String json ="{\"smoke\":" + String(smoke_value) +",\"door_status\":" + String(door_state) +",\"hood_status\":" + String(is_fan_on) +"}";
  loraSerial.println(json);
  Serial.println("Sent: " + json);
}

// 主卧窗帘控制函数
void controlMasterCurtain(bool open) {
  if (curtain_state != CURTAIN_IDLE) {
    stopCurtain();
    delay(200);
  }
  
  if (open) {
    digitalWrite(PIN_MASTER_CURTAIN_IN1, HIGH);
    digitalWrite(PIN_MASTER_CURTAIN_IN2, LOW);
    curtain_state = CURTAIN_OPENING;
    Serial.println("Master Curtain Opening");
  } else {
    digitalWrite(PIN_MASTER_CURTAIN_IN1, LOW);
    digitalWrite(PIN_MASTER_CURTAIN_IN2, HIGH);
    curtain_state = CURTAIN_CLOSING;
    Serial.println("Master Curtain Closing");
  }
  curtain_start_time = millis();
}

void stopCurtain() {
  digitalWrite(PIN_MASTER_CURTAIN_IN1, LOW);
  digitalWrite(PIN_MASTER_CURTAIN_IN2, LOW);
  if (curtain_state != CURTAIN_IDLE) {
    Serial.println("Master Curtain Stopped");
    curtain_state = CURTAIN_IDLE;
  }
}

void handleCurtainAutoStop() {
  if (curtain_state != CURTAIN_IDLE && millis() - curtain_start_time >= CURTAIN_TRAVEL_TIME) {
    stopCurtain();
    Serial.println("Master Curtain Auto Stopped");
  }
}

// 门锁控制函数
void controlDoor(bool open) {
  is_door_auto_mode = false; // 手动控制时退出自动模式
  
  if (open) {
    doorServo.write(DOOR_OPEN_ANGLE);
    door_state = true;
    Serial.println("Door OPEN");
  } else {
    doorServo.write(DOOR_CLOSED_ANGLE);
    door_state = false;
    is_door_opened_by_pir = false;
    Serial.println("Door CLOSED");
  }
}

void setDoorAutoMode(bool autoMode) {
  is_door_auto_mode = autoMode;
  is_door_opened_by_pir = false;
  Serial.println(autoMode ? "Door Auto Mode ON" : "Door Auto Mode OFF");
}

// 门自动模式处理
void handleDoorAutoMode() {
  if (is_door_auto_mode) {
    bool current_pir_state = (digitalRead(PIN_PIR_SENSOR) == HIGH);
    
    // 检测PIR状态变化
    if (current_pir_state && !last_pir_state) {
      // PIR触发，开门并记录时间
      doorServo.write(DOOR_OPEN_ANGLE);
      door_state = true;
      is_door_opened_by_pir = true;
      door_opened_time = millis();
      last_pir_trigger_time = millis();
       
    }
    
    // 更新PIR触发状态
    if (current_pir_state) {
      last_pir_trigger_time = millis();
      current_pir_triggered = true;
    } else {
      current_pir_triggered = false;
    }
    
    last_pir_state = current_pir_state;
    
    // 自动关门逻辑：检测不到人2秒后自动关门
    if (is_door_opened_by_pir && (millis() - last_pir_trigger_time >= DOOR_AUTO_CLOSE_TIME)) {
      doorServo.write(DOOR_CLOSED_ANGLE);
      door_state = false;
      is_door_opened_by_pir = false;
      Serial.println("Auto Closing Door (No person detected for 2s)");
    }
  }
}

// 油烟机控制函数
void controlKitchenFan(bool turnOn) {
  is_fan_auto_mode = false; // 手动控制时退出自动模式
  is_fan_on = turnOn;
  
  if (turnOn) {
    digitalWrite(PIN_FAN_MOTOR_IN1, HIGH);
    digitalWrite(PIN_FAN_MOTOR_IN2, LOW);
    noTone(PIN_BUZZER); // 关闭报警
    Serial.println("Kitchen Fan ON");
  } else {
    digitalWrite(PIN_FAN_MOTOR_IN1, LOW);
    digitalWrite(PIN_FAN_MOTOR_IN2, LOW);
    Serial.println("Kitchen Fan OFF");
  }
}

void setFanAutoMode(bool autoMode) {
  is_fan_auto_mode = autoMode;
  Serial.println(autoMode ? "Fan Auto Mode ON" : "Fan Auto Mode OFF");
}

// 烟雾检测处理
void handleSmokeDetection() {
  if (smoke_value > SMOKE_THRESHOLD) {
    // 烟雾浓度过高，触发报警
    tone(PIN_BUZZER, 1000);
    
    
    if (is_fan_auto_mode) {
      // 自动模式下开启风扇
      if (!is_fan_on) {
        digitalWrite(PIN_FAN_MOTOR_IN1, HIGH);
        digitalWrite(PIN_FAN_MOTOR_IN2, LOW);
        is_fan_on = true;
        Serial.println("蜂鸣器打开");
        Serial.println("Auto Fan ON due to smoke");
      }
    } 
  } else {
    // 烟雾浓度正常
    noTone(PIN_BUZZER);
    
    if (is_fan_auto_mode && is_fan_on) {
      // 自动模式下关闭风扇
      digitalWrite(PIN_FAN_MOTOR_IN1, LOW);
      digitalWrite(PIN_FAN_MOTOR_IN2, LOW);
      is_fan_on = false;
      Serial.println("Smoke Clear - Auto Fan OFF");
    }
  }
}

void stopFan() {
  digitalWrite(PIN_FAN_MOTOR_IN1, LOW);
  digitalWrite(PIN_FAN_MOTOR_IN2, LOW);
  is_fan_on = false;
  noTone(PIN_BUZZER);
}
