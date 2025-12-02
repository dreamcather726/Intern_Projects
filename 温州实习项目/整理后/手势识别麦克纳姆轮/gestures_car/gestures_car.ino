

#include <Wire.h>
#include "paj7620.h"
#include "string.h"
#include <SoftwareSerial.h>
// 定义手势动作与data/data1变量值的对应关系
// 从data变量(0x43寄存器)读取的手势
#define DATA_GES_RIGHT      GES_RIGHT_FLAG       // 向右手势
#define DATA_GES_LEFT       GES_LEFT_FLAG        // 向左手势
#define DATA_GES_UP         GES_UP_FLAG          // 向上手势
#define DATA_GES_DOWN       GES_DOWN_FLAG        // 向下手势
#define DATA_GES_FORWARD    GES_FORWARD_FLAG     // 向前手势
#define DATA_GES_BACKWARD   GES_BACKWARD_FLAG    // 向后手势
#define DATA_GES_CLOCKWISE  GES_CLOCKWISE_FLAG   // 顺时针手势
#define DATA_GES_COUNT_CLOCKWISE GES_COUNT_CLOCKWISE_FLAG // 逆时针手势

// 定义TB6612电机驱动引脚
// 电机1: 8号引脚控制正反转，6号引脚控制转速
#define MOTOR_1_DIR_PIN 7
#define MOTOR_1_PWM_PIN 5

// 电机2: 12号引脚控制正反转，9号引脚控制转速
#define MOTOR_2_DIR_PIN 9
#define MOTOR_2_PWM_PIN 8

// 电机3: 4号引脚控制正反转，3号引脚控制转速
#define MOTOR_3_DIR_PIN 3
#define MOTOR_3_PWM_PIN 2   

// 电机4: 7号引脚控制正反转，5号引脚控制转速
#define MOTOR_4_DIR_PIN 6
#define MOTOR_4_PWM_PIN 4
#define Speed 150
// 定义方向枚举
enum direction_t {
  FORWARD,
  BACKWARD
};

// 定义电机结构体（适配TB6612）
typedef struct {
  int dir_pin;     // 方向控制引脚
  int pwm_pin;     // 速度控制PWM引脚
} motor_t;
#define VOICE_RX_PIN 11
#define MP3_TX_PIN 10
char PLAY[] = {0X7E, 0XFF, 0X06, 0X0F, 0X00, 0X01, 0X01, 0XEF};
char VOLUME[] = {0X7E, 0XFF, 0X06, 0X06, 0X00, 0X01, 0X1E, 0XEF}; // 默认音量20（0-30范围）
SoftwareSerial MP3serial(VOICE_RX_PIN, MP3_TX_PIN); // RX, TX
// 电机实例（适配TB6612）
motor_t motors[4] = {
  {MOTOR_1_DIR_PIN, MOTOR_1_PWM_PIN}, // 电机1
  {MOTOR_2_DIR_PIN, MOTOR_2_PWM_PIN}, // 电机2
  {MOTOR_3_DIR_PIN, MOTOR_3_PWM_PIN}, // 电机3
  {MOTOR_4_DIR_PIN, MOTOR_4_PWM_PIN}  // 电机4
};

// 定义全局变量存储手势识别结果
String currentGesture = "";

// 从data1变量(0x44寄存器)读取的手势
#define DATA1_GES_WAVE      GES_WAVE_FLAG        // 挥手手势

#define GES_REACTION_TIME		500				// 你可以根据实际情况调整反应时间。
#define GES_ENTRY_TIME			800				// 当你想识别向前/向后手势时，你的手势反应时间必须小于GES_ENTRY_TIME(0.8秒)。
#define GES_QUIT_TIME			1000			// 退出时间，用于手势识别间隔
// 定义动作执行时间（毫秒）
#define ACTION_DURATION 2000
uint8_t data = 0, data1 = 0, error;
void setVolume(byte volume); // 设置MP3音量的函数声明

