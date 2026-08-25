# Inferir a régua do próprio app

Carregar quando não há design system e a norma precisa sair dos dados. O princípio: **um app
coerente repete seus valores; um incoerente tem variações que ninguém decidiu.** A régua é a
moda; o defeito é o quase-igual.

## O agrupamento (a moda, não a média)

Junte todos os valores de um tipo (bordas esquerdas, gaps, raios, tamanhos de fonte) e agrupe os
próximos (tolerância ~1-2px). O maior grupo é a **régua** daquele eixo — o valor que o app "quer".
Média não serve: com bordas em 16,16,16,64, a média (28) não existe em lugar nenhum; a moda (16) é
a linha real.

```
bordas L: [450, 450, 450, 450, 447, 452, 566]
  grupo 450 (4 membros) <- régua
  grupo 447 (1)  grupo 452 (1)  grupo 566 (1)
```

## Defeito × decisão — a regra que evita ruído

Um valor fora do grupo é **defeito** ou **decisão**, e a distância decide:

- **1..8px da régua → defeito.** O quase-igual é a assinatura do engano: se você *quisesse* outro
  valor, escolheria um claramente diferente; ficar 3px torto é erro de quem tentou alinhar e não
  conseguiu. É o que o olho sente e não nomeia.
- **>8px da régua → decisão.** Um valor claramente distinto tem papel próprio (o link centralizado,
  o card destacado). Marcar isso é ruído, e ruído destrói a confiança no relatório (Tese 3).

O limiar (8px) é folga: some com a tolerância do olho, calibrável por projeto.

## Base forte antes de norma

Uma régua só existe se **≥3-4 elementos** a estabelecem. Com 2 bordas em 450 e 1 em 447, não há
norma implícita — não invente uma. Poucos pontos = eixo não conclusivo, e isso **entra no mapa de
cobertura**, não vira achado.

## Emitir a régua como tokens

A régua inferida é um design system em potencial. `inferir.py --emitir-tokens` grava os valores
recorrentes (espaço, raio, tipo) num `tokens.json` — que a `v12x-design-audit` depois aplica.
É como um app sem sistema ganha um: **o sistema que ele já quase tinha, tornado explícito.**

## O que NÃO se infere

Cor de marca, hierarquia de significado, escolha estética. Frequência não é intenção: um cinza
errado repetido 20 vezes é consistente e errado. A régua diz o que o app **faz**, não o que
**devia**. A decisão de design fica com o humano — a skill só mostra onde o app briga consigo.
