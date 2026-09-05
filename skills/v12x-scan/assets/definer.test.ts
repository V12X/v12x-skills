// v12x-scan · assets/definer.test.ts
// ----------------------------------------------------------------------------
// Regra: toda função `security definer` que escreve (UPDATE, ON CONFLICT … DO UPDATE,
// DELETE) amarra a linha ao chamador com um WHERE. Sem WHERE, o argumento decide a
// linha — e qualquer chamador reescreve a linha de qualquer um, porque `definer`
// ignora a RLS.
//
// Caso real: `post_assistant_message` fazia `on conflict (id) do update set body`, e um
// membro reescrevia a mensagem do colega, mantendo o autor original. Quatro auditorias
// por leitura não viram. Este teste vê, em cada push.
//
// O que ele prova e o que não prova: prova que o WHERE existe. Se o WHERE amarra pelo
// argumento (`where id = p_id`) em vez do chamador (`where author_id = auth.uid()`),
// isso ainda é leitura humana — a Fase 0 da skill lista as candidatas para abrir.
//
// Uso: copie para o diretório de testes (ex.: web/src/seguranca/), ajuste MIGRATIONS
// e EXCECOES. Roda com vitest; para node:test, troque a linha de import por
//   import { describe, it } from 'node:test'; import assert from 'node:assert/strict'
// e `expect(x).toEqual([])` por `assert.deepEqual(x, [])`.
// ----------------------------------------------------------------------------
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, it, expect } from 'vitest'

const MIGRATIONS = join(__dirname, '../../supabase/migrations') // ajuste ao seu layout

// Exceções ESCRITAS, com motivo. Uma função entra aqui só quando o conflito não pode ser
// de outra pessoa por construção — e o motivo diz por quê. Exceção sem motivo não existe.
const EXCECOES: Record<string, string> = {
  // register_device_token:
  //   'upsert pela chave (user_id, token): o conflito só pode ser da própria linha',
}

type Funcao = { nome: string; corpo: string; definer: boolean; arquivo: string }

function lerMigrations(): { arquivo: string; sql: string }[] {
  return readdirSync(MIGRATIONS)
    .filter((f) => f.endsWith('.sql'))
    .sort()
    .map((f) => ({ arquivo: f, sql: readFileSync(join(MIGRATIONS, f), 'utf8') }))
}

// Extrai cada CREATE FUNCTION com o corpo entre dollar-quotes ($$ ou $tag$) e diz se
// a declaração traz SECURITY DEFINER (antes ou depois do corpo — os dois são válidos).
function extrairFuncoes(arquivo: string, sql: string): Funcao[] {
  const out: Funcao[] = []
  const cabecalho = /create\s+(?:or\s+replace\s+)?function\s+([\w."]+)\s*\(/gi
  let m: RegExpExecArray | null
  while ((m = cabecalho.exec(sql))) {
    const inicio = m.index
    const abre = /\$(\w*)\$/g
    abre.lastIndex = inicio
    const a = abre.exec(sql)
    if (!a) continue
    const tag = a[0]
    const corpoInicio = a.index + tag.length
    const corpoFim = sql.indexOf(tag, corpoInicio)
    if (corpoFim < 0) continue
    const fimDecl = sql.indexOf(';', corpoFim + tag.length)
    const declaracao =
      sql.slice(inicio, a.index) + sql.slice(corpoFim + tag.length, fimDecl < 0 ? undefined : fimDecl)
    out.push({
      nome: m[1].replace(/^public\./, '').replace(/"/g, ''),
      corpo: sql.slice(corpoInicio, corpoFim),
      definer: /security\s+definer/i.test(declaracao),
      arquivo,
    })
    cabecalho.lastIndex = corpoFim + tag.length
  }
  return out
}

// Cada statement do corpo que escreve precisa de WHERE. Para ON CONFLICT … DO UPDATE,
// o WHERE tem que vir DEPOIS do DO UPDATE (o WHERE do SELECT-fonte não conta).
function escritasSemWhere(corpo: string): string[] {
  const ruins: string[] = []
  for (const bruto of corpo.split(';')) {
    const s = bruto.replace(/--[^\n]*/g, '').trim()
    if (!s) continue
    const conflito = /on\s+conflict[\s\S]*?do\s+update/i.exec(s)
    if (conflito) {
      const depois = s.slice(conflito.index + conflito[0].length)
      if (!/\bwhere\b/i.test(depois)) ruins.push(resumo(s))
      continue
    }
    if (/\bupdate\s+[\w."]+\s+set\b/i.test(s) && !/\bwhere\b/i.test(s)) ruins.push(resumo(s))
    if (/\bdelete\s+from\s+[\w."]+/i.test(s) && !/\bwhere\b/i.test(s)) ruins.push(resumo(s))
  }
  return ruins
}
const resumo = (s: string) => s.replace(/\s+/g, ' ').slice(0, 110)

// A ÚLTIMA definição de cada função é a que vale (CREATE OR REPLACE sobrescreve).
function funcoesVigentes(): Map<string, Funcao> {
  const vigentes = new Map<string, Funcao>()
  for (const { arquivo, sql } of lerMigrations())
    for (const f of extrairFuncoes(arquivo, sql)) vigentes.set(f.nome, f)
  return vigentes
}

describe('security definer escreve só com WHERE amarrado', () => {
  const vigentes = funcoesVigentes()

  it('encontrou funções nas migrations (senão o caminho está errado, não o banco limpo)', () => {
    expect(vigentes.size).toBeGreaterThan(0)
  })

  it('toda escrita em função security definer leva WHERE', () => {
    const violacoes: string[] = []
    for (const f of vigentes.values()) {
      if (!f.definer || f.nome in EXCECOES) continue
      for (const s of escritasSemWhere(f.corpo)) violacoes.push(`${f.arquivo} · ${f.nome}(): ${s}`)
    }
    expect(violacoes, 'escrita sem WHERE em security definer — o argumento decide a linha').toEqual([])
  })

  it('toda exceção nomeia uma função que existe e é definer (exceção órfã é furo)', () => {
    const orfas = Object.keys(EXCECOES).filter((n) => !vigentes.get(n)?.definer)
    expect(orfas, 'exceção sem função definer correspondente').toEqual([])
  })
})
