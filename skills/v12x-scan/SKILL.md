---
name: v12x-scan
description: Auditoria de segurança em profundidade, com ferramentas determinísticas antes da análise por leitura, verificação adversarial de cada achado e relatório acionável. Use quando o usuário pedir "auditar segurança", "revisar segurança", "varredura de segurança", "tem vazamento?", "posso publicar isso?", "está seguro para open source?", "antes de publicar", "checar segredos", "auditar antes de entregar ao cliente", "hacker acessa pelo frontend", "checar IDOR/SSRF/XSS", "auditar meu agente/MCP", ou antes de tornar um repositório público, publicar app na loja, entregar código a terceiro, ou ligar multi-tenancy. Autossuficiente: cobre os fundamentos (segredos, RLS, auth, rate limit, pagamento, LLM, deploy, injeção) e vai além com aplicação web (IDOR, mass assignment, SSRF, XSS, CORS/CSRF, upload), backends fora de TS/JS (Python, Go, Ruby, PHP, Java), apps agênticos/LLM (injeção de prompt, MCP, agência excessiva), iOS/Swift nativo, isolamento entre inquilinos, cadeia de suprimento/CI e limpeza de contexto interno.
license: MIT
metadata:
  version: "1.2"
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

---

## Fase 2 — Verificação adversarial

**Nenhum achado entra no relatório sem passar por esta porta.** Para cada candidato,
responda as três perguntas. Se qualquer uma falhar, descarte ou rebaixe.

1. **Onde exatamente?** Arquivo e linha. Sem âncora, não é achado — é impressão.
2. **Qual o caminho desde entrada não confiável?** Descreva a rota concreta: requisição
   externa → parâmetro → função vulnerável. Se o código só é alcançável por script local de
   build, por teste, ou por caminho autenticado de administrador, **rebaixe**.
3. **O que um atacante consegue?** Consequência concreta e específica: "lê os documentos de
   qualquer usuário trocando o id na URL", não "pode causar exposição de dados".

Depois, tente **refutar** o achado explicitamente. Existe validação em camada anterior?
Middleware que já barra? RLS que já cobre? Se existir, o achado morre — e isso é bom.

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

---

## Fase 4 — Relatório

Ordem obrigatória: **Crítica → Alta → Média → Baixa.** Pule níveis sem achado.

Cabeçalho com âncora, veredito e **mapa de cobertura**, antes de qualquer detalhe:

```
Auditoria do commit a1b2c3d · 2026-08-13 · gitleaks 8.x
2 críticas · 3 altas · 5 médias · 1 baixa
VEREDITO: não publicar até resolver as críticas.

COBERTO: histórico git (180 commits) · árvore com ignorados · deps npm ·
         auth/autorização · RLS · iOS nativo
NÃO COBERTO: osv-scanner ausente (SwiftPM sem audit) · sem teste dinâmico ·
         binário compilado não inspecionado
```

**O mapa de cobertura é obrigatório.** É a diferença entre "não achei nada" e "não olhei".
Um leitor precisa saber exatamente o que esta auditoria não viu.

Para cada achado:

**`caminho/arquivo.ts:42` — Nome específico da falha**

Um parágrafo com o caminho de exploração concreto. Depois, correção em antes e depois, com
código real do projeto e não exemplo genérico.

Feche com uma lista numerada de ações em ordem de execução. Se houver credencial exposta, a
primeira ação é sempre **revogar**, nunca "remover do código" — o segredo já vazou no
momento em que foi commitado.

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

### O ciclo que fecha o furo de verdade

Uma auditoria pontual não deixa nada "à prova de furos" — o que aproxima disso é o ciclo:

1. **Persistir o relatório** em `.security-reports/AAAA-MM-DD.md` no repositório (e o JSON
   do gitleaks ao lado — `scripts/fase0.sh` já salva em `.security-reports/fase0/`). A próxima
   auditoria **diffa contra a anterior**: o que voltou é regressão e sobe um nível de severidade.
2. **Cada achado corrigido vira verificação permanente.** Se o achado foi "token em log",
   nasce um grep no CI que falha se o padrão voltar; se foi "tabela sem RLS", nasce o teste
   de isolamento. Achado que só vive no relatório volta. O template `assets/security-ci.yml`
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
  linguagem), degrada com elegância e emite o mapa de cobertura pronto.
- `references/fundamentos.md` — as oito classes base: segredos, RLS/regras de banco, auth,
  rate limit, pagamento, LLM, deploy, injeção. Sempre aplicável.
- `references/web-app.md` — IDOR/autorização por objeto, mass assignment, SSRF, XSS,
  CORS/CSRF, upload de arquivo, cabeçalhos de segurança, vazamento por erro e resposta.
- `references/linguagens-backend.md` — os mesmos padrões (IDOR, mass assignment, SQL, SSRF)
  em Python/Django/DRF, Ruby/Rails, PHP/Laravel, Go e Java/Kotlin/Spring.
- `references/llm-agentes.md` — injeção de prompt indireta, confiança em servidor MCP e
  tool poisoning, agência excessiva, exfiltração pelo canal de saída, saída do modelo como código.
- `references/ios-nativo.md` — Keychain contra UserDefaults, Secure Enclave, ATS, área de
  transferência, exclusão de backup, capturas de tela, deep links, manifesto de privacidade.
- `references/multi-tenancy.md` — isolamento entre organizações, RLS por inquilino,
  vazamento por armazenamento e por cache, testes de isolamento.
- `references/pre-publicacao.md` — limpeza de contexto interno, histórico do git, licenças,
  o que auditar antes de abrir o código ou entregar a um cliente.
- `references/cadeia-e-ci.md` — GitHub Actions (`pull_request_target`, injeção via
  `${{ }}`, pin por SHA), Docker, lockfiles, scripts de instalação, EXIF em imagens.
- `assets/security-ci.yml` — workflow mínimo que amarra gitleaks + osv-scanner + semgrep em
  cada push e PR, fechando o ciclo.
- `assets/baseline.example.md` — modelo de `.security-baseline.md` para registrar risco aceito.
