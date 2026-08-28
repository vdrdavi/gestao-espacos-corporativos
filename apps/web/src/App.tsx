import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import { PerfilProvider } from './perfil'
import Alocacao from './pages/Alocacao'
import Comparacao from './pages/Comparacao'
import Dashboard from './pages/Dashboard'
import Equipes from './pages/Equipes'
import Governanca from './pages/Governanca'
import Monitoramento from './pages/Monitoramento'
import Restricoes from './pages/Restricoes'
import Salas from './pages/Salas'

export default function App() {
  return (
    <PerfilProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="salas" element={<Salas />} />
          <Route path="equipes" element={<Equipes />} />
          <Route path="restricoes" element={<Restricoes />} />
          <Route path="alocacao" element={<Alocacao />} />
          <Route path="comparacao" element={<Comparacao />} />
          <Route path="monitoramento" element={<Monitoramento />} />
          <Route path="governanca" element={<Governanca />} />
        </Route>
      </Routes>
    </PerfilProvider>
  )
}
