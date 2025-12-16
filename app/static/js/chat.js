document.addEventListener("DOMContentLoaded", function() {
    console.log("🚀 Chat Script Carregado!");

    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chatContainer = document.getElementById('chat-container');

    // Validação de segurança
    if (!chatInput || !sendButton) {
        console.error("❌ Erro Crítico: Input ou Botão não encontrados no HTML.");
        return;
    }

    // Função de Envio
    async function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return; // Não envia vazio

        // 1. Adiciona mensagem do Usuário na tela (Optimistic UI)
        appendMessage(message, 'user');
        chatInput.value = ''; // Limpa campo
        chatInput.focus();    // Devolve o foco

        try {
            console.log("📤 Enviando para API...", message);
            
            // 2. Envia para o Backend
            const response = await fetch('/chat/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    message: message,
                    usuario: "Thiago" // Pode dinamizar depois
                })
            });

            if (!response.ok) throw new Error('Falha na rede');

            const data = await response.json();
            console.log("📥 Resposta recebida:", data);

            // 3. Adiciona resposta do Bot
            // Verifica se é um objeto rico (tarefas) ou texto simples
            const botResponse = typeof data.response === 'object' 
                                ? JSON.stringify(data.response, null, 2) // Temporário para debug
                                : data.response;
            
            appendMessage(botResponse, 'bot');

        } catch (error) {
            console.error("❌ Erro:", error);
            appendMessage("Desculpe, estou com problemas de conexão.", 'bot');
        }
    }

    // Função auxiliar para criar as bolhas
    function appendMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        
        // Se for Bot e tiver quebras de linha, respeita a formatação
        if (sender === 'bot') {
            // Converte quebras de linha em <br> se for texto simples
            messageDiv.innerHTML = text.replace(/\n/g, '<br>');
        } else {
            messageDiv.textContent = text;
        }

        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight; // Auto-scroll
    }

    // --- EVENT LISTENERS (O que estava faltando) ---
    
    // 1. Clique no botão
    sendButton.addEventListener('click', sendMessage);

    // 2. Apertar Enter no input
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault(); // Evita quebra de linha no input
            sendMessage();
        }
    });
});