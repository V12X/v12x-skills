# Proveniência e cadeia

Carregar quando o alvo é componente de terceiro que você vai instalar, ou quando tem
dependências e scripts de instalação. Instalar um servidor MCP ou skill é **rodar código de um
estranho no seu contexto** — a pergunta antes de "o que ele faz?" é "de quem é, e o que muda
embaixo de mim?".

---

## 1. De quem é, e dá para saber?

- **Autor e repositório identificáveis?** Componente sem autor claro, sem repositório de fonte,
  sem histórico — a confiança é zero e isso **é achado por si** (Média no mínimo). Você não pode
  auditar o que não vê.
- **Sinais de manutenção real?** Idade, commits, issues respondidas. Um servidor de um dia e zero
  histórico não ganha o benefício da dúvida com acesso à sua máquina.
- **Fonte auditável?** Se o que você instala é um binário ou pacote publicado **diferente** do
  código do repositório, você está confiando num artefato que não leu. Registre no mapa de
  cobertura: "executor X sem fonte — não coberto".

```bash
grep -nE '"(name|version|author|repository|homepage|license)"' package.json 2>/dev/null
git -C . log --oneline -5 2>/dev/null || echo "sem histórico git — proveniência não verificável"
```

## 2. Pin e rug pull — o benigno que fica malicioso depois

Um servidor honesto na instalação pode mudar a definição na próxima versão. É o **rug pull**: a
descrição que você auditou não é a que vai rodar amanhã.

- O componente está **pinado por versão exata ou SHA**, não por tag móvel nem `latest`?
- A atualização **reaudita**? A skill trata a atualização de um servidor MCP como um novo alvo —
  porque é onde a definição muda sem você olhar.
- Referência por URL de git ou `latest` muda sem aviso. Pinar.

```bash
# dependências/servidores por tag móvel, latest, ou url de git
grep -rnE '"[^"]+"\s*:\s*"(\^|~|latest|\*|git\+|https?://)' package.json 2>/dev/null
grep -rniE 'command|args' mcp.json server.json .mcp.json 2>/dev/null | grep -iE 'npx|-y|latest'
```

`npx -y algum-servidor` na configuração baixa e executa a versão de agora, sem pin — cada
inicialização pode trazer código novo.

## 3. Scripts de instalação — execução no momento da conexão

`postinstall`/`preinstall` no `package.json` rodam **quando você instala**, antes de qualquer
ferramenta ser chamada. É o vetor mais direto: você não precisa nem usar o servidor para ser
comprometido.

```bash
grep -nE '"(pre|post)?install"\s*:' package.json 2>/dev/null && echo "^ roda na instalação — LER o que faz"
```

## 4. A superfície das dependências

O servidor herda tudo o que as dependências dele podem fazer. Uma dependência comprometida é um
servidor comprometido.

```bash
osv-scanner scan source -r . 2>/dev/null || echo "NÃO COBERTO: osv-scanner ausente (brew install osv-scanner)"
grep -nE '"(git\+|https?://)' package.json 2>/dev/null   # deps fora do registro versionado
```

Confirmar também: **lockfile commitado**? Sem ele, o que você audita hoje não é o que instala
amanhã — a Tese 2 (nenhum furo silencioso) aplicada à cadeia.

## 5. Segredos no próprio componente

```bash
gitleaks git . --redact 2>/dev/null || gitleaks detect --source . --redact 2>/dev/null \
  || echo "NÃO COBERTO: gitleaks ausente"
```

---

## Quando não dá para confiar, mas você precisa usar

Nem todo componente de terceiro dá para tornar confiável por auditoria. Se o veredito é "não
comprovadamente seguro" mas há necessidade real, a saída não é "instalar mesmo assim" — é
**isolar**:

- rodar o servidor **sem acesso a segredo** (sem `.env`, sem token de produção);
- **sem rede**, ou com allowlist de destino, se ele não precisa sair;
- num sandbox/contêiner sem acesso ao sistema de arquivos do usuário;
- sem conectá-lo a **outros** servidores/ferramentas de efeito colateral (evita sombreamento).

O veredito então é condicional e explícito: *"instalar apenas isolado — sem segredo, sem rede;
não comprovadamente seguro para acesso pleno."*

---

## Verificação adversarial nesta camada

Antes de reportar: o `postinstall` faz mesmo algo perigoso, ou só compila? A dependência marcada
tem caminho de exploração no uso real do servidor, ou é transitiva sem alcance? Proveniência
fraca é sempre reportável, mas a severidade sobe com o **poder** que o componente pede — um
servidor sem autor que só formata texto local é Média; um que pede sua caixa de e-mail é Crítica.
