# 🎨 FamilyOS Frontend Documentation

**Versão:** 2.2 (Omniscient Sync + AI Core)
**Stack:** HTML5, Jinja2, CSS3 (Vanilla), JavaScript (Vanilla ES6)
**Design System:** Cyberpunk Dark Neon

---

## 1. Estrutura de Navegação (Sitemap)

A aplicação utiliza um layout mestre (`base.html`) com navegação inferior fixa (Tab Bar).

* **`/` (Dashboard):** Hub central. Exibe saudação, clima, frase do dia e atalhos rápidos.
* **`/shopping` (Mercado):** Lista de compras inteligente com suporte a quantidades.
* **`/tasks` (Tarefas):** Quadro de gestão de afazeres agrupado por responsável.
* **`/reminders` (Lembretes):** Agenda sincronizada (Espelho do Google Tasks).
* **`/login`:** Tela de acesso seguro.

---

## 2. Design System (CSS)

O sistema utiliza variáveis CSS (`:root`) para garantir consistência no tema escuro.

### Paleta de Cores
| Variável | Cor Hex | Aplicação |
| :--- | :--- | :--- |
| `--bg` | `#050509` | **Fundo Global:** Deep Void (Quase preto absoluto). |
| `--glass` | `rgba(66, 79, 105, 0.25)` | **Cards:** Fundo translúcido com efeito de vidro. |
| `--neon-p` | `#611af0` | **Primary (Roxo):** Bordas de destaque, foco, badges ativos. |
| `--neon-g` | `#22ff7a` | **Success (Verde):** Checkboxes, Botão Salvar, Prioridade Baixa. |
| `--neon-r` | `#ff3131` | **Danger (Vermelho):** Botão Arquivar, Badges de Notificação, Prioridade Alta. |
| `--neon-y` | `#ffb800` | **Warning (Amarelo):** Prioridade Média e **Identidade Google Tasks**. |

### Componentes Visuais
* **Glassmorphism:** Uso de `backdrop-filter: blur(12px)` em headers, modais e barra de navegação.
* **Inputs & Selects:** Estilizados manualmente para remover a aparência nativa do navegador (branco/azul), aplicando fundo escuro (`rgba(255,255,255,0.05)`) e bordas suaves.
* **Feedback Tátil:** Botões possuem `:active { transform: scale(0.98); }` para simular toque físico.

---

## 3. Especificação das Telas

### 3.1. Dashboard (Home)
O painel de controle da casa.
* **Header:** Saudação personalizada ("Olá, Thiago") + Widget de Clima em tempo real (Integração HG Brasil).
* **Daily Quote:** Card de destaque com mensagem inspiracional.
* **Grid de Módulos:**
    * **Mercado:** Card com ícone de carrinho e **Badge Vermelho** (contagem de itens pendentes).
    * **Tarefas:** Card com ícone de check e **Badge Vermelho** (tarefas pendentes).
    * **Lembretes:** Card com ícone de relógio e **Badge Vermelho** (pendências sincronizadas).

### 3.2. Módulo de Mercado (Shopping)
* **Visualização:** Itens agrupados por Categoria (Gerada pela IA) em accordions.
* **Item Card:**
    * **Indicador de Quantidade:** Exibe "2x", "3x" em verde neon antes do nome.
    * **Dados:** Emoji, Nome e Usuário que solicitou.
* **Ação Principal:** Checkbox circular grande (lado direito).
* **Controles (FAB Group):** Botões flutuantes fixos no canto inferior direito.
    * **Botão Verde (+):** Abre modal de adição inteligente.
    * **Botão Vermelho (Arquivo):** Arquiva itens comprados (Só aparece se houver itens).

### 3.3. Módulo de Tarefas (Tasks)
* **Visualização:** Agrupamento por Responsável (**Thiago**, **Débora**, **Casal**).
* **Task Card:**
    * Exibe Descrição.
    * **Indicador de Prioridade:** "Dot" (Bolinha) colorida ao lado do texto (🔴 Alta, 🟡 Média, 🟢 Baixa).
    * Metadados: Data de criação e nível de urgência por extenso.
* **Ação:** Checkbox para concluir.

### 3.4. Módulo de Lembretes (Google Tasks)
Interface de visualização ("Mirror Mode") do Google Tasks.
* **Identidade Visual:** Bordas e detalhes em **Amarelo Neon** (`#ffb800`) para diferenciar dos outros módulos.
* **Reminder Card:**
    * **Badge de Data:** Exibe Data (DD/MM) e Hora (HH:MM) em destaque no topo do card, facilitando a leitura rápida de prazos.
    * **Título:** Texto principal do compromisso.
    * **Notas:** Detalhes adicionais vindos do Google Tasks (exibidos de forma colapsável/discreta).
    * **Link:** Botão "Abrir no Google" exibido automaticamente se a tarefa contiver links externos.
* **Sincronização:**
    * A atualização ocorre via Webhook (n8n), garantindo que os dados exibidos sejam sempre o reflexo fiel da nuvem.

---

## 4. Funcionalidades Avançadas (JavaScript)

### 4.1. Modais de Edição (Long Press)
Para manter a interface limpa ("Zero UI"), as opções de edição são acessadas segurando o clique (**800ms**).

* **Geral:** Todos os modais possuem fundo escuro (`#121216`) e inputs flutuantes.
* **Modal de Mercado (Novo):**
    * **Nome:** Input de texto simples (A IA define a categoria no backend).
    * **Quantidade:** Controle "Stepper" com botões grandes de **(+)** e **(-)** para ajuste rápido em mobile.
    * **Hack de Usabilidade:** Remove automaticamente prefixos como "2x " do nome ao abrir a edição.
* **Modal de Tarefas:** Edita Descrição, Responsável e Prioridade.

### 4.2. Optimistic UI (Feedback Otimista)
Ao marcar um item ou tarefa:
1.  O CSS aplica o estilo "riscado/apagado" **imediatamente**.
2.  O celular vibra (`navigator.vibrate`).
3.  A requisição `fetch` é enviada ao servidor em segundo plano.

### 4.3. Hacks de Usabilidade
* **Select Styling:** O CSS sobrescreve o `appearance: none` nativo e injeta um ícone SVG (seta branca) para garantir que o dropdown siga o tema escuro em iOS e Android.
* **FAB Animation:** Os botões flutuantes possuem transição suave de entrada (`scale-in`) para não obstruir a leitura da lista.