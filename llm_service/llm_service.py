import paho.mqtt.client as mqtt
import os
import time
import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from supabase import create_client, Client

## Configuration
MQTT_BROKER = "mosquitto"
MQTT_PORT = 1883
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

## MQTT Topics
# List of all topics the service needs to listen to
TOPICS_TO_SUBSCRIBE = [
    "home/commands/natural",   # For voice commands from the web app
    "esp32/sensors/light",     # For periodic light sensor readings
    "esp32/sensors/rain",      # For periodic rain sensor readings
    "esp32/events/door"        # For instant door open events
]
# Topic this service publishes commands to
VOICE_LIGHTS_TOPIC = "home/lights/voice"

## LangChain & Gemini AI Setup
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest")
prompt = ChatPromptTemplate.from_messages([
    ("system", 
     """
        You are a smart home assistant. Analyze the user's command for controlling lights and convert it into a structured JSON command.
        The available devices are: 'voice_led_1' and 'voice_led_2'. The available actions are: 'turn_on' and 'turn_off'.
        - "bulb one", "light one", "the first light" all refer to 'voice_led_1'.
        - "bulb two", "light two", "the second light" all refer to 'voice_led_2'.
        Your response MUST be a single, valid JSON object with three keys: "device", "action", and "comment".
        If you cannot understand the command, respond with "device": "unknown".
    """),
    ("user", "{input}")
])
chain = prompt | llm

## Supabase Client Setup
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print("Supabase client initialized.")

## MQTT Functions
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("LangChain Service: Successfully connected to MQTT Broker!")
        # Subscribe to all our topics
        for topic in TOPICS_TO_SUBSCRIBE:
            client.subscribe(topic)
            print(f"Subscribed to topic: {topic}")
    else:
        print(f"LangChain Service: Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()
    print(f"\nReceived message on topic '{topic}': {payload}")

    ## Message Routing
    try:
        if topic == "home/commands/natural":
            handle_voice_command(payload)
        
        elif topic == "esp32/sensors/light":
            data = {"sensor_type": "light", "sensor_value": payload}
            supabase.table('sensor_readings').insert(data).execute()
            print(f"Logged to sensor_readings: {data}")

        elif topic == "esp32/sensors/rain":
            data = {"sensor_type": "rain", "sensor_value": payload}
            supabase.table('sensor_readings').insert(data).execute()
            print(f"Logged to sensor_readings: {data}")

        elif topic == "esp32/events/door":
            data = {"event_source": payload} # Payload will be "opened_by_pir"
            supabase.table('access_logs').insert(data).execute()
            print(f"Logged to access_logs: {data}")

    except Exception as e:
        print(f"An error occurred while handling message: {e}")

def handle_voice_command(command_text):
    print("Asking Gemini for analysis...")
    try:
        response = chain.invoke({"input": command_text})
        ai_response_text = response.content.strip()
        
        if ai_response_text.startswith("```json"):
            ai_response_text = ai_response_text[7:-3].strip()
        print(f"Gemini Response: {ai_response_text}")
        
        command_json = json.loads(ai_response_text)
        device = command_json.get("device")
        action = command_json.get("action")
        
        mqtt_payload = ""
        log_data = {}

        if device == "voice_led_1" and action == "turn_on":
            mqtt_payload = "on1"
            log_data = {"event_source": "voice_led_1_on"}
        elif device == "voice_led_1" and action == "turn_off":
            mqtt_payload = "off1"
            log_data = {"event_source": "voice_led_1_off"}
        elif device == "voice_led_2" and action == "turn_on":
            mqtt_payload = "on2"
            log_data = {"event_source": "voice_led_2_on"}
        elif device == "voice_led_2" and action == "turn_off":
            mqtt_payload = "off2"
            log_data = {"event_source": "voice_led_2_off"}

        if mqtt_payload and log_data:
            # Publish command to ESP32
            client.publish(VOICE_LIGHTS_TOPIC, mqtt_payload)
            print(f"Action: Publishing '{mqtt_payload}' to {VOICE_LIGHTS_TOPIC}.")
            # Log the successful command to the database
            supabase.table('access_logs').insert(log_data).execute()
            print(f"Logged to access_logs: {log_data}")
        else:
            print("Action: Intent unknown or not actionable. No command sent.")

    except Exception as e:
        print(f"An error occurred during AI processing: {e}")

## Main script execution
print("LangChain Service: Starting up...")
time.sleep(5) 
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()