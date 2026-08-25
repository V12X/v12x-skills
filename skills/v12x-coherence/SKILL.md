---
name: v12x-coherence
description: Auditoria de coerência visual — SEM depender de um design system. Infere a régua que o próprio app já usa (alinhamento, espaçamento, raio, tipografia) a partir dos valores medidos e aponta onde o app se contradiz: desalinhamentos de 2-3px que o olho sente e não nomeia, espaçamento fora da própria escala, raios misturados, sprawl de tipografia. Mede geometria real no navegador (bounding boxes), separa defeito de decisão, e termina num veredito. Use quando o usuário pedir "conferir alinhamento tela a tela", "as telas estão desalinhadas", "espaçamento inconsistente", "unificar os cantos", "conferir margens", "deixar a interface premium/coerente", "polir a UI", "rastrear desalinhamento entre textos e ícones", ou quando NÃO há design system definido e mesmo assim é preciso padronizar. Opcionalmente gera os tokens da régua inferida, que alimentam a v12x-design-audit. Não julga gosto nem hierarquia de significado — mede consistência.
license: MIT
metadata:
  version: "1.0.2"
---

Auditoria de **coerência visual** — a que você faz à mão, tela a tela, procurando o texto
desalinhado, a margem que fugiu, o canto com raio diferente, o espaçamento irregular. Medida.

**O que a separa da `v12x-design-audit`:** aquela compara com um sistema **dado** (os seus
tokens). Esta não precisa de sistema nenhum — a norma é **inferida do próprio app**. Ela olha
todos os valores que a tela usa, descobre a régua que o app *já quer ser* (a borda em que a
maioria alinha, o espaçamento que mais repete, o raio dominante) e marca onde o app **se
contradiz**. É o caso "não tenho design system, só quero que fique coerente e premium".

Segue o [**Método v12x**](../../METHOD.md): ferramenta antes de opinião, nenhum furo silencioso,
refute antes de reportar, veredito não pontuação.

**O encadeamento:** a régua inferida aqui pode virar o `tokens.json` que a `v12x-design-audit`
depois aplica. Pipeline: **inferir → propor o sistema → conformar.**

---

## O que ela mede, e o que ela NÃO finge medir

Premium é **consistência intencional + hierarquia**. A ferramenta entrega a primeira metade,
que é mensurável, e **aponta** a segunda — nunca inventa a terceira.

| Mede (geometria e valor, determinístico) | Não mede (fica com você) |
|---|---|
| Alinhamento (bordas quase iguais, off por 1-8px) | "Está bonito / premium?" — gosto |
| Ritmo vertical e espaçamento fora da própria escala | "A hierarquia está certa?" — significado do conteúdo |
| Raios misturados, sprawl de tipografia | "Qual espaçamento é o *certo*" — taste |
| Largura/margem inconsistente entre telas | Se um componente devia ser outro |

Prometer "gera interface premium sozinho" é o over-promise que remove funcionalidade e apaga
decisão. Consistência ela mede; beleza ela não inventa.

---

## Regra dura — sem improviso

Esta skill **mede e aponta.** Ela não é licença para refatorar telas por bom senso — foi assim
que uma auditoria irmã removeu um toggle de tema no meio do caminho. Três travas:

1. **Sem medição, sem achado.** Se você não rodou `coletar-geometria.js` e o `inferir.py`, você
   não auditou — opinou. Proibido reportar defeito a partir de screenshot no olho.
2. **Aplicação (se houver) é mecânica:** empurrar uma borda 3px, trocar um valor de espaçamento
   pelo da régua — linha a linha, do `git diff` de uma linha só. **Proibido** tocar em import,
   prop, lógica, ícone, estrutura ou comportamento. `git status` limpo antes de começar.
3. **O que não é geometria, a skill declara, não adivinha.** Ícone certo, hierarquia de
   significado, escolha estética — vão para o mapa de cobertura como **não coberto**.

---

