import { api } from '../api/client'
import { useApi } from '../api/useApi'
import { Card, Carregando, Erro, Secao } from '../components/ui'

const traco = (v: number | null | undefined, sufixo = '') =>
  v === null || v === undefined ? '—' : `${v}${sufixo}`

export default function Monitoramento() {
  const metricas = useApi(() => api.metricas())

  if (metricas.erro) return <Erro erro={metricas.erro} />
  if (metricas.carregando || !metricas.dados) return <Carregando o="as métricas" />

  const m = metricas.dados

  return (
    <Secao titulo="Monitoramento do Motor de Alocação">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card titulo="Execuções" valor={m.execucoes_total} detalhe={`${m.execucoes_com_erro} com erro`} />
        <Card titulo="Última otimização" valor={traco(m.duracao_ultima_ms, ' ms')} />
        <Card titulo="Duração p95" valor={traco(m.duracao_p95_ms, ' ms')} detalhe="limite do AC-6: 10.000 ms" />
        <Card titulo="Taxa de alocação" valor={traco(m.taxa_alocacao_pct, '%')} />
        <Card titulo="Ocupação média" valor={traco(m.ocupacao_media_pct, '%')} />
        <Card titulo="Equipes sem sala" valor={traco(m.equipes_nao_alocadas)} />
        <Card titulo="Violações" valor={traco(m.violacoes)} detalhe="restrições rígidas" />
        <Card
          titulo="Intervenções por execução"
          valor={traco(m.intervencoes_por_execucao)}
          detalhe={`${m.intervencoes_total} no total`}
          destaque
        />
      </div>

      <p className="mt-4 max-w-prose text-xs text-slate-500">
        <strong className="font-medium text-slate-700">Intervenções por execução</strong> é a métrica
        que mais importa aqui. Se o Coordenador Geral altera muitas recomendações, o motor está
        desalinhado com o julgamento humano — é o sinal de degradação mais próximo de um{' '}
        <em>drift</em> que dá para ter num protótipo.
      </p>
      <p className="mt-2 font-mono text-xs text-slate-400">motor: {m.engine_version}</p>
    </Secao>
  )
}
