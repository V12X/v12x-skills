# Ledger de cobertura · v12x-scan

Exemplo de `.security-ledger.md` persistido na raiz ao fim de uma auditoria. É gerado por
`scripts/ledger.py rascunho` (via `fase0.sh`), marcado durante a Fase 1 com `ledger.py marcar`, e
validado antes do relatório com `ledger.py validar --final`. A próxima auditoria lê este arquivo e
**herda** o que não mudou: `coberto` em `0084abc` continua coberto se `git diff 0084abc..HEAD --
<origem>` for vazio; senão volta a `planejado` com a nota "fonte mudou desde 0084abc".

Gerado em 2026-09-05 · commit b60593a · 14 unidades.
Estados: coberto 9 · amostrado 1 · fora-de-escopo 2 · adiado 1 · pendente 1

Regras: toda unidade termina com um estado. `coberto`/`amostrado` exigem `lido em` (commit).
Rodada com escopo marca o resto `fora-de-escopo`, nunca `coberto`. `adiado` leva motivo.

| id | tipo | unidade | origem | estado | lido em | nota |
|---|---|---|---|---|---|---|
| tab-ccb31 | tabela | members | supabase/migrations/0084_ninguem_entra_sozinho.sql:27 | coberto | b60593a | grant por coluna conferido |
| tab-9a1e0 | tabela | workspaces | supabase/migrations/0083_grant_por_coluna.sql:12 | coberto | b60593a | operator_note fora do grant |
| pol-7cb00 | policy | members · INSERT · "admin convida" | supabase/migrations/0084_ninguem_entra_sozinho.sql:24 | coberto | b60593a | só admin; teste de isolamento cobre |
| pol-094c5 | policy | members · SELECT · "membro lê o time" | supabase/migrations/0001_workspace.sql:148 | coberto | b60593a |  |
| pol-99dcd | policy | members · UPDATE · "cada um edita o próprio cadastro" | supabase/migrations/0001_workspace.sql:152 | coberto | b60593a | duplicada com a da 0065 (acento) — ver achado M-3 |
| fun-f0068 | função | post_assistant_message(uuid, uuid, uuid, text, uuid, jsonb) | supabase/migrations/0083_a_funcao_confere.sql:47 | coberto | b60593a | security definer · where amarra p_user |
| fun-2c7d1 | função | admin_set_plan(uuid, text) | supabase/migrations/0066_planos.sql:30 | coberto | b60593a | security definer · só service_role |
| edg-11f3a | edge | teach | supabase/functions/teach/index.ts | coberto | b60593a | lê arquivo com o token da pessoa |
| edg-6b0e2 | edge | asaas | supabase/functions/asaas/index.ts | amostrado | b60593a | lido o webhook (assinatura); cobrança não lida |
| edg-83d4c | edge | push | supabase/functions/push/index.ts | adiado |  | depende do segredo do APNs que não está no repo; validar no painel |
| buc-a1f1b | bucket | attachments | supabase/migrations/0008_chat.sql:73 | pendente |  | política de storage confere o workspace, mas o CDN da frente cacheia objeto privado? checar `x-cache` com URL assinada expirada |
| wor-d31bd | workflow | ci.yml | .github/workflows/ci.yml | coberto | b60593a | ações pinadas por SHA; permissions: contents read |
| dee-02477 | deeplink | eazyspace:// | App/Info.plist | fora-de-escopo |  | rodada só de plataforma; iOS fica para a próxima |
| rot-a8007 | rota | web/app/api/health | web/app/api/health/route.ts | fora-de-escopo |  | rodada só de plataforma |

## Removidas desde o ledger anterior (não enumeradas nesta rodada)

- `pol-3e2a9` policy · members · INSERT · "qualquer um entra" · estava `coberto`
