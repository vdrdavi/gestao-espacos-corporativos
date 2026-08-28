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

  it('devolve a execucao completa ao gerar a alocacao', async () => {
    const run = {
      id: 1,
      status: 'OPTIMAL',
      metricas: { equipes_alocadas: 84, violacoes: 0 },
      metricas_baseline: { equipes_alocadas: 79 },
      alocacoes: [{ id: 1, equipe_id: 1, sala_id: 7 }],
      nao_alocadas: [],
    }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(JSON.stringify(run), { status: 201 })),
    )

    const resposta = await api.gerarAlocacao('coordenador-geral')
    expect(resposta.status).toBe('OPTIMAL')
    expect(resposta.alocacoes).toHaveLength(1)
    expect(resposta.metricas_baseline.equipes_alocadas).toBe(79)
  })

  it('preserva o texto do 422 quando os pesos quebram a dominancia', async () => {
    // A tela precisa mostrar *por que* a execucao foi recusada: sem isso o
    // Coordenador Geral so ve um botao que nao funciona.
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'Pesos violam a regra de dominancia' }), {
          status: 422,
        }),
      ),
    )

    await expect(api.gerarAlocacao('coordenador-geral')).rejects.toSatisfy(
      (e: unknown) => e instanceof ApiError && e.status === 422 && e.message.includes('dominancia'),
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
