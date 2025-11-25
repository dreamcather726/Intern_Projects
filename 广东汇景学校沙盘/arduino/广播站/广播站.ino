#include <SoftwareSerial.h>
#include "Arduino.h"
#include "DFRobotDFPlayerMini.h"

volatile unsigned long interval;
int rec[]={0, 0, 0, 0, 0, 0, 0, 0, 0};

SoftwareSerial mySerial1(7,8);
DFRobotDFPlayerMini myPlayer;
SoftwareSerial mySerial(9,10);
volatile int playnumber;
volatile unsigned long play_flag;

void setup(){
  interval = 300000;
  Serial.begin(9600);
  mySerial1.begin(9600);
  myPlayer.begin(mySerial1);
  mySerial.begin(115200);
  playnumber = 0;
  play_flag = 0;
}

void loop(){
  if (playnumber < 7) {
    if (play_flag == 0) {
      myPlayer.playFolder(1, playnumber);
      play_flag = millis();

    }
    if (millis() - play_flag >= interval) {
      myPlayer.pause();

    }

  }
  if (playnumber == 7) {
    myPlayer.pause();

  }
  if (playnumber == 8) {
    if (play_flag == 0) {
      myPlayer.playFolder(1, 7);
      play_flag = millis();

    }
    if (millis() - play_flag >= interval) {
      myPlayer.pause();

    }

  }

  if (mySerial.available()) {
    delay(20);
    for (int i = 1; i <= 9; i = i + (1)) {
      rec[i-1] = mySerial.read();
    }
    Serial.flush();
    if ((rec[0] == 0xFE && rec[4] == 0x1F) && rec[6] == 0x06) {
      Serial.println(rec[7]);
      if (rec[7] == 0x01) {
        playnumber = 1;
        play_flag = 0;

      } else if (rec[7] == 0x02) {
        playnumber = 2;
        play_flag = 0;
      } else if (rec[7] == 0x03) {
        playnumber = 3;
        play_flag = 0;
      } else if (rec[7] == 0x04) {
        playnumber = 4;
        play_flag = 0;
      } else if (rec[7] == 0x05) {
        playnumber = 5;
        play_flag = 0;
      } else if (rec[7] == 0x06) {
        playnumber = 6;
        play_flag = 0;
      } else if (rec[7] == 0x08) {
        playnumber = 8;
        play_flag = 0;
      } else if (rec[7] == 0x07) {
        playnumber = 7;
      }

    }
    for (int i = 1; i <= 9; i = i + (1)) {
      rec[i-1] = 0;
    }

  }

}