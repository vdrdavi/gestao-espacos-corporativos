import { useMemo } from 'react'
import type { Assignment } from '../api/types'
import { type Faixa, type Referencia, montarLinhas, numero } from '../lib/alocacao'
import { Carregando } from './ui'

/**
 * Tabela equipe -> sala (desafio secao 6): equipe, setor, pessoas, sala
 * sugerida, capacidade, andar, turno, ocupacao e custo.
 *
 * `custo` sai verbatim do Assignment -- e o custo marginal que o solver
 * minimizou (docs/objetivo.md). A linha de total soma pessoas e capacidade,
 * mas nao o custo: `metricas.custo` inclui termos de par (proximidade,
 * separacao) que nao vivem em nenhuma linha, entao somar as linhas enganaria.
 */

const COR_OCUPACAO: Record<Faixa, string> = {
  livre: 'text-slate-400',
  baixa: 'text-amber-700',
  boa: 'text-teal-700',
  alta: 'text-teal-700',
  excedida: 'text-red-700',
}

export function TabelaAlocacao({
  alocacoes,
  referencia,
}: {
  alocacoes: Assignment[]
  referencia: Referencia | null
}) {
  const linhas = useMemo(
    () => (referencia ? montarLinhas(alocacoes, referencia) : []),
    [alocacoes, referencia],
  )

  if (!referencia) return <Carregando o="a tabela de alocação" />

  if (linhas.length === 0) {
    return (
      <p className="rounded border border-slate-200 bg-white p-4 text-sm text-slate-500">
        Nenhuma equipe foi alocada nesta execução.
      </p>
    )
  }

  const totalPessoas = linhas.reduce((t, l) => t + l.pessoas, 0)
  const totalCapacidade = linhas.reduce((t, l) => t + l.capacidade, 0)

  return (
    <div className="overflow-x-auto rounded border border-slate-200 bg-white">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wider text-slate-500">
            <th className="px-3 py-2">Equipe</th>
            <th className="px-3 py-2">Setor</th>
            <th className="px-3 py-2 text-right">Pessoas</th>
            <th className="px-3 py-2">Sala</th>
            <th className="px-3 py-2 text-right">Capacidade</th>
            <th className="px-3 py-2">Andar</th>
            <th className="px-3 py-2">Turno</th>
            <th className="px-3 py-2 text-right">Ocupação</th>
            <th className="px-3 py-2 text-right">Custo</th>
          </tr>
        </thead>
        <tbody>
          {linhas.map((l) => (
            <tr key={l.assignmentId} className="border-b border-slate-100 last:border-0">
              <td className="px-3 py-2 font-medium text-slate-900">{l.equipe}</td>
              <td className="px-3 py-2 text-slate-600">{l.setor}</td>
              <td className="tabular px-3 py-2 text-right">{numero(l.pessoas)}</td>
              <td className="px-3 py-2 font-mono">{l.sala}</td>
              <td className="tabular px-3 py-2 text-right">{numero(l.capacidade)}</td>
              <td className="px-3 py-2 text-slate-600">{l.andar}º</td>
              <td className="px-3 py-2 text-slate-600">{l.turno}</td>
              <td className={`tabular px-3 py-2 text-right font-medium ${COR_OCUPACAO[l.faixa]}`}>
                {l.ocupacaoPct}%
              </td>
              <td className="tabular px-3 py-2 text-right text-slate-900">{numero(l.custo)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-slate-300 text-xs text-slate-600">
            <th scope="row" className="px-3 py-2 text-left font-semibold">
              {linhas.length} equipe(s)
            </th>
            <td className="px-3 py-2" />
            <td className="tabular px-3 py-2 text-right font-semibold">{numero(totalPessoas)}</td>
            <td className="px-3 py-2" />
            <td className="tabular px-3 py-2 text-right font-semibold">{numero(totalCapacidade)}</td>
            <td colSpan={4} className="px-3 py-2 text-slate-400">
              custo = custo marginal da recomendação (docs/objetivo.md)
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  )
}
