/*
  时间播报 Arduino  5V

  串口     接    Zigbee
  软串口   接    MP3
  引脚11   接    DIN
  引脚12   接    CS
  引脚13   接    CLK

  软串口     A2=RX  A3=TX
  MP3文件夹  05
  Zigee     05

  FE 0B 80 80 05 00 CD1 CD2 CD3 CD4 CD5 CD6 CD7 FF

  CD1  月
  CD2  日
  CD3  时
  CD4  分
  CD5  秒
  CD6  年
  CD7  播报标志

*/
#include <SoftwareSerial.h>
SoftwareSerial mySerial(A2, A3); //RX=A2,TX=A3
#include <MsTimer2.h>
unsigned char i;
unsigned char j;
unsigned char z; //选歌变量
unsigned char z2; //歌曲串口变量
int z3 = 1;
int lw = 3; //联网标志位
unsigned char;
/*Port Definitions*/
long T;
int T1;//冒号计时
int maohao;//冒号显示
int year_high = 8, year_low = 8, month_high = 8, month_low = 8, day_high = 8, day_low = 8, hour_low = 8, hour_high = 8, minute_low = 8, minute_high = 8, second_low = 8, second_high = 8; //月日时分秒 high十位   low个位  在点阵屏显示

int year_ = 0, month_ = 0, day_ = 0,  hour_ = 0, minute_ = 0, second_ = 0; //月 日 时 分 秒
#define LENG 11 // 0x55 + 15 bytes equal to 16 bytes
unsigned char buf[LENG];
int key = 0;
long timeout = 0;

int flag_time_bp = 0;


#define count 32         //级联个数
int Max7219_pinCLK = 13;
int Max7219_pinCS = 12;
int Max7219_pinDIN = 11;

char YL[] = {char(0X7E), char(0XFF), char(0X06), char(0X06), char(0X00), char(0X00), char(0X1E), char(0XEF)};
char PLAY[] = {char(0X7E), char(0XFF), char(0X06), char(0X0F), char(0X00), char(0X01), char(0X01), char(0XEF)};

