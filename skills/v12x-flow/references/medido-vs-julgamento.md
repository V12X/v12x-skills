# Medido × julgamento — a fronteira honesta

Carregar na Fase 1. Esta é a camada onde a skill não pode fingir. O que ela **mede** carrega o
veredito; o que ela **opina** entra rotulado. Confundir os dois é virar mais um revisor de UX
genérico que despeja parecer subjetivo.

## Camada 1 — Quebrado (fato)

Sai da instrumentação e das ferramentas, com evidência objetiva:

- **Erro de console** (`read_console_messages`) — `error`/`unhandledrejection` na carga ou na ação.
- **Requisição falha** (`read_network_requests`) — 4xx/5xx; ou nenhuma requisição quando o fluxo
  exigia uma (submit que não dispara nada).
- **Controle morto** — clicável que não muda estado, não dispara rede, não loga.
- **Fluxo que não completa** — a tarefa trava num passo.

É o que **dirige o veredito**. Um fluxo central quebrado é bloqueador, ponto.

## Camada 2 — Fricção medível (fato-proxy)

Objetivo, mas é proxy de usabilidade, não defeito absoluto:

- `required` ausente sem validação custom → submit vazio sem feedback.
- Alvo de toque < 44px.
- Campo sem label programático (placeholder some ao digitar; leitor de tela não anuncia).
- Ausência de estado vazio / carregando / erro num fluxo que precisa deles.
- Ação sem feedback de sucesso.
- Feature inalcançável (nenhum caminho de navegação leva até ela).

Conta na severidade, com o número medido como evidência.

## Camada 3 — Fricção de julgamento (opinião rotulada)

Aqui é juízo de especialista, e **tem que sair marcado como tal**. A regra que o torna rigoroso e
não vibe: **toda opinião amarra a uma heurística nomeada E a um caso concreto.**

Vocabulário fechado de heurísticas (Nielsen), para não inventar:

1. Visibilidade do estado do sistema · 2. Correspondência com o mundo real · 3. Controle e
liberdade do usuário · 4. Consistência e padrões · 5. Prevenção de erro · 6. Reconhecer em vez de
lembrar · 7. Flexibilidade e eficiência · 8. Estética e minimalismo · 9. Ajudar a reconhecer e
recuperar de erros · 10. Ajuda e documentação.

Errado: *"a tela de configurações ficou confusa."*
Certo: *"Configurações — heurística 6 (reconhecer > lembrar): a ação de salvar só aparece após
rolar; o usuário não vê que existe. Caso: botão 'Salvar' abaixo da dobra em `Settings`."*

Severidade máxima do julgamento é **média**, e ele **nunca** entra na contagem de bloqueadores.

## Por que a separação importa

O veredito da V12X vale porque é medido e refutado. Se a opinião se disfarça de fato, o relatório
vira o que todo mundo já faz e ninguém confia. A tabela do relatório deixa a camada explícita em
cada linha — **Quebrado**, **Fricção**, **Julgamento** — para o leitor saber o que é prova e o que
é conselho.
