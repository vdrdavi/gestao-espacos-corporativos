import { useState } from 'react'
import { api } from '../api/client'
import { useApi } from '../api/useApi'
import { useReferencia } from '../api/useReferencia'
import { useUltimaRun } from '../api/useUltimaRun'
import { MapaAndares } from '../components/MapaAndares'
import { Card, Carregando, Erro, Secao } from '../components/ui'
import { LegendaRun, NotaDegradada, PainelSemRun } from '../components/estadoRun'
import { numero, pct } from '../lib/alocacao'

export default function Dashboard() {
  const ref = useReferencia()
  const ur = useUltimaRun()
  const cenarios = useApi(() => api.cenarios())
  const [carregandoCenario, setCarregandoCenario] = useState<string | null>(null)

  if (ref.erro) return <Erro erro={ref.erro} />
  if (ref.carregando || !ref.dados) return <Carregando o="a situação do prédio" />

  const { salas: listaSalas, equipes: listaEquipes } = ref.dados
  const disponiveis = listaSalas.filter((s) => s.disponivel)
  const capacidade = disponiveis.reduce((t, s) => t + s.capacidade, 0)
  const demanda = listaEquipes.reduce((t, e) => t + e.tamanho, 0)

  async function carregar(nome: string) {
    setCarregandoCenario(nome)
    try {
      await api.carregarCenario(nome)
      ref.recarregar()
      ur.recarregar()
    } finally {
      setCarregandoCenario(null)
    }
  }

  const est = ur.dados

  return (
    <>
      <Secao titulo="Situação do prédio">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Card titulo="Salas disponíveis" valor={disponiveis.length} detalhe={`${listaSalas.length} no total`} />
          <Card titulo="Capacidade" valor={capacidade.toLocaleString('pt-BR')} detalhe="assentos" />
          <Card titulo="Equipes" valor={listaEquipes.length} detalhe={`${demanda.toLocaleString('pt-BR')} pessoas`} />
          <Card
            titulo="Demanda / capacidade"
            valor={capacidade ? `${Math.round((demanda / capacidade) * 100)}%` : '—'}
            detalhe="antes de qualquer alocação"
            destaque
          />
        </div>
      </Secao>

      <Secao titulo="Indicadores da alocação">
        {ur.erro ? (
          <Erro erro={ur.erro} />
        ) : !est ? (
          <Carregando o="os indicadores" />
        ) : est.tipo !== 'ok' ? (
          <PainelSemRun estado={est} assunto="O painel de indicadores" />
        ) : (
          <>
            {est.degradada && <NotaDegradada run={est.run} />}
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Card titulo="Ocupação média" valor={pct(est.run.metricas.ocupacao_media_pct)} destaque />
              <Card titulo="Assentos ociosos" valor={numero(est.run.metricas.assentos_ociosos)} />
              <Card
                titulo="Equipes sem sala"
                valor={numero(est.run.metricas.equipes_nao_alocadas)}
                detalhe={`${numero(est.run.metricas.pessoas_nao_alocadas)} pessoas`}
              />
              <Card
                titulo="Restrições violadas"
                valor={numero(est.run.metricas.violacoes)}
                detalhe="validador independente do solver"
              />
              <Card titulo="Pessoas alocadas" valor={numero(est.run.metricas.pessoas_alocadas)} />
              <Card
                titulo="Salas ocupadas"
                valor={`${numero(est.run.metricas.salas_ocupadas)} / ${numero(est.run.metricas.salas_total)}`}
              />
              <Card titulo="Utilização de salas" valor={pct(est.run.metricas.utilizacao_salas_pct)} />
              <Card
                titulo="Equipes alocadas"
                valor={`${numero(est.run.metricas.equipes_alocadas)} / ${numero(est.run.metricas.equipes_total)}`}
              />
            </div>
            <LegendaRun run={est.run} />
          </>
        )}
      </Secao>

      <Secao titulo="Ocupação dos nove andares">
        {ur.erro ? (
          <Erro erro={ur.erro} />
        ) : !est ? (
          <Carregando o="o mapa" />
        ) : est.tipo !== 'ok' ? (
          <PainelSemRun estado={est} assunto="O mapa de ocupação" />
        ) : (
          <>
            <MapaAndares alocacoes={est.run.alocacoes} referencia={ref.dados} />
            <LegendaRun run={est.run} />
          </>
        )}
      </Secao>

      <Secao titulo="Cenários">
        <div className="grid gap-2 sm:grid-cols-2">
          {(cenarios.dados ?? []).map((c) => (
            <button
              key={c.nome}
              onClick={() => carregar(c.nome)}
              disabled={carregandoCenario !== null}
              className="rounded border border-slate-200 bg-white p-3 text-left hover:border-teal-400 disabled:opacity-50"
            >
              <div className="text-sm font-medium text-slate-900">{c.titulo}</div>
              <div className="mt-0.5 font-mono text-[11px] text-slate-400">{c.nome}</div>
              <p className="mt-1 text-xs text-slate-600">{c.descricao}</p>
            </button>
          ))}
        </div>
        <p className="mt-3 text-xs text-slate-500">
          Carregar um cenário reseta o banco. Os três de estresse existem para demonstrar o
          tratamento de exceções ao vivo.
        </p>
      </Secao>
    </>
  )
}
