"""
=============================================================================
 config.py — Configurações gerais do sistema
=============================================================================
 Aqui ficam as CONSTANTES usadas em todo o sistema:
   • nome e versão do aplicativo
   • caminhos das pastas (banco de dados, backups, recibos, relatórios)
   • paleta de cores (tirada da logomarca do Espaço)
   • listas fixas (formas de pagamento, diagnósticos, parentescos, etc.)

 Se quiser mudar uma cor ou adicionar uma forma de pagamento, é aqui.
=============================================================================
"""
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Identificação do aplicativo
# ---------------------------------------------------------------------------
APP_NOME = "Espaço Terapêutico Shay Soares"
APP_NOME_CURTO = "Shay Soares"
APP_VERSAO = "1.0.0"


# ---------------------------------------------------------------------------
# Caminhos de pastas
# ---------------------------------------------------------------------------
def _pasta_base() -> Path:
    """
    Descobre a pasta onde o sistema está instalado.
    - Rodando pelo Python normal: pasta do projeto (onde fica o main.py).
    - Rodando como executável (.exe gerado pelo PyInstaller): pasta do .exe.
    """
    if getattr(sys, "frozen", False):          # executável PyInstaller
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]  # .../EspacoShaySoares


def _pasta_recursos() -> Path:
    """Pasta dos arquivos embutidos (logo, ícone). No .exe fica em _MEIPASS."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return _pasta_base()


BASE_DIR = _pasta_base()
ASSETS_DIR = _pasta_recursos() / "assets"

# A pasta de DADOS pode ser trocada pela variável de ambiente SHAY_DADOS
# (útil para testes ou para guardar o banco numa pasta sincronizada).
DADOS_DIR = Path(os.environ.get("SHAY_DADOS", BASE_DIR / "dados"))
DB_PATH = DADOS_DIR / "espaco_shay.db"          # arquivo do banco SQLite
BACKUP_DIR = DADOS_DIR / "backups"               # cópias de segurança
RECIBOS_DIR = DADOS_DIR / "recibos"              # PDFs de recibos e carnês
RELATORIOS_DIR = DADOS_DIR / "relatorios"        # planilhas exportadas
LOG_PATH = DADOS_DIR / "sistema.log"             # registro de erros

LOGO_PATH = ASSETS_DIR / "logo.png"
ICONE_ICO = ASSETS_DIR / "icone.ico"
ICONE_PNG = ASSETS_DIR / "icone.png"


def garantir_pastas() -> None:
    """Cria as pastas de dados caso ainda não existam."""
    for pasta in (DADOS_DIR, BACKUP_DIR, RECIBOS_DIR, RELATORIOS_DIR):
        pasta.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Paleta de cores — extraída da logomarca
#   Verde-água (#86B3B5) → cor principal (título "Espaço Terapêutico")
#   Rosa-salmão (#F4A9A3) → cor de destaque (cérebro/flor)
# ---------------------------------------------------------------------------
CORES = {
    # Cores da marca
    "primaria": "#86B3B5",          # verde-água da logo
    "primaria_escura": "#5E9195",   # hover / textos de destaque
    "primaria_profunda": "#3F6D70", # títulos
    "primaria_clara": "#DCEBEC",    # fundos suaves
    "primaria_suave": "#EEF6F6",
    "destaque": "#F4A9A3",          # rosa da logo
    "destaque_escuro": "#E38880",
    "destaque_claro": "#FCE6E3",

    # Neutros
    "fundo": "#F6FAFA",             # fundo geral da janela
    "superficie": "#FFFFFF",        # cartões
    "borda": "#E3ECEC",
    "texto": "#2E4A4C",             # texto principal
    "texto_suave": "#6E8B8D",       # legendas
    "texto_claro": "#FFFFFF",

    # Menu lateral
    "menu_fundo": "#FFFFFF",
    "menu_ativo": "#DCEBEC",

    # Situação financeira (tons harmonizados com a paleta)
    "pago": "#5FAE8F",              # verde
    "pago_claro": "#E2F3EC",
    "em_dia": "#E4A951",            # âmbar
    "em_dia_claro": "#FBF0DC",
    "atraso": "#DE6F68",            # vermelho-rosado
    "atraso_claro": "#FBE3E1",
    "cancelado": "#A7B4B5",
    "cancelado_claro": "#EEF1F1",
    "whatsapp": "#25D366",
    "whatsapp_escuro": "#1DA851",
}

FONTE = "Segoe UI"  # fonte padrão do Windows; em outros sistemas cai numa similar


# ---------------------------------------------------------------------------
# Situações (status) financeiros exibidos ao usuário
# ---------------------------------------------------------------------------
SITUACAO_PAGO = "Pago"
SITUACAO_EM_DIA = "Pendente (em dia)"
SITUACAO_ATRASO = "Em atraso"
SITUACAO_CANCELADO = "Cancelado"
SITUACOES = [SITUACAO_PAGO, SITUACAO_EM_DIA, SITUACAO_ATRASO, SITUACAO_CANCELADO]

COR_SITUACAO = {
    SITUACAO_PAGO: ("pago", "pago_claro"),
    SITUACAO_EM_DIA: ("em_dia", "em_dia_claro"),
    SITUACAO_ATRASO: ("atraso", "atraso_claro"),
    SITUACAO_CANCELADO: ("cancelado", "cancelado_claro"),
}


# ---------------------------------------------------------------------------
# Formas de pagamento aceitas
# (a última coluna indica se a forma permite informar nº de vezes no cartão)
# ---------------------------------------------------------------------------
FORMAS_PAGAMENTO = [
    "PIX",
    "Dinheiro",
    "Cartão de débito",
    "Cartão de crédito (à vista)",
    "Cartão de crédito (parcelado)",
    "Transferência bancária (TED/DOC)",
    "Boleto bancário",
    "Link de pagamento",
    "Cheque",
    "Convênio / Plano de saúde",
    "Reembolso",
    "Permuta / Cortesia",
    "Outro",
]
FORMAS_COM_PARCELAS = {"Cartão de crédito (parcelado)", "Cheque", "Link de pagamento"}

# Modalidades de contratação
MODALIDADE_PARCELADO = "parcelado"
MODALIDADE_A_VISTA = "a_vista"
MODALIDADES = {
    MODALIDADE_PARCELADO: "Mensal / Parcelado",
    MODALIDADE_A_VISTA: "À vista (pagamento único)",
}

# Tipos de cobrança de um serviço
TIPO_MENSAL = "mensal"        # terapia contínua: uma mensalidade por mês
TIPO_PARCELADO = "parcelado"  # pacote com valor total dividido (ex.: avaliação)
TIPO_UNICO = "unico"          # cobrança única (ex.: taxa de adesão)
TIPOS_COBRANCA = {
    TIPO_MENSAL: "Mensalidade",
    TIPO_PARCELADO: "Pacote parcelado",
    TIPO_UNICO: "Cobrança única",
}

# Dias de vencimento usados no carnê do Espaço
DIAS_VENCIMENTO = ["05", "10", "15", "20", "25", "30"]


# ---------------------------------------------------------------------------
# Listas usadas no cadastro
# ---------------------------------------------------------------------------
DIAGNOSTICOS = [
    "TEA (Autismo)", "TDAH", "TOD", "Dislexia", "Discalculia", "Disgrafia",
    "Atraso de fala / linguagem", "Apraxia de fala", "Deficiência intelectual",
    "Síndrome de Down", "Altas habilidades", "Ansiedade", "Depressão",
    "Transtorno de processamento auditivo", "Em investigação", "Outro",
]
NIVEIS_SUPORTE_TEA = ["", "Nível 1", "Nível 2", "Nível 3", "Não se aplica"]
PARENTESCOS = [
    "Mãe", "Pai", "Avó", "Avô", "Tio(a)", "Irmão(ã)", "Padrasto", "Madrasta",
    "Tutor(a) legal", "Cônjuge", "O(a) próprio(a) paciente", "Outro",
]
SEXOS = ["", "Feminino", "Masculino", "Outro", "Prefere não informar"]
TURNOS = ["", "Manhã", "Tarde", "Noite", "Integral"]
FAIXAS_ETARIAS = ["Todas", "Criança (0-11)", "Adolescente (12-17)", "Adulto (18+)"]
UFS = ["", "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
       "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP",
       "SE", "TO"]
DIAS_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
