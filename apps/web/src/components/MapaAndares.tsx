import { useMemo } from 'react'
import type { Assignment } from '../api/types'
import {
  type CelulaSala,
  type Faixa,
  type Referencia,
  type SlotMapa,
  montarMapa,
} from '../lib/alocacao'
import { Carregando } from './ui'

/**
 * Mapa de ocupacao dos nove andares (desafio secao 7).
 *
 * Cada sala e um bloco. Uma sala servida em turnos diferentes por equipes
 * diferentes aparece dividida -- metade manha, metade tarde -- porque colorir o
 * bloco inteiro pelo turno mais cheio faria o predio parecer mais lotado do que
 * esta (docs/arquitetura.md). O detalhe por turno vai no `title`.
 */

const COR_FAIXA: Record<Faixa, string> = {
  livre: 'bg-slate-100 text-slate-400',
  baixa: 'bg-amber-200 text-amber-900',
  boa: 'bg-teal-300 text-teal-900',
  alta: 'bg-teal-600 text-white',
  excedida: 'bg-red-500 text-white',
}

const LISTRAS_INDISPONIVEL =
  'repeating-linear-gradient(45deg, #e2e8f0 0 4px, #f8fafc 4px 8px)'

function descreveSlot(s: SlotMapa): string {
  if (!s.equipe) return `${s.turno === 'manha' ? 'manhã' : 'tarde'}: livre`
  return `${s.turno === 'manha' ? 'manhã' : 'tarde'}: ${s.equipe} (${s.pessoas} · ${s.ocupacaoPct}%)`
}

function tituloCelula(c: CelulaSala): string {
  const cabeca = `Sala ${c.codigo} · ${c.andar}º · ${c.capacidade} lugares`
  if (!c.disponivel) return `${cabeca} — indisponível`
  const reserva = c.reservadaPara ? ` — reservada para ${c.reservadaPara}` : ''
  if (c.integral) {
    const s = c.slots[0]
    const corpo = s.equipe ? `integral: ${s.equipe} (${s.pessoas} · ${s.ocupacaoPct}%)` : 'livre'
    return `${cabeca}${reserva} — ${corpo}`
  }
  return `${cabeca}${reserva} — ${descreveSlot(c.slots[0])} · ${descreveSlot(c.slots[1])}`
}

function Celula({ c }: { c: CelulaSala }) {
  const base = 'relative flex h-7 w-11 overflow-hidden rounded-sm text-[9px] font-medium'
  const aro = c.reservadaPara ? ' ring-1 ring-inset ring-amber-400' : ''

  if (!c.disponivel) {
    return (
      <span
        className={`${base} border border-slate-200`}
        style={{ backgroundImage: LISTRAS_INDISPONIVEL }}
        title={tituloCelula(c)}
      />
    )
  }

  const conteudo = c.integral ? (
    <span
      className={`flex flex-1 items-center justify-center ${COR_FAIXA[c.slots[0].faixa]}`}
      data-turno="integral"
    >
      {c.slots[0].equipe ? 'I' : ''}
    </span>
  ) : (
    c.slots.map((s) => (
      <span
        key={s.turno}
        data-turno={s.turno}
        className={`flex flex-1 items-center justify-center ${
          s.equipe ? COR_FAIXA[s.faixa] : 'bg-slate-100 text-slate-300'
        } ${s.turno === 'manha' ? 'border-r border-white/70' : ''}`}
      >
        {s.equipe ? (s.turno === 'manha' ? 'M' : 'T') : ''}
      </span>
    ))
  )

  return (
    <span className={`${base} border border-slate-200${aro}`} title={tituloCelula(c)}>
      {conteudo}
      {c.conflito && (
        <span className="absolute inset-0 flex items-center justify-center bg-red-500/80 text-white">
          !
        </span>
      )}
    </span>
  )
}

const AMOSTRAS: { faixa: Faixa; rotulo: string }[] = [
  { faixa: 'livre', rotulo: 'livre' },
  { faixa: 'baixa', rotulo: 'baixa <70%' },
  { faixa: 'boa', rotulo: 'boa 70–89%' },
  { faixa: 'alta', rotulo: 'alta 90–100%' },
  { faixa: 'excedida', rotulo: 'excedida >100%' },
]

export function MapaAndares({
  alocacoes,
  referencia,
  titulo,
}: {
  alocacoes: Assignment[]
  referencia: Referencia | null
  titulo?: string
}) {
  const mapa = useMemo(
    () => (referencia ? montarMapa(alocacoes, referencia) : []),
    [alocacoes, referencia],
  )

  if (!referencia) return <Carregando o="o mapa" />

  return (
    <div className="rounded border border-slate-200 bg-white p-4">
      {titulo && <h3 className="mb-3 text-sm font-semibold text-slate-900">{titulo}</h3>}
      <div className="flex flex-col gap-1.5">
        {mapa.map((andar) => (
          <div key={andar.andar} className="flex items-center gap-3 text-xs">
            <span className="w-8 shrink-0 text-right font-mono text-slate-500">{andar.andar}º</span>
            <div className="flex flex-1 flex-wrap gap-1">
              {andar.salas.map((c) => (
                <Celula key={c.salaId} c={c} />
              ))}
            </div>
            <span className="tabular w-28 shrink-0 text-right text-slate-500">
              {andar.salasOcupadas} salas · {andar.ocupacaoPct}%
            </span>
          </div>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1.5 border-t border-slate-100 pt-3 text-[11px] text-slate-500">
        {AMOSTRAS.map((a) => (
          <span key={a.faixa} className="flex items-center gap-1">
            <span className={`inline-block h-3 w-3 rounded-sm ${COR_FAIXA[a.faixa]}`} />
            {a.rotulo}
          </span>
        ))}
        <span className="basis-full text-slate-400">
          célula dividida = manhã | tarde · listras = indisponível · aro âmbar = reservada
        </span>
      </div>
    </div>
  )
}
