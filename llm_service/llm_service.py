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

MQTT_BROKER = "mosquitto"


# MQTT and Supabase configuration
MQTT_BROKER = "mosquitto"
MQTT_PORT = 1883
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

NATURAL_COMMAND_TOPIC = "home/commands/natural"
# MQTT topics for communication
NATURAL_COMMAND_TOPIC = "home/commands/natural"
VOICE_LIGHTS_TOPIC = "home/lights/voice"
AI_RESPONSE_TOPIC = "home/ai/response"

# Initialize Supabase and MQTT clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
print("Supabase & MQTT clients initialized.")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
print("Supabase & MQTT clients initialized.")

# Format timestamps for user-friendly output
def format_timestamp(timestamp_str: str) -> str:
def format_timestamp(timestamp_str: str) -> str:
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
    else: relative_time = "just now"
    return f"on {absolute_time} (which was {relative_time})."


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

# Tool: Query database for historical sensor or access log data
@tool
def query_database(table_name: str, filters: dict, order_by: str = "created_at", ascending: bool = False, limit: int = 1) -> str:
    """
    Queries the database to find historical data. Use this for ANY question about past events.
    `table_name` must be either 'sensor_readings' or 'access_logs'.
    `filters` is a dictionary of columns and values to match.
    `order_by` is the column to sort by, usually 'created_at'.
    `ascending` should be True for 'first' events and False for 'last' events.
    """
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
            print(f"DATABASE TOOL: Successfully parsed string filter into dictionary.")
        except json.JSONDecodeError:
            return "Error: The provided filter string was not valid JSON."

    print(f"DATABASE TOOL: Querying table '{table_name}' with filters: {filters}")
    try:
        is_descending = not ascending
        query = supabase.table(table_name).select('created_at').order(order_by, desc=is_descending).limit(limit)
        
        for column, value in filters.items():
            query = query.eq(column, value)
        
        response = query.execute()

        if response.data:
            timestamp_str = response.data[0]['created_at']
            return f"I found a record for that event. It occurred {format_timestamp(timestamp_str)}"
        else:
            return f"Sorry, I have no records matching those criteria."
    except Exception as e:
        return f"Database error: {str(e)}"



# Set up LangChain agent with tools and prompt
tools = [turn_on_light, turn_off_light, query_database]
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest")
prompt = ChatPromptTemplate.from_messages([
    """
        You are an advanced smart home assistant. You have tools to control lights and a powerful tool to query a database for historical information.

        DATABASE SCHEMA:
        1. `sensor_readings` table: Records environmental states.
           - `created_at`: The timestamp of the reading.
           - `sensor_type`: The type of sensor ('light' or 'rain').
           - `sensor_value`: The state recorded ('dark', 'bright', 'raining', 'dry').
        2. `access_logs` table: Records specific device actions.
           - `created_at`: The timestamp of the action.
           - `event_source`: What caused the action (e.g., 'opened_by_pir', 'voice_led_1_on', 'voice_led_1_off', etc.).

        YOUR TASK:
        - For commands to control lights, use `turn_on_light` or `turn_off_light`.
        - For ANY question about historical data (e.g., "when was," "what was the first," "how about the last"), you MUST use the `query_database` tool.
        - You must decide which table to query. If they ask about an environmental state like 'dark', query `sensor_readings`. If they ask about a device action like 'light turned on', query `access_logs`.
        - You must determine the correct `filters`. For "when was it last raining?", the filter is `{{"sensor_type": "rain", "sensor_value": "raining"}}`. For "when was light one turned on?", the filter is `{{"event_source": "voice_led_1_on"}}`.
        - For questions with "last" or "most recent," set `ascending=False`.
        - For questions with "first" or "earliest," set `ascending=True`.
        - Always respond in a friendly, conversational way based on the tool's output.
    """),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# MQTT event handlers
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0: print("LangChain Agent Service: Connected!"); client.subscribe(NATURAL_COMMAND_TOPIC)
    else: print("Connection failed")

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
        error_message = f"Sorry, an error occurred: {str(e)}"; print(error_message); client.publish(AI_RESPONSE_TOPIC, error_message)

# Main service loop
print("LangChain Agent Service: Starting up...")
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()