/*
 * 接线说明：
 * ================================================
 * 传感器接线：
 * - DHT11温湿度传感器：
 *   - VCC -> 5V
 *   - GND -> GND
 *   - DATA -> 引脚3 (DHTPIN)
 * 
 * - 光照传感器：
 *   - VCC -> 5V
 *   - GND -> GND
 *   - OUT -> 引脚A1 (LIGHT_PIN)
 * 
 * - UV紫外线传感器：
 *   - VCC -> 5V
 *   - GND -> GND
 *   - OUT -> 引脚A2 (UV_PIN)
 * 
 * - TQ天气传感器：
 *   - VCC -> 5V
 *   - GND -> GND
 *   - OUT -> 引脚4 (TQ_PIN)
 * 
 * - PM2.5传感器：
 *   - VCC -> 5V
 *   - GND -> GND
 *   - TX -> 引脚7 (PM_RX)
 * 
 * - 语音识别模块：
 *   - VCC -> 5V
 *   - GND -> GND
 *   - TX -> 引脚6 (VOICE_TX)
 * 
 * - 显示屏：
 *   - VCC -> 5V
 *   - GND -> GND
 *   - TX -> Arduino的TX引脚
 *   - RX -> Arduino的RX引脚
 * ================================================
 */

#include <SoftwareSerial.h>
#include <DHT.h>
// #include <DFRobotDFPlayerMini.h>  // 移除MP3播放库
long atime=0;
// -------------------------- 串口配置 --------------------------
#define VOICE_TX 6 // 语音识别TX引脚（使用软件串口）
#define PM_RX 7 // PM2.5传感器软串口接收引


// -------------------------- 传感器引脚定义 --------------------------
#define DHTPIN 3     // DHT传感器数据引脚
#define DHTTYPE DHT11   // DHT 11  
#define LIGHT_PIN A1
#define UV_PIN A2
#define TQ_PIN 4

const long BAUD_RATE = 9600;  // 波特率

// -------------------------- 全局变量定义 --------------------------
// 创建一个软串口对象，用于语音识别和PM2.5通信
SoftwareSerial voicePmSerial(PM_RX, VOICE_TX);  // RX, TX
char PLAY[] = {0X7E, 0XFF, 0X06, 0X0F, 0X00, 0X01, 0X01, 0XEF};
// 创建DHT传感器对象
DHT dht(DHTPIN, DHTTYPE);


// 传感器数据变量
float pm25Value = 0;
float humidity = 0;
float temperature = 0;
int TQValue; // 读取TQ传感器值
String weather;

int rawUV ;
int uvLevel;
int LightValue ;  // 读取光照传感器值
String lightStatus;  // 存储光照强度状态

const float REFERENCE_VOLTAGE = 5.0;
const int ADC_MAX_VALUE = 1023;
const float LUX_COEFFICIENT = 12.5;
byte commandData;//语音识别命令
// 添加全局变量，标记是否正在播报
bool isPlaying = false;
void setup() {

  // 初始化硬件串口（用于屏幕通信）
  Serial.begin(BAUD_RATE);
  
  // 初始化软串口（用于语音识别和PM2.5通信）
  voicePmSerial.begin(BAUD_RATE);
  
  // 初始化DHT传感器
  dht.begin();
  pinMode(LIGHT_PIN, INPUT);
  pinMode(UV_PIN, INPUT);
  pinMode(TQ_PIN, INPUT);
  delay(1000);
  // 向屏幕发送初始化命令
  Serial.println("@FMODE 1,Black");  // 开启覆盖模式
  
  Serial.println("@GUIS 0");  // 切换到温度传感器界面  
  
}

