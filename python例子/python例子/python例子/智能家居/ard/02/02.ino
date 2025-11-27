/*
 * 智能家居系统 - 多功能节点 (Arduino ID: 0x02)
 * #include <Adafruit_PN532.h>

 * 接线说明:
 * 
 * LoRa模块:
 *   LoRa TX  -> Arduino D11
 *   LoRa RX  -> Arduino D12
 *   LoRa VCC -> 3.3V
 *   LoRa GND -> GND
 * 
 * MP3播放器:
 *   MP3 RX   -> Arduino D7
 *   MP3 TX   -> Arduino D8
 *   MP3 VCC  -> 5V
 *   MP3 GND  -> GND
 * 
 * 书桌升降电机 (L298N驱动):
 *   IN1      -> Arduino D5
 *   IN2      -> Arduino D6
 *   ENA      -> 不接(使用跳线帽使能)
 *   +12V     -> 外部12V电源正极
 *   GND      -> 外部12V电源负极 & Arduino GND
 * 
 * 次卧窗帘电机 (L298N驱动):
 *   IN1      -> Arduino D9
 *   IN2      -> Arduino D10
 *   ENA      -> 不接(使用跳线帽使能)
 *   +12V     -> 外部12V电源正极
 *   GND      -> 外部12V电源负极 & Arduino GND
 * 
 * 卫生间排风电机 (L298N驱动):
 *   IN1      -> Arduino A2
 *   IN2      -> Arduino A3
 *   ENA      -> 不接(使用跳线帽使能)
 *   +12V     -> 外部12V电源正极
 *   GND      -> 外部12V电源负极 & Arduino GND
 * 
 * 电源说明:
 *   Arduino供电: 7-12V DC
 *   电机驱动: 外部12V电源 (根据电机规格调整)
 * 
 * 功能:
 *   - MP3音乐播放控制 (播放/暂停/切歌/音量)
 *   - 书桌升降控制
 *   - 次卧窗帘控制
 *   - 卫生间排风控制
 */
#include <SoftwareSerial.h>
#include <Servo.h>

const int LORA_RX_PIN = 11;
const int LORA_TX_PIN = 12;
#define LORA_BAUD_RATE 115200
SoftwareSerial loraSerial(LORA_RX_PIN, LORA_TX_PIN);

#define NODE_ID 0x02  // 多功能节点

// MP3播放器引脚
const int PIN_MP3_RX = 7;
const int PIN_MP3_TX = 8;
SoftwareSerial mp3Serial(PIN_MP3_RX, PIN_MP3_TX);

// 书桌电机引脚
const int PIN_DESK_MOTOR_IN1 = 5;
const int PIN_DESK_MOTOR_IN2 = 6;

// 次卧窗帘引脚
const int PIN_CURTAIN_MOTOR_IN1 = 9;
const int PIN_CURTAIN_MOTOR_IN2 = 10;

// 卫生间排风引脚
const int PIN_FAN_MOTOR_IN1 = A2;
const int PIN_FAN_MOTOR_IN2 = A3;

// 书桌状态
enum DeskState { DESK_IDLE, DESK_MOVING_UP, DESK_MOVING_DOWN };
DeskState desk_state = DESK_IDLE;
unsigned long desk_start_time = 0;
const unsigned long DESK_TRAVEL_TIME = 5000;
// 移除 DESK_MOTOR_SPEED 常量，不再使用PWM

// 窗帘状态
enum CurtainState { CURTAIN_IDLE, CURTAIN_OPENING, CURTAIN_CLOSING };
CurtainState curtain_state = CURTAIN_IDLE;
unsigned long curtain_start_time = 0;
const unsigned long CURTAIN_TRAVEL_TIME = 1000;        // 正常运行时电机转动时间
const unsigned long INIT_CURTAIN_TRAVEL_TIME = 3000;   // 初始化时延长到3秒
// 窗帘物理状态变量
bool curtain_physical_open = false;  // true=打开, false=关闭
bool curtain_moving = false;         // true=正在运动

