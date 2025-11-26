/*
 * AI室内助手 - main.cpp (简化版)
 * 
 * 这是一个简化版的ES32S3应用程序，具有以下功能：
 * - AI引擎数据接收并打印
 * - WiFi连接和配置
 * - 显示屏状态显示
 * - 生成JSON格式指令通过串口发送（使用GPIO6和GPIO7）
 *
 * 适用于ESP32S3-Dev开发板
 */

// 导入必要的库
#include <Arduino.h>
#include <WiFi.h>
#include <HardwareSerial.h>
#include <ArduinoJson.h>
#include <driver/spi_common.h>
#include <esp_heap_caps.h>
#include <esp_lcd_panel_io.h>
#include <esp_lcd_panel_ops.h>
#include <esp_lcd_panel_vendor.h>
#include <string>

// AI语音引擎和相关组件
#include "ai_vox_engine.h"
#include "ai_vox_observer.h"
#include "audio_device/audio_output_device_i2s_std.h"
#include "audio_input_device_sph0645.h"
#include "components/espressif/button/button_gpio.h"
#include "components/espressif/button/iot_button.h"
#include "components/wifi_configurator/wifi_configurator.h"
#include "display.h"

// 检查开发板兼容性
#ifndef ARDUINO_ESP32S3_DEV
#error "This example only supports ESP32S3-Dev board."
#endif

// 检查PSRAM配置
#ifndef CONFIG_SPIRAM_MODE_OCT
#error "This example requires PSRAM to OPI PSRAM. Please enable it in Arduino IDE."
#endif

// WiFi配置信息
#define WIFI_SSID "HEYBLOCK"
#define WIFI_PASSWORD "12345678"
const long kRpiBaudRate = 115200;
// 匿名命名空间，包含所有全局变量和辅助函数
namespace {
  // 智能配网类型
  constexpr smartconfig_type_t kSmartConfigType = SC_TYPE_ESPTOUCH_AIRKISS;

  // 麦克风引脚定义
  constexpr gpio_num_t kMicPinSck = GPIO_NUM_5;  // 麦克风时钟引脚
  constexpr gpio_num_t kMicPinWs = GPIO_NUM_2;   // 麦克风字选择引脚
  constexpr gpio_num_t kMicPinSd = GPIO_NUM_4;   // 麦克风数据引脚

  // 扬声器引脚定义
  constexpr gpio_num_t kSpeakerPinSck = GPIO_NUM_13;  // 扬声器时钟引脚
  constexpr gpio_num_t kSpeakerPinWs = GPIO_NUM_14;   // 扬声器字选择引脚
  constexpr gpio_num_t kSpeakerPinSd = GPIO_NUM_1;    // 扬声器数据引脚

  // 按钮引脚定义
  constexpr gpio_num_t kButtonBoot = GPIO_NUM_0;  // 启动按钮引脚

  // 显示屏引脚定义
  constexpr gpio_num_t kDisplayBacklightPin = GPIO_NUM_11;  // 显示屏背光引脚
  constexpr gpio_num_t kDisplayMosiPin = GPIO_NUM_17;      // 显示屏MOSI引脚
  constexpr gpio_num_t kDisplayClkPin = GPIO_NUM_16;       // 显示屏时钟引脚
  constexpr gpio_num_t kDisplayDcPin = GPIO_NUM_12;        // 显示屏数据/命令引脚
  constexpr gpio_num_t kDisplayRstPin = GPIO_NUM_21;       // 显示屏复位引脚
  constexpr gpio_num_t kDisplayCsPin = GPIO_NUM_15;        // 显示屏片选引脚

  // 显示屏配置参数
  constexpr auto kDisplaySpiMode = 0;                // SPI模式
  constexpr uint32_t kDisplayWidth = 240;            // 显示屏宽度
  constexpr uint32_t kDisplayHeight = 240;           // 显示屏高度
  constexpr bool kDisplayMirrorX = false;            // X轴镜像
  constexpr bool kDisplayMirrorY = false;            // Y轴镜像
  constexpr bool kDisplayInvertColor = true;         // 颜色反转
  constexpr bool kDisplaySwapXY = false;             // X/Y交换
  constexpr auto kDisplayRgbElementOrder = LCD_RGB_ELEMENT_ORDER_RGB; // RGB元素顺序

