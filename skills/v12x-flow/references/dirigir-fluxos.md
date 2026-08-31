# Dirigir fluxos — tarefa por tarefa, e os estados esquecidos

Carregar na Fase 0/1. O princípio: **usabilidade se prova completando tarefas, não vendo telas.**
Uma tela pode parecer perfeita e o fluxo que passa por ela não fechar.

## Por tarefa, não por tela

Liste as tarefas reais do produto e dirija cada uma de ponta a ponta:

- entrar / criar conta / recuperar senha
- a ação central do app (criar o objeto principal, salvar, publicar)
- convidar / compartilhar / mudar permissão
- configurar (trocar tema, preferências)
- sair / apagar / desfazer

Para cada tarefa: **ela completa?** Se trava no meio, onde e por quê. O fluzo que não fecha é o
achado mais valioso — e o único que só aparece dirigindo.

## Os estados esquecidos — onde mora metade dos defeitos

O happy path quase sempre parece ok. O que ninguém testou:

- **Vazio:** submeta o form sem preencher. Valida? Dá feedback, ou é no-op silencioso?
- **Inválido:** e-mail malformado, valor fora de faixa. O erro é claro e no lugar?
- **Estado vazio da lista:** a primeira vez, sem dados. Existe uma tela vazia, ou fica em branco?
- **Carregando:** a ação demora. Tem spinner/skeleton, ou a tela congela sem sinal?
- **Erro de rede/servidor:** desligue a rede, force um 500. O app avisa, ou trava?
- **Ação sem feedback:** cliquei "salvar" — algo confirma que salvou?

Cada um é uma coleta à parte. Nomeie o estado (`window.__V12X_STATE__ = 'lista-vazia'`).

## Instrumentar cada ação

Depois de **cada** clique/submit, junte três fontes:

1. `scripts/instrumentar.js` — controles, labels, validação, erros de runtime acumulados.
2. `read_console_messages` — o log inteiro (o `error` de carga acontece antes do hook JS).
3. `read_network_requests` — requisição 4xx/5xx é fato; nenhuma requisição quando devia haver
   (o submit que não dispara nada) também é fato.

Um clique que não muda a tela, não dispara requisição e não loga nada = **controle morto**,
bloqueador ou alta conforme a centralidade.

## Mapa de cobertura de fluxos (Tese 2)

Declare, sempre, quais **tarefas e estados** foram dirigidos e quais não:

```
COBERTO: login (feliz/vazio/inválido) · criar espaço (feliz) · desktop
NÃO COBERTO: app autenticado além de criar · estados de carregando · erro de servidor · mobile
```

"Não dirigi o fluxo de convite" ≠ "o convite está ok". A tarefa que você não abriu é a que
esconde o bloqueador.

## Nativo (iOS/Swift)

Sem navegador, dirija pelo **simulador** (as ferramentas de simulador do host): instalar, abrir,
tocar, digitar, capturar tela. Não há `getBoundingClientRect` nem console web — então a camada
medível encolhe: dá para checar se o fluxo **completa**, se a ação **responde**, e ler o **log do
app** (os erros de runtime aparecem lá). Alvo de toque e label programático exigem inspeção da
árvore de acessibilidade. Declare a diferença de cobertura entre web e nativo — nunca finja que o
nativo teve a mesma instrumentação que o web.

## Verificação adversarial

Antes de reportar: reproduza. Um "fluxo quebrado" que na verdade era falta do dado certo é
cobertura, não bug. Um "atrito" que é confirmação deliberada não é fricção. O achado existe quando
você **reproduz** o defeito com o estado certo.
