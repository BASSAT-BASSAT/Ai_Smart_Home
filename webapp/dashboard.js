// --- Supabase & MQTT Client Initialization ---
// Initialize Supabase and MQTT clients
const SUPABASE_URL = 'https://kxqmvprrpodgonxeikuh.supabase.co';
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt4cW12cHJycG9kZ29ueGVpa3VoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYwOTk2MzksImV4cCI6MjA3MTY3NTYzOX0.eqtxurvLupES-c9vrhkjqkcwHyDytvDkttdpGPB_Si0';
const { createClient } = supabase;
const supabaseClient = createClient(SUPABASE_URL, SUPABASE_KEY);

// MQTT configuration and topic setup
const MQTT_BROKER = 'ws://localhost';
const MQTT_PORT = 9001;
const COMMAND_TOPIC = 'home/commands/natural';
const AI_RESPONSE_TOPIC = 'home/ai/response';
const VOICE_LIGHTS_TOPIC = 'home/lights/voice';
const client = mqtt.connect(`${MQTT_BROKER}:${MQTT_PORT}`);

// Get references to HTML elements
const userEmailSpan = document.getElementById('user-email');
const signOutButton = document.getElementById('signout-button');
const commandDisplay = document.getElementById('command-display');
const micButton = document.getElementById('mic-button');
const sensorDisplay = document.getElementById('sensor-data-display');
const accessLogDisplay = document.getElementById('access-log-display');
const filterButtons = document.querySelectorAll('.filter-buttons button');

// Manual Control Buttons
// Manual control buttons for lights
const btnLight1On = document.getElementById('btn-light1-on');
const btnLight1Off = document.getElementById('btn-light1-off');
const btnLight2On = document.getElementById('btn-light2-on');
const btnLight2Off = document.getElementById('btn-light2-off');

// Protect page: redirect if not logged in
(async () => {
    const { data, error } = await supabaseClient.auth.getUser();
    if (error || !data.user) {
        window.location.href = 'login.html';
    } else {
        userEmailSpan.textContent = data.user.email;
    }
})();

// Sign out logic
signOutButton.addEventListener('click', async () => {
    const { error } = await supabaseClient.auth.signOut();
    if (error) { console.error('Error signing out:', error); }
    else { window.location.href = 'login.html'; }
});

// MQTT connection and message handling
client.on('connect', () => {
    console.log('Successfully connected to MQTT broker!');
    commandDisplay.textContent = 'Ask a question or give a command.';
    client.subscribe(AI_RESPONSE_TOPIC, (err) => {
        if (!err) { console.log(`Subscribed to ${AI_RESPONSE_TOPIC}`); }
    });
});

client.on('message', (topic, message) => {
    if (topic === AI_RESPONSE_TOPIC) {
        const ai_answer = message.toString();
        console.log(`Received AI response: ${ai_answer}`);
        commandDisplay.textContent = ai_answer;
        speak(ai_answer);
    }
});

client.on('error', (err) => {
    console.error('MQTT Connection Error:', err);
    commandDisplay.textContent = 'Error connecting to Broker!';
});

// Text-to-speech for AI responses
function speak(text) {
    if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'en-US';
        window.speechSynthesis.speak(utterance);
    } else {
        console.log("Browser does not support text-to-speech.");
    }
}

// Web Speech API for voice commands
window.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (window.SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    let isListening = false;
    micButton.addEventListener('click', () => { isListening ? recognition.stop() : recognition.start(); });
    recognition.onstart = () => { isListening = true; micButton.textContent = 'Stop Listening'; micButton.classList.add('listening'); commandDisplay.textContent = 'Listening...'; };
    recognition.onend = () => { isListening = false; micButton.textContent = 'Start Listening'; micButton.classList.remove('listening'); commandDisplay.textContent = 'Ask a question or give a command.'; };
    recognition.onerror = (event) => { console.error('Speech recognition error:', event.error); commandDisplay.textContent = `Error: ${event.error}`; };
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        commandDisplay.textContent = `You said: "${transcript}"`;
        client.publish(COMMAND_TOPIC, transcript);
    };
} else {
    alert("Sorry, your browser does not support Speech Recognition.");
}

btnLight1On.addEventListener('click', () => {
    console.log("Button Clicked: Light 1 ON");
    client.publish(VOICE_LIGHTS_TOPIC, 'on1');
});
btnLight1Off.addEventListener('click', () => {
    console.log("Button Clicked: Light 1 OFF");
    client.publish(VOICE_LIGHTS_TOPIC, 'off1');
});
// Manual button event listeners for light control
btnLight2On.addEventListener('click', () => {
    console.log("Button Clicked: Light 2 ON");
    client.publish(VOICE_LIGHTS_TOPIC, 'on2');
});
btnLight2Off.addEventListener('click', () => {
    console.log("Button Clicked: Light 2 OFF");
    client.publish(VOICE_LIGHTS_TOPIC, 'off2');
});

// Fetch and display sensor and access log data
async function fetchData(minutes) {
    console.log(`Fetching data for the last ${minutes} minutes...`);
    sensorDisplay.innerHTML = 'Fetching data...';
    accessLogDisplay.innerHTML = 'Fetching data...';

    const now = new Date();
    const startTime = new Date(now.getTime() - minutes * 60 * 1000);
    const startTimeISO = startTime.toISOString();

    const { data: sensorData, error: sensorError } = await supabaseClient.from('sensor_readings').select('*').gte('created_at', startTimeISO).order('created_at', { ascending: false });
    const { data: logData, error: logError } = await supabaseClient.from('access_logs').select('*').gte('created_at', startTimeISO).order('created_at', { ascending: false });

    renderSensorData(sensorData, sensorError);
    renderAccessLogs(logData, logError);
}

// Render sensor data to dashboard
function renderSensorData(data, error) {
    if (error) { sensorDisplay.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`; return; }
    if (!data || data.length === 0) { sensorDisplay.innerHTML = '<p>No sensor readings in this period.</p>'; return; }
    const html = data.map(item => `<div class="log-entry">${new Date(item.created_at).toLocaleTimeString()}: [${item.sensor_type}] recorded '${item.sensor_value}'</div>`).join('');
    sensorDisplay.innerHTML = html;
}

// Render access logs to dashboard
function renderAccessLogs(data, error) {
    if (error) { accessLogDisplay.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`; return; }
    if (!data || data.length === 0) { accessLogDisplay.innerHTML = '<p>No access logs in this period.</p>'; return; }
    const html = data.map(item => `<div class="log-entry">${new Date(item.created_at).toLocaleString()}: Event by [${item.event_source}]</div>`).join('');
    accessLogDisplay.innerHTML = html;
}

// Filter buttons for data history
filterButtons.forEach(button => {
    button.addEventListener('click', () => {
        filterButtons.forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        const id = button.id;
        let minutes = 10;
        if (id === 'filter-1h') minutes = 60;
        if (id === 'filter-24h') minutes = 1440;
        fetchData(minutes);
    });
});

// Initial data load
fetchData(10);