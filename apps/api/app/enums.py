"""Vocabulario do dominio.

Convencao do projeto: o dominio fala portugues (Sala, Equipe, capacidade), a
infraestrutura fala ingles (Field, Session, router). Os *valores* dos enums sao
ASCII sem acento porque viram chave de JSON e coluna de banco.
"""

from enum import StrEnum


class TipoSala(StrEnum):
    REUNIAO = "reuniao"
    TREINAMENTO = "treinamento"
    AUDITORIO = "auditorio"
    LABORATORIO = "laboratorio"
    PROJETO = "projeto"
    COLABORATIVO = "colaborativo"


class Turno(StrEnum):
    """Faixa de horario da alocacao.

    Modelado desde o D1 porque a mesma sala pode servir duas equipes em turnos
    diferentes -- sem isso a metrica de ocupacao do predio mente para baixo.
    INTEGRAL ocupa a sala nos dois turnos.
    """

    MANHA = "manha"
    TARDE = "tarde"
    INTEGRAL = "integral"

    @property
    def slots(self) -> tuple[str, ...]:
        """Slots elementares que este turno consome (usado pela restricao H2)."""
        if self is Turno.INTEGRAL:
            return ("manha", "tarde")
        return (self.value,)

    def conflita_com(self, outro: "Turno") -> bool:
        return bool(set(self.slots) & set(outro.slots))


class Recurso(StrEnum):
    PROJETOR = "projetor"
    VIDEOCONFERENCIA = "videoconferencia"
    QUADRO_INTERATIVO = "quadro_interativo"
    BANCADA_TECNICA = "bancada_tecnica"
    PALCO = "palco"
    ILHAS_COLABORATIVAS = "ilhas_colaborativas"


class TipoRestricao(StrEnum):
    """Tipos de restricao.

    As seis primeiras sao candidatas naturais a restricao rigida (H3-H7 do
    modelo CP-SAT); as tres ultimas so fazem sentido como flexiveis. Ainda
    assim, quem decide e o campo `Restricao.rigida` -- o enunciado permite, por
    exemplo, tratar proximidade como obrigatoria em um cenario especifico.
    """

    CAPACIDADE_MINIMA = "capacidade_minima"
    ANDAR_PERMITIDO = "andar_permitido"
    ACESSIBILIDADE_OBRIGATORIA = "acessibilidade_obrigatoria"
    RECURSO_OBRIGATORIO = "recurso_obrigatorio"
    SALA_RESERVADA = "sala_reservada"
    SEPARACAO_SETORES = "separacao_setores"
    PROXIMIDADE = "proximidade"
    ANDAR_PREFERIDO = "andar_preferido"
    PRIORIDADE_EQUIPE = "prioridade_equipe"


class AlvoRestricao(StrEnum):
    EQUIPE = "equipe"
    SETOR = "setor"
    SALA = "sala"
    GLOBAL = "global"


class StatusRun(StrEnum):
    """Espelha o status devolvido pelo CP-SAT, mais ERRO para falha do processo."""

    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    UNKNOWN = "UNKNOWN"
    ERRO = "ERRO"


class TipoIntervencao(StrEnum):
    ACEITAR = "aceitar"
    REJEITAR = "rejeitar"
    ALTERAR = "alterar"
    REEXECUTAR = "reexecutar"


class CodigoMotivo(StrEnum):
    """Por que uma equipe ficou sem sala.

    O AC-4 exige que 100% das equipes nao alocadas tenham motivo registrado.
    Um enum (e nao texto livre) e o que torna esse criterio verificavel por
    teste automatizado.
    """

    SEM_SALA_COMPATIVEL = "SEM_SALA_COMPATIVEL"
    RECURSO_INDISPONIVEL = "RECURSO_INDISPONIVEL"
    ACESSIBILIDADE_INDISPONIVEL = "ACESSIBILIDADE_INDISPONIVEL"
    ANDAR_SEM_VAGA = "ANDAR_SEM_VAGA"
    CONFLITO_RESTRICOES = "CONFLITO_RESTRICOES"
    CAPACIDADE_ESGOTADA = "CAPACIDADE_ESGOTADA"


#: Encaminhamento padrao por motivo. O diagnostics.py (D3) refina com os
#: numeros do caso concreto; isto e o texto-base exigido pelo AC-4.
ENCAMINHAMENTO_PADRAO: dict[CodigoMotivo, str] = {
    CodigoMotivo.SEM_SALA_COMPATIVEL: (
        "Dividir a equipe em turmas menores, liberar uma sala hoje marcada como "
        "indisponivel ou revisar o tamanho declarado."
    ),
    CodigoMotivo.RECURSO_INDISPONIVEL: (
        "Instalar o recurso exigido em uma sala compativel ou revisar se ele e "
        "mesmo obrigatorio para esta equipe."
    ),
    CodigoMotivo.ACESSIBILIDADE_INDISPONIVEL: (
        "Nenhuma sala acessivel comporta a equipe. Priorizar adaptacao de uma "
        "sala de capacidade adequada."
    ),
    CodigoMotivo.ANDAR_SEM_VAGA: (
        "Relaxar a restricao de andar permitido ou realocar equipes de menor "
        "prioridade que ocupam o andar."
    ),
    CodigoMotivo.CONFLITO_RESTRICOES: (
        "Duas ou mais restricoes sao mutuamente insatisfazeis. Revisar qual "
        "delas pode passar de rigida para flexivel."
    ),
    CodigoMotivo.CAPACIDADE_ESGOTADA: (
        "O predio nao comporta a demanda no turno solicitado. Avaliar "
        "deslocamento para outro turno."
    ),
}