unsigned char disp1[38][8] = {

  {0x00, 0x00, 0x7E, 0x7E, 0x66, 0x66, 0x66, 0x66},
  {0x66, 0x66, 0x66, 0x66, 0x7E, 0x7E, 0x00, 0x00}, /*0 1*/

  {0x00, 0x08, 0x38, 0x78, 0x18, 0x18, 0x18, 0x18},
  {0x18, 0x18, 0x18, 0x18, 0x3C, 0x3C, 0x00, 0x00}, //1  3

  {0x00, 0x00, 0x7E, 0x7E, 0x06, 0x06, 0x06, 0x7E},
  {0x7E, 0x60, 0x60, 0x60, 0x7E, 0x7E, 0x00, 0x00}, //2  5

  {0x00, 0x7E, 0x7E, 0x06, 0x06, 0x06, 0x06, 0x7E},
  {0x7E, 0x06, 0x06, 0x06, 0x7E, 0x7E, 0x00, 0x00}, //3  7

  {0x00, 0x60, 0x6C, 0x6C, 0x6C, 0x6C, 0x6C, 0x6C},
  {0x7E, 0x7E, 0x0C, 0x0C, 0x0C, 0x0C, 0x00, 0x00}, //4   9

  {0x00, 0x00, 0x7E, 0x7E, 0x60, 0x60, 0x60, 0x7E},
  {0x7E, 0x06, 0x06, 0x46, 0x7E, 0x7E, 0x00, 0x00}, /*5    11*/

  {0x00, 0x00, 0x7E, 0x7E, 0x40, 0x40, 0x40, 0x7E},
  {0x7E, 0x42, 0x42, 0x42, 0x7E, 0x7E, 0x00, 0x00}, /*"6     13*/

  {0x00, 0x00, 0x7E, 0x7E, 0x06, 0x0C, 0x1C, 0x18},
  {0x18, 0x18, 0x18, 0x18, 0x18, 0x18, 0x00, 0x00}, /*7      15*/

  {0x00, 0x00, 0x7E, 0x7E, 0x66, 0x66, 0x66, 0x7E},
  {0x7E, 0x66, 0x66, 0x66, 0x7E, 0x7E, 0x00, 0x00}, /*8     17*/

  {0x00, 0x00, 0x7E, 0x7E, 0x66, 0x66, 0x66, 0x7E},
  {0x7E, 0x06, 0x06, 0x66, 0x66, 0x7E, 0x00, 0x00}, /*9     19*/


  {0x00, 0x00, 0x00, 0x3C, 0x3C, 0x3C, 0x00, 0x00},
  {0x00, 0x3C, 0x3C, 0x3C, 0x00, 0x00, 0x00, 0x00}, /* :     21*/


  {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00},
  {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, /*"space",23*/

  {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x7E},
  {0x7E, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, /*-",25*/


  {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x7E},
  {0x7E, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}, /*"月,27*/

  {0x00, 0x00, 0x7E, 0x42, 0x42, 0x42, 0x42, 0x7E},
  {0x7E, 0x42, 0x42, 0x42, 0x42, 0x7E, 0x00, 0x00}, /*"日,29*/

};

void Write_Max7219_byte(unsigned char DATA)
{
  unsigned char i;
  digitalWrite(Max7219_pinCS, LOW);
  for (i = 8; i >= 1; i--)
  {
    digitalWrite(Max7219_pinCLK, LOW);
    digitalWrite(Max7219_pinDIN, DATA & 0x80); // Extracting a bit data
    DATA = DATA << 1;
    digitalWrite(Max7219_pinCLK, HIGH);
  }
}


void Write_Max7219(unsigned char address, unsigned char dat)
{
  digitalWrite(Max7219_pinCS, LOW);
  Write_Max7219_byte(address);           //写入地址，即数码管编号
  Write_Max7219_byte(dat);               //写入数据，即数码管显示数字
  digitalWrite(Max7219_pinCS, HIGH);
}

void Init_MAX7219(void)
{
  //     Write_Max7219(0x09, 0x00);       //译码方式：BCD码
  //     Write_Max7219(0x0a, 0x03);       //亮度
  //     Write_Max7219(0x0b, 0x07);       //扫描界限；8个数码管显示
  //     Write_Max7219(0x0c, 0x01);       //掉电模式：0，普通模式：1
  //     Write_Max7219(0x0f, 0x00);        //显示测试：1；测试结束，正常显示：0

  unsigned char  i;
  digitalWrite(Max7219_pinCS, LOW);
  for (i = 0; i < count; i++)
  {
    Write_Max7219_byte(0x09); //译码方式：BCD码
    Write_Max7219_byte(0x00);
  }
  digitalWrite(Max7219_pinCS, HIGH);
  delay(50);
  digitalWrite(Max7219_pinCS, LOW);
  for (i = 0; i < count; i++)
  {
    Write_Max7219_byte(0x0a); //亮度
    Write_Max7219_byte(0x03);
  }
  digitalWrite(Max7219_pinCS, HIGH);
  delay(50);
  digitalWrite(Max7219_pinCS, LOW);
  for (i = 0; i < count; i++)
  {
    Write_Max7219_byte(0x0b); // //扫描界限；8个数码管显示
    Write_Max7219_byte(0x07);
  }
  digitalWrite(Max7219_pinCS, HIGH);
  delay(50);
  digitalWrite(Max7219_pinCS, LOW);
  for (i = 0; i < count; i++)
  {
    Write_Max7219_byte(0x0c); //   //掉电模式：0，普通模式：1
    Write_Max7219_byte(0x01);
  }
  digitalWrite(Max7219_pinCS, HIGH);
  digitalWrite(Max7219_pinCS, LOW);
  for (i = 0; i < count; i++)
  {
    Write_Max7219_byte(0x0f); //显示测试：1；测试结束，正常显示：0
    Write_Max7219_byte(0x00);
  }
  digitalWrite(Max7219_pinCS, HIGH);
  delay(50);
}

void flash()
{
  T1++;
  // if(T1<=10)maohao=10; rang//让冒号有亮灭的效果
  //if(T1>10&&T1<=20){maohao=11;T1=0;Init_MAX7219();}//让冒号有亮灭的效果
  if (T1 > 100)
  {
    T1 = 0; Init_MAX7219();
  }//让屏幕10秒刷新一次一秒乱码
}


void setup()
{
  Serial.begin(115200);
  mySerial.begin(9600);
  pinMode(Max7219_pinCLK, OUTPUT);
  pinMode(Max7219_pinCS, OUTPUT);
  pinMode(Max7219_pinDIN, OUTPUT);
  MsTimer2::set(100, flash);        // 中断设置函数，每 100ms 进入一次中断
  MsTimer2::start();                //开始计时
  delay(20);
  volch(30); //指定音量，降低电流对系统冲击
  delay(200);


  Init_MAX7219(); delay(800);

  for (i = 1; i < 9; i++) //初始化屏幕显示00000
  {
    digitalWrite(Max7219_pinCS, LOW);
    xianshi(hour_high);   xianshi(hour_low);   xianshi(10);    xianshi(minute_high);   xianshi(minute_low);   xianshi(10);     xianshi(second_high);   xianshi(second_low);
    xianshi1(hour_high);  xianshi1(hour_low);  xianshi1(10);   xianshi1(minute_high);  xianshi1(minute_low);  xianshi1(10);    xianshi1(second_high);  xianshi1(second_low);
    xianshi(year_high);  xianshi(year_low);   xianshi(13);    xianshi(month_high);   xianshi(month_low);    xianshi(13);    xianshi(day_high);      xianshi(day_low);
    xianshi1(year_high);  xianshi1(year_low);  xianshi1(13);  xianshi1(month_high);   xianshi1(month_low);  xianshi1(13);  xianshi1(day_high);     xianshi1(day_low);
    digitalWrite(Max7219_pinCS, HIGH);
  }
  delay(10);
  maohao = 10;
}

void loop()
{
  clk_();
  //  if (lw == 1) //lw初始化的时候等=1
  //  {
  //    bofang(16);
  //    delay(3000);
  //    lw = 2;
  //  }

  //  if (Serial.find(0x0B)) {
  //    Serial.readBytes(buf, LENG);
  //    if (buf[0] == 0x80)
  //    {
  //      month_ = buf[4]; day_ = buf[5]; hour_ = buf[6]; minute_ = buf[7]; second_ = buf[8]; year_ = buf[9]; key = buf[10];
  //      timeout = millis();
  //    }
  //  }
  Read_code();
  z3 = 1;
  //  xq2 =6; xq1 =6;
  year_high = year_ / 10;        year_low = year_ % 10;
  month_high = month_ / 10;      month_low = month_ % 10;    //月  high十位   low个位
  day_high = day_ / 10;          day_low = day_ % 10;        //日
  hour_high = hour_ / 10;        hour_low = hour_ % 10;      //时
  minute_high = minute_ / 10;    minute_low = minute_ % 10;  //分
  second_high = second_ / 10;    second_low = second_ % 10;  //秒

  //  if ((year_ > 0) && (lw == 2)) //lw初始化的时候等=1
  //  {
  //    bofang(17);
  //    delay(1000);
  //    lw = 3;
  //  }

  for (i = 1; i < 9; i++)
  {
    digitalWrite(Max7219_pinCS, LOW);
    xianshi(hour_high);   xianshi(hour_low);   xianshi(10);    xianshi(minute_high);   xianshi(minute_low);   xianshi(10);     xianshi(second_high);   xianshi(second_low);
    xianshi1(hour_high);  xianshi1(hour_low);  xianshi1(10);   xianshi1(minute_high);  xianshi1(minute_low);  xianshi1(10);    xianshi1(second_high);  xianshi1(second_low);
    xianshi(year_high);  xianshi(year_low);   xianshi(13);    xianshi(month_high);   xianshi(month_low);    xianshi(13);    xianshi(day_high);      xianshi(day_low);
    xianshi1(year_high);  xianshi1(year_low);  xianshi1(13);  xianshi1(month_high);   xianshi1(month_low);  xianshi1(13);  xianshi1(day_high);     xianshi1(day_low);
    digitalWrite(Max7219_pinCS, HIGH);
  }
  zd();
  time_bp();

}

void Read_code() {
  if (Serial.available() > 0) {
    delay(20);
    int len = Serial.available();
    unsigned char buf[len];
    Serial.readBytes(buf, len);
    //{0xFE, 0x0B, 0x80, 0x80, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF}
    if(buf[0]==0xFE && buf[4] == 0x05)
    {month_ = buf[6]; day_ = buf[7]; hour_ = buf[8]; minute_ = buf[9]; second_ = buf[10]; year_ = buf[11]; key = buf[12];
    timeout = millis();}
  }
}

void bofang(int M)//播放第几首音乐的子程序
{
  PLAY[6] = M;
  for (int i = 1; i <= 8; i = i + (1))
  {
    mySerial.print(PLAY[(int)(i - 1)]);
  }
}

void volch(int m)  //音量
{
  YL[6] = m;
  for (int i = 1; i <= 8; i = i + (1))
  {
    mySerial.print(YL[(int)(i - 1)]);
  }
}

void zd()//整点播报
{
  if (((lw == 3) && (z3 == 1) && (second_low == 0) && (second_high == 0) && (minute_low == 0) && (minute_high == 0)) || key == 1)
  {
    z = hour_high * 10 + hour_low;
    z3 = 3;
    key = 0;
  }
  if (z3 == 3)
  {
    if (z == 0)
    {   }
    else
    {
      flag_time_bp = 1;
    }
    z3 = 2; delay(300); z3 = 2; second_low = 4;
  }
}
void xianshi(int x)
{
  Write_Max7219_byte(i);           //写入地址，即数码管编号
  Write_Max7219_byte(disp1[x * 2][i - 1]); //写入数据，即数码管显示数字
}
void xianshi1(int y)
{
  Write_Max7219_byte(i);           //写入地址，即数码管编号
  Write_Max7219_byte(disp1[y * 2 + 1][i - 1]); //写入数据，即数码管显示数字
}
