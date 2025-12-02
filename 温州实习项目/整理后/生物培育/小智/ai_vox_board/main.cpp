#include <Arduino.h>
#include <WiFi.h>
#include <driver/spi_common.h>
#include <esp_heap_caps.h>
#include <esp_lcd_panel_io.h>
#include <esp_lcd_panel_ops.h>
#include <esp_lcd_panel_vendor.h>
#include <ArduinoJson.h>
#include "ai_vox_engine.h"
#include "audio_device/audio_output_device_i2s_std.h"
#include "audio_input_device_sph0645.h"
#include "components/espressif/button/button_gpio.h"
#include "components/espressif/button/iot_button.h"
#include "components/espressif/esp_audio_codec/esp_audio_simple_dec.h"
#include "components/espressif/esp_audio_codec/esp_mp3_dec.h"
#include "components/wifi_configurator/wifi_configurator.h"
#include "display.h"
#include "led_strip.h"
#include "network_config_mode_mp3.h"
#include "network_connected_mp3.h"
#include "notification_0_mp3.h"

#ifndef ARDUINO_ESP32S3_DEV
#error "This example only supports ESP32S3-Dev board."
#endif

#ifndef CONFIG_SPIRAM_MODE_OCT
#error "This example requires PSRAM to OPI PSRAM. Please enable it in Arduino IDE."
#endif

/**
 * 如果开机自动连接WiFi而不需要配置WiFi, 请注释掉下面的宏, 然后请修改下面的WIFI_SSID和WIFI_PASSWORD
 */
// #define WIFI_SSID "your_wifi_ssid"
// #define WIFI_PASSWORD "your_wifi_password"

