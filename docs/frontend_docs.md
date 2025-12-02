# 🎨 FamilyOS Frontend Documentation
**Versão:** 1.2
**Stack:** HTML5, Jinja2, CSS3 (Vanilla), JavaScript (Vanilla ES6)
**Design System:** Cyberpunk Dark Neon

---

## 1. Estrutura de Arquivos

* **\`src/templates/index.html\`**: O coração do app. Contém o HTML, Jinja2 (para renderizar dados do Python) e todo o JavaScript lógico.
* **\`src/templates/login.html\`**: Tela de login minimalista com feedback de erro (Flash Messages).
* **\`src/static/css/styles.css\`**: Folha de estilos global contendo as variáveis de cores e efeitos de vidro.

---

## 2. Design System (CSS)

O sistema utiliza variáveis CSS (\`:root\`) para facilitar a manutenção do tema.

### Variáveis Principais
| Variável | Cor | Uso |
| :--- | :--- | :--- |
| \`--bg\` | \`#050509\` | Fundo "Deep Void" (Quase preto, levemente azulado). |
| \`--glass\` | \`rgba(66, 79, 105, 0.25)\` | Base para os Cards e Headers (Efeito Vidro). |
| \`--neon-p\` | \`#611af0\` | **Roxo (Primary):** Bordas de destaque, foco. |
| \`--neon-g\` | \`#22ff7a\` | **Verde (Success):** Checkboxes, botões de salvar. |
| \`--neon-r\` | \`#ff3131\` | **Vermelho (Danger):** Botão limpar, erros. |

### Efeitos Especiais
* **Glassmorphism:** Utilizamos \`backdrop-filter: blur(12px)\` em headers e modais para criar o efeito de desfoque no fundo.
* **Feedback Tátil:** Botões e cards possuem \`:active { transform: scale(0.98); }\` para dar sensação de clique físico.

---

## 3. Funcionalidades JavaScript (Core)

Toda a lógica está embutida no \`index.html\` para reduzir requisições HTTP.

### 3.1 Long Press (Edição)
Em vez de poluir a interface com um botão "Editar", usamos o gesto de segurar o item.

* **Lógica:**
    1.  Ao tocar (\`touchstart\`/\`mousedown\`), inicia um timer de **800ms**.
    2.  Se soltar (\`touchend\`/\`mouseup\`) ou mover o dedo (\`touchmove\`) antes do tempo, o timer é cancelado.
    3.  Se o timer completar, dispara \`openModal()\` e vibra o celular (\`navigator.vibrate(100)\`).
* **Proteção:** O evento ignora cliques dentro do \`.checkbox-wrapper\` para não abrir o modal ao tentar marcar o item.

### 3.2 Modal e Autocomplete (O "Hack" do Datalist)
O campo de **Categoria** sugere as categorias existentes.

* **Problema Nativo:** Em mobile, o \`<datalist>\` muitas vezes não abre se o campo estiver vazio ou exige dois cliques.
* **Solução (The Focus Hack):**
    \`\`\`html
    <input onmousedown="if(this.value === ''){this.value=' ';this.value='';}" ... >
    \`\`\`
    Isso insere e remove um espaço milimetricamente rápido ao clicar. O navegador entende que houve "digitação" e força a abertura da lista de sugestões imediatamente. **NÃO REMOVER ESTE CÓDIGO.**

### 3.3 Checkbox Otimista
Para a interface parecer instantânea:
1.  Ao clicar, o JS altera a classe visual (\`.checked\`) **imediatamente**.
2.  Dispara o \`fetch('/toggle_item/...')\` em segundo plano.
3.  Não espera a resposta do servidor para atualizar a tela (UI Otimista).

---

## 4. Manipulação de DOM (Jinja2)

O HTML é gerado dinamicamente pelo Python (Flask).

* **Categorias:** O loop \`{% for cat, itens in categorias.items() %}\` cria as seções.
* **Toggle de Seção:** Clicar no título da categoria esconde/mostra a lista (\`display: none/block\`).
* **Estado Inicial:** Se a lista vier vazia do backend, exibe um ícone de cesta (\`.empty-state\`).