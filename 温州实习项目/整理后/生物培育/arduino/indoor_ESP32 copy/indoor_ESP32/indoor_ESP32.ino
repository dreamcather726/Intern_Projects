
#include <DHT.h>
#include <SoftwareSerial.h>

#define DEVICE_ID 15 // 设备ID
/*------------------------------*///Serial2 用來接收指令和發送傳感器
#define DHTPIN 18     // DHT传感器数据引脚
#define LIGHT_PIN 35 // 光照传感器引脚32
#define TQ_PIN 25 // 温度传感器引脚34
#define UV_PIN 27 // UV传感器引脚33

#define PM25_RX 26 // PM2.5传感器软串口接收引脚
#define PM_TX 23 // 发送屏幕软串口发送引脚



#define SEND_BAUD 115200 // 串口波特率
// 创建PM2.5传感器软串口对象
SoftwareSerial pmSerial(PM25_RX, PM_TX);
#define DHTTYPE DHT11   //  
const int ADC_MAX_VALUE = 1023;
float pm25Value = 0;
float humidity = 0;
float temperature = 0;
int rawUV ;
int uvLevel;
int LightValue ;  // 读取光照传感器值
int TQValue ;  // 读取温度传感器值
String lightStatus;  // 存储光照强度状态
String weather;
bool isPlaying = false;
char PLAY[] = {0X7E, 0XFF, 0X06, 0X0F, 0X00, 0X01, 0X01, 0XEF};
DHT dht(DHTPIN, DHTTYPE);
void setup() {
  // 初始化串口通信
  Serial.begin(9600);
  Serial2.begin(SEND_BAUD, SERIAL_8N1, 16, 17);
  // 初始化DHT传感器
  dht.begin();
  // 初始化光照传感器
  pinMode(LIGHT_PIN, INPUT);
  // 初始化UV传感器
  pinMode(UV_PIN, INPUT);
  
  // 等待传感器稳定
  pinMode(TQ_PIN, INPUT);
  // 初始化PM2.5传感器软串口
  pmSerial.begin(9600);
  
  pmSerial.println("@FMODE 1,Black");  // 开启覆盖模式
  
  pmSerial.println("@GUIS 1");  // 切换到温度传感器界面
  Serial.println("程序启动");
}

