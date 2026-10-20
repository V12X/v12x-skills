---
name: v12x-scan
description: Auditoria de segurança em profundidade, com ferramentas determinísticas antes da análise por leitura, verificação adversarial de cada achado e relatório acionável. Use quando o usuário pedir "auditar segurança", "revisar segurança", "varredura de segurança", "tem vazamento?", "posso publicar isso?", "está seguro para open source?", "antes de publicar", "checar segredos", "auditar antes de entregar ao cliente", "hacker acessa pelo frontend", "checar IDOR/SSRF/XSS", "auditar meu agente/MCP", ou antes de tornar um repositório público, publicar app na loja, entregar código a terceiro, ou ligar multi-tenancy. Autossuficiente: cobre os fundamentos (segredos, RLS, auth, rate limit, pagamento, LLM, deploy, injeção) e vai além com aplicação web (IDOR, mass assignment, SSRF, XSS, CORS/CSRF, upload), backends fora de TS/JS (Python, Go, Ruby, PHP, Java), apps agênticos/LLM (injeção de prompt, MCP, agência excessiva), iOS/Swift nativo, isolamento entre inquilinos, cadeia de suprimento/CI e limpeza de contexto interno.
license: MIT
metadata:
  version: "1.7.0"
---

Auditoria de segurança para código que vai a produção, à loja, ao cliente ou ao público.

**Esta skill é autossuficiente.** Os fundamentos (segredos, RLS, auth, rate limit,
pagamento, LLM, deploy, injeção) estão em `references/fundamentos.md`, e sobre eles a skill
acrescenta as camadas e o processo que tornam o resultado confiável:

1. **Ferramentas determinísticas antes da leitura** — o que um scanner acha, o scanner acha
   melhor, mais barato e sem alucinar.
2. **Verificação adversarial de cada achado** — auditoria por leitura tem taxa alta de falso
   positivo, e falso positivo treina o usuário a ignorar o relatório.
3. **Aplicação web, em qualquer linguagem** — IDOR, mass assignment, SSRF, XSS, CORS/CSRF,
   upload, cabeçalhos. É a camada do "ataque pelo frontend": ler suas rotas no navegador e
   bater direto na API. Os padrões existem para TS/JS **e** para backends em Python, Go, Ruby,
   PHP e Java — senão o furo é silencioso.
4. **Apps agênticos e LLM** — injeção de prompt indireta, confiança em servidor MCP, agência
   excessiva, exfiltração pelo canal de saída. A superfície nova, onde o dano não é só fatura.
5. **iOS e Swift nativo** — camada que a maioria das skills de segurança web ignora.
6. **Isolamento entre inquilinos, cadeia/CI e limpeza de contexto interno** — antes de
   multi-tenancy, antes de publicar e antes de abrir código.

> Se você também tem a skill `vibe-security` instalada, ela aprofunda os oito fundamentos com
> exemplos por framework. A v12x-scan não depende dela — mas as duas convivem bem.

---

## Por que não existe pontuação

**Nunca gere "nota de segurança de 0 a 100" nem "status Passou/Falhou" por categoria.**
Se o usuário pedir, explique e ofereça o formato correto.

Motivos:

- **Não é reprodutível.** A mesma base auditada duas vezes gera notas diferentes. Uma métrica
  que muda sem o código mudar não é métrica.
- **Dá falsa confiança.** "87/100" convida a publicar. Uma única credencial exposta é
  suficiente para o comprometimento total, e nenhuma média aritmética expressa isso.
- **Esconde severidade.** Categoria com dezenove checagens boas e uma falha crítica pontua
  alto. É exatamente o caso perigoso.
- **Não é assim que a indústria faz.** O CVSS pontua **cada vulnerabilidade** com rubrica
  definida, nunca uma base de código inteira de forma holística.

O substituto correto é: **contagem por severidade + veredito de publicação**. Exemplo:
*2 críticas, 3 altas, 5 médias. Não publicar até as críticas serem resolvidas.*

---

## Fase −1 — Escopo, ameaça e âncora

Cinco minutos que calibram todo o resto. Sem isso a severidade sai desregulada.

1. **O que está em jogo aqui?** Identifique os ativos reais deste projeto: dado de usuário?
   dinheiro? credencial de terceiro? dado entre inquilinos concorrentes? A resposta muda o
   que é Crítico. Num cofre, a área de transferência é Crítica; num site estático, nem
   existe.
2. **Qual o evento que motiva a auditoria?** Publicar repositório, mandar para a loja,
   entregar a cliente, ligar multi-tenant. Isso decide quais referências carregar.
3. **Ancore o relatório**, para ele ser reprodutível e comparável:

```bash
echo "commit: $(git rev-parse HEAD 2>/dev/null || echo 'sem git')"
echo "data:   $(date '+%Y-%m-%d %H:%M')"
echo "gitleaks: $(gitleaks version 2>/dev/null || echo 'AUSENTE')"
```

O cabeçalho do relatório declara o commit auditado. Auditoria sem âncora não pode ser
comparada com a próxima nem provada depois.

**Regra de cobertura, e ela é o que torna o scan confiável:** nenhuma fase pode falhar em
silêncio. Se uma ferramenta não está instalada, se um diretório foi pulado, se uma categoria
não se aplica — isso **entra no relatório** como "não coberto", nunca desaparece. Um furo
declarado é administrável; um furo silencioso é o que derruba.

