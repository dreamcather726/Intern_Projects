#include <Wire.h>
#include <Arduino.h>

#include <Adafruit_PN532.h>
#define PN532_IRQ   (13)
#define PN532_RESET (22) 
Adafruit_PN532 nfc(PN532_IRQ, PN532_RESET);
#include "Freenove_WS2812_Lib_for_ESP32.h"
 
 
#include "SoftwareSerial.h"

#define LEDS_COUNT  6   //彩灯数目
#define LEDS_PIN  2    //ESP32控制ws2812的引脚
#define CHANNEL   0    //控制通道，最多8路
Freenove_ESP32_WS2812 strip = Freenove_ESP32_WS2812(LEDS_COUNT, LEDS_PIN, CHANNEL, TYPE_GRB);//申请一个彩灯控制对象
EspSoftwareSerial::UART swSer;
// 自定义I2C引脚（根据实际硬件修改）
#define I2C_SDA 5   // 实际SDA引脚
#define I2C_SCL 15   // 实际SCL引脚

 
#define OutPut 2
#define InPut 1
#define Len2 5
#define Len3 6

#define L1 5
#define L2 10
#define L4 14
#define L5 15
#define L6 16
 
String N1 ="0x619C0106"; // 
String N2 ="0x012E0206";//0x01 0x2E 0x02 0x06
String N3 ="0xB1310206";//0xB1 0x31 0x02 0x06
String N4 ="0xD1AA0106";//0xD1 0xAA 0x01 0x06
String N5 ="0xE1320206";//0xE1 0x32 0x02 0x06
String N6 ="0xB1AC0106";//0xB1 0xAC 0x01 0x06
String N7 ="0xD13E0206";//0xD1 0x3E 0x02 0x06
String N8 ="0xF12F0206";//0xF1 0x2F 0x02 0x06
String N9 ="0xA1AE0106"; //0xA1 0xAE 0x01 0x06
 
