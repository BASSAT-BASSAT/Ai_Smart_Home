const SUPABASE_URL = 'https://kxqmvprrpodgonxeikuh.supabase.co';
const SUPABASE_URL = 'https://kxqmvprrpodgonxeikuh.supabase.co';
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imt4cW12cHJycG9kZ29ueGVpa3VoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYwOTk2MzksImV4cCI6MjA3MTY3NTYzOX0.eqtxurvLupES-c9vrhkjqkcwHyDytvDkttdpGPB_Si0';

const { createClient } = supabase;
const supabaseClient = createClient(SUPABASE_URL, SUPABASE_KEY);

const signInButton = document.getElementById('signin-button');
const signInButton = document.getElementById('signin-button');
const signUpButton = document.getElementById('signup-button');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const messageDiv = document.getElementById('message');

signUpButton.addEventListener('click', async () => {
signUpButton.addEventListener('click', async () => {
    messageDiv.textContent = '';
    const email = emailInput.value;
    const password = passwordInput.value;

    try {
        const { data, error } = await supabaseClient.auth.signUp({ email, password });

        if (error) {
            throw error;
        }

        messageDiv.textContent = 'Success! Please check your email for a confirmation link.';
    messageDiv.style.color = '#4CAF50';

    } catch (error) {
        messageDiv.textContent = `Error: ${error.message}`;
    messageDiv.style.color = '#f44336';
    }
});

signInButton.addEventListener('click', async () => {
    messageDiv.textContent = '';
    const email = emailInput.value;
    const password = passwordInput.value;

    try {
        const { data, error } = await supabaseClient.auth.signInWithPassword({ email, password });

        if (error) {
            throw error;
        }

        window.location.href = 'dashboard.html';

    } catch (error) {
        messageDiv.textContent = `Error: ${error.message}`;
    messageDiv.style.color = '#f44336';
    }
});
