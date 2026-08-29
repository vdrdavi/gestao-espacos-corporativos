import { api } from './client'
import type { Referencia } from '../lib/alocacao'
import { useApi } from './useApi'

/**
 * Salas + equipes + setores num pacote so.
 *
 * A tabela e o mapa do D4 precisam dos tres para traduzir os ids de um
 * Assignment em nome, capacidade e andar. Uma busca por pagina; enquanto
 * qualquer uma nao voltou, `dados` e `null` e o componente mostra "Carregando".
 */
export function useReferencia(): {
  dados: Referencia | null
  carregando: boolean
  erro: Error | null
  recarregar: () => void
} {
  const salas = useApi(() => api.salas())
  const equipes = useApi(() => api.equipes())
  const setores = useApi(() => api.setores())

  const carregando = salas.carregando || equipes.carregando || setores.carregando
  const erro = salas.erro ?? equipes.erro ?? setores.erro
  const dados =
    salas.dados && equipes.dados && setores.dados
      ? { salas: salas.dados, equipes: equipes.dados, setores: setores.dados }
      : null

  const recarregar = () => {
    salas.recarregar()
    equipes.recarregar()
    setores.recarregar()
  }

  return { dados, carregando, erro, recarregar }
}