// 排风状态
bool is_fan_auto_mode = false;
bool is_fan_on = false;

// MP3状态
enum MP3State {
  MP3_STOPPED,    // 停止状态
  MP3_PLAYING,    // 播放状态  
  MP3_PAUSED      // 暂停状态
};
MP3State mp3_state = MP3_STOPPED;
int current_track = 1;
int current_volume = 20;
bool is_mp3_playing = false;  // 保持原有变量兼容性
// MP3原始指令
char MP3_PLAY_TRACK_1[]  = {0X7E, 0XFF, 0X06, 0X0F, 0X00, 0X01, 0X01, 0XEF};
char MP3_PLAY_TRACK_2[]  = {0X7E, 0XFF, 0X06, 0X0F, 0X00, 0X01, 0X02, 0XEF};
char MP3_PLAY_TRACK_3[]  = {0X7E, 0XFF, 0X06, 0X0F, 0X00, 0X01, 0X03, 0XEF};
char MP3_PLAY_TRACK_4[]  = {0X7E, 0XFF, 0X06, 0X0F, 0X00, 0X01, 0X04, 0XEF};
char MP3_PLAY_TRACK_5[]  = {0X7E, 0XFF, 0X06, 0X0F, 0X00, 0X01, 0X05, 0XEF};
char MP3_PLAY_TRACK_6[]  = {0X7E, 0XFF, 0X06, 0X0F, 0X00, 0X01, 0X06, 0XEF};
char MP3_PLAY_TRACK_7[]  = {0X7E, 0XFF, 0X06, 0X0F, 0X00, 0X01, 0X07, 0XEF};
char MP3_PLAY_TRACK_8[]  = {0X7E, 0XFF, 0X06, 0X0F, 0X00, 0X01, 0X08, 0XEF};
char MP3_PLAY_TRACK_9[]  = {0X7E, 0XFF, 0X06, 0X0F, 0X00, 0X01, 0X09, 0XEF};
char MP3_PLAY_TRACK_10[] = {0X7E, 0XFF, 0X06, 0X0F, 0X00, 0X01, 0X0A, 0XEF};
char MP3_PAUSE[]         = {0X7E, 0XFF, 0X06, 0X0E, 0X00, 0X00, 0X00, 0XEF};
char MP3_RESUME[]        = {0X7E, 0XFF, 0X06, 0X0D, 0X00, 0X00, 0X00, 0XEF};
char MP3_NEXT[]          = {0X7E, 0XFF, 0X06, 0X01, 0X00, 0X00, 0X00, 0XEF};
char MP3_PREV[]          = {0X7E, 0XFF, 0X06, 0X02, 0X00, 0X00, 0X00, 0XEF};
char MP3_VOL_30[]        = {0X7E, 0XFF, 0X06, 0X06, 0X00, 0X00, 0X1E, 0XEF};
char MP3_VOL_25[]        = {0X7E, 0XFF, 0X06, 0X06, 0X00, 0X00, 0X19, 0XEF};
char MP3_VOL_20[]        = {0X7E, 0XFF, 0X06, 0X06, 0X00, 0X00, 0X14, 0XEF};
char MP3_VOL_15[]        = {0X7E, 0XFF, 0X06, 0X06, 0X00, 0X00, 0X0F, 0XEF};
char MP3_VOL_10[]        = {0X7E, 0XFF, 0X06, 0X06, 0X00, 0X00, 0X0A, 0XEF};

