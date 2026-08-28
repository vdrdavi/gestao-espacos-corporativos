import type { ReactNode } from 'react'

export function Card({
  titulo,
  valor,
  detalhe,
  destaque = false,
}: {
  titulo: string
  valor: ReactNode
  detalhe?: string
  destaque?: boolean
}) {
  return (
    <div
      className={`rounded border p-4 ${
        destaque ? 'border-teal-300 bg-teal-50' : 'border-slate-200 bg-white'
      }`}
    >
      <div className="text-xs font-medium uppercase tracking-wider text-slate-500">{titulo}</div>
      <div className="tabular mt-1 text-2xl font-semibold text-slate-900">{valor}</div>
      {detalhe && <div className="mt-1 text-xs text-slate-500">{detalhe}</div>}
    </div>
  )
}

export function Secao({ titulo, acao, children }: { titulo: string; acao?: ReactNode; children: ReactNode }) {
  return (
    <section className="mb-8">
      <div className="mb-3 flex items-baseline justify-between gap-4">
        <h2 className="text-lg font-semibold text-slate-900">{titulo}</h2>
        {acao}
      </div>
      {children}
    </section>
  )
}

export function Carregando({ o = 'dados' }: { o?: string }) {
  return <p className="text-sm text-slate-500">Carregando {o}...</p>
}

export function Erro({ erro }: { erro: Error }) {
  return (
    <div className="rounded border border-red-200 bg-red-50 p-4 text-sm text-red-800">
      <strong className="font-semibold">Não foi possível carregar.</strong> {erro.message}
      <p className="mt-2 text-xs text-red-700">
        A API está no ar? <code className="font-mono">make api</code> na raiz do projeto.
      </p>
    </div>
  )
}

/**
 * Marcador de tela ainda nao construida.
 *
 * Deliberado: e melhor a tela dizer em que dia ela fica pronta do que exibir
 * numeros falsos que ninguem sabe se sao reais. O mesmo criterio do 501 em
 * POST /api/runs.
 */
export function Pendente({ dia, o }: { dia: string; o: string }) {
  return (
    <div className="rounded border border-dashed border-amber-300 bg-amber-50 p-6">
      <div className="text-xs font-medium uppercase tracking-wider text-amber-700">
        Previsto para o {dia}
      </div>
      <p className="mt-2 max-w-prose text-sm text-amber-900">{o}</p>
    </div>
  )
}

export function Pill({ children, tom = 'neutro' }: { children: ReactNode; tom?: 'neutro' | 'ok' | 'alerta' }) {
  const cores = {
    neutro: 'border-slate-300 text-slate-600',
    ok: 'border-teal-400 text-teal-700',
    alerta: 'border-amber-400 text-amber-700',
  }[tom]
  return (
    <span className={`inline-block rounded border px-1.5 py-0.5 font-mono text-[11px] ${cores}`}>
      {children}
    </span>
  )
}
