#include <U8x8lib.h>  // OLED显示库
#include <Wire.h>     // I2C通信库（OLED依赖）
// OLED初始化 - 适配SSD1306 128x64屏幕，I2C默认地址0x3C
U8X8_SSD1306_128X64_NONAME_HW_I2C u8x8(U8X8_PIN_NONE);

int level_state;  // 水位状态（数字）
String level_str; // 水位状态（文本）
int counter = 0;  // 示例计数器变量

void setup() {
  
  // 初始化串口调试
  Serial.begin(9600);
  
  // 初始化OLED
  if (!u8x8.begin()) {
    Serial.println("ERROR: OLED初始化失败！");
    while (1);  // 初始化失败则停止
  }
  u8x8.setContrast(200);  // 调整OLED亮度（0-255）
  // 使用支持中文的字体
  u8x8.setFont(u8x8_font_cjk16_8r);  // 支持中日韩字符的字体
  u8x8.clearDisplay();  // 清空屏幕

}

void loop() {
  // 使用sprintf格式化（更高效）、直接显示数字
  counter++;
  if (counter > 999) counter = 0; // 重置计数器
  char numBuffer[10];
  sprintf(numBuffer, "%d", counter);
  
  // 清空屏幕
  u8x8.clearDisplay();
  
  // 显示中文内容
  u8x8.drawString(0, 1, "中文测试");  // 在第1行显示中文
  u8x8.drawString(0, 3, "计数:");     // 在第3行显示中文标签
  u8x8.drawString(4, 3, numBuffer);   // 在第3行显示计数值
  u8x8.drawString(0, 5, "水位状态:"); // 在第5行显示中文标签
  u8x8.drawString(5, 5, "正常");     // 在第5行显示中文状态
  
  delay(1000); // 每秒更新一次
}

