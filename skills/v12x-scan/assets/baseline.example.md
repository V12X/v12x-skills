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