void setup() {
  Serial.begin(115200);
  loraSerial.begin(LORA_BAUD_RATE);
  mp3Serial.begin(9600);
  
  Serial.println(F("Multi-Function Node Booting... (ID: 0x02)"));

  // 初始化引脚
  pinMode(PIN_DESK_MOTOR_IN1, OUTPUT);
  pinMode(PIN_DESK_MOTOR_IN2, OUTPUT);
  pinMode(PIN_CURTAIN_MOTOR_IN1, OUTPUT);
  pinMode(PIN_CURTAIN_MOTOR_IN2, OUTPUT);
  pinMode(PIN_FAN_MOTOR_IN1, OUTPUT);
  pinMode(PIN_FAN_MOTOR_IN2, OUTPUT);
  
  // 初始状态
  stopDesk();
  stopCurtain();
  stopFan();
  
  // 设置MP3初始音量
  sendMP3Command(MP3_VOL_20, 8);
  curtain_physical_open = false;
  curtain_moving = false;
  // 上电自动打开次卧窗帘 - 延长初始化运行时间
  delay(500);  // 短暂延时确保系统稳定
  Serial.println("Power On: Second Bedroom Curtain Opening (Extended Time)");
  openCurtainForInit();  // 使用专门的初始化函数
  
  Serial.println(F("Setup Complete."));
}

void loop() {
  // 处理LoRa指令
  if (loraSerial.available() >= 6) {
    byte buffer[6];
    if (loraSerial.read() == 0x55) {
      buffer[0] = 0x55;
      loraSerial.readBytes(&buffer[1], 5);
      
      if (buffer[1] == 0xAA && buffer[5] == 0xFF) {
        byte device_type = buffer[2];
        byte action = buffer[3];
        
        // 处理MP3/书桌/窗帘/排风指令(02)和所有设备指令(05)
        if (device_type == 0x02 || device_type == 0x05) {
          processMultiFunctionCommand(device_type, action);
        }
      }
    }
    while (loraSerial.available()) {
      byte discard = loraSerial.read();
    }
  }
  
  // 处理MP3状态请求 - 新增
  handleMP3StatusRequest();
  
  // 自动停止处理
  handleDeskAutoStop();
  handleCurtainAutoStop();
  
  delay(10);
}

// 专门的初始化窗帘打开函数 - 延长运行时间
void openCurtainForInit() {
  if (curtain_state != CURTAIN_IDLE) {
    stopCurtain();
    delay(200);
  }
  
  curtain_moving = true;
  digitalWrite(PIN_CURTAIN_MOTOR_IN1, HIGH);
  digitalWrite(PIN_CURTAIN_MOTOR_IN2, LOW);
  curtain_state = CURTAIN_OPENING;
  Serial.println("Curtain Opening for Initialization (Extended Time)");
  
  // 使用延长时间
  curtain_start_time = millis();
  
  // 等待初始化完成
  while (millis() - curtain_start_time < INIT_CURTAIN_TRAVEL_TIME) {
    // 等待窗帘打开完成
    delay(10);
  }
  
  stopCurtain();
  curtain_physical_open = true;  // 设置初始状态为打开
  Serial.println("Curtain Initialization Complete - State: OPEN");
}

//MP3状态上报函数
void sendMP3StatusToPi() {
  // 构建JSON字符串
  String track_name = String(current_track);
  if (track_name.length() == 1) {
    track_name = "00" + track_name;  // 补零到3位
  } else if (track_name.length() == 2) {
    track_name = "0" + track_name;   // 补零到3位
  }
  
  String json = "{\"MP3_Name\":\"" + track_name + "\"}";
  
  // 发送到LoRa
  loraSerial.print('$');
  loraSerial.print(json);
  loraSerial.print('#');
  
  // 调试输出
  Serial.println("-> To Pi (via LoRa): $" + json + "#");
  Serial.print("Current MP3 Track: ");
  Serial.println(current_track);
}

//处理上位机请求的函数
void handleMP3StatusRequest() {
  // 检查是否收到FE 02 FF请求
  if (loraSerial.available() >= 3) {
    byte buffer[3];
    loraSerial.readBytes(buffer, 3);
    
    if (buffer[0] == 0xFE && buffer[1] == 0x02 && buffer[2] == 0xFF) {
      Serial.println("Received MP3 status request: FE 02 FF");
      // 发送当前MP3状态
      sendMP3StatusToPi();
    }
  }
}

