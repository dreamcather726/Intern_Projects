#include <HardwareSerial.h>
#include "Arduino.h"
#include "DFRobotDFPlayerMini.h"
#include <DHT.h>
#include <U8g2lib.h>
#include <Wire.h>

DFRobotDFPlayerMini myPlayer;
volatile long premil;
volatile long interval;
volatile int temp;
volatile int humi;
volatile int uv;
volatile int light;
volatile float fengsu;
volatile int yudi;
volatile int mode1;
String rain;
String guangzhao;
String ziwaixian;
String fengxiang;
volatile int dhtflag;
volatile byte sendgz;
volatile byte sendzwx;
volatile byte sendr;
DHT dht21(21, 11);
byte bytes[]={0, 0, 0, 0};

volatile byte byte2;
volatile byte byte3;
volatile float PM;
byte rec[]={0, 0, 0, 0, 0, 0, 0, 0, 0};

byte send[]={0xFE, 0x06, 0x90, 0x90, 0x1F, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF};

U8G2_SH1106_128X64_NONAME_F_SW_I2C u8g2(U8G2_R0,  15, 5, U8X8_PIN_NONE);

void page1() {
  u8g2.setFont(u8g2_font_timR12_tf);
  u8g2.setFontPosTop();
  u8g2.setFont(u8g2_font_wqy12_t_gb2312);
  u8g2.setFontPosTop();
  u8g2.setCursor(1,1);
  u8g2.print("温度:");
  u8g2.setCursor(32,1);
  u8g2.print(String(temp));
  u8g2.setCursor(45,1);
  u8g2.print("°");
  u8g2.setCursor(50,1);
  u8g2.print("C");
  u8g2.setCursor(60,1);
  u8g2.print("湿度:");
  u8g2.setCursor(95,1);
  u8g2.print(String(humi));
  u8g2.setCursor(110,1);
  u8g2.print("%");
  u8g2.setCursor(1,13);
  u8g2.print("PM:");
  u8g2.setCursor(20,13);
  u8g2.print(String(PM, 1));
  u8g2.setCursor(45,13);
  u8g2.print("ug/m3");
  u8g2.setCursor(1,25);
  u8g2.print("风速:");
  u8g2.setCursor(32,25);
  u8g2.print(String(fengsu, 1));
  u8g2.setCursor(55,25);
  u8g2.print("m/s");
  u8g2.setCursor(1,37);
  u8g2.print("紫外线:");
  u8g2.setCursor(40,37);
  u8g2.print(ziwaixian);
  u8g2.setCursor(60,37);
  u8g2.print("光照:");
  u8g2.setCursor(95,37);
  u8g2.print(guangzhao);
  u8g2.setCursor(1,49);
  u8g2.print("天气:");
  u8g2.setCursor(40,49);
  u8g2.print(rain);
}

void setup(){
  Serial1.begin(9600,SERIAL_8N1,3,1);
  Serial2.begin(115200,SERIAL_8N1,18,19);
  myPlayer.begin(Serial1);
  premil = 0;
  interval = 3000;
  myPlayer.volume(30);
  temp = 0;
  humi = 0;
  uv = 0;
  light = 0;
  fengsu = 0;
  yudi = 0;
  mode1 = 0;
  rain = "";
  guangzhao = "";
  ziwaixian = "";
  fengxiang = "";
  dhtflag = 0;
  sendgz = 0;
  sendzwx = 0;
  sendr = 0;
   dht21.begin();
  pinMode(4, INPUT);
  pinMode(32, INPUT);
  pinMode(35, INPUT);
  pinMode(26, INPUT);
  Serial.begin(9600,SERIAL_8N1,16,17);
  byte2 = 0;
  byte3 = 0;
  PM = 0;
  u8g2.setI2CAddress(0x3C*2);
  u8g2.begin();
  u8g2.enableUTF8Print();

}

