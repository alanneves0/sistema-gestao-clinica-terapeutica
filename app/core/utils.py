"""
=============================================================================
 utils.py — Funções auxiliares (formatação, validação, datas, extenso)
=============================================================================
 Funções "puras" (não dependem de tela nem de banco), usadas em todo lugar:
   • dinheiro:  formatar_moeda(1234.5)      -> "R$ 1.234,50"
                ler_moeda("1.234,50")       -> 1234.5
   • datas:     data_br("2026-09-29")       -> "29/09/2026"
                ler_data("29/09/2026")      -> date(2026, 9, 29)
   • CPF:       validar_cpf / formatar_cpf
   • telefone:  formatar_telefone / telefone_whatsapp
   • extenso:   valor_por_extenso(200)      -> "duzentos reais"
=============================================================================
"""
from __future__ import annotations

import calendar
import re
import unicodedata
from datetime import date, datetime

# ---------------------------------------------------------------------------
# Textos
# ---------------------------------------------------------------------------

def somente_digitos(texto) -> str:
    """Remove tudo que não for número. Ex.: '(81) 9 9767-3217' -> '81997673217'."""
    return re.sub(r"\D", "", str(texto or ""))


def sem_acentos(texto: str) -> str:
    """Remove acentos — usado nas buscas ('Joao' encontra 'João')."""
    normal = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normal if not unicodedata.combining(c)).lower()


def primeiro_nome(nome: str) -> str:
    return (nome or "").strip().split(" ")[0] if nome else ""


# ---------------------------------------------------------------------------
# Dinheiro
# ---------------------------------------------------------------------------

def formatar_moeda(valor, simbolo: bool = True) -> str:
    """Formata número no padrão brasileiro: 1234.5 -> 'R$ 1.234,50'."""
    try:
        valor = float(valor or 0)
    except (TypeError, ValueError):
        valor = 0.0
    texto = f"{abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sinal = "-" if valor < -0.004 else ""
    return f"{sinal}R$ {texto}" if simbolo else f"{sinal}{texto}"


def ler_moeda(texto) -> float:
    """
    Converte o que o usuário digitou em número.
    Aceita: '200', '200,50', '1.200,50', 'R$ 1.200,50', '1200.50'.
    """
    if isinstance(texto, (int, float)):
        return round(float(texto), 2)
    t = str(texto or "").strip().replace("R$", "").replace(" ", "")
    if not t:
        return 0.0
    if "," in t:                       # padrão BR: ponto = milhar, vírgula = decimal
        t = t.replace(".", "").replace(",", ".")
    elif t.count(".") > 1:             # '1.200.000' -> milhar
        t = t.replace(".", "")
    try:
        return round(float(t), 2)
    except ValueError as exc:
        raise ValueError(f"Valor inválido: '{texto}'") from exc


# ---------------------------------------------------------------------------
# Datas
# ---------------------------------------------------------------------------
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]
MESES_ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set",
               "Out", "Nov", "Dez"]


def hoje() -> date:
    return date.today()


