---
name: v12x-design-audit
description: Auditoria de conformidade ao design system, com aplicação das trocas. Varre tela a tela o que é realmente pintado, compara com os tokens (cor por ΔE perceptual, raio/espaço por distância, fonte por família), produz a tabela "valor usado → token" e aplica os swaps com verificação. Use quando o usuário pedir "aplicar o design system", "padronizar o layout", "as fontes não foram trocadas", "substituir uma cor específica", "o corner dos campos está errado", "varrer tela a tela", "checar conformidade de UI", "o protótipo não segue o design system", "auditar UI/UX", ou ao aplicar um design system definido DEPOIS que as telas já existiam. Cobre cor, tipografia, raio, espaçamento e sombra, com mapa de cobertura declarando estados e telas não varridos.
license: MIT
metadata:
  version: "1.0"
---

Auditoria de **conformidade ao design system** — e a aplicação das trocas.

O caso que esta skill existe para resolver: **o design system foi definido depois.** As telas já
existem, o protótipo já roda, e agora é preciso fazer tudo obedecer aos tokens. As dores são
sempre as mesmas: fonte que não foi trocada em algum canto, uma cor específica repetida em
lugares que ninguém acha, o raio de um campo fora da escala.

Esta skill segue o [**Método v12x**](../../METHOD.md): ferramenta antes de opinião, nenhum furo
silencioso, refute antes de reportar, veredito não pontuação. O alvo muda — aqui a norma é o
**seu design system**, não uma norma de segurança — mas o processo é o mesmo.

**Por que é híbrida, e isso não é opcional:** o **app rodando** é a única fonte de verdade do que
é realmente pintado (pega o CSS que o código esconde, estilo herdado, tema de biblioteca). Mas
**só no código dá para trocar**. Varredura que não volta ao código gera relatório que ninguém
aplica; linter de código que nunca viu a tela reporta o que não aparece e perde o que aparece.
As duas pontas se unem pelo **valor bruto** (`#3a3a3a`, `7px`, `Arial`), que é a chave comum.

---

## Por que não existe pontuação

**Nunca gere "89% de conformidade" nem "nota do design system".** Uma tela com 200 valores
certos e o **botão primário fora da marca** pontua alto — e é exatamente o caso que importa.
Conformidade média esconde o desvio visível.

O substituto é **contagem por severidade + veredito de handoff**. Exemplo: *1 crítica, 3 altas.
Não aprovar o handoff até resolver as críticas.*

---

## Fase −1 — Escopo e âncora

1. **Onde está o design system?** `tokens.json` (formato W3C ou plano), CSS custom properties,
   `tailwind.config`, ou o arquivo que o time usa. Sem tokens não há norma — e sem norma não há
   auditoria, só opinião. Se não existir, o primeiro entregável é **extrair** o sistema de fato
   (os valores mais usados viram os tokens candidatos).
2. **Qual o inventário de telas?** Liste-as antes de varrer: as que existem, as que exigem login,
   os modais, os estados. O que não entrar na lista não é varrido — e **entra no mapa de
   cobertura**.
3. **Ancore:** commit do código, data, e a lista de telas varridas. Auditoria de UI sem âncora
   não pode ser comparada com a próxima.

**Regra de cobertura (Tese 2), e aqui ela é decisiva:** uma varredura de telas estáticas **não
vê** hover, foco, disabled, erro, empty state, dark mode, nem o modal que não foi aberto. É
justamente onde a padronização vaza. Isso **entra no relatório como não coberto**, sempre.

---

## Fase 0 — Coleta determinística

Os dois lados. Nenhum julgamento ainda — só inventário.

### Tela (a verdade do que é pintado)

`scripts/coletar-tela.js` roda no navegador e tabula cada valor visual com onde aparece. Uma
**tela por vez**; o nome da tela vira etiqueta.

```bash
# via ferramenta de browser do agente, ou colado no console
# saída: usados-<tela>.json
```

Varra também, como coletas separadas: **cada estado relevante** (hover/foco/erro/disabled),
**cada tema** (claro/escuro) e **cada breakpoint** que o produto suporta. O que não for varrido é
declarado.

### Código (onde a troca acontece)

```bash
bash scripts/coletar-codigo.sh . > usados-codigo.json
```

Coleta hex/px/font **hardcoded** com `arquivo:linha`, e **ignora** o que já usa token
(`var(--x)`, `theme.x`, `$var`) — isso já é conforme.

### Mapeamento (o coração determinístico)

```bash
python3 scripts/mapear.py --tokens tokens.json \
  --usados usados-home.json usados-checkout.json usados-codigo.json \
  --json mapa.json
```

Para cada valor usado, encontra o token mais próximo:

| Tipo | Métrica | Leitura |
|---|---|---|
| **Cor** | ΔE CIEDE2000 (perceptual, não diferença de hex) | `<1` imperceptível · `1–3` só lado a lado · `3–10` distinta · `>10` outra cor |
| **Raio, espaço, tamanho** | distância absoluta em px | `0` conforme · `≤1px` quase certo · `≤3px` provável · `>3px` sem token |
| **Fonte** | família normalizada | exata ou **fora do sistema** |

