import { useCallback, useEffect, useState } from 'react'
import { ApiError } from './client'

interface Estado<T> {
  dados: T | null
  carregando: boolean
  erro: ApiError | Error | null
  recarregar: () => void
}

/**
 * Busca simples com estado de carregamento e erro.
 *
 * Nao e um cliente de cache -- e o minimo para que cada tela do D1 consuma um
 * endpoint real em vez de dado falso. Se o projeto crescer, trocar por
 * TanStack Query e uma substituicao local.
 */
export function useApi<T>(buscar: () => Promise<T>, deps: unknown[] = []): Estado<T> {
  const [dados, setDados] = useState<T | null>(null)
  const [carregando, setCarregando] = useState(true)
  const [erro, setErro] = useState<ApiError | Error | null>(null)
  const [gatilho, setGatilho] = useState(0)

  const recarregar = useCallback(() => setGatilho((n) => n + 1), [])

  useEffect(() => {
    let ativo = true
    setCarregando(true)
    setErro(null)

    buscar()
      .then((resultado) => ativo && setDados(resultado))
      .catch((e) => ativo && setErro(e instanceof Error ? e : new Error(String(e))))
      .finally(() => ativo && setCarregando(false))

    return () => {
      ativo = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gatilho, ...deps])

  return { dados, carregando, erro, recarregar }
}