  // 串口引脚定义
  constexpr gpio_num_t kSerialTxPin = GPIO_NUM_6;  // 串口发送引脚
  constexpr gpio_num_t kSerialRxPin = GPIO_NUM_7;  // 串口接收引脚

  // 握手协议相关常量
  constexpr unsigned long HANDSHAKE_TIMEOUT = 2000;  // 握手超时时间（毫秒）
  constexpr int MAX_RETRIES = 3;  // 最大重试次数

  // 握手协议相关全局变量
  bool g_awaiting_handshake = false;  // 是否等待握手响应
  String g_last_command_event = "";  // 最后发送的指令事件名
  String g_last_command_json = "";  // 最后发送的指令JSON内容
  unsigned long g_command_sent_time = 0;  // 最后发送指令的时间戳
  int g_retry_count = 0;  // 当前指令的重试次数

  // 全局对象定义
  auto g_audio_output_device = std::make_shared<ai_vox::AudioOutputDeviceI2sStd>(
    kSpeakerPinSck, kSpeakerPinWs, kSpeakerPinSd);   // 音频输出设备
  button_handle_t g_button_boot_handle = nullptr;    // 启动按钮句柄
  HardwareSerial customSerial(2);  // 使用UART2作为自定义串口

  std::unique_ptr<Display> g_display;                // 显示屏对象
  auto g_observer = std::make_shared<ai_vox::Observer>();  // AI引擎观察者
  
  /**
   * @brief 初始化显示屏
   * 设置SPI总线、初始化LCD面板、配置显示参数并启动显示
   */
  void InitDisplay() {
    printf("init display\n");
    // 配置显示屏背光引脚
    pinMode(kDisplayBacklightPin, OUTPUT);
    analogWrite(kDisplayBacklightPin, 255);  // 最大亮度

    // 配置SPI总线
    spi_bus_config_t buscfg{
        .mosi_io_num = kDisplayMosiPin,
        .miso_io_num = GPIO_NUM_NC,  // 不使用MISO
        .sclk_io_num = kDisplayClkPin,
        .quadwp_io_num = GPIO_NUM_NC,
        .quadhd_io_num = GPIO_NUM_NC,
        .data4_io_num = GPIO_NUM_NC,
        .data5_io_num = GPIO_NUM_NC,
        .data6_io_num = GPIO_NUM_NC,
        .data7_io_num = GPIO_NUM_NC,
        .data_io_default_level = false,
        .max_transfer_sz = kDisplayWidth * kDisplayHeight * sizeof(uint16_t),
        .flags = 0,
        .isr_cpu_id = ESP_INTR_CPU_AFFINITY_AUTO,
        .intr_flags = 0,
    };
    ESP_ERROR_CHECK(spi_bus_initialize(SPI3_HOST, &buscfg, SPI_DMA_CH_AUTO));

    esp_lcd_panel_io_handle_t panel_io = nullptr;
    esp_lcd_panel_handle_t panel = nullptr;

    // 配置LCD IO
    esp_lcd_panel_io_spi_config_t io_config = {};
    io_config.cs_gpio_num = kDisplayCsPin;
    io_config.dc_gpio_num = kDisplayDcPin;
    io_config.spi_mode = kDisplaySpiMode;
    io_config.pclk_hz = 40 * 1000 * 1000;  // 40MHz时钟频率
    io_config.trans_queue_depth = 10;
    io_config.lcd_cmd_bits = 8;
    io_config.lcd_param_bits = 8;
    ESP_ERROR_CHECK(esp_lcd_new_panel_io_spi(SPI3_HOST, &io_config, &panel_io));

    // 配置LCD面板
    esp_lcd_panel_dev_config_t panel_config = {};
    panel_config.reset_gpio_num = kDisplayRstPin;
    panel_config.rgb_ele_order = kDisplayRgbElementOrder;
    panel_config.bits_per_pixel = 16;  // 16位色
    ESP_ERROR_CHECK(esp_lcd_new_panel_st7789(panel_io, &panel_config, &panel));

    // 初始化和配置面板
    esp_lcd_panel_reset(panel);
    esp_lcd_panel_init(panel);
    esp_lcd_panel_invert_color(panel, kDisplayInvertColor);
    esp_lcd_panel_swap_xy(panel, kDisplaySwapXY);
    esp_lcd_panel_mirror(panel, kDisplayMirrorX, kDisplayMirrorY);

    // 创建并启动显示屏对象
    g_display = std::make_unique<Display>(panel_io, panel, kDisplayWidth, kDisplayHeight,
      0, 0, kDisplayMirrorX, kDisplayMirrorY, kDisplaySwapXY);
    g_display->Start();
  }

