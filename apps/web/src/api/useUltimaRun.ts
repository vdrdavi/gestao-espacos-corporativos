import { api } from './client'
import type { RunDetalhe, StatusRun } from './types'
import { useApi } from './useApi'

/**
 * Nao existe endpoint de "alocacao vigente": o Dashboard e a Comparacao
 * mostram a ultima execucao *valida*. Se a mais recente falhou, cai para a
 * ultima OPTIMAL/FEASIBLE e sinaliza `degradada` -- inventar numeros de uma
 * execucao reprovada seria pior que um aviso.
 */
export type EstadoUltimaRun =
  | { tipo: 'sem-runs' }
  | { tipo: 'sem-run-valida'; ultimoStatus: StatusRun }
  | { tipo: 'ok'; run: RunDetalhe; degradada: boolean }

async function carregarUltimaRun(): Promise<EstadoUltimaRun> {
  const runs = await api.runs() // criado_em desc
  if (runs.length === 0) return { tipo: 'sem-runs' }

  const valida = runs.find((r) => r.status === 'OPTIMAL' || r.status === 'FEASIBLE')
  if (!valida) return { tipo: 'sem-run-valida', ultimoStatus: runs[0].status }

  const run = await api.run(valida.id)
  return { tipo: 'ok', run, degradada: runs[0].id !== valida.id }
}

export function useUltimaRun() {
  return useApi(carregarUltimaRun, [])
}