## Por que não existe pontuação

**Nunca gere "índice de coerência" nem "nota premium".** Uma tela com 200 medidas certas e o
botão principal 4px torto pontua alto — e é o torto que o olho vê. O substituto é **contagem por
severidade + veredito**. Ex.: *2 altas, 3 médias. Incoerente até resolver as altas.*

---

## Fase −1 — Escopo, telas e âncora

1. **Inventário de telas.** Liste antes de medir: as telas, os estados (hover/foco/erro), os
   temas (claro/escuro), os breakpoints. O que não medir **entra no mapa de cobertura**.
2. **Âncora:** commit, data, telas medidas.

---

## Fase 0 — Coleta determinística

### Geometria (no navegador — a fonte de verdade)

`scripts/coletar-geometria.js` roda no navegador, **uma tela por vez**, e extrai a bounding box
de cada elemento visível. É o que permite achar o desalinhamento de 2-3px.

```
# via ferramenta de browser do agente, ou colado no console (ajuste SCREEN)
# saída: geometria-<tela>.json
```

Colete cada estado e cada tema como uma tela à parte. **Nativo (Swift):** não há geometria de
runtime fácil — a parte de *valor* (raio, espaço, tipo no código) ainda funciona, mas o
alinhamento entra como **cobertura parcial** (precisaria de screenshot + visão computacional).

### O motor

```
python3 scripts/inferir.py geometria-*.json [--emitir-tokens tokens.json]
```

Para cada tela, infere a **borda dominante** e o **ritmo dominante**, e marca os quase-alinhados.
`--emitir-tokens` grava a régua inferida para alimentar a `v12x-design-audit`. Detalhe em
`references/inferir-a-regua.md` e `references/alinhamento-e-ritmo.md`.

---

## Fase 1 — Análise

O motor faz o determinístico. A leitura crítica entra em **uma** pergunta: o desvio é engano ou
intenção? Ver Fase 2.

---

## Fase 2 — Verificação adversarial (defeito × decisão)

**A regra que faz a skill não virar ruído:**

- **Perto da régua (1..8px)** → quase-alinhado → **defeito.** Se fosse de propósito, estaria em
  0px; estar 3px torto é assinatura de erro, não de escolha.
- **Longe da régua (>8px)** → papel diferente → **decisão, ignora.** O link centralizado no meio
  de uma coluna alinhada à esquerda não é bug — é outro papel.

Antes de reportar: o elemento é visível e faz parte do fluxo, ou é medida de um wrapper invisível?
A borda dominante tem base forte (≥3-4 elementos), ou são poucos e não há norma implícita?

---

## Fase 3 — Severidade

| Nível | Critério |
|---|---|
| **Alta** | Quase-alinhamento de ≥2px numa linha forte (≥4 elementos): o olho vê. |
| **Média** | Ritmo ou espaçamento fora da própria escala; borda com base fraca. |
| **Baixa** | Largura quase-igual, raio solto, near-duplicata de tipografia. |

---

## Fase 4 — Relatório e (opcional) aplicação

Cabeçalho com âncora, veredito e **mapa de cobertura** (o que não foi medido — estados, temas,
telas, e sempre: ícone e hierarquia de significado). Depois, cada defeito com a tela, a medida, e
**a correção em px** ("puxar +3px").

A aplicação segue a Regra dura: mecânica, em lotes, com verificação de tela depois, e `git`
limpo para desfazer. Nunca refatorar — só empurrar a borda / trocar o valor.

---

## Referências e scripts

- `scripts/coletar-geometria.js` — extrai a geometria real de uma tela no navegador.
- `scripts/inferir.py` — infere a régua do app e marca os quase-alinhados; `--emitir-tokens`.
- `references/inferir-a-regua.md` — como a régua é inferida (agrupamento, moda, defeito × decisão).
- `references/alinhamento-e-ritmo.md` — bordas, ritmo vertical, largura, e o método no navegador.
