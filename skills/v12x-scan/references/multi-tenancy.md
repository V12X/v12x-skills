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
achado por si:

```
1. criar organização A e organização B, com um usuário em cada
2. criar registro em A
3. autenticar como usuário de B
4. tentar ler, atualizar e apagar o registro de A, por API e por consulta direta
5. as quatro operações precisam falhar
```

Rodar esse teste para **cada tabela** com dado de inquilino, e para o storage. É o único
jeito de transformar "acho que isola" em "prova que isola".

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
```
