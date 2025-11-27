/**
 * @file MP3.ino
 * @author your name (you@domain.com)
 * @brief 基于Arduino的MP3模块控制
 * @version 0.1
 * @date 2023-03-20
 * 
 * @copyright Copyright (c) 2023
 * 
 */

#include <Arduino.h>
#include <SoftwareSerial.h>
SoftwareSerial mp3Serial(9, 10); // RX, TX

//char数据类型，通过打印出来的就是 hex 格式
char PLAY[] = {0X7E, 0XFF, 0X06, 0X0F, 0X00, 0X01, 0X01, 0XEF};
char volumeCmd[] = {0X7E, 0XFF, 0X06, 0X06, 0X00, 0X01, 0X00, 0XEF};// 默认音量20（0-30范围）
 
void setup() {
  // put your setup code here, to run once:
  mp3Serial.begin(9600);
  Serial.begin(9600);
  Serial.println("MP3 Module Test");
}

void loop() {
  // put your main code here, to run repeatedly:
  Serial.println("输入播放的语音编号（1-10）：");
  while(Serial.available() == 0){
    // 等待用户输入
  }
  byte voiceNum = Serial.read();
  Serial.println(voiceNum);
  Play_voice(0x01, voiceNum);
  voiceNum=0;
}
void Play_voice(byte action,byte number){  
  setVolume(20);
  delay(100);
  if(action==0x01){//播放指令  
    if(number<=0x0F){
      PLAY[6]=number;
    }
  }else if(action==0x02){//停止指令
    PLAY[6]=0xFF;
  }
  mp3Serial.write(PLAY, sizeof(PLAY));
  
}
void setVolume(byte volume) {
  // 确保音量在有效范围内（0-30）
  if (volume > 30) volume = 30;
  if (volume < 0) volume = 0;
  
  volumeCmd[6] = volume; // 设置音量值
  
  // 发送音量命令
  mp3Serial.write(volumeCmd, sizeof(volumeCmd));  
  

}