/*
 * 智能家居系统 - 灯光控制节点 (Arduino ID: 0x01)
 * 
 * 接线说明:
 * 
 * LoRa模块:
 *   LoRa TX  -> Arduino D11
 *   LoRa RX  -> Arduino D12
 *   LoRa VCC -> 3.3V
 *   LoRa GND -> GND
 * 
 * 主卧灯带 (7颗灯珠):
 *   DATA IN  -> Arduino D2
 *   VCC      -> 5V
 *   GND      -> GND
 * 
 * 次卧灯带 (7颗灯珠):
 *   DATA IN  -> Arduino D3
 *   VCC      -> 5V
 *   GND      -> GND
 * 
 * 客厅灯带1 (7颗灯珠):
 *   DATA IN  -> Arduino D4
 *   VCC      -> 5V
 *   GND      -> GND
 * 
 * 客厅灯带2 (7颗灯珠):
 *   DATA IN  -> Arduino D5
 *   VCC      -> 5V
 *   GND      -> GND
 * 
 * 客厅灯带3 (7颗灯珠):
 *   DATA IN  -> Arduino D6
 *   VCC      -> 5V
 *   GND      -> GND
 * 
 * 客厅灯带4 (13颗灯珠):
 *   DATA IN  -> Arduino D7
 *   VCC      -> 5V
 *   GND      -> GND
 * 
 * 书房灯带 (7颗灯珠):
 *   DATA IN  -> Arduino D8
 *   VCC      -> 5V
 *   GND      -> GND
 * 
 * 电源说明:
 *   Arduino供电: 7-12V DC
 *   灯带供电: 5V (建议使用外部电源，每颗灯珠约60mA)
 * 
 * 功能:
 *   - 控制7个房间的RGB灯带
 *   - 支持开关、亮度调节、色温调节
 *   - 支持呼吸灯、流水灯特效
 *   - 支持七种固定颜色设置
 */
#include <SoftwareSerial.h>
#include <Adafruit_NeoPixel.h>

const int LORA_RX_PIN = 11;
const int LORA_TX_PIN = 12;
#define LORA_BAUD_RATE 115200
SoftwareSerial loraSerial(LORA_RX_PIN, LORA_TX_PIN);

#define NODE_ID 0x01  // 灯光控制节点

// 灯光引脚定义 - 根据实际布置
const int PIN_MASTER_BEDROOM_LIGHT = 2;   // 主卧灯 - 7颗
const int PIN_BEDROOM_LIGHT = 3;          // 次卧灯 - 7颗  
const int PIN_LIVING_ROOM_LIGHT_1 = 4;    // 客厅灯1 - 7颗
const int PIN_LIVING_ROOM_LIGHT_2 = 5;    // 客厅灯2 - 7颗
const int PIN_LIVING_ROOM_LIGHT_3 = 6;    // 客厅灯3 - 7颗
const int PIN_LIVING_ROOM_LIGHT_4 = 7;    // 客厅灯4 - 13颗
const int PIN_STUDY_LIGHT = 8;            // 书房灯 - 7颗

// 灯珠数量定义
#define NUM_PIXELS_SMALL 7     // 7颗灯珠的灯带
#define NUM_PIXELS_LARGE 13    // 13颗灯珠的灯带

// 灯光效果状态
enum LightEffect {
  EFFECT_NONE,
  EFFECT_BREATHING,
  EFFECT_WATER_FLOW
};

// 七色数组 - 彩虹色系
const uint32_t RAINBOW_COLORS[] = {
  Adafruit_NeoPixel::Color(255, 0, 0),     // 红
  Adafruit_NeoPixel::Color(255, 165, 0),   // 橙  
  Adafruit_NeoPixel::Color(255, 255, 0),   // 黄
  Adafruit_NeoPixel::Color(0, 255, 0),     // 绿
  Adafruit_NeoPixel::Color(0, 255, 255),   // 青
  Adafruit_NeoPixel::Color(0, 0, 255),     // 蓝
  Adafruit_NeoPixel::Color(128, 0, 128)    // 紫
};
const int NUM_RAINBOW_COLORS = 7;

