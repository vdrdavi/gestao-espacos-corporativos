import { useState } from 'react'
import { ApiError, api } from '../api/client'
import type { Assignment, Explicacao, NaoAlocada, RunDetalhe } from '../api/types'
import { Card, Pendente, Pill, Secao } from '../components/ui'
import { usePerfil } from '../perfil'

const MOTIVOS: Record<NaoAlocada['codigo_motivo'], string> = {
  SEM_SALA_COMPATIVEL: 'Sem sala compatível',
  RECURSO_INDISPONIVEL: 'Recurso indisponível',
  ACESSIBILIDADE_INDISPONIVEL: 'Acessibilidade indisponível',
  ANDAR_SEM_VAGA: 'Andar sem vaga',
  CONFLITO_RESTRICOES: 'Conflito de restrições',
  CAPACIDADE_ESGOTADA: 'Capacidade esgotada',
}

/** Cada termo com o peso que o multiplica, como em docs/objetivo.md. */
const TERMOS: Record<string, string> = {
  ociosidade: 'Ociosidade (W_OC)',
  andar_preferido: 'Andar preferido (W_AP)',
  proximidade: 'Proximidade (W_PR)',
  restricao_flexivel: 'Restrição flexível (W_RS)',
}

function numero(valor: number | undefined): string {
  return valor === undefined ? '—' : valor.toLocaleString('pt-BR')
}

type Explicada = Assignment & { explicacao: Explicacao }

/**
 * Execucoes gravadas antes do D3 nao tem explicacao, e o registro e append-only:
 * elas nunca serao preenchidas. A tela omite o painel em vez de inventar um
 * texto para uma decisao cuja razao ninguem registrou.
 */
function explicada(alocacao: Assignment): alocacao is Explicada {
  return 'resumo' in (alocacao.explicacao ?? {})
}

/**
 * "Por que esta sala foi recomendada para esta equipe?" (secao 9 do enunciado).
 *
 * Mostra a conta que o solver minimizou, termo a termo, e as salas que ficaram
 * pelo caminho -- inclusive as que teriam sido melhores e estavam ocupadas. E o
 * que separa "o algoritmo decidiu" de uma decisao auditavel.
 */