namespace {
/**
 *  SC_TYPE_ESPTOUCH            protocol: ESPTouch
 *  SC_TYPE_AIRKISS,            protocol: AirKiss
 *  SC_TYPE_ESPTOUCH_AIRKISS,   protocol: ESPTouch and AirKiss
 *  SC_TYPE_ESPTOUCH_V2,        protocol: ESPTouch v2
 */
constexpr smartconfig_type_t kSmartConfigType = SC_TYPE_ESPTOUCH_AIRKISS;  // ESPTouch and AirKiss

constexpr gpio_num_t kMicPinSck = GPIO_NUM_5;
constexpr gpio_num_t kMicPinWs = GPIO_NUM_2;
constexpr gpio_num_t kMicPinSd = GPIO_NUM_4;

constexpr gpio_num_t kSpeakerPinSck = GPIO_NUM_13;
constexpr gpio_num_t kSpeakerPinWs = GPIO_NUM_14;
constexpr gpio_num_t kSpeakerPinSd = GPIO_NUM_1;

constexpr gpio_num_t kButtonBoot = GPIO_NUM_0;

constexpr gpio_num_t kDisplayBacklightPin = GPIO_NUM_11;
constexpr gpio_num_t kDisplayMosiPin = GPIO_NUM_17;
constexpr gpio_num_t kDisplayClkPin = GPIO_NUM_16;
constexpr gpio_num_t kDisplayDcPin = GPIO_NUM_12;
constexpr gpio_num_t kDisplayRstPin = GPIO_NUM_21;
constexpr gpio_num_t kDisplayCsPin = GPIO_NUM_15;

constexpr gpio_num_t kWs2812LedPin = GPIO_NUM_41;

constexpr auto kDisplaySpiMode = 0;
constexpr uint32_t kDisplayWidth = 240;
constexpr uint32_t kDisplayHeight = 240;
constexpr bool kDisplayMirrorX = false;
constexpr bool kDisplayMirrorY = false;
constexpr bool kDisplayInvertColor = true;
constexpr bool kDisplaySwapXY = false;
constexpr auto kDisplayRgbElementOrder = LCD_RGB_ELEMENT_ORDER_RGB;
// 串口引脚定义
constexpr gpio_num_t kSerialTxPin = GPIO_NUM_6;  // 串口发送引脚
constexpr gpio_num_t kSerialRxPin = GPIO_NUM_7;  // 串口接收引脚
const long kRpiBaudRate = 115200;
HardwareSerial customSerial(2);  // 使用UART2作为自定义串口
auto g_audio_output_device = std::make_shared<ai_vox::AudioOutputDeviceI2sStd>(kSpeakerPinSck, kSpeakerPinWs, kSpeakerPinSd);
button_handle_t g_button_boot_handle = nullptr;

std::unique_ptr<Display> g_display;
auto g_observer = std::make_shared<ai_vox::Observer>();

bool g_led_on = false;
led_strip_handle_t g_led_strip;

void InitDisplay() {
  printf("init display\n");
  pinMode(kDisplayBacklightPin, OUTPUT);
  analogWrite(kDisplayBacklightPin, 255);

  spi_bus_config_t buscfg{
      .mosi_io_num = kDisplayMosiPin,
      .miso_io_num = GPIO_NUM_NC,
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

  esp_lcd_panel_io_spi_config_t io_config = {};
  io_config.cs_gpio_num = kDisplayCsPin;
  io_config.dc_gpio_num = kDisplayDcPin;
  io_config.spi_mode = kDisplaySpiMode;
  io_config.pclk_hz = 40 * 1000 * 1000;
  io_config.trans_queue_depth = 10;
  io_config.lcd_cmd_bits = 8;
  io_config.lcd_param_bits = 8;
  ESP_ERROR_CHECK(esp_lcd_new_panel_io_spi(SPI3_HOST, &io_config, &panel_io));

  esp_lcd_panel_dev_config_t panel_config = {};
  panel_config.reset_gpio_num = kDisplayRstPin;
  panel_config.rgb_ele_order = kDisplayRgbElementOrder;
  panel_config.bits_per_pixel = 16;
  ESP_ERROR_CHECK(esp_lcd_new_panel_st7789(panel_io, &panel_config, &panel));

  esp_lcd_panel_reset(panel);

  esp_lcd_panel_init(panel);
  esp_lcd_panel_invert_color(panel, kDisplayInvertColor);
  esp_lcd_panel_swap_xy(panel, kDisplaySwapXY);
  esp_lcd_panel_mirror(panel, kDisplayMirrorX, kDisplayMirrorY);

  g_display = std::make_unique<Display>(panel_io, panel, kDisplayWidth, kDisplayHeight, 0, 0, kDisplayMirrorX, kDisplayMirrorY, kDisplaySwapXY);
  g_display->Start();
}

void InitLed() {
  printf("init led\n");

  // LED strip general initialization, according to your led board design
  led_strip_config_t strip_config = {.strip_gpio_num = kWs2812LedPin,  // The GPIO that connected to the LED strip's data line
                                     .max_leds = 1,                    // The number of LEDs in the strip,
                                     .led_model = LED_MODEL_WS2812,    // LED strip model
                                     .color_component_format = LED_STRIP_COLOR_COMPONENT_FMT_GRB,  // The color order of the strip: GRB
                                     .flags = {
                                         .invert_out = false,  // don't invert the output signal
                                     }};

  // LED strip backend configuration: RMT
  led_strip_rmt_config_t rmt_config = {.clk_src = RMT_CLK_SRC_DEFAULT,     // different clock source can lead to different power consumption
                                       .resolution_hz = 10 * 1000 * 1000,  // RMT counter clock frequency
                                       .mem_block_symbols = 0,             // the memory block size used by the RMT channel
                                       .flags = {
                                           .with_dma = 0,  // Using DMA can improve performance when driving more LEDs
                                       }};
  ESP_ERROR_CHECK(led_strip_new_rmt_device(&strip_config, &rmt_config, &g_led_strip));
  ESP_ERROR_CHECK(led_strip_clear(g_led_strip));
}

#ifdef PRINT_HEAP_INFO_INTERVAL
void PrintMemInfo() {
  if (heap_caps_get_total_size(MALLOC_CAP_SPIRAM) > 0) {
    const auto total_size = heap_caps_get_total_size(MALLOC_CAP_SPIRAM);
    const auto free_size = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
    const auto min_free_size = heap_caps_get_minimum_free_size(MALLOC_CAP_SPIRAM);
    printf("SPIRAM total size: %zu B (%zu KB), free size: %zu B (%zu KB), minimum free size: %zu B (%zu KB)\n",
           total_size,
           total_size >> 10,
           free_size,
           free_size >> 10,
           min_free_size,
           min_free_size >> 10);
  }

  if (heap_caps_get_total_size(MALLOC_CAP_INTERNAL) > 0) {
    const auto total_size = heap_caps_get_total_size(MALLOC_CAP_INTERNAL);
    const auto free_size = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
    const auto min_free_size = heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL);
    printf("IRAM total size: %zu B (%zu KB), free size: %zu B (%zu KB), minimum free size: %zu B (%zu KB)\n",
           total_size,
           total_size >> 10,
           free_size,
           free_size >> 10,
           min_free_size,
           min_free_size >> 10);
  }

  if (heap_caps_get_total_size(MALLOC_CAP_DEFAULT) > 0) {
    const auto total_size = heap_caps_get_total_size(MALLOC_CAP_DEFAULT);
    const auto free_size = heap_caps_get_free_size(MALLOC_CAP_DEFAULT);
    const auto min_free_size = heap_caps_get_minimum_free_size(MALLOC_CAP_DEFAULT);
    printf("DRAM total size: %zu B (%zu KB), free size: %zu B (%zu KB), minimum free size: %zu B (%zu KB)\n",
           total_size,
           total_size >> 10,
           free_size,
           free_size >> 10,
           min_free_size,
           min_free_size >> 10);
  }
}
#endif

void PlayMp3(const uint8_t* data, size_t size) {
  auto ret = esp_mp3_dec_register();
  if (ret != ESP_AUDIO_ERR_OK) {
    printf("Failed to register mp3 decoder: %d\n", ret);
    abort();
  }

  esp_audio_simple_dec_handle_t decoder = nullptr;
  esp_audio_simple_dec_cfg_t audio_dec_cfg{
      .dec_type = ESP_AUDIO_SIMPLE_DEC_TYPE_MP3,
      .dec_cfg = nullptr,
      .cfg_size = 0,
  };
  ret = esp_audio_simple_dec_open(&audio_dec_cfg, &decoder);
  if (ret != ESP_AUDIO_ERR_OK) {
    printf("Failed to open mp3 decoder: %d\n", ret);
    abort();
  }
  g_audio_output_device->OpenOutput(16000);

  esp_audio_simple_dec_raw_t raw = {
      .buffer = const_cast<uint8_t*>(data),
      .len = size,
      .eos = true,
      .consumed = 0,
      .frame_recover = ESP_AUDIO_SIMPLE_DEC_RECOVERY_NONE,
  };

  uint8_t* frame_data = (uint8_t*)malloc(4096);
  esp_audio_simple_dec_out_t out_frame = {
      .buffer = frame_data,
      .len = 4096,
      .needed_size = 0,
      .decoded_size = 0,
  };

  while (raw.len > 0) {
    const auto ret = esp_audio_simple_dec_process(decoder, &raw, &out_frame);
    if (ret == ESP_AUDIO_ERR_BUFF_NOT_ENOUGH) {
      // Handle output buffer not enough case
      out_frame.buffer = reinterpret_cast<uint8_t*>(realloc(out_frame.buffer, out_frame.needed_size));
      if (out_frame.buffer == nullptr) {
        break;
      }
      out_frame.len = out_frame.needed_size;
      continue;
    }

    if (ret != ESP_AUDIO_ERR_OK) {
      break;
    }

    g_audio_output_device->Write(reinterpret_cast<int16_t*>(out_frame.buffer), out_frame.decoded_size >> 1);
    raw.len -= raw.consumed;
    raw.buffer += raw.consumed;
  }

  free(frame_data);

  g_audio_output_device->CloseOutput();
  esp_audio_simple_dec_close(decoder);
  esp_audio_dec_unregister(ESP_AUDIO_TYPE_MP3);
}

void ConfigureWifi() {
  printf("configure wifi\n");
  auto wifi_configurator = std::make_unique<WifiConfigurator>(WiFi, kSmartConfigType);

  ESP_ERROR_CHECK(iot_button_register_cb(
      g_button_boot_handle,
      BUTTON_PRESS_DOWN,
      nullptr,
      [](void*, void* data) {
        printf("boot button pressed\n");
        static_cast<WifiConfigurator*>(data)->StartSmartConfig();
      },
      wifi_configurator.get()));

  g_display->ShowStatus("网络配置中");
  PlayMp3(kNotification0mp3, sizeof(kNotification0mp3));

#if defined(WIFI_SSID) && defined(WIFI_PASSWORD)
  printf("wifi config start with wifi: %s, %s\n", WIFI_SSID, WIFI_PASSWORD);
  wifi_configurator->Start(WIFI_SSID, WIFI_PASSWORD);
#else
  printf("wifi config start\n");
  wifi_configurator->Start();
  
  // 尝试从树莓派获取WiFi凭据
  bool connected = false;
  unsigned long request_start = millis();
  unsigned long last_request_time = 0;
  
  while (millis() - request_start < 20000 && !connected) { // 总共等待20秒
    // 每2秒发送一次请求
    if (millis() - last_request_time >= 2000) {
      printf("尝试从树莓派获取WiFi凭据\n");
      String wifi_request = "{\"event\": \"wifi_get\"}";
      customSerial.println(wifi_request);
      printf("Requesting WiFi credentials from Pi: %s\n", wifi_request.c_str());
      last_request_time = millis();
    }
    
    if (customSerial.available()) {
      String response = customSerial.readStringUntil('\n');
      response.trim();
      printf("收到树莓派响应: %s\n", response.c_str());
      
      // 尝试解析JSON响应
      StaticJsonDocument<256> doc;
      DeserializationError error = deserializeJson(doc, response);
      
      if (!error && doc.containsKey("ssid") && !doc["ssid"].as<String>().isEmpty()) {
        // 从响应中提取SSID和密码
        const char* ssid = doc["ssid"];
        const char* password = doc["password"];
        
        if (ssid && password) {
          printf("从树莓派获取到WiFi凭据: SSID=%s, Password=%s\n", ssid, password);
          g_display->ShowStatus("获取WiFi凭据成功");
          
          // 尝试使用获取到的凭据连接WiFi
          WiFi.begin(ssid, password);
          int retry_count = 0;
          while (WiFi.status() != WL_CONNECTED && retry_count < 15) {
            delay(1000);
            retry_count++;
            printf("使用树莓派提供的凭据连接中... (%d/15)\n", retry_count);
            g_display->ShowStatus("连接WiFi中...");
          }
          
          if (WiFi.status() == WL_CONNECTED) {
            printf("WiFi连接成功！IP: %s\n", WiFi.localIP().toString().c_str());
            g_display->ShowStatus("WiFi连接成功");
            connected = true;
            break; // 跳出等待树莓派响应的循环
          } else {
            printf("使用树莓派提供的凭据连接失败\n");
          }
        }
      }
    }
    
    delay(100); // 短暂延时避免CPU占用过高
  }
  
  // 如果通过树莓派获取凭据并连接成功，则不再等待WifiConfigurator状态变化
  if (connected) {
    printf("通过树莓派提供的凭据完成WiFi配置\n");
    g_display->ShowStatus("网络已连接");
    String wifi_set = "{\"event\": \"wifi_set\"}";
    customSerial.println(wifi_set);
    printf("-> Sent wifi set command: %s\n", wifi_set.c_str());
    iot_button_unregister_cb(g_button_boot_handle, BUTTON_PRESS_DOWN, nullptr);
    return; // 直接返回，跳过后续的状态等待
  } else {
    printf("未能从树莓派获取有效WiFi凭据，继续使用默认配置流程\n");
  }
#endif

  while (true) {
    const auto state = wifi_configurator->WaitStateChanged();
    if (state == WifiConfigurator::State::kConnecting) {
      printf("wifi connecting\n");
      g_display->ShowStatus("网络连接中");
    } else if (state == WifiConfigurator::State::kSmartConfiguring) {
      printf("wifi smart configuring\n");
      g_display->ShowStatus("配网模式");
      PlayMp3(kNetworkConfigModeMp3, sizeof(kNetworkConfigModeMp3));
    } else if (state == WifiConfigurator::State::kFinished) {
      break;
    }
  }

  iot_button_unregister_cb(g_button_boot_handle, BUTTON_PRESS_DOWN, nullptr);

  printf("wifi connected\n");
  printf("- mac address: %s\n", WiFi.macAddress().c_str());
  printf("- bssid:       %s\n", WiFi.BSSIDstr().c_str());
  printf("- ssid:        %s\n", WiFi.SSID().c_str());
  printf("- ip:          %s\n", WiFi.localIP().toString().c_str());
  printf("- gateway:     %s\n", WiFi.gatewayIP().toString().c_str());
  printf("- subnet mask: %s\n", WiFi.subnetMask().toString().c_str());

  g_display->ShowStatus("网络已连接");
  PlayMp3(kNetworkConnectedMp3, sizeof(kNetworkConnectedMp3));
}

void InitMcpTools() {
  auto& engine = ai_vox::Engine::GetInstance();
  engine.AddMcpTool("self.audio_speaker.set_volume",         // tool name
                    "Set the volume of the audio speaker.",  // tool description
                    {
                        {
                            "volume",  // parameter name

                            ai_vox::ParamSchema<int64_t>{
                                // parameter type can be bool, std::string or int64_t
                                .default_value = std::nullopt,  // default value, set to std::nullopt if not specified
                                .min = 0,                       // minimum value, set to std::nullopt if not specified
                                .max = 100,                     // maximum value, set to std::nullopt if not specified
                            },
                        },
                        // add more parameter schema as needed
                    }  // parameter schema
  );

  engine.AddMcpTool("self.audio_speaker.get_volume",         // tool name
                    "Get the volume of the audio speaker.",  // tool description
                    {
                        // empty
                    }  // parameter schema
  );

  engine.AddMcpTool("self.led.set",                                           // tool name
                    "Set the state of the LED, true for on, false for off.",  // tool description
                    {
                        {
                            "state",  // parameter name
                            ai_vox::ParamSchema<bool>{
                                // parameter type can be bool, std::string or int64_t
                                .default_value = std::nullopt,  // default value, set to std::nullopt if not specified
                            },                                  // parameter type
                        },
                        // add more parameter schema as needed
                    }  // parameter schema
  );

  engine.AddMcpTool("self.led.get",                                           // tool name
                    "Get the state of the LED, true for on, false for off.",  // tool description
                    {
                        // empty
                    }  // parameter schema
  );
}
}  // namespace