void loop() {
  // 定期清理串口缓冲区，防止长时间运行时的数据堆积
  static unsigned long lastClearTime = 0;
  if (millis() - lastClearTime > 5000) { // 每5秒清理一次
    clearSerialBuffer();
    lastClearTime = millis();
  }

  // 读取湿度值
  readDHT();
  // 读取PM2.5数据
  readPM25(); 
  // 读取光照数据
  readLight();
  // 读取天气数据
  readTQ();
  // 更新屏幕显示
  updatedisplay();
  
  byte command = 0; // 初始化为0
  
  byte startByte = Serial2.read();
  
  if(startByte == 0xB0)
    {
        
        byte nextByte = Serial2.read();
         
        if (nextByte == DEVICE_ID)
        {
            sendSensorData();
            clearSerialBuffer(); // 处理完数据请求后清理缓冲区
        }
    }
  
  
    
    // 接收并解析A0格式数据包
  else if (startByte == 0xA0) {
      Serial.println("检测到帧头0xA0");
      
      // 等待剩余4个字节的数据到达，设置超时
      unsigned long startTime = millis();
      while (Serial2.available() < 4 && millis() - startTime < 100) { 
        // 等待数据到达，超时100ms
      }
      
      byte buffer[4];
      int remainingBytes = Serial2.readBytes(buffer, 4); // 读取剩余的4字节数据包
      Serial.print("读取到的字节数: ");
      Serial.println(remainingBytes);
      
      // 打印接收到的每个字节的十六进制值
      Serial.print("接收到的数据: 0xA0 ");
      for (int i = 0; i < remainingBytes; i++) {
        if (buffer[i] < 0x10) Serial.print("0");
        Serial.print(buffer[i], HEX);
        Serial.print(" ");
      }
      Serial.println();
      
      if (remainingBytes == 4) {
        Serial.println("成功读取4字节数据包");
        
        // 构建完整数据包
        byte fullPacket[5] = {0xA0, buffer[0], buffer[1], buffer[2], buffer[3]};
        
        // 验证设备ID
        if (fullPacket[1] == DEVICE_ID) {
          Serial.println("设备ID匹配");
          
          // 提取数据
          byte device_id = fullPacket[1];
          byte action = fullPacket[2];
          byte value = fullPacket[3];
          byte checksum_received = fullPacket[4];
          
          // 计算校验和
          byte checksum_calculated = (device_id + action + value) & 0x0F;
          
          // 打印详细信息
          Serial.print("原始数据: 0xA0 ");
          Serial.print(device_id, HEX); Serial.print(" ");
          Serial.print(action, HEX); Serial.print(" ");
          Serial.print(value, HEX); Serial.print(" ");
          Serial.println(checksum_received, HEX);
          
          Serial.print("计算得到的校验和: 0x");
          Serial.println(checksum_calculated, HEX);
          
          // 校验和验证
          if (checksum_received == 0XFF) {
            // 校验通过
            command = fullPacket[2]; // 指令是第3个字节
            Serial.print("接收到有效指令: ");
            Serial.println(command);
            // 清空A0命令处理后的缓冲区
              while (Serial2.available() > 0) {
                Serial2.read();
              }
          } else {
            Serial.println("校验和验证失败");
          }
        } else {
          Serial.println("设备ID不匹配");
        }
      } else {
        Serial.println("未收到完整的4字节数据");
      }
    } else {
      Serial.println("未检测到帧头0xA0，忽略此字节");
    }
    
    

  if (!isPlaying && command > 0) {
      Serial.println("开始播报：");
      Serial.println(command);
      clearSerialBuffer();
      Serial.println("已清除重复指令");
    if(command == 1)
    {
      wendu();
    }
    else if(command == 2)
    {
      shidu();
    }
    else if(command == 3)
    {
      UV();    
    }
    else if(command == 4)
    {
      
     light();
      
    }
    else if(command == 5)
    {
      TQ();
    }
    else if(command == 6)
    {
      pm25();
    }
    else if(command == 7)
    {
     wendu();//
     shidu();//
     UV();//
     light();
     TQ();
     pm25();//
    }
  }
}

void readDHT(){
  // 读取湿度值
  humidity = dht.readHumidity();  
  // 读取温度值（摄氏度）
  temperature = int(dht.readTemperature());
  delay(1000);
}
void readTQ(){
  // 读取温度值（摄氏度）
  TQValue = digitalRead(TQ_PIN);
}
void readPM25() {
  const int DATA_LENGTH = 3;  // A5后需读取3个字节（2个数据+1个校验）
  static byte dataBuffer[DATA_LENGTH];  // 存储A5后的3个字节
  static bool isRecording = false;  // 是否已检测到A5并开始记录
  static int recordCount = 0;       // 已记录的字节数
  pmSerial.listen(); // 确保监听LoRa串口
  while (pmSerial.available() > 0) {
     byte rawData = pmSerial.read();

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
         byte dataH = dataBuffer[0];
         byte dataL = dataBuffer[1];
         byte checkSum = dataBuffer[2];
        
        // Serial.print("A5后3个字节: ");
        // Serial.print(dataH, HEX);
        // Serial.print(" ");
        // Serial.print(dataL, HEX);
        // Serial.print(" ");
        // Serial.println(checkSum, HEX);
        
        // 尝试多种校验方式
        byte calculatedChecksum = (0xA5 + dataH + dataL);
        bool checkPass = false;
        
        // Serial.print("计算校验和: ");
        // Serial.println(calculatedChecksum, HEX);
        
        // // 方式1: 直接和
        // if (calculatedChecksum == checkSum) {
        //   checkPass = true;
        //   Serial.println("校验方式1通过！");
        // }
        // // 方式2: 低8位
        // else if ((calculatedChecksum & 0xFF) == checkSum) {
        //   checkPass = true;
        //   Serial.println("校验方式2通过！");
        // }
        // // 方式3: 低7位
         if ((calculatedChecksum & 0x0F) == (checkSum & 0x0F)) {
          checkPass = true;
          // Serial.println("校验方式3通过！");
        }
        
        if (checkPass) {
          // 校验通过，处理数据 - 使用256进行组合和0.1的转换系数
          int result = dataH * 128 + dataL;
          pm25Value = result * 0.1;
          // Serial.print("PM2.5数据有效: ");
          // Serial.println(pm25Value);
        } else {
          //校验失败
          Serial.print("校验和错误! 计算值:");
          Serial.print(calculatedChecksum, HEX);
            Serial.print(" 接收值:");
            Serial.println(checkSum, HEX);
          }
        }
      }
    }
  }