---

## Fase 0 — Ferramentas determinísticas

Rode primeiro. É barato, é preciso e reduz o que sobra para leitura.

> **Atalho — rode a fase inteira de uma vez.** `scripts/fase0.sh` executa tudo desta seção,
> degrada com elegância quando falta ferramenta (cada ausência já vira "NÃO COBERTO"), detecta
> a linguagem do backend e imprime o mapa de cobertura pronto para o relatório. Prefira o
> script; os blocos abaixo documentam o que ele faz e servem de fallback manual quando ele não
> puder rodar.
>
> ```bash
> bash scripts/fase0.sh .      # alvo = diretório atual; relatórios em .security-reports/fase0
> ```
>
> Leia a saída e o mapa de cobertura antes de seguir para a Fase 1, usando as linguagens que
> ele detectou.

### Segredos: histórico E árvore de trabalho, são varreduras diferentes

**Armadilha que anula a varredura se ignorada:** `gitleaks detect` varre commits — arquivo
**não rastreado ou ignorado pelo git não é varrido**. E são exatamente os `.env` reais.
Rode os dois modos, sempre:

```bash
# 1. histórico completo (remover em commit posterior NÃO remove do histórico)
gitleaks detect --source . --redact --report-format json --report-path /tmp/gl-git.json
# gitleaks >= 8.19 renomeou `detect` para `git` (a forma antiga ainda roda, com aviso).
# scripts/fase0.sh detecta a versão e usa a forma certa sozinho.
```

**Não rode `gitleaks dir .` na raiz de projeto JS** — ele desce em `node_modules` e não
termina. Use a varredura direcionada: enumere só os não rastreados e ignorados relevantes e
varra esses (validado em projeto real: 43 arquivos em 0,3s, contra varredura completa que
não concluiu; achou 14 segredos, incluindo chave GCP num `.env.local`):

```bash
# 2. árvore de trabalho: não rastreados + ignorados, sem vendor nem binário
mkdir -p /tmp/gl-alvo && rm -rf /tmp/gl-alvo/*
{ git ls-files --others --exclude-standard; git ls-files --others --ignored --exclude-standard; } \
  | grep -vE '^(node_modules|\.next|\.build|build|dist|Pods|\.vercel|DerivedData)/' \
  | grep -vE '\.(png|jpg|jpeg|heic|webp|ico|woff2?|ttf|map)$' | while read f; do
    [ -f "$f" ] && mkdir -p "/tmp/gl-alvo/$(dirname "$f")" && cp "$f" "/tmp/gl-alvo/$f"
  done
gitleaks dir /tmp/gl-alvo --redact --report-format json --report-path /tmp/gl-dir.json
rm -rf /tmp/gl-alvo
```

Se não estiver instalado: `brew install gitleaks`.

Segredo em arquivo ignorado não é vazamento público, mas é achado quando o evento é
"entregar a cliente" ou "zipar o projeto" — o ignorado vai junto.

**Upgrade opcional que muda a natureza do achado:** `trufflehog` (via `brew`) tem modo de
**verificação ativa** — testa se a credencial vazada ainda está válida no provedor.
"Exposta E VIVA" e "exposta mas revogada" são achados de severidade diferente, e essa
distinção elimina a discussão de "mas essa chave é antiga":

```bash
trufflehog git file://. --only-verified 2>/dev/null
```

### Submódulos e o próprio .git

```bash
# submódulos carregam histórico próprio — auditar cada um
git submodule status 2>/dev/null

# se o deploy serve arquivos estáticos: o diretório .git não pode ser servível
```

Para arquivos fora do git (chaves soltas no diretório):

```bash
find . -type f \( -name '*.p8' -o -name '*.p12' -o -name '*.pem' -o -name '*.key' -o -name '*.keystore' -o -name '*.mobileprovision' \) -not -path '*/node_modules/*' -not -path '*/.build/*'
```

E os `.env` que deveriam estar ignorados:

```bash
find . -name '.env*' -not -path '*/node_modules/*' | while read f; do
  git check-ignore -q "$f" 2>/dev/null && echo "ok (ignorado): $f" || echo "EXPOSTO: $f"
done
```

### Dependências — cobrir TODOS os ecossistemas presentes

`npm audit` só cobre npm. Projeto Swift tem `Package.resolved` e ele também é cadeia de
suprimento:

```bash
# npm, se houver package-lock.json
npm audit --audit-level=high 2>/dev/null || true

# cobertura multi-ecossistema (npm + SwiftPM + o que mais houver)
# se ausente: brew install osv-scanner — e a ausência ENTRA no relatório como lacuna
osv-scanner scan source -r . 2>/dev/null || echo "NÃO COBERTO: osv-scanner ausente"
```

Verificar também: o lockfile **existe e está commitado**? Sem lockfile, cada instalação
resolve versões diferentes e o audit de hoje não vale amanhã. E scripts de ciclo de vida
(`postinstall`) no próprio `package.json` — vetor clássico de cadeia.

### Padrões estáticos

Se `semgrep` existir, rode `semgrep --config=auto --severity=ERROR .` (há regras para Swift
além de TS/JS). Se não existir, sugira `brew install semgrep`, registre como lacuna de
cobertura, e **não bloqueie a auditoria** — siga para a fase 1.