function Justificativa({ alocacoes }: { alocacoes: Assignment[] }) {
  const explicadas = alocacoes.filter(explicada)
  const [indice, setIndice] = useState(0)

  if (explicadas.length === 0) return null

  const alocacao = explicadas[Math.min(indice, explicadas.length - 1)]
  const { explicacao } = alocacao
  const { comparacao } = explicacao

  return (
    <div className="rounded border border-slate-200 bg-white p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h3 className="text-sm font-semibold text-slate-900">Por que esta sala?</h3>
        <label className="text-xs text-slate-500">
          Recomendação{' '}
          <select
            aria-label="Recomendação a justificar"
            value={Math.min(indice, explicadas.length - 1)}
            onChange={(e) => setIndice(Number(e.target.value))}
            className="rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800"
          >
            {explicadas.map((a, i) => (
              <option key={a.id} value={i}>
                {a.explicacao.equipe.nome} → sala {a.explicacao.sala.codigo}
              </option>
            ))}
          </select>
        </label>
      </div>

      <p className="mt-3 max-w-prose text-sm text-slate-700">{explicacao.resumo}</p>

      <div className="mt-3 flex flex-wrap gap-1.5">
        <Pill>turno {explicacao.equipe.turno}</Pill>
        <Pill>prioridade {explicacao.equipe.prioridade}</Pill>
        <Pill tom={explicacao.ocupacao_pct >= 70 ? 'ok' : 'alerta'}>
          ocupação {explicacao.ocupacao_pct}%
        </Pill>
        {explicacao.recursos_exigidos.length > 0 && (
          <Pill tom={explicacao.recursos_atendidos ? 'ok' : 'alerta'}>
            recursos: {explicacao.recursos_exigidos.join(', ')}
          </Pill>
        )}
        {explicacao.acessibilidade_atendida !== null && (
          <Pill tom={explicacao.acessibilidade_atendida ? 'ok' : 'alerta'}>
            acessibilidade {explicacao.acessibilidade_atendida ? 'atendida' : 'não atendida'}
          </Pill>
        )}
        {explicacao.andar_preferido_atendido !== null && (
          <Pill tom={explicacao.andar_preferido_atendido ? 'ok' : 'alerta'}>
            andar preferido {explicacao.andar_preferido}º{' '}
            {explicacao.andar_preferido_atendido ? 'atendido' : 'não atendido'}
          </Pill>
        )}
      </div>

      {/* A conta, e nao um resumo dela: e o numero que o solver minimizou. */}
      <table className="mt-4 w-full text-xs">
        <caption className="sr-only">Custo decomposto termo a termo</caption>
        <tbody>
          {explicacao.termos.map((termo) => (
            <tr key={termo.nome} className="border-t border-slate-100">
              <th scope="row" className="w-44 py-1.5 text-left font-medium text-slate-600">
                {TERMOS[termo.nome] ?? termo.nome}
              </th>
              <td className="py-1.5 text-slate-500">{termo.detalhe}</td>
              <td className="tabular w-16 py-1.5 text-right font-medium text-slate-900">
                {numero(termo.valor)}
              </td>
            </tr>
          ))}
          <tr className="border-t-2 border-slate-300">
            <th scope="row" className="py-1.5 text-left font-semibold text-slate-900">
              Custo total
            </th>
            <td className="py-1.5 text-slate-500">
              {explicacao.alternativas_avaliadas} sala(s) avaliada(s)
            </td>
            <td className="tabular py-1.5 text-right font-semibold text-slate-900">
              {numero(explicacao.custo_total)}
            </td>
          </tr>
        </tbody>
      </table>

      <p
        className={`mt-4 rounded border p-3 text-xs ${
          comparacao.tipo === 'trade_off_global'
            ? 'border-amber-300 bg-amber-50 text-amber-900'
            : 'border-slate-200 bg-slate-50 text-slate-600'
        }`}
      >
        {comparacao.detalhe}
      </p>

      {alocacao.alternativas.length > 0 && (
        <>
          <h4 className="mt-5 text-xs font-medium uppercase tracking-wider text-slate-500">
            Alternativas descartadas
          </h4>
          <ul className="mt-2 space-y-1.5">
            {alocacao.alternativas.map((alternativa) => (
              <li
                key={alternativa.sala_id}
                className="flex flex-wrap items-baseline gap-x-2 border-t border-slate-100 pt-1.5 text-xs"
              >
                <span className="font-medium text-slate-800">
                  Sala {alternativa.codigo} · {alternativa.andar}º · {alternativa.capacidade} lugares
                </span>
                <span className="tabular text-slate-500">
                  custo {numero(alternativa.custo)} ({alternativa.delta >= 0 ? '+' : ''}
                  {numero(alternativa.delta)})
                </span>
                {/* Uma sala ocupada nao era uma opcao real: dizer isso e mais
                    honesto que exibi-la como se tivesse sido preterida. */}
                {!alternativa.disponivel && <Pill tom="alerta">indisponível</Pill>}
                <span className="basis-full text-slate-500">{alternativa.por_que_nao}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}

export default function Alocacao() {
  const { perfil } = usePerfil()
  const [executando, setExecutando] = useState(false)
  const [run, setRun] = useState<RunDetalhe | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  async function gerar() {
    setExecutando(true)
    setRun(null)
    setErro(null)
    try {
      setRun(await api.gerarAlocacao(perfil))
    } catch (e) {
      setErro(e instanceof ApiError || e instanceof Error ? e.message : String(e))
    } finally {
      setExecutando(false)
    }
  }

  const m = run?.metricas ?? {}
  const antes = run?.metricas_baseline ?? {}

  return (
    <Secao titulo="Gerar alocação otimizada">
      <button
        onClick={gerar}
        disabled={executando}
        className="rounded bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800 disabled:opacity-50"
      >
        {executando ? 'Executando...' : 'GERAR ALOCAÇÃO OTIMIZADA'}
      </button>

      {erro && (
        <div className="mt-6 rounded border border-red-200 bg-red-50 p-4 text-sm text-red-800">{erro}</div>
      )}

      {run && (
        <div className="mt-6">
          {/* O validador independente é quem decide se a execução vale. Quando
              ele discorda do solver, o alerta vem antes dos números — um
              indicador bonito sobre uma solução inválida seria pior que nada. */}
          {run.erro && (
            <div className="mb-4 rounded border border-red-300 bg-red-50 p-4 text-sm text-red-900">
              <strong className="font-semibold">Execução reprovada pelo validador.</strong> {run.erro}
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Card
              titulo="Equipes alocadas"
              valor={`${numero(m.equipes_alocadas)} / ${numero(m.equipes_total)}`}
              detalhe={`guloso: ${numero(antes.equipes_alocadas)}`}
              destaque
            />
            <Card
              titulo="Ocupação média"
              valor={`${m.ocupacao_media_pct ?? '—'}%`}
              detalhe={`guloso: ${antes.ocupacao_media_pct ?? '—'}%`}
              destaque
            />
            <Card
              titulo="Assentos ociosos"
              valor={numero(m.assentos_ociosos)}
              detalhe={`guloso: ${numero(antes.assentos_ociosos)}`}
            />
            <Card
              titulo="Restrições violadas"
              valor={numero(m.violacoes)}
              detalhe="verificado por validador independente do solver"
            />
            <Card titulo="Pessoas alocadas" valor={numero(m.pessoas_alocadas)} />
            <Card
              titulo="Salas ocupadas"
              valor={`${numero(m.salas_ocupadas)} / ${numero(m.salas_total)}`}
            />
            <Card titulo="Custo da solução" valor={numero(m.custo)} detalhe={`guloso: ${numero(antes.custo)}`} />
            <Card
              titulo="Tempo"
              valor={`${(run.duracao_ms / 1000).toFixed(2)} s`}
              detalhe={`${run.status} · execução #${run.id}`}
            />
          </div>

          {run.nao_alocadas.length > 0 && (
            <div className="mt-6 rounded border border-amber-300 bg-amber-50 p-5">
              <div className="text-xs font-medium uppercase tracking-wider text-amber-700">
                {run.nao_alocadas.length} equipe(s) sem sala
              </div>
              <p className="mt-1 max-w-prose text-xs text-amber-800">
                O sistema não esconde o que não conseguiu resolver nem faz uma alocação inválida
                para melhorar o próprio indicador.
              </p>
              <ul className="mt-3 space-y-3">
                {run.nao_alocadas.map((na) => (
                  <li key={na.id} className="border-t border-amber-200/60 pt-3 text-xs text-amber-900">
                    <div className="font-medium">
                      Equipe {na.equipe_id} — {MOTIVOS[na.codigo_motivo] ?? na.codigo_motivo}
                    </div>
                    <div className="mt-0.5">{na.causa}</div>
                    <div className="mt-0.5 text-amber-800">Encaminhamento: {na.encaminhamento}</div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-6 space-y-4">
            <Justificativa alocacoes={run.alocacoes} />
            <Pendente
              dia="D4"
              o="A tabela equipe → sala e o mapa de ocupação dos nove andares. Os dados desta execução já estão no banco; falta a tela que os desenha."
            />
          </div>
        </div>
      )}
    </Secao>
  )
}
