/*
 * 霍尔编码电机驱动程序 - 单中断版本
 * 引脚配置：
 *   PWM控制：引脚5
 *   方向控制：引脚6 (HIGH=正转, LOW=反转 或反之)
 *   编码器A相：引脚2（外部中断0）- 仅使用A相
 *   编码器B相：引脚3 - 不使用中断
 */

// ========== 引脚定义区域 ==========
#define MOTOR_PWM_PIN     5   // 电机PWM控制引脚
#define MOTOR_DIR_PIN     6   // 电机方向控制引脚
#define ENCODER_A_PIN     2   // 编码器A相（外部中断0）
#define ENCODER_B_PIN     4   // 编码器B相（仅用于方向检测）


// ========== 常量定义区域 ==========
#define MAX_SPEED         255   // PWM最大值
#define DEFAULT_SPEED     150   // 默认速度
#define ENCODER_PPR       390   // 霍尔编码器每圈脉冲数

// ========== 全局变量 ==========
volatile long encoderCount = 0;    // 编码器计数值
int motorSpeed = DEFAULT_SPEED;    // 当前电机速度
bool directionLogic = true;        // 方向逻辑: true=HIGH正转, false=LOW正转
bool motorRunning = false;         // 电机运行状态
bool lastEncoderState = false;     // 编码器上一次状态
bool autoStopEnabled = true;       // 是否启用自动停止功能

// ========== 函数声明 ==========
void stopMotor();
void forwardMotor();
void backwardMotor();
void setMotorSpeed(int speed);
void toggleDirectionLogic();
void printStatus();
float getRevolutions();
void toggleAutoStop();

// ========== 初始化函数 ==========
void setup() {
  // 初始化串口通信
  Serial.begin(115200);
  Serial.println("===== 单中断编码器电机控制系统 =====");
  Serial.println("命令列表:");
  Serial.println("'u' - 电机正转");
  Serial.println("'s' - 电机停止"); 
  Serial.println("'b' - 电机反转");
  Serial.println("'+' - 增加速度");
  Serial.println("'-' - 减少速度");
  Serial.println("'x' - 切换方向逻辑");
  Serial.println("'e' - 显示圈数");
  Serial.println("'r' - 重置编码器");
  Serial.println("'?' - 显示状态");
  Serial.println("'a' - 切换自动停止功能");
  
  // 初始化电机控制引脚
  pinMode(MOTOR_PWM_PIN, OUTPUT);
  pinMode(MOTOR_DIR_PIN, OUTPUT);
  
  // 初始化编码器引脚
  pinMode(ENCODER_A_PIN, INPUT_PULLUP);
  pinMode(ENCODER_B_PIN, INPUT_PULLUP);
  
  // 只设置A相的中断
  attachInterrupt(digitalPinToInterrupt(ENCODER_A_PIN), updateEncoder, CHANGE);
  
  // 初始停止电机
  stopMotor();
  
  // 记录初始编码器状态
  lastEncoderState = digitalRead(ENCODER_A_PIN);
  
  Serial.println("系统初始化完成 - 使用单中断模式");
  printStatus();
}

// ========== 编码器中断服务函数 - 单中断版本 ==========
void updateEncoder() {
  // 读取当前A相状态
  bool currentAState = digitalRead(ENCODER_A_PIN);
  
  // 只在状态变化时计数
  if (currentAState != lastEncoderState) {
    // 使用B相状态判断方向
    bool bState = digitalRead(ENCODER_B_PIN);
    
    // 根据A相和B相的相对状态判断方向
    if (currentAState == bState) {
      encoderCount++;  // 正转
    } else {
      encoderCount--;  // 反转
    }
    
    lastEncoderState = currentAState;
  }
}

// ========== 电机控制函数 ==========

// 停止电机
void stopMotor() {
  analogWrite(MOTOR_PWM_PIN, 0);
  motorRunning = false;
  Serial.println("电机已停止");
}

// 电机正转
void forwardMotor() {
  if (directionLogic) {
    digitalWrite(MOTOR_DIR_PIN, HIGH);
  } else {
    digitalWrite(MOTOR_DIR_PIN, LOW);
  }
  // 启动前重置编码器计数，确保从0开始计数
  resetEncoder();
  analogWrite(MOTOR_PWM_PIN, motorSpeed);
  motorRunning = true;
  Serial.println("电机正转");
}

// 电机反转
void backwardMotor() {
  if (directionLogic) {
    digitalWrite(MOTOR_DIR_PIN, LOW);
  } else {
    digitalWrite(MOTOR_DIR_PIN, HIGH);
  }
  // 启动前重置编码器计数，确保从0开始计数
  resetEncoder();
  analogWrite(MOTOR_PWM_PIN, motorSpeed);
  motorRunning = true;
  Serial.println("电机反转");
}

