#include <Adafruit_NeoPixel.h>
#include <SoftwareSerial.h>

Adafruit_NeoPixel rgb_display_4 = Adafruit_NeoPixel(100,4,NEO_GRB + NEO_KHZ800);
int rec[]={0, 0, 0, 0, 0, 0, 0, 0, 0, 0};

SoftwareSerial mySerial(9,10);
volatile int rgb_mode;
volatile unsigned long item;
volatile int rgb_number;
volatile int rgb_color;
volatile int rgb_color_old;

void setup(){
  rgb_display_4.begin();
  rgb_display_4.setBrightness(255);
  Serial.begin(9600);
  mySerial.begin(115200);
  rgb_mode = 0;
  item = 0;
  rgb_number = 100;
  rgb_color = 7;
  rgb_color_old = 7;
}

void loop(){
  if (rgb_color != rgb_color_old) {
    switch (rgb_color) {
     case 0:
      for (int i = (1); i <= (rgb_number); i = i + (1)) {
        rgb_display_4.setPixelColor(i - 1, (((180 & 0xffffff) << 16) | ((30 & 0xffffff) << 8) | 20));
      }
      break;
     case 1:
      for (int i = (1); i <= (rgb_number); i = i + (1)) {
        rgb_display_4.setPixelColor(i - 1, (((240 & 0xffffff) << 16) | ((80 & 0xffffff) << 8) | 0));
      }
      break;
     case 2:
      for (int i = (1); i <= (rgb_number); i = i + (1)) {
        rgb_display_4.setPixelColor(i - 1, (((255 & 0xffffff) << 16) | ((180 & 0xffffff) << 8) | 0));
      }
      break;
     case 3:
      for (int i = (1); i <= (rgb_number); i = i + (1)) {
        rgb_display_4.setPixelColor(i - 1, (((60 & 0xffffff) << 16) | ((150 & 0xffffff) << 8) | 20));
      }
      break;
     case 4:
      for (int i = (1); i <= (rgb_number); i = i + (1)) {
        rgb_display_4.setPixelColor(i - 1, (((0 & 0xffffff) << 16) | ((255 & 0xffffff) << 8) | 130));
      }
      break;
     case 5:
      for (int i = (1); i <= (rgb_number); i = i + (1)) {
        rgb_display_4.setPixelColor(i - 1, (((30 & 0xffffff) << 16) | ((180 & 0xffffff) << 8) | 180));
      }
      break;
     case 6:
      for (int i = (1); i <= (rgb_number); i = i + (1)) {
        rgb_display_4.setPixelColor(i - 1, (((230 & 0xffffff) << 16) | ((60 & 0xffffff) << 8) | 80));
      }
      break;
     case 7:
      for (int i = (1); i <= (rgb_number); i = i + (1)) {
        rgb_display_4.setPixelColor(i - 1, (((0 & 0xffffff) << 16) | ((0 & 0xffffff) << 8) | 0));
      }
      break;
    }
    rgb_display_4.show();
    rgb_color_old = rgb_color;

  }

  if (mySerial.available()) {
    delay(20);
    for (int i = 1; i <= 9; i = i + (1)) {
      rec[i-1] = mySerial.read();
    }
    if ((rec[0] == 0xFE && rec[6] == 0x08) && rec[7] == 0x01 || (rec[0] == 0xFE && rec[6] == 0x09) && rec[7] == 0x09) {
      rgb_color_old = rgb_color;
      rgb_color = 0;

    }
    if ((rec[0] == 0xFE && rec[6] == 0x08) && rec[7] == 0x02 || (rec[0] == 0xFE && rec[6] == 0x09) && rec[7] == 0x0A) {
      rgb_color_old = 8;
      rgb_color = 7;

    }
    Serial.write(rec[1]);
    for (int i = 1; i <= 9; i = i + (1)) {
      rec[i-1] = 0;
    }
    mySerial.flush();

  }
  if (millis() - item >= 10000) {
    item = millis();
    if (rgb_color < 6) {
      rgb_color_old = rgb_color;
      rgb_color = rgb_color + 1;

    }
    if (rgb_color == 6) {
      rgb_color_old = rgb_color;
      rgb_color = 0;

    }
    Serial.println(rgb_color);

  }

  Serial.println(rec[7]);

}