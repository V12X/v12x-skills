# Changelog

Todas as mudanças relevantes deste repositório são registradas aqui.

O formato segue [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o
versionamento segue [SemVer](https://semver.org/lang/pt-BR/). Cada entrada nomeia a **skill**
afetada e a sua versão; o repositório reúne mais de uma skill sob o [Método v12x](METHOD.md).

## [v12x-design-audit 1.0.0] — 2026-08-19

Primeira versão. Auditoria de conformidade ao design system, com aplicação das trocas — para o
caso em que o design system foi definido **depois** que as telas já existiam.

### Adicionado
- Arquitetura híbrida: `scripts/coletar-tela.js` varre o que é realmente pintado (a verdade) e
  `scripts/coletar-codigo.sh` inventaria os valores hardcoded com `arquivo:linha` (onde trocar);
  os dois se unem pelo valor bruto.
- `scripts/mapear.py`: motor de mapeamento determinístico — ΔE CIEDE2000 para cor (distância
  perceptual, não diferença de hex), distância absoluta para raio/espaço/tamanho, família
  normalizada para fonte. Emite a tabela `valor usado → token` com confiança e o veredito.
- Severidade por impacto visual e de marca; desvio repetido sobe de nível (é um componente
  errado propagado, não N erros).
- Referências: `cobertura-e-estados.md` (o que a varredura não vê — estados, temas, breakpoints,
  modais — e como declarar) e `aplicacao-segura.md` (lotes do seguro ao arriscado, trocar no
  componente e não nas folhas, usar o token e não o valor, verificar entre lotes).

## [v12x-design-audit 1.1.0] — 2026-08-25

### Corrigido
- **Trava anti-improviso.** Numa auditoria real de um app híbrido, o modelo, em vez de rodar os
  coletores, improvisou um refactor no lado web: trocou ícones (fora do escopo), reescreveu
  assinaturas de componente e **removeu um toggle de tema** — o oposto de uma auditoria de
  conformidade. O `SKILL.md` ganha três travas duras: sem `mapa.json` não se aplica nada;
  aplicação é só `literal → token` linha a linha (proibido tocar em import, prop, lógica, ícone);
  e o teste de uma linha no `git diff` antes de cada troca. `aplicacao-segura.md` carrega a mesma
  trava e exige `git status` limpo antes de começar.

### Adicionado
- Seção "Fora de escopo — declare, não adivinhe": ícone, escolha semântica de token e estrutura
  não são conformidade de valor, não são determinísticos, entram no mapa de cobertura como não
  cobertos. Silêncio aqui é o furo que o modelo preenche com achismo (Tese 2).

## [v12x-agent-audit 1.0.0] — 2026-08-19

Primeira versão. Auditoria de **confiança** de agentes, servidores MCP e skills — antes de
instalar um de terceiro ou publicar o seu.

### Adicionado
- Processo em fases (escopo/ameaça, extração determinística da superfície, análise por camada,
  verificação adversarial, severidade, veredito de instalação/publicação), sem pontuação.
- `scripts/fase0.sh`: extrai a superfície sem rodar o servidor — ferramentas e descrições,
  caracteres invisíveis (com fallback perl/python3 para o macOS sem `grep -P`), padrões
  perigosos no executor, permissões pedidas e proveniência — e emite o mapa de cobertura.
- Referências: `superficie-de-instrucao.md` (envenenamento de descrição, injeção indireta, texto
  escondido, sombreamento), `agencia-e-exfiltracao.md` (escopo mínimo, combinação letal, canal de
  saída, fronteira de segredo) e `proveniencia-e-cadeia.md` (autoria, rug pull, scripts de
  instalação, isolamento quando não dá para confiar).

## [v12x-scan 1.2.0] — 2026-08-14

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

## [v12x-scan 1.1.0] — 2026-08-13

### Adicionado
- Primeira versão pública da `v12x-scan` como skill autossuficiente: processo em fases
  (escopo/ameaça, ferramentas determinísticas, análise por categoria, verificação adversarial,
  severidade, relatório), sem pontuação e com mapa de cobertura obrigatório.
- Referências de fundamentos, aplicação web (IDOR, SSRF, XSS), iOS/Swift
  nativo, isolamento entre inquilinos, cadeia de suprimento/CI e pré-publicação.
- Empacotamento como marketplace de plugin do Claude Code.

[v12x-agent-audit 1.0.0]: https://github.com/V12X/v12x-skills/tree/main/skills/v12x-agent-audit
[v12x-scan 1.2.0]: https://github.com/V12X/v12x-skills/releases/tag/v1.2.0
[v12x-scan 1.1.0]: https://github.com/V12X/v12x-skills/commit/2b08afe520e44b66a47aa34fc5efbd4f497359f5
[v12x-design-audit 1.0.0]: https://github.com/V12X/v12x-skills/tree/main/skills/v12x-design-audit