//  0x619C0106
//  0x012E0206
//  0xB1310206
//  0xD1AA0106
//  0xE1320206
//  0xB1AC0106
// 0xD13E0206
// 0xF12F0206
// 0xA1AE0106
 

 
char YL[] = {0X7E, 0XFF, 0X06, 0X06, 0X00, 0X00, 0X00, 0XEF}; //音量调节
//MP3播放
char KS[] = {0X7E, 0XFF, 0X06, 0X0F, 0X00, 0X01, 0X01, 0XEF}; //播放第1首音乐 文件夹名字
/*****LGT硬件引脚
   ADC IN  14~21 7
   PWM OUT 3 5 6 9 10 11
  左轮 方向脚 8
  左轮 速度脚 9
  左轮 中断脚 3 外部中断1
  左轮 计数脚 4

  右轮 方向脚 7
  右轮 速度脚 6
  右轮 中断脚 2 外部中断0
  右轮 计数脚 23

  L1 脉冲脚 5
  L2 脉冲脚 10
  L4 模拟脚 14
  L5 模拟脚 15
  L6 模拟脚 16
*****/
//第2位 功能【0 复位】【1 输入】【2 输出】
//复位
unsigned char RST[5] = {0x55, 0xAA, 0x00, 0x00, 0xFF};
//设置
unsigned char SET[Len2] = {0x55, 0xAA, 0x01, 0x00, 0xFF};
//操作
unsigned char OPER[Len3] = {0x55, 0xAA, 0x00, 0x00, 0x00, 0xFF};//第2位=>操作  第3位=>引脚号；第四位=>数字值
//MP3音量
char code_send[] = {0xFE, 0x06, 0x90, 0x90, 0x1F, 0x10, 0x00, 0x00, 0xFF};
int bc = 0;
int SPeed=65;
int LGT_address = 0x01;
float ero = 1.0;
int I1, I2, I3, I4;
long find_time = 0;//寻找到黑线的时间
bool find_flag = 1;//允许寻找黑线
int find_count = 0;//寻找到黑线的次数
bool P_flag = 0;//停车表示
float basicSpeed = 50;//小车运行速度F
float oldBS = 65;
int carTraceFlag = 0;
int rfidReadFlag= 0;
int tSignFlag = 0;
int readTSignFlag =0;
int tSignCode = 0;
int opFlag = 0;
int blckLineCount =0;
int carParkFlag =0;
int bSChangeFlag = 0;
int halfRightBackFlag=0;
int palyflag = 0;
long curTime =0;
byte curPos=0x0F;
int lastPosint = 0;
int currPosInt =0;
int firstPosInt = 0;
// 全局变量用于循迹计时
unsigned long trackStartTime = 0;
bool isTracking = false;
void setup() {
  Serial.begin(115200);
  Serial2.begin(115200, SERIAL_8N1, 16, 17);
  Serial.println("PN532 RFID测试（WiFiDuino32 自定义I2C引脚）");
  // // 关键：使用自定义引脚初始化I2C
  Wire.begin(I2C_SDA, I2C_SCL);  // 手动指定SDA和SCL引脚

  // 初始化PN532模块
  nfc.begin();

  // 检查PN532是否连接成功
  uint32_t versiondata = nfc.getFirmwareVersion();
  if (!versiondata) {
    Serial.println("未检测到PN532模块，请检查I2C接线！");
    while (1);  // 模块连接失败时停机
  }else{
      Serial.println("等待ISO14443A标准标签（如NTAG203/213）...");
  }
  swSer.begin(9600, EspSoftwareSerial::SWSERIAL_8N1, 18, 19);//RX,TX
  swSer.enableIntTx(true);
  strip.begin();      //初始化彩灯控制引脚
  strip.setBrightness(50);//设置彩灯亮度
  for (int i = 0; i < LEDS_COUNT; i++) {
    strip.setLedColorData(i, 255, 0, 0);
  }
   strip.show();//显示颜色
  delay(1000);
  for (int i = 0; i < LEDS_COUNT; i++) {
    strip.setLedColorData(i, 0, 255, 0);
  }
   strip.show();//显示颜色
  delay(1000);
  for (int i = 0; i < LEDS_COUNT; i++) {
    strip.setLedColorData(i, 0, 0, 255);
  }
  strip.show();//显示颜色
  delay(1000);
  Serial.println("PN532 RFID测试（WiFiDuino32 自定义I2C引脚）");
  volch(20);


}

void loop() {
  if(carTraceFlag == 1)
  {     
      traceLine();
        NfcHandle();
  }
 
  
  
    
  
 
  if (Serial2.available()>9) {
      delay(20);
      unsigned char buf[9];
      Serial2.readBytes(buf, 9);
      if (buf[0] == 0xFE && buf[1] == 0x06&&  buf[3] == 0x90 && buf[4] == 0x1F && buf[6] == 0x10)
      {      
        if (buf[7] == 0x01) {//开始
          carTraceFlag = 1;
          rfidReadFlag = 1;
        }
        else if (buf[7] == 0x02) {//停止
          carStop();
          carTraceFlag = 0;
          rfidReadFlag = 0;
        }       
      }  
      while(Serial2.available())
      {
        delay(20);
        Serial2.read();
      }
    }
    if(curPos!=0x00){
      Serial.println("发送:");
      Serial.println(curPos);
      send_code(curPos);
      curPos=0x00;
      
    }
}
 

