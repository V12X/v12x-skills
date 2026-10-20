# Linha de base de segurança

Renomeie para `.security-baseline.md` na raiz do repositório.

A skill lê este arquivo **antes** de reportar e omite do relatório o que estiver aqui como
risco aceito, mencionando só a contagem ("3 achados suprimidos pela linha de base"). Serve para
o relatório mostrar só o que é novo ou ainda aberto, sem repetir a cada auditoria o que já foi
decidido conscientemente.

Regras:

- Um risco só entra aqui depois de **decidido de propósito**, com motivo e responsável — nunca
  para calar um achado incômodo.
- Todo item tem **data de revisão**. Risco aceito não é aceito para sempre; a data força reabrir.
- Credencial exposta **não** entra na linha de base. Segredo se revoga, não se aceita.

Formato de cada entrada (uma por linha):

```markdown
- `arquivo.ts:42` — nome do achado — aceito em 2026-08-14 por: <motivo> — revisar em: <data>
```

## Exemplos

- `src/lib/legacy-import.ts:88` — SSRF em importador de URL — aceito em 2026-08-14 por: rota atrás de auth de admin, host em allowlist fixa, sem plano de expor ao público — revisar em: 2026-11-14
- `infra/Dockerfile:1` — imagem base sem pin por digest — aceito em 2026-08-14 por: ambiente só de build interno, não distribuído — revisar em: 2027-02-14

## Refutações — o que a Fase 2 já provou que NÃO é achado

Seção separada dos aceitos, de propósito: o aceito é um achado real que se decidiu tolerar; o
refutado nunca foi achado. Registrar evita re-litigar o mesmo candidato a cada auditoria — num
projeto real, a "chave publicável em arquivo ignorado" foi refutada pela **quarta auditoria
seguida**. A próxima auditoria lê aqui, pula direto, e menciona só a contagem.

Cada entrada guarda **o caminho que provou** a refutação, **o commit** contra o qual foi provada e
**o que reabriria** o candidato — sem os dois últimos, a refutação vira cheque em branco.

```markdown
- `arquivo:linha` — candidato — refutado em AAAA-MM-DD por: <a prova> — provado em: <commit> — reabrir se: <o que mudaria a conclusão>
```

**A refutação vale enquanto a fonte não muda, e isso se confere por diff, não de memória.** Na
auditoria seguinte, para cada entrada:

```bash
git diff <commit>..HEAD --stat -- <arquivo>   # mudou? a refutação reabre, independente do "reabrir se"
```

A prosa do "reabrir se" é o que o auditor lembrou de prever; o diff é o que aconteceu. Mesma regra
para o risco aceito: aceito em cima de um arquivo que mudou é aceito em cima de outra coisa.

### Exemplos

- `web/.env.local:3` — "chave vazada" em arquivo ignorado — refutado em 2026-09-04 por: é a chave **publicável** (anon) do Supabase, desenhada para o cliente; o arquivo é ignorado e o dado está atrás de RLS — provado em: b60593a — reabrir se: a chave `service_role` aparecer no mesmo arquivo, ou o arquivo entrar no git
- `.github/workflows/web.yml:41` — injeção via `${{ }}` — refutado em 2026-09-04 por: as interpolações são SHAs de ações e `github.sha`, não entrada de PR — provado em: b60593a — reabrir se: entrar `github.event.pull_request.*` ou `head_ref` num `run:`
- `supabase/functions/assistant/index.ts` — injeção indireta de prompt — refutado em 2026-09-04 por: o assistente não tem ferramenta de efeito colateral e a resposta não é renderizada com busca de URL; sem canal de saída, a injeção fica presa na própria resposta — provado em: b60593a — reabrir se: ganhar ferramenta que envia/apaga/publica, ou markdown com imagem remota

## Pendente de validação — o que depende de um fato fora do repositório

Não é risco aceito nem refutação: é hipótese precisa com **uma** incógnita que só o dono resolve
(painel do provedor, CDN, réplica, retenção). Fica aqui até ser resolvida — e a resolução vira
refutação ou achado. Sem severidade, por definição.

```markdown
- `arquivo:linha` — hipótese — fato que falta: <o quê> — checagem: <como o dono confere> — se confirmado: <nível> — aberto em AAAA-MM-DD
```

- `supabase/config.toml` — proteção contra senha vazada desligada — fato que falta: o interruptor em Authentication → Settings → Password security está ligado em produção? (não vive no repo) — checagem: abrir o painel e conferir — se confirmado desligado: Baixa — aberto em 2026-09-04
