#include <U8g2lib.h>
#include <Wire.h>
#include <Sentry.h>
#include <Servo.h>
#include <SoftwareSerial.h>
#include "hy1.h"
#include "hy2.h"
#include "cph.h"

U8G2_SSD1306_128X64_NONAME_1_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);
Sentry2 sentry(0x60);
volatile unsigned long oled_time;
volatile int opendeg;
volatile int closedeg;
volatile int zhaji_state;
volatile long lastDetectionTime;
volatile long interval;
Servo servo_A0;
volatile int sendflag;
int zhajikaiguan[]={0x55, 0x01, 0x00, 0x0F, 0xFF};

SoftwareSerial mySerial1(9,10);
volatile long sendtime;
volatile int count;
volatile int targetAngle;
volatile int currentAngle;

void controlZhaji(int state) {
  zhaji_state = state;
  targetAngle = ((state == 1)?opendeg:closedeg);
  currentAngle = servo_A0.read();
  while (currentAngle != targetAngle) {
    currentAngle = currentAngle + ((currentAngle < targetAngle)?1:(-1));
    servo_A0.write(currentAngle);
    delay(20);
  }
  delay(50);
}

void page1() {
  u8g2.drawXBMP(30, 15, 96, 32, hy1);
  u8g2.drawXBMP(27, 30, 96, 32, hy2);
}

void page3() {
  u8g2.drawXBMP(43, 20, 100, 32, cph);
}

void page2() {
  u8g2.setFont(u8g2_font_timR10_tf);
  u8g2.setFontPosTop();
  for (int i = (1); i <= (count); i = i + (1)) {
    if (sentry.GetValue(Sentry2::kVisionAprilTag,kLabel,i) < 10) {
      u8g2.setCursor(55,20);
      u8g2.print(String("A0000") + String(sentry.GetValue(Sentry2::kVisionAprilTag,kLabel,i)));

    } else {
      u8g2.setCursor(55,20);
      u8g2.print(String("A000") + String(sentry.GetValue(Sentry2::kVisionAprilTag,kLabel,i)));

    }
  }
}

void chepaihao() {
  u8g2.firstPage();
  do
  {
    page3();
    page2();
  }while(u8g2.nextPage());
}

void displayWelcome() {
  u8g2.firstPage();
  do
  {
    page1();
  }while(u8g2.nextPage());
}

void setup(){
  u8g2.setI2CAddress(0x3C*2);
  u8g2.begin();
  Wire.begin();

  oled_time = 0;
  opendeg = 90;
  closedeg = 0;
  zhaji_state = 0;
  lastDetectionTime = 0;
  interval = 15000;
  servo_A0.attach(A0);
  sendflag = 4;
  mySerial1.begin(115200);
  while (SENTRY_OK != sentry.begin(&Wire)) {yield();}
  sentry.VisionBegin(Sentry2::kVisionAprilTag);
  servo_A0.write(closedeg);
  delay(0);
  displayWelcome();
  for (int i = 0; i <= 4; i = i + (1)) {
    mySerial1.write(zhajikaiguan[i]);
  }
  Serial.begin(9600);
  sendtime = 0;
  count = 0;
  targetAngle = 0;
  currentAngle = 0;
  u8g2.enableUTF8Print();

}

void loop(){
  count = sentry.GetValue(Sentry2::kVisionAprilTag, kStatus);
  if (count > 0) {
    chepaihao();
    controlZhaji(1);
    lastDetectionTime = millis();
    sendflag = 1;
    zhajikaiguan[3] = 0x0A;

  }
  delay(10);
  if (zhaji_state == 1 && millis() - lastDetectionTime >= interval) {
    sendflag = 1;
    zhajikaiguan[3] = 0x0F;
    displayWelcome();
    controlZhaji(0);
    zhaji_state = 0;
    lastDetectionTime = 0;

  }
  if (millis() - sendtime >= 3000) {
    if (sendflag < 4) {
      for (int i = 0; i <= 4; i = i + (1)) {
        mySerial1.write(zhajikaiguan[i]);
      }
      sendflag = sendflag + 1;

    } else {
      zhajikaiguan[3] = 0x0F;

    }
    sendtime = millis();

  }

}