void NfcHandle()  
{ 
  String pos = "None";
  
  // 检查循迹状态和时间
  if (isTracking) {
    if (millis() - trackStartTime >= 2000) { // 循迹2秒

      isTracking = false;
      rfidReadFlag = 1;  // 重新启用RFID识别
      Serial.println("循迹2秒结束，重新启用RFID识别");
    }
    else{
      rfidReadFlag=0;
    }
  }
  

  
  
  if(rfidReadFlag == 1)
  {
    pos = readNFC();    
  }
  
  if(pos != "None")
  {
    Serial.print("读取到NFC标签UID（完整十六进制数）: ");
    Serial.println(pos);
    if(pos==N1){
      currPosInt=1;
    }else if(pos == N2){
      currPosInt=2;
    }else if(pos == N3){
      currPosInt=3;
    }else if(pos == N4){
      currPosInt=4;
    }else if(pos == N5){
      currPosInt=5;
    }else if(pos == N6){
      currPosInt=6;
    }else if(pos == N7){
      currPosInt=7;
    }else if(pos == N8){
      currPosInt=8;
    }else if(pos == N9){
      currPosInt=9;
    }
    Serial.print("currPosInt:");
    Serial.print(currPosInt);
    Serial.print("lastPosint:");
    Serial.println(lastPosint);
    bool flag = isway(currPosInt,lastPosint);
    if(!flag)
    { 
      Serial.println("是false路径,掉头");
      //掉头
      setRomeoMotor(0,basicSpeed);
      setRomeoMotor(1, -basicSpeed);
      delay(1500);
      return;
       
    } 
    if(currPosInt == 1) {curPos = 0x01;midHandle(1);Serial.println("N1");carTraceFlag = 0;}
    else if(currPosInt == 2) {curPos = 0x02;midHandle(2);Serial.println("N2");}
    else if(currPosInt == 3) {curPos = 0x03;midHandle(3);Serial.println("N3");}
    else if(currPosInt == 4) {curPos = 0x04;midHandle(4);Serial.println("N4");carTraceFlag = 0;}//停车等待中控指令
    else if(currPosInt == 5) {curPos = 0x05;midHandle(5);Serial.println("N5");}
    else if(currPosInt == 6) {curPos = 0x06;midHandle(6);Serial.println("N6");}
    else if(currPosInt == 7) {curPos = 0x07;midHandle(7);Serial.println("N7");}
    else if(currPosInt == 8) {curPos = 0x08;midHandle(8);Serial.println("N8");}    
    else if(currPosInt == 9) {curPos = 0x0A;midHandle(9);Serial.println("N9");}
      pos = "None";
  } 
  lastPosint = currPosInt;
}

bool isway(int currPos ,int lastPos )
{
 if(firstPosInt == 0)
  {//第一次不管是哪个点，都记录下来，都是起点
        Serial.println("起点");
    firstPosInt = currPos;
    return true;

  }
  if(currPos == 1)
  {

    
    return true;
  }
   if(currPos == 4 and firstPosInt == 4)
  {
    return true;
  }
  if(currPos != lastPos+1)
  {
    Serial.println("不是连续点");
    return false;
  }
  else
  {
    Serial.println("是连续点");
    return true;
  }
}
void startHandle()
{
  carStop();
  send_code(0x01);
  play(1);
 
}



void midHandle(int i)
{
  
  carForward();
  delay(500);
  Serial.println("走一会");
  
  carStop();
  play(i);
  delay(9000);
  Serial.println("播报结束，开始循迹");
  
  // 启动循迹模式，设置开始时间
  isTracking = true;
  trackStartTime = millis();
  rfidReadFlag = 0;
 
}

