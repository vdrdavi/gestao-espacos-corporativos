// Espelho dos schemas do backend (apps/api/app/schemas.py).
// Mantido a mao de proposito: o OpenAPI foi congelado no D1, entao qualquer
// divergencia aqui e uma mudanca de contrato que merece ser vista no diff.

export type TipoSala =
  | 'reuniao'
  | 'treinamento'
  | 'auditorio'
  | 'laboratorio'
  | 'projeto'
  | 'colaborativo'

export type Turno = 'manha' | 'tarde' | 'integral'

export type StatusRun = 'OPTIMAL' | 'FEASIBLE' | 'INFEASIBLE' | 'UNKNOWN' | 'ERRO'

export type TipoIntervencao = 'aceitar' | 'rejeitar' | 'alterar' | 'reexecutar'

export interface Sala {
  id: number
  codigo: string
  andar: number
  capacidade: number
  tipo: TipoSala
  recursos: string[]
  acessivel: boolean
  disponivel: boolean
  reservada_para_setor_id: number | null
}

export interface Setor {
  id: number
  nome: string
  coordenador: string
  total_funcionarios: number
}

export interface Equipe {
  id: number
  setor_id: number
  nome: string
  tamanho: number
  turno: Turno
  recursos_requeridos: string[]
  exige_acessibilidade: boolean
  andar_preferido: number | null
  prioridade: number
}

export interface Restricao {
  id: number
  tipo: string
  alvo_tipo: string
  alvo_id: number | null
  parametros: Record<string, unknown>
  rigida: boolean
  peso: number
  descricao: string
}

export interface Run {
  id: number
  criado_em: string
  usuario: string
  engine_version: string
  seed: number | null
  pesos: Record<string, number>
  hash_entrada: string
  duracao_ms: number
  status: StatusRun
  metricas: Record<string, number>
  metricas_baseline: Record<string, number>
  erro: string | null
}

export interface Intervencao {
  id: number
  run_id: number
  criado_em: string
  usuario: string
  tipo: TipoIntervencao
  antes: Record<string, unknown>
  depois: Record<string, unknown>
  justificativa: string
  alerta: string | null
}

export interface Metricas {
  execucoes_total: number
  execucoes_com_erro: number
  duracao_ultima_ms: number | null
  duracao_p50_ms: number | null
  duracao_p95_ms: number | null
  ocupacao_media_pct: number | null
  taxa_alocacao_pct: number | null
  equipes_nao_alocadas: number | null
  violacoes: number | null
  intervencoes_total: number
  intervencoes_por_execucao: number | null
  engine_version: string
}

export interface Cenario {
  nome: string
  titulo: string
  descricao: string
}

/** Corpo do 501 devolvido por POST /api/runs enquanto o motor e stub (D1). */
export interface MotorPendente {
  mensagem: string
  etapa: string
  previsto_para: string
  pipeline_ate_aqui: {
    salas: number
    equipes: number
    restricoes: number
    capacidade_total: number
    hash_entrada: string
    engine_version: string
    pesos: Record<string, number>
  }
}
