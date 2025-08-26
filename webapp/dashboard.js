// Supabase Client Initialization
const SUPABASE_URL = 'https://kxqmvprrpodgonxeikuh.supabase.co';
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt4cW12cHJycG9kZ29ueGVpa3VoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYwOTk2MzksImV4cCI6MjA3MTY3NTYzOX0.eqtxurvLupES-c9vrhkjqkcwHyDytvDkttdpGPB_Si0';

const { createClient } = supabase;
const supabaseClient = createClient(SUPABASE_URL, SUPABASE_KEY);

// Get HTML Elements
const userEmailSpan = document.getElementById('user-email');
const signOutButton = document.getElementById('signout-button');
const commandDisplay = document.getElementById('command-display');
const micButton = document.getElementById('mic-button');

// Page Protection & User Info
// This function runs as soon as the page loads
(async () => {
    const { data, error } = await supabaseClient.auth.getUser();
    
    // If there's an error or no user, redirect to the login page
    if (error || !data.user) {
        console.log('No user logged in. Redirecting to login page.');
        window.location.href = 'login.html';
    } else {
        // If a user is logged in, display their email
        console.log('User is logged in:', data.user);
        userEmailSpan.textContent = data.user.email;
    }
})();

// Sign Out Logic
signOutButton.addEventListener('click', async () => {
    const { error } = await supabaseClient.auth.signOut();
    if (error) {
        console.error('Error signing out:', error);
    } else {
        // Redirect to login page on successful sign out
        window.location.href = 'login.html';
    }
});


// MQTT & Voice Control Logic

// Configuration
const MQTT_BROKER = 'ws://localhost'; // Use your computer's IP if testing on another device
const MQTT_PORT = 9001;
const COMMAND_TOPIC = 'home/commands/natural';

// MQTT Client Setup
const client = mqtt.connect(`${MQTT_BROKER}:${MQTT_PORT}`);

client.on('connect', () => {
    console.log('Successfully connected to MQTT broker!');
    commandDisplay.textContent = 'Press the button and speak a command.';
});

client.on('error', (err) => {
    console.error('MQTT Connection Error:', err);
    commandDisplay.textContent = 'Error connecting to Broker!';
    client.end();
});

// Web Speech API Setup
window.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (window.SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    let isListening = false;

    micButton.addEventListener('click', () => {
        isListening ? recognition.stop() : recognition.start();
    });

    recognition.onstart = () => {
        isListening = true;
        micButton.textContent = 'Stop Listening';
        micButton.classList.add('listening');
        commandDisplay.textContent = 'Listening...';
    };

    recognition.onend = () => {
        isListening = false;
        micButton.textContent = 'Start Listening';
        micButton.classList.remove('listening');
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        commandDisplay.textContent = `Error: ${event.error}`;
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        commandDisplay.textContent = `"${transcript}"`;
        console.log(`Publishing to '${COMMAND_TOPIC}': ${transcript}`);
        client.publish(COMMAND_TOPIC, transcript);
    };
} else {
    alert("Sorry, your browser does not support Speech Recognition. Please try Chrome or Edge.");
}