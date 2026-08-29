import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Alocacao from '../pages/Alocacao'
import { PerfilProvider } from '../perfil'
import { stubFetchRoteado } from './helpers'
import equipes from './fixtures/equipes.json'
import salas from './fixtures/salas.json'
import setores from './fixtures/setores.json'

const RUN = {
  id: 7,
  status: 'OPTIMAL',
  duracao_ms: 610,
  erro: null,
  metricas: {
    equipes_total: 87,
    equipes_alocadas: 84,
    ocupacao_media_pct: 86.9,
    assentos_ociosos: 563,
    violacoes: 0,
    custo: 70763,
  },
  metricas_baseline: { equipes_alocadas: 79, ocupacao_media_pct: 72.8, assentos_ociosos: 1215 },
  alocacoes: [
    {
      id: 1,
      equipe_id: 1,
      sala_id: 49,
      turno: 'integral',
      custo: 1,
      // O payload real do explainer, encurtado. Copiado de uma execução de
      // verdade: um mock inventado esconderia uma mudança de contrato.
      explicacao: {
        equipe: { id: 1, nome: 'Tecnologia Alpha', tamanho: 19, turno: 'integral', prioridade: 2 },
        sala: { id: 49, codigo: '501', andar: 5, capacidade: 20 },
        ocupacao_pct: 95,
        recursos_exigidos: ['videoconferencia'],
        recursos_atendidos: true,
        acessibilidade_atendida: null,
        andar_preferido: null,
        andar_preferido_atendido: null,
        andares_permitidos: [],
        termos: [
          { nome: 'ociosidade', valor: 1, detalhe: '1 assento ocioso (20 lugares para 19 pessoas)' },
          { nome: 'andar_preferido', valor: 0, detalhe: 'a equipe nao declarou andar preferido' },
          { nome: 'proximidade', valor: 0, detalhe: 'equipe 2 no mesmo andar' },
          { nome: 'restricao_flexivel', valor: 0, detalhe: 'nenhuma restricao flexivel violada' },
        ],
        custo_total: 1,
        alternativas_avaliadas: 12,
        comparacao: {
          tipo: 'melhor_local',
          detalhe: 'Nenhuma alternativa livre custa menos: a melhor descartada e a sala 502.',
        },
        resumo: 'Sala 501 recomendada para Tecnologia Alpha.',
      },
      alternativas: [
        {
          sala_id: 50,
          codigo: '502',
          andar: 5,
          capacidade: 20,
          custo: 1,
          delta: 0,
          disponivel: false,
          por_que_nao: 'ocupada pela equipe 46 no turno da manha',
        },
      ],
    },
  ],
  nao_alocadas: [
    {
      id: 1,
      equipe_id: 30,
      codigo_motivo: 'SEM_SALA_COMPATIVEL',
      causa: 'A equipe tem 92 pessoas e a maior sala disponivel comporta 80.',
      encaminhamento: 'Dividir a equipe em turmas menores.',
    },
  ],
}

/** A execução é um POST; salas/equipes/setores alimentam a tabela e o mapa do D4. */
function stubRun(corpo: unknown, status = 201) {
  return stubFetchRoteado([
    [/\/api\/runs$/, corpo, status],
    [/\/api\/salas/, salas],
    [/\/api\/equipes/, equipes],
    [/\/api\/setores/, setores],
  ])
}

function renderizar() {
  return render(
    <PerfilProvider>
      <Alocacao />
    </PerfilProvider>,
  )
}