// Gamma校正表 - 改善颜色线性度
const uint8_t PROGMEM gamma8[] = {
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,
    1,  1,  1,  1,  1,  1,  1,  1,  1,  2,  2,  2,  2,  2,  2,  2,
    2,  3,  3,  3,  3,  3,  3,  3,  4,  4,  4,  4,  4,  5,  5,  5,
    5,  6,  6,  6,  6,  7,  7,  7,  7,  8,  8,  8,  9,  9,  9, 10,
   10, 10, 11, 11, 11, 12, 12, 13, 13, 13, 14, 14, 15, 15, 16, 16,
   17, 17, 18, 18, 19, 19, 20, 20, 21, 21, 22, 22, 23, 24, 24, 25,
   25, 26, 27, 27, 28, 29, 29, 30, 31, 32, 32, 33, 34, 35, 35, 36,
   37, 38, 39, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 50,
   51, 52, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 66, 67, 68,
   69, 70, 72, 73, 74, 75, 77, 78, 79, 81, 82, 83, 85, 86, 87, 89,
   90, 92, 93, 95, 96, 98, 99,101,102,104,105,107,109,110,112,114,
  115,117,119,120,122,124,126,127,129,131,133,135,137,138,140,142,
  144,146,148,150,152,154,156,158,160,162,164,167,169,171,173,175,
  177,180,182,184,186,189,191,193,196,198,200,203,205,208,210,213,
  215,218,220,223,225,228,231,233,236,239,241,244,247,249,252,255
};

struct Light {
  Adafruit_NeoPixel strip;
  bool isOn;
  uint8_t brightness;
  uint8_t colorTemp;
  uint32_t solidColor;
  LightEffect effect;
  unsigned long lastEffectUpdate;
  int breathDirection;
  int waterFlowPosition;
  const char* name;
  int currentRainbowColor;  // 新增：当前彩虹色索引
  unsigned long lastColorChange;  // 新增：上次颜色变化时间
};

Light lights[] = {
  // 主卧灯 - 7颗
  { Adafruit_NeoPixel(NUM_PIXELS_SMALL, PIN_MASTER_BEDROOM_LIGHT, NEO_GRB + NEO_KHZ800), 
    false, 100, 50, 0, EFFECT_NONE, 0, 1, 0, "主卧灯", 0, 0 },
  
  // 次卧灯 - 7颗
  { Adafruit_NeoPixel(NUM_PIXELS_SMALL, PIN_BEDROOM_LIGHT, NEO_GRB + NEO_KHZ800), 
    false, 100, 50, 0, EFFECT_NONE, 0, 1, 0, "次卧灯", 0, 0 },
  
  // 客厅灯1 - 7颗
  { Adafruit_NeoPixel(NUM_PIXELS_SMALL, PIN_LIVING_ROOM_LIGHT_1, NEO_GRB + NEO_KHZ800), 
    false, 100, 50, 0, EFFECT_NONE, 0, 1, 0, "客厅灯1", 0, 0 },
  
  // 客厅灯2 - 7颗
  { Adafruit_NeoPixel(NUM_PIXELS_SMALL, PIN_LIVING_ROOM_LIGHT_2, NEO_GRB + NEO_KHZ800), 
    false, 100, 50, 0, EFFECT_NONE, 0, 1, 0, "客厅灯2", 0, 0 },
  
  // 客厅灯3 - 7颗
  { Adafruit_NeoPixel(NUM_PIXELS_SMALL, PIN_LIVING_ROOM_LIGHT_3, NEO_GRB + NEO_KHZ800), 
    false, 100, 50, 0, EFFECT_NONE, 0, 1, 0, "客厅灯3", 0, 0 },
  
  // 客厅灯4 - 13颗
  { Adafruit_NeoPixel(NUM_PIXELS_LARGE, PIN_LIVING_ROOM_LIGHT_4, NEO_GRB + NEO_KHZ800), 
    false, 100, 50, 0, EFFECT_NONE, 0, 1, 0, "客厅灯4", 0, 0 },
  
  // 书房灯 - 7颗
  { Adafruit_NeoPixel(NUM_PIXELS_SMALL, PIN_STUDY_LIGHT, NEO_GRB + NEO_KHZ800), 
    false, 100, 50, 0, EFFECT_NONE, 0, 1, 0, "书房灯", 0, 0 }
};

