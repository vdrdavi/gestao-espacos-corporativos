import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import Layout from '../components/Layout'
import { PerfilProvider } from '../perfil'

function renderizar() {
  return render(
    <MemoryRouter>
      <PerfilProvider>
        <Layout />
      </PerfilProvider>
    </MemoryRouter>,
  )
}

describe('Layout', () => {
  it('mostra as telas do Coordenador Geral por padrao', () => {
    renderizar()
    for (const tela of ['Dashboard', 'Alocação', 'Governança', 'Monitoramento']) {
      expect(screen.getByRole('link', { name: tela })).toBeInTheDocument()
    }
  })

  it('oferece a troca de perfil, que alimenta a trilha de auditoria', () => {
    renderizar()
    const seletor = screen.getByLabelText(/perfil/i)
    expect(seletor).toHaveValue('coordenador-geral')
  })
})
