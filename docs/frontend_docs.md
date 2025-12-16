# 🎨 FamilyOS Frontend Documentation

**Versão:** 2.2 (Omniscient Sync)
**Stack:** HTML5, Jinja2, CSS3 (Vanilla), JavaScript (Vanilla ES6)
**Design System:** Cyberpunk Dark Neon

---

## 1. Estrutura de Navegação (Sitemap)

A aplicação utiliza um layout mestre (`base.html`) com navegação inferior fixa (Tab Bar).

* **`/` (Dashboard):** Hub central. Exibe saudação, clima, frase do dia e atalhos rápidos.
* **`/shopping` (Mercado):** Lista de compras categorizada com edição rápida.
* **`/tasks` (Tarefas):** Quadro de gestão de afazeres agrupado por responsável.
* **`/reminders` (Lembretes):** Agenda sincronizada com Google Tasks.
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
| `--neon-r` | `#ff3131` | **Danger (Vermelho):** Botão Limpar, Badges de Notificação, Prioridade Alta. |
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
    * **Mercado:** Card com ícone de carrinho e **Badge Vermelho** (contagem de itens).
    * **Tarefas:** Card com ícone de check e **Badge Vermelho** (tarefas pendentes).
    * **Lembretes:** Card com ícone de relógio/calendário e **Badge Vermelho** (sincronia pendente).

### 3.2. Módulo de Mercado (Shopping)
* **Visualização:** Itens agrupados por Categoria (Padaria, Hortifrúti, etc.) em accordions.
* **Item Card:** Exibe Emoji, Nome e Usuário que solicitou.
* **Ação Principal:** Checkbox circular grande (lado direito).
* **Footer:** Botão "Arquivar Comprados" (Vermelho Neon com Glow).

### 3.3. Módulo de Tarefas (Tasks)
* **Visualização:** Agrupamento por Responsável (**Thiago**, **Débora**, **Casal**).
* **Task Card:**
    * Exibe Descrição.
    * **Indicador de Prioridade:** "Dot" (Bolinha) colorida ao lado do texto (🔴 Alta, 🟡 Média, 🟢 Baixa).
    * Metadados: Data de criação e nível de urgência por extenso.
* **Ação:** Checkbox para concluir.

### 3.4. Módulo de Lembretes (Google Tasks) **[NOVO]**
Interface de agenda sincronizada.
* **Identidade Visual:** Bordas e detalhes em **Amarelo Neon** (`#ffb800`) para diferenciar dos outros módulos.
* **Reminder Card:**
    * **Badge de Data:** Exibe Data (DD/MM) e Hora (HH:MM) em destaque no topo do card.
    * **Título:** Texto principal do compromisso.
    * **Notas:** Detalhes adicionais (colapsáveis).
    * **Link:** Botão "Abrir no Google" se houver link externo.
* **Ação Principal:** Botão Flutuante/Fixo **"Sincronizar Agora"**.
    * Ao clicar, o ícone gira (`fa-spin`) indicando comunicação com o n8n.
    * A página recarrega automaticamente após 3 segundos para refletir a batch sync.

---

## 4. Funcionalidades Avançadas (JavaScript)

### 4.1. Modais de Edição (Long Press)
Para manter a interface limpa ("Zero UI"), as opções de edição são acessadas segurando o clique (**800ms**).

* **Geral:** Todos os modais possuem fundo escuro (`#121216`), borda neon correspondente ao módulo e inputs flutuantes.
* **Modal de Mercado:** Edita Nome e Categoria.
* **Modal de Tarefas:** Edita Descrição, Responsável e Prioridade.
* **Modal de Lembretes:**
    * Permite editar Título, Notas, Data e Hora.
    * Ao salvar, a alteração é enviada para o Google Tasks via n8n.

### 4.2. Optimistic UI (Feedback Otimista)
Ao marcar um item ou tarefa:
1.  O CSS aplica o estilo "riscado/apagado" **imediatamente**.
2.  O celular vibra (`navigator.vibrate`).
3.  A requisição `fetch` é enviada ao servidor em segundo plano.

### 4.3. Hacks de Usabilidade
* **Focus Hack:** No mobile, o `datalist` é forçado a abrir no primeiro clique injetando um caractere vazio temporário via JS.
* **Select Styling:** O CSS sobrescreve o `appearance: none` nativo e injeta um ícone SVG (seta branca) para garantir que o dropdown siga o tema escuro em iOS e Android.