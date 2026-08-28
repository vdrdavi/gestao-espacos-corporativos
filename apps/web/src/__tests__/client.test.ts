import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api } from '../api/client'

describe('cliente da API', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('devolve o corpo em caso de sucesso', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify([{ id: 1, codigo: '701' }]), { status: 200 }),
      ),
    )
    await expect(api.salas()).resolves.toHaveLength(1)
  })

  it('preserva o detalhe estruturado do 501 do motor', async () => {
    // Enquanto o motor e stub (D1), a tela de alocacao depende deste corpo
    // para dizer qual etapa falta em vez de mostrar "erro inesperado".
    const detail = { etapa: 'O solver CP-SAT', previsto_para: 'D2' }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail }), { status: 501 })),
    )

    await expect(api.gerarAlocacao('coordenador-geral')).rejects.toSatisfy(
      (e: unknown) => e instanceof ApiError && e.status === 501 && (e.detail as typeof detail).previsto_para === 'D2',
    )
  })

  it('usa a mensagem do servidor quando o detalhe e texto', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'Sala 999 nao encontrada' }), { status: 404 }),
      ),
    )
    await expect(api.salas()).rejects.toThrow('Sala 999 nao encontrada')
  })

  it('trata 204 sem tentar ler JSON', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))
    await expect(api.salas()).resolves.toBeUndefined()
  })
})