### Banco de dados: o catálogo vivo, não só as migrations

Migration é **intenção**; o catálogo do banco em produção é o que **é**. Uma migration que não
aplicou limpa, um grant dado à mão no painel, uma policy editada fora do git — nada disso está no
repositório, e só aparece lendo o banco vivo. Se a auditoria tem acesso ao banco (cliente SQL, MCP
do Supabase), leia o catálogo; se não tem, isso **entra no mapa de cobertura** como lacuna, nunca
como "RLS conferida".

```sql
-- grants de TABELA e de COLUNA por papel: o que anon/authenticated alcançam de verdade
SELECT table_name, grantee, privilege_type FROM information_schema.role_table_grants
WHERE table_schema = 'public' AND grantee IN ('anon','authenticated') ORDER BY 1,2;
SELECT table_name, column_name, grantee, privilege_type FROM information_schema.column_privileges
WHERE table_schema = 'public' AND grantee IN ('anon','authenticated') ORDER BY 1,2;

-- policies VIVAS (não as do arquivo)
SELECT tablename, policyname, cmd, roles, qual, with_check FROM pg_policies WHERE schemaname = 'public';

-- quem pode EXECUTAR cada função — em especial o que sobrou para anon
SELECT p.proname, p.prosecdef AS definer, (aclexplode(p.proacl)).grantee::regrole AS grantee
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND p.proacl IS NOT NULL ORDER BY 1;
```

**São dois bancos, e o achado precisa dizer de qual é.** As migrations descrevem o banco que
**nasce dos arquivos**: a stack local, o CI, qualquer reconstrução. Produção é outro banco, e
diverge sem ninguém ver: migration aplicada por outro caminho (MCP, painel, texto editado antes de
subir), policy criada à mão. Caso real: as três primeiras migrations subiram para produção com os
nomes das policies **sem acento**, e os arquivos sempre os tiveram **com**. Quatro replaces que
dropavam o nome sem acento valiam em produção e falhavam calados no banco dos arquivos, onde a
policy antiga continuava somando por OR. Lido só dos arquivos, parecia furo de produção; era furo
do CI. O `ledger.py catalogo` compara os dois:

```bash
python3 scripts/ledger.py catalogo --sql          # a consulta que exporta o catálogo vivo como JSON
# rode-a no banco de produção e salve o resultado em catalogo.json; depois:
python3 scripts/ledger.py catalogo . --vivo catalogo.json
```

Ele classifica cada divergência: policy que **sobrevive só no banco dos arquivos** (soma por OR
com a quase homônima, e o vivo não a tem), **grafia diferente** (mesma policy; o próximo replace
falha num dos dois), **só nos arquivos** (migration que não subiu, drop à mão) e **só no vivo**
(criada fora do git: superfície que a leitura do repositório nunca vê). Sai com 1 se houver
qualquer uma. O replay das migrations não segue SQL dinâmico (`execute format('drop policy …')`),
e avisa quando encontra; para o banco dos arquivos exato, rode a mesma consulta num banco montado
das migrations (`supabase db reset`) e passe com `--montado`.

Função de leitura executável por `anon` que "devolve vazio" ainda é achado (Baixa, de coerência):
a superfície de EXECUTE é a menor possível, não a que "por acaso não vaza". E rode os **advisors**
do provedor (no Supabase, o Security Advisor): RLS desligada, função `definer` com `search_path`
mutável, proteção contra senha vazada desligada — o provedor lista o que ele mesmo considera errado.

### `security definer` que escreve sem amarrar o chamador

Função `security definer` roda com o privilégio de quem a criou e **ignora a RLS**. Se ela faz
`update … set` ou `on conflict … do update` amarrando só pelo `id` que veio no argumento, qualquer
chamador reescreve a linha de qualquer um — o `where` de posse precisa vir do chamador validado
(`auth.uid()`, ou o `p_user` que a função extrai do JWT), nunca do parâmetro. Caso real: uma
função de mensagem do assistente fazia `on conflict (id) do update set body`, e um membro
reescrevia a mensagem do colega, mantendo o autor original. **Quatro auditorias por leitura não
viram; o grep abaixo vê:**

```bash
# toda função security definer que escreve — abrir cada uma: o where amarra a auth.uid()?
grep -rliE 'security\s+definer' --include='*.sql' . | grep -v node_modules | while read f; do
  grep -nEi 'on\s+conflict.*do\s+update|^\s*update\s+[a-z_."]+\s+set|delete\s+from' "$f" \
    | grep -vE '(^|:)[0-9]+:\s*--' | sed "s|^|$f:|"
done
```

A lista é por **arquivo** — função que não é `definer` mas mora no mesmo `.sql` aparece também, e
se descarta em segundos (o `assets/definer.test.ts` é o que separa por função). Cada linha que sair
é para abrir: o `where` (ou o `with check` do caminho) amarra a linha ao chamador? Se amarra só pelo argumento, é achado **Alta**. O `assets/definer.test.ts` transforma a
regra em teste de CI que lê as migrations e falha quando um `do update` em `definer` chega sem
`where` — a exceção fica escrita no próprio teste, com motivo. Detalhe da regra em
`references/multi-tenancy.md`.

