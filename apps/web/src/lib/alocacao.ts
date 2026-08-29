// O JOIN do D4: transforma o que o motor gravou (Assignment[], so com ids) mais
// as entidades atuais (Sala/Equipe/Setor) nas duas estruturas que as telas
// desenham -- a tabela equipe -> sala (desafio secao 6) e o mapa de ocupacao
// dos nove andares (secao 7).
//
// Regra 5 do CLAUDE.md: nenhum numero aqui recalcula o que o solver minimizou.
// `custo` sai verbatim do Assignment. A unica conta e a ocupacao *descritiva*
// (tamanho / capacidade) e a soma por andar -- que, feita turno a turno igual a
// `Solucao.metricas` (engine/types.py), re-agrega para o `ocupacao_media_pct`
// gravado no Run.

import type { Assignment, Equipe, Explicacao, Sala, Setor, Turno } from '../api/types'

export type Faixa = 'livre' | 'baixa' | 'boa' | 'alta' | 'excedida'

/**
 * Faixa de ocupacao de uma ocupacao percentual.
 *
 * O corte em 70 e o mesmo que o painel "Por que esta sala?" ja usa como divisor
 * saudavel (Alocacao.tsx). Abaixo dele sobram assentos -- a ociosidade que a
 * funcao de custo minimiza. Acima de 100 so acontece em Run invalido (H1), e a
 * cor tem que alarmar.
 */
export function faixaOcupacao(pct: number): Faixa {
  if (pct <= 0) return 'livre'
  if (pct < 70) return 'baixa'
  if (pct < 90) return 'boa'
  if (pct <= 100) return 'alta'
  return 'excedida'
}

export interface Referencia {
  salas: Sala[]
  equipes: Equipe[]
  setores: Setor[]
}

/** `explicacao` so vem preenchida em Run do D3+. Antes disso e `{}`. */
function temExplicacao(a: Assignment): a is Assignment & { explicacao: Explicacao } {
  return 'sala' in (a.explicacao ?? {})
}

function arredondarPct(pessoas: number, capacidade: number): number {
  return capacidade > 0 ? Math.round((pessoas / capacidade) * 100) : 0
}

// ---------------------------------------------------------------------------
// (a) tabela equipe -> sala
// ---------------------------------------------------------------------------

export interface LinhaAlocacao {
  assignmentId: number
  equipe: string
  setor: string
  pessoas: number
  sala: string
  capacidade: number
  andar: number
  turno: Turno
  ocupacaoPct: number
  faixa: Faixa
  custo: number
}

/**
 * Uma linha por Assignment. Resolve nome/capacidade/andar pela entidade atual;
 * se o id nao existe mais (a entrada mudou depois da execucao, e o registro e
 * append-only), cai para o retrato gravado em `explicacao`; so entao usa um
 * placeholder `#id`.
 */
export function montarLinhas(alocacoes: Assignment[], ref: Referencia): LinhaAlocacao[] {
  const salaPorId = new Map(ref.salas.map((s) => [s.id, s]))
  const equipePorId = new Map(ref.equipes.map((e) => [e.id, e]))
  const setorPorId = new Map(ref.setores.map((s) => [s.id, s]))

  const linhas = alocacoes.map((a): LinhaAlocacao => {
    const exp = temExplicacao(a) ? a.explicacao : null
    const sala = salaPorId.get(a.sala_id)
    const equipe = equipePorId.get(a.equipe_id)

    const nomeEquipe = equipe?.nome ?? exp?.equipe.nome ?? `Equipe #${a.equipe_id}`
    const pessoas = equipe?.tamanho ?? exp?.equipe.tamanho ?? 0
    const setorId = equipe?.setor_id
    const setor = setorId != null ? (setorPorId.get(setorId)?.nome ?? '—') : '—'
    const codigoSala = sala?.codigo ?? exp?.sala.codigo ?? `#${a.sala_id}`
    const capacidade = sala?.capacidade ?? exp?.sala.capacidade ?? 0
    const andar = sala?.andar ?? exp?.sala.andar ?? 0
    const ocupacaoPct = arredondarPct(pessoas, capacidade)

    return {
      assignmentId: a.id,
      equipe: nomeEquipe,
      setor,
      pessoas,
      sala: codigoSala,
      capacidade,
      andar,
      turno: a.turno,
      ocupacaoPct,
      faixa: faixaOcupacao(ocupacaoPct),
      custo: a.custo,
    }
  })

  return linhas.sort(
    (x, y) =>
      x.andar - y.andar || x.sala.localeCompare(y.sala, 'pt-BR', { numeric: true }),
  )
}

// ---------------------------------------------------------------------------
// (b) mapa andar / sala / turno
// ---------------------------------------------------------------------------

export interface SlotMapa {
  turno: 'manha' | 'tarde'
  equipe: string | null
  pessoas: number
  ocupacaoPct: number
  faixa: Faixa
}

export interface CelulaSala {
  salaId: number
  codigo: string
  andar: number
  capacidade: number
  disponivel: boolean
  /** Nome do setor quando a sala e reservada (H6); senao `null`. */
  reservadaPara: string | null
  /** Uma equipe de turno integral ocupa os dois slots. */
  integral: boolean
  /** Sempre [manha, tarde]. */
  slots: [SlotMapa, SlotMapa]
  /** Mais de uma equipe no mesmo slot -- so aparece em Run reprovado. */
  conflito: boolean
}

