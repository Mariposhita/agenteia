const chatbotButton = document.querySelector('.chatbot-button');
const chatbotModal = document.getElementById('chatbotModal');
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');

function toggleChatbot() {
    if (chatbotModal.style.display === 'block') {
        chatbotModal.style.display = 'none';
    } else {
        chatbotModal.style.display = 'block';
        chatInput.focus();
    }
}

chatbotButton.addEventListener('click', toggleChatbot);

async function enviarMensaje() {
    const mensaje = chatInput.value.trim();
    if (!mensaje) return;

    agregarMensaje('user', mensaje);
    chatInput.value = '';
    
    // Llamada al backend para obtener respuesta
    const response = await fetch('/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: mensaje})
    });
    const data = await response.json();

    agregarMensaje('bot', data.answer);

    if (data.ticket_required) {
        // Mostrar formulario para crear ticket
        mostrarFormularioTicket();
    }
}

function agregarMensaje(remitente, texto) {
    const div = document.createElement('div');
    div.classList.add('message');
    div.classList.add(remitente === 'user' ? 'user-message' : 'bot-message');
    div.innerHTML = `<strong>${remitente === 'user' ? 'Tú' : '🤖 Asistente IA'}:</strong><br>${texto}`;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function mostrarFormularioTicket() {
    // Aquí puedes implementar mostrar un formulario para que el usuario ingrese datos
    // Por simplicidad, alertamos y pedimos datos con prompt (mejorar con modal o formulario real)
    const nombre = prompt("Por favor, ingresa tu nombre completo:");
    const telefono = prompt("Por favor, ingresa tu teléfono:");
    const domicilio = prompt("Por favor, ingresa tu domicilio:");
    const problema = prompt("Describe brevemente el problema:");

    if (nombre && telefono && domicilio && problema) {
        crearTicket({nombre, telefono, domicilio, problema});
    } else {
        agregarMensaje('bot', 'No se pudo crear el ticket porque faltaron datos.');
    }
}

async function crearTicket(datos) {
    const response = await fetch('/create_ticket', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(datos)
    });
    const data = await response.json();
    agregarMensaje('bot', data.message);
}