Saída: tabela `valor → token sugerido`, com confiança, ocorrências e onde. É ela que **dirige a
troca** — não é relatório de leitura, é plano de execução.

---

## Fase 1 — Análise

Carregue a referência conforme o que apareceu:

| Camada | Quando | Referência |
|---|---|---|
| **Cobertura e estados** | sempre — define o que a varredura não viu | `references/cobertura-e-estados.md` |
| **Aplicação segura** | quando for trocar de fato | `references/aplicacao-segura.md` |

**O que a ferramenta não decide:** se `#e11d48` é o `danger` errado ou um vermelho **proposital**
daquele componente. A máquina mede a distância; **a intenção é leitura crítica.** Priorize tempo
nos casos `media`/`nenhuma` — os `exato`/`alta` são mecânicos.

---

## Fase 2 — Verificação adversarial

Nenhuma troca entra no plano sem passar por aqui:

1. **Onde exatamente?** `arquivo:linha` (código) ou seletor + tela (runtime). Sem âncora, não
   troca.
2. **É mesmo desvio?** O valor pode já vir de um token por outro caminho (herança, tema,
   biblioteca). Se vier, **não é achado** — a troca seria ruído.
3. **É one-off proposital?** Ilustração, logo de terceiro, gráfico com escala própria, estado de
   marca de campanha. Um desvio intencional **não é falha** — é decisão de design. Rebaixe ou
   registre na linha de base.
4. **A troca muda o layout?** Trocar `15px → 16px` desloca tudo em volta. Espaçamento tem risco
   de regressão maior que cor — separe os dois lotes.

**Calibragem:** vale mais trocar 5 valores certos que 30 duvidosos. Uma troca errada num
componente compartilhado quebra dezenas de telas de uma vez.

---

## Fase 3 — Severidade

Por **impacto visual e de marca**, não por quantidade:

| Nível | Critério |
|---|---|
| **Crítica** | Fonte fora do design system, ou elemento que define a marca fora do token (botão primário, cor de marca, cor semântica de erro/sucesso). **Bloqueia o handoff.** |
| **Alta** | Desvio sistemático (mesmo valor errado em muitos lugares — indica componente errado propagado), ou near-miss em elemento de marca. |
| **Média** | Desvio isolado com distância visível; exige decisão de intenção. |
| **Baixa** | Diferença imperceptível (ΔE<1, ≤1px) em elemento secundário. |

Um desvio **repetido** sobe de nível: 14 ocorrências não são 14 erros, são **um componente
errado** — e a correção é no componente, não nas 14 telas.

---

## Fase 4 — Relatório e aplicação

Cabeçalho com âncora, veredito e **mapa de cobertura**:

```
Conformidade · commit a1b2c3d · 2026-08-19 · 14 telas varridas
1 crítica · 3 altas · 1 média · 2 baixas
VEREDITO: não aprovar o handoff até resolver as críticas.

COBERTO: 14 telas (claro, desktop) · código (CSS + componentes) · cor, tipografia, raio, espaço
NÃO COBERTO: estados (hover/foco/erro/disabled) · dark mode · mobile · 3 modais não abertos
             · telas atrás de login
```

Depois, para cada achado: `valor → token`, ocorrências, onde, e a nota de confiança.

**A aplicação** segue `references/aplicacao-segura.md` — em lotes por tipo, do mais seguro para o
mais arriscado, com verificação na tela depois de cada lote. Nunca troque tudo de uma vez.

### Linha de base

Se existir `.design-baseline.md` na raiz, leia antes de reportar e **omita o que estiver lá como
desvio aceito** (o one-off proposital), citando só a contagem. Formato:

```markdown
- `.grafico-receita` — paleta própria do gráfico — aceito em 2026-08-19 por: escala de dados, não é UI
```

### O ciclo

1. **Persistir** o relatório e o `mapa.json` em `.design-reports/AAAA-MM-DD/`. A próxima
   auditoria **diffa**: valor que voltou é regressão.
2. **Cada correção vira verificação permanente** — um lint de token no CI, ou um teste que falha
   se um hex hardcoded reaparecer. Achado que só vive no relatório volta.
3. **Reauditar depois de aplicar** — a Fase 0 inteira. Troca de estilo introduz regressão visual
   com frequência.

---

## Quando estiver criando telas

Preventivo: antes de escrever um componente novo, use os tokens desde o primeiro commit.
Conformidade nasce barata e se aplica cara.

---

## Referências e scripts

- `scripts/coletar-tela.js` — varredura do que é realmente pintado, tela a tela (somente leitura).
- `scripts/coletar-codigo.sh` — inventário de valores hardcoded, com `arquivo:linha`.
- `scripts/mapear.py` — motor de mapeamento: ΔE de cor, distância numérica, família de fonte;
  emite a tabela `valor → token` e o veredito.
- `references/cobertura-e-estados.md` — o que uma varredura não vê, como varrer estados e temas,
  e como declarar a lacuna.
- `references/aplicacao-segura.md` — ordem dos lotes, o que é automático e o que exige decisão,
  verificação depois da troca, e como não quebrar o layout.
