# Pré-publicação

Auditar antes de tornar um repositório público, entregar código a cliente, ou publicar um
pacote open source. É a última janela em que ainda dá para consertar de graça: **depois de
publicado, o histórico é imutável na prática** — clones e forks já saíram.

---

## Histórico do git é a superfície real

O erro mais caro é auditar a árvore de trabalho e esquecer o histórico. Segredo removido num
commit posterior **continua no repositório** e é recuperável com um comando.

```bash
gitleaks detect --source . --redact --report-format json --report-path /tmp/leaks.json

# arquivos sensíveis que já existiram em qualquer ponto do histórico
git log --all --diff-filter=A --name-only --format='' \
  | sort -u | grep -iE '\.(env|p8|p12|pem|key|keystore|mobileprovision)$|credential|secret'

# tamanho suspeito no histórico (banco de dados, dump, backup commitado por engano)
git rev-list --objects --all \
  | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' \
  | awk '$1=="blob" && $3>1000000 {print $3, $4}' | sort -rn | head -20
```

**Se achar segredo no histórico, a ordem é esta e não outra:**

1. **Revogar a credencial.** Primeiro, sempre. Ela já vazou no instante do commit.
2. Reescrever o histórico com `git filter-repo` ou publicar repositório novo sem histórico.
3. Só então publicar.

Inverter essa ordem é o erro clássico: limpa-se o histórico, publica-se, e a chave antiga
continua válida.

---

## Limpeza de contexto interno

O que não é vulnerabilidade técnica mas entrega informação de reconhecimento a quem quiser
atacar, e expõe pessoas.

| O que procurar | Por quê |
|---|---|
| IP interno, faixa privada, hostname de rede | Mapa da infraestrutura interna |
| E-mail corporativo, nome de funcionário, telefone | Alvo de engenharia social e dado pessoal de terceiro |
| Caminho absoluto com nome de usuário (`/Users/fulano/`, `C:\Users\Admin\`) | Expõe pessoa e estrutura da máquina |
| URL de painel interno, Jira, Notion, Confluence | Superfície interna e possível acesso indevido |
| Comentário descrevendo arquitetura privada, "gambiarra", "TODO: consertar antes que descubram" | Aponta onde atacar, e é constrangedor |
| Nome de cliente em código ou em dado de teste | Quebra de confidencialidade contratual |
| Dado de teste com CPF, e-mail ou telefone real | Dado pessoal real vazando como fixture |

```bash
# caminhos absolutos de máquina
grep -rnE '/(Users|home)/[a-z][a-z0-9._-]+/' --include='*.ts' --include='*.tsx' --include='*.swift' --include='*.js' --include='*.md' . | grep -v node_modules

# IPs privados
grep -rnE '\b(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)[0-9]{1,3}\.[0-9]{1,3}\b' . | grep -v node_modules

# e-mails que não sejam de exemplo
grep -rnE '[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}' --include='*.ts' --include='*.swift' --include='*.md' . \
  | grep -viE 'example\.(com|org)|@sentry|noreply|localhost' | grep -v node_modules

# comentários que revelam mais do que deviam
grep -rniE '(TODO|FIXME|HACK|XXX).{0,80}(senha|password|token|chave|interno|prod|cliente)' --include='*.ts' --include='*.swift' . | grep -v node_modules
```

---

## Auditoria de log

Variável sensível que chega ao log vaza para o console, para o arquivo, e principalmente
para o serviço de monitoramento de erro — que é um terceiro com retenção própria.

```bash
grep -rnE '(console\.(log|error|warn)|print\(|NSLog|os_log|logger\.)' --include='*.ts' --include='*.tsx' --include='*.swift' . \
  | grep -viE 'test|spec' \
  | grep -iE 'senha|password|token|secret|key|cpf|email|auth|session|card|cvv'
```

Auditar também o que vai ao Sentry, Crashlytics ou equivalente: contexto de usuário, corpo de
requisição e cabeçalho costumam ir junto por padrão e carregam `Authorization`.

Em Swift, `os_log` com interpolação padrão **redige** valores dinâmicos em produção, mas
`"\(valor, privacy: .public)"` desfaz isso. Procurar `privacy: .public` em log com dado de
usuário.

---

## Proteção de custo em serviço pago

Vale como categoria própria porque a consequência é fatura, não vazamento — e chega rápido.

- Toda chamada a LLM define **`max_tokens`** e **timeout**? Sem teto, uma entrada maliciosa
  gera resposta gigante e cara.
- O backend limita o **tamanho do corpo da requisição**? Sem limite, o usuário manda 50 MB
  para processar. No Next.js, `bodyParser.sizeLimit`; num proxy, `client_max_body_size`.
- Existe **rate limit por usuário** nas rotas caras, e ele é imposto no servidor?
- Existe **teto de gasto** configurado no painel do provedor? É a última linha de defesa e
  não custa nada ligar.
- Chamada a serviço pago exige **autenticação**? Endpoint de IA aberto é conta drenada em
  horas.

```bash
# chamadas de LLM sem teto aparente
grep -rnE '(openai|anthropic|generativelanguage|gemini)' --include='*.ts' --include='*.swift' . \
  | grep -v node_modules | grep -viE 'max_?tokens|maxTokens'
```

---

## Licenciamento

Ponto ignorado que vira passivo jurídico, principalmente em modelo open-core.

- O repositório tem arquivo de licença explícito? Sem licença, ninguém pode usar legalmente —
  e é o oposto do objetivo de publicar.
- **Compatibilidade de dependência:** dependência GPL dentro de produto proprietário
  contamina. Auditar a árvore com `npm ls --all` ou o `Package.resolved`.
- **Núcleo GPL com app proprietário na App Store** é o caso mais delicado: a licença exige
  poder relicenciar, e a distribuição da loja impõe restrições que historicamente conflitam
  com a GPL. Se essa for a estrutura, **isto é achado que exige revisão jurídica**, e a
  auditoria deve dizer isso explicitamente em vez de opinar.
- Se houver dual-licensing, existe CLA dos contribuidores? Sem isso, não há direito de
  relicenciar contribuição de terceiro.

---

## Checklist final antes de publicar

- [ ] `gitleaks` limpo na árvore **e** no histórico
- [ ] Toda credencial que já apareceu no histórico foi **revogada**, não só removida
- [ ] `.gitignore` cobre `.env*`, `*.p8`, `*.p12`, `*.pem`, `*.key`, `*.mobileprovision`
- [ ] Nenhum caminho absoluto com nome de pessoa
- [ ] Nenhum IP interno, e-mail corporativo ou URL de painel interno
- [ ] Nenhum dado pessoal real em fixture de teste
- [ ] Log não emite segredo nem dado pessoal
- [ ] Arquivo de licença presente e compatível com as dependências
- [ ] Serviço pago com teto, timeout, limite de payload e autenticação
- [ ] README não descreve infraestrutura interna
- [ ] Se o repositório já foi público antes: assumir que tudo do histórico já foi visto
