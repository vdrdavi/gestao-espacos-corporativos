import { numero } from '../lib/alocacao'

/**
 * Situacao inicial x situacao otimizada (desafio secao 8).
 *
 * "Antes" = `metricas_baseline` (guloso first-fit, a distribuicao manual de
 * hoje, AC-5). "Depois" = `metricas` (CP-SAT). Ambas gravadas no mesmo Run,
 * entao a comparacao e sempre entre a mesma entrada.
 */

interface Indicador {
  chave: string
  rotulo: string
  sufixo?: string
  /** Direcao que conta como melhora, para colorir o delta. */
  melhor: 'maior' | 'menor'
}

const INDICADORES: Indicador[] = [
  { chave: 'ocupacao_media_pct', rotulo: 'Ocupação média', sufixo: '%', melhor: 'maior' },
  { chave: 'assentos_ociosos', rotulo: 'Assentos ociosos', melhor: 'menor' },
  { chave: 'equipes_nao_alocadas', rotulo: 'Equipes sem sala', melhor: 'menor' },
  { chave: 'violacoes', rotulo: 'Violações', melhor: 'menor' },
  { chave: 'equipes_alocadas', rotulo: 'Equipes alocadas', melhor: 'maior' },
  { chave: 'custo', rotulo: 'Custo da solução', melhor: 'menor' },
]

function celula(valor: number | undefined, sufixo?: string): string {
  if (valor === undefined) return '—'
  return `${numero(valor)}${sufixo ?? ''}`
}

function delta(
  antes: number | undefined,
  depois: number | undefined,
  melhor: 'maior' | 'menor',
  sufixo?: string,
): { texto: string; cor: string } {
  if (antes === undefined || depois === undefined) return { texto: '—', cor: 'text-slate-400' }
  const d = Math.round((depois - antes) * 10) / 10
  if (d === 0) return { texto: '0', cor: 'text-slate-400' }
  const melhorou = melhor === 'maior' ? d > 0 : d < 0
  const sinal = d > 0 ? '+' : ''
  return {
    texto: `${sinal}${numero(d)}${sufixo ?? ''}`,
    cor: melhorou ? 'text-teal-700' : 'text-red-700',
  }
}

export function TabelaComparacao({
  baseline,
  otimizada,
}: {
  baseline: Record<string, number>
  otimizada: Record<string, number>
}) {
  return (
    <div className="overflow-x-auto rounded border border-slate-200 bg-white">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs uppercase tracking-wider text-slate-500">
            <th className="px-3 py-2">Indicador</th>
            <th className="px-3 py-2 text-right">Antes</th>
            <th className="px-3 py-2 text-right">Depois</th>
            <th className="px-3 py-2 text-right">Δ</th>
          </tr>
        </thead>
        <tbody>
          {INDICADORES.map((ind) => {
            const antes = baseline[ind.chave]
            const depois = otimizada[ind.chave]
            const d = delta(antes, depois, ind.melhor, ind.sufixo)
            return (
              <tr key={ind.chave} className="border-b border-slate-100 last:border-0">
                <th scope="row" className="px-3 py-2 text-left font-medium text-slate-700">
                  {ind.rotulo}
                </th>
                <td className="tabular px-3 py-2 text-right text-slate-600">
                  {celula(antes, ind.sufixo)}
                </td>
                <td className="tabular px-3 py-2 text-right font-medium text-slate-900">
                  {celula(depois, ind.sufixo)}
                </td>
                <td className={`tabular px-3 py-2 text-right font-medium ${d.cor}`}>{d.texto}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