describe('Tela de alocação', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('mostra os indicadores da execução ao lado dos do guloso', async () => {
    stubRun(RUN)
    renderizar()
    fireEvent.click(screen.getByRole('button', { name: /gerar alocação/i }))

    await waitFor(() => expect(screen.getByText('84 / 87')).toBeInTheDocument())
    // A comparação "antes x depois" é o que responde se a recomendação é vantajosa.
    expect(screen.getByText('guloso: 79')).toBeInTheDocument()
    expect(screen.getByText('86.9%')).toBeInTheDocument()
  })

  it('mostra a equipe sem sala com causa e encaminhamento', async () => {
    // Secao 11: o sistema nao esconde o que nao conseguiu resolver.
    stubRun(RUN)
    renderizar()
    fireEvent.click(screen.getByRole('button', { name: /gerar alocação/i }))

    await waitFor(() => expect(screen.getByText(/1 equipe\(s\) sem sala/i)).toBeInTheDocument())
    expect(screen.getByText(/Sem sala compatível/)).toBeInTheDocument()
    expect(screen.getByText(/maior sala disponivel comporta 80/)).toBeInTheDocument()
  })

  it('destaca a execução reprovada pelo validador antes dos números', async () => {
    // Um indicador bonito sobre uma solucao invalida seria pior que nada.
    const reprovada = { ...RUN, status: 'ERRO', erro: 'O validador acusou 2 violacoes (H1).' }
    stubRun(reprovada)
    renderizar()
    fireEvent.click(screen.getByRole('button', { name: /gerar alocação/i }))

    await waitFor(() =>
      expect(screen.getByText(/reprovada pelo validador/i)).toBeInTheDocument(),
    )
  })

  it('mostra a conta que decidiu a sala, termo a termo', async () => {
    // Secao 9: a tela tem que responder *por que* esta sala, e nao so qual.
    stubRun(RUN)
    renderizar()
    fireEvent.click(screen.getByRole('button', { name: /gerar alocação/i }))

    await waitFor(() =>
      expect(screen.getByText(/Sala 501 recomendada para Tecnologia Alpha/)).toBeInTheDocument(),
    )
    expect(screen.getByText('Ociosidade (W_OC)')).toBeInTheDocument()
    expect(screen.getByText(/1 assento ocioso/)).toBeInTheDocument()
    expect(screen.getByText('Custo total')).toBeInTheDocument()
    expect(screen.getByText(/12 sala\(s\) avaliada\(s\)/)).toBeInTheDocument()
  })

  it('mostra a sala descartada e quem a ocupava', async () => {
    // "A 502 seria igual, mas está com a equipe 46" explica a decisão melhor
    // que uma lista vazia — e é o que o Coordenador Geral precisa para decidir
    // se intervém.
    stubRun(RUN)
    renderizar()
    fireEvent.click(screen.getByRole('button', { name: /gerar alocação/i }))

    await waitFor(() => expect(screen.getByText(/Alternativas descartadas/i)).toBeInTheDocument())
    expect(screen.getByText(/Sala 502/)).toBeInTheDocument()
    expect(screen.getByText(/ocupada pela equipe 46/)).toBeInTheDocument()
    expect(screen.getAllByText('indisponível').length).toBeGreaterThan(0)
  })

  it('omite a justificativa das execuções gravadas antes do explainer', async () => {
    // O registro é append-only: uma execução antiga nunca terá explicação. A
    // tela cala em vez de inventar uma razão que ninguém registrou.
    const antiga = { ...RUN, alocacoes: [{ ...RUN.alocacoes[0], explicacao: {}, alternativas: [] }] }
    stubRun(antiga)
    renderizar()
    fireEvent.click(screen.getByRole('button', { name: /gerar alocação/i }))

    await waitFor(() => expect(screen.getByText('84 / 87')).toBeInTheDocument())
    expect(screen.queryByText('Por que esta sala?')).not.toBeInTheDocument()
  })

  it('mostra o motivo quando a API recusa a execução', async () => {
    stubRun({ detail: 'Nao ha equipes cadastradas.' }, 422)
    renderizar()
    fireEvent.click(screen.getByRole('button', { name: /gerar alocação/i }))

    await waitFor(() => expect(screen.getByText(/Nao ha equipes cadastradas/)).toBeInTheDocument())
  })

  it('desenha a tabela equipe → sala e o mapa desta execução (D4)', async () => {
    stubRun(RUN)
    renderizar()
    fireEvent.click(screen.getByRole('button', { name: /gerar alocação/i }))

    await waitFor(() =>
      expect(screen.getByRole('columnheader', { name: 'Equipe' })).toBeInTheDocument(),
    )
    // uma linha equipe -> sala com a ocupação descritiva
    const linha = screen.getByText('Tecnologia Alpha').closest('tr')!
    expect(linha).toHaveTextContent('501')
    expect(linha).toHaveTextContent('5º')
    expect(linha).toHaveTextContent('integral')
    expect(linha).toHaveTextContent('95%')
    // e o mapa dos nove andares
    expect(screen.getByText('Ocupação dos nove andares')).toBeInTheDocument()
    expect(screen.getByTitle(/Sala 501 · 5º/)).toBeInTheDocument()
  })
})
