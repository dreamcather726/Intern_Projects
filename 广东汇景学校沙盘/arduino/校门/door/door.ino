#include <SoftwareSerial.h>


volatile int speed;
volatile int closesp;
volatile unsigned long closetime;
volatile unsigned long opentime;
volatile unsigned long item;
volatile unsigned long StartTime;
volatile boolean motorRunning;
volatile int motorAction;
volatile int open_flag;
int send[]={0xFE, 0x06, 0x90, 0x90, 0x1F, 0x07, 0x00, 0x00, 0xFF};

int rec[]={0, 0, 0, 0, 0, 0, 0, 0, 0};

SoftwareSerial mySerial(9,10);


void setMotor8833(int speedpin, int dirpin, int speed) {
  if (speed == 0) {
    digitalWrite(dirpin, LOW);
    analogWrite(speedpin, 0);
  } else if (speed > 0) {
    digitalWrite(dirpin, LOW);
    analogWrite(speedpin, speed);
  } else {
    digitalWrite(dirpin, HIGH);
    analogWrite(speedpin, 255 + speed);
  }
}



void setup(){
  speed = -120;
  closesp = 120;
  closetime = 60000;
  opentime = 3000;
  item = 0;
  pinMode(11, OUTPUT);
  pinMode(12, OUTPUT);
  digitalWrite(11, LOW);
  digitalWrite(12, LOW);
  StartTime = millis();
  motorRunning = true;
  motorAction = 2;
  open_flag = 0;
  setMotor8833(11, 12, closesp);
  Serial.begin(9600);
  mySerial.begin(115200);
   

}

void loop(){
  send[7] = motorAction;

  if (motorRunning) {
    if (millis() - StartTime >= opentime) {
      setMotor8833(11, 12, 0);
      motorRunning = false;
      if (open_flag == 1 && motorAction == 1) {
        item = millis();

      }

    }

  }
  if (mySerial.available() > 0) {
    delay(20);
    for (int i = 1; i <= 9; i = i + (1)) {
      rec[i-1] = mySerial.read();
    }
    Serial.flush();
    if ((rec[0] == 0xFE && rec[4] == 0x1F) && rec[6] == 0x07) {
      if (rec[7] == 0x01 && !motorRunning) {
        setMotor8833(11, 12, speed);
        StartTime = millis();
        motorRunning = true;
        motorAction = 1;
        open_flag = 1;

      } else if (rec[7] == 0x02) {
        setMotor8833(11, 12, closesp);
        StartTime = millis();
        motorRunning = true;
        motorAction = 2;
        open_flag = 0;
      }

    }
    for (int i = 1; i <= 9; i = i + (1)) {
      rec[i-1] = 0;
    }

  }
  if (open_flag == 1 && !motorRunning) {
    if (millis() - item >= closetime) {
      setMotor8833(11, 12, closesp);
      StartTime = millis();
      motorRunning = true;
      motorAction = 2;
      open_flag = 0;

    }

  }

}