### O ledger de cobertura: as unidades vêm do código, não da memória

O `fase0.sh` termina emitindo `.security-reports/ledger.md` (via `scripts/ledger.py`): **uma linha
por unidade de superfície**, enumerada por ferramenta — cada tabela, cada policy (tabela ×
operação), cada função SQL (com `security definer` marcada), cada Edge Function, cada bucket, cada
rota, cada workflow, cada URL scheme. Com o replay das migrations na ordem certa: `drop` remove,
`replace` sobrescreve, sobrecarga é unidade própria, e `alter`/`grant`/`revoke` movem a origem da
tabela para o último toque.

É o "nenhum furo silencioso" **verificável por máquina**. A auditoria não decide o que cobrir de
cabeça: a lista já existe, e cada unidade termina com um estado (Fase 1). Num projeto real, foram
304 unidades em 0,3 s — 114 funções `definer`, 100 policies — e a policy que escondia a crítica
apareceu na primeira rodada, com arquivo e linha.

Se já existe `.security-ledger.md` na raiz (a auditoria anterior persistiu), o rascunho **herda**
os estados cuja fonte não mudou e **reabre por diff** os que mudaram — ver Fase 4.

Com o catálogo vivo exportado, `ledger.py rascunho . --vivo catalogo.json` anota cada policy que
diverge e **acrescenta as que só existem no vivo**, com origem `catálogo vivo`. Essas nunca herdam
`coberto` de uma rodada anterior: o catálogo não tem `git diff` que prove que não mudou.

### CI e arquivos de infraestrutura

Se existir `.github/workflows/`, Dockerfile ou docker-compose, carregue
`references/cadeia-e-ci.md`. Workflow de CI é código executável com acesso a segredos, e
tem classes de falha próprias (`pull_request_target`, injeção via `${{ }}`).

---

## Fase 1 — Análise por categoria

Carregue só o que a base usa. Pule o resto sem comentar.

**Fundamentos** — sempre aplicáveis, em `references/fundamentos.md`:
segredos e variáveis de ambiente · controle de acesso no banco (RLS do Supabase, regras do
Firebase) · autenticação e autorização · rate limiting · pagamento · integração com LLM ·
configuração de deploy · injeção e validação de entrada.

**Camadas específicas** (carregue quando aplicável):

| Camada | Quando carregar | Referência |
|---|---|---|
| **Aplicação web** | há rota de API, server action ou endpoint HTTP no backend | `references/web-app.md` |
| **Linguagens de backend** | o backend **não** é TS/JS (há `.py`, `.go`, `.rb`, `.php`, `.java`/`.kt`) | `references/linguagens-backend.md` |
| **Apps agênticos / LLM** | há chamada a modelo, definição de ferramenta/tool, servidor MCP, RAG ou agente que age | `references/llm-agentes.md` |
| **iOS e Swift nativo** | há `.swift`, `project.yml`, `Info.plist` ou `.xcodeproj` | `references/ios-nativo.md` |
| **Isolamento entre inquilinos** | há coluna de organização, `tenant_id`, subdomínio por cliente, ou o projeto vai virar multi-tenant | `references/multi-tenancy.md` |
| **Pré-publicação** | o repositório vai ficar público, o código vai para um cliente, ou é entrega open source | `references/pre-publicacao.md` |

**Cobertura por linguagem, e ela é o que evita o furo silencioso:** `references/web-app.md`
mostra os padrões em TS/JS; se o backend detectado na Fase 0 for outro, carregue
`references/linguagens-backend.md` e aplique os padrões equivalentes. Reportar "autorização
coberta" tendo olhado só `.ts` num projeto Python é o furo que a skill promete não ter.

### Autorização é o que a leitura acha e a ferramenta não

Priorize tempo aqui, porque é onde scanner não ajuda e onde o dano é maior. **Este é o
"ataque pelo frontend": o navegador é público, então quem ataca lê suas rotas no JavaScript
e bate direto na API, fora da sua tela.** A defesa é toda no servidor — detalhe em
`references/web-app.md`, itens 1 e 2, que são as duas falhas mais frequentes em código
gerado com IA:

- Todo endpoint que recebe um identificador de recurso confere **se o solicitante é dono
  dele**? A falha clássica é `GET /api/documento/:id` que valida sessão e não valida posse
  (IDOR).
- O objeto do usuário é montado a partir de `req.body` inteiro? Então ele grava `role: admin`
  (mass assignment).
- Ações de administrador conferem papel **no servidor**, e não só escondem o botão?
- O identificador do usuário vem da **sessão**, e nunca do corpo da requisição?

**Cada unidade do ledger termina com um estado.** Ao percorrer uma categoria, marque no ledger o
que foi feito, com `scripts/ledger.py marcar` (por id ou por regex, em lote):

| Estado | Significa | Exige |
|---|---|---|
| `coberto` | lido inteiro, com o critério da categoria aplicado | `lido em` = commit (o `marcar` grava sozinho) |
| `amostrado` | lido em parte — e isso é declarado, não escondido | `lido em`, e a nota diz o quanto |
| `fora-de-escopo` | esta rodada decidiu não olhar | — (mas é visível) |
| `adiado` | não deu, e o motivo está na nota | nota |
| `pendente` | depende de fato fora do repositório (Fase 2) | nota com a checagem |