const int NUM_LIGHTS = sizeof(lights) / sizeof(lights[0]);

// 颜色定义
const uint32_t COLOR_RED = Adafruit_NeoPixel::Color(255, 0, 0);
const uint32_t COLOR_ORANGE = Adafruit_NeoPixel::Color(255, 165, 0);
const uint32_t COLOR_YELLOW = Adafruit_NeoPixel::Color(255, 255, 0);
const uint32_t COLOR_GREEN = Adafruit_NeoPixel::Color(0, 255, 0);
const uint32_t COLOR_CYAN = Adafruit_NeoPixel::Color(0, 255, 255);
const uint32_t COLOR_BLUE = Adafruit_NeoPixel::Color(0, 0, 255);
const uint32_t COLOR_PURPLE = Adafruit_NeoPixel::Color(128, 0, 128);

// 全局特效控制
bool global_breathing_effect = false;
bool global_water_flow_effect = false;
uint32_t global_solid_color = 0;

void setup() {
  Serial.begin(115200);
  loraSerial.begin(LORA_BAUD_RATE);
  Serial.println(F("Light Control Node Booting... (ID: 0x01)"));

  // 初始化所有灯带
  for (int i = 0; i < NUM_LIGHTS; i++) {
    lights[i].strip.begin();
    lights[i].strip.clear();
    lights[i].strip.show();
    Serial.print("Initialized: ");
    Serial.println(lights[i].name);
  }
  
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
        
        // 只处理灯光相关指令(01)和所有设备指令(05)
        if (device_type == 0x01 || device_type == 0x05) {
          processLightCommand(device_type, action);
        }
      }
    }
  }
  
  // 处理灯光效果
  handleLightEffects();
  delay(10);
}

void processLightCommand(byte device_type, byte action) {
  Serial.print("Light Command - Action: 0x");
  Serial.println(action, HEX);
  
  switch (action) {
    // 单个灯光控制
    case 0x01: // 打开主卧灯光 或 打开所有设备
      if (device_type == 0x01) {
        controlSingleLight(0, true);  // 单个设备指令：打开主卧灯
      } else if (device_type == 0x05) {
        controlAllLights(true);       // 所有设备指令：打开所有灯
      }
      break;
    
    case 0x02: // 关闭主卧灯光 或 关闭所有设备  
      if (device_type == 0x01) {
        controlSingleLight(0, false); // 单个设备指令：关闭主卧灯
      } else if (device_type == 0x05) {
        controlAllLights(false);      // 所有设备指令：关闭所有灯
      }
      break;
    case 0x03: controlSingleLight(1, true); break;   // 打开次卧灯光
    case 0x04: controlSingleLight(1, false); break;  // 关闭次卧灯光
    
    // 客厅灯光控制 - 同时控制4条灯带
    case 0x05: controlLivingRoomLights(true); break;  // 打开客厅灯光
    case 0x06: controlLivingRoomLights(false); break; // 关闭客厅灯光
    
    // 书房灯光控制
    case 0x09: controlSingleLight(6, true); break;   // 打开书房灯光
    case 0x0A: controlSingleLight(6, false); break;  // 关闭书房灯光
    
    // 所有灯光控制
    case 0x0D: controlAllLights(true); break;        // 打开所有灯光
    case 0x0E: controlAllLights(false); break;       // 关闭所有灯光
    
    // 全局特效和颜色控制 (自动开启所有灯光)
    case 0x0F: adjustAllColorTemp(-10); break;       // 调暖一些
    case 0x11: adjustAllColorTemp(10); break;        // 调冷一些
    case 0x12: adjustAllBrightness(10); break;       // 亮度调亮
    case 0x13: adjustAllBrightness(-10); break;      // 亮度调暗
    case 0x14: setGlobalEffect(EFFECT_BREATHING); break; // 打开呼吸灯(自动开灯)
    case 0x15: setGlobalEffect(EFFECT_WATER_FLOW); break; // 打开流水灯(自动开灯)
    case 0x16: setGlobalSolidColor(COLOR_RED); break;    // 设置为红色(自动开灯)
    case 0x17: setGlobalSolidColor(COLOR_ORANGE); break; // 设置为橙色(自动开灯)
    case 0x18: setGlobalSolidColor(COLOR_YELLOW); break; // 设置为黄色(自动开灯)
    case 0x19: setGlobalSolidColor(COLOR_GREEN); break;  // 设置为绿色(自动开灯)
    case 0x1A: setGlobalSolidColor(COLOR_CYAN); break;   // 设置为青色(自动开灯)
    case 0x1B: setGlobalSolidColor(COLOR_BLUE); break;   // 设置为蓝色(自动开灯)
    case 0x1C: setGlobalSolidColor(COLOR_PURPLE); break; // 设置为紫色(自动开灯)
  }
}

