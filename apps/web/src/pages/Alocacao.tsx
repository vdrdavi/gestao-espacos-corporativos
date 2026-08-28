import { useState } from 'react'
import { ApiError, api } from '../api/client'
import type { MotorPendente } from '../api/types'
import { Secao } from '../components/ui'
import { usePerfil } from '../perfil'

export default function Alocacao() {
  const { perfil } = usePerfil()
  const [executando, setExecutando] = useState(false)
  const [pendente, setPendente] = useState<MotorPendente | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  async function gerar() {
    setExecutando(true)
    setPendente(null)
    setErro(null)
    try {
      await api.gerarAlocacao(perfil)
    } catch (e) {
      // O 501 do D1 nao e uma falha: e o motor dizendo qual etapa falta.
      if (e instanceof ApiError && e.status === 501) setPendente(e.detail as MotorPendente)
      else setErro(e instanceof Error ? e.message : String(e))
    } finally {
      setExecutando(false)
    }
  }

  return (
    <Secao titulo="Gerar alocação otimizada">
      <button
        onClick={gerar}
        disabled={executando}
        className="rounded bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-50"
      >
        {executando ? 'Executando...' : 'GERAR ALOCAÇÃO OTIMIZADA'}
      </button>

      {erro && (
        <div className="mt-6 rounded border border-red-200 bg-red-50 p-4 text-sm text-red-800">{erro}</div>
      )}

      {pendente && (
        <div className="mt-6 rounded border border-amber-300 bg-amber-50 p-5">
          <div className="text-xs font-medium uppercase tracking-wider text-amber-700">
            Motor previsto para o {pendente.previsto_para}
          </div>
          <p className="mt-2 max-w-prose text-sm text-amber-900">{pendente.mensagem}</p>

          <div className="mt-4 border-t border-amber-200 pt-4">
            <div className="text-xs font-medium uppercase tracking-wider text-amber-700">
              O que já funciona
            </div>
            <p className="mt-1 max-w-prose text-xs text-amber-800">
              O problema foi montado, o snapshot da entrada foi calculado e o hash de auditoria foi
              gerado. Falta apenas a decisão de alocação.
            </p>
            <dl className="mt-3 grid gap-x-6 gap-y-1 text-xs sm:grid-cols-2">
              {[
                ['Salas analisadas', pendente.pipeline_ate_aqui.salas],
                ['Equipes analisadas', pendente.pipeline_ate_aqui.equipes],
                ['Restrições', pendente.pipeline_ate_aqui.restricoes],
                ['Capacidade total', pendente.pipeline_ate_aqui.capacidade_total],
                ['Versão do motor', pendente.pipeline_ate_aqui.engine_version],
                ['Hash da entrada', `${pendente.pipeline_ate_aqui.hash_entrada.slice(0, 16)}…`],
              ].map(([rotulo, valor]) => (
                <div key={String(rotulo)} className="flex justify-between gap-4 border-b border-amber-200/60 py-1">
                  <dt className="text-amber-800">{rotulo}</dt>
                  <dd className="tabular font-mono text-amber-900">{valor}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      )}
    </Secao>
  )
}
