import { useState } from 'react'
import { api } from '../api/client'
import { useApi } from '../api/useApi'
import { Card, Carregando, Erro, Pendente, Secao } from '../components/ui'

export default function Dashboard() {
  const salas = useApi(() => api.salas())
  const equipes = useApi(() => api.equipes())
  const cenarios = useApi(() => api.cenarios())
  const [carregandoCenario, setCarregandoCenario] = useState<string | null>(null)

  if (salas.erro) return <Erro erro={salas.erro} />
  if (salas.carregando || equipes.carregando) return <Carregando o="a situação do prédio" />

  const listaSalas = salas.dados ?? []
  const listaEquipes = equipes.dados ?? []
  const disponiveis = listaSalas.filter((s) => s.disponivel)
  const capacidade = disponiveis.reduce((t, s) => t + s.capacidade, 0)
  const demanda = listaEquipes.reduce((t, e) => t + e.tamanho, 0)

  async function carregar(nome: string) {
    setCarregandoCenario(nome)
    try {
      await api.carregarCenario(nome)
      salas.recarregar()
      equipes.recarregar()
    } finally {
      setCarregandoCenario(null)
    }
  }

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

      <Secao titulo="Ocupação dos nove andares">
        <div className="rounded border border-slate-200 bg-white p-4">
          <div className="flex flex-col gap-1">
            {[9, 8, 7, 6, 5, 4, 3, 2, 1].map((andar) => {
              const doAndar = disponiveis.filter((s) => s.andar === andar)
              const capAndar = doAndar.reduce((t, s) => t + s.capacidade, 0)
              const largura = capacidade ? (capAndar / Math.max(capacidade / 9, 1)) * 50 : 0
              return (
                <div key={andar} className="flex items-center gap-3 text-xs">
                  <span className="w-8 text-right font-mono text-slate-500">{andar}º</span>
                  <div
                    className="h-5 rounded-sm bg-teal-200"
                    style={{ width: `${Math.min(largura, 100)}%`, minWidth: '2px' }}
                  />
                  <span className="tabular text-slate-600">
                    {doAndar.length} salas · {capAndar} assentos
                  </span>
                </div>
              )
            })}
          </div>
          <p className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-500">
            Hoje o mapa mostra <strong>capacidade instalada</strong>. No D4 cada sala vira um bloco
            colorido pela faixa de ocupação da alocação vigente.
          </p>
        </div>
      </Secao>

      <Secao titulo="Indicadores da alocação">
        <Pendente
          dia="D4"
          o="Ocupação média, assentos ociosos, equipes sem sala e restrições violadas aparecem aqui assim que o motor produzir a primeira alocação. Enquanto não houver execução, não há número a mostrar — e inventar um seria pior que deixar vazio."
        />
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
