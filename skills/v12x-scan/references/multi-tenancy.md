# Isolamento entre inquilinos

Auditar **antes** de ligar multi-tenancy, nunca depois. Vazamento entre inquilinos é a falha
mais cara de um SaaS B2B: expõe dado de um cliente para o concorrente dele, e num sistema
para agências os inquilinos são concorrentes diretos por definição.

---

## O princípio

**Todo caminho de leitura e escrita precisa filtrar por inquilino no servidor.** Filtrar na
consulta do frontend não vale nada — o atacante fala direto com a API.

E filtro por inquilino não pode depender de o desenvolvedor lembrar. Se o isolamento
depende de alguém escrever `.eq('org_id', orgId)` em toda consulta, **um esquecimento vaza
tudo**. O isolamento precisa ser imposto pela camada de baixo.

---

## Supabase e Postgres

### RLS ligado em toda tabela com dado de inquilino

```sql
-- verificar quais tabelas estão sem RLS
SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname = 'public' AND rowsecurity = false;
```

Qualquer tabela com `org_id`, `tenant_id` ou `client_id` e `rowsecurity = false` é **achado
Crítico**.

### A política precisa derivar da sessão, não do parâmetro

```sql
-- ERRADO — confia em algo que o cliente controla
CREATE POLICY sel ON documentos FOR SELECT
USING (org_id = current_setting('request.jwt.claims')::json->>'org_id');
-- se o org_id vier de claim editável pelo usuário, não isola nada

-- CERTO — deriva de tabela de vínculo, checada no servidor
CREATE POLICY sel ON documentos FOR SELECT
USING (org_id IN (
  SELECT org_id FROM membros WHERE user_id = auth.uid()
));
```

Auditar: a política usa `auth.uid()` como origem da verdade? Ou aceita um identificador que
vem do cliente?

### Políticas por operação

`FOR SELECT` isolado não protege escrita. Confirmar que existem políticas para `INSERT`,
`UPDATE` e `DELETE`, e que o `WITH CHECK` do insert impede gravar em inquilino alheio:

```sql
CREATE POLICY ins ON documentos FOR INSERT
WITH CHECK (org_id IN (SELECT org_id FROM membros WHERE user_id = auth.uid()));
```

Sem `WITH CHECK`, um usuário insere linha marcada com o `org_id` de outra organização.

### A chave `service_role` ignora RLS

Todo uso de `service_role` é um ponto onde o isolamento **não existe**. Auditar cada
ocorrência: está em código que roda só no servidor? A consulta filtra por inquilino
manualmente? Nunca pode estar em código de cliente nem em variável com prefixo público.

### `security definer` escreve com o privilégio do dono — e amarra pelo argumento?

Função `security definer` ignora a RLS. Se ela faz `update … set` ou `on conflict … do update`
amarrando só pelo `id` que veio no argumento, **qualquer chamador reescreve a linha de qualquer
um**: a policy que protegeria a tabela nem é consultada. O `where` de posse tem que vir do chamador
validado (`auth.uid()`, ou o `p_user` que a função extrai do JWT), nunca do parâmetro.

Caso real: função de mensagem do assistente com `on conflict (id) do update set body` — um membro
reescrevia a mensagem do colega, com o autor original e sem `edited_at`. **Escapou de quatro
auditorias por leitura.** O grep que lista as candidatas está na Fase 0 da SKILL; abrir cada uma
e perguntar: o `where` amarra o chamador, ou só o argumento?

```sql
-- ERRADO — o conflito é pelo id que veio de fora; a linha pode ser de qualquer um
insert into mensagens (id, canal_id, body) values (p_id, p_canal, p_body)
on conflict (id) do update set body = excluded.body;

-- CERTO — só reescreve o que já era do chamador (ou do assistente, no mesmo canal)
on conflict (id) do update set body = excluded.body
where mensagens.author_id = p_user and mensagens.canal_id = p_canal;
```

O `assets/definer.test.ts` fixa a regra no CI: todo `do update` em `definer` leva `where`. A
exceção fica **escrita no teste, com motivo** — um upsert de token de aparelho pela chave
`(user_id, token)`, por exemplo, só pode conflitar com a linha do próprio usuário.

### Coluna nova herda o grant da tabela — a lição que se repete

