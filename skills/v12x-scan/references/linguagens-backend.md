# Linguagens de backend além de TS/JS

Carregar quando a Fase 0 detectar backend que **não** é TypeScript/JavaScript
(`.py`, `.go`, `.rb`, `.php`, `.java`/`.kt`).

Por que esta referência existe: os `grep` de `web-app.md` e `fundamentos.md` casam
idiomas de TS/JS (`req.body`, `dangerouslySetInnerHTML`, `queryRaw`). Um backend em
Python, Go, Ruby, PHP ou Java **passa limpo** por esses padrões estando cheio de IDOR e
mass assignment. Reportar "COBERTO: autorização" tendo olhado só TS é o **furo
silencioso** que a skill promete não ter. Aqui estão os padrões equivalentes.

As três falhas de sempre — **IDOR/autorização por objeto**, **mass assignment** e **SQL
por concatenação** — mudam de nome em cada framework, mas são a mesma coisa. A régua não
muda: *o identificador do dono vem da sessão, o objeto gravável é uma allowlist, a query é
parametrizada.* Tudo aqui passa pela verificação adversarial da Fase 2.

---

## Python — Django / DRF

- **IDOR:** `Model.objects.get(pk=id)` sem escopo pelo usuário. Em DRF, `queryset =
  Model.objects.all()` numa view sem `get_queryset` filtrando por `self.request.user` serve
  qualquer objeto a qualquer usuário logado.

  ```python
  # ERRADO
  queryset = Documento.objects.all()
  # CERTO — escopo pela sessão
  def get_queryset(self):
      return Documento.objects.filter(dono=self.request.user)
  ```

- **Mass assignment:** `fields = '__all__'` num `ModelForm` ou `ModelSerializer` deixa gravar
  qualquer coluna, inclusive `is_staff`/`role`. Declarar os campos, e pôr os sensíveis em
  `read_only_fields`.
- **SQL:** `.raw()`, `.extra()` e `cursor.execute(f"... {x}")` com f-string reabrem injeção.
  ORM com parâmetro nomeado é seguro; f-string em SQL nunca.
- **Deploy:** `DEBUG = True` em produção expõe stack trace e variáveis (equivale ao item 8 de
  `web-app.md`). `ALLOWED_HOSTS = ['*']` e `SECRET_KEY` embutido no código são achados.
- **SSRF:** `requests.get(url_do_usuario)`, `urllib.request.urlopen(...)`. **Desserialização:**
  `pickle.loads`, `yaml.load` sem `SafeLoader`, `eval`, `subprocess(..., shell=True)`.

```bash
grep -rnE "objects\.(all|get|filter)\(|fields\s*=\s*['\"]__all__['\"]|\.raw\(|\.extra\(|cursor\.execute\(f|DEBUG\s*=\s*True|ALLOWED_HOSTS\s*=\s*\[['\"]\*|pickle\.loads|yaml\.load\(|shell\s*=\s*True|requests\.(get|post)\(" \
  --include='*.py' . | grep -viE 'test|migrations'
```

---

## Ruby — Rails

- **IDOR:** `Model.find(params[:id])` sem escopo. O certo é derivar do usuário:
  `current_user.documentos.find(params[:id])`.
- **Mass assignment:** `params.permit!` ou `params.require(:x).permit!` liberam tudo. Strong
  params com allowlist explícita: `params.require(:user).permit(:name, :bio)` — nunca `:role`.
- **SQL:** `where("nome = '#{params[:q]}'")` e `find_by_sql` com interpolação. Usar a forma com
  placeholder: `where("nome = ?", params[:q])`.
- **Outros:** `Marshal.load` sobre dado do usuário; `send(params[:m])`/`public_send` com nome de
  método vindo do cliente; `constantize` sobre entrada.

```bash
grep -rnE "\.find\(params|\.permit!|where\(\"[^\"]*#\{|find_by_sql|Marshal\.load|\.(send|public_send|constantize)\(params" \
  --include='*.rb' . | grep -viE 'spec|test'
```

---

## PHP — Laravel

- **Mass assignment:** `$guarded = []`, `Model::unguard()`, `->fill($request->all())` e
  `Model::create($request->all())` gravam qualquer atributo. Usar `$fillable` explícito ou
  `$request->only([...])`.
- **IDOR:** `Model::find($id)` sem `->where('user_id', auth()->id())`. Preferir *route model
  binding* com policy (`$this->authorize('view', $doc)`).
- **SQL:** `DB::raw`, `whereRaw`, `->select(DB::raw("... $x"))` com entrada. Usar binding: `?`.
- **Deploy:** `APP_DEBUG=true` em produção; `env()` chamado fora de `config/` (quebra o cache
  de config e vaza vazio em produção); `.env` servível dentro de `public/`.

```bash
grep -rnE '\$guarded\s*=\s*\[\]|::unguard\(|->fill\(\$request|::create\(\$request->all|::find\(\$|whereRaw|DB::raw|APP_DEBUG\s*=\s*true' \
  --include='*.php' --include='.env*' . | grep -viE 'tests?/'
```

---

## Go

- **IDOR:** query por id sem cláusula de dono. Com `database/sql` ou GORM, incluir o
  `owner_id`/`tenant_id` no `WHERE`, derivado do contexto autenticado, nunca do parâmetro.
- **SQL:** `fmt.Sprintf` montando query, ou `db.Query(sql + userInput)`. Usar sempre parâmetro
  posicional: `db.Query("... WHERE id=$1 AND owner=$2", id, uid)`.
- **SSRF:** `http.Get(userURL)`, `http.NewRequest(..., userURL, ...)` sem allowlist de host.
- **XSS:** `template.HTML(userInput)` desliga o escape do `html/template`; só com conteúdo
  confiável. **Comando:** `exec.Command("sh", "-c", userInput)`.

```bash
grep -rnE 'fmt\.Sprintf\([^)]*(SELECT|INSERT|UPDATE|DELETE)|db\.(Query|Exec)\([^,)]*\+|http\.(Get|Post)\(|template\.HTML\(|exec\.Command\(' \
  --include='*.go' . | grep -viE '_test\.go'
```

---

## Java / Kotlin — Spring

- **Mass assignment:** `@RequestBody` desserializando direto na **entidade** JPA deixa o cliente
  setar qualquer campo persistido. Receber um **DTO** com só os campos permitidos.
- **IDOR:** `repository.findById(id)` sem checar o dono; `@PreAuthorize`/`@PostAuthorize` ou
  filtro por usuário ausente no repositório.
- **SQL:** `Statement` com concatenação, ou `@Query` com SpEL/`?#{}` sobre entrada. Usar
  `PreparedStatement`/parâmetro nomeado.
- **SSRF:** `restTemplate.getForObject(userUrl, ...)`, `WebClient` com URL do usuário.
  **Injeção de expressão:** SpEL avaliando entrada; `ObjectInputStream.readObject` (desserialização).

```bash
grep -rnE '@RequestBody\s+\w*Entity|findById\(|createStatement\(|Statement[^;]*\+|getForObject\(|readObject\(' \
  --include='*.java' --include='*.kt' . | grep -viE 'src/test'
```

---

## Verificação adversarial nesta camada

O mesmo teste da Fase 2: só reportar quando a entrada é controlável por quem ataca. Um
`find(params[:id])` num controller que já roda dentro de `current_user.documentos` **não** é
IDOR. Um `fmt.Sprintf` de SQL com constante do próprio código **não** é injeção. O achado
existe quando há caminho concreto de entrada não confiável até o ponto vulnerável — e some se
uma camada anterior (policy, middleware, RLS) já barra.
