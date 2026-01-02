import json
import re
import logging
import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)

class AIAssistant:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AIAssistant, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        try:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0.0,
                max_retries=2,
                timeout=15
            )
            logger.info("✅ AIAssistant (Gemini) inicializado.")
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar AIAssistant: {e}")
            self.llm = None

    def process_intention(self, texto, usuario="App"):
        if not self.llm:
            return None

        agora = datetime.datetime.now()
        str_agora = agora.strftime("%Y-%m-%d %H:%M Semana: %A")

        template_str = """
        Você é o cérebro do FamilyOS. Sua função é classificar e estruturar intenções.

        CONTEXTO:
        - Data Atual: {data_atual}
        - Usuário: {usuario}

        🚨 REGRAS DE DESAMBIGUAÇÃO:
        1. SHOPPING (Compras):
           - Verbo "Comprar" + Objeto Físico -> SHOPPING.
           - Frases curtas de objetos ("Leite", "Pão 2un") -> SHOPPING.
           - 🎨 EMOJI: Gere SEMPRE um emoji representativo no campo "emoji".

        2. TASKS (Tarefas):
           - Ações, serviços, consertos.

        ESTRUTURA JSON ESPERADA:
        {{
            "shopping": [ {{ "nome": "Leite", "cat": "LATICINIOS", "qty": 2, "emoji": "🥛" }} ],
            "tasks": [],
            "reminders": []
        }}

        ENTRADA: "{texto}"
        Responda APENAS o JSON.
        """

        try:
            prompt = ChatPromptTemplate.from_template(template_str)
            chain = prompt | self.llm
            
            logger.info(f"🤖 [AI Service] Processando: {texto}")
            res = chain.invoke({
                "data_atual": str_agora,
                "texto": texto,
                "usuario": usuario
            })

            # Limpeza do JSON (Markdown strip)
            clean_json = re.sub(r'```json|```', '', res.content).strip()
            if not clean_json.startswith('{'):
                match = re.search(r'\{.*\}', clean_json, re.DOTALL)
                if match: clean_json = match.group(0)

            return json.loads(clean_json)

        except Exception as e:
            logger.error(f"❌ Erro na IA: {e}")
            return None