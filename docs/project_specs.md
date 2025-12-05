# Documentação FamilyOS v2.0 — Módulos e Funcionalidades

## 1. Visão Geral do Sistema
O **FamilyOS v2.0** é um sistema operacional doméstico que unifica gestão de compras, tarefas, clima e inspiração diária em uma única plataforma.

**Tecnologias:**
- Backend: Python Flask + SQLite + SQLAlchemy
- Frontend: HTML5, CSS3 (Cyberpunk Dark Neon), JavaScript Vanilla
- IA: Google Gemini Pro
- Infraestrutura: Docker + Traefik + n8n

---

## 2. Módulo Dashboard (Tela Inicial)

### Layout
A tela inicial é um Dashboard com:

1. **Header:**
   - Saudação dinâmica (“Bom dia, Thiago”)
   - Ícone do clima + temperatura atual

2. **Widget “Mensagem do Dia”**
   - Card com fundo de vidro
   - Frase inspiracional/religiosa (atualizada diariamente)

3. **Widget “Estratégia do Tempo”**
   - Resumo do dia (manhã/tarde/noite)
   - Previsão do fim de semana (sábado e domingo)

4. **Grid de Módulos (Botões Grandes):**
   - 🛒 **Lista de Compras** (ativo, com badge de pendentes)
   - ✅ **Tarefas** (ativo, com badge de alta prioridade)
   - 🥗 **Inserir Ingredientes** (opaco, desabilitado)
   - ⏰ **Lembretes** (opaco, desabilitado)

---

## 3. Módulo de Tarefas

### Funcionalidades
- Adição via Telegram (voz/texto) ou manualmente
- Atribuição automática por IA:
  - **Explícita:** Nome na frase → responsável nomeado
  - **Coletiva:** “Temos que” → responsável “Casal”
  - **Implícita:** Sem nome → atribui ao remetente
- Classificação de prioridade:
  - 🟢 Baixa (verde)
  - 🟡 Média (amarelo)
  - 🔴 Alta (vermelho) → notificação por e-mail
- Agrupamento visual:
  - 👤 Thiago
  - 👤 Debora
  - 👥 Casal

### Interface
- **Task Card:**
  - Checkbox circular (esquerda)
  - Descrição da tarefa (centro)
  - Bolinha colorida de prioridade (direita)
- **Interações:**
  - Clique: marcar/desmarcar
  - Long Press (800ms): abrir modal de edição
- **Edição via modal:**
  - Alterar responsável (dropdown: Thiago, Debora, Casal)
  - Alterar prioridade (radio: baixa, média, alta)

### API Endpoints (Tarefas)
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/tasks/magic` | Processa texto natural, atribui responsável e prioridade |
| POST | `/tasks/toggle/<id>` | Alterna status (pendente/concluído) |
| POST | `/tasks/update` | Edita descrição, responsável ou prioridade |
| GET | `/tasks` | Renderiza o quadro de tarefas (frontend) |

---

## 4. Módulo de Compras (Mantido v1.2)

### Funcionalidades
- Adição via Telegram (IA processa áudio/texto)
- Categorização automática
- Checkbox otimista com vibração
- Edição via Long Press
- Limpeza de carrinho (arquivamento)

### API Endpoints (Compras)
| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/magic` | Processa transcrição e insere itens |
| POST | `/toggle_item/<id>` | Alterna status (pendente/comprado) |
| POST | `/update_item` | Edita nome e categoria do item |
| POST | `/clear_cart` | Arquivar itens comprados |
| GET | `/shopping` | Renderiza a lista de compras |

---

## 5. API de Dados do Dashboard

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/weather` | Retorna dados meteorológicos cacheados (atualizado a cada 1h) |
| GET | `/api/inspiration` | Retorna mensagem do dia (API externa ou banco local) |

---

## 6. Banco de Dados (Schema v2.0)

### Tabela `tasks`
| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer | PK |
| descricao | String | Descrição da tarefa |
| responsavel | String | 'Thiago', 'Debora', 'Casal' |
| prioridade | Integer | 1=Baixa, 2=Média, 3=Alta |
| status | String | 'pendente', 'concluido' |
| prazo | DateTime | Opcional |
| created_at | DateTime | Data de criação |

### Tabela `weather_cache`
| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer | PK (singleton) |
| city | String | 'Itajaí' |
| data_json | JSON | Payload da API de clima |
| last_updated | DateTime | Última atualização |

### Tabela `inspiration_cache`
| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | Integer | PK (singleton) |
| text | String | Texto da mensagem |
| author | String | Autor (se houver) |
| last_updated | DateTime | Última atualização |

---

## 7. Integrações Externas

### 7.1 Meteorologia
- **Provedor:** OpenWeatherMap ou HG Brasil
- **Frequência:** Cache de 1 hora
- **Dados:** Temperatura, condição, previsão 3 dias

### 7.2 Mensagem do Dia
- **Provedor:** API de citações (ex.: TheySaidSo) ou banco local

### 7.3 n8n (Roteador de Intenção)
1. Recebe webhook do Telegram
2. Classifica intenção (`SHOPPING` ou `TASK`)
3. Roteia para o endpoint correspondente (`/magic` ou `/tasks/magic`)

### 7.4 Notificações por E-mail
- Disparadas quando:
  - Tarefa com prioridade **Alta** é criada
  - Responsável: Thiago, Debora ou ambos (Casal)

---

## 8. Estratégia de Desenvolvimento (Roadmap)

### Fase 1 — Fundação
- Criar tabelas `tasks`, `weather_cache`, `inspiration_cache`
- Implementar endpoints de tarefas e dashboard

### Fase 2 — Inteligência
- Configurar n8n para roteamento de intenção
- Ajustar prompt do Gemini para extrair responsável e prioridade

### Fase 3 — Frontend
- Criar `home.html` (Dashboard)
- Criar `tasks.html` (Quadro de tarefas)
- Mover lista de compras para `shopping.html`

### Fase 4 — Notificações
- Configurar SMTP para envio de e-mails
- Implementar disparo automático para tarefas de alta prioridade

---

## 9. Design System (Cyberpunk Dark Neon)

### Cores Principais
| Variável | Cor | Uso |
|----------|-----|-----|
| `--bg` | `#050509` | Fundo principal |
| `--glass` | `rgba(66,79,105,0.25)` | Efeito vidro |
| `--neon-p` | `#611af0` | Roxo (destaque) |
| `--neon-g` | `#22ff7a` | Verde (sucesso) |
| `--neon-r` | `#ff3131` | Vermelho (urgente) |

### Cores de Prioridade (Tarefas)
| Nível | Cor | Hex |
|-------|-----|-----|
| Baixa | Verde | `#22ff7a` |
| Média | Dourado | `#ffb800` |
| Alta | Vermelho | `#ff3131` |

---

## 10. Estrutura de Arquivos

```
familyos/
├── src/
│   ├── app.py
│   ├── templates/
│   │   ├── home.html       # Dashboard
│   │   ├── shopping.html   # Lista de compras
│   │   ├── tasks.html      # Quadro de tarefas
│   │   └── login.html
│   └── static/css/styles.css
├── docs/
│   ├── api_docs.md
│   ├── frontend_docs.md
│   ├── env_setup_docker.md
│   └── project_specs.md
└── data/
    └── familyos.db
```

---

**Autor:** Thiago Scutari  
**Visão:** Transformar a casa em uma empresa autogerenciável.