# Cobertura e estados

Carregar sempre. É a aplicação da Tese 2 (nenhum furo silencioso) ao caso de UI — e aqui ela é
mais importante que em qualquer outra auditoria, porque **uma varredura de telas parece completa
quando não é.**

O princípio: **a varredura vê o que está na tela naquele instante.** Tudo o que exige uma
interação, um tema, um tamanho ou um dado diferente **não foi visto** — e é exatamente onde a
padronização vaza, porque ninguém revisa o estado de erro do formulário.

---

## O que uma varredura NÃO vê (e precisa ser declarado)

| Lacuna | Por que escapa | Como cobrir |
|---|---|---|
| **Estados de interação** — hover, foco, active, disabled | só existem sob interação | varredura separada com o estado forçado |
| **Estados de dado** — erro, vazio, carregando, sucesso | dependem de dado ou falha | acionar o estado, varrer |
| **Tema** — escuro/claro | tokens diferentes por tema | varrer cada tema como coleta separada |
| **Breakpoint** — mobile, tablet | CSS responsivo troca valores | varrer cada viewport suportado |
| **Modal, drawer, tooltip, menu** | fechados no load | abrir cada um e varrer |
| **Telas atrás de login/permissão** | inacessíveis à varredura | autenticar, ou declarar |
| **Conteúdo longo/curto** | truncamento e reflow mudam layout | testar com dado real extremo |
| **Impressão, e-mail** | folha de estilo própria | quase sempre esquecidos — declarar |

**Regra:** o que não foi varrido entra no relatório como `NÃO COBERTO`, nominalmente. "14 telas
varridas" sem dizer que nenhum estado de erro foi visto passa uma confiança que não foi
conquistada.

---

## Como varrer os estados

O coletor lê o que está pintado — então basta **forçar o estado antes de coletar**.

**Estados de interação**, no navegador:

```js
// foco: dispara e varre
document.querySelector('.input-field').focus();
// depois rode o coletar-tela.js com o nome "checkout · input:focus"
```

Para `hover`, a via confiável é o DevTools (forçar estado no painel de elementos) ou uma classe
equivalente que o design system já defina (`.is-hover`). Simular `mouseover` nem sempre aplica o
`:hover` do CSS.

**Tema**, em geral um atributo na raiz:

```js
document.documentElement.setAttribute('data-theme', 'dark');
// varra de novo, com o nome "home · dark"
```

**Breakpoint**: redimensione a janela para cada largura suportada e varra novamente. O coletor já
registra `viewport` e `tema` na saída, então as coletas não se confundem.

**Modais**: abra, varra, feche. Cada um é uma coleta com nome próprio.

Nomeie cada coleta pelo par **tela + estado** (`checkout · erro`, `home · dark`). O nome vira a
etiqueta em `onde`, e é o que faz o relatório apontar o lugar certo.

---

## Priorização honesta

Varrer tudo é caro. A ordem que mais dá retorno:

1. **As telas de maior tráfego**, em tema claro e desktop — a base.
2. **Estado de erro e disabled dos formulários** — os campeões de desvio, porque quase nunca
   foram desenhados no design system e alguém improvisou um vermelho.
3. **Dark mode**, se o produto tem — costuma ter uma segunda paleta inteira fora do sistema.
4. **Mobile** — CSS responsivo é onde valores mágicos se escondem.
5. O resto, declarado como não coberto até ser feito.

Uma auditoria que cobre 1 e 2 e **diz** que não cobriu 3, 4 e 5 vale mais que uma que alega cobrir
tudo e olhou só o load da home.

---

## O caso especial: valores que só existem em um estado

Se `--color-danger` só aparece no estado de erro e você nunca varreu o estado de erro, o
relatório vai dizer que o token **não é usado** — e alguém pode concluir que ele é morto e
removê-lo.

Por isso o mapa de cobertura protege nos dois sentidos: **impede afirmar que algo está conforme
sem ter olhado, e impede afirmar que um token é inútil quando o estado que o usa nunca foi
varrido.**
