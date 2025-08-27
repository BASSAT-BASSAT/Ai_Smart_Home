# Include required libraries
#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>
#include "LiquidCrystal_I2C.h"
#include <ESP32Servo.h>

# Load WiFi and MQTT credentials from config.h
 #include "config.h"

const char* VOICE_LIGHTS_TOPIC = "home/lights/voice";
const char* LIGHT_SENSOR_TOPIC = "esp32/sensors/light";
const char* RAIN_SENSOR_TOPIC = "esp32/sensors/rain";
const char* DOOR_EVENT_TOPIC = "esp32/events/door";

# Define hardware pins
#define LCD_SDA_PIN 21
#define LCD_SCL_PIN 22
#define DOOR_PIR_PIN 33
#define SERVO_PIN 13
#define VOICE_LED_1_PIN 12
#define VOICE_LED_2_PIN 14
#define LDR_PIN 34
#define NIGHT_LIGHT_LED_PIN 27
#define RAIN_SENSOR_PIN 32

# Initialize global objects
WiFiClient espClient;
PubSubClient client(espClient);
LiquidCrystal_I2C lcd(0x27, 16, 2);
Servo doorServo;

# Track door state and LCD message
enum DoorState { CLOSED, OPEN };
DoorState currentDoorState = CLOSED;
String currentLcdMessage = "";
int lightThreshold = 1000;
unsigned long lastSensorPublishTime = 0;
const long sensorPublishInterval = 30000;

// Main setup: initialize hardware and connect to WiFi/MQTT
void setup() {
  Serial.begin(115200);
  lcd.init();
  lcd.backlight();
  pinMode(DOOR_PIR_PIN, INPUT);
  pinMode(VOICE_LED_1_PIN, OUTPUT);
  pinMode(VOICE_LED_2_PIN, OUTPUT);
  pinMode(LDR_PIN, INPUT);
  pinMode(NIGHT_LIGHT_LED_PIN, OUTPUT);
  pinMode(RAIN_SENSOR_PIN, INPUT);
  
  doorServo.attach(SERVO_PIN);
  doorServo.write(0);

  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);

  Serial.println("\nFull System Ready. Logging to Database.");
}

  // Main loop: read sensors, control devices, and publish data
void loop() {
  if (!client.connected()) { reconnect(); }
  client.loop();

  
    // Read sensor values
  bool isMotionDetected = (digitalRead(DOOR_PIR_PIN) == LOW);
  int lightValue = analogRead(LDR_PIN);
  bool isRaining = (digitalRead(RAIN_SENSOR_PIN) == LOW);

  
    // Control door servo based on motion
  if (isMotionDetected && currentDoorState == CLOSED) {
    doorServo.write(90);
    currentDoorState = OPEN;
    
    Serial.println("Publishing door open event (PIR).");
    client.publish(DOOR_EVENT_TOPIC, "opened_by_pir");
  } 
  else if (!isMotionDetected && currentDoorState == OPEN) {
    doorServo.write(0);
    currentDoorState = CLOSED;
  }

  
    // Control night light based on light sensor
  if (lightValue < lightThreshold) {
    digitalWrite(NIGHT_LIGHT_LED_PIN, HIGH);
  } else {
    digitalWrite(NIGHT_LIGHT_LED_PIN, LOW);
  }

  
    // Update LCD message based on priority
  String newMessage = "";
  if (isMotionDetected) { newMessage = "Welcome Home!"; }
  else if (isRaining) { newMessage = "It's Raining!"; }
  else { newMessage = (lightValue < lightThreshold) ? "Status: Dark" : "Status: Bright"; }

  if (currentLcdMessage != newMessage) {
    lcd.clear();
    lcd.print(newMessage);
    currentLcdMessage = newMessage;
  }

  
    // Periodically publish sensor data to MQTT
  if (millis() - lastSensorPublishTime > sensorPublishInterval) {
    lastSensorPublishTime = millis(); // Reset the timer

    // Publish Light Sensor Data
    String lightStatus = (lightValue < lightThreshold) ? "dark" : "bright";
    client.publish(LIGHT_SENSOR_TOPIC, lightStatus.c_str());
    Serial.printf("Published light status: %s\n", lightStatus.c_str());

    // Publish Rain Sensor Data
    String rainStatus = isRaining ? "raining" : "dry";
    client.publish(RAIN_SENSOR_TOPIC, rainStatus.c_str());
    Serial.printf("Published rain status: %s\n", rainStatus.c_str());
  }
}


// Handle incoming MQTT messages for light control
void callback(char* topic, byte* payload, unsigned int length) {
  String message;
  for (int i = 0; i < length; i++) { message += (char)payload[i]; }
  
  if (String(topic) == VOICE_LIGHTS_TOPIC) {
    Serial.printf("Received voice command: %s\n", message.c_str());
    if (message == "on1") digitalWrite(VOICE_LED_1_PIN, HIGH);
    if (message == "off1") digitalWrite(VOICE_LED_1_PIN, LOW);
    if (message == "on2") digitalWrite(VOICE_LED_2_PIN, HIGH);
    if (message == "off2") digitalWrite(VOICE_LED_2_PIN, LOW);
  }
}

// Connect to WiFi using credentials
void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

// Reconnect to MQTT broker if disconnected
void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    if (client.connect("ESP32_FullSystem_Client")) {
      Serial.println("connected");
      client.subscribe(VOICE_LIGHTS_TOPIC);
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}