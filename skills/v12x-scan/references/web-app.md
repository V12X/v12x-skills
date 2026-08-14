# Vulnerabilidades de aplicação web

Carregar quando há backend que atende requisição HTTP (rota de API, server action, endpoint).
É a camada do ataque "ler o frontend e bater no backend": o navegador é público, então toda
defesa real está aqui, no servidor.

Ordem de prioridade abaixo é por frequência e dano reais. IDOR e mass assignment são os que
mais aparecem em código gerado com IA.

> **Os `grep` desta referência casam idiomas de TS/JS** (`req.body`,
> `dangerouslySetInnerHTML`, `queryRaw`). Se a Fase 0 detectou backend em Python, Go, Ruby,
> PHP ou Java, os conceitos são os mesmos mas os padrões mudam — use
> `references/linguagens-backend.md`, senão o furo é silencioso.

---

## 1. IDOR / autorização por objeto — o nº 1

Autenticação responde "quem é você". Autorização por objeto responde "isto é seu". A falha
clássica valida a sessão e esquece a posse:

```ts
// ERRADO — confere que está logado, não que o documento é dele
export async function GET(req, { params }) {
  const session = await auth(req)            // só autenticação
  if (!session) return unauthorized()
  return db.document.findUnique({ where: { id: params.id } })  // id de QUALQUER um
}

// CERTO — o dono faz parte da condição
  return db.document.findUnique({
    where: { id: params.id, ownerId: session.userId }
  })
```

O atacante lê no seu JavaScript que existe `/api/document/:id`, e no terminal percorre
`1,2,3…` ou troca o UUID por um que viu em outra resposta. **Se o servidor devolve sem checar
posse, invadiu — e nem passou pela sua tela.**

Caça sistemática: liste toda rota que recebe um identificador e confirme que a posse entra na
consulta, não numa checagem separada que alguém pode esquecer.

```bash
# rotas com parâmetro de id — revisar posse em cada uma
grep -rnE '\[(id|slug|uuid|[a-z]+Id)\]|:[a-zA-Z]+Id|params\.(id|[a-z]+Id)' \
  app/ pages/ src/ 2>/dev/null | grep -viE 'test|spec' | grep -v node_modules
```

Regra decisiva: **o identificador do usuário vem sempre da sessão, nunca do corpo, query ou
parâmetro da requisição.**

---

## 2. Mass assignment — o objeto inteiro vindo do cliente

Passar `req.body` direto para o ORM deixa o usuário gravar qualquer coluna, inclusive as que
a tela não mostra:

```ts
// ERRADO — usuário manda {"email":"...","role":"admin","credits":99999}
await db.user.update({ where: { id }, data: req.body })

// CERTO — allowlist explícita do que pode ser gravado
const { name, bio } = req.body
await db.user.update({ where: { id }, data: { name, bio } })
```

É especialmente perigoso em cadastro e edição de perfil: o campo `role`, `isAdmin`,
`plan`, `balance` nunca pode ser gravável a partir do corpo. Valide a forma da entrada com
um schema (zod, valibot) que só declara os campos permitidos.

```bash
# ORM recebendo o corpo inteiro
grep -rnE '(create|update|updateMany|upsert)\(\{[^}]*data:\s*(req\.body|body|input|data)\b' \
  --include='*.ts' --include='*.js' . | grep -v node_modules
```

---

## 3. SSRF — o servidor busca uma URL que o usuário controla

Se o backend faz `fetch(url)` com `url` vindo do usuário, o atacante aponta para dentro:
`http://169.254.169.254/…` (metadados da nuvem, que devolvem credencial da instância),
`http://localhost:...`, serviços internos que só o servidor alcança.

```ts
// ERRADO
const r = await fetch(req.body.imageUrl)     // aponta para onde quiser

// CERTO — allowlist de host, bloqueio de IP privado, sem seguir redirect
const host = new URL(input).hostname
if (!ALLOWED_HOSTS.has(host)) throw new Error('host não permitido')
const r = await fetch(input, { redirect: 'error' })  // redirect burla allowlist
```

Bloquear também faixas privadas (10., 192.168., 172.16–31., 127., 169.254., `::1`) resolvendo
o DNS antes, porque um domínio público pode resolver para IP interno. Comum em: proxy de
imagem, webhook de saída, "importar de URL", geração de preview de link.

```bash
grep -rnE '(fetch|axios|got|request|urllib|URLSession)\s*\(?\s*(req\.|request\.|body|input|params|query)' \
  --include='*.ts' --include='*.swift' . | grep -v node_modules
```

---

## 4. XSS — conteúdo do usuário renderizado como HTML

React escapa por padrão, então o vetor é quase sempre `dangerouslySetInnerHTML`, ou HTML
injetado em `WKWebView`/`innerHTML`:

```tsx
// ERRADO — bio do usuário com <script> executa no navegador de quem vê
<div dangerouslySetInnerHTML={{ __html: user.bio }} />

// CERTO — sanitizar antes
import DOMPurify from 'isomorphic-dompurify'
<div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(user.bio) }} />
```

