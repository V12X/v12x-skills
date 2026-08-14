# v12x-skills

**Português** · [English](README.en.md)

[![Release](https://img.shields.io/github/v/release/V12X/v12x-skills?label=release&color=2ea043)](https://github.com/V12X/v12x-skills/releases/latest)
[![Licença](https://img.shields.io/github/license/V12X/v12x-skills?color=blue)](LICENSE)

Skills da [V12X](https://github.com/V12X) para o [Claude Code](https://claude.com/claude-code).
Um repositório, várias skills, instaláveis de uma vez como marketplace de plugin.

## Skills

| Skill | O que faz |
|---|---|
| **[v12x-scan](skills/v12x-scan)** | Auditoria de segurança em profundidade — ferramentas determinísticas antes da leitura, verificação adversarial de cada achado, relatório com veredito de publicação. Cobre fundamentos, aplicação web (IDOR, SSRF, XSS), backends fora de TS/JS (Python, Go, Ruby, PHP, Java), apps agênticos/LLM (injeção de prompt, MCP), iOS nativo, multi-tenancy, cadeia/CI e pré-publicação. Traz `scripts/fase0.sh` (fase determinística num comando) e templates de CI e linha de base. |

## Instalar

### Como marketplace de plugin (recomendado)

No Claude Code:

```
/plugin marketplace add V12X/v12x-skills
/plugin install v12x-scan@v12x-skills
```

### Manual

Copie a pasta da skill para o seu diretório de skills:

```bash
git clone https://github.com/V12X/v12x-skills.git
cp -R v12x-skills/skills/v12x-scan ~/.claude/skills/
```

## Usar

Depois de instalada, a skill dispara sozinha quando você pede uma auditoria, ou por nome:

```
/v12x-scan audita este repositório antes de eu publicar
```

## Princípios

Estas skills seguem o [**Método v12x**](METHOD.md) — auditoria de segurança em quatro teses:

1. **Ferramenta antes de opinião.** O que um scanner determinístico acha, ele acha melhor,
   mais barato e sem alucinar. A leitura crítica entra onde a ferramenta não alcança.
2. **Nenhum furo silencioso.** O relatório declara o que foi coberto e o que não foi. A
   diferença entre "não achei nada" e "não olhei" precisa estar escrita.
3. **Refute antes de reportar.** Todo achado sobrevive a uma tentativa de refutação. Falso
   positivo destrói a confiança no relatório inteiro.
4. **Veredito, não pontuação.** Nada de nota de 0 a 100: contagem por severidade e uma decisão
   binária de publicar.

O manifesto completo, com o porquê e um contraexemplo de cada tese, está em [METHOD.md](METHOD.md).

## Changelog

Mudanças por versão em [CHANGELOG.md](CHANGELOG.md). A versão atual é a
[v1.2.0](https://github.com/V12X/v12x-skills/releases/tag/v1.2.0).

## Licença

MIT — veja [LICENSE](LICENSE).

## Contribuir

Antes de subir qualquer skill nova, rode a `v12x-scan` nela: `.gitignore` cobrindo segredos,
varredura de histórico limpa, nenhum caminho de máquina ou nome interno vazado. A ferramenta
audita as próprias ferramentas. Detalhes de estilo, versionamento e release em
[CONTRIBUTING.md](CONTRIBUTING.md).
