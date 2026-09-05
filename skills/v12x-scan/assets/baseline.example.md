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

Cada entrada guarda **o caminho que provou** a refutação e **o que reabriria** o candidato — sem
o segundo, a refutação vira cheque em branco.

```markdown
- `arquivo:linha` — candidato — refutado em AAAA-MM-DD por: <a prova> — reabrir se: <o que mudaria a conclusão>
```

### Exemplos

- `web/.env.local:3` — "chave vazada" em arquivo ignorado — refutado em 2026-09-04 por: é a chave **publicável** (anon) do Supabase, desenhada para o cliente; o arquivo é ignorado e o dado está atrás de RLS — reabrir se: a chave `service_role` aparecer no mesmo arquivo, ou o arquivo entrar no git
- `.github/workflows/web.yml:41` — injeção via `${{ }}` — refutado em 2026-09-04 por: as interpolações são SHAs de ações e `github.sha`, não entrada de PR — reabrir se: entrar `github.event.pull_request.*` ou `head_ref` num `run:`
- `supabase/functions/assistant/index.ts` — injeção indireta de prompt — refutado em 2026-09-04 por: o assistente não tem ferramenta de efeito colateral e a resposta não é renderizada com busca de URL; sem canal de saída, a injeção fica presa na própria resposta — reabrir se: ganhar ferramenta que envia/apaga/publica, ou markdown com imagem remota
