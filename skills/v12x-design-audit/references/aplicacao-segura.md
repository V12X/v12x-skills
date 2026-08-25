# Aplicação segura das trocas

Carregar quando for **aplicar** o mapeamento, não só reportar.

## Antes de tudo — a trava que não se contorna

A aplicação é **mecânica**: `um literal → um token`, linha a linha, saído do `mapa.json`. Não é
uma oportunidade de melhorar a tela. Num app real, o modelo "melhorou" e **removeu um toggle de
tema** no meio de uma suposta auditoria — o oposto do que a skill promete.

- **`git status` limpo antes de começar.** Sem isso, não dá para `git checkout`/`stash` desfazer
  um escorregão. Se o repo está sujo, pare e peça para commitar/limpar antes.
- **Cada troca passa no teste de uma linha:** o `git diff` daquela linha mostra **só** um valor
  virando um token? Se removeu import, mudou prop, apagou handler, trocou ícone ou mexeu em
  lógica — **você saiu da skill.** Reverta a linha e reporte como fora de escopo.
- **Sem `mapa.json`, não se aplica nada.** Editar a partir de leitura de tela ou intuição é
  improviso, não auditoria. Aqui a skill deixa de auditar e
passa a mexer no layout — e uma troca errada num componente compartilhado quebra dezenas de telas
de uma vez.

O princípio: **trocar em lotes, do mais seguro para o mais arriscado, verificando na tela entre
os lotes.** Nunca aplicar o `mapa.json` inteiro num comando.

---

## 1. O que é automático e o que exige decisão

A coluna `confianca` do `mapa.json` decide:

| Confiança | Significado | Ação |
|---|---|---|
| `exato` | idêntico ao token (ΔE<0,5 ou 0px) | já conforme — nem entra na troca |
| `alta` | ΔE<3 ou ≤1px de distância | **candidato a troca automática** |
| `media` | ΔE 3–10 ou 2–3px | **decisão humana** — pode ser proposital |
| `nenhuma` | sem token próximo | **decisão humana** — ou falta token, ou é one-off legítimo |

`nenhuma` merece atenção especial: às vezes o achado não é "o código está errado", é **o design
system está incompleto**. Um cinza usado em 20 lugares e sem token equivalente é um token
faltando, não 20 erros.

O mesmo vale para valor **abaixo da escala**: 16 ocorrências de `spacing: 2` num sistema cuja
menor medida é 4 não são 16 erros — é um token ausente para um caso que o sistema não previu
(no exemplo real: o respiro entre título e subtítulo, que é detalhe tipográfico e não
espaçamento de layout). Trocar as 16 para 4px engordaria todas as pilhas de texto do app. A
correção certa é **adicionar o token**, e a pergunta que decide é sempre: *o sistema previu este
caso?*

**Zero nunca é desvio.** `spacing: 0`, `cornerRadius: 0` e `padding(0)` significam "ausência
desta propriedade", e nenhum design system tokeniza ausência. Reportá-los é ruído — e ruído em
auditoria de design é o que faz o time parar de ler o relatório.

## 2. A ordem dos lotes — do seguro ao arriscado

Aplique um lote, verifique, só então o próximo:

1. **Cor** — o mais seguro. Trocar `#3a3a3a → var(--color-neutral-800)` não muda geometria; no
   pior caso, muda um tom imperceptível.
2. **Fonte (família)** — seguro no valor, mas **muda métrica**: outra família tem largura e altura
   diferentes, então o texto reflui. Verificar quebra de linha e truncamento.
3. **Raio** — visual puro, sem reflow. Seguro.
4. **Tamanho de fonte e line-height** — muda altura do texto: reflui, pode estourar container.
5. **Espaçamento (padding/margin/gap)** — **o mais arriscado**. `15px → 16px` desloca tudo em
   volta e pode quebrar alinhamentos que alguém ajustou à mão. Faça por último e em lotes
   pequenos.

## 3. Trocar no componente, não nas ocorrências

Um valor que aparece 14 vezes quase nunca são 14 erros — é **um componente errado propagado**.
Antes de trocar 14 linhas, procure a origem:

- O valor está num componente compartilhado, num CSS global, num tema?
- Se sim, **uma** troca resolve as 14. Se você trocar as 14 folhas e não a raiz, o próximo
  componente nasce errado de novo.

Isto é o equivalente, aqui, da regra "cada correção vira verificação permanente": corrigir a
origem impede o retorno.

## 4. Usar o token, não o valor do token

A troca certa referencia o token, não copia o valor dele:

```css
/* ERRADO — conforme hoje, dessincroniza amanhã */
color: #383838;

/* CERTO — segue o design system quando ele mudar */
color: var(--color-neutral-800);
```

Copiar o valor "resolve" o relatório e recria o problema na próxima mudança de marca. Se o
projeto usa Tailwind/tema, use a referência daquele sistema (`text-neutral-800`, `theme.colors…`).

## 5. Verificação depois de cada lote

Trocar sem reverificar é o erro clássico — correção de estilo introduz regressão visual com
frequência irritante.

- **Rerodar a coleta de tela** nas telas afetadas e conferir que o valor antigo sumiu **e** que
  não apareceu nenhum valor novo fora do sistema.
- **Comparar antes/depois** visualmente nas telas de maior tráfego (screenshot antes, screenshot
  depois).
- **Conferir o que reflui**: texto truncado, botão que cresceu, card que quebrou em duas linhas.
- Se o projeto tiver teste de regressão visual, rodar. Se não tiver, **isso é achado por si** —
  não há rede de segurança para a próxima troca.

## 6. Escape hatch — a linha de base

Nem todo desvio é erro. Gráfico com paleta própria, ilustração, logo de terceiro, campanha
sazonal. Em vez de "corrigir", registre em `.design-baseline.md`:

```markdown
- `.grafico-receita` — paleta própria do gráfico — aceito em 2026-08-19 por: escala de dados, não é UI — revisar em: 2027-02-19
```

A próxima auditoria omite o que está aqui e cita só a contagem. Um desvio **declarado** é decisão
de design; um desvio silencioso é dívida.

---

## Verificação adversarial nesta camada

Antes de aplicar cada troca: o valor vem mesmo hardcoded daquele `arquivo:linha`, ou é herdado de
outro lugar (e trocar ali não muda nada)? O elemento é visível em produção, ou é código morto? A
troca é no componente ou numa folha? Uma troca que não muda o que se vê é ruído — e ruído em
commit de design system é o que faz o time perder a confiança no processo.
