import { useState } from 'react'
import { api } from '../api/client'
import { useApi } from '../api/useApi'
import { Carregando, Erro, Pill, Secao } from '../components/ui'

export default function Equipes() {
  const equipes = useApi(() => api.equipes())
  const setores = useApi(() => api.setores())
  const [salvando, setSalvando] = useState<number | null>(null)

  if (equipes.erro) return <Erro erro={equipes.erro} />
  if (equipes.carregando) return <Carregando o="as equipes" />

  const nomeSetor = new Map((setores.dados ?? []).map((s) => [s.id, s.nome]))

  /**
   * Etapa 3 do roteiro da demo: o Coordenador de Setor altera a quantidade de
   * funcionarios de uma equipe e o sistema passa a considerar o novo numero na
   * proxima otimizacao.
   */
  async function alterarTamanho(id: number, tamanho: number) {
    if (!Number.isFinite(tamanho) || tamanho < 1) return
    setSalvando(id)
    try {
      await api.atualizarEquipe(id, { tamanho })
      equipes.recarregar()
    } finally {
      setSalvando(null)
    }
  }

  return (
    <Secao titulo={`Equipes (${(equipes.dados ?? []).length})`}>
      <div className="overflow-x-auto rounded border border-slate-200 bg-white">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wider text-slate-500">
              <th className="px-3 py-2">Equipe</th>
              <th className="px-3 py-2">Setor</th>
              <th className="px-3 py-2 text-right">Pessoas</th>
              <th className="px-3 py-2">Turno</th>
              <th className="px-3 py-2 text-right">Prioridade</th>
              <th className="px-3 py-2">Requisitos</th>
            </tr>
          </thead>
          <tbody>
            {(equipes.dados ?? []).map((e) => (
              <tr key={e.id} className="border-b border-slate-100 last:border-0">
                <td className="px-3 py-2 font-medium text-slate-900">{e.nome}</td>
                <td className="px-3 py-2 text-slate-600">{nomeSetor.get(e.setor_id) ?? '—'}</td>
                <td className="px-3 py-2 text-right">
                  <input
                    type="number"
                    min={1}
                    defaultValue={e.tamanho}
                    disabled={salvando === e.id}
                    onBlur={(ev) => {
                      const novo = Number(ev.target.value)
                      if (novo !== e.tamanho) alterarTamanho(e.id, novo)
                    }}
                    className="tabular w-20 rounded border border-slate-200 px-2 py-1 text-right focus:border-teal-500 focus:outline-none"
                  />
                </td>
                <td className="px-3 py-2 text-slate-600">{e.turno}</td>
                <td className="tabular px-3 py-2 text-right text-slate-600">{e.prioridade}</td>
                <td className="px-3 py-2">
                  <span className="flex flex-wrap gap-1">
                    {e.recursos_requeridos.map((r) => (
                      <Pill key={r}>{r}</Pill>
                    ))}
                    {e.exige_acessibilidade && <Pill tom="alerta">acessibilidade</Pill>}
                    {e.andar_preferido && <Pill>prefere {e.andar_preferido}º</Pill>}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-slate-500">
        Alterar o número de pessoas salva na hora. A próxima otimização já considera o novo valor.
      </p>
    </Secao>
  )
}
