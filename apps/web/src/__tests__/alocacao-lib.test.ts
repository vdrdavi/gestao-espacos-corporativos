import { describe, expect, it } from 'vitest'
import type { Assignment } from '../api/types'
import {
  type Referencia,
  faixaOcupacao,
  montarLinhas,
  montarMapa,
  numero,
  pct,
} from '../lib/alocacao'
import equipes from './fixtures/equipes.json'
import runCompleto from './fixtures/run-completo.json'
import runReferencia from './fixtures/run-referencia.json'
import salas from './fixtures/salas.json'
import setores from './fixtures/setores.json'

const REF: Referencia = {
  salas: salas as Referencia['salas'],
  equipes: equipes as Referencia['equipes'],
  setores: setores as Referencia['setores'],
}

describe('faixaOcupacao', () => {
  it('corta em 0, 70, 90 e 100', () => {
    expect(faixaOcupacao(0)).toBe('livre')
    expect(faixaOcupacao(1)).toBe('baixa')
    expect(faixaOcupacao(69)).toBe('baixa')
    expect(faixaOcupacao(70)).toBe('boa')
    expect(faixaOcupacao(89)).toBe('boa')
    expect(faixaOcupacao(90)).toBe('alta')
    expect(faixaOcupacao(100)).toBe('alta')
    expect(faixaOcupacao(101)).toBe('excedida')
  })
})

describe('montarLinhas', () => {
  const linhas = montarLinhas(runReferencia.alocacoes as Assignment[], REF)

  it('junta nome de equipe, setor e código da sala', () => {
    const alpha = linhas.find((l) => l.equipe === 'Tecnologia Alpha')
    expect(alpha).toMatchObject({
      setor: 'Tecnologia',
      sala: '501',
      andar: 5,
      turno: 'integral',
      pessoas: 19,
      capacidade: 20,
    })
  })

  it('calcula a ocupação como pessoas / capacidade e mantém o custo verbatim', () => {
    const alpha = linhas.find((l) => l.equipe === 'Tecnologia Alpha')!
    expect(alpha.ocupacaoPct).toBe(Math.round((19 / 20) * 100)) // 95
    expect(alpha.faixa).toBe('alta')
    expect(alpha.custo).toBe(1)
  })

  it('ordena por andar e depois por código numérico da sala', () => {
    const andares = linhas.map((l) => l.andar)
    expect(andares).toEqual([...andares].sort((a, b) => a - b))
    // as duas salas 108 (1o andar) vêm antes da 304 (3o andar)
    expect(linhas[0].sala).toBe('108')
    expect(linhas[1].sala).toBe('108')
    expect(linhas[2].sala).toBe('304')
  })

  it('cai para o retrato gravado em explicacao quando o id sumiu da referência', () => {
    const vazio: Referencia = { salas: [], equipes: [], setores: [] }
    const [l] = montarLinhas([runReferencia.alocacoes[0] as Assignment], vazio)
    expect(l.equipe).toBe('Tecnologia Alpha') // veio de explicacao.equipe.nome
    expect(l.sala).toBe('501')
    expect(l.custo).toBe(1)
  })

  it('não quebra quando não há nem entidade nem explicacao', () => {
    const cru: Assignment = {
      id: 99,
      equipe_id: 9999,
      sala_id: 8888,
      turno: 'manha',
      custo: 7,
      explicacao: {},
      alternativas: [],
    }
    const vazio: Referencia = { salas: [], equipes: [], setores: [] }
    const [l] = montarLinhas([cru], vazio)
    expect(l.equipe).toBe('Equipe #9999')
    expect(l.sala).toBe('#8888')
    expect(l.ocupacaoPct).toBe(0)
    expect(l.custo).toBe(7)
  })
})