// 客厅灯光控制函数 - 同时控制4条灯带
void controlLivingRoomLights(bool turnOn) {
  // 客厅灯带索引：2,3,4,5 (客厅灯1、2、3、4)
  for (int i = 2; i <= 5; i++) {
    lights[i].isOn = turnOn;
    if (turnOn) {
      // 如果全局特效开启，应用特效
      if (global_breathing_effect) {
        lights[i].effect = EFFECT_BREATHING;
        lights[i].breathDirection = 1;
        lights[i].currentRainbowColor = 0;
        lights[i].lastColorChange = millis();
      } else if (global_water_flow_effect) {
        lights[i].effect = EFFECT_WATER_FLOW;
        lights[i].waterFlowPosition = 0;
      } else if (global_solid_color != 0) {
        lights[i].solidColor = global_solid_color;
        lights[i].effect = EFFECT_NONE;
        applyLightState(i);
      } else {
        applyLightState(i);
      }
    } else {
      lights[i].strip.clear();
      lights[i].strip.show();
      lights[i].effect = EFFECT_NONE;
      lights[i].solidColor = 0;
      lights[i].currentRainbowColor = 0;
    }
  }
  Serial.println(turnOn ? "ALL LIVING ROOM LIGHTS ON" : "ALL LIVING ROOM LIGHTS OFF");
}

// 单个灯光控制函数
void controlSingleLight(int index, bool turnOn) {
  lights[index].isOn = turnOn;
  if (turnOn) {
    // 如果全局特效开启，应用特效
    if (global_breathing_effect) {
      lights[index].effect = EFFECT_BREATHING;
      lights[index].breathDirection = 1;
      lights[index].currentRainbowColor = 0;
      lights[index].lastColorChange = millis();
    } else if (global_water_flow_effect) {
      lights[index].effect = EFFECT_WATER_FLOW;
      lights[index].waterFlowPosition = 0;
    } else if (global_solid_color != 0) {
      lights[index].solidColor = global_solid_color;
      lights[index].effect = EFFECT_NONE;
      applyLightState(index);
    } else {
      applyLightState(index);
    }
  } else {
    lights[index].strip.clear();
    lights[index].strip.show();
    lights[index].effect = EFFECT_NONE;
    lights[index].solidColor = 0;
    lights[index].currentRainbowColor = 0;
  }
  Serial.print(lights[index].isOn ? "ON" : "OFF");
  Serial.print(" - ");
  Serial.println(lights[index].name);
}

// 所有灯光控制函数
void controlAllLights(bool turnOn) {
  for (int i = 0; i < NUM_LIGHTS; i++) {
    lights[i].isOn = turnOn;
    if (turnOn) {
      // 如果之前有特效，清除特效并设置为白灯
      if (lights[i].effect != EFFECT_NONE) {
        lights[i].effect = EFFECT_NONE;
        lights[i].solidColor = 0;  // 清除固定颜色
        lights[i].currentRainbowColor = 0;  // 重置彩虹色索引
        // 设置为默认白光
        applyLightState(i);
        Serial.print("Effect cleared for ");
        Serial.println(lights[i].name);
      } else {
        applyLightState(i);
      }
    } else {
      lights[i].strip.clear();
      lights[i].strip.show();
      lights[i].effect = EFFECT_NONE;
      lights[i].solidColor = 0;
      lights[i].currentRainbowColor = 0;
    }
  }
  Serial.println(turnOn ? "ALL LIGHTS ON (Effects cleared to white)" : "ALL LIGHTS OFF");
}

