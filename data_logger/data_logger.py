# In data_logger/data_logger.py

import paho.mqtt.client as mqtt
import os
from supabase import create_client, Client
import json

# Configuration
MQTT_BROKER = "mosquitto"
MQTT_PORT = 1883
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Topics the ESP32 is publishing to 
LIGHT_SENSOR_TOPIC = "esp32/sensors/light"
RAIN_SENSOR_TOPIC = "esp32/sensors/rain"
DOOR_EVENT_TOPIC = "esp32/events/door"

#Initialization
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Data Logger: Supabase client initialized.")
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    print("Data Logger: MQTT client initialized.")
except Exception as e:
    print(f"Error during initialization: {e}")
    exit(1)


# MQTT Callbacks
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Data Logger: Connected to MQTT Broker!")
        # Subscribe to all the topics from the ESP32
        client.subscribe(LIGHT_SENSOR_TOPIC)
        client.subscribe(RAIN_SENSOR_TOPIC)
        client.subscribe(DOOR_EVENT_TOPIC)
        print(f"Data Logger: Subscribed to {LIGHT_SENSOR_TOPIC}, {RAIN_SENSOR_TOPIC}, and {DOOR_EVENT_TOPIC}")
    else:
        print(f"Data Logger: Failed to connect, return code {rc}\n")

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    print(f"Data Logger: Received message on topic '{msg.topic}': {payload}")

    try:
        if msg.topic == LIGHT_SENSOR_TOPIC:
            log_data = {'sensor_type': 'light', 'sensor_value': payload}
            supabase.table('sensor_readings').insert(log_data).execute()
            print(f"Data Logger: Logged to 'sensor_readings': {log_data}")

        elif msg.topic == RAIN_SENSOR_TOPIC:
            log_data = {'sensor_type': 'rain', 'sensor_value': payload}
            supabase.table('sensor_readings').insert(log_data).execute()
            print(f"Data Logger: Logged to 'sensor_readings': {log_data}")

        elif msg.topic == DOOR_EVENT_TOPIC:
            log_data = {'event_source': payload}
            supabase.table('access_logs').insert(log_data).execute()
            print(f"Data Logger: Logged to 'access_logs': {log_data}")

    except Exception as e:
        print(f"Data Logger: Failed to insert data into Supabase. Error: {e}")


# Main Execution
print("Data Logger Service: Starting up...")
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Run the client loop forever
client.loop_forever()