void setup() {
  Serial.begin(115200);
  customSerial.begin(kRpiBaudRate, SERIAL_8N1, kSerialRxPin, kSerialTxPin);
  printf("setup\n");
  
  InitLed();

  printf("init button\n");
  const button_config_t btn_cfg = {
      .long_press_time = 1000,
      .short_press_time = 50,
  };

  const button_gpio_config_t gpio_cfg = {
      .gpio_num = kButtonBoot,
      .active_level = 0,
      .enable_power_save = false,
      .disable_pull = false,
  };

  ESP_ERROR_CHECK(iot_button_new_gpio_device(&btn_cfg, &gpio_cfg, &g_button_boot_handle));

  InitDisplay();

  if (heap_caps_get_total_size(MALLOC_CAP_SPIRAM) == 0) {
    g_display->SetChatMessage(Display::Role::kSystem, "No SPIRAM available, please check your board.");
    while (true) {
      printf("No SPIRAM available, please check your board.\n");
      delay(1000);
    }
  }

  g_display->ShowStatus("初始化");
  ConfigureWifi();
  InitMcpTools();

  auto audio_input_device = std::make_shared<AudioInputDeviceSph0645>(kMicPinSck, kMicPinWs, kMicPinSd);
  auto& ai_vox_engine = ai_vox::Engine::GetInstance();
  ai_vox_engine.SetObserver(g_observer);
  ai_vox_engine.SetOtaUrl("https://api.tenclass.net/xiaozhi/ota/");
  ai_vox_engine.ConfigWebsocket("wss://api.tenclass.net/xiaozhi/v1/",
                                {
                                    {"Authorization", "Bearer test-token"},
                                });
  printf("engine starting\n");
  g_display->ShowStatus("AI引擎启动中");

  ai_vox_engine.Start(audio_input_device, g_audio_output_device);

  printf("engine started\n");

  ESP_ERROR_CHECK(iot_button_register_cb(
      g_button_boot_handle,
      BUTTON_PRESS_DOWN,
      nullptr,
      [](void* button_handle, void* usr_data) {
        printf("boot button pressed\n");
        ai_vox::Engine::GetInstance().Advance();
      },
      nullptr));

  g_display->ShowStatus("AI引擎已启动");
}

