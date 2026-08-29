import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Comparacao from '../pages/Comparacao'
import { TabelaComparacao } from '../components/TabelaComparacao'
import { stubFetchRoteado } from './helpers'
import runReferencia from './fixtures/run-referencia.json'
import runsDegradada from './fixtures/runs-degradada.json'
import runsOk from './fixtures/runs-ok.json'
import runsVazio from './fixtures/runs-vazio.json'

function renderizar(runs: unknown) {
  stubFetchRoteado([
    [/\/api\/runs\/\d+$/, runReferencia],
    [/\/api\/runs$/, runs],
  ])
  return render(
    <MemoryRouter>
      <Comparacao />
    </MemoryRouter>,
  )
}

describe('Tela de comparação', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('sem execução, mostra painel vazio com link e nenhum número', async () => {
    renderizar(runsVazio)
    await waitFor(() =>
      expect(screen.getByText(/Nenhuma alocação foi gerada ainda/)).toBeInTheDocument(),
    )
    expect(screen.getByRole('link', { name: /gerar alocação/i })).toBeInTheDocument()
    expect(screen.queryByText('86,9%')).not.toBeInTheDocument()
  })

  it('mostra Antes, Depois e Δ para os indicadores da seção 8', async () => {
    renderizar(runsOk)
    await waitFor(() => expect(screen.getByText('86,9%')).toBeInTheDocument())

    expect(screen.getByText('72,8%')).toBeInTheDocument()
    expect(screen.getByText('+14,1%')).toBeInTheDocument()
    expect(screen.getByText('1.215')).toBeInTheDocument()
    expect(screen.getByText('-652')).toBeInTheDocument()
    for (const rotulo of ['Ocupação média', 'Assentos ociosos', 'Equipes sem sala', 'Violações']) {
      expect(screen.getByText(rotulo)).toBeInTheDocument()
    }
  })

  it('quando a execução mais recente falhou, mostra a nota de degradada', async () => {
    renderizar(runsDegradada)
    await waitFor(() => expect(screen.getByText('86,9%')).toBeInTheDocument())
    expect(screen.getByText(/execução mais recente que falhou/i)).toBeInTheDocument()
  })

  it('colore o Δ de vermelho quando o indicador piora na direção que interessa', () => {
    render(
      <TabelaComparacao
        baseline={{ assentos_ociosos: 400, custo: 100 }}
        otimizada={{ assentos_ociosos: 900, custo: 100 }}
      />,
    )
    const delta = screen.getByText('+500')
    expect(delta.className).toMatch(/text-red-700/)
  })
})