void loop(){
  if (Serial2.available() > 0) {
    delay(20);
    for (int i = 1; i <= 9; i = i + (1)) {
      rec[(i - 1)] = Serial2.read();
    }
    Serial2.flush();
    if (rec[0] == 0xFE && rec[6] == 0x03) {
      dhtflag = rec[7];

    }
    for (int i = 1; i <= 9; i = i + (1)) {
      rec[(i - 1)] = 0;
    }

  }
  if (millis() - premil > interval) {
    premil = millis();
    send[7] = humi;
    send[8] = temp;
    send[9] = (((unsigned int)(PM * 10))&0XFF);
    send[10] = ((((unsigned int)(PM * 10))>>8)&0XFF);
    send[11] = sendgz;
    send[12] = (((unsigned int)(fengsu * 10))&0XFF);
    send[13] = sendzwx;
    send[14] = sendr;
    for (int i = 0; i <= 16; i = i + (1)) {
      Serial2.write(send[i]);
    }

  }
  temp = dht21.readTemperature();
  humi = dht21.readHumidity();
  yudi = digitalRead(4);
  uv = analogRead(32);
  light = analogRead(35);
  fengsu = ((analogRead(26) / 4095.0) * 5.0) * 27.0;
  if (light <= 400) {
    guangzhao = "充足";
    sendgz = 1;

  } else {
    guangzhao = "稀少";
    sendgz = 0;

  }
  if (uv >= 1000) {
    ziwaixian = "强";
    sendzwx = 1;

  } else {
    ziwaixian = "弱";
    sendzwx = 0;

  }
  if (yudi == 0) {
    rain = "雨";
    sendr = 1;

  } else {
    rain = "晴";
    sendr = 0;

  }
  if (Serial.available() > 0) {
    for (int i = 0; i <= 3; i = i + (1)) {
      bytes[i] = Serial.read();
    }

  }
  byte2 = bytes[1];
  byte3 = bytes[2];
  PM = (byte2 * 128 + byte3) * 0.4;
  if (dhtflag == 1 || dhtflag == 5) {
    myPlayer.playFolder(1, 16);
    delay(1800);
    if (humi <= 10) {
      myPlayer.playFolder(1, humi);
      delay(650);

    } else if (humi > 10) {
      myPlayer.playFolder(1, (humi / 10));
      delay(650);
      myPlayer.playFolder(1, 10);
      delay(650);
      myPlayer.playFolder(1, ((long) (humi) % (long) (10)));
      delay(650);
    }
    if (dhtflag != 5) {
      dhtflag = 0;

    }

  }
  // 湿度
  if (dhtflag == 2 || dhtflag == 5) {
    myPlayer.playFolder(1, 14);
    delay(1500);
    if (temp <= 10) {
      myPlayer.playFolder(1, temp);
      delay(650);

    } else if (temp > 10) {
      myPlayer.playFolder(1, (temp / 10));
      delay(600);
      myPlayer.playFolder(1, 10);
      delay(650);
      myPlayer.playFolder(1, ((long) (temp) % (long) (10)));
      delay(650);
    }
    myPlayer.playFolder(1, 15);
    delay(1500);
    if (dhtflag != 5) {
      dhtflag = 0;

    }

  }
  // pm
  if (dhtflag == 3 || dhtflag == 5) {
    myPlayer.playFolder(1, 26);
    delay(2000);
    if (PM >= 1 && PM <= 10) {
      myPlayer.playFolder(1, PM);
      delay(650);
      myPlayer.playFolder(1, 12);
      delay(650);
      if ((long) ((PM * 10)) % (long) (10) == 0) {
        myPlayer.playFolder(1, 11);

      } else {
        myPlayer.playFolder(1, ((long) ((PM * 10)) % (long) (10)));

      }
      delay(650);

    } else if (PM < 1) {
      myPlayer.playFolder(1, 11);
      delay(650);
      myPlayer.playFolder(1, 12);
      delay(650);
      if ((long) ((PM * 10)) % (long) (10) == 0) {
        myPlayer.playFolder(1, 11);

      } else {
        myPlayer.playFolder(1, ((long) ((PM * 10)) % (long) (10)));

      }
      delay(650);
    } else if (PM > 10) {
      myPlayer.playFolder(1, (PM / 10));
      delay(650);
      myPlayer.playFolder(1, 10);
      delay(650);
      myPlayer.playFolder(1, ((long) (PM) % (long) (10)));
      delay(650);
      myPlayer.playFolder(1, 12);
      delay(650);
      if ((long) ((PM * 10)) % (long) (10) == 0) {
        myPlayer.playFolder(1, 11);

      } else {
        myPlayer.playFolder(1, ((long) ((PM * 10)) % (long) (10)));

      }
      delay(650);
    }
    myPlayer.playFolder(1, 27);
    delay(2000);
    if (dhtflag != 5) {
      dhtflag = 0;

    }

  }
  // 湿度
  if (dhtflag == 6 || dhtflag == 5) {
    myPlayer.playFolder(1, 21);
    delay(2000);
    if (fengsu < 1) {
      myPlayer.playFolder(1, 11);
      delay(650);
      myPlayer.playFolder(1, 12);
      delay(650);
      if ((long) ((fengsu * 10)) % (long) (10) == 0) {
        myPlayer.playFolder(1, 11);

      } else {
        myPlayer.playFolder(1, ((long) ((fengsu * 10)) % (long) (10)));

      }
      delay(650);

    } else if (fengsu >= 1 && fengsu <= 10) {
      myPlayer.playFolder(1, fengsu);
      delay(650);
      myPlayer.playFolder(1, 12);
      delay(650);
      if ((long) ((fengsu * 10)) % (long) (10) == 0) {
        myPlayer.playFolder(1, 11);

      } else {
        myPlayer.playFolder(1, ((long) ((fengsu * 10)) % (long) (10)));

      }
      delay(650);
    } else if (fengsu > 10) {
      myPlayer.playFolder(1, (fengsu / 10));
      delay(650);
      myPlayer.playFolder(1, 10);
      delay(650);
      myPlayer.playFolder(1, ((long) (fengsu) % (long) (10)));
      delay(650);
      myPlayer.playFolder(1, 12);
      delay(650);
      if ((long) ((fengsu * 10)) % (long) (10) == 0) {
        myPlayer.playFolder(1, 11);

      } else {
        myPlayer.playFolder(1, ((long) ((fengsu * 10)) % (long) (10)));

      }
      delay(650);
    }
    myPlayer.playFolder(1, 22);
    delay(2000);
    if (dhtflag != 5) {
      dhtflag = 0;

    }

  }
  // 湿度
  if (dhtflag == 7 || dhtflag == 5) {
    if (ziwaixian == "强") {
      myPlayer.playFolder(1, 19);
      delay(2000);

    } else if (ziwaixian == "弱") {
      myPlayer.playFolder(1, 20);
      delay(2500);
    }
    if (dhtflag != 5) {
      dhtflag = 0;

    }

  }
  // 湿度
  if (dhtflag == 8 || dhtflag == 5) {
    if (guangzhao == "充足") {
      myPlayer.playFolder(1, 17);
      delay(2000);

    } else if (guangzhao == "稀少") {
      myPlayer.playFolder(1, 18);
      delay(2000);
    }
    if (dhtflag != 5) {
      dhtflag = 0;

    }

  }
  // 湿度
  if (dhtflag == 9 || dhtflag == 5) {
    if (rain == "晴") {
      myPlayer.playFolder(1, 23);
      delay(2000);

    } else if (rain == "雨") {
      myPlayer.playFolder(1, 24);
      delay(2000);
    }
    dhtflag = 0;

  }

  u8g2.firstPage();
  do
  {
    page1();
  }while(u8g2.nextPage());

}