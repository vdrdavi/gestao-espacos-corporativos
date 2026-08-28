import { NavLink, Outlet } from 'react-router-dom'
import { usePerfil, type Perfil } from '../perfil'

const TELAS: { rota: string; nome: string; perfis: Perfil[] }[] = [
  { rota: '/', nome: 'Dashboard', perfis: ['coordenador-geral'] },
  { rota: '/salas', nome: 'Salas', perfis: ['coordenador-geral'] },
  { rota: '/equipes', nome: 'Equipes', perfis: ['coordenador-geral', 'coordenador-setor'] },
  { rota: '/restricoes', nome: 'Restrições', perfis: ['coordenador-geral', 'coordenador-setor'] },
  { rota: '/alocacao', nome: 'Alocação', perfis: ['coordenador-geral'] },
  { rota: '/comparacao', nome: 'Comparação', perfis: ['coordenador-geral'] },
  { rota: '/monitoramento', nome: 'Monitoramento', perfis: ['coordenador-geral'] },
  { rota: '/governanca', nome: 'Governança', perfis: ['coordenador-geral'] },
]

export default function Layout() {
  const { perfil, setPerfil } = usePerfil()
  const visiveis = TELAS.filter((t) => t.perfis.includes(perfil))

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-3">
          <div>
            <div className="text-sm font-semibold text-slate-900">Gestão de Espaços Corporativos</div>
            <div className="text-xs text-slate-500">9 andares · 108 salas · 8 setores</div>
          </div>

          <label className="flex items-center gap-2 text-xs text-slate-600">
            Perfil
            <select
              value={perfil}
              onChange={(e) => setPerfil(e.target.value as Perfil)}
              className="rounded border border-slate-300 bg-white px-2 py-1 font-mono text-xs"
            >
              <option value="coordenador-geral">coordenador-geral</option>
              <option value="coordenador-setor">coordenador-setor</option>
            </select>
          </label>
        </div>

        <nav className="mx-auto max-w-6xl px-6">
          <ul className="flex flex-wrap gap-1">
            {visiveis.map((tela) => (
              <li key={tela.rota}>
                <NavLink
                  to={tela.rota}
                  end={tela.rota === '/'}
                  className={({ isActive }) =>
                    `-mb-px inline-block border-b-2 px-3 py-2 text-sm ${
                      isActive
                        ? 'border-teal-600 font-medium text-teal-700'
                        : 'border-transparent text-slate-600 hover:text-slate-900'
                    }`
                  }
                >
                  {tela.nome}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
