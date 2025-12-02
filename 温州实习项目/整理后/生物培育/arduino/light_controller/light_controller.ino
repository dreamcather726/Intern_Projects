#include <SoftwareSerial.h>




SoftwareSerial mySerial1(11, 12); // RX, TX


// 灯光控制函数
void light1_on() {
  digitalWrite(2, HIGH);
  digitalWrite(3, HIGH);
}

void light1_off() {
  digitalWrite(2, LOW);
  digitalWrite(3, LOW);

}

void light2_on() {
  digitalWrite(4, HIGH);
  digitalWrite(5, HIGH);

}

void light2_off() {
  digitalWrite(4, LOW);
  digitalWrite(5, LOW);

}

void light3_on() {
  digitalWrite(6, HIGH);
  digitalWrite(7, HIGH);
 
}

void light3_off() {
  digitalWrite(6, LOW);
  digitalWrite(7, LOW);
}

void light4_on() { // 鱼缸灯
  digitalWrite(8, HIGH);
  digitalWrite(9, HIGH);
}

void light4_off() { // 鱼缸灯
  digitalWrite(8, LOW);
  digitalWrite(9, LOW);

}

void all_lights_on() {
  digitalWrite(2, HIGH);
  digitalWrite(3, HIGH);
  digitalWrite(4, HIGH);
  digitalWrite(5, HIGH);
  digitalWrite(6, HIGH);
  digitalWrite(7, HIGH);
  digitalWrite(8, HIGH);
  digitalWrite(9, HIGH);

}

void all_lights_off() {
  digitalWrite(2, LOW);
  digitalWrite(3, LOW);
  digitalWrite(4, LOW);
  digitalWrite(5, LOW);
  digitalWrite(6, LOW);
  digitalWrite(7, LOW);
  digitalWrite(8, LOW);
  digitalWrite(9, LOW);
}

// 定时发送状态反馈 (用于告知树莓派指令已执行)


void setup() {
  Serial.begin(9600);
  mySerial1.begin(115200);

  // 初始化所有灯光引脚为输出
  pinMode(2, OUTPUT);
  pinMode(3, OUTPUT);
  pinMode(4, OUTPUT);
  pinMode(5, OUTPUT);
  pinMode(6, OUTPUT);
  pinMode(7, OUTPUT);
  pinMode(8, OUTPUT);
  pinMode(9, OUTPUT);

  // 启动时确保所有灯都关闭
  all_lights_off();

  
}

void loop() {


  // 检查是否收到LoRa数据
  if (mySerial1.available() > 0) {
    delay(20); // 等待数据传输完成
    byte first=mySerial1.read();
    byte rec[4];    
    if(first==0xA0){    
    int bytesRead = mySerial1.readBytes(rec, 4);
    // 只解析灯光控制指令 (帧头 A0 0F 05 00 FF)
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
      //全局灯光控制指令 (类型 0D )
      if(rec[0]==0x0D){
        if(rec[1]==0x01){
          all_lights_on();
          Serial.println("all_lights_on");
        }else if(rec[1]==0x02){
          all_lights_off();
          Serial.println("all_lights_off");
        }
      }else if(rec[0]==0x0B){//全部设备
        if(rec[1]==0x01){
          all_lights_on();
          Serial.println("all_lights_on");
        }else if(rec[1]==0x02){
          all_lights_off();
          Serial.println("all_lights_off");
        }
      }
      
      
      else if(rec[0]==0x0c){
        if(rec[1]==0x01){
          light1_on();
          Serial.println("light1_on");
        }else if(rec[1]==0x02){
          light1_off();
          Serial.println("light1_off");
        }else if(rec[1]==0x03){
          light2_on();
          Serial.println("light2_on");
        }else if(rec[1]==0x04){
          light2_off();
          Serial.println("light2_off");
        }else if(rec[1]==0x05){
          light3_on();
          Serial.println("light3_on");
        }else if(rec[1]==0x06){
          light3_off();
          Serial.println("light3_off");
        }else if(rec[1]==0x07){
          light4_on(); // 鱼缸灯开
          Serial.println("light4_on");
        }else if(rec[1]==0x08){
          light4_off(); // 鱼缸灯关
          Serial.println("light4_off");
        }
      }
      clearSerialBuffer();
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
  mySerial1.flush();
  
  // 短暂延时确保所有响应数据都已到达
  delay(50);
  
  // 清空接收缓冲区中可能存在的残留数据
  while (mySerial1.available() > 0) {
    mySerial1.read(); // 读取并丢弃所有可用字节
  }
}