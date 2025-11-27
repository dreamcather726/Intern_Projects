#include <Adafruit_NeoPixel.h>

int pixel_num = 300;
// 定义两条灯带，分别连接到引脚2和3
Adafruit_NeoPixel strip1 = Adafruit_NeoPixel(pixel_num, 4, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel strip2 = Adafruit_NeoPixel(pixel_num, 12, NEO_GRB + NEO_KHZ800);

// 使用HardwareSerial for LoRa
HardwareSerial SerialPort(2); // 使用串口2

// FE命令接收相关
byte feBuffer[9]; // 存储FE命令帧
int feBufferIndex = 0;
bool feFrameStarted = false;

int mode1 = 11;
//流水灯
int led_num = 0;
//炫彩灯
long led_time = 0;
int led_c = 0;
int color1[] = {0xB41E14, 0xFF5000, 0xFFB400, 0x3C9614, 0x00FF82, 0x1EB4B4, 0xE63C50};
//呼吸灯
int Bright = 100;
int BrightFlag = 0;

// 启动效果相关变量
int num = 1;

// 上电自启动效果相关变量
bool startupEffect = true;
int startupStep = 0;
long startupLastTime = 0;
int startupDelay = 20;
int startupCurrentLED = 0;
int startupColorIndex = 0;
int startupColors[] = {
  0xB41E14, 0xFF5000, 0xFFB400, 0x3C9614, 0x00FFFF, 0x1EB4B4, 0xE63C50,
  0xFFFFFF, 0xFF00FF, 0x00FFFF
};
int startupColorCount = 10;

// 彩虹效果相关变量
long rainbowTime = 0;
int rainbowHue = 0;
int rainbowSpeed = 5; // 彩虹变化速度

void setup(){
  // 调试串口
  Serial.begin(115200);
  
  // LoRa串口 - 使用GPIO16(RX), GPIO17(TX)
  SerialPort.begin(115200, SERIAL_8N1, 16, 17);
  
  // 初始化两条灯带
  strip1.begin();
  strip2.begin();
  
  // 初始化启动效果
  strip1.clear();
  strip2.clear();
  strip1.show();
  strip2.show();
  
  startupLastTime = millis();
  
  Serial.println("双灯带控制系统启动 - LoRa模式");
  Serial.println("等待LoRa数据...");
}

void checkResponse(String cmd) {
  if (SerialPort.available()) {
    String response = SerialPort.readString();
    Serial.print(cmd + " 响应: ");
    Serial.println(response);
  } else {
    Serial.println(cmd + " 无响应");
  }
}

void loop(){
  // 处理上电自启动效果
  if (startupEffect) {
    processStartupEffect();
    return;
  }

  // 接收LoRa数据
  receiveLoRaData();

  // 设置颜色 - 两条灯带同步
  if(mode1 >= 1 && mode1 <= 7){
    led_c = mode1 - 1;
    for (int i = 0; i < pixel_num; i++) {
      strip1.setPixelColor(i, color1[led_c]);
      strip2.setPixelColor(i, color1[led_c]);
    }
    strip1.setBrightness(100);
    strip2.setBrightness(100);
  }
  else if(mode1 == 10){//炫彩灯
    if (millis() - led_time >= 3000) {
      led_time = millis();
      led_c = led_c + 1;
      if(led_c == 7) {
        led_c = 0;
      }
    }
    for (int i = 0; i < pixel_num; i++) {
      strip1.setPixelColor(i, color1[led_c]);
      strip2.setPixelColor(i, color1[led_c]);
    }
    strip1.setBrightness(100);
    strip2.setBrightness(100);
  }
  
  // 设置数量
  else if(mode1 == 11){
    start1();
  }
  
  // 改进的流水灯效果 - 两条灯带同步流动
  else if(mode1 == 9){
    strip1.clear();
    strip2.clear();
    led_num++;
    if(led_num >= pixel_num/2-6){
      led_num = 0;
      // 流水灯颜色渐变
      led_c = (led_c + 1) % 7;
    }
    
    // 创建流动效果，使用多个LED
    for(int i = 0; i < 6; i++) { // 6个LED一组
      int pos1 = (led_num + i) % (pixel_num/2);
      int pos2 = pos1 + pixel_num/2;
      
      // 计算亮度衰减
      int brightness = 255 - (i * 40);
      if (brightness < 50) brightness = 50;
      
      uint32_t baseColor = color1[led_c];
      uint32_t fadeColor = fadeColorBrightness(baseColor, brightness);
      
      // 两条灯带同步设置
      strip1.setPixelColor(pos1, fadeColor);
      strip1.setPixelColor(pos2, fadeColor);
      strip2.setPixelColor(pos1, fadeColor);
      strip2.setPixelColor(pos2, fadeColor);
    }
    strip1.setBrightness(100);
    strip2.setBrightness(100);
    delay(15); // 加快流动速度
  }
  
  // 改进的呼吸灯效果 - 两条灯带同步呼吸
  else if(mode1 == 8){
    if(BrightFlag == 0 && Bright <= 10){
      BrightFlag = 1;
    }
    else if(BrightFlag == 1 && Bright >= 200){
      BrightFlag = 0;
    }

    if(BrightFlag == 0){
      Bright = Bright - 2;
    }
    else if(BrightFlag == 1){
      Bright = Bright + 2;
    }
    
    // 呼吸灯也可以使用彩虹颜色
    uint32_t breathColor = color1[led_c];
    if (millis() - rainbowTime > 5000) { // 每5秒换一次颜色
      rainbowTime = millis();
      led_c = (led_c + 1) % 7;
    }
    
    strip1.setBrightness(Bright);
    strip2.setBrightness(Bright);
    for (int i = 0; i < pixel_num; i++) {
      strip1.setPixelColor(i, breathColor);
      strip2.setPixelColor(i, breathColor);
    }
  }
  
  // 新增彩虹效果 - 两条灯带同步彩虹
  else if(mode1 == 12){
    rainbowEffect();
    strip1.setBrightness(150);
    strip2.setBrightness(150);
  }
  
  // 关闭所有灯带
  else if(mode1 == 0x0F) {
    strip1.setBrightness(0);
    strip2.setBrightness(0);
  }
  
  // 同时更新两条灯带
  strip1.show();
  strip2.show();
}

// LoRa数据接收函数
void receiveLoRaData() {
  while (SerialPort.available()) {
    byte inByte = SerialPort.read();
    
    if (inByte == 0xFE) {
      // 开始新的FE帧
      feFrameStarted = true;
      feBufferIndex = 0;
      feBuffer[feBufferIndex++] = inByte;
    } else if (feFrameStarted && feBufferIndex < 9) {
      // 收集后续字节
      feBuffer[feBufferIndex++] = inByte;
      
      if (feBufferIndex == 9) {
        // 检查帧结束是否为0xFF
        if (feBuffer[8] == 0xFF && feBuffer[6] == 0x02) {
          // 帧完整且有效，处理命令
          Serial.print("收到完整FE命令帧: ");
          for (int i = 0; i < 9; i++) {
            if (feBuffer[i] < 16) Serial.print("0");
            Serial.print(feBuffer[i], HEX);
            Serial.print(" ");
          }
          Serial.println();
          if(feBuffer[5]!=0x07){
            // 提取命令字节 (第8个字节，索引7)
          int commandValue = feBuffer[7];
          executeLEDCommand(commandValue);
          }
          
          
          // 执行命令
          
          
          // 重置
          feFrameStarted = false;
          feBufferIndex = 0;
        } else {
          // 帧无效，重置
          feFrameStarted = false;
          feBufferIndex = 0;
          Serial.println("FE命令帧结束符错误");
        }
      }
    }
    // 忽略其他字节
  }
}

// 上电自启动效果 - 两条灯带同步
void processStartupEffect() {
  unsigned long currentTime = millis();
  
  if (currentTime - startupLastTime >= startupDelay) {
    startupLastTime = currentTime;
    
    switch (startupStep) {
      case 0:
        if (startupCurrentLED < pixel_num) {
          // 两条灯带同步设置
          strip1.setPixelColor(startupCurrentLED, startupColors[startupColorIndex]);
          strip2.setPixelColor(startupCurrentLED, startupColors[startupColorIndex]);
          if (startupCurrentLED % 10 == 0) {
            startupColorIndex = (startupColorIndex + 1) % startupColorCount;
          }
          startupCurrentLED++;
        } else {
          startupStep = 1;
          startupLastTime = currentTime;
          startupDelay = 2000;
        }
        break;
        
      case 1:
        startupStep = 2;
        startupLastTime = currentTime;
        startupDelay = 50;
        break;
        
      case 2:
        for (int i = 0; i < pixel_num; i++) {
          int colorIndex = (i + startupCurrentLED) % startupColorCount;
          // 两条灯带同步设置
          strip1.setPixelColor(i, startupColors[colorIndex]);
          strip2.setPixelColor(i, startupColors[colorIndex]);
        }
        startupCurrentLED = (startupCurrentLED + 1) % startupColorCount;
        startupStep = 3;
        startupLastTime = currentTime;
        startupDelay = 3000;
        break;
        
      case 3:
        startupEffect = false;
        mode1 = 10;
        Serial.println("启动完成，进入炫彩灯模式");
        break;
    }
    // 同时更新两条灯带
    strip1.show();
    strip2.show();
  }
}

// 彩虹效果函数 - 两条灯带同步彩虹
void rainbowEffect() {
  for(int i=0; i<pixel_num; i++) {
    // 计算每个LED的色相，形成彩虹渐变
    int hue = (rainbowHue + (i * 65536L / pixel_num)) % 65536;
    uint32_t color = strip1.ColorHSV(hue, 255, 255);
    // 两条灯带同步设置
    strip1.setPixelColor(i, color);
    strip2.setPixelColor(i, color);
  }
  rainbowHue += rainbowSpeed * 256;
  if (rainbowHue >= 65536) rainbowHue = 0;
}

// 颜色亮度衰减函数
uint32_t fadeColorBrightness(uint32_t color, int brightness) {
  uint8_t r = (color >> 16) & 0xFF;
  uint8_t g = (color >> 8) & 0xFF;
  uint8_t b = color & 0xFF;
  
  r = (r * brightness) / 255;
  g = (g * brightness) / 255;
  b = (b * brightness) / 255;
  
  return strip1.Color(r, g, b);
}

// 执行LED命令
void executeLEDCommand(int commandValue) {
  Serial.print("解析的命令值: ");
  Serial.println(commandValue);
  
  // 执行灯光控制命令
  if (commandValue >= 1 && commandValue <= 7 || commandValue == 8 || commandValue == 9 || commandValue == 10 || commandValue == 0x0F) {
    mode1 = commandValue;
    Serial.print("设置灯光模式为: ");
    Serial.println(mode1);
    
    // 重置相关变量
    if (commandValue == 8) { // 呼吸灯
      Bright = 100;
      BrightFlag = 0;
      rainbowTime = millis();
      led_c = 0;
    } else if (commandValue == 9) { // 流水灯
      led_num = 0;
      led_c = 0;
    } else if (commandValue == 10) { // 炫彩灯
      led_c = 0;
      led_time = millis();
    } else if (commandValue == 11) { // 启动效果
      num = 1;
    } else if (commandValue == 12) { // 彩虹效果
      rainbowHue = 0;
    }
    
  } else {
    Serial.println("无效的命令值");
  }
}

// 启动效果 - 两条灯带同步
void start1(){
  strip1.clear();
  strip2.clear();
  for (int i = 0; i < num; i++) {
    strip1.setPixelColor(i, 0xB41E14);
    strip2.setPixelColor(i, 0xB41E14);
  }
  strip1.show();
  strip2.show();
  delay(25);
  num++;
  if (num >= pixel_num) {
    mode1 = 10;
  }
}