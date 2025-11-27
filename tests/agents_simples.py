# importar bibliotecas
from dotenv import load_dotenv, dotenv_values
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain.tools import tool

# carregar api-keys
try:
    load_dotenv()
    api_keys = dotenv_values()
    # apenas para validacao | excluir depois
    for i, f in api_keys.items():
        if len(f'{f}') > 15:
            print(f'{i}: {f[:7]}***...')
except ValueError as e:
    print(f'Erro ao importar api-key: {e}')

# carregar LLM
try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.5,
        verbose=True
    )
    # apenas para validacao | excluir depois
    print(f'Modelo carregado com sucesso: {llm.model}')
except ValueError as e:
    print(f'Erro ao importar api-key: {e}')

# criar agente
system_promt = """
    Você é um experiente recepcionista cortez e gentil. 
    1. Descubra o nome do usuário
    2. Dê as boas vindas ao convidado!
"""

@tool
def perguntar_nome()-> str:
    """Utilize essa ferramenta para descobrir o nome do convidado"""
    guest_name = input("Seja muito bem vindo! \nComo devo chamá-lo?\n")
    return guest_name

tools = [perguntar_nome]

agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=system_promt
    )


# iniciar agente
response = agent.invoke(
    {
        "messages": [
            {"role": "user", "content": "Descubra o nome do usuário e depois dê as boas vindas."}
        ]
    }
)

resultado_final = response["messages"]
ultima_resposta = resultado_final[-1]
mensagem_final = ultima_resposta.text

print(f'\n{mensagem_final}\n')

"""
```plaintext
    (venv) PS D:\langchain\projects\todo_market_list\src> python .\agents.py
    GEMINI_API_KEY: AIzaSyA***...
    SERPER_API_KEY: 3568202***...
    FIRECRAWL_API_KEY: fc-648b***...
    Modelo carregado com sucesso: models/gemini-2.5-flash
    Seja muito bem vindo!
    Como devo chamá-lo?
    Thiago Scutari

    Olá, Thiago Scutari! Seja muito bem-vindo(a)! É um prazer tê-lo(a) aqui.

    (venv) PS D:\langchain\projects\todo_market_list\src>
```
"""


