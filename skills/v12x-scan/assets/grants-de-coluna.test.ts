// v12x-scan · assets/grants-de-coluna.test.ts
// ----------------------------------------------------------------------------
// Regra: tabela declarada "grant por coluna" NÃO tem GRANT SELECT de tabela para o
// papel, e toda coluna dela tem GRANT SELECT (coluna) explícito OU um motivo de ser
// privada. `GRANT SELECT ON tabela` dá SELECT em todas as colunas, inclusive as que
// ainda não existem — a coluna sensível criada numa migration depois nasce dentro do
// grant e fica legível por todo membro, sem que ninguém tenha decidido isso.
//
// Caso real: `workspaces.operator_note` (a lembrança do operador sobre a empresa),
// legível por qualquer membro dela. Terceira tabela com a mesma lição (0033, 0045,
// 0072). Erro que se repete três vezes é ausência de regra — esta é a regra.
//
// Como declarar uma coluna privada, no mesmo lugar em que ela nasce:
//   alter table workspaces add column operator_note text; -- privada: só o operador lê
// ou
//   comment on column workspaces.operator_note is 'privada: só o operador lê';
//
// O que este teste NÃO vê: ALTER DEFAULT PRIVILEGES e grants dados à mão no painel.
// Ele lê a intenção (migrations); a Fase 0 da skill lê a realidade (catálogo vivo).
// São os dois, sempre.
//
// Uso: copie para o diretório de testes, ajuste MIGRATIONS, TABELAS_POR_COLUNA e PAPEL.
// Roda com vitest (para node:test, ver o cabeçalho de definer.test.ts).
// ----------------------------------------------------------------------------
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, it, expect } from 'vitest'

const MIGRATIONS = join(__dirname, '../../supabase/migrations') // ajuste ao seu layout
const TABELAS_POR_COLUNA = ['workspaces'] // tabelas que misturam coluna de todos com coluna de poucos
const PAPEL = 'authenticated'