bool control_mode = false;// 控制模式，false为语音控制，true为手势控制
void setup()
{
	uint8_t error = 0;
	// 初始化电机引脚
	motor_Init();
	MP3serial.begin(9600);
	Serial.begin(9600);
	setVolume(25);
	error = paj7620Init();			// 初始化Paj7620寄存器
	Serial.println("@FMODE 2");
 	Serial.println("@BMP 0,0,57"); 
	Serial.println("@SET 100,开始");  
	delay(1500);
}

void loop(){
	if(MP3serial.available()){
  	char firstByte = MP3serial.read();
    if(firstByte == 0x55){   
	  byte temp[5];
      MP3serial.readBytes(temp,5);
      byte all[6]={firstByte,temp[0],temp[1],temp[2],temp[3],temp[4]};
      byte command = all[2];
	  byte value = all[3];
	  executeVoiceCommand(command, value);
    }  
  }

	// 在语音控制模式下，执行已经设置好的手势命令
	if(control_mode==false && currentGesture != ""){
		PLAY[6] = 0X08;
		MP3serial.write(PLAY, sizeof(PLAY));
		executeGesture(currentGesture);
		currentGesture=""; // 清空当前手势
	}

	// 手势控制模式下，进行手势识别和执行
	if(control_mode){
		Gesture_Recognition();		
		if(currentGesture != ""){
			PLAY_MP3();
			executeGesture(currentGesture);
			currentGesture=""; // 清空当前手势
		}
	}		
	// 短暂延迟，避免CPU占用过高
	delay(50);
}

void Gesture_Recognition(){    
	error = paj7620ReadReg(0x43, 1, &data);				// Read Bank_0_Reg_0x43/0x44 for gesture result.
	if (!error) 
	{
		switch (data) 									// When different gestures be detected, the variable 'data' will be set to different values by paj7620ReadReg(0x43, 1, &data).
		{
			case GES_RIGHT_FLAG:
				delay(GES_ENTRY_TIME);
				paj7620ReadReg(0x43, 1, &data);
				if(data == GES_FORWARD_FLAG) 
				{
				
					currentGesture = "forward";
					delay(GES_QUIT_TIME);
				}
				else if(data == GES_BACKWARD_FLAG) 
				{
					currentGesture = "backward";
					delay(GES_QUIT_TIME);
				}
				else
				{
					currentGesture = "right";
				}          
				break;
			case GES_LEFT_FLAG: 
				delay(GES_ENTRY_TIME);
				paj7620ReadReg(0x43, 1, &data);
				if(data == GES_FORWARD_FLAG) 
				{
					currentGesture = "forward";
					delay(GES_QUIT_TIME);
				}
				else if(data == GES_BACKWARD_FLAG) 
				{
					currentGesture = "backward";
					delay(GES_QUIT_TIME);
				}
				else
				{
					currentGesture = "left";
				}          
				break;
			case GES_UP_FLAG:
				delay(GES_ENTRY_TIME);
				paj7620ReadReg(0x43, 1, &data);
				if(data == GES_FORWARD_FLAG) 
				{
					currentGesture = "forward";
					delay(GES_QUIT_TIME);
				}
				else if(data == GES_BACKWARD_FLAG) 
				{
					currentGesture = "backward";
					delay(GES_QUIT_TIME);
				}
				else
				{
					currentGesture = "up";
				}          
				break;
			case GES_DOWN_FLAG:
				delay(GES_ENTRY_TIME);
				paj7620ReadReg(0x43, 1, &data);
				if(data == GES_FORWARD_FLAG) 
				{
					currentGesture = "forward";
					delay(GES_QUIT_TIME);
				}
				else if(data == GES_BACKWARD_FLAG) 
				{
					currentGesture = "backward";	
					delay(GES_QUIT_TIME);
				}
				else
				{
					currentGesture = "down";
				}          
				break;
			case GES_FORWARD_FLAG:
				currentGesture = "forward";
				delay(GES_QUIT_TIME);
				break;
			case GES_BACKWARD_FLAG:		  
				currentGesture = "backward";
				delay(GES_QUIT_TIME);
				break;
			case GES_CLOCKWISE_FLAG:
				currentGesture = "clockwise";	
				break;
			case GES_COUNT_CLOCKWISE_FLAG:
				currentGesture = "count_clockwise";	
				break;  
			default:
				paj7620ReadReg(0x44, 1, &data1);
				if (data1 == GES_WAVE_FLAG) 
				{
					currentGesture = "wave";
				}
				break;
		}
	}
	delay(100);
}
// 停止所有电机函数
void stopAllMotors() {
	MotorRunWithSpeed(motors[0], FORWARD, 0);
	MotorRunWithSpeed(motors[1], FORWARD, 0);
	MotorRunWithSpeed(motors[2], FORWARD, 0);
	MotorRunWithSpeed(motors[3], FORWARD, 0);
	Serial.println("@BMP 0,0,57"); 
	// Serial.println("所有电机已停止");
}