void loop() {   
  // 解析语音命令
  byte text = parseVoiceCommand();
  //byte text = 6;
  delay(500);
  
  // 只有当不在播报状态时，才处理新的语音指令
  if (!isPlaying && text > 0) {
    if(text == 1)
    {
      wendu();
    }
    else if(text == 2)
    {
      shidu();
    }
    else if(text == 3)
    {
      UV();    
    }
    else if(text == 4)
    {
      light();
    }
    else if(text == 5)
    {
      TQ();
    }
    else if(text == 6)
    {
      pm25();
    }
    else if(text == 7)
    {
     wendu();
     shidu();
     UV();
     light();
     TQ();
     pm25();
    }
  }
  // 读取PM2.5数据
  readPM25(); 
  // 读取温湿度数据
  readDHT();  
  // 更新屏幕显示
  updateDisplay();  
  // 短暂延迟，避免CPU占用过高
  delay(100);
}

void readPM25() {
  const int DATA_LENGTH = 3;  // A5后需读取3个字节（2个数据+1个校验）
  static unsigned char dataBuffer[DATA_LENGTH];  // 存储A5后的3个字节
  static bool isRecording = false;  // 是否已检测到A5并开始记录
  static int recordCount = 0;       // 已记录的字节数

  while (voicePmSerial.available() > 0) {
    
    unsigned char rawData = voicePmSerial.read();

    // 检测到帧头0xA5，开启记录模式
    if (rawData == 0xA5) {
      isRecording = true;
      recordCount = 0;  // 重置计数
      continue;
    }

    // 记录A5后的3个字节
    if (isRecording && recordCount < DATA_LENGTH) {
      dataBuffer[recordCount] = rawData;
      recordCount++;
      
      // 当收集满3个字节后进行处理
      if (recordCount == DATA_LENGTH) {
        isRecording = false;  // 关闭记录模式
        
        // 提取数据
        unsigned char dataH = dataBuffer[0];
        unsigned char dataL = dataBuffer[1];
        unsigned char checkSum = dataBuffer[2];
        
        // 计算数值
        unsigned int result = dataH * 128 + dataL;
        pm25Value = result*0.1;
        pm25Value=constrain(pm25Value,0,99);
        //Serial.println(pm25Value);
        // 打印必要信息
      }
    }
  }
}   

void readDHT() {
  // 读取湿度和温度
  humidity = dht.readHumidity();
  temperature = dht.readTemperature(); // 默认摄氏度
  
  // 检查读取是否成功
  if (isnan(humidity) || isnan(temperature)) {
    // 读取失败，可以添加错误处理逻辑
    return;
  }
}

void updateDisplay() {
  // 更新温度显示
  TQValue = digitalRead(TQ_PIN);  // 读取TQ传感器值
  weather = (TQValue == 1) ? "晴" : "雨";
  
  rawUV = analogRead(UV_PIN);
  uvLevel = map(rawUV, 0, ADC_MAX_VALUE, 0, 10);
  LightValue = analogRead(LIGHT_PIN);  // 读取光照传感器值  
  //voicePmSerial.println(LightValue);
  if (LightValue > 512) {
    lightStatus = "弱";  // 大于512设为弱
  } else {
    lightStatus = "强";  // 小于等于512设为强
  }
  Serial.print("@SET 109,");
  Serial.println(temperature);

  Serial.print("@SET 110,");
  Serial.println(humidity);

  Serial.print("@SET 112,");
  Serial.println(lightStatus);

  Serial.print("@SET 113,");
  Serial.println(uvLevel);

  Serial.print("@SET 111,");
  Serial.println(weather);

  Serial.print("@SET 114,");
  Serial.println(pm25Value);
}

