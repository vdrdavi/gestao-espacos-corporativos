import { Link } from 'react-router-dom'
import type { EstadoUltimaRun } from '../api/useUltimaRun'
import type { RunDetalhe } from '../api/types'

/**
 * O que as telas de leitura (Dashboard, Comparacao) mostram quando ainda nao ha
 * uma execucao valida para ler. Regra 4 do CLAUDE.md: painel honesto com o
 * caminho para gerar uma, nunca zeros nem "Previsto para o D...".
 */
export function PainelSemRun({
  estado,
  assunto,
}: {
  estado: Extract<EstadoUltimaRun, { tipo: 'sem-runs' | 'sem-run-valida' }>
  assunto: string
}) {
  return (
    <div className="rounded border border-slate-200 bg-white p-6 text-sm text-slate-600">
      {estado.tipo === 'sem-runs' ? (
        <p>Nenhuma alocação foi gerada ainda. {assunto} aparece depois da primeira execução do motor.</p>
      ) : (
        <p>
          A última execução ({estado.ultimoStatus}) não produziu uma alocação válida. {assunto} usa a
          última execução aprovada pelo validador.
        </p>
      )}
      <Link
        to="/alocacao"
        className="mt-3 inline-block rounded bg-teal-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-teal-800"
      >
        Gerar alocação
      </Link>
    </div>
  )
}

function dataCurta(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('pt-BR')
}

/** Legenda "Execução #id · STATUS · data" sob os números de uma Run. */
export function LegendaRun({ run }: { run: RunDetalhe }) {
  return (
    <p className="mt-2 text-xs text-slate-400">
      Execução #{run.id} · {run.status} · {dataCurta(run.criado_em)}
    </p>
  )
}

/** Aviso de que existe execução mais recente que falhou. */
export function NotaDegradada({ run }: { run: RunDetalhe }) {
  return (
    <p className="mb-3 rounded border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900">
      Há uma execução mais recente que falhou no validador. Estes números são os da última execução
      válida (#{run.id}, {dataCurta(run.criado_em)}).
    </p>
  )
}