void loop() {
#ifdef PRINT_HEAP_INFO_INTERVAL
  static uint32_t s_print_heap_info_time = 0;
  if (s_print_heap_info_time == 0 || millis() - s_print_heap_info_time >= PRINT_HEAP_INFO_INTERVAL) {
    s_print_heap_info_time = millis();
    PrintMemInfo();
  }
#endif

  // 检查串口是否有数据可读
  if (customSerial.available()) {
    String response = customSerial.readStringUntil('\n');
    response.trim();
    printf("收到串口数据: %s\n", response.c_str());
    
    // 尝试解析JSON响应
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, response);
    
    if (!error && doc.containsKey("event") && doc["event"].as<String>() == "ask") {
      // 当收到{"event": "ask"}后，发送{"event": "wifi_set"}
      delay(1000);
      String wifi_set = "{\"event\": \"wifi_set\"}";
      customSerial.println(wifi_set);
      printf("-> 发送wifi_set命令: %s\n", wifi_set.c_str());
    }
  }

  auto& engine = ai_vox::Engine::GetInstance();

  const auto events = g_observer->PopEvents();

  for (auto& event : events) {
    if (auto text_received_event = std::get_if<ai_vox::TextReceivedEvent>(&event)) {
      printf("on text received: %s\n", text_received_event->content.c_str());
    } else if (auto activation_event = std::get_if<ai_vox::ActivationEvent>(&event)) {
      printf("activation code: %s, message: %s\n", activation_event->code.c_str(), activation_event->message.c_str());
      g_display->ShowStatus("激活设备");
      g_display->SetChatMessage(Display::Role::kSystem, activation_event->message);
    } else if (auto state_changed_event = std::get_if<ai_vox::StateChangedEvent>(&event)) {
      switch (state_changed_event->new_state) {
        case ai_vox::ChatState::kIdle: {
          printf("Idle\n");
          break;
        }
        case ai_vox::ChatState::kInitted: {
          printf("Initted\n");
          g_display->ShowStatus("初始化完成");
          break;
        }
        case ai_vox::ChatState::kLoading: {
          printf("Loading...\n");
          g_display->ShowStatus("加载协议中");
          break;
        }
        case ai_vox::ChatState::kLoadingFailed: {
          printf("Loading failed, please retry\n");
          g_display->ShowStatus("加载协议失败，请重试");
          break;
        }
        case ai_vox::ChatState::kStandby: {
          printf("Standby\n");
          g_display->ShowStatus("待命");
          break;
        }
        case ai_vox::ChatState::kConnecting: {
          printf("Connecting...\n");
          g_display->ShowStatus("连接中...");
          break;
        }
        case ai_vox::ChatState::kListening: {
          printf("Listening...\n");
          g_display->ShowStatus("聆听中");
          break;
        }
        case ai_vox::ChatState::kSpeaking: {
          printf("Speaking...\n");
          g_display->ShowStatus("说话中");
          break;
        }
        default: {
          break;
        }
      }
    } else if (auto emotion_event = std::get_if<ai_vox::EmotionEvent>(&event)) {
      printf("emotion: %s\n", emotion_event->emotion.c_str());
      g_display->SetEmotion(emotion_event->emotion);
    } else if (auto chat_message_event = std::get_if<ai_vox::ChatMessageEvent>(&event)) {
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
        }    
    
     else if (auto mcp_tool_call_event = std::get_if<ai_vox::McpToolCallEvent>(&event)) {
      printf("on mcp tool call: %s\n", mcp_tool_call_event->ToString().c_str());

      if ("self.audio_speaker.set_volume" == mcp_tool_call_event->name) {
        const auto volume_ptr = mcp_tool_call_event->param<int64_t>("volume");
        if (volume_ptr != nullptr) {
          printf("on mcp tool call: self.audio_speaker.set_volume, volume: %" PRId64 "\n", *volume_ptr);
          g_audio_output_device->set_volume(*volume_ptr);
          engine.SendMcpCallResponse(mcp_tool_call_event->id, true);
        } else {
          engine.SendMcpCallError(mcp_tool_call_event->id, "Missing valid argument: volume");}
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
    
  }
}
