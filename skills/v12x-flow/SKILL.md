---
name: v12x-flow
description: Scan de fluxo e usabilidade que OPERA o app, não opina sobre o print. Dirige o app tarefa por tarefa — clica, digita, completa o fluxo, exercita os estados esquecidos (vazio, carregando, erro) — e instrumenta console, rede e controles para achar o que está QUEBRADO (fato) antes do que é friccionado (fato-proxy) e do que é heurística (opinião rotulada). Web via navegador, nativo via simulador. Use quando o usuário pedir "scan de usabilidade", "o que não funciona no app", "UX complicada", "testar os fluxos", "conferir seção por seção", "o botão não faz nada", "revisar usabilidade do app e web", "auditar UX", "estados vazios/de erro", ou quiser saber onde o app trava, não completa ou confunde o usuário. Não julga gosto; mede o que funciona, separa fato de opinião, e termina num veredito por bloqueadores — nunca numa nota.
license: MIT
metadata:
  version: "1.0"
---

Scan de **fluxo e usabilidade** — o que está quebrado, o que não funciona, e onde o usuário
trava. A auditoria que acha coisas que a de segurança não acha, porque **usabilidade é ortogonal
a segurança**: um app perfeitamente seguro pode ser intragável.

Segue o [**Método v12x**](../../METHOD.md): ferramenta antes de opinião, nenhum furo silencioso,
refute antes de reportar, veredito não pontuação.

**O diferencial, e sem ele não vale rodar:** esta skill **opera o app, não olha o screenshot.**
É a Tese 1 aplicada a UX. O modelo não vê uma imagem e "acha que está confuso"; ele **dirige** —
clica em cada controle, completa cada fluxo, instrumenta console/rede/controles — e reporta o que
**de fato** quebrou ou travou. Um review de print jamais pega o botão principal que não faz nada
no submit vazio; dirigindo, pega em segundos. Se você não vai dirigir, use outra ferramenta.

---

## As três camadas — e por que separá-las é tudo

"Usabilidade" são três coisas com status epistêmico diferente. Misturá-las é o que faz os
revisores de UX de IA serem rasos. Aqui elas ficam **separadas e rotuladas**:

| Camada | O que é | Peso |
|---|---|---|
| **Quebrado** | erro de console, requisição falha, controle que não dispara nada, fluxo que não completa, estado que nunca resolve | **Fato** — dirige o veredito |
| **Fricção medível** | `required` ausente sem feedback, alvo de toque <44px, campo sem label, ausência de estado vazio/carregando/erro, ação sem feedback, feature inalcançável | **Fato-proxy** — conta na severidade |
| **Fricção de julgamento** | heurística (Nielsen), carga cognitiva, copy confusa, modelo mental errado | **Opinião** — anexa, rotulada, NÃO entra no veredito |

O **fato** carrega o veredito; a **opinião** entra marcada como juízo, amarrada a uma heurística
nomeada **e a um caso concreto** — nunca "achei que ficou confuso".

---

## Regra dura — dirige e registra, não refatora

Esta skill **opera e mede.** Ela **não** conserta a UI, não "melhora" um fluxo, não mexe no
código por conta própria — foi o improviso que apagou um toggle de tema num app real. Ela dirige,
instrumenta, reporta. A correção é do usuário (ou de uma sessão separada, com o achado em mãos).

---

## Por que não existe pontuação

**Nunca gere "usabilidade 78/100".** Um app com 200 detalhes bons e o **login que não funciona**
pontua alto — e é o login que importa. O substituto é **contagem de bloqueadores + fricção por
severidade + go/no-go**. Ex.: *2 fluxos bloqueados, 5 fricções altas. Não entregar até os fluxos
completarem.*

---

## Fase −1 — Escopo, tarefas e âncora

1. **Inventário de TAREFAS, não de telas.** Usabilidade é completar tarefas ("criar espaço",
   "trocar tema", "convidar alguém", "entrar"), não ver telas. Liste as tarefas do produto.
2. **Acesso.** Fluxo rico mora atrás do login. Sem credencial de teste, você audita só a
   superfície não-autenticada — e isso **entra no mapa de cobertura**, declarado.
3. **Ancore:** commit, data, plataforma (web/nativo), tarefas na lista.