export interface AndarMapa {
  andar: number
  salas: CelulaSala[]
  salasOcupadas: number
  /**
   * Σ pessoas(alocacoes do andar) / Σ capacidade(alocacoes do andar).
   * Mesma conta turno a turno de `Solucao.metricas`: a media ponderada dos
   * nove andares reproduz `run.metricas.ocupacao_media_pct`.
   */
  ocupacaoPct: number
}

export type MapaAlocacao = AndarMapa[]

const ANDARES = [9, 8, 7, 6, 5, 4, 3, 2, 1]

function slotVazio(turno: 'manha' | 'tarde'): SlotMapa {
  return { turno, equipe: null, pessoas: 0, ocupacaoPct: 0, faixa: 'livre' }
}

/**
 * O mapa parte de *todas* as salas da referencia, agrupadas por andar: mostra o
 * predio inteiro, nao so o que foi ocupado. Cada Assignment preenche o slot do
 * seu turno (integral preenche os dois). Dois times no mesmo slot marcam
 * `conflito` e forcam a faixa 'excedida' -- so ocorre em solucao invalida, onde
 * o banner do validador ja avisa.
 */
export function montarMapa(alocacoes: Assignment[], ref: Referencia): MapaAlocacao {
  const equipePorId = new Map(ref.equipes.map((e) => [e.id, e]))
  const setorPorId = new Map(ref.setores.map((s) => [s.id, s]))
  const salaPorId = new Map(ref.salas.map((s) => [s.id, s]))

  const celulaPorSala = new Map<number, CelulaSala>()
  for (const s of ref.salas) {
    celulaPorSala.set(s.id, {
      salaId: s.id,
      codigo: s.codigo,
      andar: s.andar,
      capacidade: s.capacidade,
      disponivel: s.disponivel,
      reservadaPara:
        s.reservada_para_setor_id != null
          ? (setorPorId.get(s.reservada_para_setor_id)?.nome ?? `setor #${s.reservada_para_setor_id}`)
          : null,
      integral: false,
      slots: [slotVazio('manha'), slotVazio('tarde')],
      conflito: false,
    })
  }

  for (const a of alocacoes) {
    const celula = celulaPorSala.get(a.sala_id)
    if (!celula) continue // sala saiu da entrada depois da execucao (append-only)

    const exp = temExplicacao(a) ? a.explicacao : null
    const equipe = equipePorId.get(a.equipe_id)
    const nome = equipe?.nome ?? exp?.equipe.nome ?? `Equipe #${a.equipe_id}`
    const pessoas = equipe?.tamanho ?? exp?.equipe.tamanho ?? 0
    const pct = arredondarPct(pessoas, celula.capacidade)
    const alvos: (0 | 1)[] = a.turno === 'integral' ? [0, 1] : a.turno === 'manha' ? [0] : [1]
    if (a.turno === 'integral') celula.integral = true

    for (const i of alvos) {
      const slot = celula.slots[i]
      if (slot.equipe !== null) {
        celula.conflito = true
        slot.faixa = 'excedida'
        continue
      }
      celula.slots[i] = {
        turno: slot.turno,
        equipe: nome,
        pessoas,
        ocupacaoPct: pct,
        faixa: faixaOcupacao(pct),
      }
    }
  }

  const alocacaoPorSala = new Map<number, Assignment[]>()
  for (const a of alocacoes) {
    if (!salaPorId.has(a.sala_id)) continue
    const lista = alocacaoPorSala.get(a.sala_id) ?? []
    lista.push(a)
    alocacaoPorSala.set(a.sala_id, lista)
  }

  return ANDARES.map((andar) => {
    const salas = ref.salas
      .filter((s) => s.andar === andar)
      .map((s) => celulaPorSala.get(s.id)!)
      .sort((x, y) => x.codigo.localeCompare(y.codigo, 'pt-BR', { numeric: true }))

    let pessoas = 0
    let capacidade = 0
    const ocupadas = new Set<number>()
    for (const s of salas) {
      for (const a of alocacaoPorSala.get(s.salaId) ?? []) {
        const eq = equipePorId.get(a.equipe_id)
        const exp = temExplicacao(a) ? a.explicacao : null
        pessoas += eq?.tamanho ?? exp?.equipe.tamanho ?? 0
        capacidade += s.capacidade
        ocupadas.add(s.salaId)
      }
    }

    return {
      andar,
      salas,
      salasOcupadas: ocupadas.size,
      ocupacaoPct: capacidade > 0 ? Math.round((pessoas / capacidade) * 1000) / 10 : 0,
    }
  })
}

// ---------------------------------------------------------------------------
// formatadores (para as telas nao reimportarem de Alocacao.tsx)
// ---------------------------------------------------------------------------

export function numero(v: number | null | undefined): string {
  return v == null || Number.isNaN(v) ? '—' : v.toLocaleString('pt-BR')
}

export function pct(v: number | null | undefined): string {
  return v == null || Number.isNaN(v) ? '—' : `${v.toLocaleString('pt-BR')}%`
}