Perigo maior quando o conteúdo de um usuário é exibido para **outro** (comentário, perfil
público, mensagem) — vira XSS armazenado, que ataca todo mundo que abre a página.

```bash
grep -rnE 'dangerouslySetInnerHTML|\.innerHTML\s*=|v-html|loadHTMLString' \
  --include='*.tsx' --include='*.ts' --include='*.vue' --include='*.swift' . | grep -v node_modules
```

Defesa em profundidade: um `Content-Security-Policy` sem `unsafe-inline` neutraliza boa parte
do XSS mesmo quando um escapa (ver item 7).

---

## 5. CORS e CSRF

**CORS mal configurado** entrega sua API para qualquer site. O combo fatal é refletir a
origem e permitir credencial:

```ts
// ERRADO — reflete qualquer origem COM cookie: qualquer site lê a resposta autenticada
res.setHeader('Access-Control-Allow-Origin', req.headers.origin)
res.setHeader('Access-Control-Allow-Credentials', 'true')

// CERTO — allowlist fixa
if (ALLOWED_ORIGINS.has(origin)) res.setHeader('Access-Control-Allow-Origin', origin)
```

`Allow-Origin: *` **nunca** junto de `Allow-Credentials: true`. E refletir `origin` sem
allowlist é o mesmo que `*`.

**CSRF** só afeta autenticação por **cookie**. Se a sua API usa `Authorization: Bearer` em
header, ela é imune (outro site não consegue setar seu header). Se usa cookie de sessão, toda
rota que muda estado precisa de `SameSite=Lax/Strict` no cookie e, idealmente, token CSRF.

```bash
grep -rnE "Access-Control-Allow-Origin.*(\*|origin)" --include='*.ts' . | grep -v node_modules
grep -rnE 'cookie.*(sameSite|SameSite)' --include='*.ts' . | grep -v node_modules   # ausência é o achado
```

---

## 6. Upload de arquivo

Quatro checagens, e faltar qualquer uma abre um buraco:

- **Tipo por conteúdo, não por extensão.** `foto.png` pode ser um script. Ler os magic bytes.
- **Nome aleatório no destino.** Usar o nome enviado permite path traversal (`../../etc/...`)
  e sobrescrita. Gerar UUID.
- **Fora da raiz servível.** Arquivo do usuário em pasta que o servidor entrega estático =
  upload de código executável. Guardar em storage de objeto (privado) ou fora do web root.
- **Limite de tamanho.** Sem teto, é negação de serviço e conta de storage estourada.

```bash
grep -rnE '(multer|formidable|busboy|\.file|multipart|UploadedFile)' \
  --include='*.ts' --include='*.js' . | grep -v node_modules
```

---

## 7. Cabeçalhos de segurança e redirecionamento aberto

Endurecimento que fecha classes inteiras de uma vez. Ausência é achado Médio (defesa em
profundidade), não Crítico:

| Cabeçalho | O que fecha |
|---|---|
| `Content-Security-Policy` | Reduz XSS drasticamente; sem `unsafe-inline` |
| `Strict-Transport-Security` | Força HTTPS, impede downgrade |
| `X-Content-Type-Options: nosniff` | Impede o navegador de "adivinhar" tipo e executar |
| `X-Frame-Options` / `frame-ancestors` | Impede clickjacking por iframe |
| `Referrer-Policy` | Impede vazar URL interna no header Referer |

**Redirecionamento aberto:** `redirect(req.query.next)` sem validar deixa o atacante usar seu
domínio confiável para mandar a vítima a um site de phishing. Validar que o destino é
relativo ou está numa allowlist.

```bash
grep -rnE '(redirect|Location).*(req\.|query|params|searchParams|body)' \
  --include='*.ts' . | grep -v node_modules
```

---

## 8. Vazamento por mensagem de erro e resposta

- **Stack trace em produção** entrega caminho de arquivo, versão de framework e, às vezes,
  query com dado. Erro genérico para o cliente, detalhe só no log do servidor.
- **Objeto de usuário inteiro na resposta** costuma incluir `passwordHash`, `resetToken`,
  `stripeCustomerId`. Selecionar campos explicitamente em vez de devolver o registro cru.
- **Diferença de mensagem no login** ("e-mail não existe" vs "senha errada") permite
  enumerar contas. Mensagem única para os dois casos.

```bash
# registro cru voltando na resposta
grep -rnE '(res\.json|return Response\.json|c\.json)\(\s*(user|account|record|row)\b' \
  --include='*.ts' . | grep -v node_modules
```

---

## Verificação adversarial nesta camada

Antes de reportar qualquer um destes, confirme o caminho do dado não confiável até o ponto
vulnerável (fase 2 do SKILL). Um `dangerouslySetInnerHTML` com string constante do próprio
código **não** é XSS. Um `fetch` de URL que só vem de config interna **não** é SSRF. O achado
existe quando a entrada é controlável por quem ataca.