Duas regras sem exceção: **rodada com escopo marca o resto `fora-de-escopo`, nunca `coberto`** — é
o que impede "li as migrations recentes" de virar "RLS coberta" —; e **`planejado` no fim da
auditoria é furo silencioso**: `ledger.py validar --final` sai com 1, e o relatório não sai antes.

**Autorização não se amostra — varre-se.** Um scanner pode amostrar; autorização não. Basta
**um** handler sem checagem de posse para o dado vazar, então percorra **todos** os handlers de
rota que recebem um identificador ou fazem escrita, um a um, e cruze **cada** gate de papel do
frontend (`isAdmin`, `canEdit`, `role`) com o endpoint correspondente — confirmando que o
servidor valida o privilégio. "Revisei as principais rotas" não é cobertura; é a rota que você
não abriu que vaza. Se a lista de rotas for grande demais para varrer inteira, isso **entra no
mapa de cobertura** como amostrado, nunca como coberto.

---

## Fase 2 — Verificação adversarial

**Nenhum achado entra no relatório sem passar por esta porta.** Primeiro a âncora: **arquivo e
linha**. Sem âncora não é achado, é impressão. Depois, o teste de admissão em quatro partes. Um
candidato só é achado se nomear **os quatro**; se qualquer um faltar, descarte ou rebaixe.

1. **Quem ataca?** O principal de **menor confiança** que alcança o caminho: anônimo, membro
   comum, inquilino vizinho. Se só o próprio dono do dado chega lá, não há fronteira cruzada —
   impacto só em si mesmo não é vulnerabilidade.
2. **Que fronteira ele cruza?** A rota concreta: requisição externa → parâmetro → função
   vulnerável. Se o código só é alcançável por script local de build, por teste, ou por caminho
   autenticado de administrador, **rebaixe**.
3. **Que controle deveria barrar e não barra?** A policy, o middleware, a checagem de posse que
   existe para isso — e por que ela não cobre este caminho. **Boa prática ausente não é falha**:
   "não tem rate limit" sem um caminho que o explore é endurecimento, não achado.
4. **O que ele consegue, observável?** Consequência concreta e específica: "lê os documentos de
   qualquer usuário trocando o id na URL", não "pode causar exposição de dados". E nunca mais
   forte do que o que foi de fato demonstrado: **a severidade não pode exceder o impacto
   observado** — a leitura que prova "lê o título" não autoriza reportar "lê o documento".

Depois, tente **refutar** o achado explicitamente. Existe validação em camada anterior?
Middleware que já barra? RLS que já cobre? Se existir, o achado morre — e isso é bom.

**Achado de banco lido só nos arquivos não é "Confirmado" ainda.** Policy, grant ou função que a
auditoria viu nas migrations descreve o banco que nasce dos arquivos; se há acesso ao banco vivo,
o achado passa pelo `ledger.py catalogo` antes de receber severidade. Se o vivo diverge, o achado
é do banco dos arquivos (CI, stack local, reconstrução) e se escreve assim: "no banco que o CI
monta, X; produção não tem". Continua sendo achado — o teste do CI prova a coisa errada, e a
próxima reconstrução herda o furo —, mas a severidade é a desse banco, não a de produção. Sem
acesso ao vivo, o achado de produção fica **pendente de validação**, com a consulta como checagem.

### Os três estados de um candidato

Cada candidato que passou pela âncora termina em **exatamente um** destes:

- **Confirmado** — os quatro nomeados, com caminho completo no código e resultado observado (ou
  demonstrado por leitura sem lacuna). Só ele recebe severidade (Fase 3) e vira issue (Fase 4).
- **Refutado** — uma camada visível barra, ou falta impacto real, ou o pré-requisito é
  impossível. Fica registrado com a prova (Fase 4, linha de base), nunca descrito como achado.
- **Pendente de validação** — o caminho no código fecha, mas a conclusão depende de **um fato
  que o repositório não contém**: o interruptor no painel do provedor, o comportamento do CDN
  diante de resposta autenticada, o lag da réplica, a política de retenção do backup, o header
  que o proxy da frente adiciona. Este estado tem regras duras:
  - nomeia **o fato exato** que falta e **a checagem não destrutiva** que o dono faz para
    resolvê-lo ("Authentication → Settings → Password security: ligado?");
  - **nunca recebe severidade** — severidade é consequência demonstrada, e aqui nada foi;
  - **nunca é estacionamento para ideia especulativa**: "talvez o CDN cacheie" sem um caminho
    concreto no código é descarte, não pendência. Pendente é hipótese *precisa* com uma
    *única* incógnita fora do repositório;
  - entra no relatório em seção própria e **conta no veredito**: se o fato, confirmado, faria
    o achado Crítico, o veredito é "não publicar até o dono validar X" — a severidade continua
    sem atribuir, mas a decisão não espera.

### Crítica e Alta passam por quem não as achou

