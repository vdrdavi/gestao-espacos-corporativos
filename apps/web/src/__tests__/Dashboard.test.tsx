import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Dashboard from '../pages/Dashboard'
import { stubFetchRoteado } from './helpers'
import equipes from './fixtures/equipes.json'
import runReferencia from './fixtures/run-referencia.json'
import runsDegradada from './fixtures/runs-degradada.json'
import runsOk from './fixtures/runs-ok.json'
import runsVazio from './fixtures/runs-vazio.json'
import salas from './fixtures/salas.json'
import setores from './fixtures/setores.json'

const REFERENCIA: [RegExp, unknown][] = [
  [/\/api\/salas/, salas],
  [/\/api\/equipes/, equipes],
  [/\/api\/setores/, setores],
  [/\/api\/cenarios/, []],
  [/\/api\/runs\/\d+$/, runReferencia],
]

function renderizar(runs: unknown) {
  stubFetchRoteado([...REFERENCIA, [/\/api\/runs$/, runs]])
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  )
}

describe('Dashboard', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('sem execução, mostra o painel honesto — nunca zeros nem marcador de dia', async () => {
    renderizar(runsVazio)
    await waitFor(() => expect(screen.getByText('Indicadores da alocação')).toBeInTheDocument())

    expect(screen.getAllByText(/Nenhuma alocação foi gerada ainda/).length).toBeGreaterThan(0)
    expect(screen.getAllByRole('link', { name: /gerar alocação/i }).length).toBeGreaterThan(0)
    expect(screen.queryByText(/Previsto para o D4/)).not.toBeInTheDocument()
  })

  it('com execução, mostra os indicadores e o mapa dos nove andares', async () => {
    renderizar(runsOk)
    await waitFor(() => expect(screen.getByText('86,9%')).toBeInTheDocument())

    expect(screen.getByText('563')).toBeInTheDocument() // assentos ociosos
    for (const andar of ['9º', '5º', '1º']) {
      expect(screen.getByText(andar)).toBeInTheDocument()
    }
    expect(screen.getByTitle(/Sala 501 · 5º/)).toBeInTheDocument()
    expect(screen.getAllByText(/Execução #1 ·/).length).toBeGreaterThan(0)
  })

  it('quando a execução mais recente falhou, avisa que os números são da última válida', async () => {
    renderizar(runsDegradada)
    await waitFor(() => expect(screen.getByText('86,9%')).toBeInTheDocument())
    expect(
      screen.getAllByText(/execução mais recente que falhou/i).length,
    ).toBeGreaterThan(0)
  })

  it('mantém "Situação do prédio" e "Cenários"', async () => {
    renderizar(runsOk)
    await waitFor(() => expect(screen.getByText('Situação do prédio')).toBeInTheDocument())
    expect(screen.getByText('Salas disponíveis')).toBeInTheDocument()
    expect(screen.getByText('Cenários')).toBeInTheDocument()
  })
})
