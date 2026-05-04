// Scroll messages to bottom if available
document.addEventListener("DOMContentLoaded", () => {
    const messagesContainer = document.querySelector('.messages-container');
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Theme logic
    initTheme();

    setupThemeToggle('theme-toggle', 'theme-icon');
    // Also setup index specific one if it exists
    setupThemeToggle('theme-toggle-index', 'theme-icon-index');
});

function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    let currentTheme = 'light';
    if (savedTheme) {
        currentTheme = savedTheme;
    } else if (systemPrefersDark) {
        currentTheme = 'dark';
    }
    
    document.documentElement.setAttribute('data-theme', currentTheme);
    updateAllThemeIcons(currentTheme);
}

function setupThemeToggle(btnId, iconId) {
    const themeToggleBtn = document.getElementById(btnId);
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            let currentTheme = document.documentElement.getAttribute('data-theme');
            let newTheme = currentTheme === 'light' ? 'dark' : 'light';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateAllThemeIcons(newTheme);
        });
    }
}

function updateAllThemeIcons(theme) {
    const icons = ['theme-icon', 'theme-icon-index'];
    icons.forEach(id => {
        const icon = document.getElementById(id);
        if (icon) {
            icon.textContent = theme === 'dark' ? '☀️' : '🌙';
        }
    });
}

// Chatbot UI and API logic
document.addEventListener("DOMContentLoaded", () => {
    const chatbotToggle = document.getElementById('chatbot-toggle');
    const chatbotWindow = document.getElementById('chatbot-window');
    const chatbotClose = document.getElementById('chatbot-close');
    const chatbotInput = document.getElementById('chatbot-input-field');
    const chatbotSend = document.getElementById('chatbot-send');
    const chatbotMessages = document.getElementById('chatbot-messages');

    if (chatbotToggle && chatbotWindow) {
        chatbotToggle.addEventListener('click', () => {
            chatbotWindow.classList.toggle('active');
        });

        chatbotClose.addEventListener('click', () => {
            chatbotWindow.classList.remove('active');
        });

        const sendMessageToBot = async () => {
            const message = chatbotInput.value.trim();
            if (!message) return;

            // Add user message to UI
            addBotMessage(message, 'user');
            chatbotInput.value = '';

            try {
                const response = await fetch('/chatbot', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                });

                const data = await response.json();
                if (data.reply) {
                    addBotMessage(data.reply, 'bot');
                }
            } catch (error) {
                console.error('Error communicating with bot:', error);
                addBotMessage('Sorry, I am having trouble connecting right now.', 'bot');
            }
        };

        if (chatbotSend) {
            chatbotSend.addEventListener('click', sendMessageToBot);
        }
        
        if (chatbotInput) {
            chatbotInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    sendMessageToBot();
                }
            });
        }
    }

    function addBotMessage(text, sender) {
        if (!chatbotMessages) return;
        const msgDiv = document.createElement('div');
        msgDiv.className = sender === 'user' ? 'user-msg' : 'bot-msg';
        msgDiv.textContent = text;
        chatbotMessages.appendChild(msgDiv);
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
    }
});