  /**
   * @brief 配置WiFi连接
   * 初始化WiFi配置器，注册按钮回调，处理WiFi连接状态
   */
  void ConfigureWifi() {
    printf("configure wifi\n");
    // 创建WiFi配置器
    auto wifi_configurator = std::make_unique<WifiConfigurator>(WiFi, kSmartConfigType);

    // 注册启动按钮按下事件，用于触发智能配网
    ESP_ERROR_CHECK(iot_button_register_cb(
      g_button_boot_handle,
      BUTTON_PRESS_DOWN,
      nullptr,
      [](void*, void* data) {
        printf("boot button pressed\n");
        static_cast<WifiConfigurator*>(data)->StartSmartConfig();
      },
      wifi_configurator.get()));

    // 显示网络配置状态
    g_display->ShowStatus("网络配置中");

#if defined(WIFI_SSID) && defined(WIFI_PASSWORD)
    // 使用预定义的WiFi配置
    printf("wifi config start with wifi: %s, %s\n", WIFI_SSID, WIFI_PASSWORD);
    wifi_configurator->Start(WIFI_SSID, WIFI_PASSWORD);
#else
    // 使用空配置（等待智能配网）
    printf("wifi config start\n");
    wifi_configurator->Start();
#endif

    // 等待WiFi连接状态变化
    while (true) {
      const auto state = wifi_configurator->WaitStateChanged();
      if (state == WifiConfigurator::State::kConnecting) {
        printf("wifi connecting\n");
        g_display->ShowStatus("网络连接中");
      } else if (state == WifiConfigurator::State::kSmartConfiguring) {
        printf("wifi smart configuring\n");
        g_display->ShowStatus("配网模式");
      } else if (state == WifiConfigurator::State::kFinished) {
        break;
      }
    }

    // 取消注册按钮回调
    iot_button_unregister_cb(g_button_boot_handle, BUTTON_PRESS_DOWN, nullptr);

    // 显示连接成功信息
    printf("wifi connected\n");
    printf("- mac address: %s\n", WiFi.macAddress().c_str());
    printf("- bssid:       %s\n", WiFi.BSSIDstr().c_str());
    printf("- ssid:        %s\n", WiFi.SSID().c_str());
    printf("- ip:          %s\n", WiFi.localIP().toString().c_str());
    printf("- gateway:     %s\n", WiFi.gatewayIP().toString().c_str());
    printf("- subnet mask: %s\n", WiFi.subnetMask().toString().c_str());

    // 显示网络已连接状态
    g_display->ShowStatus("网络已连接");
  }

  /**
   * @brief 生成JSON格式的指令
   * 将AI引擎接收到的数据转换为JSON格式
   * @param type 指令类型
   * @param content 指令内容
   * @return JSON格式的字符串
   */
  void SendJsonWithHandshake(const String& json_command, const String& event_name);
  void SendSimpleJsonEventWithHandshake(const char* event_name) {
    StaticJsonDocument<128> doc;
    doc["event"] = event_name;
    String json_output;
    serializeJson(doc, json_output);
    SendJsonWithHandshake(json_output, String(event_name));
  }
  void SendJsonWithHandshake(const String& json_command, const String& event_name) {
  // if (g_awaiting_handshake && (millis() - g_command_sent_time < HANDSHAKE_TIMEOUT)) {
  //       printf("正在等待上一条指令 '%s' 的握手, 新指令 '%s' 已被丢弃\n", g_last_command_event.c_str(), event_name.c_str());
  //   return;
  // }
  
  //   if (!g_awaiting_handshake || g_last_command_event != event_name) {
  //   g_retry_count = 0;
  // }
  
  // if (g_retry_count >= MAX_RETRIES) {
  //       printf("指令 '%s' 已达最大重试次数, 放弃发送\n", event_name.c_str());
  //   g_awaiting_handshake = false;
  //   return;
  // }
  
    customSerial.println(json_command);
    // printf("-> 发送指令给Pi (第 %d 次): %s\n", g_retry_count + 1, json_command.c_str());
  
  // g_awaiting_handshake = true;
  //   g_last_command_event = event_name;
  //   g_last_command_json = json_command;
  // g_command_sent_time = millis();
  // g_retry_count++;
}  // namespace
}
/**
 * @brief Arduino setup函数
 * 初始化硬件和软件组件，配置系统
 */
 void InitLed() {
  // 初始化按钮
  printf("init button\n");
  const button_config_t btn_cfg = {
    .long_press_time = 1000,  // 长按时间阈值（毫秒）
    .short_press_time = 50,   // 短按时间阈值（毫秒）
  };

  const button_gpio_config_t gpio_cfg = {
    .gpio_num = kButtonBoot,
    .active_level = 0,  // 低电平有效
    .enable_power_save = false,
    .disable_pull = false,
  };

  // 创建按钮设备
  ESP_ERROR_CHECK(iot_button_new_gpio_device(&btn_cfg, &gpio_cfg, &g_button_boot_handle));

 }