void processMultiFunctionCommand(byte device_type, byte action) {
  Serial.print("Multi-Function Command - Action: 0x");
  Serial.println(action, HEX);
  
  switch (action) {
    // MP3控制 - 这些指令会触发状态上报
    case 0x01:  // 播放MP3音乐
      controlMP3(true); 
      break;
    case 0x05:  // 下一首
      nextTrack();
      break;
    case 0x06:  // 上一首
      prevTrack();
      break;
//    case 0x01: controlMP3(true); break;        // 播放MP3音乐
    case 0x02: controlMP3(false); break;       // 暂停MP3音乐
    case 0x03: resumeMP3(); break;             // 继续播放MP3音乐
    case 0x04: stopMP3(); break;               // 停止播放MP3音乐
//    case 0x05: nextTrack(); break;             // 下一首
//    case 0x06: prevTrack(); break;             // 上一首
    case 0x07: adjustMP3Volume(5); break;      // 提高MP3音量
    case 0x08: adjustMP3Volume(-5); break;     // 降低MP3音量
    case 0x09: setMP3Volume(30); break;        // MP3最高音量
    case 0x0A: setMP3Volume(10); break;        // MP3最低音量
    case 0x0B: setMP3Volume(20); break;        // MP3中等音量
    
    // 书桌控制
    case 0x0C: controlDesk(true); break;       // 调高书桌
    case 0x0D: controlDesk(false); break;      // 调低书桌
    case 0x0E: stopDesk(); break;              // 停止书桌
    
    // 排风控制
    case 0x0F: controlFan(true); break;        // 打开排风
    case 0x11: controlFan(false); break;       // 关闭排风
    case 0x12: setFanAutoMode(true); break;    // 自动排风
    
    // 次卧窗帘控制
    case 0x13: controlCurtain(true); break;    // 拉开次卧窗帘
    case 0x14: controlCurtain(false); break;   // 关闭次卧窗帘
  }
}

// MP3控制函数
void controlMP3(bool play) {
  if (play) {
    // 检查当前状态
    if (mp3_state == MP3_PAUSED) {
      Serial.println("MP3 is paused, use resume command instead");
      return;
    }
    
    // 只有在停止状态才能开始播放
    if (mp3_state == MP3_STOPPED) {
      sendMP3Command(MP3_PLAY_TRACK_1, 8);
      mp3_state = MP3_PLAYING;
      is_mp3_playing = true;
      current_track = 1;
      Serial.println("MP3 Started Playing Track 1");
    } else {
      Serial.println("MP3 is already playing");
    }
  } else {
    sendMP3Command(MP3_PAUSE, 8);
    mp3_state = MP3_PAUSED;
    is_mp3_playing = false;
    Serial.println("MP3 Paused");
  }
  // 移除自动发送状态
}

void resumeMP3() {
  // 只有在暂停状态才能继续播放
  if (mp3_state == MP3_PAUSED) {
    sendMP3Command(MP3_RESUME, 8);
    mp3_state = MP3_PLAYING;
    is_mp3_playing = true;
    Serial.println("MP3 Resumed");
  } else if (mp3_state == MP3_STOPPED) {
    Serial.println("MP3 is stopped, use play command instead");
  } else {
    Serial.println("MP3 is already playing");
  }
}

void stopMP3() {
  sendMP3Command(MP3_PAUSE, 8);
  mp3_state = MP3_STOPPED;
  is_mp3_playing = false;
  Serial.println("MP3 Stopped");
}

