# 🏠 Voice AI Home

A full-stack smart home system combining IoT sensors, voice control, AI-powered command parsing, and a modern web dashboard. Built with ESP32, MQTT, LangChain, Gemini AI, Supabase, Docker, and more.

## 🚀 Features

- **IoT ESP32**: Monitors light, rain, and motion; controls LEDs and servo for door; displays status on LCD.
- **Voice Control**: Speak commands via web dashboard, parsed by Gemini AI and executed on devices.
- **AI Service**: LangChain + Gemini interprets natural language and sends structured commands.
- **MQTT Broker**: Reliable messaging between devices and services.
- **Web Dashboard**: Login/signup, voice command, real-time status, built with Supabase and MQTT over WebSockets.
- **Secrets Management**: All credentials stored in `.env` and `config.h` (excluded from git).

## 🧩 Architecture

```
[Web Dashboard] <--MQTT/WebSocket--> [Mosquitto Broker] <--MQTT--> [ESP32 IoT Device]
         |                                      |
         |                                      |
   [Supabase Auth & DB]                [LangChain AI Service]
```

## 🛠️ Setup

### 1. Clone & Configure

```sh
git clone https://github.com/BASSAT-BASSAT/voice_ai_home.git
cd voice_ai_home
```

- Fill in your secrets in `.env` (already set for demo).
- For ESP32, copy `iot_C_code/config.h.template` to `config.h` and add your WiFi/MQTT credentials.

### 2. Start Backend Services

```sh
docker-compose up --build
```

- Mosquitto broker runs on ports `1883` (MQTT) and `9001` (WebSocket).
- LangChain AI service connects to Gemini and Supabase using your secrets.

### 3. Flash ESP32

- Open `iot_C_code/iot_C_code.ino` in Arduino IDE.
- Ensure `config.h` is present with your credentials.
- Upload to your ESP32.

### 4. Web Dashboard

- Open `webapp/login.html` in your browser.
- Sign up or log in with Supabase.
- Use the dashboard to send voice commands and view status.

## 🔒 Secrets & Environment

- `.env`: Stores API keys and URLs for Docker and backend.
- `iot_C_code/config.h`: Stores WiFi and MQTT credentials for ESP32 (excluded from git).
- `.gitignore` ensures secrets are not committed.

## 📡 MQTT Topics

- `home/commands/natural`: Voice commands from web to AI service.
- `home/lights/voice`: AI service to ESP32 for LED control.
- `esp32/sensors/light`, `esp32/sensors/rain`, `esp32/events/door`: ESP32 sensor data to backend.

## 🧠 AI Command Parsing

- Gemini AI converts natural language (e.g., "turn on the first light") to JSON commands.
- Only recognized devices (`voice_led_1`, `voice_led_2`) and actions (`turn_on`, `turn_off`) are allowed.

## 📝 Contributing

Pull requests and issues welcome! See the code for comments and extension points.

## 📄 License

MIT
