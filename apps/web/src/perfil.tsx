import { createContext, useContext, useState, type ReactNode } from 'react'

/**
 * Perfil do usuario logado.
 *
 * Nao ha autenticacao no prototipo -- e um seletor no cabecalho. O que importa
 * e que o nome escolhido aqui e o que vai para `Run.usuario` e para
 * `Intervencao.usuario`: a trilha de auditoria precisa responder "quem
 * executou?" (secao 12), e no prototipo quem responde e este seletor.
 */
export type Perfil = 'coordenador-geral' | 'coordenador-setor'

interface PerfilContexto {
  perfil: Perfil
  setPerfil: (p: Perfil) => void
}

const Contexto = createContext<PerfilContexto | null>(null)

export function PerfilProvider({ children }: { children: ReactNode }) {
  const [perfil, setPerfil] = useState<Perfil>('coordenador-geral')
  return <Contexto.Provider value={{ perfil, setPerfil }}>{children}</Contexto.Provider>
}

export function usePerfil(): PerfilContexto {
  const contexto = useContext(Contexto)
  if (!contexto) throw new Error('usePerfil precisa estar dentro de <PerfilProvider>')
  return contexto
}
