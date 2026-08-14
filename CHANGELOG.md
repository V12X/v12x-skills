# Changelog

Todas as mudanças relevantes deste repositório são registradas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o
versionamento segue [SemVer](https://semver.org/lang/pt-BR/). As versões referem-se à skill
`v12x-scan` (a única do repositório até aqui).

## [1.2.0] — 2026-08-14

### Adicionado
- `scripts/fase0.sh`: roda toda a fase determinística num comando (segredos no histórico e na
  árvore com ignorados, chaves soltas, `.env` exposto, dependências, semgrep). Degrada com
  elegância quando falta ferramenta — cada ausência vira `NÃO COBERTO` —, detecta a linguagem
  do backend e imprime o mapa de cobertura pronto.
- `references/linguagens-backend.md`: os padrões de IDOR, mass assignment, SQL por
  concatenação e SSRF para Python/Django/DRF, Ruby/Rails, PHP/Laravel, Go e Java/Kotlin/Spring
  — fecha o furo silencioso de backends fora de TS/JS.
- `references/llm-agentes.md`: camada de apps agênticos — injeção de prompt indireta,
  confiança em servidor MCP e *tool poisoning*, agência excessiva, exfiltração pelo canal de
  saída e saída do modelo como código.
- `assets/security-ci.yml`: workflow mínimo que amarra gitleaks + osv-scanner + semgrep em
  cada push e PR, sem nenhuma ação de terceiro para pinar.
- `assets/baseline.example.md`: modelo de `.security-baseline.md` para registrar risco aceito.
- Badges de release e licença no `README`.

### Alterado
- `SKILL.md`: atalho para `scripts/fase0.sh` na Fase 0, tabela de camadas ampliada (linguagens
  de backend e apps agênticos/LLM), nota de cobertura por linguagem e ponteiros para os
  templates de CI e linha de base.
- Descrição da skill no `README` e no `marketplace.json` refletindo as novas camadas; versão
  do plugin para `1.2.0`.

### Corrigido
- Precisão de comando: `gitleaks detect` → `gitleaks git` (renomeado na 8.19+); o
  `scripts/fase0.sh` detecta a forma disponível sozinho.

## [1.1.0] — 2026-08-13

### Adicionado
- Primeira versão pública da `v12x-scan` como skill autossuficiente: processo em fases
  (escopo/ameaça, ferramentas determinísticas, análise por categoria, verificação adversarial,
  severidade, relatório), sem pontuação e com mapa de cobertura obrigatório.
- Referências de fundamentos, aplicação web (IDOR, SSRF, XSS, CORS/CSRF, upload), iOS/Swift
  nativo, isolamento entre inquilinos, cadeia de suprimento/CI e pré-publicação.
- Empacotamento como marketplace de plugin do Claude Code.

[1.2.0]: https://github.com/V12X/v12x-skills/releases/tag/v1.2.0
[1.1.0]: https://github.com/V12X/v12x-skills/commit/2b08afe520e44b66a47aa34fc5efbd4f497359f5