describe('montarMapa', () => {
  it('tem sempre nove andares, do 9 ao 1', () => {
    const mapa = montarMapa([], REF)
    expect(mapa.map((a) => a.andar)).toEqual([9, 8, 7, 6, 5, 4, 3, 2, 1])
  })

  it('sala sem alocação fica com os dois slots livres', () => {
    const mapa = montarMapa([], REF)
    const celula = mapa.flatMap((a) => a.salas)[0]
    expect(celula.slots[0].equipe).toBeNull()
    expect(celula.slots[1].equipe).toBeNull()
    expect(celula.integral).toBe(false)
  })

  it('turno integral preenche os dois slots com a mesma equipe', () => {
    const mapa = montarMapa([runReferencia.alocacoes[0] as Assignment], REF)
    const c = mapa.flatMap((a) => a.salas).find((s) => s.codigo === '501')!
    expect(c.integral).toBe(true)
    expect(c.slots[0].equipe).toBe('Tecnologia Alpha')
    expect(c.slots[1].equipe).toBe('Tecnologia Alpha')
    expect(c.conflito).toBe(false)
  })

  it('manhã e tarde de equipes distintas viram dois slots, sem conflito', () => {
    const mapa = montarMapa(runReferencia.alocacoes as Assignment[], REF)
    const c = mapa.flatMap((a) => a.salas).find((s) => s.codigo === '108')!
    expect(c.slots[0].equipe).toBe('Operacoes Mu')
    expect(c.slots[1].equipe).toBe('Operacoes Nu')
    expect(c.integral).toBe(false)
    expect(c.conflito).toBe(false)
  })

  it('sala usada só de manhã deixa o slot da tarde livre', () => {
    const mapa = montarMapa(runReferencia.alocacoes as Assignment[], REF)
    const c = mapa.flatMap((a) => a.salas).find((s) => s.codigo === '304')!
    expect(c.slots[0].equipe).toBe('Tecnologia Iota')
    expect(c.slots[1].equipe).toBeNull()
  })

  it('marca conflito e força excedida quando duas equipes caem no mesmo slot', () => {
    const a = runReferencia.alocacoes[2] as Assignment // Operacoes Mu, sala 108, manha
    const b = { ...(runReferencia.alocacoes[3] as Assignment), turno: 'manha' as const }
    const mapa = montarMapa([a, b], REF)
    const c = mapa.flatMap((x) => x.salas).find((s) => s.codigo === '108')!
    expect(c.conflito).toBe(true)
    expect(c.slots[0].faixa).toBe('excedida')
  })

  it('expõe disponivel e reservadaPara da sala', () => {
    const mapa = montarMapa([], REF)
    const celulas = mapa.flatMap((a) => a.salas)
    expect(celulas.some((c) => !c.disponivel)).toBe(true)
    // referência sintética: uma sala reservada
    const ref2: Referencia = {
      ...REF,
      salas: [{ ...REF.salas[0], reservada_para_setor_id: 1 }],
    }
    const [c] = montarMapa([], ref2).flatMap((a) => a.salas)
    expect(c.reservadaPara).toBe('Tecnologia')
  })

  it('a ocupação por andar bate com a conta feita à parte e re-agrega para o ocupacao_media_pct gravado', () => {
    const salaPorId = new Map(REF.salas.map((s) => [s.id, s]))
    const equipePorId = new Map(REF.equipes.map((e) => [e.id, e]))

    // conta independente: turno a turno, capacidade contada uma vez por alocação
    const porAndar = new Map<number, { pessoas: number; capacidade: number }>()
    for (const a of runCompleto.alocacoes as Assignment[]) {
      const s = salaPorId.get(a.sala_id)!
      const e = equipePorId.get(a.equipe_id)!
      const acc = porAndar.get(s.andar) ?? { pessoas: 0, capacidade: 0 }
      acc.pessoas += e.tamanho
      acc.capacidade += s.capacidade
      porAndar.set(s.andar, acc)
    }

    const mapa = montarMapa(runCompleto.alocacoes as Assignment[], REF)
    for (const andar of mapa) {
      const esperado = porAndar.get(andar.andar)
      if (!esperado) continue
      expect(andar.ocupacaoPct).toBeCloseTo(
        Math.round((esperado.pessoas / esperado.capacidade) * 1000) / 10,
        5,
      )
    }

    const totalPessoas = [...porAndar.values()].reduce((t, v) => t + v.pessoas, 0)
    const totalCap = [...porAndar.values()].reduce((t, v) => t + v.capacidade, 0)
    expect(Math.round((totalPessoas / totalCap) * 1000) / 10).toBeCloseTo(
      runCompleto.metricas.ocupacao_media_pct,
      1,
    )
  })
})

describe('formatadores', () => {
  it('numero e pct devolvem traço para nulo/NaN', () => {
    expect(numero(1234)).toBe('1.234')
    expect(numero(undefined)).toBe('—')
    expect(pct(86.9)).toBe('86,9%')
    expect(pct(null)).toBe('—')
  })
})
