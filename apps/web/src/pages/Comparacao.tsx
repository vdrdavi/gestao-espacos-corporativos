import { TabelaComparacao } from '../components/TabelaComparacao'
import { Carregando, Erro, Secao } from '../components/ui'
import { LegendaRun, NotaDegradada, PainelSemRun } from '../components/estadoRun'
import { useUltimaRun } from '../api/useUltimaRun'

/**
 * Situacao inicial x situacao otimizada (desafio secao 8). Le as duas colunas
 * de metricas gravadas no mesmo Run -- `metricas_baseline` (guloso) e
 * `metricas` (CP-SAT) -- da ultima execucao valida.
 */
export default function Comparacao() {
  const ur = useUltimaRun()

  if (ur.erro) return <Erro erro={ur.erro} />
  if (ur.carregando || !ur.dados) return <Carregando o="a comparação" />

  const e = ur.dados

  return (
    <Secao titulo="Situação inicial × situação otimizada">
      {e.tipo !== 'ok' ? (
        <PainelSemRun estado={e} assunto="A comparação" />
      ) : (
        <>
          {e.degradada && <NotaDegradada run={e.run} />}
          <TabelaComparacao baseline={e.run.metricas_baseline} otimizada={e.run.metricas} />
          <p className="mt-3 max-w-prose text-xs text-slate-500">
            Antes = alocação gulosa first-fit, a distribuição manual de hoje (AC-5). Depois = CP-SAT.
          </p>
          <LegendaRun run={e.run} />
        </>
      )}
    </Secao>
  )
}
