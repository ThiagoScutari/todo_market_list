# Documento Mestre de Arquitetura: FamilyOS

## 1. Introdução

### 1.1. Propósito do Documento
Este documento estabelece a arquitetura completa do sistema FamilyOS, substituindo a especificação inicial que se encontra defasada frente às implementações realizadas. Serve como fonte única da verdade para o desenvolvimento, manutenção e evolução do projeto.

### 1.2. Escopo do Projeto
O FamilyOS é um sistema híbrido de gestão doméstica inteligente, com foco inicial no módulo de compras. O sistema combina tecnologias de nuvem e processamento local para oferecer experiência de **Fricção Zero** na entrada e gestão de informações.

### 1.3. Partes Interessadas
- **Usuários finais:** Membros da família (Thiago, Esposa)
- **Equipe de desenvolvimento:** Alpha, Architect, Experience, Builder
- **Administradores do sistema:** Responsáveis pela infraestrutura

## 2. Visão Geral do Sistema

### 2.1. Objetivos Estratégicos
- Reduzir a fricção na entrada de dados domésticos
- Centralizar informações familiares de forma inteligente
- Automatizar processos domésticos recorrentes
- Prover insights baseados em dados históricos

### 2.2. Princípios Arquiteturais
1. **Fricção Zero:** Interface natural (voz) como padrão
2. **Resiliência Nativa:** Tolerância a falhas por design
3. **Desacoplamento:** Separação clara de responsabilidades
4. **Escalabilidade:** Capacidade de crescimento modular
5. **Privacidade:** Controle sobre dados sensíveis

## 3. Arquitetura Técnica Detalhada

### 3.1. Visão de Alto Nível

```
┌─────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   INTERFACE     │    │   ORQUESTRADOR   │    │    CÉREBRO       │
│                 │    │                  │    │                  │
│  • Telegram     │───▶│  • n8n           │───▶│  • Flask API     │
│  • (Voz/Texto)  │    │  • Whisper       │    │  • Gemini AI     │
│                 │    │  • Ngrok         │    │  • LangChain     │
└─────────────────┘    └──────────────────┘    └──────────────────┘
                                                           │
                                                           ▼
┌─────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   VISUALIZAÇÃO  │    │    MEMÓRIA       │    │  INTELIGÊNCIA    │
│                 │    │                  │    │                  │
│  • WEB          │◀──│  • SQLite        │◀──│  • Processamento  │
│  • (Futuro Web) │    │  • SQLAlchemy    │    │  • Analytics     │
│                 │    │  • Models        │    │                  │
└─────────────────┘    └──────────────────┘    └──────────────────┘
```

### 3.2. Componentes do Sistema

### 3.2.1. Camada de Interface (Frontend)
**Telegram Bot (Input)**
- Função: Interface primária de entrada rápida (Voz/Texto).

**Web App Responsivo (Visualização & Controle)**
- Função: Dashboard para visualização da lista no mercado e gestão financeira.
- Stack: Flask Templates (Jinja2) + HTML5 + CSS (Bootstrap/Tailwind).
- Características:
  - Mobile-First (Focado no uso via celular no mercado).
  - Checkboxes interativos para marcar itens comprados.
  - Atualização em tempo real (AJAX/Fetch).
  - Acesso via navegador (sem instalação de app).

#### 3.2.2. Camada de Orquestração (Middleware)
**n8n Workflow**
```yaml
Workflow Principal:
  - Trigger: Telegram Message
  - Processamento:
      - Tipo: Audio/Text Detection
      - Transcrição: Gemini (para áudio)
      - Enriquecimento: Extração de metadados do usuário
  - Saída: HTTP Request para API Flask
```

**Ngrok Tunnel**
- **Propósito:** Exposição segura do ambiente local
- **Configuração:** Túnel HTTPS para `localhost:5000`
- **Segurança:** Criptografia ponta a ponta

