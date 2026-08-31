# Versionamento

Dois níveis, de propósito — a coleção evolui num ritmo, cada skill no seu.

## 1. Cada skill tem sua versão (SemVer)

Vive em **dois lugares que precisam bater**:
- `skills/<skill>/SKILL.md` → `metadata.version`
- `skills/<skill>/.claude-plugin/plugin.json` → `version`

SemVer, por skill:

| Parte | Sobe quando… | Exemplo real |
|---|---|---|
| **MAJOR** | muda de forma incompatível: remove uma fase, muda o formato de saída, renomeia um script que alguém chama | — |
| **MINOR** | capacidade nova e compatível: uma camada/referência nova, um eixo novo, uma saída opcional | v12x-scan 1.2 → **1.3** (issues de GitHub, pontos fortes) |
| **PATCH** | correção ou calibração, sem capacidade nova: bug de coletor, ajuste de limiar, correção de texto | v12x-coherence 1.0.0 → **1.0.1** (calibração no Quezty) |

## 2. O marketplace tem a sua (0.x)

Vive em `.claude-plugin/marketplace.json` → `metadata.version`. É a versão **da coleção**, não de
uma skill. Sobe quando o conjunto muda: uma skill nova entra, ou várias são atualizadas num lote.

Ainda em `0.x` porque a família está crescendo rápido. O `1.0.0` do marketplace fica para quando o
conjunto estabilizar (escopo de skills fechado, sem mudança estrutural à vista).

## Tags e releases do GitHub

- A tag segue a versão do **marketplace**: `v0.5.0`, `v0.6.0`…
- A release reúne o estado da suíte inteira naquele ponto; as notas saem do `CHANGELOG.md`.
- **Legado:** `v1.2.0` foi tagueada quando havia só a `v12x-scan` e a tag seguia a versão *dela*.
  A partir de `v0.5.0` a tag é sempre a do marketplace. O `v1.2.0` fica como marco histórico —
  apesar do número, não é "maior" que `v0.5.0` no sentido da coleção; são esquemas diferentes, e o
  atual é o do marketplace.

## Ao subir uma versão — checklist

**Uma skill mudou:**
1. `skills/<skill>/SKILL.md` → `metadata.version`
2. `skills/<skill>/.claude-plugin/plugin.json` → `version` (igual ao de cima)
3. `.claude-plugin/marketplace.json` → a `version` da entrada daquela skill em `plugins[]`
4. uma entrada no `CHANGELOG.md`: `## [<skill> X.Y.Z] — AAAA-MM-DD`

**A coleção mudou (skill nova, ou lote), e vai publicar:**
5. `.claude-plugin/marketplace.json` → `metadata.version` (o marketplace)
6. `gh release create v<marketplace>` com as notas montadas do CHANGELOG

O `scripts/smoke-plugins.py` valida que os nomes e a presença dos manifestos batem, e roda no CI —
então um plugin com versão fora do lugar não passa despercebido.

## O CHANGELOG é a fonte das notas

Uma entrada por versão de skill, no formato `## [<skill> X.Y.Z] — data`, com
Adicionado/Alterado/Corrigido. A release não reescreve texto: ela **cita** o CHANGELOG.
