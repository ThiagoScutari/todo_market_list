from datetime import datetime
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

try:
    load_dotenv()
except:
    pass

class ChatProcessor:
    def __init__(self, nlp_system):
        self.nlp_system = nlp_system

    def process_message(self, message):
        """
        Processa uma mensagem de chat e a categoriza em tarefas ou lembretes.

        :param message: str - A mensagem de chat a ser processada.
        :return: dict - Um dicionário contendo as tarefas e lembretes extraídos.
        """
        # Usa o sistema de PLN para entender a intenção da mensagem
        processed_data = self.nlp_system.process(message)

        tasks = []
        reminders = []

        # Itera sobre os dados processados para separar tarefas e lembretes
        for item in processed_data:
            if item['type'] == 'task':
                tasks.append({
                    'description': item['description'],
                    'priority': item.get('priority', 'Média'),
                    'responsible': item.get('responsible', 'Thiago')
                })
            elif item['type'] == 'reminder':
                reminders.append({
                    'description': item['description'],
                    'date': item.get('date', datetime.now().strftime("%Y-%m-%d %H:%M"))
                })

        return {
            'tasks': tasks,
            'reminders': reminders
        }

# Exemplo de uso
if __name__ == "__main__":
    # Supondo que Gemini é um sistema de PLN já implementado
    gemini_nlp = ChatOpenAI(model="gpt-4o", temperature=0.2) 
    chat_processor = ChatProcessor(gemini_nlp)
    message = "Lavar o carro e a reunião com a diretoria é amanhã às 14h."
    result = chat_processor.process_message(message)
    print(result)
