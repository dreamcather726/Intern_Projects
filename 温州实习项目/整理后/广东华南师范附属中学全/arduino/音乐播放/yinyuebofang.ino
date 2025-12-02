#include <SoftwareSerial.h>


SoftwareSerial mp3Serial(7, 8); // 声明软串口对象，RX接7，TX接8
SoftwareSerial zigbeeSerial(5, 6); // 声明另一个软串口对象，RX接6，TX接5
unsigned char buf[9];
char XH[] = {0X7E, 0XFF, 0X06, 0X0F, 0X00, 0X01, 0X01, 0XEF}; //mp3
char ST[] = {0X7E, 0XFF, 0X06, 0X0E, 0X00, 0X00, 0X00, 0XEF}; //暂停
char JX[] = {0X7E, 0XFF, 0X06, 0X0D, 0X00, 0X00, 0X00, 0XEF}; //继续
char NE[] = {0X7E, 0XFF, 0X06, 0X01, 0X00, 0X00, 0X00, 0XEF}; //下
char LA[] = {0X7E, 0XFF, 0X06, 0X02, 0X00, 0X00, 0X00, 0XEF}; //上
char CL[] = {0X7E, 0XFF, 0X06, 0X16, 0X00, 0X00, 0X00, 0XEF}; //关闭音乐
char YL[] = {0X7E, 0XFF, 0X06, 0X06, 0X00, 0X00, 0X14, 0XEF}; //音量调节
char JJ[] = {0X7E, 0XFF, 0X06, 0X0F, 0X00, 0X01, 0X0A, 0XEF}; //mp3
int music_max=30;//最大音量
int music_v = 20;//当前音量
int music_num = 1;

void setup() {
  Serial.begin(9600); // 初始化硬串口
  mp3Serial.begin(9600); // 初始化MP3模块的软串口
  zigbeeSerial.begin(115200); // 初始化lora模块的软串口

  mp3_volch();
}

void loop() {
  if (zigbeeSerial.available() > 0) {
    zigbeeSerial.readBytes(buf, 9);
//    for(int i = 0;i<9;i++)
//    {
//      Serial.println(buf[i]);
//    }
    if ( buf[2] == 144 && buf[3] == 144 && buf[4] == 0x1F && buf[6] == 0x01 && buf[7] == 0x01) { //播放音乐
        music_num = 1;
        mp3_display();
    }
    else if (buf[2] == 144 && buf[3] == 144 && buf[4] == 0x1F && buf[6] == 0x01 && buf[7] == 0x02) {//下一首
        music_num = music_num + 1;
        if (music_num == 10) {
            music_num = 1;
        }
        mp3_display();
    }
    else if (buf[2] == 144 && buf[3] == 144 && buf[4] == 0x1F && buf[6] == 0x01 && buf[7] == 0x03) {//上一首
        music_num = music_num - 1;
        if (music_num <= 0) {
            music_num = 9;
        }
        mp3_display();
    }
    else if (buf[2] == 144 && buf[3] == 144 && buf[4] == 0x1F && buf[6] == 0x01 && buf[7] == 0x04) {//提高音量
        music_v = music_v + 5;
        if (music_v > 30) {
            music_v = 30;
        }
        mp3_volch();
    }
    else if (buf[2] == 144 && buf[3] == 144 && buf[4] == 0x1F && buf[6] == 0x01 && buf[7] == 0x05) {//降低音量
        music_v = music_v - 5;
        if (music_v < 0) {
            music_v = 0;
        }
        mp3_volch();
    }
    else if (buf[2] == 144 && buf[3] == 144 && buf[4] == 0x1F && buf[6] == 0x01 && buf[7] == 0x06) {//暂停播放
        mp3_Stop();
    }
    else if (buf[2] == 144 && buf[3] == 144 && buf[4] == 0x1F && buf[6] == 0x01 && buf[7] == 0x07) {//继续播放
        mp3_s();
    }
    else if (buf[2] == 144 && buf[3] == 144 && buf[4] == 0x1F && buf[6] == 0x01 && buf[7] == 0x08) {//最大音量
        music_v = 30;
        mp3_volch();
    }
    else if (buf[2] == 144 && buf[3] == 144 && buf[4] == 0x1F && buf[6] == 0x01 && buf[7] == 0x09) {//最小音量
        music_v = 10;
        mp3_volch();
    }
    else if (buf[2] == 144 && buf[3] == 144 && buf[4] == 0x1F && buf[6] == 0x01 && buf[7] == 0x0A) {//中等音量
        music_v = 20;
        mp3_volch();
    }
    else if (buf[2] == 144 && buf[3] == 144 && buf[4] == 0x1F && buf[6] == 0x01 && buf[7] == 0x0B) {//关闭音乐
        mp3_over();
    }
    else if (buf[2] == 144 && buf[3] == 144 && buf[4] == 0x1F && buf[6] == 0x01 && buf[7] == 0x0C) {//播放校园简介
        mp3_intro();
    }
  }
}


void mp3_display() {
  XH[6] = music_num;
  for (int i = 1; i <= 8; i = i + (1))
  {
    mp3Serial.print(XH[(int)(i - 1)]);
  }
//  Music_name_1 = music_num / 100;
//  Music_name_2 = (music_num / 10) % 10;
//  Music_name_3 = music_num % 10;
}

void mp3_volch()  //音量
{
  YL[6] = music_v;
  if (YL[6] > music_max) {
    YL[6] = music_max;
  }
  for (int i = 1; i <= 8; i = i + (1))
  {
    mp3Serial.print(YL[(int)(i - 1)]);
  }
}

void mp3_Stop()  //暂停
{
  for (int i = 1; i <= 8; i = i + (1))
  {
    mp3Serial.print(ST[(int)(i - 1)]);
  }
}

void mp3_s()  //继续
{
  for (int i = 1; i <= 8; i = i + (1))
  {
    mp3Serial.print(JX[(int)(i - 1)]);
  }
}

void mp3_Next()  //下一首
{
  for (int i = 1; i <= 8; i = i + (1))
  {
    mp3Serial.print(NE[(int)(i - 1)]);
  }
}

void mp3_Last()  //上一首
{
  for (int i = 1; i <= 8; i = i + (1))
  {
    mp3Serial.print(LA[(int)(i - 1)]);
  }
}

void mp3_over()  //关闭音乐
{
  music_num = 0;
  for (int i = 1; i <= 8; i = i + (1))
  {
    mp3Serial.print(CL[(int)(i - 1)]);
  }
}

void mp3_intro()  //播放校园简介
{
  for (int i = 1; i <= 8; i = i + (1))                                                                            
  {
    mp3Serial.print(JJ[(int)(i - 1)]);
  }
}
