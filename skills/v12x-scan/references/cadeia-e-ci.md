# Cadeia de suprimento e CI

Carregar quando existir `.github/workflows/`, Dockerfile, docker-compose, ou quando a
auditoria for de pré-publicação (o repositório público expõe o CI junto).

---

## GitHub Actions

Workflow é código executável com acesso aos segredos do repositório. As três falhas que
importam:

### 1. `pull_request_target` com checkout do código do PR

O gatilho `pull_request_target` roda **com os segredos do repositório**, no contexto da
branch alvo. Se o workflow faz checkout do código do PR e executa qualquer coisa dele
(build, teste, lint), **um PR de estranho executa código com acesso aos seus segredos**.

```bash
grep -rn "pull_request_target" .github/workflows/ 2>/dev/null
```

Se aparecer junto de `actions/checkout` com `ref` apontando para o PR, é **Crítico** em
repositório público.

### 2. Injeção via interpolação `${{ }}`

Título de PR, nome de branch e corpo de issue são **entrada do atacante**. Interpolados
direto num `run:`, viram execução de shell:

```yaml
# ERRADO — título do PR vira comando
run: echo "${{ github.event.pull_request.title }}"

# CERTO — passa por variável de ambiente, o shell não interpreta
env:
  TITLE: ${{ github.event.pull_request.title }}
run: echo "$TITLE"
```

```bash
grep -rnE '\$\{\{\s*github\.(event\.(pull_request|issue|comment)|head_ref)' .github/workflows/ 2>/dev/null
```

### 3. Ações de terceiro sem pin

`uses: alguma-acao@v3` resolve para o que o dono da tag quiser — tag é móvel. Compromisso da
ação vira compromisso do seu CI (o caso tj-actions/changed-files em 2025 vazou segredos de
milhares de repositórios exatamente assim).

Regra: ação de terceiro pinada por **SHA completo**, não por tag. Ações oficiais
(`actions/*`) por tag maior são aceitáveis.

```bash
grep -rn "uses:" .github/workflows/ 2>/dev/null | grep -vE '@[0-9a-f]{40}' | grep -v "actions/"
```

### Permissões do token

Sem declaração, o `GITHUB_TOKEN` pode ter escopo largo. Exigir no topo do workflow:

```yaml
permissions:
  contents: read
```

E elevar só o job que precisa. Workflow sem bloco `permissions` é achado Médio.

### Segredo vazando em log

`echo` de variável que contém segredo, `set -x` em script com credencial, ou upload de
artefato que inclui `.env`. O GitHub mascara o valor exato do segredo, mas não mascara
transformações (base64, URL-encoded).

---

## Docker

- **Segredo em camada**: `COPY .env .` ou `ARG API_KEY` com valor em build fica gravado na
  camada, mesmo que apagado depois. `docker history` recupera. Usar secret mounts do
  BuildKit.
- **`.dockerignore` existe?** Sem ele, o contexto de build carrega `.git`, `.env` e tudo
  mais para dentro da imagem.
- **Imagem base pinada?** `FROM node:latest` muda embaixo de você. Pinar por digest em
  produção.
- **Roda como root?** Ausência de `USER` não-root é endurecimento (Baixa), mas entra.

```bash
grep -nE '^(COPY|ADD)\s+\.env|^ARG.*(KEY|SECRET|TOKEN|PASSWORD)' Dockerfile 2>/dev/null
test -f .dockerignore || echo "SEM .dockerignore"
```

---

## Cadeia de dependências

- **Lockfile commitado** (`package-lock.json`, `Package.resolved`): sem ele, o build de
  amanhã não é o que foi auditado hoje. Ausência é achado Médio.
- **Scripts de ciclo de vida**: `postinstall`/`preinstall` no `package.json` próprio e nas
  dependências diretas — é o vetor de execução na instalação.
- **Dependência por URL de git** em vez de registro versionado: muda sem aviso.
- **Pacote interno com nome não registrado** no npm público: risco de dependency confusion
  se o build resolver o registro público primeiro.

```bash
# scripts de instalação no projeto
grep -nE '"(pre|post)?install"' package.json 2>/dev/null

# dependências por git/url
grep -nE '"(git\+|https?://)' package.json 2>/dev/null
```

---

## Imagens e assets

Antes de publicar repositório com screenshots ou fotos: imagem tirada com telefone carrega
EXIF com **coordenada GPS** e identificação do aparelho.

```bash
find . \( -name '*.jpg' -o -name '*.jpeg' -o -name '*.heic' \) -not -path '*/node_modules/*' | while read f; do
  lat=$(mdls -name kMDItemLatitude -raw "$f" 2>/dev/null)
  [ "$lat" != "(null)" ] && [ -n "$lat" ] && echo "GPS EXIF: $f"
done
```

Screenshot de app pode vazar dado real: nome, e-mail, saldo, conversa. Revisar cada imagem
que vai a público como se fosse texto.
