import os
import re
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    Flowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# CONFIGURAÇÕES DE PASTAS E ARQUIVOS
PASTA_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PASTA_LOGOS = "assets/logos"
LOGO_CABECALHO = "logo_cabecalho.png"
LOGO_RODAPE = "logo_rodape.png"
LOGO_MARCA_DAGUA = "marca_dagua.png"
QRCODE = "qrcode.png"

st.set_page_config(
    page_title="Atualizador de PDF Cadastral",
    page_icon="📄",
    layout="centered"
)

st.markdown("""
    <style>
    .main {
        background-color: #0d1117;
    }
    .stTextArea textarea {
        background-color: #161b22;
        color: #ffffff;
        border: 1px solid #30363d;
    }
    .stTextInput input {
        background-color: #161b22;
        color: #ffffff;
        border: 1px solid #30363d;
    }
    h1, h2, h3 {
        color: #ffffff !important;
    }
    .subtext {
        color: #8b949e;
        text-align: center;
        margin-bottom: 25px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center;'>Atualizador de PDF Cadastral</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtext'>Escolha entre preencher manualmente ou colar os dados da ficha</p>", unsafe_allow_html=True)

def extrair_dados_ficha(texto_ficha):
    dados = {
        "RAZÃO": "",
        "CNPJ": "",
        "SITUAÇÃO ATIVA": "ATIVA",
        "CPF MASTER": "",
    }

    if not texto_ficha.strip():
        return dados

    texto_limpo = texto_ficha.replace("\\", "/")

    # 1. Extração de CNPJ
    match_cnpj = re.search(r"CNPJ[:\s]+([\d./-]+)", texto_limpo, re.IGNORECASE)
    if match_cnpj:
        c_nums = re.sub(r"\D", "", match_cnpj.group(1))
        if len(c_nums) == 14:
            dados["CNPJ"] = f"{c_nums[:2]}.{c_nums[2:5]}.{c_nums[5:8]}/{c_nums[8:12]}-{c_nums[12:]}"
        else:
            dados["CNPJ"] = match_cnpj.group(1).strip()
    else:
        busca_generica = re.search(r"\b(\d{14})\b", texto_limpo)
        if busca_generica:
            c = busca_generica.group(1)
            dados["CNPJ"] = f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}"

    # 2. Extração de Razão Social
    match_razao = re.search(r"RAZ[ÃA]O\s*(?:SOCIAL)?[:\s]+([^\n\r]+)", texto_limpo, re.IGNORECASE)
    if match_razao:
        dados["RAZÃO"] = match_razao.group(1).strip()
    else:
        match_nome = re.search(r"NOME FANTASIA[:\s]+([^\n\r]+)", texto_limpo, re.IGNORECASE)
        if match_nome:
            dados["RAZÃO"] = match_nome.group(1).strip()

    # 3. Extração da Situação
    match_sit = re.search(r"SITUA[ÇC][ÃA]O(?:\s+CADASTRAL)?[:\s]+([^\n\r]+)", texto_limpo, re.IGNORECASE)
    if match_sit:
        dados["SITUAÇÃO ATIVA"] = match_sit.group(1).strip().upper()

    # 4. Extração do CPF Master
    match_cpf_master = re.search(r"(?:CPF\s+USU[ÁA]RIO\s+MASTER|CPF\s+MASTER)[:\s]+([\d.-]+)", texto_limpo, re.IGNORECASE)
    if match_cpf_master:
        cpf_nums = re.sub(r"\D", "", match_cpf_master.group(1))
        if len(cpf_nums) == 11:
            dados["CPF MASTER"] = f"{cpf_nums[:3]}.{cpf_nums[3:6]}.{cpf_nums[6:9]}-{cpf_nums[9:]}"
    else:
        match_cpf_socio = re.search(r"CPF[:\s]+(\d{11}|\d{3}\.\d{3}\.\d{3}-\d{2})", texto_limpo, re.IGNORECASE)
        if match_cpf_socio:
            cpf_nums = re.sub(r"\D", "", match_cpf_socio.group(1))
            if len(cpf_nums) == 11:
                dados["CPF MASTER"] = f"{cpf_nums[:3]}.{cpf_nums[3:6]}.{cpf_nums[6:9]}-{cpf_nums[9:]}"
            else:
                dados["CPF MASTER"] = match_cpf_socio.group(1).strip()

    return dados

class CheckVerde(Flowable):
    def __init__(self, tamanho=10):
        super().__init__()
        self.tamanho = tamanho
        self.width = tamanho
        self.height = tamanho

    def draw(self):
        c = self.canv
        s = self.tamanho
        r = s / 2
        c.saveState()
        c.setFillColor(colors.HexColor("#00A859"))
        c.circle(r, r, r, fill=1, stroke=0)
        c.setStrokeColor(colors.white)
        c.setLineWidth(1.4)
        c.setLineCap(1)
        c.line(s * 0.28, s * 0.48, s * 0.42, s * 0.32)
        c.line(s * 0.42, s * 0.32, s * 0.72, s * 0.68)
        c.restoreState()

class LinhaVertical(Flowable):
    def __init__(self, altura=38, cor="#B0B0B0", largura_linha=1):
        super().__init__()
        self.altura = altura
        self.cor = cor
        self.largura_linha = largura_linha
        self.width = largura_linha
        self.height = altura

    def draw(self):
        c = self.canv
        c.saveState()
        c.setStrokeColor(colors.HexColor(self.cor))
        c.setLineWidth(self.largura_linha)
        c.line(0, 0, 0, self.altura)
        c.restoreState()

def caminho_logo(pasta_script, nome):
    return os.path.join(pasta_script, PASTA_LOGOS, nome)

def carregar_imagem(caminho, largura=None, altura=None):
    if os.path.exists(caminho):
        img = Image(caminho)
        if altura and not largura:
            fator = altura / float(img.imageHeight)
            img.drawWidth = img.imageWidth * fator
            img.drawHeight = altura
        elif largura and not altura:
            fator = largura / float(img.imageWidth)
            img.drawWidth = largura
            img.drawHeight = img.imageHeight * fator
        elif largura and altura:
            img.drawWidth = largura
            img.drawHeight = altura
        return img
    return Spacer(largura or 100, altura or 30)

def adicionar_marca_dagua(canvas, doc):
    caminho = caminho_logo(PASTA_SCRIPT, LOGO_MARCA_DAGUA)
    if not os.path.exists(caminho):
        caminho = caminho_logo(PASTA_SCRIPT, LOGO_RODAPE)
    canvas.saveState()
    try:
        canvas.setFillAlpha(0.05)
        canvas.setStrokeAlpha(0.05)
    except AttributeError:
        pass
    largura_item, altura_item, passo_x, passo_y = 130, 120, 130, 120
    if os.path.exists(caminho):
        row_idx = 0
        for y in range(-20, int(A4[1]) + 70, passo_y):
            offset_x = (row_idx % 2) * (passo_x / 2)
            for x in range(-80, int(A4[0]) + 100, passo_x):
                canvas.drawImage(caminho, x + offset_x, y, width=largura_item, height=altura_item, mask="auto", preserveAspectRatio=True)
            row_idx += 1
    canvas.restoreState()

def gerar_pdf(pasta_script, dados_empresa):
    razao = dados_empresa.get("RAZÃO", "EMPRESA")
    razao_limpa = re.sub(r'[\\/*?:"<>|]', "", razao)
    nome_pdf = f"ATUALIZAÇÃO MODULO TOPAZ - {razao_limpa}.pdf"
    caminho_pdf = os.path.join(pasta_script, nome_pdf)

    doc = SimpleDocTemplate(caminho_pdf, pagesize=A4, rightMargin=45, leftMargin=45, topMargin=45, bottomMargin=45)
    story = []
    styles = getSampleStyleSheet()

    estilo_titulo = ParagraphStyle("Titulo", parent=styles["Heading1"], fontSize=13.5, leading=16, fontName="Helvetica-Bold", textColor=colors.HexColor("#111111"))
    estilo_sub = ParagraphStyle("Sub", parent=styles["Heading2"], fontSize=11, leading=14, fontName="Helvetica-Bold", textColor=colors.HexColor("#222222"))
    estilo_secao = ParagraphStyle("Secao", parent=styles["Normal"], fontSize=10, leading=13, fontName="Helvetica-Bold", textColor=colors.HexColor("#333333"))
    estilo_texto = ParagraphStyle("Texto", parent=styles["Normal"], fontSize=9.5, leading=13.5, textColor=colors.HexColor("#444444"))
    estilo_topico = ParagraphStyle("Topico", parent=styles["Normal"], fontSize=9.5, leading=14, textColor=colors.HexColor("#333333"))
    estilo_qr_legenda = ParagraphStyle("QRLegenda", parent=styles["Normal"], fontSize=8, leading=10, alignment=1, textColor=colors.HexColor("#666666"))

    logo_topo = carregar_imagem(caminho_logo(pasta_script, LOGO_CABECALHO), altura=68)
    linha_divisoria = LinhaVertical(altura=60, cor