void executeGesture(String gesture){
		Serial.println("@BMP 0,0,57"); 
	if (gesture == "up") {
			// 执行向上动作
			
			Serial.print("@SET 100,");
			Serial.println("前进");
			Serial.println("@BMP 370,106,61");
			MotorRunWithSpeed(motors[0], FORWARD, Speed);
			MotorRunWithSpeed(motors[1], FORWARD, Speed);
			MotorRunWithSpeed(motors[2], FORWARD, Speed);
			MotorRunWithSpeed(motors[3], FORWARD, Speed);
			// Serial.println("设置为向上");
			// 执行规定时间后停止
			delay(ACTION_DURATION);
			stopAllMotors();
	} else if (gesture == "down") {
			// 执行向下动作
			 
			Serial.print("@SET 100,");
			Serial.println("后退");			 			
			Serial.println("@BMP 375,339,59");
			MotorRunWithSpeed(motors[0], BACKWARD, Speed);
			MotorRunWithSpeed(motors[1], BACKWARD, Speed);
			MotorRunWithSpeed(motors[2], BACKWARD, Speed);
			MotorRunWithSpeed(motors[3], BACKWARD, Speed);
			// Serial.println("设置为向下");
			// 执行规定时间后停止
			delay(ACTION_DURATION);
			stopAllMotors();
	} else if (gesture == "left") {
			// 执行向左动作
			Serial.println("@BMP 0,0,57"); 
			Serial.print("@SET 100,");
			Serial.println("左移");
			Serial.println("@BMP 214,238,60");
			MotorRunWithSpeed(motors[0], BACKWARD, 0);
			MotorRunWithSpeed(motors[1], FORWARD, Speed);
			MotorRunWithSpeed(motors[2], BACKWARD, 0);
			MotorRunWithSpeed(motors[3], FORWARD, Speed);
			// Serial.println("设置为向左");
			// 执行规定时间后停止
			delay(ACTION_DURATION);
			stopAllMotors();
	} else if (gesture == "right") {
			// 执行向右动作
			Serial.println("@BMP 0,0,57"); 
			Serial.print("@SET 100,");
			Serial.println("右移");
			Serial.println("@BMP 489,236,58");
			Serial.print("@SET 100,");
			Serial.println("右移");
			MotorRunWithSpeed(motors[0], FORWARD, Speed);
			MotorRunWithSpeed(motors[1], BACKWARD, 0);
			MotorRunWithSpeed(motors[2], FORWARD, Speed);
			MotorRunWithSpeed(motors[3], BACKWARD, 0);
			// Serial.println("设置为向右");
			// 执行规定时间后停止
			delay(ACTION_DURATION);
			stopAllMotors();
	} else if (gesture == "clockwise") {
			// 执行顺时针动作
			Serial.println("@BMP 0,0,57"); 
			Serial.print("@SET 100,");
			Serial.println("顺时");
			Serial.println("@BMP 242,149,55");
			MotorRunWithSpeed(motors[0], FORWARD, Speed);
			MotorRunWithSpeed(motors[1], BACKWARD, Speed);
			MotorRunWithSpeed(motors[2], FORWARD, Speed);
			MotorRunWithSpeed(motors[3], BACKWARD, Speed);
			// Serial.println("设置为顺时针");
			// 执行规定时间后停止
			delay(ACTION_DURATION);
			stopAllMotors();
	} else if (gesture == "count_clockwise") {
			// 执行逆时针动作
			Serial.println("@BMP 0,0,57"); 
			Serial.print("@SET 100,");
			Serial.println("逆时");
			Serial.println("@BMP 465,144,62");
			MotorRunWithSpeed(motors[0], BACKWARD, Speed);
			MotorRunWithSpeed(motors[1], FORWARD, Speed);
			MotorRunWithSpeed(motors[2], BACKWARD, Speed);
			MotorRunWithSpeed(motors[3], FORWARD, Speed);
			// Serial.println("设置为逆时针");
			// 执行规定时间后停止
			delay(ACTION_DURATION);
			stopAllMotors();
	} else if (gesture == "wave") {
			// 执行挥手动作 - 可以设置为停止所有电机
			Serial.println("@BMP 0,0,57"); 
			Serial.println("停止"); 
			stopAllMotors();
	}else if (gesture=="up_left")//左上角
	{
			// 执行向上向左动作
			Serial.println("@BMP 0,0,57");  
			Serial.print("@SET 100,");
			Serial.println("左上角");
			Serial.println("@BMP 217,133,63");
			MotorRunWithSpeed(motors[0], FORWARD, Speed);
			MotorRunWithSpeed(motors[1], FORWARD, Speed);
			MotorRunWithSpeed(motors[2], FORWARD, Speed);
			MotorRunWithSpeed(motors[3], FORWARD, Speed);
			// Serial.println("设置为向上");
			// 执行规定时间后停止
			delay(ACTION_DURATION);
			stopAllMotors();
	}else if (gesture=="up_right")//右上角
	{
			// 执行向上向右动作
			Serial.println("@BMP 0,0,57"); 
			Serial.print("@SET 100,");
			Serial.println("右上角");
			Serial.println("@BMP 484,134,65");
			MotorRunWithSpeed(motors[0], FORWARD, Speed);
			MotorRunWithSpeed(motors[1], FORWARD, Speed);
			MotorRunWithSpeed(motors[2], FORWARD, Speed);
			MotorRunWithSpeed(motors[3], FORWARD, Speed);
			// Serial.println("设置为向上");
			// 执行规定时间后停止
			delay(ACTION_DURATION);
			stopAllMotors();
	}else if (gesture=="bottom_left")//左下角
	{
			// 执行向下向左动作
			Serial.println("@BMP 0,0,57");
			delay(100);
			Serial.print("@SET 100,");
			delay(100);
			Serial.println("左下角");
			delay(100);
			Serial.println("@BMP 217,334,64");
			delay(100);
			MotorRunWithSpeed(motors[0], BACKWARD, Speed);
			MotorRunWithSpeed(motors[1], BACKWARD, Speed);
			MotorRunWithSpeed(motors[2], BACKWARD, Speed);
			MotorRunWithSpeed(motors[3], BACKWARD, Speed);
			// Serial.println("设置为向下");
			// 执行规定时间后停止
			delay(ACTION_DURATION);
			stopAllMotors();
	}else if (gesture=="bottom_right")//右下角
	{
			// 执行向下向右动作
 			Serial.println("@BMP 0,0,57"); 
			Serial.print("@SET 100,");
			Serial.println("右下角");
			Serial.println("@BMP 480,334,66");
			MotorRunWithSpeed(motors[0], BACKWARD, Speed);
			MotorRunWithSpeed(motors[1], BACKWARD, Speed);
			MotorRunWithSpeed(motors[2], BACKWARD, Speed);
			MotorRunWithSpeed(motors[3], BACKWARD, Speed);
			// Serial.println("设置为向下");
			// 执行规定时间后停止
			delay(ACTION_DURATION);
			stopAllMotors();
	} else if (gesture == "stop") {
			// 执行停止动作 - 可以设置为停止所有电机
			Serial.println("@BMP 0,0,57"); 
			Serial.print("@SET 100,");
			Serial.println("停止"); 
			stopAllMotors();
	}
	Serial.print("@SET 100,");
	Serial.println("停止 ");
}
void motor_Init() {
  // 初始化电机引脚（适配TB6612）
  pinMode(MOTOR_1_DIR_PIN, OUTPUT);
  pinMode(MOTOR_1_PWM_PIN, OUTPUT);
  pinMode(MOTOR_2_DIR_PIN, OUTPUT);
  pinMode(MOTOR_2_PWM_PIN, OUTPUT);
  pinMode(MOTOR_3_DIR_PIN, OUTPUT);
  pinMode(MOTOR_3_PWM_PIN, OUTPUT);
  pinMode(MOTOR_4_DIR_PIN, OUTPUT);
  pinMode(MOTOR_4_PWM_PIN, OUTPUT);
  
  // 初始化PWM引脚为LOW
  digitalWrite(MOTOR_1_PWM_PIN, LOW);
  digitalWrite(MOTOR_2_PWM_PIN, LOW);
  digitalWrite(MOTOR_3_PWM_PIN, LOW);
  digitalWrite(MOTOR_4_PWM_PIN, LOW);
}
void MotorRunWithSpeed(motor_t motor, direction_t direction, int speed) {
  // 确保speed值在有效范围内（0-255）
  if (speed < 0) speed = 0;
  if (speed > 255) speed = 255;
  
  // TB6612控制逻辑
  // 方向引脚设置：HIGH为一个方向，LOW为另一个方向
  // PWM引脚控制速度
  if (direction == FORWARD) {
    digitalWrite(motor.dir_pin, HIGH);  // 设置前进方向
    analogWrite(motor.pwm_pin, speed);  // 设置PWM速度
  } else if (direction == BACKWARD) {
    digitalWrite(motor.dir_pin, LOW);   // 设置后退方向
    analogWrite(motor.pwm_pin, speed);  // 设置PWM速度
  }
}
// 设置MP3音量的函数
void setVolume(byte volume) {
  // 确保音量在有效范围内（0-30）
  if (volume > 30) volume = 30;
  if (volume < 0) volume = 0;
  
  // 设置音量命令
  char volumeCmd[] = {0X7E, 0XFF, 0X06, 0X06, 0X00, 0X01, 0X00, 0XEF};
  volumeCmd[6] = volume; // 设置音量值
  
  // 发送音量命令
  MP3serial.write(volumeCmd, sizeof(volumeCmd));

}
void PLAY_MP3(){
	if(currentGesture == "up"){
		PLAY[6] = 0X01;
		MP3serial.write(PLAY, sizeof(PLAY));
	}else if(currentGesture == "down"){
		PLAY[6] = 0X02;
		MP3serial.write(PLAY, sizeof(PLAY));
	}else if(currentGesture == "left"){
		PLAY[6] = 0X03;
		MP3serial.write(PLAY, sizeof(PLAY));
	}
	else if(currentGesture == "right"){
		PLAY[6] = 0X04;
		MP3serial.write(PLAY, sizeof(PLAY));
	}
	else if(currentGesture == "clockwise"){
		PLAY[6] = 0X05;
		MP3serial.write(PLAY, sizeof(PLAY));
	}
	else if(currentGesture == "count_clockwise"){
		PLAY[6] = 0X06;
		MP3serial.write(PLAY, sizeof(PLAY));
	}
	else if(currentGesture == "wave"){
		PLAY[6] = 0X07;
		MP3serial.write(PLAY, sizeof(PLAY));
	}
	
}
void executeVoiceCommand(byte command, byte value){
	if(command == 0x02 && value == 0x01){
		control_mode = true;
		Serial.println("手势控制模式");
	}else if(command == 0x03 && value == 0x01){
		control_mode = false;
		Serial.println("语音控制模式");
	}
	if(control_mode==false){//语音 控制模式
		if(value == 0x02){
			currentGesture = "up";
		}else if(value == 0x03){
			currentGesture = "down";
		}else if(value == 0x04){
			currentGesture = "left";
		}else if(value == 0x05){
			currentGesture = "right";
		}else if(value == 0x06){
			currentGesture = "clockwise";
		}else if(value == 0x07){
			currentGesture = "count_clockwise";
		}else if(value == 0x08){
			currentGesture = "up_left";
		}else if(value == 0x09){
			currentGesture = "bottom_left";
		}else if(value == 0x0A){
			currentGesture = "up_right";
		}else if(value == 0x0B){
			currentGesture = "bottom_right";
		}
	}
}