byte parseVoiceCommand() {
  byte returnCommand = 0; // 默认返回值
  // 检查语音识别软串口是否有数据
  if (voicePmSerial.available() > 0) {
    //voicePmSerial.print("[原始数据] ");
    // 定义缓冲区和包相关常量
    const int PACKET_SIZE = 6; // 数据包大小(例如:55 AA 02 01 00 FF)
    const int COMMAND_INDEX = 3; // 命令数据在第4个位置(索引从0开始)
    static byte packetBuffer[PACKET_SIZE]; // 数据包缓冲区
    static int bufferIndex = 0; // 当前缓冲区索引
    
    // 读取并显示所有可用数据
    while (voicePmSerial.available() > 0) {
      byte data = voicePmSerial.read(); // 读取一个字节
      
      // 以十六进制格式显示数据
      if (data < 0x10) {
        //voicePmSerial.print("0"); // 补零
      }
      //voicePmSerial.print(data, HEX);
      //voicePmSerial.print(" ");
      
      // 数据包解析逻辑
      if (bufferIndex < PACKET_SIZE) {
        packetBuffer[bufferIndex++] = data;
        
        // 检查是否收集了完整的数据包
        if (bufferIndex == PACKET_SIZE) {
          // 检查帧头是否为55 AA
          if (packetBuffer[0] == 0x55 && packetBuffer[1] == 0xAA) {
            // 解析第4个数据(索引为3)
            commandData = packetBuffer[COMMAND_INDEX];
            returnCommand = commandData; // 设置返回值为解析到的命令
            //voicePmSerial.print("[解析结果] 命令数据: 0x");
            //voicePmSerial.print("0");
            //voicePmSerial.println(commandData, HEX);
          }
          // 重置缓冲区索引，准备接收下一个数据包
          bufferIndex = 0;
        }
      }
    }
    voicePmSerial.println(); // 换行
    }  
  return returnCommand; // 返回解析到的命令
}
void bofang(int M)//播放第几首音乐的子程序
{
  PLAY[6] = M;
  for (int i = 0; i < 8; i ++)
  {
    voicePmSerial.print(PLAY[i]);
  }
}
void wendu()
{
  isPlaying = true; // 开始播报
  int temp1 = (int)temperature/10;
  int temp2 = (int)temperature%10;
  bofang(14);//现在温度
    delay(1500);
  if(temp1 != 0)
  {
    
    bofang(temp1);delay(650);
    bofang(10); delay(750);
    }
  bofang(temp2);
  delay(800);
  bofang(15);//摄氏度
  delay(1500);
  isPlaying = false; // 播报结束
}
void shidu()
{
  isPlaying = true; // 开始播报
  int temp1 = (int)humidity/10;
  int temp2 = (int)humidity%10;
  bofang(16);//现在湿度
    delay(2000); 
  if(temp1 != 0)
  {
    
    bofang(temp1);delay(650);
    bofang(10); delay(800);
  }
  bofang(temp2);
  delay(1500);
  isPlaying = false; // 播报结束
}
void TQ()
{
  isPlaying = true; // 开始播报
  if(weather == "晴")
  {
    bofang(23);//天气
  }
  else if(weather == "雨")
  {
    bofang(24);//天气
  }
  delay(2000);
  isPlaying = false; // 播报结束
}
void light()
{
  isPlaying = true; // 开始播报
  if(lightStatus == "弱")
  {
    bofang(18);//光照
  }
  else if(lightStatus == "强")
  {
    bofang(17);//光照
  }
  delay(2000);
  isPlaying = false; // 播报结束
}
void UV()
{
  isPlaying = true; // 开始播报
  if(uvLevel <= 6)
  {
    bofang(20);//UV
  }
  else
  {
    bofang(19);//UV
  }
  delay(2500);
  isPlaying = false; // 播报结束
}
void pm25()
{
  isPlaying = true; // 开始播报
  int temp1 = (int)pm25Value/10;
  int temp2 = (int)pm25Value%10; 
  bofang(26);//现在PM2.5
  delay(2000);
  if(temp1 != 0)
  {
    
    bofang(temp1);delay(650);
    bofang(10); delay(800);
  }
  bofang(temp2);
  delay(800);
  bofang(27);
  delay(1000);
  isPlaying = false; // 播报结束
}
