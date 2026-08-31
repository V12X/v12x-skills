# Fundamentos

As oito classes que qualquer auditoria precisa cobrir, independentemente de stack. São os
padrões que aplicação gerada com IA erra com mais frequência. Se você tiver a skill
`vibe-security` instalada ao lado, ela aprofunda cada um; esta referência existe para que a
v12x-scan funcione sozinha.

Princípio que atravessa tudo: **nunca confie no cliente.** Todo preço, id de usuário, papel,
status de assinatura e contador de rate limit precisa ser validado no servidor. Se existe só
no navegador, no app ou no corpo da requisição, quem ataca controla.

---

## 1. Segredos e variáveis de ambiente

- **Nada de credencial embutida no código.** Chave, token, senha, string de conexão. Se um
  segredo já foi commitado, considere-o comprometido e **rotacione** — apagar num commit
  posterior não remove do histórico (fase 0 cobre a varredura).
- **Prefixos de cliente vazam no bundle.** `NEXT_PUBLIC_`, `VITE_`, `EXPO_PUBLIC_`,
  `REACT_APP_` são embutidos no JavaScript do navegador em build. Tudo que leva esse prefixo é
  público.

| Pode ser público | Nunca pode |
|---|---|
| Chave publicável do Stripe (`pk_*`) | Chave secreta do Stripe (`sk_*`) |
| Chave anônima do Supabase (com RLS ativo) | `service_role` do Supabase (ignora RLS) |
| Config de cliente do Firebase | String de conexão de banco |
| ID público de analytics | Segredo de assinatura de JWT, secret de OAuth |

- **`.gitignore` antes do primeiro commit** cobrindo `.env`, `.env.local`, `.env.*.local`.
- **`.env.example` só com placeholder**, nunca valor real.
- **Default público que vira segredo real.** Um `${JWT_SECRET:-dev-secret}` ou
  `SECRET_KEY = os.getenv("KEY", "changeme")` **funciona sem a variável setada** — e em produção,
  se ninguém sobrescreveu, o "default de desenvolvimento" **é o segredo de produção**, e ele está
  no código, público. Procurar em docker-compose, charts (Helm), CI, `settings.py`, `config.*`:
  ```bash
  # shell/compose: ${VAR:-default}
  grep -rnE '\$\{[A-Z_]+:-[^}]+\}' . | grep -viE 'test|example' | grep -v node_modules
  # código: getenv/env com fallback embutido
  grep -rnE 'getenv\([^,)]+,[^)]+\)|process\.env\.[A-Z_]+\s*\|\|' . | grep -viE 'test|example' | grep -v node_modules
  ```
- **Falta de validação de startup é o que torna o default perigoso.** O app deveria **recusar
  subir** se um segredo estiver no valor de default (ou vazio) em produção. A ausência desse
  check — o app sobe feliz com `dev-secret` — é achado por si (Alta): nada avisa que a produção
  está rodando com a credencial do exemplo.

## 2. Controle de acesso no banco

O nº 1 em criticidade de app gerado com IA.

- **Supabase:** RLS ligado em toda tabela com dado de usuário, com política derivando de
  `auth.uid()`, e política por operação (SELECT, INSERT, UPDATE, DELETE) — não só SELECT. O
  `WITH CHECK` do insert impede gravar em nome de outro. Detalhe em `multi-tenancy.md`.
- **Firebase:** regras de segurança que conferem `request.auth.uid`; o padrão perigoso é
  `allow read, write: if true`.
- **Regra geral:** a autorização não pode viver só na consulta do frontend. O atacante fala
  direto com o banco/API.

## 3. Autenticação e autorização

- **Autenticação** confere que a sessão é válida. **Autorização** confere que o recurso é
  daquele usuário. App gerado com IA quase sempre faz a primeira e esquece a segunda — é o
  IDOR, detalhado em `web-app.md` item 1.
- Verificação de JWT com a assinatura conferida no servidor, não só decodificada.
- Middleware de auth cobre **todas** as rotas protegidas, inclusive as novas.
- Server Actions e rotas de API revalidam a sessão — não presumem que o cliente já checou.

## 4. Rate limiting

- Endpoints de autenticação (login, recuperação de senha, OTP) precisam de limite, senão
  são alvo de força bruta e de enumeração.
- Operações caras (IA, geração de relatório, envio de e-mail) precisam de limite por usuário.
- O contador vive no servidor. Contador em cookie ou header é adulterável.

## 5. Pagamento

- **Preço vem do servidor, nunca do corpo da requisição.** O padrão fatal é
  `unit_amount: req.body.price` — o atacante paga R$ 0,01. Buscar o preço pelo id do produto
  no servidor.
- **Webhook com assinatura verificada.** Sem verificar a assinatura do Stripe, qualquer um
  simula "pagamento aprovado".
- **Status de assinatura conferido no servidor** a cada acesso a recurso pago, não guardado
  só no cliente.

## 6. Integração com LLM

- Chave da API de IA **nunca no cliente** — vai num backend que faz proxy. Chave embutida no
  app ou no bundle é conta drenada.
- Teto de uso: `max_tokens` e timeout em toda chamada, e rate limit por usuário. Sem isso, um
  usuário gera custo ilimitado.
- Saída do modelo é conteúdo não confiável: se for renderizada como HTML, sanitizar
  (`web-app.md` item 4). Se alimentar outra ação, tratar como entrada de usuário.
- Injeção de prompt: entrada do usuário não pode sobrescrever a instrução de sistema em
  operação sensível.
- **App agêntico (ferramentas, MCP, RAG, agente que age):** a superfície vai muito além disto —
  injeção de prompt indireta, tool poisoning, agência excessiva, exfiltração pelo canal de
  saída. Ver `references/llm-agentes.md`.

## 7. Configuração de deploy

- Modo produção real: sem debug, sem stack trace exposto ao cliente (`web-app.md` item 8).
- Source maps não servidos em produção (entregam o código-fonte original).
- Separação de ambiente: credencial de produção não vive em `.env` de desenvolvimento nem em
  preview público.
- Cabeçalhos de segurança configurados (`web-app.md` item 7).

## 8. Injeção e validação de entrada

- **SQL/NoSQL:** consulta parametrizada sempre. Nunca concatenar entrada do usuário em query.
  ORM ajuda, mas `queryRaw` com template de string reabre o buraco.
- **Validação na entrada** com schema (zod, valibot) que declara os campos permitidos — isso
  também fecha mass assignment (`web-app.md` item 2).
- **Comando de shell** com entrada do usuário: evitar; se inevitável, sem interpolação em
  shell, com argumentos separados.
- **Caminho de arquivo** derivado de entrada: normalizar e conferir que fica dentro do
  diretório esperado (path traversal).

---

## Verificação rápida

```bash
# segredo com prefixo público
grep -rnE '(NEXT_PUBLIC|VITE|EXPO_PUBLIC|REACT_APP)_[A-Z_]*(KEY|SECRET|TOKEN|PASSWORD|SERVICE)' . | grep -v node_modules

# service_role em qualquer lugar
grep -rnE 'service_role|SERVICE_ROLE' . | grep -v node_modules

# preço vindo do corpo
grep -rnE 'unit_amount|amount.*req\.(body|query)' --include='*.ts' . | grep -v node_modules

# SQL cru com interpolação
grep -rnE '(queryRaw|query\()\s*`[^`]*\$\{' --include='*.ts' . | grep -v node_modules

# Firebase aberto
grep -rnE 'allow (read|write|read, write):\s*if true' . 2>/dev/null

# regra da casa: cada achado aqui passa pela verificação adversarial da fase 2 do SKILL
```
