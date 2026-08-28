import { useState } from 'react'
import { api } from '../api/client'
import { useApi } from '../api/useApi'
import { Carregando, Erro, Pill, Secao } from '../components/ui'

export default function Salas() {
  const [andar, setAndar] = useState<number | undefined>()
  const salas = useApi(() => api.salas(andar ? { andar } : undefined), [andar])

  if (salas.erro) return <Erro erro={salas.erro} />

  return (
    <Secao
      titulo="Salas"
      acao={
        <select
          value={andar ?? ''}
          onChange={(e) => setAndar(e.target.value ? Number(e.target.value) : undefined)}
          className="rounded border border-slate-300 bg-white px-2 py-1 text-sm"
        >
          <option value="">Todos os andares</option>
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((a) => (
            <option key={a} value={a}>
              {a}º andar
            </option>
          ))}
        </select>
      }
    >
      {salas.carregando ? (
        <Carregando o="as salas" />
      ) : (
        <div className="overflow-x-auto rounded border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wider text-slate-500">
                <th className="px-3 py-2">Código</th>
                <th className="px-3 py-2">Andar</th>
                <th className="px-3 py-2 text-right">Capacidade</th>
                <th className="px-3 py-2">Tipo</th>
                <th className="px-3 py-2">Recursos</th>
                <th className="px-3 py-2">Situação</th>
              </tr>
            </thead>
            <tbody>
              {(salas.dados ?? []).map((s) => (
                <tr key={s.id} className="border-b border-slate-100 last:border-0">
                  <td className="px-3 py-2 font-mono">{s.codigo}</td>
                  <td className="px-3 py-2 text-slate-600">{s.andar}º</td>
                  <td className="tabular px-3 py-2 text-right">{s.capacidade}</td>
                  <td className="px-3 py-2 text-slate-600">{s.tipo}</td>
                  <td className="px-3 py-2">
                    <span className="flex flex-wrap gap-1">
                      {s.recursos.map((r) => (
                        <Pill key={r}>{r}</Pill>
                      ))}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <span className="flex flex-wrap gap-1">
                      {s.acessivel && <Pill tom="ok">acessível</Pill>}
                      {!s.disponivel && <Pill tom="alerta">indisponível</Pill>}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Secao>
  )
}