`GRANT SELECT ON workspaces TO authenticated` dá SELECT em **todas as colunas, inclusive as que
ainda não existem**. A coluna sensível criada numa migration depois (`operator_note`,
`internal_flag`, `cost_cents`) nasce **dentro** desse grant e é legível por todo membro da
organização, sem que ninguém tenha decidido isso. Num projeto real essa foi a lição da migration
0033, da 0045 **e da 0072 — a terceira tabela**. Erro que se repete três vezes não é descuido: é
ausência de regra.

Regra: tabela que mistura coluna de todos com coluna de poucos tem grant **por coluna**, não por
tabela — e coluna nova precisa de grant explícito ou motivo declarado de ser privada.

```sql
-- tabelas com grant de TABELA para authenticated: cada coluna delas é pública para o membro
SELECT DISTINCT table_name FROM information_schema.role_table_grants
WHERE table_schema = 'public' AND grantee = 'authenticated' AND privilege_type = 'SELECT';
-- para cada uma, liste as colunas e pergunte, uma a uma: "todo membro pode ler isto?"
```

O `assets/grants-de-coluna.test.ts` fixa isso no CI: para cada tabela declarada "grant por
coluna", coluna nova em migration sem `GRANT SELECT (coluna)` explícito e sem comentário de motivo
falha o build.

### A referência que o `service_role` segue precisa ser re-amarrada ao inquilino

O caso mais sutil: a linha tem `workspace_id` certo, a RLS está ligada, e mesmo assim vaza —
porque um **id que a linha aponta** (`file_id`, `document_id`, `account_id`) não está amarrado ao
mesmo inquilino, e um caminho com `service_role` **desreferencia** esse id sem conferir. Caso
real: `documentos.file_id` aceitava o id de um arquivo de outra empresa, e a função de ingestão
lia o arquivo com a chave de serviço — o contrato da empresa B foi transcrito, indexado e
respondido pelo assistente da empresa A.

Regra: **toda coluna de referência que um caminho privilegiado segue é amarrada ao inquilino da
própria linha** — por trigger ou constraint que confere que o alvo pertence ao mesmo
`workspace_id` — e o caminho privilegiado lê o alvo com o **token da pessoa**, não com a chave de
serviço, sempre que puder. Assim a RLS do alvo trabalha a favor.

```sql
-- colunas de referência em tabelas com inquilino: cada uma amarra ao mesmo inquilino?
SELECT c.table_name, c.column_name FROM information_schema.columns c
WHERE c.table_schema = 'public' AND c.column_name LIKE '%\_id'
  AND c.column_name NOT IN ('workspace_id','org_id','tenant_id','user_id')
  AND EXISTS (SELECT 1 FROM information_schema.columns w WHERE w.table_name = c.table_name
              AND w.column_name IN ('workspace_id','org_id','tenant_id'));
```

Cada linha que sair: existe trigger/constraint que prove que o alvo é do mesmo inquilino? Se não,
e um caminho `service_role` segue esse id, é achado **Alta**.

---

## Armazenamento de arquivo

O ponto mais esquecido, e o mais fácil de explorar porque não exige nem autenticação.

- **Bucket público com caminho previsível** é vazamento direto. `/anexos/{org}/{arquivo}` num
  bucket público significa que qualquer pessoa lista e baixa tudo.
- O correto é bucket privado com URL assinada de validade curta, gerada no servidor **depois**
  de conferir que o solicitante pertence ao inquilino dono do arquivo.
- Se houver política de storage do Supabase, ela precisa refletir o mesmo vínculo da tabela.

```sql
CREATE POLICY "leitura_do_proprio_inquilino" ON storage.objects FOR SELECT
USING (
  bucket_id = 'anexos'
  AND (storage.foldername(name))[1] IN (
    SELECT org_id::text FROM membros WHERE user_id = auth.uid()
  )
);
```

---

## Credencial por inquilino

Num sistema que integra serviços externos em nome do cliente (contas de anúncio, e-mail,
pagamento), **credencial global compartilhada é falha de isolamento**: o inquilino A opera
com o token que também alcança os dados do inquilino B.

Auditar: existe uma tabela de credenciais por organização? Os valores estão cifrados em
repouso, com a chave fora do banco? Quem consegue ler a tabela consegue ler os segredos de
todos os clientes de uma vez.