void readLight()
{
  rawUV = analogRead(UV_PIN);
  uvLevel = map(rawUV, 0, 4096, 0, 10);
  LightValue = analogRead(LIGHT_PIN);  // 读取光照传感器值 
Serial.println(rawUV);
  if(LightValue<2000){
    lightStatus = "强";
  }else{
    lightStatus = "弱";
  }
}
// -------------------------- 发送传感器数据 --------------------------
void sendSensorData() {
  
  // 数据格式：设备码,温度,湿度,PM2.5,光照,UV（逗号分隔，便于接收端解析）
  String sendData;

  // 安全地构造数据字符串，确保所有值都已正确初始化
  sendData = String(DEVICE_ID) + ",";
  sendData += String(int(temperature)) + ",";
  sendData += String(int(humidity)) + ",";
  sendData += String(int(pm25Value)) + ",";
  sendData += String(LightValue) + ",";
  sendData += String(uvLevel)+",";  // 最后一个数据项后面不加逗号
  sendData +=String(TQValue);
  
  // 发送数据（末尾加换行符，接收端可按行读取）
  
  Serial2.println(sendData);
  clearSerialBuffer();

}
void updatedisplay(){

  pmSerial.print("@SET 104,");
  pmSerial.println(String(temperature));

  pmSerial.print("@SET 105,");
  pmSerial.println(String(humidity));

  pmSerial.print("@SET 106,");
  if(TQValue ==1){
    weather = "晴";
    pmSerial.println(weather);
  }else{
    weather = "雨";
    pmSerial.println(weather);
  }

  pmSerial.print("@SET 107,");
  if(LightValue<2000){
    
    pmSerial.println("强");
  }else{
    
    pmSerial.println("弱");
  }

  pmSerial.print("@SET 108,");
  pmSerial.println(String(uvLevel));

  pmSerial.print("@SET 109,");
  pmSerial.println(String(pm25Value));
}
void bofang(int M)//播放第几首音乐的子程序
{
  PLAY[6] = M;
  for (int i = 0; i < 8; i ++)
  {
    Serial.print(PLAY[i]);
  }
}
void wendu()
{
  isPlaying = true; // 开始播报
  int temp1 = (int)temperature/10;
  int temp2 = (int)temperature%10;
  delay(500);
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
  delay(500); 
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
  delay(500);
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
  delay(500);
  if(lightStatus == "弱")
  {
    bofang(18);//光照
  }
  else
  {
    bofang(17);//光照
  }
  delay(2000);
  isPlaying = false; // 播报结束
}
void UV()
{ delay(500);
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
{delay(500);
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
void clearSerialBuffer() {
 
  
  // 等待发送缓冲区数据发送完成
  Serial2.flush();
  
  // 短暂延时确保所有响应数据都已到达
  delay(50);
  
  // 清空接收缓冲区中可能存在的残留数据
  while (Serial2.available() > 0) {
    Serial2.read(); // 读取并丢弃所有可用字节
  }
}