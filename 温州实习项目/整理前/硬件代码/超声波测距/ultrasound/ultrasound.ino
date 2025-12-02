// 超声波测距模块(HC-SR04)控制代码

// 定义引脚连接
#define TRIG_PIN 9    // 触发引脚
#define ECHO_PIN 10   // 接收引脚
#define MAX_DISTANCE 400  // 最大测量距离(cm)

float distance;  // 测量距离(cm)
unsigned long duration;  // 回波持续时间(us)

void setup() {
  // 初始化串口通信，用于调试输出
  Serial.begin(9600);
  Serial.println("超声波测距模块初始化完成");
  
  // 配置引脚模式
  pinMode(TRIG_PIN, OUTPUT);  // 触发引脚设为输出
  pinMode(ECHO_PIN, INPUT);   // 接收引脚设为输入
  
  // 确保触发引脚初始为低电平
  digitalWrite(TRIG_PIN, LOW);
  delay(200);  // 等待传感器稳定
}

void loop() {
  // 测量距离
  distance = measureDistance();
  
  // 输出测量结果到串口
  Serial.print("距离: ");
  Serial.print(distance);
  Serial.println(" cm");
  
  // 延时，避免测量过于频繁
  delay(500);
}

// 测量距离函数
float measureDistance() {
  // 发送10微秒的高电平触发信号
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  
  // 读取回波信号的持续时间
  duration = pulseIn(ECHO_PIN, HIGH);
  
  // 计算距离(声速约为340m/s = 0.034cm/μs，除以2是因为声波往返)
  // 距离(cm) = 时间(μs) * 0.034 / 2
  float dist = (duration * 0.034) / 2;
  
  // 检查是否超出测量范围
  if (dist > MAX_DISTANCE || dist <= 0) {
    Serial.println("测量距离超出范围或无效");
    return 0;
  }
  
  return dist;
}