void nextTrack() {
  // 只有在播放或暂停状态才能切歌
  if (mp3_state == MP3_PLAYING || mp3_state == MP3_PAUSED) {
    current_track = (current_track % 10) + 1;
    switch(current_track) {
      case 1: sendMP3Command(MP3_PLAY_TRACK_1, 8); break;
      case 2: sendMP3Command(MP3_PLAY_TRACK_2, 8); break;
      case 3: sendMP3Command(MP3_PLAY_TRACK_3, 8); break;
      case 4: sendMP3Command(MP3_PLAY_TRACK_4, 8); break;
      case 5: sendMP3Command(MP3_PLAY_TRACK_5, 8); break;
      case 6: sendMP3Command(MP3_PLAY_TRACK_6, 8); break;
      case 7: sendMP3Command(MP3_PLAY_TRACK_7, 8); break;
      case 8: sendMP3Command(MP3_PLAY_TRACK_8, 8); break;
      case 9: sendMP3Command(MP3_PLAY_TRACK_9, 8); break;
      case 10: sendMP3Command(MP3_PLAY_TRACK_10, 8); break;
    }
    mp3_state = MP3_PLAYING;  // 切歌后自动进入播放状态
    is_mp3_playing = true;
    Serial.println("MP3 Next Track: " + String(current_track));
  } else {
    Serial.println("MP3 is stopped, cannot change track");
  }
  // 移除自动发送状态
}

void prevTrack() {
  // 只有在播放或暂停状态才能切歌
  if (mp3_state == MP3_PLAYING || mp3_state == MP3_PAUSED) {
    current_track = (current_track == 1) ? 10 : current_track - 1;
    switch(current_track) {
      case 1: sendMP3Command(MP3_PLAY_TRACK_1, 8); break;
      case 2: sendMP3Command(MP3_PLAY_TRACK_2, 8); break;
      case 3: sendMP3Command(MP3_PLAY_TRACK_3, 8); break;
      case 4: sendMP3Command(MP3_PLAY_TRACK_4, 8); break;
      case 5: sendMP3Command(MP3_PLAY_TRACK_5, 8); break;
      case 6: sendMP3Command(MP3_PLAY_TRACK_6, 8); break;
      case 7: sendMP3Command(MP3_PLAY_TRACK_7, 8); break;
      case 8: sendMP3Command(MP3_PLAY_TRACK_8, 8); break;
      case 9: sendMP3Command(MP3_PLAY_TRACK_9, 8); break;
      case 10: sendMP3Command(MP3_PLAY_TRACK_10, 8); break;
    }
    mp3_state = MP3_PLAYING;  // 切歌后自动进入播放状态
    is_mp3_playing = true;
    Serial.println("MP3 Previous Track: " + String(current_track));
  } else {
    Serial.println("MP3 is stopped, cannot change track");
  }
  // 移除自动发送状态
}

void adjustMP3Volume(int delta) {
  current_volume = constrain(current_volume + delta, 10, 30);
  setMP3Volume(current_volume);
  Serial.println("MP3 Volume: " + String(current_volume));
}

void setMP3Volume(int volume) {
  current_volume = volume;
  if (volume <= 10) sendMP3Command(MP3_VOL_10, 8);
  else if (volume <= 15) sendMP3Command(MP3_VOL_15, 8);
  else if (volume <= 20) sendMP3Command(MP3_VOL_20, 8);
  else if (volume <= 25) sendMP3Command(MP3_VOL_25, 8);
  else sendMP3Command(MP3_VOL_30, 8);
  Serial.println("MP3 Volume Set: " + String(volume));
}

void sendMP3Command(char* command, int length) {
  mp3Serial.listen();
  delay(10);
  for (int i = 0; i < length; i++) {
    mp3Serial.write(command[i]);
  }
  delay(50);
  loraSerial.listen();
}

// 书桌控制函数 - 修改为不使用PWM
void controlDesk(bool moveUp) {
  if (desk_state != DESK_IDLE) {
    stopDesk();
    delay(200);
  }
  
  if (moveUp) {
    // 不使用PWM，直接使用数字输出
    digitalWrite(PIN_DESK_MOTOR_IN1, HIGH);
    digitalWrite(PIN_DESK_MOTOR_IN2, LOW);
    desk_state = DESK_MOVING_UP;
    Serial.println("Desk Moving UP (Full Speed)");
  } else {
    // 不使用PWM，直接使用数字输出
    digitalWrite(PIN_DESK_MOTOR_IN1, LOW);
    digitalWrite(PIN_DESK_MOTOR_IN2, HIGH);
    desk_state = DESK_MOVING_DOWN;
    Serial.println("Desk Moving DOWN (Full Speed)");
  }
  desk_start_time = millis();
}