// 应用Gamma校正的函数
uint32_t applyGamma(uint32_t color) {
  uint8_t r = (color >> 16) & 0xFF;
  uint8_t g = (color >> 8) & 0xFF;
  uint8_t b = color & 0xFF;
  
  r = pgm_read_byte(&gamma8[r]);
  g = pgm_read_byte(&gamma8[g]);
  b = pgm_read_byte(&gamma8[b]);
  
  return Adafruit_NeoPixel::Color(r, g, b);
}

// 改进的色温转换函数
uint32_t colorTempToColor(uint8_t temp) {
  temp = constrain(temp, 10, 90);
  
  byte red   = map(temp, 0, 100, 255, 180);
  byte green = map(temp, 0, 100, 180, 255);
  byte blue  = map(temp, 0, 100, 100, 255);
  
  red = pgm_read_byte(&gamma8[red]);
  green = pgm_read_byte(&gamma8[green]);
  blue = pgm_read_byte(&gamma8[blue]);
  
  return Adafruit_NeoPixel::Color(red, green, blue);
}

void applyLightState(int index) {
  if (lights[index].effect == EFFECT_NONE) {
    // 限制最大亮度，避免颜色失真
    uint8_t safeBrightness = constrain(lights[index].brightness, 0, 80);
    
    if (lights[index].solidColor != 0) {
      uint32_t color = applyGamma(lights[index].solidColor);
      lights[index].strip.fill(color);
    } else {
      uint32_t color = colorTempToColor(lights[index].colorTemp);
      lights[index].strip.fill(color);
    }
    
    lights[index].strip.setBrightness(map(safeBrightness, 0, 100, 0, 255));
    lights[index].strip.show();
  }
}

// 全局控制函数 - 控制所有打开的灯
void adjustAllColorTemp(int delta) {
  // 自动开启所有灯光
  for (int i = 0; i < NUM_LIGHTS; i++) {
    if (!lights[i].isOn) {
      lights[i].isOn = true;
      lights[i].effect = EFFECT_NONE;
      lights[i].solidColor = 0;
    }
    lights[i].colorTemp = constrain(lights[i].colorTemp + delta, 0, 100);
    lights[i].solidColor = 0; // 清除固定颜色
    lights[i].effect = EFFECT_NONE; // 清除特效
    global_solid_color = 0;
    global_breathing_effect = false;
    global_water_flow_effect = false;
    applyLightState(i);
  }
  Serial.print("All Lights ColorTemp adjusted - All lights turned on automatically: ");
  Serial.println(delta);
}

void adjustAllBrightness(int delta) {
  // 自动开启所有灯光
  for (int i = 0; i < NUM_LIGHTS; i++) {
    if (!lights[i].isOn) {
      lights[i].isOn = true;
      lights[i].effect = EFFECT_NONE;
      lights[i].solidColor = 0;
    }
    
    // 限制亮度在安全范围内 (10-80)
    int newBrightness = lights[i].brightness + delta;
    lights[i].brightness = constrain(newBrightness, 10, 80);
    
    // 如果接近上限，给出警告
    if (lights[i].brightness >= 75) {
      Serial.println("Warning: Brightness near maximum to avoid color shift");
    }
    
    applyLightState(i);
  }
  Serial.print("All Lights Brightness adjusted - All lights turned on automatically: ");
  Serial.println(delta);
}