const PALAVRAS_DE_CONSTRAINT = /^(constraint|primary|unique|foreign|check|exclude|like)\b/i
const limpa = (t: string) => t.replace(/^public\./i, '').replace(/"/g, '').toLowerCase()

function sqlCompleto(): string {
  return readdirSync(MIGRATIONS)
    .filter((f) => f.endsWith('.sql'))
    .sort()
    .map((f) => readFileSync(join(MIGRATIONS, f), 'utf8'))
    .join('\n')
}

// Divide o miolo de CREATE TABLE por vírgulas de nível zero (numeric(10,2) não separa).
function definicoesDeColuna(miolo: string): string[] {
  const partes: string[] = []
  let nivel = 0, atual = ''
  for (const ch of miolo) {
    if (ch === '(') nivel++
    if (ch === ')') nivel--
    if (ch === ',' && nivel === 0) { partes.push(atual); atual = '' } else atual += ch
  }
  partes.push(atual)
  return partes.map((p) => p.trim()).filter(Boolean)
}

type Estado = { colunas: Set<string>; privadas: Map<string, string>; grantColuna: Set<string>; grantTabela: boolean }

function estadoDaTabela(tabela: string, sql: string): Estado {
  const e: Estado = { colunas: new Set(), privadas: new Map(), grantColuna: new Set(), grantTabela: false }
  const T = tabela.toLowerCase()
  const marcaPrivada = (linha: string, coluna: string) => {
    const m = /--\s*privad[ao]\s*:\s*(.+)$/i.exec(linha)
    if (m) e.privadas.set(coluna, m[1].trim())
  }

  // Comentário que segue o `;` na MESMA linha pertence ao statement anterior
  // (`add column x text; -- privada: motivo`): move-o para antes do `;` antes de dividir.
  const normalizado = sql.replace(/;([ \t]*--[^\n]*)/g, '$1;')
  // Processa statement a statement, na ordem: grant e revoke se cancelam pela sequência.
  for (const bruto of normalizado.split(';')) {
    const st = bruto.trim()
    if (!st) continue
    const semComentario = st.replace(/--[^\n]*/g, '')

    // create table T ( ... )
    const ct = new RegExp(`create\\s+table\\s+(?:if\\s+not\\s+exists\\s+)?(?:public\\.)?"?${T}"?\\s*\\(([\\s\\S]*)\\)\\s*(?:with|tablespace|inherits|partition|$)`, 'i').exec(semComentario)
    if (ct) {
      for (const def of definicoesDeColuna(ct[1])) {
        if (PALAVRAS_DE_CONSTRAINT.test(def)) continue
        const coluna = limpa(def.split(/\s+/)[0])
        e.colunas.add(coluna)
        const linhaOriginal = st.split('\n').find((l) => new RegExp(`^\\s*"?${coluna}"?\\b`, 'i').test(l)) ?? ''
        marcaPrivada(linhaOriginal, coluna)
      }
    }

    // alter table T add column C ...  -- privada: motivo
    const add = new RegExp(`alter\\s+table\\s+(?:if\\s+exists\\s+)?(?:only\\s+)?(?:public\\.)?"?${T}"?\\s+add\\s+(?:column\\s+)?(?:if\\s+not\\s+exists\\s+)?"?(\\w+)"?`, 'i').exec(semComentario)
    if (add) { const c = add[1].toLowerCase(); e.colunas.add(c); marcaPrivada(st, c) }

    const drop = new RegExp(`alter\\s+table\\s+(?:if\\s+exists\\s+)?(?:only\\s+)?(?:public\\.)?"?${T}"?\\s+drop\\s+(?:column\\s+)?(?:if\\s+exists\\s+)?"?(\\w+)"?`, 'i').exec(semComentario)
    if (drop) { const c = drop[1].toLowerCase(); e.colunas.delete(c); e.privadas.delete(c); e.grantColuna.delete(c) }

    // comment on column T.C is 'privada: motivo'
    const com = new RegExp(`comment\\s+on\\s+column\\s+(?:public\\.)?"?${T}"?\\."?(\\w+)"?\\s+is\\s+'privad[ao]\\s*:\\s*([^']*)'`, 'i').exec(semComentario)
    if (com) e.privadas.set(com[1].toLowerCase(), com[2].trim())

    // grants — o papel tem que aparecer na lista do TO
    const paraPapel = new RegExp(`\\bto\\s+[^;]*\\b${PAPEL}\\b`, 'i').test(semComentario)
    const dePapel = new RegExp(`\\bfrom\\s+[^;]*\\b${PAPEL}\\b`, 'i').test(semComentario)
    const sobreTabela = new RegExp(`\\bon\\s+(?:table\\s+)?(?:public\\.)?"?${T}"?\\b`, 'i').test(semComentario)
    const sobreTodas = /\bon\s+all\s+tables\s+in\s+schema\s+public\b/i.test(semComentario)

    if (/^grant\b/i.test(semComentario) && paraPapel && (sobreTabela || sobreTodas)) {
      const porColuna = /grant\s+(?:select|all)\s*\(([^)]*)\)/i.exec(semComentario)
      if (porColuna && sobreTabela) porColuna[1].split(',').forEach((c) => e.grantColuna.add(limpa(c.trim())))
      else if (/grant\s+(?:select|all)\b/i.test(semComentario)) e.grantTabela = true
    }
    if (/^revoke\b/i.test(semComentario) && dePapel && (sobreTabela || sobreTodas)) {
      const porColuna = /revoke\s+(?:select|all)\s*\(([^)]*)\)/i.exec(semComentario)
      if (porColuna && sobreTabela) porColuna[1].split(',').forEach((c) => e.grantColuna.delete(limpa(c.trim())))
      else if (/revoke\s+(?:select|all)\b/i.test(semComentario)) e.grantTabela = false
    }
  }
  return e
}

describe.each(TABELAS_POR_COLUNA)('grant por coluna em %s', (tabela) => {
  const e = estadoDaTabela(tabela, sqlCompleto())

  it('a tabela existe nas migrations (senão o nome está errado, não o grant certo)', () => {
    expect(e.colunas.size, `nenhuma coluna encontrada para ${tabela}`).toBeGreaterThan(0)
  })

  it(`não há GRANT SELECT de TABELA para ${PAPEL} (ele daria as colunas que ainda não existem)`, () => {
    expect(e.grantTabela).toBe(false)
  })

  it('toda coluna tem grant explícito ou motivo declarado de ser privada', () => {
    const semDecisao = [...e.colunas].filter((c) => !e.grantColuna.has(c) && !e.privadas.has(c))
    expect(
      semDecisao,
      `coluna sem decisão em ${tabela} — dê GRANT SELECT (${semDecisao.join(', ')}) ou marque "-- privada: motivo"`,
    ).toEqual([])
  })

  it('nenhum grant aponta para coluna que não existe (grant órfão é erro de digitação)', () => {
    const orfaos = [...e.grantColuna].filter((c) => !e.colunas.has(c))
    expect(orfaos).toEqual([])
  })
})
