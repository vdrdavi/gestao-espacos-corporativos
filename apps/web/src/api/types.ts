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

/** Uma parcela do custo, com o numero e a frase que o explica. */
export interface Termo {
  nome: string
  valor: number
  detalhe: string
}

/** Uma sala descartada, com o motivo pelo qual nao foi ela. */
export interface Alternativa {
  sala_id: number
  codigo: string
  andar: number
  capacidade: number
  custo: number
  /** Quanto esta sala custaria a mais (ou a menos) que a recomendada. */
  delta: number
  /** `false` quando a sala estava ocupada ou bloqueada por H2/H7/proximidade. */
  disponivel: boolean
  por_que_nao: string
}

/**
 * O porque de uma recomendacao (secao 9 do enunciado).
 *
 * Gravado junto do Assignment, nao recalculado na leitura: o registro e
 * append-only e a entrada muda entre execucoes, entao recalcular mostraria a
 * razao de hoje para uma decisao tomada ontem.
 */
export interface Explicacao {
  equipe: { id: number; nome: string; tamanho: number; turno: Turno; prioridade: number }
  sala: { id: number; codigo: string; andar: number; capacidade: number }
  ocupacao_pct: number
  recursos_exigidos: string[]
  recursos_atendidos: boolean
  /** `null` quando a equipe nao exige acessibilidade. */
  acessibilidade_atendida: boolean | null
  andar_preferido: number | null
  /** `null` quando a equipe nao declarou preferencia. */
  andar_preferido_atendido: boolean | null
  andares_permitidos: number[]
  termos: Termo[]
  custo_total: number
  /** Conta a sala escolhida, por isso nunca e zero. */
  alternativas_avaliadas: number
  comparacao: { tipo: 'melhor_local' | 'trade_off_global' | 'sem_alternativa'; detalhe: string }
  resumo: string
}

export interface Assignment {
  id: number
  equipe_id: number
  sala_id: number
  turno: Turno
  custo: number
  /** Decomposicao termo a termo. Vazia so em execucoes gravadas antes do D3. */
  explicacao: Explicacao | Record<string, never>
  /** As salas descartadas, da mais barata para a mais cara. */
  alternativas: Alternativa[]
}

export type CodigoMotivo =
  | 'SEM_SALA_COMPATIVEL'
  | 'RECURSO_INDISPONIVEL'
  | 'ACESSIBILIDADE_INDISPONIVEL'
  | 'ANDAR_SEM_VAGA'
  | 'CONFLITO_RESTRICOES'
  | 'CAPACIDADE_ESGOTADA'

export interface NaoAlocada {
  id: number
  equipe_id: number
  codigo_motivo: CodigoMotivo
  causa: string
  encaminhamento: string
}

/** Corpo de POST /api/runs e de GET /api/runs/{id}. */
export interface RunDetalhe extends Run {
  snapshot_entrada: Record<string, unknown>
  alocacoes: Assignment[]
  nao_alocadas: NaoAlocada[]
}