---

## Fase 0 — Dirigir e instrumentar

Operar o app. Nenhum julgamento ainda — só o que a máquina registra.

1. **Suba o app.** Web: dev server + navegador. Nativo: simulador iOS.
2. **Instale a instrumentação e audite o estado inicial** com `scripts/instrumentar.js`
   (alvo de toque, label ausente, form sem validação, controle morto, erros de runtime).
   **Use também `read_console_messages` e `read_network_requests`** — o `error` de carga acontece
   antes do hook JS; a ferramenta pega o log inteiro.
3. **Dirija cada tarefa da lista:**
   - complete o fluxo feliz — ele completa?
   - **exercite os estados esquecidos:** submeta vazio (valida?), com dado inválido (erra bem?),
     veja a tela vazia (existe?), o carregando (existe?), o erro (existe?);
   - após **cada** ação: re-rode `instrumentar.js`, leia console e rede. Requisição 4xx/5xx,
     `error` no console, clique que não dispara nada = **fato**.
4. Nomeie cada estado (`window.__V12X_STATE__`) — vira etiqueta no relatório e no mapa de cobertura.

---

## Fase 1 — Análise por camada

Classifique cada sinal medido nas três camadas (ver `references/medido-vs-julgamento.md`). A
leitura crítica entra só na camada de julgamento — e sai rotulada. Detalhe de como dirigir
tarefa por tarefa e cobrir os estados em `references/dirigir-fluxos.md`.

---

## Fase 2 — Verificação adversarial

Nenhum achado entra sem passar:

1. **Está quebrado, ou faltou dado/estado?** Um fluxo que "não completa" porque você não tinha o
   registro certo não é bug — é cobertura. Reproduza com o estado certo.
2. **É fricção real, ou decisão de design?** Um passo a mais pode ser confirmação deliberada.
   Refute antes de chamar de fricção.
3. **Reproduza o defeito** — os passos exatos. Sem repro, é impressão.

---

## Fase 3 — Severidade

| Nível | Critério |
|---|---|
| **Bloqueador** | o fluxo **não completa** (login não entra, submit não faz nada, erro que trava) |
| **Alta** | fricção que faz o usuário falhar ou desistir; estado de erro/vazio ausente num fluxo central |
| **Média** | atrito real mas contornável; label/feedback ausente; alvo de toque pequeno |
| **Baixa** | polimento. Julgamento de heurística entra aqui **no máximo**, sempre rotulado. |

---

## Fase 4 — Relatório

Cabeçalho com âncora, **veredito** (bloqueadores + contagem) e **mapa de cobertura de FLUXOS**:

```
Fluxo & usabilidade · commit a1b2c3d · 2026-08-27 · web
1 bloqueador · 2 altas · 3 médias
VEREDITO: não entregar — o login não completa no submit vazio (nenhum feedback).

COBERTO: login (feliz, vazio, inválido) · superfície não-autenticada · desktop
NÃO COBERTO: app autenticado (sem credencial) · estados de carregando · mobile · fluxo "criar"
```

**Verificado e sólido:** liste os fluxos que **completam** com evidência ("criar espaço completa,
com estado de carregando e sucesso") — a contraparte positiva, prova que você dirigiu, não amostrou.

Para cada achado: **camada** (quebrado/fricção/julgamento), o **fluxo + passos de repro** (ou
`arquivo:linha` quando for defeito de código), a evidência (erro de console, requisição, medida),
e a correção. Julgamento sempre marcado como tal, com a heurística nomeada.

**Issues acionáveis** (opcional, como na `v12x-scan`): cada achado confirmado vira uma issue
pronta — título, evidência, passos de repro, correção, critérios de aceite. É o que fecha o ciclo.

---

## Referências e scripts

- `scripts/instrumentar.js` — audita um estado no navegador (controles, labels, validação, erros).
- `references/dirigir-fluxos.md` — dirigir tarefa por tarefa, exercitar os estados esquecidos,
  o mapa de cobertura de fluxos, e o caso nativo (simulador iOS).
- `references/medido-vs-julgamento.md` — as três camadas, as heurísticas nomeadas, e a fronteira
  honesta entre o que a skill mede e o que ela só opina (rotulado).
