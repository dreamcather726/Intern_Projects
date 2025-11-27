void PinMode(int PIN, int PINMODE) {
  SET[2] = PINMODE;
  SET[3] = PIN;
  Wire.beginTransmission(LGT_address);
  Wire.write(SET, Len2);
  Wire.endTransmission();
}

int AnalogRead(int PIN) {
  int READ = 0;
  OPER[2] = 0x11;//读取模拟量 模式
  OPER[3] = PIN;//读取该引脚
  Wire.beginTransmission(LGT_address);//打开通讯
  Wire.write(OPER, Len3);//发送读取指令
  Wire.endTransmission();//关闭通讯
  Wire.requestFrom(LGT_address, 6);//读取数值
  if (Wire.available() > 0) {
    int len = 6;
    int buf[len];
    for (int i = 0; i < len; i++) {
      buf[i] = Wire.read();
    }
    READ = (buf[3] << 8 ) + (buf[4]);
  }
  return READ;
}

void AnalogWrite(int PIN, int HOW) {
  OPER[2] = 0x12;//读取模拟量 模式
  OPER[3] = PIN;//读取该引脚
  OPER[4] = HOW;//读取该引脚
  Wire.beginTransmission(LGT_address);//打开通讯
  Wire.write(OPER, Len3);//发送读取指令
  Wire.endTransmission();//关闭通讯
}

int DigitalRead(int PIN) {
  int READ = 0;
  OPER[2] = 0x13;//读取模拟量 模式
  OPER[3] = PIN;//读取该引脚
  Wire.beginTransmission(LGT_address);//打开通讯
  Wire.write(OPER, Len3);//发送读取指令
  Wire.endTransmission();//关闭通讯
  Wire.requestFrom(LGT_address, 6);//读取数值
  if (Wire.available() > 0) {
    int len = 6;
    int buf[len];
    for (int i = 0; i < len; i++) {
      buf[i] = Wire.read();
    }
    READ = buf[3];
  }
  return READ;
}

void DigitalWrite(int PIN, int HOW) {
  OPER[2] = 0x14;//读取模拟量 模式
  OPER[3] = PIN;//读取该引脚
  OPER[4] = HOW;//读取该引脚
  Wire.beginTransmission(LGT_address);//打开通讯
  Wire.write(OPER, Len3);//发送读取指令
  Wire.endTransmission();//关闭通讯
}

//打开外部中断  0右  1左
void AttachInterrupt(int NUM) {
  OPER[2] = 0x20;//打开中断操作模式
  OPER[3] = NUM;//操作该中断
  Wire.beginTransmission(LGT_address);//打开通讯
  Wire.write(OPER, Len3);//发送读取指令
  Wire.endTransmission();//关闭通讯
}

//关闭外部中断  0右  1左
void DetachInterrupt(int NUM) {
  OPER[2] = 0x21;//关闭中断操作模式
  OPER[3] = NUM;//操作该中断
  Wire.beginTransmission(LGT_address);//打开通讯
  Wire.write(OPER, Len3);//发送读取指令
  Wire.endTransmission();//关闭通讯
}

//清空编码器计数  0右  1左
void Clear(int NUM) {
  OPER[2] = 0x22;
  OPER[3] = NUM;
  Wire.beginTransmission(LGT_address);//打开通讯
  Wire.write(OPER, Len3);//发送读取指令
  Wire.endTransmission();//关闭通讯
}

//回传编码器计数  0右  1左
int GetCounter(int NUM) {
  long READ = 0;
  OPER[2] = 0x23;//读取模拟量 模式
  OPER[3] = NUM;//读取该引脚
  Wire.beginTransmission(LGT_address);//打开通讯
  Wire.write(OPER, Len3);//发送读取指令
  Wire.endTransmission();//关闭通讯
  Wire.requestFrom(LGT_address, 6);//读取数值
  if (Wire.available() > 0) {
    int len = 6;
    int buf[len];
    for (int i = 0; i < len; i++) {
      buf[i] = Wire.read();
    }
    READ = (buf[3] << 8 ) + (buf[4]);
    if (buf[2] == 0) {
      READ = 0 - READ;
    }
  }
  return READ;
}
