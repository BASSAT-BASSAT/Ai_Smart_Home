import paho.mqtt.client as mqtt
import os
import time
import json
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from supabase import create_client, Client
from langchain.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from datetime import datetime, timezone

# MQTT and Supabase configuration
MQTT_BROKER = "mosquitto"
MQTT_PORT = 1883
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# MQTT topics for communication
NATURAL_COMMAND_TOPIC = "home/commands/natural"
VOICE_LIGHTS_TOPIC = "home/lights/voice"
AI_RESPONSE_TOPIC = "home/ai/response"

# Initialize Supabase and MQTT clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
print("Supabase & MQTT clients initialized.")

# Format timestamps for user-friendly output
def format_timestamp(timestamp_str: str) -> str:
    """Converts a Supabase timestamp into a human-friendly string."""
    try:
        # This is the corrected, more flexible timestamp parsing logic
        # It handles cases where microseconds might have trailing zeros trimmed.
        if '.' in timestamp_str and '+' in timestamp_str:
            time_part, tz_part = timestamp_str.split('+')
            time_part = time_part.ljust(26, '0') # Pad with zeros to ensure 6 microsecond digits
            timestamp_str = f"{time_part}+{tz_part}"
        
        timestamp = datetime.fromisoformat(timestamp_str).astimezone(timezone.utc)
        
        absolute_time = timestamp.strftime("%B %d at %I:%M %p UTC")
        time_since = datetime.now(timezone.utc) - timestamp
        days = time_since.days
        hours, remainder = divmod(time_since.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        
        if days > 1: relative_time = f"{days} days ago"
        elif days == 1: relative_time = "1 day ago"
        elif hours > 1: relative_time = f"{hours} hours ago"
        elif hours == 1: relative_time = "1 hour ago"
        elif minutes > 1: relative_time = f"{minutes} minutes ago"
        else: relative_time = "just a moment ago"
        return f"on {absolute_time} (which was {relative_time})."
    except Exception as e:
        return f"at an unknown time due to a timestamp parsing error: {e}"

# Tool: Turn on a specific light
@tool
def turn_on_light(light_number: int) -> str:
    """Turns on a specific voice-controlled LED light."""
    if light_number not in [1, 2]: return "Error: Invalid light number."
    mqtt_payload = f"on{light_number}"; client.publish(VOICE_LIGHTS_TOPIC, mqtt_payload)
    log_data = {"event_source": f"voice_led_{light_number}_on"}; supabase.table('access_logs').insert(log_data).execute()
    return f"OK. I've turned on voice light {light_number}."

# Tool: Turn off a specific light
@tool
def turn_off_light(light_number: int) -> str:
    """Turns off a specific voice-controlled LED light."""
    if light_number not in [1, 2]: return "Error: Invalid light number."
    mqtt_payload = f"off{light_number}"; client.publish(VOICE_LIGHTS_TOPIC, mqtt_payload)
    log_data = {"event_source": f"voice_led_{light_number}_off"}; supabase.table('access_logs').insert(log_data).execute()
    return f"OK. I've turned off voice light {light_number}."

@tool
def get_environmental_sensor_history(sensor_type: str, sensor_value: str, find_first: bool = False) -> str:
    """Finds the first or last time an ENVIRONMENTAL SENSOR was in a certain state (e.g., when it was 'dark')."""
    if sensor_type not in ["light", "rain"]: return "Error: Invalid sensor type."
    if sensor_value not in ["dark", "bright", "raining", "dry"]: return "Error: Invalid sensor value."
    
    is_ascending = find_first
    response = supabase.table('sensor_readings').select('created_at').eq('sensor_type', sensor_type).eq('sensor_value', sensor_value).order('created_at', desc=not is_ascending).limit(1).execute()
    
    if response.data:
        return f"The {'first' if find_first else 'last'} time the status was '{sensor_value}' was {format_timestamp(response.data[0]['created_at'])}"
    else:
        return f"I have no record of the status ever being '{sensor_value}'."

@tool
def get_device_action_history(event_source: str, find_first: bool = False) -> str:
    """Finds the first or last time a specific DEVICE ACTION occurred (e.g., when a light was turned on). Also used to check for current events."""
    valid_sources = ["opened_by_pir", "voice_led_1_on", "voice_led_1_off", "voice_led_2_on", "voice_led_2_off"]
    if event_source not in valid_sources: return f"Error: I don't know about the event '{event_source}'."

    is_ascending = find_first
    response = supabase.table('access_logs').select('created_at').eq('event_source', event_source).order('created_at', desc=not is_ascending).limit(1).execute()
    
    if response.data:
        timestamp_str = response.data[0]['created_at']
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        time_since_seconds = (datetime.now(timezone.utc) - timestamp).total_seconds()

        if not find_first and time_since_seconds < 30:
            return f"Yes, the event '{event_source}' happened just {int(time_since_seconds)} seconds ago."

        return f"The {'first' if find_first else 'last'} time the event '{event_source}' occurred was {format_timestamp(timestamp_str)}"
    else:
        return f"I have no record of the event '{event_source}' ever happening."

tools = [turn_on_light, turn_off_light, get_environmental_sensor_history, get_device_action_history]
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest")

prompt = ChatPromptTemplate.from_messages([
    ("system", """
        You are an advanced smart home data analyst. Your goal is to answer user questions by intelligently choosing from a set of tools.

        **Tool Guide:**
        1.  `turn_on_light` / `turn_off_light`: Use these for direct commands to control lights.
        2.  `get_environmental_sensor_history`: Use this for questions about an environmental STATE.
            - Keywords: dark, bright, raining, dry.
            - Example: "When was it last dark?" -> `get_environmental_sensor_history(sensor_type='light', sensor_value='dark')`
        3.  `get_device_action_history`: Use this for questions about a DEVICE ACTION.
            - Keywords: light turned on, light turned off, door opened.
            - Example: "When was light 1 turned on?" -> `get_device_action_history(event_source='voice_led_1_on')`
            - Example: "Is there motion at the door now?" -> `get_device_action_history(event_source='opened_by_pir')` The tool is smart enough to handle "now".

        **Your Task:**
        1.  Analyze the user's question.
        2.  Decide if it's a command or a data query.
        3.  If it's a data query, determine if it's about a STATE (use `get_environmental_sensor_history`) or an ACTION (use `get_device_action_history`).
        4.  Determine if the user is asking for the "first" or "last" event. For "first", set `find_first=True`. For "last" or "now", set `find_first=False`.
        5.  Construct the correct `event_source` or `sensor_value` from the user's words based on this mapping:
            - "door opened": 'opened_by_pir'
            - "light one on": 'voice_led_1_on'
            - "light one off": 'voice_led_1_off'
            - "light two on": 'voice_led_2_on'
            - "light two off": 'voice_led_2_off'
        6.  Call the correct tool with the correct parameters.
        7.  Respond in a friendly, conversational way based on the tool's output.
    """),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# MQTT event handlers
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("LangChain Agent Service: Connected!")
        client.subscribe(NATURAL_COMMAND_TOPIC)
    else:
        print("Connection failed")

# Handle incoming MQTT messages and route to agent
def on_message(client, userdata, msg):
    command_text = msg.payload.decode()
    print(f"\n> Command: '{command_text}'")
    try:
        response = agent_executor.invoke({"input": command_text})
        final_answer = response['output']
        print(f"< Agent Answer: {final_answer}")
        client.publish(AI_RESPONSE_TOPIC, final_answer)
    except Exception as e:
        error_message = f"Sorry, an error occurred: {str(e)}"
        print(error_message)
        client.publish(AI_RESPONSE_TOPIC, error_message)

# Main service loop
print("LangChain Agent Service: Starting up...")
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()