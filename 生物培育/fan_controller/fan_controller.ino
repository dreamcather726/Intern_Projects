#include <SoftwareSerial.h>



SoftwareSerial loraSerial(11, 12); // LoRa通信串口

// 风扇控制函数
void fan3_on() {
  digitalWrite(4, HIGH);
  Serial.println("Fan 3 ON (Control only)");
}

void all_fans_on() {
  digitalWrite(2, HIGH);
  digitalWrite(3, HIGH);
  digitalWrite(4, HIGH);
  Serial.println("All fans ON (Control only)");
}

void fan1_on() {
  digitalWrite(2, HIGH);
  Serial.println("Fan 1 ON (Control only)");
}

void fan3_off() {
  digitalWrite(4, LOW);
  Serial.println("Fan 3 OFF (Control only)");
}

void fan1_off() {
  digitalWrite(2, LOW);
  Serial.println("Fan 1 OFF (Control only)");
}

void all_fans_off() {
  digitalWrite(2, LOW);
  digitalWrite(3, LOW);
  digitalWrite(4, LOW);
  Serial.println("All fans OFF (Control only)");
}

void fan2_on() {
  digitalWrite(3, HIGH);
  Serial.println("Fan 2 ON (Control only)");
}

void fan2_off() {
  digitalWrite(3, LOW);
  Serial.println("Fan 2 OFF (Control only)");
}

void setup() {
  Serial.begin(9600);
  loraSerial.begin(115200);
  
  // 初始化风扇控制引脚
  pinMode(4, OUTPUT);
  pinMode(2, OUTPUT);
  pinMode(3, OUTPUT);
  
  Serial.println("Fan Controller Started");

}

void loop() {
  
  
  // 处理LoRa接收数据
  if (loraSerial.available() > 0) {
    delay(20);
    byte first=loraSerial.read();
    byte rec[4]; 
    if (first==0xA0){
      int bytesRead = loraSerial.readBytes(rec, 4);
      if (rec[2] == 0x00 && rec[3] == 0xFF) {
      Serial.print("原始指令: ");
      Serial.print(" ");
      Serial.print(rec[0] < 0x10 ? "0" : "");
      Serial.print(rec[0], HEX);
      Serial.print(" ");
      Serial.print(rec[1] < 0x10 ? "0" : "");
      Serial.print(rec[1], HEX);
      Serial.print(" ");
      Serial.print(rec[2] < 0x10 ? "0" : "");
      Serial.print(rec[2], HEX);
      Serial.print(" ");
      Serial.print(rec[3] < 0x10 ? "0" : "");
      Serial.println(rec[3], HEX);      
      clearSerialBuffer();
      if (rec[0]==0x09){//全部风扇
        if (rec[1]==0x01){
          all_fans_on();
        }else if (rec[1]==0x02){
          all_fans_off();
        }
      }else if (rec[0]==0x0B){//全部设备

        if (rec[1]==0x01){
          all_fans_on();
        }else if (rec[1]==0x02){
          all_fans_off();
        }
      }else if (rec[0]==0x0E){//单个风扇
        if (rec[1]==0x01){
          fan1_on();
        }else if (rec[1]==0x02){
          fan1_off();
        }else if (rec[1]==0x03){
          fan2_on();
        }else if (rec[1]==0x04){
          fan2_off();
        }else if (rec[1]==0x05){  
          fan3_on();
        }else if (rec[1]==0x06){
          fan3_off();
        }
      }


    }
    
  }
}
}
/**
 * 清理串口缓冲区
 * 等待发送完成，短暂延时后清空接收缓冲区
 */
void clearSerialBuffer() {
  // 等待发送缓冲区数据发送完成
  loraSerial.flush();
  
  // 短暂延时确保所有响应数据都已到达
  delay(50);
  
  // 清空接收缓冲区中可能存在的残留数据
  while (loraSerial.available() > 0) {
    loraSerial.read(); // 读取并丢弃所有可用字节
  }
}
