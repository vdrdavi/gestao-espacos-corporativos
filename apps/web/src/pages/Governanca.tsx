import { api } from '../api/client'
import { useApi } from '../api/useApi'
import { Carregando, Erro, Secao } from '../components/ui'

export default function Governanca() {
  const runs = useApi(() => api.runs())
  const auditoria = useApi(() => api.auditoria())

  if (runs.erro) return <Erro erro={runs.erro} />
  if (runs.carregando) return <Carregando o="o histórico" />

  const lista = runs.dados ?? []

  return (
    <>
      <Secao titulo="Histórico de execuções">
        {lista.length === 0 ? (
          <div className="rounded border border-slate-200 bg-white p-6 text-sm text-slate-600">
            Nenhuma execução registrada ainda. Cada vez que o motor rodar, uma linha imutável
            aparece aqui com usuário, data, versão do mecanismo, hash da entrada e resultado — as
            cinco perguntas da governança.
          </div>
        ) : (
          <div className="overflow-x-auto rounded border border-slate-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wider text-slate-500">
                  <th className="px-3 py-2">#</th>
                  <th className="px-3 py-2">Data/hora</th>
                  <th className="px-3 py-2">Usuário</th>
                  <th className="px-3 py-2">Motor</th>
                  <th className="px-3 py-2">Entrada</th>
                  <th className="px-3 py-2 text-right">Duração</th>
                  <th className="px-3 py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {lista.map((r) => (
                  <tr key={r.id} className="border-b border-slate-100 last:border-0">
                    <td className="px-3 py-2 font-mono">{r.id}</td>
                    <td className="px-3 py-2 text-slate-600">
                      {new Date(r.criado_em).toLocaleString('pt-BR')}
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">{r.usuario}</td>
                    <td className="px-3 py-2 font-mono text-xs text-slate-500">{r.engine_version}</td>
                    <td className="px-3 py-2 font-mono text-xs text-slate-500">
                      {r.hash_entrada.slice(0, 12)}…
                    </td>
                    <td className="tabular px-3 py-2 text-right">{r.duracao_ms} ms</td>
                    <td className="px-3 py-2 font-mono text-xs">{r.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Secao>

      <Secao titulo="Trilha de auditoria">
        <div className="rounded border border-slate-200 bg-white p-6 text-sm text-slate-600">
          {(auditoria.dados ?? []).length === 0
            ? 'Nenhuma intervenção humana registrada. Aceitar, rejeitar, alterar manualmente ou reexecutar cria uma linha aqui — o registro nunca substitui a recomendação original.'
            : `${auditoria.dados?.length} intervenção(ões) registrada(s).`}
        </div>
      </Secao>
    </>
  )
}