void stopDesk() {
  // 确保两个引脚都设置为低电平，完全停止电机
  digitalWrite(PIN_DESK_MOTOR_IN1, LOW);
  digitalWrite(PIN_DESK_MOTOR_IN2, LOW);
  if (desk_state != DESK_IDLE) {
    Serial.println("[ACTION] Desk: STOPPED");
    desk_state = DESK_IDLE;
  }
}

void handleDeskAutoStop() {
  if (desk_state != DESK_IDLE && millis() - desk_start_time >= DESK_TRAVEL_TIME) {
    stopDesk();
    Serial.println("Desk Auto Stopped");
  }
}

// 窗帘控制函数 - 正常运行时使用原来的时间
void controlCurtain(bool open) {
  // 检查窗帘是否正在运动中
  if (curtain_moving) {
    Serial.println("Curtain is moving, command ignored");
    return;
  }
  
  // 检查目标状态是否与当前状态一致
  if (open == curtain_physical_open) {
    Serial.println("Curtain already in target state, command ignored");
    return;
  }
  
  if (curtain_state != CURTAIN_IDLE) {
    stopCurtain();
    delay(200);
  }
  
  curtain_moving = true;
  
  if (open) {
    digitalWrite(PIN_CURTAIN_MOTOR_IN1, HIGH);
    digitalWrite(PIN_CURTAIN_MOTOR_IN2, LOW);
    curtain_state = CURTAIN_OPENING;
    Serial.println("Curtain Opening");
  } else {
    digitalWrite(PIN_CURTAIN_MOTOR_IN1, LOW);
    digitalWrite(PIN_CURTAIN_MOTOR_IN2, HIGH);
    curtain_state = CURTAIN_CLOSING;
    Serial.println("Curtain Closing");
  }
  curtain_start_time = millis();
}

void stopCurtain() {
  digitalWrite(PIN_CURTAIN_MOTOR_IN1, LOW);
  digitalWrite(PIN_CURTAIN_MOTOR_IN2, LOW);
  if (curtain_state != CURTAIN_IDLE) {
    // 根据运动方向更新物理状态
    if (curtain_state == CURTAIN_OPENING) {
      curtain_physical_open = true;
    } else if (curtain_state == CURTAIN_CLOSING) {
      curtain_physical_open = false;
    }
    
    curtain_moving = false;
    curtain_state = CURTAIN_IDLE;
    Serial.println("Curtain Stopped, Physical State: " + String(curtain_physical_open ? "OPEN" : "CLOSED"));
  }
}

void handleCurtainAutoStop() {
  if (curtain_state != CURTAIN_IDLE && millis() - curtain_start_time >= CURTAIN_TRAVEL_TIME) {
    stopCurtain();
    Serial.println("Curtain Auto Stopped");
  }
}

// 排风控制函数
void controlFan(bool turnOn) {
  is_fan_auto_mode = false;
  is_fan_on = turnOn;
  if (turnOn) {
    digitalWrite(PIN_FAN_MOTOR_IN1, HIGH);
    digitalWrite(PIN_FAN_MOTOR_IN2, LOW);
    Serial.println("Fan ON");
  } else {
    digitalWrite(PIN_FAN_MOTOR_IN1, LOW);
    digitalWrite(PIN_FAN_MOTOR_IN2, LOW);
    Serial.println("Fan OFF");
  }
}

void setFanAutoMode(bool autoMode) {
  is_fan_auto_mode = autoMode;
  Serial.println(autoMode ? "Fan Auto Mode ON" : "Fan Auto Mode OFF");
}

void stopFan() {
  digitalWrite(PIN_FAN_MOTOR_IN1, LOW);
  digitalWrite(PIN_FAN_MOTOR_IN2, LOW);
  is_fan_on = false;
}
