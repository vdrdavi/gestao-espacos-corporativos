import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useUltimaRun } from '../api/useUltimaRun'
import { stubFetchRoteado } from './helpers'
import runReferencia from './fixtures/run-referencia.json'
import runsDegradada from './fixtures/runs-degradada.json'
import runsOk from './fixtures/runs-ok.json'
import runsTodasErro from './fixtures/runs-todas-erro.json'
import runsVazio from './fixtures/runs-vazio.json'

function Sonda() {
  const { dados, carregando } = useUltimaRun()
  if (carregando || !dados) return <p>carregando</p>
  return <pre data-testid="estado">{JSON.stringify(dados)}</pre>
}

async function estado() {
  render(<Sonda />)
  await waitFor(() => expect(screen.getByTestId('estado')).toBeInTheDocument())
  return JSON.parse(screen.getByTestId('estado').textContent!)
}

const DETALHE: [RegExp, unknown] = [/\/api\/runs\/\d+$/, runReferencia]

describe('useUltimaRun', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('sem nenhuma execução, não busca o detalhe', async () => {
    const fetch = stubFetchRoteado([[/\/api\/runs/, runsVazio]])
    expect(await estado()).toEqual({ tipo: 'sem-runs' })
    expect(fetch).toHaveBeenCalledTimes(1)
  })

  it('com uma execução válida, busca o detalhe dela', async () => {
    const fetch = stubFetchRoteado([DETALHE, [/\/api\/runs$/, runsOk]])
    const e = await estado()
    expect(e.tipo).toBe('ok')
    expect(e.degradada).toBe(false)
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(fetch.mock.calls[1][0]).toMatch(/\/api\/runs\/7$/)
  })

  it('quando a mais recente falhou, cai para a última válida e marca degradada', async () => {
    stubFetchRoteado([DETALHE, [/\/api\/runs$/, runsDegradada]])
    const e = await estado()
    expect(e.tipo).toBe('ok')
    expect(e.degradada).toBe(true)
    expect(e.run.id).toBe(1) // o detalhe roteado, pedido para o id 7
  })

  it('quando todas falharam, não busca detalhe e reporta o último status', async () => {
    const fetch = stubFetchRoteado([DETALHE, [/\/api\/runs$/, runsTodasErro]])
    expect(await estado()).toEqual({ tipo: 'sem-run-valida', ultimoStatus: 'ERRO' })
    expect(fetch).toHaveBeenCalledTimes(1)
  })
})