---

## Vazamento por cache e por resolução de subdomínio

- **Cache sem chave de inquilino** entrega resposta do inquilino A para o B. Auditar chave de
  cache, `revalidateTag`, cache de CDN e memoização em servidor: o identificador do inquilino
  faz parte da chave?
- **Middleware de subdomínio** que resolve `cliente.app.com` precisa **confirmar que a sessão
  pertence àquele inquilino**, não apenas ler o subdomínio. Sem isso, um usuário logado no A
  acessa o B trocando a URL.
- **Cabeçalhos de cache** em rota autenticada: `Cache-Control: public` numa resposta com dado
  de inquilino é vazamento via proxy intermediário.

---

## Enumeração por identificador sequencial

Id inteiro sequencial permite descobrir volume e adivinhar recurso. Preferir UUID. **Não é
substituto de autorização** — UUID sem checagem de posse continua vulnerável, só é mais
difícil de varrer.

---

## Teste que prova o isolamento

Auditoria por leitura não prova isolamento. Exija teste automatizado, e a ausência dele é
achado por si. E a receita cobre **cinco** operações, não três: a crítica que quatro auditorias
por leitura não viram — uma policy de INSERT que deixava qualquer conta se inserir numa
organização **como admin** — só apareceu quando o teste tentou **inserir** e **chamar função**
como a outra empresa.

```
1. criar organização A e organização B, com uma pessoa em cada
2. como A: criar uma linha em CADA tabela com coluna de inquilino, mais um objeto no storage;
   provar que A lê tudo
3. virar a pessoa de B — a troca de identidade é a do PostgREST por dentro:
   `set local role authenticated` + `request.jwt.claims` com o sub de B
4. como B, contra os ids de A:
   - LER cada tabela                                → zero linhas
   - ATUALIZAR e APAGAR por id                      → zero linhas afetadas
   - INSERIR em cada tabela com o inquilino de A    → recusado
   - CHAMAR cada função exposta (rpc) com ids de A  → recusado ou "não encontrado"
   - ler o objeto de A no storage                   → recusado
5. tudo numa transação que termina em rollback
```

Três detalhes que decidem se o teste prova ou só parece provar:

- **A lista vem do catálogo, não da mão.** Tabelas de `pg_tables` filtradas pela coluna de
  inquilino, funções de `pg_proc` no schema público — assim **a próxima tabela entra sozinha**.
  Lista escrita à mão é lista que envelhece, e a tabela nova é justamente a que ninguém pensou.
- **Só o código de recusa conta como recusa.** `42501` (permissão/RLS), e `22023` ou "não
  encontrado" para o que a RLS esconde. Erro de digitação, coluna que não existe, função com
  assinatura errada — tudo isso **derruba o teste**, não passa como "recusou". Senão o teste fica
  verde por acidente.
- **Roda no CI contra um banco vazio** que sobe das migrations (a stack local do Supabase no
  runner). Se as migrations não sobem limpas num banco vazio, isso já é achado — é assim que
  aparecem o prefixo de migration duplicado e a migration que depende de uma conta que só existe
  em produção.

---

## Verificação rápida

```bash
# tabelas sem RLS (rodar via cliente SQL)
# SELECT tablename FROM pg_tables WHERE schemaname='public' AND rowsecurity=false;

# uso de service_role
grep -rnE 'service_role|SERVICE_ROLE|SUPABASE_SERVICE' --include='*.ts' --include='*.tsx' --include='*.js' . | grep -v node_modules

# segredo com prefixo público
grep -rnE 'NEXT_PUBLIC_[A-Z_]*(KEY|SECRET|TOKEN|PASSWORD)' . | grep -v node_modules

# consultas sem filtro de inquilino (revisar manualmente cada uma)
grep -rn "\.from('" --include='*.ts' . | grep -v node_modules | grep -viE "org_id|tenant_id|client_id"

# funções security definer que escrevem — abrir cada uma: o where amarra a auth.uid()?
grep -rliE 'security\s+definer' --include='*.sql' . | grep -v node_modules \
  | xargs grep -nEi 'on\s+conflict.*do\s+update|^\s*update\s+[a-z_."]+\s+set|delete\s+from' 2>/dev/null \
  | grep -vE '(^|:)[0-9]+:\s*--'
```
