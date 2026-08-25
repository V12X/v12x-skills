# Instalar e usar as skills da V12X

Testado no Claude Code. Se algo aqui falhar, é bug de empacotamento nosso —
[abra uma issue](https://github.com/V12X/v12x-skills/issues), porque o
`plugins.yml` deveria ter pego antes de chegar em você.

## 1. Adicionar o marketplace

```
/plugin marketplace add V12X/v12x-skills
```

Se você já tinha adicionado antes (e as skills novas não aparecem), o clone local
está velho. **Remova e adicione de novo** — é o reset que resolve 90% dos casos:

```
/plugin marketplace remove v12x-skills
/plugin marketplace add V12X/v12x-skills
```

## 2. Instalar a(s) skill(s)

```
/plugin install v12x-scan@v12x-skills
/plugin install v12x-agent-audit@v12x-skills
/plugin install v12x-design-audit@v12x-skills
```

## 3. Recarregar

Comando novo só entra em vigor no boot. **Reinicie a sessão** do Claude Code
(feche e reabra). Algumas versões têm `/reload-plugins`; se a sua não tiver,
reiniciar tem o mesmo efeito.

## 4. Usar — dois caminhos

**a) Slash command** (o comando é *namespaced* por plugin):

```
/v12x-scan:scan          audita segurança deste repositório antes de publicar
/v12x-agent-audit:audit  esse servidor MCP é seguro para instalar?
/v12x-design-audit:audit aplica o design system nestas telas
```

Digite `/v12x` e o autocomplete mostra a forma exata.

**b) Por nome da skill** (funciona sempre, mesmo se o comando não carregar):

> Use a skill **v12x-design-audit** para auditar a conformidade deste projeto ao
> design system em `caminho/do/design-system`.

Skill dispara por descrição — não depende de comando, de restart, nem de nada.

## Como saber se a skill rodou de verdade (não improvisou)

Toda skill da V12X tem a mesma **impressão digital**:

1. No começo, a **contagem de itens varridos** ("51 arquivos .swift varridos").
2. No fim, um **veredito com contagem por severidade** — nunca uma nota.

Se você vê prosa solta, sem contagem e sem veredito, o modelo improvisou a partir
da sua frase. Repita nomeando a skill explicitamente (caminho **b**).


## Instalação manual (web/desktop, sem `/plugin`)

Onde `/plugin` não existe (app web/desktop, SDK), copie as skills para `~/.claude/skills/` com um comando, do clone do repo:

```bash
bash scripts/sync-skills.sh
```

Rode de novo sempre que atualizar uma skill (a cópia não se atualiza sozinha) e **reinicie a sessão**. `--dry-run` mostra o que faria sem copiar.

## Solução de problemas

| Sintoma | Causa | O que fazer |
|---|---|---|
| `Unknown command: /v12x-...` | comando ainda não carregado | reiniciar a sessão após instalar |
| "a skill X não existe neste ambiente" | não instalada, ou marketplace velho | remover+adicionar marketplace, reinstalar |
| skill nova não aparece para instalar | clone local do marketplace desatualizado | `/plugin marketplace remove` e `add` de novo |
| o modelo "auditou" mas sem contagem nem veredito | improvisou, não carregou a skill | nomear a skill na mensagem (caminho **b**) |
| `/plugin` não existe | sessão não-interativa (cron, SDK) | use o caminho **b** (por nome da skill) |

## Requisitos das ferramentas determinísticas

As skills chamam ferramentas de linha de comando quando presentes, e **declaram
como não coberto** quando faltam (nunca fingem cobertura):

- `v12x-scan`: `gitleaks`, `osv-scanner`, `semgrep` (`brew install ...`)
- `v12x-agent-audit`: `gitleaks`, `osv-scanner`; `perl` ou `python3` para invisíveis
- `v12x-design-audit`: `python3`; navegador (web) ou projeto Swift local