def para_date(valor) -> date | None:
    """Aceita date, datetime, 'AAAA-MM-DD' ou 'DD/MM/AAAA' e devolve date."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()[:10]
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def ler_data(texto: str) -> date | None:
    """Lê data digitada 'DD/MM/AAAA' (ou 'DDMMAAAA'). Retorna None se vazio."""
    t = (texto or "").strip()
    if not t:
        return None
    dig = somente_digitos(t)
    if len(dig) == 8 and "/" not in t and "-" not in t:
        t = f"{dig[:2]}/{dig[2:4]}/{dig[4:]}"
    d = para_date(t)
    if d is None:
        raise ValueError(f"Data inválida: '{texto}'. Use o formato DD/MM/AAAA.")
    return d


def data_br(valor) -> str:
    """Converte para 'DD/MM/AAAA' (texto vazio se não houver data)."""
    d = para_date(valor)
    return d.strftime("%d/%m/%Y") if d else ""


def data_iso(valor) -> str | None:
    """Converte para 'AAAA-MM-DD' (formato gravado no banco)."""
    d = para_date(valor)
    return d.isoformat() if d else None


def data_extenso(valor) -> str:
    """29/09/2026 -> '29 de setembro de 2026'."""
    d = para_date(valor)
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}" if d else ""


def mes_ano(valor) -> str:
    """date(2026, 9, 1) -> '09/2026'."""
    d = para_date(valor)
    return d.strftime("%m/%Y") if d else ""


def adicionar_meses(base: date, meses: int, dia_preferido: int | None = None) -> date:
    """
    Soma meses a uma data mantendo o dia de vencimento.
    Se o mês não tiver o dia (ex.: 30 de fevereiro), usa o último dia do mês.
    """
    dia = dia_preferido or base.day
    total = base.month - 1 + meses
    ano = base.year + total // 12
    mes = total % 12 + 1
    ultimo = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(dia, ultimo))


def calcular_idade(nascimento) -> int | None:
    d = para_date(nascimento)
    if not d:
        return None
    h = hoje()
    return h.year - d.year - ((h.month, h.day) < (d.month, d.day))


def faixa_etaria(nascimento) -> str:
    idade = calcular_idade(nascimento)
    if idade is None:
        return "—"
    if idade < 12:
        return "Criança"
    if idade < 18:
        return "Adolescente"
    return "Adulto"


def texto_idade(nascimento) -> str:
    idade = calcular_idade(nascimento)
    if idade is None:
        return "—"
    return f"{idade} ano" if idade == 1 else f"{idade} anos"


# ---------------------------------------------------------------------------
# Documentos e contatos
# ---------------------------------------------------------------------------

def validar_cpf(cpf: str) -> bool:
    """Valida CPF pelos dígitos verificadores (vazio é considerado válido)."""
    n = somente_digitos(cpf)
    if not n:
        return True
    if len(n) != 11 or n == n[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(n[i]) * (tamanho + 1 - i) for i in range(tamanho))
        digito = (soma * 10) % 11 % 10
        if digito != int(n[tamanho]):
            return False
    return True


def formatar_cpf(cpf: str) -> str:
    n = somente_digitos(cpf)
    if len(n) != 11:
        return cpf or ""
    return f"{n[:3]}.{n[3:6]}.{n[6:9]}-{n[9:]}"


def formatar_cep(cep: str) -> str:
    n = somente_digitos(cep)
    return f"{n[:5]}-{n[5:]}" if len(n) == 8 else (cep or "")


def formatar_telefone(tel: str) -> str:
    """'81997673217' -> '(81) 99767-3217'."""
    n = somente_digitos(tel)
    if n.startswith("55") and len(n) in (12, 13):
        n = n[2:]
    if len(n) == 11:
        return f"({n[:2]}) {n[2:7]}-{n[7:]}"
    if len(n) == 10:
        return f"({n[:2]}) {n[2:6]}-{n[6:]}"
    return tel or ""


def telefone_whatsapp(tel: str, ddd_padrao: str = "81") -> str | None:
    """
    Converte o telefone para o formato internacional usado pelo WhatsApp
    (55 + DDD + número). Se o número vier sem DDD, usa o DDD padrão.
    Retorna None se o número for inválido.
    """
    n = somente_digitos(tel)
    if not n:
        return None
    if n.startswith("0"):
        n = n.lstrip("0")
    if len(n) in (8, 9):                       # sem DDD
        n = somente_digitos(ddd_padrao) + n
    if len(n) in (10, 11):                     # com DDD, sem país
        n = "55" + n
    if len(n) in (12, 13) and n.startswith("55"):
        return n
    return None


def validar_email(email: str) -> bool:
    if not email:
        return True
    return re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email.strip()) is not None


# ---------------------------------------------------------------------------
# Valor por extenso (usado nos recibos)
# ---------------------------------------------------------------------------
_UNIDADES = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete",
             "oito", "nove", "dez", "onze", "doze", "treze", "quatorze", "quinze",
             "dezesseis", "dezessete", "dezoito", "dezenove"]
_DEZENAS = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta",
            "setenta", "oitenta", "noventa"]
_CENTENAS = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos",
             "seiscentos", "setecentos", "oitocentos", "novecentos"]


def _ate_999(n: int) -> str:
    """Escreve números de 1 a 999 por extenso."""
    if n == 100:
        return "cem"
    c, resto = divmod(n, 100)
    partes = []
    if c:
        partes.append(_CENTENAS[c])
    if resto:
        if resto < 20:
            partes.append(_UNIDADES[resto])
        else:
            d, u = divmod(resto, 10)
            partes.append(_DEZENAS[d] + (f" e {_UNIDADES[u]}" if u else ""))
    return " e ".join(partes)


def numero_por_extenso(n: int) -> str:
    """Escreve inteiros por extenso (até bilhões). 1600 -> 'mil e seiscentos'."""
    if n == 0:
        return "zero"
    grupos = []
    escalas = [(10**9, "bilhão", "bilhões"), (10**6, "milhão", "milhões"), (1000, "mil", "mil")]
    resto = n
    for divisor, singular, plural in escalas:
        q, resto = divmod(resto, divisor)
        if q:
            if divisor == 1000:
                grupos.append("mil" if q == 1 else f"{_ate_999(q)} mil")
            else:
                grupos.append(f"{_ate_999(q)} {singular if q == 1 else plural}")
    if resto:
        grupos.append(_ate_999(resto))
    if len(grupos) == 1:
        return grupos[0]
    # Regra do "e": usa "e" antes do último grupo se ele for < 100 ou centena redonda
    ultimo_usa_e = resto and (resto < 100 or resto % 100 == 0)
    if ultimo_usa_e:
        return " ".join(grupos[:-1]) + " e " + grupos[-1]
    return " ".join(grupos)


def valor_por_extenso(valor: float) -> str:
    """200.5 -> 'duzentos reais e cinquenta centavos'."""
    valor = round(float(valor or 0), 2)
    reais = int(valor)
    centavos = int(round((valor - reais) * 100))
    partes = []
    if reais:
        texto = numero_por_extenso(reais)
        # "um milhão de reais", "dois milhões de reais"
        sufixo = "real" if reais == 1 else ("de reais" if reais % 10**6 == 0 else "reais")
        partes.append(f"{texto} {sufixo}")
    if centavos:
        partes.append(f"{numero_por_extenso(centavos)} {'centavo' if centavos == 1 else 'centavos'}")
    if not partes:
        return "zero reais"
    return " e ".join(partes)


def normalizar_texto(texto: str) -> str:
    """
    Corrige emojis lidos de caixas de texto da interface (Tk pode devolvê-los
    como 'pares substitutos'). Assim a mensagem chega certa ao WhatsApp.
    """
    try:
        return texto.encode("utf-16", "surrogatepass").decode("utf-16")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return texto
