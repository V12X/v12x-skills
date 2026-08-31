# Contribuir

Obrigado por contribuir com as skills da V12X. Este guia descreve o mínimo para uma mudança
entrar com segurança.

## Regra de ouro: rode a `v12x-scan` na sua própria mudança

Antes de commitar skill nova ou alteração, **audite os arquivos com a própria `v12x-scan`** —
é o dogfooding que mantém o repositório limpo. Na prática, rode a fase determinística e
confirme que está tudo limpo:

```bash
bash skills/v12x-scan/scripts/fase0.sh .
```

E valide o empacotamento (o CI roda isto a cada push):

```bash
python3 scripts/smoke-plugins.py
```

O que precisa passar antes de subir:

- `gitleaks` limpo no **histórico** e na **árvore** (incluindo arquivos ignorados).
- Nenhum caminho absoluto de máquina com nome de pessoa (`/Users/fulano/`, `C:\Users\...`).
- Nenhum e-mail corporativo, IP interno, URL de painel interno ou nome de cliente.
- Nenhum segredo real em exemplo — use placeholders (`sk-...`, `example.com`).

Contexto interno não vaza para um repositório público: ver
`skills/v12x-scan/references/pre-publicacao.md`.

## Estilo das skills

- **Português**, direto, alto sinal por linha. Uma referência carrega só o que a auditoria
  daquela camada precisa.
- Exemplos de código no par **ERRADO / CERTO**, com o padrão de `grep` correspondente ao final
  da seção quando fizer sentido.
- Ferramenta antes de opinião; nenhum furo silencioso; verificação antes de reportar — os três
  princípios do `README`.

## Versão

O esquema (versão por skill em SemVer + versão do marketplace) está em
[VERSIONING.md](VERSIONING.md), com o checklist de onde tocar ao subir uma versão. O
`scripts/smoke-plugins.py` (no CI) confere que os manifestos batem.


## Changelog e release

O `CHANGELOG.md` (padrão [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)) é a
**fonte da verdade** das notas de release — não duplique o texto.

1. Adicione a entrada da nova versão no topo do `CHANGELOG.md`, com as subseções
   **Adicionado / Alterado / Corrigido / Removido** que se aplicarem.
2. Garanta que a versão casa com o `SKILL.md` e o `marketplace.json`.
3. Publique a release montando as notas **a partir da seção do CHANGELOG**:

```bash
gh release create vX.Y.Z --target main --title "vX.Y.Z — <resumo>" --notes-file <seção-do-changelog>
```

## Commits

- Mensagem no imperativo, explicando o **porquê** além do quê.
- Um commit coeso por unidade de mudança; evite misturar refatoração com conteúdo novo.
