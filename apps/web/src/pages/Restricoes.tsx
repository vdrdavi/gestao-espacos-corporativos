import { api } from '../api/client'
import { useApi } from '../api/useApi'
import { Carregando, Erro, Pill, Secao } from '../components/ui'

export default function Restricoes() {
  const restricoes = useApi(() => api.restricoes())

  if (restricoes.erro) return <Erro erro={restricoes.erro} />
  if (restricoes.carregando) return <Carregando o="as restrições" />

  const lista = restricoes.dados ?? []
  const rigidas = lista.filter((r) => r.rigida)

  return (
    <Secao titulo={`Restrições (${rigidas.length} rígidas, ${lista.length - rigidas.length} flexíveis)`}>
      <div className="mb-4 rounded border border-slate-200 bg-white p-4 text-sm text-slate-600">
        <strong className="font-medium text-slate-900">Rígida</strong> vira restrição do modelo
        CP-SAT e nunca pode ser violada. <strong className="font-medium text-slate-900">Flexível</strong>{' '}
        vira termo ponderado da função de custo: o motor pode violá-la se o ganho compensar o peso.
      </div>

      <div className="overflow-x-auto rounded border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wider text-slate-500">
              <th className="px-3 py-2">Tipo</th>
              <th className="px-3 py-2">Natureza</th>
              <th className="px-3 py-2 text-right">Peso</th>
              <th className="px-3 py-2">Descrição</th>
            </tr>
          </thead>
          <tbody>
            {lista.map((r) => (
              <tr key={r.id} className="border-b border-slate-100 last:border-0">
                <td className="px-3 py-2 font-mono text-xs">{r.tipo}</td>
                <td className="px-3 py-2">
                  {r.rigida ? <Pill tom="alerta">rígida</Pill> : <Pill tom="ok">flexível</Pill>}
                </td>
                <td className="tabular px-3 py-2 text-right text-slate-600">{r.peso || '—'}</td>
                <td className="px-3 py-2 text-slate-700">{r.descricao}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Secao>
  )
}