void setup() {
  // 初始化串口通信 - 使用GPIO6和GPIO7
  customSerial.begin(kRpiBaudRate, SERIAL_8N1, kSerialRxPin, kSerialTxPin);
  Serial.begin(115200);  // 保留默认串口用于调试
   // 初始化显示屏
  InitDisplay();

  // 检查SPIRAM是否可用
  if (heap_caps_get_total_size(MALLOC_CAP_SPIRAM) == 0) {
    g_display->SetChatMessage(Display::Role::kSystem, "No SPIRAM available, please check your board.");
    while (true) {
      printf("No SPIRAM available, please check your board.\n");
      delay(1000);
    }
  }
  //等待树莓派响应WiFi凭据 暂时不写

  InitLed();

  // 初始化系统各组件
  g_display->ShowStatus("初始化");
  ConfigureWifi();  // 配置WiFi

  // 创建音频输入设备
  auto audio_input_device = std::make_shared<AudioInputDeviceSph0645>(kMicPinSck, kMicPinWs, kMicPinSd);
  // 配置AI引擎
  auto& ai_vox_engine = ai_vox::Engine::GetInstance();
  ai_vox_engine.SetObserver(g_observer);
  ai_vox_engine.SetOtaUrl("https://api.tenclass.net/xiaozhi/ota/");
  ai_vox_engine.ConfigWebsocket("wss://api.tenclass.net/xiaozhi/v1/",
    {{
      "Authorization", "Bearer test-token"
    }}
  );
  g_display->ShowStatus("AI Vox Engine starting...");
  // 启动AI引擎
  ai_vox_engine.Start(audio_input_device, g_audio_output_device);
  // 注册按钮回调，用于触发AI引擎交互
  ESP_ERROR_CHECK(iot_button_register_cb(
    g_button_boot_handle,
    BUTTON_PRESS_DOWN,
    nullptr,
    [](void* button_handle, void* usr_data) {
      printf("boot button pressed\n");
      ai_vox::Engine::GetInstance().Advance();
    },
    nullptr
  ));

  g_display->ShowStatus("AI引擎已启动");
}

/**
 * @brief Arduino loop函数
 * 主循环，处理各种事件和状态变化
 */