#### 3.2.3. Camada de Processamento (Backend)
**API Flask (`app.py`)**
```python
# Estrutura Principal
Endpoints:
  - POST /magic: Processamento NLP e persistência
  - (Futuro) GET /items: Consulta de itens
  - (Futuro) PUT /items/:id: Atualização de status

Características:
  - Arquitetura de Microserviço
  - Tratamento robusto de erros
  - Logging detalhado
```

**Motor de Inteligência Artificial**
```python
# Configuração LangChain
model = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite", 
    temperature=0.0
)

# Pipeline NLP
prompt_template = """
Extraia os itens de compra. Retorne LISTA JSON.
Campos: nome, quantidade, unidade, categoria
"""
```

#### 3.2.4. Camada de Dados (Persistence)
**Modelo de Dados SQLAlchemy**
```python
# Entidades Principais
- Categoria: Categorização de produtos
- UnidadeMedida: Unidades de medida suportadas
- Produto: Catálogo mestre de produtos
- ListaItem: Itens ativos nas listas
- TipoLista: Classificação de listas
- Receita: Gestão de receitas culinárias
```

**Esquema do Banco de Dados**
```sql
-- Tabela Principal: Lista de Itens
CREATE TABLE lista_itens (
    id INTEGER PRIMARY KEY,
    produto_id INTEGER FOREIGN KEY,
    tipo_lista_id INTEGER DEFAULT 1,
    quantidade FLOAT NOT NULL,
    unidade_id INTEGER FOREIGN KEY,
    usuario VARCHAR(50),           -- Nova coluna
    status VARCHAR(20) DEFAULT 'pendente',
    adicionado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    origem_input VARCHAR(100)
);
```

### 3.3. Fluxos de Processamento

#### 3.3.1. Fluxo Principal: Voice-to-Database
**Passo 1: Coleta (Telegram)**
- Usuário envia áudio/texto para o bot
- Sistema captura metadados (usuário, timestamp)

**Passo 2: Preparação (n8n)**
```javascript
// Lógica de processamento inicial
const inputTexto = {{ $json.text || $json.message.text }};
const usuario = {{ $json.message.from.first_name }};
```

**Passo 3: Transcrição (Whisper)**
- Arquivo de áudio convertido para texto
- Tratamento de qualidade de áudio

**Passo 4: Processamento Inteligente (Flask + Gemini)**
- Análise NLP do texto natural
- Extração estruturada de entidades
- Classificação automática de categorias

**Passo 5: Persistência (SQLAlchemy)**
```python
# Lógica de negócio
1. Verifica existência do produto
2. Cria produto se necessário
3. Adiciona item à lista com usuário
4. Commit transacional
```

**Passo 6: Confirmação (Telegram)**
- Feedback imediato ao usuário
- Confirmação dos itens processados

## 4. Especificações Técnicas Detalhadas

### 4.1. Stack Tecnológica

#### 4.1.1. Backend
```yaml
Linguagem: Python 3.11+
Framework: Flask 3.0+
ORM: SQLAlchemy 2.0+
AI Framework: LangChain 0.2+
Database: SQLite (Dev) / PostgreSQL (Prod)
```

#### 4.1.2. Processamento de Linguagem Natural
```yaml
Modelo Primário: Google Gemini 2.5 Flash-Lite
Modelo Secundário: OpenAI GPT-4 (Fallback)
Transcrição: OpenAI Whisper
Temperatura: 0.0 (Determinístico)
```

#### 4.1.3. Infraestrutura
```yaml
Desenvolvimento: Ngrok + Localhost
Produção: VPS/Render + Domain
Monitoramento: Logs estruturados
Backup: Scripts automáticos
```

### 4.2. Modelo de Dados Expandido

#### 4.2.1. Entidades e Relacionamentos
```python
# Diagrama de Relacionamentos
Categoria (1) ─┐
               ├─ (N) Produto (1) ─┐
UnidadeMedida (1) ─┘                ├─ (N) ListaItem
                                    │
TipoLista (1) ──────────────────────┘
```

#### 4.2.2. Atributos Críticos
**Tabela `lista_itens`:**
- `usuario`: Rastreamento por membro da família
- `origem_input`: Audit trail (telegram_voice, manual, etc.)
- `status`: Máquina de estados (pendente → comprado → cancelado)
- `adicionado_em`: Timestamp para analytics

