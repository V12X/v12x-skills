# Alinhamento e ritmo — o método no navegador

Carregar para a parte geométrica. Só o **app rodando** dá a verdade do que está pintado:
`getBoundingClientRect` devolve a posição exata de cada elemento, e é aí que mora o
desalinhamento de 2-3px que o código não denuncia (herança, flexbox, margem colapsada).

## Bordas

Para cada tela, colete `L` (esquerda), `R` (direita) e `cx` (centro) de cada elemento. Agrupe
cada eixo (ver `inferir-a-regua.md`):

- **Esquerda:** a coluna de conteúdo. A régua é a borda em que a maioria alinha; o quase-igual
  (1..8px) é o texto/ícone que fugiu da coluna.
- **Direita:** captura o elemento com largura levemente errada (borda direita torta mesmo com a
  esquerda certa).
- **Centro (`cx`):** o que deveria estar centralizado e ficou 2px para um lado.

Ignore o container full-bleed (largura ≈ viewport): ele não alinha nada.

## Ritmo vertical

Ordene os elementos por `T` (topo) e meça o **gap** entre o fundo de um e o topo do próximo. Um
app polido tem um ritmo (ex.: 16px repetido); o gap fora do ritmo dominante é o respiro que
alguém ajustou à mão e esqueceu. Mesmo agrupamento, mesma regra defeito × decisão.

```
logo   ↓ 16px   título   ↓ 16px   campo   ↓ 11px   campo   ← 11 é o fora-do-ritmo
```

## Largura e margem entre telas

Larguras que se repetem definem os "tamanhos" do app (o card, o campo, o botão). A quase-igual
(uma a 380, outra a 377) é engano. E a **margem de conteúdo** (borda esquerda dominante) deve ser
a mesma tela a tela — se cada tela alinha numa coluna diferente, o app inteiro treme ao navegar.

## Estados e temas são telas diferentes

Hover, foco, erro, disabled, claro, escuro: cada um é uma coleta à parte. Uma varredura só do
estado de repouso **não vê** o botão que cresce 1px no hover e quebra o alinhamento. O que não
for coletado é declarado não coberto — nenhum furo silencioso.

## Nativo (Swift/iOS)

Sem runtime de navegador, não há `getBoundingClientRect`. A parte de **valor** (raio, espaço,
tipo lidos do código) funciona; o **alinhamento** exigiria screenshot + visão computacional ou um
snapshot da árvore de acessibilidade — mais ruidoso. Até existir, alinhamento nativo é **cobertura
parcial declarada**, nunca "tudo alinhado" por omissão.