void loop() {
  // 获取并处理所有事件
  // while(customSerial.available() > 0) {
  //   String line = customSerial.readStringUntil('\n');
  //   customSerial.println("<- 从Pi接收: " + line);
  // }
  const auto events = g_observer->PopEvents();
  
  for (auto& event : events) {
    if (auto activation_event = std::get_if<ai_vox::ActivationEvent>(&event)) {
      // 处理设备激活事件
      printf("activation code: %s, message: %s\n", activation_event->code.c_str(), activation_event->message.c_str());
      g_display->ShowStatus("激活设备");
      g_display->SetChatMessage(Display::Role::kSystem, activation_event->message);
     
    } else if (auto state_changed_event = std::get_if<ai_vox::StateChangedEvent>(&event)) {
      // 处理状态变化事件
      switch (state_changed_event->new_state) {
        case ai_vox::ChatState::kIdle: 
          printf("Idle\n");
          break;
        case ai_vox::ChatState::kInitted: 
          printf("Initted\n");
          g_display->ShowStatus("初始化");
          break;
        case ai_vox::ChatState::kLoading: 
          printf("Loading...\n");
          g_display->ShowStatus("加载协议中");
          break;
        case ai_vox::ChatState::kLoadingFailed: 
          printf("Loading failed, please retry\n");
          g_display->ShowStatus("加载协议失败，请重试");
          break;
        case ai_vox::ChatState::kStandby: 
          printf("Standby\n");
          g_display->ShowStatus("待命");
          break;
        case ai_vox::ChatState::kConnecting: 
          printf("Connecting...\n");
          g_display->ShowStatus("连接中...");
          break;
        case ai_vox::ChatState::kListening: 
          printf("Listening...\n");
          g_display->ShowStatus("聆听中");
          break;
        case ai_vox::ChatState::kSpeaking: 
          printf("Speaking...\n");
          g_display->ShowStatus("说话中");
          break;
        default: 
          break;
      }
    } else if (auto emotion_event = std::get_if<ai_vox::EmotionEvent>(&event)) {
      // 处理情绪事件
      printf("emotion: %s\n", emotion_event->emotion.c_str());
      g_display->SetEmotion(emotion_event->emotion);
    } else if (auto chat_message_event = std::get_if<ai_vox::ChatMessageEvent>(&event)) {
      // 处理聊天消息事件
      StaticJsonDocument<256> doc;
      doc["event"] = "chat_message";
      switch (chat_message_event->role) {
        case ai_vox::ChatRole::kAssistant: {
          printf("role: assistant, content: %s\n", chat_message_event->content.c_str());
          g_display->SetChatMessage(Display::Role::kAssistant, chat_message_event->content);
          // 生成JSON格式指令并通过串口发送
          doc["role"] = "assistant";
          doc["content"] = chat_message_event->content;
          
          break;
        }
        case ai_vox::ChatRole::kUser: {
          printf("role: user, content: %s\n", chat_message_event->content.c_str());
          g_display->SetChatMessage(Display::Role::kUser, chat_message_event->content);
          // 生成JSON格式指令并通过串口发送
          doc["role"] = "user";
          doc["content"] = chat_message_event->content;
          
          break;
        }
      }
      
      String output;
      serializeJson(doc, output);
      customSerial.println(output);        
      printf("-> Sent chat message to Pi: %s\n", output.c_str());
    }else if (auto mcp_tool_call_event = std::get_if<ai_vox::McpToolCallEvent>(&event)) {
      printf("on mcp tool call: %s\n", mcp_tool_call_event->ToString().c_str());

      if ("self.audio_speaker.set_volume" == mcp_tool_call_event->name) {
        const auto volume_ptr = mcp_tool_call_event->param<int64_t>("volume");
        if (volume_ptr != nullptr) {
          printf("on mcp tool call: self.audio_speaker.set_volume, volume: %" PRId64 "\n", *volume_ptr);
          g_audio_output_device->set_volume(*volume_ptr);
          engine.SendMcpCallResponse(mcp_tool_call_event->id, true);
        } else {
          engine.SendMcpCallError(mcp_tool_call_event->id, "Missing valid argument: volume");
        }
      } else if ("self.audio_speaker.get_volume" == mcp_tool_call_event->name) {
        const auto volume = g_audio_output_device->volume();
        printf("on mcp tool call: self.audio_speaker.get_volume, volume: %" PRIu16 "\n", volume);
        engine.SendMcpCallResponse(mcp_tool_call_event->id, volume);
      } else if ("self.led.set" == mcp_tool_call_event->name) {
        const auto state_ptr = mcp_tool_call_event->param<bool>("state");
        if (state_ptr != nullptr) {
          printf("on mcp tool call: self.led.set, state: %d\n", *state_ptr);
          if (*state_ptr) {
            ESP_ERROR_CHECK(led_strip_set_pixel(g_led_strip, 0, 10, 10, 10));
          } else {
            ESP_ERROR_CHECK(led_strip_clear(g_led_strip));
          }
          ESP_ERROR_CHECK(led_strip_refresh(g_led_strip));
          g_led_on = *state_ptr;
          engine.SendMcpCallResponse(mcp_tool_call_event->id, true);
        } else {
          engine.SendMcpCallError(mcp_tool_call_event->id, "Missing valid argument: state");
        }
      } else if ("self.led.get" == mcp_tool_call_event->name) {
        printf("on mcp tool call: self.led.get, state: %d\n", g_led_on);
        engine.SendMcpCallResponse(mcp_tool_call_event->id, g_led_on);
      }
    }







    taskYIELD();
  }
}