void setGlobalEffect(LightEffect effect) {
  // 清除其他全局效果
  global_solid_color = 0;
  global_breathing_effect = false;
  global_water_flow_effect = false;
  
  // 设置新的全局效果
  if (effect == EFFECT_BREATHING) {
    global_breathing_effect = true;
    // 自动开启所有灯光并设置呼吸灯效果
    for (int i = 0; i < NUM_LIGHTS; i++) {
      lights[i].isOn = true;  // 自动开启灯光
      lights[i].effect = EFFECT_BREATHING;
      lights[i].breathDirection = 1;
      lights[i].solidColor = 0;
      lights[i].currentRainbowColor = 0;  // 从红色开始
      lights[i].lastColorChange = millis();
    }
    Serial.println("Global Breathing Effect ON - All lights turned on automatically");
  } else if (effect == EFFECT_WATER_FLOW) {
    global_water_flow_effect = true;
    // 自动开启所有灯光并设置流水灯效果
    for (int i = 0; i < NUM_LIGHTS; i++) {
      lights[i].isOn = true;  // 自动开启灯光
      lights[i].effect = EFFECT_WATER_FLOW;
      lights[i].waterFlowPosition = 0;
      lights[i].solidColor = 0;
    }
    Serial.println("Global Water Flow Effect ON - All lights turned on automatically");
  }
}

void setGlobalSolidColor(uint32_t color) {
  // 清除全局特效
  global_breathing_effect = false;
  global_water_flow_effect = false;
  global_solid_color = color;
  
  // 自动开启所有灯光并设置固定颜色
  for (int i = 0; i < NUM_LIGHTS; i++) {
    lights[i].isOn = true;  // 自动开启灯光
    lights[i].solidColor = color;
    lights[i].effect = EFFECT_NONE;
    applyLightState(i);
  }
  Serial.println("Global Solid Color Set - All lights turned on automatically");
}

void handleLightEffects() {
  unsigned long currentTime = millis();
  
  for (int i = 0; i < NUM_LIGHTS; i++) {
    if (!lights[i].isOn || lights[i].effect == EFFECT_NONE) continue;
    
    // 修改这里：从50ms增加到100ms，降低频率
    if (currentTime - lights[i].lastEffectUpdate > 100) { // 改为100ms，频率减半
      lights[i].lastEffectUpdate = currentTime;
      
      switch (lights[i].effect) {
        case EFFECT_BREATHING:
          handleBreathingEffect(i);
          break;
        case EFFECT_WATER_FLOW:
          handleWaterFlowEffect(i);
          break;
      }
    }
  }
}

void handleBreathingEffect(int index) {
  unsigned long currentTime = millis();
  
  // 每3秒切换颜色
  if (currentTime - lights[index].lastColorChange >= 3000) {
    lights[index].currentRainbowColor = (lights[index].currentRainbowColor + 1) % NUM_RAINBOW_COLORS;
    lights[index].lastColorChange = currentTime;
  }
  
  // 呼吸亮度效果
  static int breathValue = 0;
  breathValue += lights[index].breathDirection * 3;
  
  if (breathValue >= 100) {
    breathValue = 100;
    lights[index].breathDirection = -1;
  } else if (breathValue <= 10) {
    breathValue = 10;
    lights[index].breathDirection = 1;
  }
  
  // 使用当前彩虹色
  uint32_t currentColor = RAINBOW_COLORS[lights[index].currentRainbowColor];
  lights[index].strip.fill(currentColor);
  lights[index].strip.setBrightness(map(breathValue, 0, 100, 0, 255));
  lights[index].strip.show();
}

void handleWaterFlowEffect(int index) {
  int numPixels = lights[index].strip.numPixels();
  
  // 清空灯带
  lights[index].strip.clear();
  
  // 为每个灯珠设置不同的彩虹色
  for (int i = 0; i < numPixels; i++) {
    int colorIndex = (lights[index].waterFlowPosition + i) % NUM_RAINBOW_COLORS;
    uint32_t pixelColor = RAINBOW_COLORS[colorIndex];
    lights[index].strip.setPixelColor(i, pixelColor);
  }
  
  lights[index].strip.setBrightness(map(lights[index].brightness, 0, 100, 0, 255));
  lights[index].strip.show();
  
  // 移动流水位置
  lights[index].waterFlowPosition = (lights[index].waterFlowPosition + 1) % NUM_RAINBOW_COLORS;
}
