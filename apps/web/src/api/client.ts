import type {
  Cenario,
  Equipe,
  Intervencao,
  Metricas,
  Restricao,
  Run,
  Sala,
  Setor,
} from './types'

/**
 * Erro de API com o status e o corpo preservados.
 *
 * O `detail` importa: o 501 de POST /api/runs carrega um objeto explicando
 * qual etapa do motor falta e em que dia ela entra, e a tela de alocacao
 * mostra isso em vez de um "erro inesperado".
 */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: unknown,
    mensagem: string,
  ) {
    super(mensagem)
    this.name = 'ApiError'
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const resposta = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })

  if (resposta.status === 204) return undefined as T

  const corpo = await resposta.json().catch(() => null)

  if (!resposta.ok) {
    const detail = corpo && typeof corpo === 'object' ? (corpo as { detail?: unknown }).detail : null
    throw new ApiError(
      resposta.status,
      detail,
      typeof detail === 'string' ? detail : `${resposta.status} em ${path}`,
    )
  }

  return corpo as T
}

export const api = {
  health: () => req<{ status: string; engine_version: string }>('/health'),

  salas: (params?: { andar?: number }) =>
    req<Sala[]>(`/api/salas${params?.andar ? `?andar=${params.andar}` : ''}`),
  criarSala: (dados: Omit<Sala, 'id'>) =>
    req<Sala>('/api/salas', { method: 'POST', body: JSON.stringify(dados) }),

  setores: () => req<Setor[]>('/api/setores'),

  equipes: (params?: { setor_id?: number }) =>
    req<Equipe[]>(`/api/equipes${params?.setor_id ? `?setor_id=${params.setor_id}` : ''}`),
  atualizarEquipe: (id: number, dados: Partial<Equipe>) =>
    req<Equipe>(`/api/equipes/${id}`, { method: 'PATCH', body: JSON.stringify(dados) }),

  restricoes: () => req<Restricao[]>('/api/restricoes'),

  runs: () => req<Run[]>('/api/runs'),
  gerarAlocacao: (usuario: string) =>
    req<Run>('/api/runs', { method: 'POST', body: JSON.stringify({ usuario }) }),

  metricas: () => req<Metricas>('/api/metrics'),
  auditoria: () => req<Intervencao[]>('/api/audit'),

  cenarios: () => req<Cenario[]>('/api/cenarios'),
  carregarCenario: (nome: string) =>
    req<Record<string, number | string>>(`/api/cenarios/${nome}/carregar`, { method: 'POST' }),
}
