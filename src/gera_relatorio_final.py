"""
Gera o Relatório Final (Módulo 3) em .docx seguindo o template UFMS Digital.

Números: results/metricas.json (src/analise_preliminar.py), results/metricas_final.json
(src/solucao_final.py) e results/varredura_reclamacoes.json (src/varredura_reclamacoes.py).

PREENCHER: os quatro campos logo abaixo (PENDENTES). Enquanto estiverem como None, o
relatório mostra um marcador amarelo [A PREENCHER: ...] no lugar.

Uso:  python -I src/gera_relatorio_final.py   (a partir da pasta proj-integrador-1)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_COLOR_INDEX
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

# =============================================================================
# PENDENTES: textos que dependem do autor (None = marcador amarelo no relatório)
# =============================================================================
LINK_REPOSITORIO = "https://github.com/rubens-m1/projeto-integrador-1"
LINK_VIDEO = "https://drive.google.com/file/d/199o2dluuhCn9zprluUk_GBA8_xviOZym/view?usp=drive_link"
# Opcional: devolutivas do tutor e dos colegas sobre o relatório parcial (texto corrido).
# None = o item não aparece no relatório.
DEVOLUTIVAS_TUTOR_COLEGAS = None
# Lista de (devolutiva recebida, o que mudou na solução final) para a Tabela de melhorias.
MELHORIAS_POR_DEVOLUTIVA: list[tuple[str, str]] = []
# Apresentação ao público-alvo: para quem, quando, como (on-line/presencial), quantas pessoas,
# e o que disseram (um parágrafo).
APRESENTACAO_PUBLICO = (
    "A solução e a cartilha foram apresentadas ao público-alvo de forma remota, com o compartilhamento "
    "do material em grupos de WhatsApp. Esse canal levou a orientação além do meio acadêmico e alcançou "
    "pessoas de perfis variados, que usam cartão no dia a dia. A devolutiva foi positiva: a cartilha foi "
    "bem aceita e reconhecida como uma forma simples de levar informação sobre o golpe a públicos "
    "diversos, o que mostra que a linguagem e o formato escolhidos cumpriram seu papel. Fora essa "
    "avaliação geral, não houve comentários detalhados nem pedidos de alteração. Por isso, a ausência de "
    "um retorno mais aprofundado é tratada como limitação, e uma escuta mais estruturada fica como "
    "sugestão de continuidade.")

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
OUT = ROOT / "relatorio" / "Relatorio_Final_Modulo3_Rubens.docx"
OUT.parent.mkdir(exist_ok=True)
M = json.load(open(ROOT / "results" / "metricas.json", encoding="utf-8"))
MF = json.load(open(ROOT / "results" / "metricas_final.json", encoding="utf-8"))
V = json.load(open(ROOT / "results" / "varredura_reclamacoes.json", encoding="utf-8"))

FONT = "Arial"
LR, RF, GB = "Regressão Logística", "Random Forest", "Gradient Boosting"
PEND = []  # marcadores ainda não preenchidos (impressos no fim)


# ---------------------------------------------------------------- formatação pt-BR
def n(x, d=2):
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, d=2):
    return f"{n(x, d)}%"


def frac_pct(x, d=1):
    return pct(100 * x, d)


def brl(x):
    return f"R$ {n(x, 0)}"


# ---------------------------------------------------------------- documento
doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
sec.top_margin, sec.left_margin = Cm(3), Cm(3)
sec.bottom_margin, sec.right_margin = Cm(2), Cm(2)

st = doc.styles["Normal"]
st.font.name = FONT
st.font.size = Pt(12)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
st.paragraph_format.line_spacing = 1.5
st.paragraph_format.space_after = Pt(6)

for lvl, size in [(1, 12), (2, 12)]:
    hs = doc.styles[f"Heading {lvl}"]
    hs.font.name = FONT
    hs.font.size = Pt(size)
    hs.font.bold = True
    hs.font.italic = False
    hs.font.color.rgb = RGBColor(0, 0, 0)
    hs.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    rf = hs.element.rPr.rFonts
    for a in ("w:ascii", "w:hAnsi", "w:cs"):
        rf.set(qn(a), FONT)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        rf.attrib.pop(qn(a), None)
    hs.paragraph_format.space_before = Pt(18 if lvl == 1 else 12)
    hs.paragraph_format.space_after = Pt(6)
    hs.paragraph_format.keep_with_next = True
    hs.paragraph_format.line_spacing = 1.5

fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r = fp.add_run()
for tag, txt in [("begin", None), (None, "PAGE"), ("end", None)]:
    if tag:
        el = OxmlElement("w:fldChar")
        el.set(qn("w:fldCharType"), tag)
    else:
        el = OxmlElement("w:instrText")
        el.set(qn("xml:space"), "preserve")
        el.text = txt
    r._r.append(el)
r.font.size = Pt(10)


def link(p, url, texto=None, size=None):
    """Hiperlink clicável (azul, sublinhado)."""
    r_id = p.part.relate_to(url, RT.HYPERLINK, is_external=True)
    h = OxmlElement("w:hyperlink")
    h.set(qn("r:id"), r_id)
    run = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    for tag, val in (("w:color", "1F4E99"), ("w:u", "single")):
        e = OxmlElement(tag); e.set(qn("w:val"), val); rpr.append(e)
    if size:
        e = OxmlElement("w:sz"); e.set(qn("w:val"), str(int(size * 2))); rpr.append(e)
    run.append(rpr)
    t = OxmlElement("w:t"); t.text = texto or url; t.set(qn("xml:space"), "preserve")
    run.append(t)
    h.append(run)
    p._p.append(h)


def runs(p, text, size=None, italic=False):
    """Texto com **negrito**, *itálico*, [[A PREENCHER: ...]] (amarelo) e <<url>> (hiperlink)."""
    for part in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|\[\[[^\]]+\]\]|<<[^>]+>>)", text):
        if not part:
            continue
        if part.startswith("<<"):
            link(p, part[2:-2], size=size)
            continue
        if part.startswith("**"):
            rr = p.add_run(part[2:-2]); rr.bold = True
        elif part.startswith("[["):
            rr = p.add_run(f"[{part[2:-2]}]"); rr.bold = True
            rr.font.highlight_color = WD_COLOR_INDEX.YELLOW
            PEND.append(part[2:-2])
        elif part.startswith("*"):
            rr = p.add_run(part[1:-1]); rr.italic = True
        else:
            rr = p.add_run(part)
        if italic:
            rr.italic = True
        if size:
            rr.font.size = Pt(size)
    return p


def P(text, align="justify", indent=True, size=None, italic=False, space_after=6):
    p = doc.add_paragraph()
    p.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "center": WD_ALIGN_PARAGRAPH.CENTER,
                   "left": WD_ALIGN_PARAGRAPH.LEFT}[align]
    if indent:
        p.paragraph_format.first_line_indent = Cm(1.25)
    p.paragraph_format.space_after = Pt(space_after)
    return runs(p, text, size, italic)


def B(text, level=0):
    p = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(3)
    return runs(p, text)


def H(text, level=1):
    return doc.add_heading(text, level=level)


def campo(rotulo, valor):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    rr = p.add_run(f"{rotulo}: "); rr.bold = True
    runs(p, valor)


def legenda(texto):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.keep_with_next = True
    runs(p, texto, size=10)


def fonte(texto="Fonte: elaborada pelo autor (2026)."):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(10)
    p.paragraph_format.line_spacing = 1.0
    runs(p, texto, size=10)


FIGN = [0]
F_KAGGLE = "Fonte: elaborada pelo autor (2026), com base na Kaggle (CREDIT..., 2026)."
F_AUTOR = "Fonte: elaborada pelo autor (2026)."


def figura(arq, titulo, largura=15.5, fonte_txt=None):
    FIGN[0] += 1
    legenda(f"**Figura {FIGN[0]}** – {titulo}")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_after = Pt(0)
    p.add_run().add_picture(str(FIG / arq), width=Cm(largura))
    fonte(fonte_txt or F_KAGGLE)
    return FIGN[0]


TABN = [0]


def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def tabela(titulo, linhas, larguras, fonte_txt=F_AUTOR, destaque=(), alinhar_esq=(0,), tam=9.5,
           inteira=True):
    """inteira=False deixa a tabela quebrar entre páginas, repetindo o cabeçalho."""
    TABN[0] += 1
    legenda(f"**Tabela {TABN[0]}** – {titulo}")
    t = doc.add_table(rows=len(linhas), cols=len(linhas[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, linha in enumerate(linhas):
        for j, val in enumerate(linha):
            c = t.cell(i, j)
            c.width = Cm(larguras[j])
            c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.keep_with_next = (i < len(linhas) - 1) if inteira else (i == 0)
            p.paragraph_format.space_after = Pt(1)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j in alinhar_esq else WD_ALIGN_PARAGRAPH.CENTER
            runs(p, str(val), size=tam)
            if i == 0:
                for rr in p.runs:
                    rr.bold = True
                shade(c, "DCE6F0")
            elif i in destaque:
                shade(c, "FBEDE5")
    for i, row in enumerate(t.rows):
        trPr = row._tr.get_or_add_trPr()
        trPr.append(OxmlElement("w:cantSplit"))
        if i == 0:
            trPr.append(OxmlElement("w:tblHeader"))
    fonte(fonte_txt)
    return TABN[0]


def pendente(valor, descricao):
    """Texto do autor ou marcador amarelo."""
    return valor if valor else f"[[A PREENCHER: {descricao}]]"


# ---------------------------------------------------------------- atalhos para os números
c, ra, bol = M["classe"], V["reclame_aqui"], V["boletim_consumidor_gov_2025"]
caso, cm = M["caso_real"], M["caso_real_no_modelo"]
mf = MF["modelos"]
mlr, mrf, mgb = mf[LR], mf[RF], mf[GB]
rr_ = MF["resumo_regras"]
gbm = MF["gb_grade"]["melhor"]
REPO = f"<<{LINK_REPOSITORIO}>>" if LINK_REPOSITORIO else "[[A PREENCHER: link do repositório no GitHub]]"

# ================================================================ CABEÇALHO
for txt in ["AVALIAÇÃO DO MÓDULO 3", "RELATÓRIO FINAL DA AÇÃO DE EXTENSÃO"]:
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    rr = p.add_run(txt); rr.bold = True; rr.font.size = Pt(13)
doc.add_paragraph()

campo("Projeto de Extensão", "Programa de Extensão UFMS Digital (95DX7.200525)")
campo("Nome completo", "Rubens Lima Araújo")
campo("Disciplina", "PROJETO INTEGRADOR DE CIÊNCIA DOS DADOS I")
campo("Semestre letivo", "2026/2 - T01")
campo("Curso", "Ciência dos dados")
campo("Público-alvo", "usuários de cartões de crédito e/ou débito, em especial consumidores que pagam "
                      "presencialmente na entrega de pedidos (delivery), e estudantes e interessados em "
                      "Ciência de Dados, Tecnologia da Informação, Matemática, Estatística e áreas correlatas")
campo("Local de realização", "Remoto/On-line")
campo("Título da ação", "**MACHINE LEARNING E INTELIGÊNCIA DE NEGÓCIOS NA DETECÇÃO DE FRAUDES EM "
                        "CARTÕES DE CRÉDITO**")
doc.add_paragraph()

# ================================================================ RESUMO
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
p.paragraph_format.line_spacing = 1.0
rr = p.add_run("Resumo: "); rr.bold = True
runs(p,
     "A ação de extensão tem como tema a aplicação de mineração de dados e *Machine Learning* na "
     "detecção de fraudes em cartões, com recorte no golpe da maquininha, em que o entregador de um "
     "pedido usa uma maquininha para cobrar valores indevidos na porta da casa do cliente. O tema "
     "nasceu de um golpe sofrido pelo autor: três tentativas no débito de um cartão que só tinha a "
     "função crédito foram negadas apenas porque a função não existia, e duas compras no crédito, de "
     "R$ 1.010 e R$ 1.011, foram aprovadas logo depois. O objetivo geral foi aplicar mineração de dados e "
     "*Machine Learning* a uma base pública de transações para identificar padrões de fraude e propor "
     "um modelo de classificação e regras de bloqueio capazes de barrar golpes desse tipo. A metodologia "
     "seguiu o *Design Thinking* (ouvir, criar e implementar), com relato de experiência, pesquisa "
     f"documental em {n(ra['total_reclamacoes_busca'], 0)} reclamações públicas, análise exploratória e "
     f"três modelos em Python, aplicados a {n(M['base']['linhas'], 0)} transações do Kaggle com "
     f"{pct(c['taxa_fraude_pct'])} de fraudes. O público-alvo reúne usuários de cartões e estudantes da "
     f"área de dados. A Regressão Logística foi o modelo final (PR-AUC de {n(mlr['teste_pr_auc'], 3)} no "
     f"teste), à frente do *Gradient Boosting* ({n(mgb['teste_pr_auc'], 3)}) e do Random Forest "
     f"({n(mrf['teste_pr_auc'], 3)}). Sem o histórico das tentativas negadas, a compra do caso real "
     f"recebeu probabilidade de fraude de {frac_pct(cm['prob_sem_contexto_das_recusas'])}; com ele, "
     f"{frac_pct(cm['prob_com_contexto_das_recusas'])}. Um motor de cinco regras barrou "
     f"{rr_['golpes_com_bloqueio']} de {rr_['golpes']} golpes simulados, inclusive o caso real já na "
     f"segunda tentativa, sem bloquear clientes legítimos. Como produtos, a ação entrega uma cartilha "
     "de orientação ao consumidor, um notebook Jupyter documentado e um repositório aberto. A cartilha "
     "foi compartilhada em grupos de WhatsApp e bem aceita por públicos diversos.")
p = doc.add_paragraph(); p.paragraph_format.line_spacing = 1.0
rr = p.add_run("Palavras-chave: "); rr.bold = True
p.add_run("Detecção de Fraudes. Machine Learning. Golpe da Maquininha. Ciência de Dados.")

# ================================================================ INTRODUÇÃO
H("Introdução")
P("A digitalização dos meios de pagamento ampliou o acesso a serviços financeiros e acelerou as "
  "transações, mas também abriu espaço para novas formas de fraude. Segundo a Federação Brasileira de "
  "Bancos (Febraban), os golpes financeiros causaram prejuízo de R$ 10,1 bilhões em 2024 (GOLPES..., "
  "2025). Nesse cenário, estratégias orientadas a dados, que combinam *Machine Learning* e "
  "Inteligência de Negócios, tornaram-se essenciais para equilibrar a experiência do cliente e a "
  "proteção financeira (DUQUE, 2025).")
P("Entre essas fraudes está o golpe da maquininha, também chamado de golpe do entregador ou do "
  "delivery. Nele, o entregador apresenta uma maquininha com o visor danificado ou ilegível, alega um "
  "problema no pagamento e passa valores muito acima do pedido. O cliente digita a senha sem ver o "
  "valor. Em 2020, o Procon-SP registrou queixas que somavam mais de R$ 600 mil em cobranças indevidas "
  "desse tipo (GOLPE..., 2020). Como a compra é presencial, com cartão físico e senha, ela tende a "
  "parecer legítima para os sistemas de segurança, o que torna o golpe difícil de detectar.")
P("A motivação desta ação vem de uma experiência vivida pelo autor, que é formado em Matemática e "
  "atua como estagiário de Ciência de Dados no setor bancário. Ao receber um pedido em casa, durante o "
  "dia, o autor teve o cartão passado cinco vezes na maquininha do entregador. O cartão, emitido pelo "
  "maior banco digital brasileiro, era **apenas de crédito**: a função débito nunca havia sido "
  "contratada, ativada ou usada. Mesmo assim, o golpista tentou cobrar **duas vezes R$ 2.000 e uma vez "
  "R$ 1.000 no débito**. As três tentativas foram negadas, mas **apenas por uma questão de sistema**, "
  "porque a função não existia, e não porque algum mecanismo antifraude reconheceu o risco. Em "
  "seguida, **duas compras no crédito, de R$ 1.010 e R$ 1.011, foram aprovadas**. Os valores quase "
  "idênticos sugerem uma tentativa de escapar de regras de duplicidade.")
P("O autor percebeu o problema logo depois que o entregador foi embora. Com apenas 5% de bateria no "
  "celular, entrou no aplicativo do banco e viu o prejuízo, mas o golpista já tinha ido. As "
  "reclamações pelo atendimento do banco, pelo Reclame Aqui e pelo Procon não resolveram o caso. O "
  "valor só foi devolvido cerca de quatro anos depois, por meio de reclamação ao Banco Central do "
  "Brasil, e sem correção monetária.")
P("O caso mostra uma falha que vai além do modelo estatístico. A recusa técnica (\"função "
  "inexistente\") não foi tratada como sinal de risco para as transações seguintes. Isso indica uma "
  "lacuna de mapeamento entre as áreas de dados, produto e processos: cientistas de dados, "
  "desenvolvedores, analistas de qualidade (QA) e gestores de produto (PO e PM). O foco desta ação é, "
  "portanto, investigar como a Ciência de Dados pode identificar padrões de fraude presencial, como as "
  "tentativas repetidas e a sondagem de valores, e transformá-los em variáveis, modelos e regras de "
  "bloqueio.")
P("O objeto de estudo é uma base pública do Kaggle com "
  f"{n(M['base']['linhas'], 0)} transações e {M['base']['colunas']} variáveis, como valor, canal, "
  "método de autenticação, dispositivo, horário, novas tentativas e indicadores de risco (CREDIT..., "
  "2026). A ação apoia-se em conceitos de mineração de dados, análise exploratória e aprendizado "
  "supervisionado para detecção de anomalias (QUIROZ-VÁZQUEZ, 2025), implementados com a biblioteca "
  "Scikit-learn (PEDREGOSA *et al.*, 2011).")
P("O público-alvo foi escolhido por dois motivos. De um lado, os **usuários de cartões**, sobretudo "
  "quem paga presencialmente em entregas, são as vítimas diretas do golpe e precisam reconhecer os "
  "sinais de alerta e os caminhos de reclamação. De outro, os **estudantes e interessados em Ciência "
  "de Dados** e áreas afins são quem vai construir os sistemas antifraude e podem usar este projeto, "
  "com código aberto e documentado, como referência prática. O caráter extensionista está em devolver "
  "à comunidade tanto o conhecimento técnico quanto a orientação ao consumidor. Este relatório final "
  "apresenta a solução completa e as melhorias feitas em relação à solução inicial do relatório parcial.")

# ================================================================ OBJETIVOS
H("Objetivo geral")
P("Aplicar técnicas de mineração de dados e *Machine Learning* a uma base pública de transações com "
  "cartão para identificar padrões de fraude, com ênfase em fraudes presenciais do tipo golpe da "
  "maquininha, e propor um modelo de classificação e regras de bloqueio capazes de barrar esse tipo de "
  "golpe.")

H("Objetivos específicos")
B("**Identificar** (exploratório) as características das transações fraudulentas na base pública e o "
  "comportamento das transações presenciais (maquininha e aproximação).")
B("**Caracterizar** (descritivo) a sequência de eventos do golpe sofrido pelo autor, traduzindo-a em "
  "variáveis e regras: tentativas em modalidade não contratada, recusas técnicas em sequência, valores "
  "decrescentes e valores quase duplicados.")
B("**Avaliar** (explicativo) modelos de classificação com Python e Scikit-learn, usando métricas "
  "adequadas a classes desbalanceadas (recall, precisão e PR-AUC), e analisar o equilíbrio entre "
  "fraudes barradas e falsos positivos.")
B("**Verificar** (explicativo) se o modelo e as regras propostas teriam barrado o caso real e outros "
  "padrões de golpe, e em qual tentativa.")
B("**Descrever** (descritivo), em linguagem acessível, os sinais de alerta do golpe e os caminhos de "
  "reclamação (SAC, ouvidoria, Procon e Banco Central) para os usuários de cartão.")

# ================================================================ JUSTIFICATIVA
H("Justificativa e delimitação do problema")
P("A pergunta que norteia esta ação é: **como técnicas de mineração de dados e Machine Learning "
  "podem identificar fraudes presenciais com cartão, como o golpe da maquininha, que os sistemas "
  "antifraude ainda deixam passar, mesmo quando há sinais claros, como tentativas repetidas em uma "
  "modalidade que o cliente não possui?**")
P("A **relevância social** está no impacto direto sobre o consumidor. O golpe ocorre na porta de "
  "casa, em segundos, e a vítima só percebe depois que o golpista já foi embora. No caso que motivou "
  "o projeto, o ressarcimento levou cerca de quatro anos e veio sem correção monetária, o que mostra "
  "como o caminho de contestação é longo e desgastante. Isso acontece apesar de o Código de Defesa do "
  "Consumidor prever a responsabilidade do fornecedor por defeitos na prestação do serviço (BRASIL, "
  "1990) e de o Superior Tribunal de Justiça ter sumulado que as instituições financeiras respondem "
  "objetivamente por fraudes praticadas por terceiros no âmbito de operações bancárias (BRASIL, 2012). "
  "Por isso, a ação também orienta o público sobre como agir, inclusive pelo canal de reclamações do "
  "Banco Central (BANCO CENTRAL DO BRASIL, 2026).")
P("A **relevância acadêmica** está em tratar um problema real de classificação com classes muito "
  "desbalanceadas, no qual a acurácia engana e a escolha de métricas e limiares é decisiva "
  "(SAITO; REHMSMEIER, 2015; DAL POZZOLO *et al.*, 2015). O projeto também mostra como o conhecimento "
  "do domínio, vindo de um caso real, pode virar variáveis e regras que melhoram a detecção. Para o "
  "público de estudantes, o repositório e o notebook documentados servem como estudo de caso "
  "completo, do dado bruto à avaliação do modelo.")
P("**Delimitação.** A análise usa uma base pública e didática do Kaggle, que não pertence a nenhuma "
  "instituição específica e cujos valores estão em dólar. A base não tem coluna que separe débito de "
  "crédito, nem identificador de cliente ou data e hora completas. Por isso, o histórico de tentativas "
  "negadas do caso real foi aproximado por variáveis disponíveis, como número de novas tentativas, "
  "transações nas últimas 24 horas, horas desde a última transação e índice de velocidade, e as regras "
  "baseadas em sequência de eventos foram testadas à parte, no caso real e em cenários simulados. "
  "A base também não tem categoria de entrega por aplicativo (delivery) e é sintética: há combinações "
  f"que não existem no mundo real, como {n(M['coerencia_base']['atm_machine_no_canal_online'], 0)} "
  "transações feitas em caixa eletrônico pelo canal on-line. Por isso, ela serve para estudar padrões "
  "gerais de fraude, mas não para medir a frequência do golpe. Essa lacuna é coberta pela pesquisa "
  "documental em reclamações públicas. **Nenhuma instituição é identificada neste trabalho**: o banco "
  "do caso é tratado como o maior banco digital brasileiro, e as reclamações são apresentadas por tipo "
  "de instituição.")

# ================================================================ FUNDAMENTAÇÃO TEÓRICA
H("Fundamentação teórica")
P("**Fraude com cartão e engenharia social presencial.** A detecção de anomalias busca pontos de "
  "dados que fogem do comportamento esperado. No setor financeiro, ela é aplicada para sinalizar "
  "transações suspeitas em tempo real (QUIROZ-VÁZQUEZ, 2025). O golpe da maquininha é um caso de "
  "engenharia social presencial: o cartão é verdadeiro, está nas mãos do titular e a senha é digitada "
  "por ele. Assim, os sinais clássicos de fraude, como cartão clonado, localização distante ou compra "
  "online sem autenticação, não aparecem. O risco está no **contexto**: valores incompatíveis com o "
  "histórico, tentativas repetidas e recusas em sequência (GOLPE..., 2020).")
P("**Mineração de dados e análise exploratória.** A mineração de dados e a análise exploratória "
  "(EDA) permitem extrair relações e visualizar comportamentos em grandes bases estruturadas. Na "
  "detecção de fraudes, a EDA orienta a criação de variáveis e ajuda a entender por que um modelo "
  "erra (DUQUE, 2025).")
P("**Aprendizado supervisionado.** Na classificação supervisionada, o modelo aprende com transações "
  "já rotuladas como fraudulentas ou legítimas e passa a estimar a probabilidade de fraude de novos "
  "registros. Esta ação compara três modelos da biblioteca Scikit-learn (PEDREGOSA *et al.*, 2011). A "
  "**Regressão Logística** é um modelo linear generalizado, interpretável. O **Random Forest** combina "
  "árvores de decisão treinadas em amostras aleatórias dos dados e das variáveis (BREIMAN, 2001). O "
  "**Gradient Boosting** também combina árvores, mas de forma sequencial: cada nova árvore corrige "
  "os erros das anteriores (FRIEDMAN, 2001).")
P("**Classes desbalanceadas.** Em fraude, os casos positivos são raros. Um modelo que classifica tudo "
  "como legítimo teria acurácia alta e seria inútil. Por isso, usam-se recall (fração das fraudes "
  "barradas), precisão (fração dos alertas que são fraudes) e a área sob a curva de "
  "precisão-recall (PR-AUC), que é mais informativa que a curva ROC em bases desbalanceadas (SAITO; "
  "REHMSMEIER, 2015). Técnicas de reamostragem ou de pesos por classe alteram as probabilidades "
  "estimadas, o que exige cuidado na escolha do limiar de decisão (DAL POZZOLO *et al.*, 2015).")
P("**Modelos e regras de negócio.** Na prática, sistemas antifraude combinam modelos estatísticos com "
  "regras determinísticas. As regras cobrem padrões que não devem depender de probabilidade, como "
  "uma transação em uma modalidade que o cliente nunca contratou. O caso que motivou este projeto "
  "mostra o que acontece quando essa camada de regras não converte uma recusa técnica em sinal de "
  "risco.")
P("**Responsabilidade das instituições e canais de reclamação.** O Código de Defesa do Consumidor "
  "estabelece, no art. 14, que o fornecedor de serviços responde, independentemente de culpa, pelos "
  "danos causados por defeitos na prestação do serviço (BRASIL, 1990). A Súmula 479 do STJ aplica esse "
  "entendimento às fraudes e delitos praticados por terceiros em operações bancárias (BRASIL, 2012). "
  "Quando o atendimento comum não resolve, a ouvidoria da instituição deve responder em até dez dias "
  "úteis (CONSELHO MONETÁRIO NACIONAL, 2020), e o cliente ainda pode recorrer ao Banco Central "
  "(BANCO CENTRAL DO BRASIL, 2026).")
P("**Design Thinking e reprodutibilidade.** O *Design Thinking* é uma abordagem de inovação centrada "
  "nas pessoas, que combina empatia com o problema, geração de ideias, prototipação e teste (BROWN, "
  "2008). Nesta ação, suas etapas organizam a metodologia em três passos: ouvir, criar e implementar. "
  "Para que outros possam conferir e reutilizar a análise, ela foi publicada em um notebook Jupyter, "
  "formato que une código, resultados e texto explicativo em um único documento executável (KLUYVER "
  "*et al.*, 2016).")

H("Aplicação das disciplinas estudadas no Projeto Integrador I", 2)
P("O projeto mobilizou conteúdos de disciplinas do curso de Ciência dos Dados cursadas até o 4º "
  "período, em que o Projeto Integrador de Ciência dos Dados I está inserido na matriz curricular "
  "(UNIVERSIDADE FEDERAL DE MATO GROSSO DO SUL, 2025). A Tabela 1 relaciona cada disciplina aos "
  "conteúdos usados e ao ponto do trabalho em que foram aplicados.")
t_disc = tabela(
    "Disciplinas do curso aplicadas no projeto",
    [["Disciplina (período)", "Conteúdos usados", "Aplicação no projeto"],
     ["Algoritmos e Programação I e II (1º e 2º)", "Programação em Python, listas, laços, funções e "
      "arquivos", "Scripts de análise, leitura do CSV e motor de regras R1–R5"],
     ["Estatística e Probabilidade (2º)", "Estatística descritiva, estimação e teste de hipótese",
      "Taxas de fraude, intervalo de confiança de Wilson e teste qui-quadrado por horário"],
     ["Banco de Dados (3º)", "Modelagem de dados", "Tradução do caso real em variáveis (Tabela 2) e "
      "proposta de registrar a recusa técnica como evento"],
     ["Gestão de Inovação e Desenvolvimento de Produtos (3º)", "Prototipagem de ideias e análise de "
      "riscos", "Protótipo de regras, cenários de teste e cartilha"],
     ["Introdução a Ciência de Dados (4º)", "Pandas, NumPy, Jupyter, descoberta de conhecimento e "
      "pré-processamento", "Preparação dos dados e notebook Jupyter do projeto"],
     ["Mineração de Dados (4º)", "Classificação supervisionada, medidas de capacidade preditiva, "
      "seleção de atributos e combinação de classificadores", "Regressão Logística, Random Forest e "
      "Gradient Boosting; PR-AUC; importância por permutação"],
     ["Modelagem e Inferência Estatística (4º)", "Modelos lineares generalizados e seleção de modelos",
      "Regressão Logística e escolha do modelo por validação cruzada"],
     ["Ética, Cidadania e Sociedade (1º)", "Ética, cidadania e direitos", "Anonimização das "
      "instituições, nenhum dado pessoal coletado e orientação ao consumidor"],
     ["Leitura e Produção de Textos (1º)", "Metodologia científica e ética em pesquisa",
      "Pesquisa documental, redação do relatório e referências na ABNT"],
     ["Projeto Integrador de Ciência dos Dados I (4º)", "Ação de extensão, resolução de problemas e "
      "controle de versão", "Ação com o público-alvo e repositório público versionado"]],
    [4.6, 5.4, 6.0], fonte_txt="Fonte: elaborada pelo autor (2026), com base na matriz curricular "
                               "(UNIVERSIDADE FEDERAL DE MATO GROSSO DO SUL, 2025).",
    alinhar_esq=(0, 1, 2), tam=9, inteira=False)

# ================================================================ METODOLOGIA
H("Metodologia")
P("A ação seguiu as etapas do *Design Thinking*, conforme a Figura 1. Todo o código está no "
  f"repositório do projeto ({REPO}) e no notebook Jupyter descrito no Apêndice A, que reproduzem os "
  "números e as figuras deste relatório.")
f_pipe = figura("fig14_pipeline_solucao_final.png",
                "Pipeline da solução final organizado nas etapas do Design Thinking", 16, F_AUTOR)

H("Ouvir e interpretar o contexto", 2)
B("**Contexto:** ação remota, desenvolvida no semestre 2026/2 na disciplina de Projeto Integrador "
  "de Ciência dos Dados I, a partir de um golpe da maquininha sofrido pelo autor ao receber um pedido "
  "em casa.")
B("**Sujeitos:** o próprio autor, como vítima (relato de experiência), e o público-alvo: usuários de "
  "cartões, representados também pelos consumidores que relataram o golpe em plataformas públicas de "
  "reclamação, e estudantes da área de dados. Nenhum dado pessoal de terceiros foi registrado: as "
  "reclamações foram lidas e contadas, e só números agregados são apresentados.")
B("**Coleta das informações iniciais:** (i) relato estruturado do golpe, com a linha do tempo das "
  "cinco tentativas, reconstruída a partir das notificações e do extrato no aplicativo do banco; "
  "(ii) pesquisa documental em fontes públicas sobre o golpe, sobre prejuízos com fraudes e sobre os "
  "direitos do consumidor; (iii) **pesquisa documental em reclamações públicas**, feita à mão no "
  "navegador, sem robôs de raspagem: busca pelo termo "
  f"\"golpe da maquininha\" no Reclame Aqui ({n(ra['total_reclamacoes_busca'], 0)} reclamações), "
  f"agrupamento das {ra['empresas_top']} empresas mais citadas por tipo de instituição e leitura de "
  f"{ra['leitura_qualitativa_n']} relatos sobre o banco do caso; e consulta ao Boletim "
  "Consumidor.gov.br 2025 (BRASIL, 2026); e (iv) leitura do dicionário de variáveis da base do Kaggle "
  "para mapear o que dela se aproxima do caso real (Tabela 2).")

tabela("Tradução do caso real em variáveis e regras",
       [["Sinal observado no caso real", "Variável aproximada na base", "Regra proposta"],
        ["Tentativas no débito, função não contratada", "Não existe na base", "R1: modalidade não contratada"],
        ["3 recusas técnicas em poucos minutos", "cvv_retry_count, txn_count_last_24h",
         "R2: 2 ou mais falhas em 10 min bloqueiam o cartão"],
        ["Valores caindo de R$ 2.000 para R$ 1.000", "velocity_score", "R3: valores decrescentes após recusa"],
        ["R$ 1.010 e R$ 1.011 em sequência", "hours_since_last_txn", "R4: valor quase igual (< 2%)"],
        ["Valores muito acima de um pedido comum", "amount_usd", "R5: valor acima de 5× o ticket médio"],
        ["Maquininha de entregador desconhecido", "channel = POS, is_new_merchant", "Contexto do alerta"],
        ["Compra na casa do cliente, com senha", "distance_from_home_km, auth_method = PIN",
         "Sinais que dão falsa segurança"]],
       [5.2, 5.0, 5.8], alinhar_esq=(0,))

H("Criar e prototipar", 2)
B("**Preparação dos dados:** conversão de seis colunas numéricas gravadas como texto no formato "
  "brasileiro (por exemplo, \"$1.080,71\"), verificação de ausentes e duplicados e medição do "
  "desbalanceamento das classes.")
B("**Análise exploratória quantitativa:** taxas de fraude por canal, categoria, método de "
  "autenticação, hora e número de tentativas, com recorte das transações presenciais "
  "(maquininha e aproximação), que representam o cenário do golpe. Nas faixas horárias, usaram-se "
  "intervalos de confiança de Wilson e o teste qui-quadrado.")
B("**Modelos:** Regressão Logística, Random Forest e *Gradient Boosting* "
  "(HistGradientBoostingClassifier) no Scikit-learn, com codificação *one-hot* das variáveis "
  "categóricas, padronização das numéricas e pesos por classe. Os dados foram divididos em treino "
  f"({n(M['divisao']['treino'], 0)}) e teste ({n(M['divisao']['teste'], 0)}), mantendo a proporção de "
  "fraudes. No treino, usou-se validação cruzada estratificada com 5 partes, com PR-AUC como métrica "
  f"principal. Para o *Gradient Boosting*, testou-se uma grade de {len(MF['gb_grade']['configuracoes'])} "
  "combinações de hiperparâmetros. Na solução final, o modelo é escolhido pela validação cruzada, e "
  "não pelo teste, e o **limiar de decisão** é definido só no treino, com as probabilidades fora da "
  "dobra, como o menor nível de alerta que ainda garante recall de 80%.")
B("**Protótipo de regras:** um motor com cinco regras (R1 a R5 da Tabela 2), que avalia cada "
  "tentativa antes da autorização usando o histórico das tentativas anteriores no mesmo terminal, "
  "em uma janela de 10 minutos.")
B("**Material de orientação:** cartilha de uma página, em linguagem simples, com os sinais de "
  "alerta, os cuidados na hora do pagamento e o passo a passo de reclamação.")

H("Implementar e testar", 2)
B("**Teste do modelo:** avaliação no conjunto de teste, que o modelo não viu no treino, com recall, "
  "precisão, F1, ROC-AUC, PR-AUC e matriz de confusão, além de uma análise de limiares que mostra "
  "quantas fraudes são barradas e quantos clientes legítimos seriam incomodados.")
B("**Teste com o caso real:** a compra aprovada de R$ 1.010 foi montada no formato da base e avaliada "
  "pelos três modelos em duas visões: **sem** o histórico das tentativas negadas, que é o que o "
  "sistema \"vê\" quando a recusa técnica não vira dado, e **com** esse histórico, aproximado pelas "
  "variáveis de tentativas e velocidade. Hipóteses: câmbio de "
  f"R$ {n(cm['cambio_hipotese_brl_por_usd'])} por dólar, horário diurno ({cm['hora_hipotese']}h, já que "
  "o golpe ocorreu durante o dia e a hora exata não foi registrada), cerca de um minuto entre as "
  "tentativas e demais variáveis na mediana da base.")
B(f"**Teste das regras em cenários:** além do caso real, o motor foi aplicado a {rr_['golpes'] - 1} "
  "outros golpes inspirados nos padrões relatados nas reclamações públicas (sondagem de saldo, troca "
  "de modalidade após recusa, \"não passou, passa de novo\" e cobrança única alta) e a "
  f"{rr_['legitimos']} situações de clientes legítimos, para medir os alarmes falsos. Os valores dos "
  "cenários são hipotéticos, exceto no caso real.")
B("**Devolutivas coletadas:** (i) **validação pelo próprio autor, como vítima**, que corrigiu fatos "
  "do caso (função débito nunca contratada, recusas só por regra de sistema, golpe durante o dia) e "
  "originou a regra R1; (ii) **retorno indireto do público-alvo** nas reclamações públicas, que levou "
  "a tratar a categoria restaurantes como limitação, a separar compras presenciais e não presenciais "
  "na análise por horário e a montar os cenários de golpe; " +
  (f"(iii) **devolutivas do tutor e dos colegas** sobre o relatório parcial: {DEVOLUTIVAS_TUTOR_COLEGAS}; e (iv) "
   if DEVOLUTIVAS_TUTOR_COLEGAS else "e (iii) ") +
  "**retorno do público-alvo na apresentação** da solução e da cartilha em grupos de WhatsApp, em que o "
  "material foi bem aceito, descrito na seção de resultados.")
B("**Melhorias indicadas e realizadas:** ajuste do limiar do Random Forest, teste de *Gradient "
  "Boosting*, escolha do modelo pela validação cruzada, ampliação das regras (R5) e teste em cenários, "
  "cartilha ao consumidor e notebook documentado. A Tabela 7 resume o que mudou.")

# ================================================================ RESULTADO: SOLUÇÃO FINAL
H("Resultado: solução final")
P("Os resultados a seguir foram obtidos com a execução do código do projeto e estão organizados nos "
  "três passos da metodologia. Ao fim, a Tabela 7 compara a solução inicial, do relatório parcial, "
  "com a solução final.")

H("Resultado do passo Ouvir: o caso real e a voz do público", 2)
P("A Figura 2 reconstrói o golpe. As três primeiras tentativas foram feitas no débito, uma função "
  "que o cartão não tinha, e foram negadas por regra de sistema. As duas seguintes, no crédito, foram "
  f"aprovadas e somaram **R$ {n(caso['prejuizo_real_brl'])}** de prejuízo. A linha tracejada marca "
  "onde as regras propostas bloqueariam o cartão.")
figura("fig10_caso_real_linha_do_tempo.png", "Linha do tempo do golpe da maquininha sofrido pelo autor", 16,
       "Fonte: elaborada pelo autor (2026), com base no relato e no extrato do aplicativo.")

pt_ = ra["por_tipo"]
bc = ra["banco_do_caso"]
P("**O caso não é isolado.** A busca por \"golpe da maquininha\" no Reclame Aqui retornou "
  f"{n(ra['total_reclamacoes_busca'], 0)} reclamações. As {ra['empresas_top']} empresas mais citadas "
  f"somam {n(ra['reclamacoes_top50'], 0)} delas e foram agrupadas por tipo de instituição "
  f"(Tabela {TABN[0] + 1}). Os bancos e emissores de cartão e as empresas de maquininha concentram "
  f"{pct(pt_['Bancos e emissores de cartão']['pct_top50'] + pt_['Maquininhas e instituições de pagamento']['pct_top50'], 1)} "
  "das reclamações. Os aplicativos de entrega, serviços e transporte, contexto do caso do autor, "
  f"respondem por {pct(pt_['Aplicativos de entrega, serviços e transporte']['pct_top50'], 1)}. O "
  f"banco do caso aparece em {bc['posicao_geral']}º lugar entre todas as empresas, com "
  f"{n(bc['reclamacoes'], 0)} reclamações, e em 1º entre os bancos.")
linhas = [["Tipo de instituição", "Empresas", "Reclamações", "% do total"]]
for t_, v in pt_.items():
    linhas.append([t_, str(v["empresas"]), n(v["reclamacoes"], 0), pct(v["pct_top50"], 1)])
linhas.append(["**Total**", f"**{ra['empresas_top']}**", f"**{n(ra['reclamacoes_top50'], 0)}**", "**100,0%**"])
t_rec = tabela("Reclamações sobre o golpe da maquininha por tipo de instituição (50 empresas mais "
               "citadas)", linhas, [7.4, 2.4, 3.0, 2.6],
               fonte_txt="Fonte: elaborada pelo autor (2026), com base no Reclame Aqui (RECLAME AQUI, 2026).")
P(f"A leitura de {ra['leitura_qualitativa_n']} relatos sobre o banco do caso que citam maquininha, "
  "tentativas e débito mostrou o mesmo padrão do caso do autor: cartão passado várias vezes seguidas, "
  "compra recusada seguida de nova tentativa, uso das funções débito e crédito na mesma sequência e "
  "contestação negada pelo banco. Esses padrões viraram os cenários de teste das regras. Os problemas "
  "mais marcados nas reclamações gerais são cobrança indevida "
  f"({n(ra['problemas_top']['Cobrança indevida'], 0)}) e pedido de estorno "
  f"({n(ra['problemas_top']['Estorno do valor pago'], 0)}). Esses números contam reclamações que "
  "mencionam os termos, não golpes confirmados.")
P("Os dados oficiais apontam na mesma direção. Em 2025, o Consumidor.gov.br finalizou "
  f"{n(bol['reclamacoes_finalizadas'], 0)} reclamações. O segmento de bancos, financeiras e "
  f"administradoras de cartão respondeu por {pct(bol['pct_segmento_bancos_financeiras_cartao'])} "
  "delas, e \"cartão de crédito, cartão de débito e cartão de loja\" foi o assunto mais reclamado do "
  f"país, com {n(bol['assunto_cartao_credito_debito_loja'], 0)} reclamações "
  f"({pct(bol['pct_assunto_cartao'])}) (BRASIL, 2026). O boletim, porém, não separa golpes nem "
  "fraudes presenciais, o que reforça a falta de dados específicos sobre esse tipo de fraude.")

H("Resultado do passo Criar: dados e análise exploratória", 2)
q = M["qualidade"]
P(f"A base tem {n(M['base']['linhas'], 0)} transações e {M['base']['colunas']} variáveis, sem valores "
  f"ausentes ({q['valores_ausentes']}) e sem registros duplicados ({q['linhas_duplicadas']}). Há "
  f"{n(c['fraudes'], 0)} fraudes, ou seja, **{pct(c['taxa_fraude_pct'])}** do total, o que confirma o "
  "forte desbalanceamento. A mediana do valor das fraudes é de "
  f"US$ {n(M['valor_usd']['mediana_fraude'])}, contra US$ {n(M['valor_usd']['mediana_legitima'])} nas "
  f"legítimas (Figura {FIGN[0] + 1}). O valor, isoladamente, separa mal as classes.")
figura("fig04_distribuicao_valor.png", "Distribuição do valor das transações fraudulentas e legítimas", 13.5)

tc = M["taxa_por_canal_pct"]
rp = M["recorte_presencial"]
ta = M["taxa_por_autenticacao_pct"]
P("As transações presenciais têm taxas de fraude **abaixo da média**: "
  f"{pct(tc['POS'])} na maquininha e {pct(tc['Contactless'])} na aproximação, contra "
  f"{pct(tc['Online'])} no canal on-line (Figura {FIGN[0] + 1}). Do mesmo modo, compras com senha (PIN) "
  f"têm taxa de {pct(ta['PIN'])}, contra {pct(ta['No Authentication'])} nas sem autenticação. Ou seja, "
  "no agregado, uma compra presencial com senha **parece segura**, e é exatamente essa aparência que "
  "o golpe da maquininha explora.")
figura("fig02_fraude_por_canal.png", "Taxa de fraude por canal da transação", 13.5)

st_ = M["sinais_tentativas"]
P(f"O cenário muda quando se olham os sinais de tentativas repetidas (Figura {FIGN[0] + 1}). A taxa "
  f"de fraude passa de {pct(st_['cvv_retry_count']['0']['taxa_pct'])} sem novas tentativas para "
  f"{pct(st_['cvv_retry_count']['1']['taxa_pct'])} com uma e "
  f"{pct(st_['cvv_retry_count']['2']['taxa_pct'])} com duas. Também cresce com o número de transações "
  f"nas últimas 24 horas, de {pct(st_['txn_count_last_24h']['0']['taxa_pct'])} (nenhuma) para "
  f"{pct(st_['txn_count_last_24h']['8']['taxa_pct'])} (oito ou mais). No recorte presencial "
  f"({n(rp['n'], 0)} transações), a taxa em estabelecimentos novos para o cliente é de "
  f"{pct(rp['taxa_novo_estabelecimento_pct'])}, contra {pct(rp['taxa_estabelecimento_conhecido_pct'])} "
  "nos já conhecidos. Esses são justamente os sinais presentes no caso real.")
figura("fig05_sinais_tentativas.png", "Taxa de fraude segundo tentativas repetidas e histórico", 16)

tcat = M["taxa_por_categoria_pct"]
hp = M["hora"]["por_grupo"]["Presencial (maquininha e aproximação)"]
hr = M["hora"]["por_grupo"]["Não presencial (on-line e app)"]
P(f"Por horário, a taxa de fraude entre 22h e 5h é de {pct(M['hora']['taxa_noite_22_5_pct'])}, contra "
  f"{pct(M['hora']['taxa_dia_6_21_pct'])} no restante do dia. A Figura {FIGN[0] + 1} separa as "
  "compras presenciais das não presenciais e mostra que o efeito **não** vem do canal on-line: nas "
  f"presenciais, a noite pesa ainda mais ({pct(hp['taxa_noite_22_5_pct'])} contra "
  f"{pct(hp['taxa_dia_6_21_pct'])} de dia) do que nas não presenciais "
  f"({pct(hr['taxa_noite_22_5_pct'])} contra {pct(hr['taxa_dia_6_21_pct'])}), com p < 0,01 no teste "
  "qui-quadrado. A menor taxa está nas compras presenciais entre 12h e 15h "
  f"({pct(hp['faixas']['12-15h']['taxa_pct'])}). Uma compra presencial, com senha e de dia, como a do "
  "caso do autor, é o perfil de **menor risco** da base.")
figura("fig06_fraude_por_hora.png", "Taxa de fraude por faixa horária: compras presenciais e não presenciais", 12.5)
P(f"Entre as categorias, destacam-se corretoras de criptomoedas ({pct(tcat['Crypto Exchange'])}) e "
  f"cartões-presente ({pct(tcat['Gift Cards'])}). A base não tem categoria de entrega por aplicativo. "
  f"A mais próxima, restaurantes, fica em {pct(rp['taxa_restaurantes_pct'])} nas compras presenciais, "
  f"com só {rp['fraudes_restaurantes']} fraudes em {n(rp['n_restaurantes'], 0)} transações. Esse número "
  f"**não** indica que o delivery seja seguro: as reclamações (Tabela {t_rec}) mostram o contrário. A "
  "diferença ilustra a principal limitação da base: ela não registra o contexto do golpe.")

H("Resultado do passo Implementar: modelos", 2)
lin = [["Métrica", LR, RF, GB]]
for rot, f in [("PR-AUC na validação cruzada (5 partes)",
                lambda m: f"{n(m['cv5_pr_auc_media'], 3)} ± {n(m['cv5_pr_auc_dp'], 3)}"),
               ("PR-AUC no teste", lambda m: n(m["teste_pr_auc"], 3)),
               ("ROC-AUC no teste", lambda m: n(m["teste_roc_auc"], 3)),
               ("Recall no limiar 0,5", lambda m: frac_pct(m["limiar_0_5"]["recall"])),
               ("Limiar ajustado no treino (recall ≥ 80%)", lambda m: n(m["limiar_recall80_treino"]["limiar"], 3)),
               ("Recall no limiar ajustado", lambda m: frac_pct(m["limiar_recall80_treino"]["recall"])),
               ("Precisão no limiar ajustado", lambda m: frac_pct(m["limiar_recall80_treino"]["precisao"])),
               ("Transações alertadas no limiar ajustado",
                lambda m: pct(m["limiar_recall80_treino"]["pct_transacoes_alertadas"], 1)),
               ("Falsos positivos no limiar ajustado", lambda m: n(m["limiar_recall80_treino"]["fp"], 0))]:
    lin.append([rot, f(mlr), f(mrf), f(mgb)])
t_mod = tabela(f"Desempenho dos três modelos no conjunto de teste ({n(MF['divisao']['teste'], 0)} transações, "
               f"{MF['divisao']['fraudes_teste']} fraudes)", lin, [6.4, 3.2, 3.2, 3.2])
P(f"A **Regressão Logística** continuou sendo o melhor modelo (Tabela {t_mod}), tanto na validação "
  f"cruzada ({n(mlr['cv5_pr_auc_media'], 3)}) quanto no teste ({n(mlr['teste_pr_auc'], 3)}), cerca de "
  f"{n(mlr['teste_pr_auc'] / MF['taxa_fraude_teste'], 0)} vezes a PR-AUC de um classificador aleatório. As "
  "duas melhorias prometidas no relatório parcial foram feitas. (i) O **limiar do Random Forest** "
  f"foi ajustado no treino: no limiar 0,5, ele barrava só {frac_pct(mrf['limiar_0_5']['recall'])} das "
  f"fraudes; no limiar ajustado ({n(mrf['limiar_recall80_treino']['limiar'], 3)}), passou a barrar "
  f"{frac_pct(mrf['limiar_recall80_treino']['recall'])}. (ii) O **Gradient Boosting** foi testado em "
  f"{len(MF['gb_grade']['configuracoes'])} combinações; a melhor (taxa de aprendizado "
  f"{n(gbm['learning_rate'], 2)}, {gbm['max_leaf_nodes']} folhas por árvore) alcançou PR-AUC de "
  f"{n(mgb['teste_pr_auc'], 3)} no teste, acima do Random Forest, mas abaixo do modelo linear. Na base "
  "sintética, a relação entre as variáveis e a fraude parece ser quase linear, e modelos mais "
  "complexos não trouxeram ganho.")
P(f"O limiar ajustado também foi aplicado à Regressão Logística ({n(mlr['limiar_recall80_treino']['limiar'], 3)}). "
  f"Ele barra {frac_pct(mlr['limiar_recall80_treino']['recall'])} das fraudes do teste e alerta "
  f"{pct(mlr['limiar_recall80_treino']['pct_transacoes_alertadas'], 1)} das transações, contra "
  f"{pct(M['limiares_melhor_modelo']['0.5']['pct_transacoes_alertadas'], 1)} no limiar 0,5. Com isso, "
  f"os falsos positivos caem de {n(mlr['limiar_0_5']['fp'], 0)} para "
  f"{n(mlr['limiar_recall80_treino']['fp'], 0)}, ao custo de {mlr['limiar_0_5']['vp'] - mlr['limiar_recall80_treino']['vp']} "
  f"fraudes a menos barradas. A Figura {FIGN[0] + 1} mostra as curvas precisão-recall dos três modelos.")
figura("fig11_modelos_precisao_recall.png", "Curvas precisão-recall dos três modelos no conjunto de teste", 12.5)

lim = M["limiares_melhor_modelo"]
linhas = [["Limiar", "Recall", "Precisão", "Fraudes barradas", "Falsos positivos", "Transações alertadas"]]
for t_, v in lim.items():
    linhas.append([n(float(t_), 1), frac_pct(v["recall"]), frac_pct(v["precisao"]), str(v["vp"]),
                   n(v["fp"], 0), pct(v["pct_transacoes_alertadas"])])
t_lim = tabela("Efeito do limiar de decisão na Regressão Logística", linhas, [2.0, 2.4, 2.4, 3.0, 3.0, 3.2])
P(f"A Tabela {t_lim} e a Figura {FIGN[0] + 1} mostram o equilíbrio entre bloquear fraudes e incomodar "
  f"clientes. Com limiar de 0,7, o modelo barra {frac_pct(lim['0.7']['recall'])} das fraudes e alerta "
  f"{pct(lim['0.7']['pct_transacoes_alertadas'])} das transações. Com 0,3, barra "
  f"{frac_pct(lim['0.3']['recall'])}, mas alerta {pct(lim['0.3']['pct_transacoes_alertadas'])}. A escolha "
  "depende do custo de cada erro para o banco e para o cliente. Por isso, as regras determinísticas, "
  "que não dependem de limiar, são um complemento importante.")
figura("fig07_limiar_recall_precisao.png", "Recall e precisão da Regressão Logística em função do limiar", 12)
figura("fig08_matriz_confusao.png", "Matriz de confusão da Regressão Logística no limiar 0,5", 8.5)

imp = M["importancia_permutacao_top12"]
top3 = list(imp)[:3]
P(f"Na importância por permutação (Figura {FIGN[0] + 1}), a variável mais relevante foi **{top3[0]}** "
  f"(número de novas tentativas), seguida de {top3[1]} e {top3[2]}. Isso confirma, com dados, a tese do "
  "relato: **tentativas repetidas são o sinal mais forte de fraude** na base analisada.")
figura("fig09_importancia_variaveis.png", "Variáveis mais importantes para a Regressão Logística", 13.5)

crm = MF["caso_real_nos_modelos"]
assert all(not v["alerta_sem_contexto"] and v["alerta_com_contexto"] for v in crm.values()), \
    "o texto diz que os três modelos só alertam com o histórico; revise o parágrafo"
P("**Teste com o caso real.** Avaliada **sem** o histórico das tentativas negadas, a compra aprovada "
  f"de R$ 1.010 (cerca de US$ {n(cm['valor_usd'])}) recebeu probabilidade de fraude de "
  f"**{frac_pct(cm['prob_sem_contexto_das_recusas'])}** na Regressão Logística, mais baixa que a de "
  f"{n(100 - cm['percentil_risco_sem_contexto'], 0)}% das transações do teste. Avaliada **com** esse "
  f"histórico, subiu para **{frac_pct(cm['prob_com_contexto_das_recusas'])}**, acima de "
  f"{n(cm['percentil_risco_com_contexto'], 1)}% das transações. Os outros modelos seguem o mesmo "
  f"padrão: o Random Forest passa de {frac_pct(crm[RF]['prob_sem_contexto'])} para "
  f"{frac_pct(crm[RF]['prob_com_contexto'])}, e o *Gradient Boosting*, de "
  f"{frac_pct(crm[GB]['prob_sem_contexto'])} para {frac_pct(crm[GB]['prob_com_contexto'])}. Nos três, "
  "a compra só gera alerta quando o histórico é considerado. O problema não é a falta de um modelo, e "
  "sim a falta de **dado**: se a recusa técnica não é registrada, nenhum modelo consegue usá-la.")

H("Resultado do passo Implementar: regras em cenários", 2)
cen = MF["cenarios"]
linhas = [["Cenário", "Tentativas", "1º alerta", "Bloqueio", "Perda real", "Perda com bloqueio"]]
for cc in cen:
    golpe = cc["tipo"] == "golpe"
    linhas.append([cc["nome"], str(cc["n_tentativas"]),
                   f"{cc['primeiro_alerta']}ª" if cc["primeiro_alerta"] else "–",
                   f"{cc['primeiro_bloqueio']}ª" if cc["primeiro_bloqueio"] else "–",
                   brl(cc["perda_real_brl"]) if golpe else "–",
                   brl(cc["perda_so_bloqueio_brl"]) if golpe else "–"])
dest = tuple(i + 1 for i, cc in enumerate(cen) if cc["tipo"] == "golpe")
t_cen = tabela("Motor de regras R1–R5 aplicado a cenários de golpe (G) e de clientes legítimos (L)",
               linhas, [5.6, 2.0, 1.9, 1.9, 2.3, 2.6], destaque=dest,
               fonte_txt="Fonte: elaborada pelo autor (2026). Cenários G2 a G5 e L1 a L4 são hipotéticos.",
               tam=9)
P(f"As regras bloquearam {rr_['golpes_com_bloqueio']} dos {rr_['golpes']} golpes simulados (Tabela "
  f"{t_cen} e Figura {FIGN[0] + 1}). No **caso real**, o cartão seria bloqueado na "
  f"**{caso['tentativa_do_bloqueio_proposto']}ª tentativa**, a segunda em uma modalidade não "
  f"contratada, e o prejuízo cairia de R$ {n(caso['prejuizo_real_brl'])} para "
  f"**R$ {n(caso['prejuizo_com_regras_brl'])}**. Somando os {rr_['golpes']} golpes, a perda cairia de "
  f"{brl(rr_['perda_real_total_brl'])} para {brl(rr_['perda_so_bloqueio_total_brl'])} só com os "
  "bloqueios. Se o alerta também retiver a compra até o cliente confirmar no aplicativo, a perda "
  f"seria de {brl(rr_['perda_bloqueio_e_alerta_total_brl'])}. Nenhum cliente legítimo teve o cartão "
  f"bloqueado, e {rr_['legitimos_com_alerta']} das {rr_['legitimos']} situações legítimas receberam um "
  "pedido de confirmação (quem errou a senha e tentou de novo e quem fez uma compra alta planejada), "
  "um incômodo pequeno. O cenário G5, de cobrança única alta, mostra o limite das regras: sem "
  "tentativas anteriores, só há alerta. Nesse caso, a melhor defesa é o consumidor conferir o valor no "
  "visor, como orienta a cartilha.")
figura("fig12_regras_cenarios.png", "Decisão do motor de regras em cada tentativa dos nove cenários", 16,
       "Fonte: elaborada pelo autor (2026).")

H("Resultado do passo Implementar: devolução ao público-alvo", 2)
P("**Cartilha.** A Figura " + str(FIGN[0] + 1) + " apresenta a cartilha \"Golpe da maquininha: sem "
  "visor, sem senha\", que traduz os achados do projeto para o consumidor. Ela reúne os sinais de "
  "alerta vistos no caso real e nas reclamações (visor ilegível, \"não passou, passa de novo\", troca "
  "de débito para crédito), os cuidados na hora do pagamento e o passo a passo de reclamação, do SAC "
  "ao Banco Central. A cartilha também tem uma versão em PDF, pronta para compartilhar.")
P("**Notebook e repositório.** Para o público de estudantes, toda a análise foi reunida em um "
  "notebook Jupyter que explica cada etapa em texto e código e confere, na última seção, se chega aos "
  f"mesmos números deste relatório. O notebook e os scripts estão no repositório público {REPO}. Para "
  "manter a decisão de não identificar instituições, os dados brutos das reclamações, que contêm nomes "
  "de empresas, ficaram de fora; o repositório traz só os números agregados por tipo. O Apêndice A "
  "descreve a estrutura do notebook.")
P("**Apresentação ao público-alvo.** " + pendente(
    APRESENTACAO_PUBLICO, "para quem a solução e a cartilha foram apresentadas, quando, como e quantas "
                          "pessoas; o que disseram e o que mudou a partir disso"))
figura("fig13_cartilha_golpe_maquininha.png", "Cartilha de orientação ao consumidor sobre o golpe da maquininha",
       12.5, F_AUTOR)

H("Melhorias em relação à solução inicial", 2)
mlr0 = M["modelos"][LR]
mrf0 = M["modelos"][RF]
linhas = [["Aspecto", "Solução inicial (Módulo 2)", "Solução final (Módulo 3)", "Origem"],
          ["Random Forest", f"Limiar 0,5: recall de {frac_pct(mrf0['limiar_0_5']['recall'])}",
           f"Limiar ajustado no treino: recall de {frac_pct(mrf['limiar_recall80_treino']['recall'])}",
           "Indicada no parcial"],
          ["Gradient Boosting", "Não testado",
           f"Grade de {len(MF['gb_grade']['configuracoes'])} combinações; PR-AUC {n(mgb['teste_pr_auc'], 3)}",
           "Indicada no parcial"],
          ["Escolha do modelo e do limiar", "Pelo teste; limiar fixo em 0,5",
           "Pela validação cruzada; limiar definido só no treino", "Rigor metodológico"],
          ["Limiar da Regressão Logística",
           f"{pct(lim['0.5']['pct_transacoes_alertadas'], 1)} das transações alertadas",
           f"{pct(mlr['limiar_recall80_treino']['pct_transacoes_alertadas'], 1)} alertadas, recall de "
           f"{frac_pct(mlr['limiar_recall80_treino']['recall'])}", "Equilíbrio fraude × incômodo"],
          ["Regras", "R1–R4, testadas só no caso real",
           f"R1–R5, testadas em {rr_['golpes'] + rr_['legitimos']} cenários (golpe e legítimo)",
           "Reclamações públicas"],
          ["Orientação ao consumidor", "Prevista", "Cartilha em PNG e PDF", "Indicada no parcial"],
          ["Reprodutibilidade", "Scripts Python", "Notebook narrado e repositório público sem nomes",
           "Público de estudantes"],
          ["Divulgação ao público", "Prevista", "Cartilha compartilhada em grupos de WhatsApp e bem aceita",
           "Apresentação ao público-alvo"]]
for dev, mudanca in MELHORIAS_POR_DEVOLUTIVA:
    linhas.append([dev, "–", mudanca, "Devolutiva do tutor/colegas"])
t_mel = tabela("Comparação entre a solução inicial e a solução final", linhas, [3.4, 4.0, 5.4, 3.2],
               alinhar_esq=(0, 1, 2), tam=9)
assert t_mel == 7, f"a Tabela de melhorias virou a Tabela {t_mel}; ajuste as referências no texto"
P(f"Em síntese, a solução final combina: (i) a Regressão Logística com limiar escolhido no treino, que "
  f"barra {frac_pct(mlr['limiar_recall80_treino']['recall'])} das fraudes da base alertando "
  f"{pct(mlr['limiar_recall80_treino']['pct_transacoes_alertadas'], 1)} das transações; (ii) cinco regras "
  "de negócio que transformam a recusa técnica em dado de risco e teriam evitado todo o prejuízo do "
  "caso real; (iii) uma cartilha para o consumidor; e (iv) um notebook e um repositório que permitem "
  "reproduzir e reutilizar toda a análise.")

# ================================================================ CONSIDERAÇÕES FINAIS
H("Considerações finais")
P("Esta ação partiu de um golpe da maquininha sofrido pelo autor para investigar como a Ciência de "
  "Dados pode identificar fraudes presenciais com cartão. Os objetivos foram atingidos. As "
  "características das fraudes e do recorte presencial foram identificadas na base pública; o caso "
  "real foi traduzido em variáveis e regras; três modelos foram avaliados com métricas adequadas a "
  "classes desbalanceadas; verificou-se em que tentativa o caso real e outros golpes seriam barrados; e "
  "os sinais de alerta e os caminhos de reclamação foram descritos em linguagem acessível na cartilha.")
P("O principal resultado confirma o que o relato sugeria e a literatura sobre fraudes aponta: o risco "
  "do golpe está no **contexto**, e não na transação isolada. Na base, as compras presenciais e com "
  "senha parecem seguras, e a compra do caso real, sem histórico, fica entre as de menor risco. As "
  "tentativas repetidas, porém, são o sinal mais forte de fraude, e, quando o histórico de recusas "
  f"entra no modelo, a probabilidade sobe de {frac_pct(cm['prob_sem_contexto_das_recusas'])} para "
  f"{frac_pct(cm['prob_com_contexto_das_recusas'])}. Como apontam Saito e Rehmsmeier (2015) e Dal "
  "Pozzolo *et al.* (2015), em bases desbalanceadas a escolha da métrica e do limiar pesa tanto quanto "
  "a do algoritmo. Aqui, um modelo linear simples superou modelos de árvores mais complexos.")
P("**Contribuições.** Para o público técnico, o projeto mostra que uma recusa técnica deve ser "
  "registrada como evento de risco e oferece regras simples, testadas em cenários, que fecham a "
  "lacuna entre dados, produto e processos. Para os consumidores, oferece uma cartilha prática e "
  "lembra que a lei protege a vítima (BRASIL, 1990; BRASIL, 2012). Para os estudantes, oferece um "
  "estudo de caso completo e reprodutível.")
P("**Limitações.** A base é sintética e não tem modalidade débito/crédito, histórico por cliente nem "
  "categoria de delivery. Por isso, as regras foram testadas em cenários hipotéticos, e não em dados "
  "reais de um emissor. O câmbio e a hora do caso são hipóteses declaradas. As reclamações públicas "
  "foram contadas por busca de texto e não confirmam golpes um a um. O retorno do público-alvo foi "
  "positivo, mas pouco detalhado, o que limita a avaliação do material.")
P("**Impactos na comunidade externa.** A cartilha foi compartilhada em grupos de WhatsApp e bem aceita, "
  "levando orientação sobre o golpe a públicos diversos, além do meio acadêmico. Ela e o repositório "
  "ficam disponíveis para uso livre.")
P("**Trabalhos futuros.** (i) Testar as regras em uma base real, com histórico por cliente e "
  "modalidade, em parceria com uma instituição; (ii) estimar o custo de cada tipo de erro para "
  "escolher o limiar pelo menor custo total; (iii) ampliar a escuta do público com um formulário "
  "anônimo, com consentimento, para colher devolutivas mais detalhadas e estimar a frequência do golpe; "
  "e (iv) levar a cartilha a mais grupos, como associações de bairro e comunidades on-line, e continuar "
  "o trabalho no Projeto Integrador II.")

# ================================================================ VÍDEO
H("Vídeo")
p = doc.add_paragraph()
p.paragraph_format.first_line_indent = Cm(1.25)
runs(p, "Vídeo do checkout de presença do Módulo 3: ")
runs(p, f"<<{LINK_VIDEO}>>" if LINK_VIDEO else "[[A PREENCHER: link do vídeo]]")

# ================================================================ REFERÊNCIAS
H("Referências")
refs = [
    "BANCO CENTRAL DO BRASIL. **Meu BC**: reclamação contra bancos e outras instituições financeiras. "
    "Brasília, DF: BCB, 2026. Disponível em: https://www.bcb.gov.br/meubc. Acesso em: 8 nov. 2026.",
    "BRASIL. Lei nº 8.078, de 11 de setembro de 1990. Dispõe sobre a proteção do consumidor e dá outras "
    "providências. **Diário Oficial da União**: seção 1, Brasília, DF, 12 set. 1990. Disponível em: "
    "https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm. Acesso em: 8 nov. 2026.",
    "BRASIL. Ministério da Justiça e Segurança Pública. Secretaria Nacional do Consumidor. **Boletim "
    "Consumidor.gov.br 2025**. Brasília, DF: Senacon, 2026. Disponível em: "
    "https://www.gov.br/mj/pt-br/assuntos/seus-direitos/consumidor/defesadoconsumidor/Biblioteca/"
    "boletins-1/boletim-consumidor-gov-br-2025-vfinal.pdf. Acesso em: 8 nov. 2026.",
    "BRASIL. Superior Tribunal de Justiça. **Súmula nº 479**. As instituições financeiras respondem "
    "objetivamente pelos danos gerados por fortuito interno relativo a fraudes e delitos praticados por "
    "terceiros no âmbito de operações bancárias. Brasília, DF: STJ, 2012. Disponível em: "
    "https://scon.stj.jus.br/SCON/sumstj/toc.jsp?sumula=479. Acesso em: 8 nov. 2026.",
    "BREIMAN, Leo. Random forests. **Machine Learning**, v. 45, n. 1, p. 5-32, 2001.",
    "BROWN, Tim. Design thinking. **Harvard Business Review**, v. 86, n. 6, p. 84-92, jun. 2008.",
    "CONSELHO MONETÁRIO NACIONAL. **Resolução CMN nº 4.860, de 23 de outubro de 2020**. Dispõe sobre a "
    "constituição e o funcionamento de componente organizacional de ouvidoria pelas instituições "
    "financeiras e demais instituições autorizadas a funcionar pelo Banco Central do Brasil. Brasília, "
    "DF: BCB, 2020. Disponível em: https://www.bcb.gov.br/estabilidadefinanceira/buscanormas. Acesso "
    "em: 15 nov. 2026.",
    "CREDIT card fraud detection 2026. **Kaggle**, 2026. Conjunto de dados publicado pelo usuário "
    "uditjain13. Disponível em: https://www.kaggle.com/datasets/uditjain13/credit-card-fraud-detection-2026. "
    "Acesso em: 9 set. 2026.",
    "DAL POZZOLO, Andrea; CAELEN, Olivier; JOHNSON, Reid A.; BONTEMPI, Gianluca. Calibrating "
    "probability with undersampling for unbalanced classification. *In*: IEEE SYMPOSIUM SERIES ON "
    "COMPUTATIONAL INTELLIGENCE, 2015, Cape Town. **Proceedings** [...]. Piscataway: IEEE, 2015. "
    "p. 159-166. DOI: 10.1109/SSCI.2015.33.",
    "DUQUE, Gabriel. Tecnologia bancária: como a transformação digital está redefinindo o segmento "
    "financeiro. **Blog GIF Consulting**, 5 jun. 2025. Disponível em: "
    "https://gifconsulting.com/blog/tecnologia-bancaria/. Acesso em: 9 set. 2026.",
    "FRIEDMAN, Jerome H. Greedy function approximation: a gradient boosting machine. **The Annals of "
    "Statistics**, v. 29, n. 5, p. 1189-1232, 2001.",
    "GOLPE do entregador causou R$ 600 mil em prejuízo, diz Procon-SP. **Tecnoblog**, 2020. Disponível "
    "em: https://tecnoblog.net/356896/golpe-do-entregador-causou-r-600-mil-em-prejuizo-diz-procon-sp/. "
    "Acesso em: 8 nov. 2026.",
    "GOLPES causaram prejuízo de R$ 10,1 bi em 2024, diz Febraban. **Poder360**, Brasília, DF, 2025. "
    "Disponível em: https://www.poder360.com.br/poder-economia/golpes-causaram-prejuizo-de-r-101-bi-em-2024-diz-febraban/. "
    "Acesso em: 8 nov. 2026.",
    "KLUYVER, Thomas *et al.* Jupyter Notebooks: a publishing format for reproducible computational "
    "workflows. *In*: LOIZIDES, Fernando; SCHMIDT, Birgit (ed.). **Positioning and power in academic "
    "publishing**: players, agents and agendas. Amsterdam: IOS Press, 2016. p. 87-90.",
    "PEDREGOSA, Fabian *et al.* Scikit-learn: machine learning in Python. **Journal of Machine Learning "
    "Research**, v. 12, p. 2825-2830, 2011.",
    "QUIROZ-VÁZQUEZ, Camilo. Aprendizado de máquina para detecção de anomalias. **IBM Think**, 2025. "
    "Disponível em: https://www.ibm.com/br-pt/think/topics/machine-learning-for-anomaly-detection. "
    "Acesso em: 9 set. 2026.",
    "RECLAME AQUI. **Busca por reclamações**: \"golpe da maquininha\". São Paulo: Reclame Aqui, 2026. "
    "Disponível em: https://www.reclameaqui.com.br/busca/?q=golpe+da+maquininha. Acesso em: 8 nov. 2026.",
    "SAITO, Takaya; REHMSMEIER, Marc. The precision-recall plot is more informative than the ROC plot "
    "when evaluating binary classifiers on imbalanced datasets. **PLoS ONE**, v. 10, n. 3, e0118432, "
    "2015. DOI: 10.1371/journal.pone.0118432.",
    "UNIVERSIDADE FEDERAL DE MATO GROSSO DO SUL. Conselho de Graduação. **Resolução nº 1.333-Cograd/UFMS, "
    "de 12 de dezembro de 2025**: anexo – projeto pedagógico do curso de Ciência dos Dados – AGEAD. "
    "Campo Grande: UFMS, 2025. Disponível em: https://agead.ufms.br/files/2026/02/Parcial-Ciencia-de-Dados.pdf. "
    "Acesso em: 15 nov. 2026.",
]
for ref in refs:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_after = Pt(10)
    runs(p, ref)

# ================================================================ APÊNDICE A – NOTEBOOK
doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
H("Apêndice A – Notebook Jupyter do projeto")
P("O notebook **deteccao_fraudes_golpe_maquininha.ipynb** reúne toda a análise em texto e código "
  f"executável. Ele está na pasta notebook/ do repositório {REPO}, em versão já executada (com "
  "gráficos e tabelas) e em HTML, que pode ser aberto em qualquer navegador. Para executá-lo, basta "
  "abrir o arquivo no Jupyter, no VS Code ou no Google Colab, com a base do Kaggle na pasta do "
  f"projeto. A Tabela {TABN[0] + 1} resume sua estrutura.")
tabela("Estrutura do notebook do projeto",
       [["Seção", "Etapa", "O que faz"],
        ["1. Bibliotecas e configuração", "–", "Importa pandas, NumPy, SciPy, Matplotlib e Scikit-learn"],
        ["2. O caso real e a voz do público", "Ouvir", "Linha do tempo do golpe e reclamações agregadas por tipo"],
        ["3. Preparação dos dados", "Criar", "Converte os números em texto, checa ausentes, duplicados e classes"],
        ["4. Análise exploratória", "Criar", "Canal, autenticação, valor, tentativas, recorte presencial e horário"],
        ["5. Modelos", "Implementar", "RL, RF e Gradient Boosting, grade, limiar no treino, importância"],
        ["6. Caso real no modelo", "Implementar", "Probabilidade da compra de R$ 1.010 sem e com as recusas"],
        ["7. Motor de regras R1–R5", "Implementar", "Nove cenários de golpe e de clientes legítimos"],
        ["8. Conferência", "–", "Compara os números do notebook com os do relatório"],
        ["9. Conclusões", "–", "Síntese dos achados e limitações"]],
       [5.0, 2.6, 8.4], alinhar_esq=(0, 2), tam=9)
P("O trecho a seguir, retirado da seção 7 do notebook, mostra o núcleo do motor de regras. Ele "
  "registra cada recusa e usa esse histórico para decidir a tentativa seguinte, que é exatamente o "
  "que faltou no caso real.")
codigo = '''def motor_regras(contratadas, ticket, eventos, janela=10):
    hist, out, bloqueado = [], [], False
    for (minuto, mod, valor, resp) in eventos:
        jan = [h for h in hist if minuto - h[0] <= janela]
        recusas = [h for h in jan if h[3] != APROV]
        r1 = mod not in contratadas                       # modalidade não contratada
        r2 = len(recusas) + int(r1) >= 2                  # 2+ falhas em 10 min
        r3 = bool(recusas) and len(jan) >= 2 and valor < max(h[2] for h in jan)
        r4 = any(abs(valor - h[2]) / h[2] < 0.02 for h in jan)   # quase igual
        r5 = valor > FATOR_TICKET * ticket                # valor atípico
        bloqueado = bloqueado or r2 or (r3 + r4 + r5) >= 2
        ...'''
p = doc.add_paragraph()
p.paragraph_format.line_spacing = 1.0
p.paragraph_format.left_indent = Cm(0.5)
rr = p.add_run(codigo)
rr.font.name = "Consolas"
rr.font.size = Pt(8.5)
rr.element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
fonte("Fonte: elaborado pelo autor (2026).")

doc.save(OUT)
print("OK", OUT, "| figuras:", FIGN[0], "| tabelas:", TABN[0])
if PEND:
    print("PENDENTES (marcadores amarelos):")
    for x in dict.fromkeys(PEND):
        print("  -", x)
