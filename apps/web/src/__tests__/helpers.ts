import { vi } from 'vitest'

type Rota = [padrao: RegExp | string, corpo: unknown, status?: number]

/**
 * Stub de `fetch` que roteia por URL. As telas do D4 disparam varias chamadas
 * (salas + equipes + setores + runs + o detalhe da run), entao o
 * `mockResolvedValue` unico usado nos testes do D1-D3 nao serve: ele devolveria
 * o mesmo corpo para todas.
 *
 * A primeira rota cujo padrao casa a URL vence. Sem correspondencia => 404.
 */
export function stubFetchRoteado(rotas: Rota[]) {
  const fn = vi.fn((entrada: RequestInfo | URL) => {
    const url = typeof entrada === 'string' ? entrada : entrada.toString()
    for (const [padrao, corpo, status] of rotas) {
      const casa = typeof padrao === 'string' ? url.includes(padrao) : padrao.test(url)
      if (casa) {
        return Promise.resolve(new Response(JSON.stringify(corpo), { status: status ?? 200 }))
      }
    }
    return Promise.resolve(new Response('null', { status: 404 }))
  })
  vi.stubGlobal('fetch', fn)
  return fn
}