String readNFC()
{
  boolean success;
  uint8_t uid[] = { 0, 0, 0, 0, 0, 0, 0 };
  uint8_t uidLength;
  String UID = "";
  success = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, &uid[0], &uidLength, 100); // 添加100ms超时，避免阻塞
  if (success) {
    // 创建调试用的16进制字符串（带0x前缀，按字节分隔）
    String debugUID = "";
    // 创建完整UID的16进制字符串（无分隔符，带0x前缀）
    String fullHexUID = "0x";
    for (uint8_t i = 0; i < uidLength; i++) {
      // 保持原有格式用于NFC标签匹配（无0x前缀，空格分隔）
      UID += String(uid[i], HEX);
      if (i < (uidLength - 1)) {
        UID += " ";
      }
      // 生成带0x前缀的两位十六进制字符串用于字节分隔打印
      char hexByte[5];
      sprintf(hexByte, "0x%02X", uid[i]);
      debugUID += hexByte;
      if (i < (uidLength - 1)) {
        debugUID += " ";
      }
      // 生成完整UID的十六进制字符串
      sprintf(hexByte, "%02X", uid[i]);
      fullHexUID += hexByte;
    }

    // 打印完整的16进制UID数
    
    // 返回完整的十六进制UID（带0x前缀）
    return fullHexUID;
  }
  else {
    return "None";
  }
}
void Read_IT() {
  Wire.requestFrom(9, 7);//读取数值
  if (Wire.available() > 0) {
    int len = 7;
    int buf[len];
    for (int i = 0; i < len; i++) {
      buf[i] = Wire.read();
    }
    I1 = buf[2];
    I2 = buf[3];
    I3 = buf[4];
    I4 = buf[5];
 
  }
}
void nfcInit()
 {
  nfc.begin();
  uint32_t versiondata = nfc.getFirmwareVersion();
  if (!versiondata)
  {
    Serial.println("Didn't find PN53x board");
    while (1); // halt
  }
  // Got ok data, print it out!
  digitalWrite(A0, HIGH);
  Serial.print("Found chip PN5");
  Serial.println((versiondata >> 24) & 0xFF, HEX);
  Serial.print("Firmware ver. ");
  Serial.print((versiondata >> 16) & 0xFF, DEC);
  Serial.print('.'); Serial.println((versiondata >> 8) & 0xFF, DEC);
  nfc.setPassiveActivationRetries(0x01);
  nfc.SAMConfig();
  Serial.println("Waiting for an ISO14443A card");
 }
void traceLine() {
    Read_IT(); 
    if (I1 == 1 && I2 == 1) {
      carForward();
      // Serial.println("前进");
    }
    else if (I1 == 0 && I2 == 1) {
      carTurnRight();
      // Serial.println("右转");//
    }
    else if (I1 == 1 && I2 == 0) {
      carTurnLeft();
      // Serial.println("左转");/
    }

  if (I4 == 1 && I3 ==0) {
    carTurnRightFast();
      // Serial.println("快速右转");//
  }
  else if (I3 == 1 && I4 == 0 ) {
    carTurnLeftFast();
      // Serial.println("快速左转"); 
  }
 if((I1== 1 && I3 == 1&&I2 == 1 && I4 ==1 ))
 {
  carStop();
  // Serial.println("停止");
 }
 if((I1== 0 && I3 == 0&&I2 == 0 && I4 ==0 ))
 {
  carTurnLeftFast();
  // Serial.println("停止");
 }
  I1=I2=I3=I4 = 0;
}
 

 
void send_code(byte pos){
  code_send[7] = pos;
  for (int i = 0; i < 9; i++)
  {Serial2.print(code_send[i]);}
  code_send[7] = 0x00;
}

void setRomeoMotor(int N, float speed) {
  int DIR, PWM, F;
  float SP;
  if (N == 1) {
    DIR = 8;
    PWM = 9;
    F = 0;
    SP = ero * speed;
  }
  else if (N == 0) {
    DIR = 7;
    PWM = 6;
    F = 1;
    SP = speed;
  }
  if (speed <= 0) {
    DigitalWrite(DIR, F);
    AnalogWrite(PWM,abs(SP));
  } else {
    DigitalWrite(DIR, !F);
    AnalogWrite(PWM, abs(SP));
  }
}
void carForward(){
  setRomeoMotor(0,basicSpeed);
  setRomeoMotor(1,basicSpeed);
}
void carBackward(){
  setRomeoMotor(0,-basicSpeed);
  setRomeoMotor(1,-basicSpeed);
}

void carTurnLeft(){ //0是右轮，1是左轮，M1是左轮，M2是右轮
   //if(basicSpeed<=130)
    //setRomeoMotor(0,(basicSpeed+10));
   setRomeoMotor(0,basicSpeed-20);
  setRomeoMotor(1,0);
}

void carTurnLeftFast(){
  setRomeoMotor(0,basicSpeed);
  setRomeoMotor(1,0);
}
void carTurnRight(){
  setRomeoMotor(0,0);
 
  setRomeoMotor(1,basicSpeed-20);
}
void carTurnRightFast(){
  setRomeoMotor(0,0);
  setRomeoMotor(1,basicSpeed);
}
void carTurnRightRound(){
  setRomeoMotor(0,-35);
  setRomeoMotor(1,30);
}