Verificar o próprio candidato é refutar com viés de confirmação: quem acabou de montar o caminho
tende a enxergá-lo fechado. Para o que importa — **todo candidato a Crítica ou Alta** — a
refutação é feita por um **verificador independente**: um subagente que recebe **só** o candidato
(âncora, caminho, resultado alegado) e acesso ao código, **sem** o contexto da caça nem a sua
conclusão, com uma ordem: *"Você não escreveu este candidato. Tente refutá-lo pelo código."* Ele
devolve um dos três estados com a prova. Se ele refutar, o candidato morre ou vira pendente — não
se "negocia". Para Média e Baixa a autorrefutação basta; o custo do subagente não se justifica.
Se o ambiente não permite abrir subagente, a Crítica/Alta fica com autorrefutação **e isso entra
no mapa de cobertura** ("Crítica/Alta sem verificador independente") — nunca em silêncio.

### Anti-padrões que esta fase existe para barrar

- Reportar desvio de checklist ou boa prática ausente como vulnerabilidade.
- Adivinhar comportamento de deploy ("provavelmente não tem WAF") em vez de marcar pendente.
- Tratar impacto só sobre o próprio usuário como fronteira cruzada.
- Reportar efeito mais forte que o observado.
- Dar severidade a pendente de validação.
- Chamar de furo de produção o que só foi lido nas migrations.
- Escrever o relatório antes de a verificação terminar.

**Regra de calibragem:** é melhor entregar cinco achados sólidos que trinta candidatos, dos
quais vinte são ruído. Falso positivo destrói a confiança no relatório inteiro.

---

## Fase 3 — Severidade

Classifique por consequência real, não por categoria teórica.

| Nível | Critério |
|---|---|
| **Crítica** | Credencial de produção válida exposta, ou qualquer usuário acessa dado de outro usuário, ou desvio total de autenticação. **Bloqueia publicação.** |
| **Alta** | Exige alguma condição (conta válida, id conhecido) mas leva a acesso indevido, manipulação de preço, ou custo ilimitado em API paga. |
| **Média** | Requer condição improvável ou o impacto é limitado. Falta de defesa em profundidade. |
| **Baixa** | Endurecimento. Não há caminho de exploração conhecido hoje. |

**Um segredo exposto é sempre Crítico até ser provado revogado.** Não rebaixe porque "é de
teste" — verifique.

**Só o confirmado é classificado.** Pendente de validação não recebe nível (Fase 2): o que entra
na tabela acima é consequência demonstrada, e pendente, por definição, ainda não demonstrou. O
que ele recebe é o lugar no veredito.

---

## Fase 4 — Relatório

Ordem obrigatória: **Crítica → Alta → Média → Baixa.** Pule níveis sem achado.

Cabeçalho com âncora, veredito e **mapa de cobertura**, antes de qualquer detalhe:

```
Auditoria do commit a1b2c3d · 2026-08-13 · gitleaks 8.x
2 críticas · 3 altas · 5 médias · 1 baixa · 2 pendentes de validação
VEREDITO: não publicar até resolver as críticas e validar o cache do CDN (pendente 1).

COBERTO: histórico git (180 commits) · árvore com ignorados · deps npm ·
         auth/autorização · RLS · iOS nativo
NÃO COBERTO: osv-scanner ausente (SwiftPM sem audit) · sem teste dinâmico ·
         binário compilado não inspecionado
```

Depois dos achados por severidade, a seção **Pendente de validação**, uma entrada por hipótese,
sem nível, com o fato que falta e a checagem que o resolve:

```
PENDENTE 1 — `vercel.json` sem `Cache-Control` nas rotas autenticadas
  Caminho: /api/documentos devolve dado do inquilino sem cabeçalho de cache.
  Fato que falta: o CDN da frente cacheia resposta autenticada por padrão?
  Checagem: curl -I com cookie de sessão; conferir `x-vercel-cache` e `age`.
  Se confirmado: Crítica (inquilino A recebe o documento de B pelo cache).
```

Pendente **não** vira issue de correção (Fase 4, issues) — vira item de verificação para o dono.
"Se confirmado" declara o que está em jogo, sem fingir que foi demonstrado.

**O mapa de cobertura é obrigatório.** É a diferença entre "não achei nada" e "não olhei".
Um leitor precisa saber exatamente o que esta auditoria não viu.

**E o ledger fecha o mapa por unidade.** Antes de escrever o relatório, `ledger.py validar
.security-reports/ledger.md --final` (com `--escopo /regex/` se a rodada teve escopo). Se sair 1, a
auditoria não acabou. No cabeçalho, a contagem por estado substitui o "coberto" em prosa:

```
LEDGER: 304 unidades · coberto 251 · amostrado 12 (rotas: 12 de 40, as de escrita) ·
        fora-de-escopo 38 (iOS: rodada só de plataforma) · adiado 3 (motivo no ledger)
```

