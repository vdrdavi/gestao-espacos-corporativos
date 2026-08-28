import { Pendente, Secao } from '../components/ui'

export default function Comparacao() {
  return (
    <Secao titulo="Situação inicial × situação otimizada">
      <Pendente
        dia="D4"
        o="A comparação lê as duas execuções gravadas no mesmo Run: metricas_baseline (alocação gulosa first-fit, que representa a distribuição manual de hoje) e metricas (CP-SAT). Os indicadores comparados são ocupação média, assentos ociosos, equipes sem sala e violações de restrição. O campo já existe no modelo de dados desde o D1 — falta o motor preencher."
      />
    </Secao>
  )
}