void carTurnLeftRound(){
  setRomeoMotor(0,30);
  setRomeoMotor(1,-35);
}

void carStop(){
  setRomeoMotor(0,0);
  setRomeoMotor(1,0);
}

void Off_line(float SPEED1, float SPEED2) {
  setRomeoMotor(1, SPEED1);
  setRomeoMotor(0, SPEED2);
}

void carTurnRightAround(){
  setRomeoMotor(0,70);
  setRomeoMotor(1,-70);
}

void carTurnHalfRightBack()
{
  Read_IT();
  carTurnRightAround();
  if((halfRightBackFlag == 0 && I4 == 1 && I1 == 0 && I2 == 0 && I3 == 0))
  {halfRightBackFlag = 1;Serial.println(halfRightBackFlag);
  }
  if((halfRightBackFlag == 1 && I3 == 0 && I1 == 0 && I2 == 1 && I4 == 0))
  {halfRightBackFlag = 2;Serial.println(halfRightBackFlag);
  }
  if((halfRightBackFlag == 2 && I3 == 0 && I1 == 1 && I2 == 1 && I4 == 0))
  {
    carStop();
    halfRightBackFlag = 0;
  } 
}

int run_L(int way) {
  oldBS = basicSpeed;
  basicSpeed = 170;
  Clear(1);
  AttachInterrupt(1);
  while (1) {
    if (GetCounter(1) < way) {
      Off_line(basicSpeed, 0);
    }
    else if (GetCounter(1) > way) {
      Off_line(-basicSpeed, 0);
    }
    else {
      Off_line(0, 0);
      DetachInterrupt(1);
      basicSpeed = oldBS;
      return 1;
    }
  }
  
}

int run_R(int way) {
  oldBS = basicSpeed;
  basicSpeed = 170;
  Clear(0);
  AttachInterrupt(0);
  while (1) {
    if (GetCounter(0) < way) {
      Off_line(0, basicSpeed);
    }
    else if (GetCounter(0) > way) {
      Off_line(0, -basicSpeed);
    }
    else {
      Off_line(0, 0);
      DetachInterrupt(0);
      basicSpeed = oldBS;
      return 1;
    }
  }
  
}
int run_LR(int way) {
  Clear(0);
  AttachInterrupt(0);
  while (1) {
    if (GetCounter(0) < way) {
      Off_line(basicSpeed, basicSpeed);
    }
    else if (GetCounter(0) > way) {
      Off_line(-basicSpeed, -basicSpeed);
    }
    else {
      Off_line(0, 0);
      DetachInterrupt(0);
      return 1;
    }
  }
}

int run_Encode_Motor(int RL, int way, int mSpeed) {
  int mRL = 0;
  if(RL == 0) mRL = 1;
  else mRL = 0;
  Clear(mRL);
  AttachInterrupt(mRL);
  while (1) {
    if (GetCounter(mRL) < way) {
      if(RL ==0) Off_line(mSpeed, 0);
      else if(RL ==1) Off_line(0,mSpeed);
      else if(RL ==2) Off_line(mSpeed,mSpeed);
    }
    else if (GetCounter(mRL) > way) {
      if(RL ==0)Off_line(-mSpeed, 0);
      else if(RL == 1) Off_line(0,-mSpeed);
      else if(RL == 2) Off_line(-mSpeed,-mSpeed);
    }
    else {
      Off_line(0, 0);
      DetachInterrupt(mRL);
      return 1;
    }
  }
}

void volch(int m)  //音量
{
  YL[6] = m;
  for (int i = 1; i <= 8; i = i + (1))
  {
    swSer.print(YL[(int)(i - 1)]);
  }
}

void play(int n)  //开始
{
  Serial.println("播报开始");
  KS[6] = n;
  for (int i = 1; i <= 8; i = i + (1))
  {
    swSer.print(KS[(int)(i - 1)]);
  }
}

 