// 设置电机速度
void setMotorSpeed(int speed) {
  if (speed < 0) speed = 0;
  if (speed > MAX_SPEED) speed = MAX_SPEED;
  
  motorSpeed = speed;
  
  if (motorRunning) {
    analogWrite(MOTOR_PWM_PIN, motorSpeed);
  }
  
  Serial.print("速度设置为: ");
  Serial.println(motorSpeed);
}

// 切换方向逻辑
void toggleDirectionLogic() {
  directionLogic = !directionLogic;
  Serial.print("方向逻辑已切换: ");
  Serial.println(directionLogic ? "HIGH=正转" : "LOW=正转");
  
  // 如果电机正在运行，重新应用方向
  if (motorRunning) {
    // 短暂停止然后重新启动
    analogWrite(MOTOR_PWM_PIN, 0);
    delay(10);
    if (directionLogic) {
      digitalWrite(MOTOR_DIR_PIN, HIGH);
    } else {
      digitalWrite(MOTOR_DIR_PIN, LOW);
    }
    analogWrite(MOTOR_PWM_PIN, motorSpeed);
    // 重新启动时重置编码器计数
    resetEncoder();
  }
}

// 切换自动停止功能
void toggleAutoStop() {
  autoStopEnabled = !autoStopEnabled;
  Serial.print("自动停止功能已");
  Serial.println(autoStopEnabled ? "启用" : "禁用");
}

// 获取旋转圈数
float getRevolutions() {
  // 禁用中断以确保安全读取
  noInterrupts();
  long count = encoderCount;
  interrupts();
  
  // 计算圈数：总脉冲数 / 每圈脉冲数
  return (float)count / ENCODER_PPR;
}

// 重置编码器计数
void resetEncoder() {
  noInterrupts();
  encoderCount = 0;
  interrupts();
  Serial.println("编码器计数已重置");
}

// 打印状态信息
void printStatus() {
  Serial.println("===== 系统状态 =====");
  Serial.print("方向逻辑: ");
  Serial.println(directionLogic ? "HIGH=正转, LOW=反转" : "LOW=正转, HIGH=反转");
  Serial.print("当前速度: ");
  Serial.println(motorSpeed);
  Serial.print("编码器计数: ");
  Serial.println(encoderCount);
  Serial.print("电机圈数: ");
  Serial.print(getRevolutions(), 3);
  Serial.println(" 圈");
  Serial.print("电机状态: ");
  Serial.println(motorRunning ? "运行" : "停止");
  Serial.print("自动停止: ");
  Serial.println(autoStopEnabled ? "启用" : "禁用");
  Serial.print("编码器A相状态: ");
  Serial.println(digitalRead(ENCODER_A_PIN));
  Serial.print("编码器B相状态: ");
  Serial.println(digitalRead(ENCODER_B_PIN));
  Serial.println("====================");
}

// ========== 主循环函数 ==========
void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();
    
    switch (command) {
      case 'u':
      case 'U':
        forwardMotor();
        break;
        
      case 's':
      case 'S':
        stopMotor();
        break;
        
      case 'b':
      case 'B':
        backwardMotor();
        break;
        
      case '+':
        motorSpeed += 20;
        setMotorSpeed(motorSpeed);
        break;
        
      case '-':
        motorSpeed -= 20;
        setMotorSpeed(motorSpeed);
        break;
        
      case 'x':
      case 'X':
        toggleDirectionLogic();
        break;
        
      case 'e':
      case 'E':
        Serial.print("当前圈数: ");
        Serial.print(getRevolutions(), 3);
        Serial.println(" 圈");
        break;
        
      case 'r':
      case 'R':
        resetEncoder();
        break;
        
      case '?':
        printStatus();
        break;
        
      case 'a':
      case 'A':
        toggleAutoStop();
        break;
        
      default:
        Serial.println("未知命令，输入'?'查看帮助");
        break;
    }
  }
  
  // 检测是否旋转了一圈，如果启用了自动停止功能则停止电机
  if (motorRunning && autoStopEnabled) {
    float currentRevolutions = getRevolutions();
    // 检查是否旋转了一圈或更多
    if (abs(currentRevolutions) >= 1.0) {
      stopMotor();
      Serial.println("已旋转一圈，电机自动停止");
    }
  }
  
  // 自动检测圈数变化并更新显示
  static unsigned long lastReportTime = 0;
  static float lastRevolutions = 0;
  
  if (motorRunning && millis() - lastReportTime > 1000) {
    float currentRevolutions = getRevolutions();
    
    // 检查圈数是否有明显变化
    if (abs(currentRevolutions - lastRevolutions) >= 0.1) {
      Serial.print("运行中 - 圈数: ");
      Serial.print(currentRevolutions, 3);
      Serial.println(" 圈");
      lastRevolutions = currentRevolutions;
    }
    
    lastReportTime = millis();
  }
  
  delay(10);
}