Ao encerrar, **persista o ledger** como `.security-ledger.md` na raiz, junto do relatório e da
linha de base. É o que a próxima auditoria herda: `ledger.py rascunho` lê o anterior, mantém
`coberto` onde `git diff <lido em>..HEAD -- <origem>` está vazio, e reabre como `planejado` ("fonte
mudou desde X") o que mudou — a mesma regra de diff da linha de base, agora por unidade. "Coberto"
passa a ter data e prova; e a policy da 0001 que ninguém releu em quatro auditorias aparece como
`lido em: nunca`.

### Verificado e sólido (a prova de que a auditoria trabalhou)

Depois do mapa de cobertura, liste em uma ou duas linhas **o que foi verificado e está
correto**, com evidência — não só o que está errado:

```
SÓLIDO: router de documentos valida posse em todos os 14 handlers (routes/docs.ts) ·
        RLS ativo e derivado de auth.uid() em todas as tabelas com tenant_id ·
        segredos só via env, sem default embutido
```

Isto não é enfeite: um relatório que só lista problemas não prova que **olhou** o resto. "Auth
verificada e correta em X" é a contraparte positiva do mapa de cobertura — mostra que a categoria
foi varrida, não pulada, e é o que separa "não achei IDOR" de "confirmei posse em cada rota".
Nunca invente um ponto forte: só entra o que foi de fato verificado, com o arquivo.

Para cada achado:

**`caminho/arquivo.ts:42` — Nome específico da falha**

Um parágrafo com o caminho de exploração concreto. Depois, correção em antes e depois, com
código real do projeto e não exemplo genérico.

Feche com uma lista numerada de ações em ordem de execução. Se houver credencial exposta, a
primeira ação é sempre **revogar**, nunca "remover do código" — o segredo já vazou no
momento em que foi commitado.

### Issues acionáveis (saída opcional — é o que fecha o ciclo)

Quando o usuário quiser transformar o relatório em trabalho, gere, para **cada achado
confirmado**, uma issue pronta para colar no rastreador. É o passo que falta entre "achei" e
"cada correção vira verificação permanente": uma issue vira um PR vira um teste no CI.

Formato de cada issue, em bloco delimitado (`--- ISSUE n ---` … `--- FIM ISSUE n ---`):

- **Título:** `[Segurança] <descrição curta da falha>`
- **Labels:** `security`, mais a severidade (`crítica`/`alta`/`média`/`baixa`)
- **Problema e por que é explorável** — o caminho concreto de exploração
- **Evidência:** `arquivo:linha` com o trecho real
- **Impacto** — a consequência específica
- **Correção sugerida** — antes/depois com o código do projeto
- **Critérios de aceite** — checklist verificável (`[ ] a rota valida posse`, `[ ] teste que
  prova que o usuário B não lê o dado de A`)

**Agrupe achados triviais do mesmo tema numa issue só** (vários defaults de segredo, várias rotas
com o mesmo padrão de IDOR) — uma issue por *classe*, não por linha, para não virar spam. Um
achado Crítico ganha issue própria, sempre. E a issue nasce do achado **já refutado** na Fase 2:
nada de issue para candidato que não sobreviveu.

### Linha de base

Se existir `.security-baseline.md` na raiz, leia antes de reportar e **omita o que estiver
lá como risco aceito**, mencionando só a contagem: *"3 achados suprimidos pela linha de
base"*. Ao encerrar, ofereça registrar os aceitos — há um modelo pronto em
`assets/baseline.example.md`. Credencial exposta nunca entra na linha de base: segredo se
revoga, não se aceita.

Formato de cada entrada da linha de base:

```markdown
- `arquivo.ts:42` — nome do achado — aceito em 2026-08-13 por: <motivo> — revisar em: <data>
```

**Refutações também atravessam auditorias.** O que a Fase 2 refutou hoje será candidato de novo
amanhã — a mesma chave publicável em arquivo ignorado, o mesmo `${{ }}` que é SHA, a mesma injeção
indireta sem canal de saída. Re-litigar o mesmo não-achado a cada rodada é desperdício: num projeto
real, a chave publicável foi refutada pela **quarta auditoria seguida**. Registre a refutação na
linha de base, com **o caminho que a provou** e **o que a reabriria**, e a próxima auditoria pula
direto, mencionando só a contagem — como faz com os aceitos. Refutação e risco aceito ficam em
seções separadas, de propósito: o aceito é um achado real que se decidiu tolerar; o refutado nunca
foi achado.

```markdown
- `arquivo:linha` — candidato — refutado em AAAA-MM-DD por: <a prova> — provado em: <commit> — reabrir se: <o que mudaria a conclusão>
```

**A refutação vale enquanto a fonte não muda — e isso se confere por máquina, não de memória.**
A entrada registra o commit contra o qual foi provada; na auditoria seguinte, um `git diff
<commit>..HEAD --stat -- <arquivo>` por entrada diz se o arquivo mudou. **Arquivo mudou, refutação
reabre**, mesmo que o "reabrir se" em prosa não tenha acontecido — a prosa é o que o auditor
lembra; o diff é o que aconteceu. Mesma regra para o risco aceito: aceito em cima de um arquivo
que mudou é aceito em cima de outra coisa.

### O ciclo que fecha o furo de verdade

Uma auditoria pontual não deixa nada "à prova de furos" — o que aproxima disso é o ciclo:

1. **Persistir o relatório** em `.security-reports/AAAA-MM-DD.md` no repositório (e o JSON
   do gitleaks ao lado — `scripts/fase0.sh` já salva em `.security-reports/fase0/`), e **o ledger**
   como `.security-ledger.md`. A próxima auditoria **diffa contra a anterior**: o que voltou é
   regressão e sobe um nível de severidade; e o ledger herda o coberto que não mudou.
2. **Cada achado corrigido vira verificação permanente.** Se o achado foi "token em log",
   nasce um grep no CI que falha se o padrão voltar; se foi "tabela sem RLS", nasce o teste
   de isolamento; se foi função `security definer` escrevendo sem `where`, ou coluna nova que
   herdou o grant da tabela, entram `assets/definer.test.ts` e `assets/grants-de-coluna.test.ts`,
   que leem as migrations no CI. Achado que só vive no relatório volta. **E o teste novo precisa
   ser visto falhando uma vez**, contra um banco onde o furo ainda está aberto, antes de valer como
   prova: teste de recusa que nunca falhou pode não saber falhar. Dois casos reais, no mesmo
   arquivo de isolamento: o helper que exigia a recusa levantava "o banco aceitou" com um código
   que o próprio bloco capturava como recusa, e passou por seis semanas sem falhar uma vez; e um
   caso buscava o id do alvo **como o atacante**, que a RLS impedia de ver, então o id vinha nulo
   e a recusa era de outra coisa. Detalhe em `references/multi-tenancy.md`. O template `assets/security-ci.yml`
   amarra gitleaks, osv-scanner e semgrep em cada push e PR — é o mínimo que faz a Fase 0
   rodar sozinha.
3. **Reauditar após as correções**, no mínimo a fase 0 inteira — correção de segurança
   introduz regressão com frequência irritante.
4. **Se não há CI, isso é achado por si** (Média): nenhuma das verificações acima roda
   sozinha, então tudo depende de alguém lembrar. Ofereça o `assets/security-ci.yml`.

---

## Quando estiver gerando código

Isto vale de forma preventiva. Antes de escrever código que toque autenticação, autorização,
pagamento, acesso a banco, chave de API, dado de usuário ou chamada a serviço pago, consulte
a referência aplicável. Prevenir é mais barato que auditar.

---

## Referências, scripts e templates

- `scripts/fase0.sh` — roda a Fase 0 inteira (segredos, chaves, deps, semgrep, detecção de
  linguagem, ledger), degrada com elegância e emite o mapa de cobertura pronto.
- `scripts/ledger.py` — ledger de cobertura por unidade de superfície: `rascunho` enumera
  (replay das migrations, Edge Functions, rotas, buckets, CI, deep links) e herda do anterior por
  diff; `marcar` registra estado com commit; `validar --final` é o portão; `catalogo` compara as
  policies dos arquivos com as do banco vivo (e `rascunho --vivo` anota o ledger). Só lê o
  repositório e o JSON que você exportou.
- `references/fundamentos.md` — as oito classes base: segredos, RLS/regras de banco, auth,
  rate limit, pagamento, LLM, deploy, injeção. Sempre aplicável.
- `references/web-app.md` — IDOR/autorização por objeto, mass assignment, SSRF, XSS,
  CORS/CSRF, upload de arquivo, cabeçalhos de segurança, vazamento por erro e resposta.
- `references/linguagens-backend.md` — os mesmos padrões (IDOR, mass assignment, SQL, SSRF)
  em Python/Django/DRF, Ruby/Rails, PHP/Laravel, Go e Java/Kotlin/Spring.
- `references/llm-agentes.md` — injeção de prompt indireta, confiança em servidor MCP e
  tool poisoning, agência excessiva, exfiltração pelo canal de saída, saída do modelo como código,
  quota por inquilino na chave da plataforma, identidade do assistente forjável pelo cliente.
- `references/ios-nativo.md` — Keychain contra UserDefaults, Secure Enclave, ATS, área de
  transferência, exclusão de backup, capturas de tela, deep links, manifesto de privacidade.
- `references/multi-tenancy.md` — isolamento entre organizações, RLS por inquilino, função
  `security definer` que escreve pelo argumento, coluna nova que herda o grant da tabela,
  referência que o `service_role` segue sem re-escopo, vazamento por armazenamento e por cache,
  cópias derivadas (índice, embeddings, exportação) com ACL própria, autorização que sobrevive à
  revogação, exportação e restauração que expandem escopo, teste de isolamento em cinco
  operações a partir do catálogo.
- `references/pre-publicacao.md` — limpeza de contexto interno, histórico do git, licenças,
  o que auditar antes de abrir o código ou entregar a um cliente.
- `references/cadeia-e-ci.md` — GitHub Actions (`pull_request_target`, injeção via
  `${{ }}`, pin por SHA, portão que distingue rede de achado), Docker, lockfiles, scripts de
  instalação, EXIF em imagens.
- `assets/security-ci.yml` — workflow mínimo que amarra gitleaks + osv-scanner + semgrep em
  cada push e PR, fechando o ciclo.
- `assets/ledger.example.md` — como fica um `.security-ledger.md` persistido, com os seis estados
  em uso e o que cada um exige.
- `assets/baseline.example.md` — modelo de `.security-baseline.md` para registrar risco aceito
  **e refutação** com o commit da prova, para a próxima auditoria não re-litigar o mesmo
  não-achado e reabrir por diff quando a fonte mudar.
- `assets/definer.test.ts` — teste de CI que lê as migrations: todo `update`/`do update` em função
  `security definer` leva `where`; a exceção fica escrita no teste, com motivo.
- `assets/grants-de-coluna.test.ts` — teste de CI: em tabela declarada "grant por coluna", coluna
  nova sem `GRANT SELECT (coluna)` explícito e sem motivo de ser privada falha o build.