### 4.3. APIs e Endpoints

#### 4.3.1. API Magic (`POST /magic`)
**Request:**
```json
{
  "texto": "comprar 2 litros de leite",
  "usuario": "Thiago"
}
```

**Response:**
```json
{
  "message": "Sucesso! Thiago adicionou: leite",
  "dados": [
    {
      "nome": "leite",
      "quantidade": 2,
      "unidade": "L",
      "categoria": "Padaria"
    }
  ]
}
```

**Fluxo de Erro:**
```python
try:
    # Processamento principal
except JSONDecodeError:
    # Correção automática do JSON
except SQLAlchemyError:
    # Rollback transacional
except Exception as e:
    # Logging e retorno genérico
```

## 5. Plano de Desenvolvimento e Evolução

### 5.1. Sprint 3: Frontend Web (Shopping List)
**Objetivo:** Eliminar a dependência do Notion e criar interface própria.
**Entregáveis:**
- Rota `/` no Flask servindo o HTML.
- Interface de Lista de Compras com Checkbox.
- Botão para limpar itens comprados.
- Filtro por Categoria (Hortifrúti, Padaria, etc.).

### 5.2. Sprint 4: Deploy de Produção
**Objetivo:** Ambiente profissional
**Entregáveis:**
- Migração para VPS/Render
- Domain próprio
- SSL Certificate
- Backup automation

### 5.3. Sprint 5: Funcionalidades Avançadas
**Objetivo:** Expansão do sistema
**Entregáveis:**
- Módulo de receitas
- Sistema de alertas
- Analytics preditivo
- Integração com mercados

## 6. Considerações de Qualidade

### 6.1. Segurança
- Autenticação de usuários via Telegram
- Validação de entrada em todas as camadas
- Logs de auditoria completos
- Criptografia em trânsito (HTTPS)

### 6.2. Performance
- Cache de produtos frequentes
- Otimização de queries SQL
- Processamento assíncrono onde aplicável
- Monitoramento de latência

### 6.3. Manutenibilidade
- Código modular e testável
- Documentação atualizada
- Logs estruturados
- Procedures de deploy

### 6.4. Escalabilidade
- Arquitetura stateless
- Possibilidade de sharding
- Load balancing futuro
- Microserviços independentes

## 7. Métricas de Sucesso

### 7.1. Métricas Técnicas
- Uptime: 99.5%+
- Latência API: < 2 segundos
- Precisão NLP: > 95%
- Disponibilidade: 24/7

### 7.2. Métricas de Negócio
- Adoção familiar: 2+ usuários ativos
- Itens processados: 50+ por semana
- Redução de tempo: 70% vs método tradicional
- Satisfação: Feedback positivo contínuo

## 8. Riscos e Mitigações

### 8.1. Riscos Técnicos
| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Downtime Ngrok | Médio | Alto | Migração para infraestrutura profissional |
| Limitação API Gemini | Baixo | Médio | Sistema de fallback para OpenAI |
| Corrupção de BD | Baixo | Crítico | Backups automáticos e recovery plan |

### 8.2. Riscos Operacionais
| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Resistência usuários | Médio | Alto | Onboarding gradual e suporte |
| Manutenção complexa | Baixo | Médio | Documentação detalhada e automation |

## 9. Conclusão

O FamilyOS representa uma evolução significativa na gestão doméstica inteligente, combinando tecnologias modernas com foco na experiência do usuário. A arquitetura aqui documentada fornece base sólida para crescimento sustentável, mantendo os princípios de fricção zero e resiliência que guiaram o desenvolvimento desde o início.

Este documento deve ser revisado e atualizado a cada sprint significativa ou mudança arquitetural majoritária, mantendo-se como a fonte única da verdade para o projeto FamilyOS.

---
**Document Version:** 2.0  
**Last Updated:** {{current_date}}  
**Maintainer:** Architecture Team  
**Status:** ✅ Approved