"""
Gera o Relatório Parcial (Módulo 2) em .docx seguindo a estrutura do template UFMS Digital.
Todos os números vêm de results/metricas.json (gerado por src/analise_preliminar.py).

Uso:  python -I src/gera_relatorio.py   (a partir da pasta proj-integrador-1)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
OUT = ROOT / "relatorio" / "Relatorio_Parcial_Modulo2_Rubens.docx"
OUT.parent.mkdir(exist_ok=True)
M = json.load(open(ROOT / "results" / "metricas.json", encoding="utf-8"))
V = json.load(open(ROOT / "results" / "varredura_reclamacoes.json", encoding="utf-8"))

FONT = "Arial"
LR, RF = "Regressão Logística", "Random Forest"


# ---------------------------------------------------------------- formatação pt-BR
def n(x, d=2):
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x, d=2):
    return f"{n(x, d)}%"


def frac_pct(x, d=1):
    return pct(100 * x, d)


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

# Rodapé com número de página (à direita, como no template)
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


def runs(p, text, size=None, italic=False):
    """Texto com **negrito** e *itálico* simples."""
    for part in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*)", text):
        if not part:
            continue
        if part.startswith("**"):
            rr = p.add_run(part[2:-2]); rr.bold = True
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


def figura(arq, titulo, largura=15.5, fonte_txt=None):
    FIGN[0] += 1
    legenda(f"**Figura {FIGN[0]}** – {titulo}")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_after = Pt(0)
    p.add_run().add_picture(str(FIG / arq), width=Cm(largura))
    fonte(fonte_txt or "Fonte: elaborada pelo autor (2026), com base na Kaggle (CREDIT..., 2026).")
    return FIGN[0]


TABN = [0]


def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hexcolor)
    tcPr.append(shd)


def tabela(titulo, linhas, larguras, fonte_txt="Fonte: elaborada pelo autor (2026).", destaque=()):
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
            p.paragraph_format.keep_with_next = i < len(linhas) - 1  # tabela não quebra de página
            p.paragraph_format.space_after = Pt(1)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            runs(p, str(val), size=9.5)
            if i == 0:
                for rr in p.runs:
                    rr.bold = True
                shade(c, "DCE6F0")
            elif i in destaque:
                shade(c, "FBEDE5")
    fonte(fonte_txt)
    return TABN[0]


# ================================================================ CABEÇALHO
for txt in ["AVALIAÇÃO DO MÓDULO 2", "RELATÓRIO PARCIAL DA AÇÃO DE EXTENSÃO"]:
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
c, mlr = M["classe"], M["modelos"][LR]
caso, cm = M["caso_real"], M["caso_real_no_modelo"]
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
p.paragraph_format.line_spacing = 1.0
rr = p.add_run("Resumo: "); rr.bold = True
runs(p,
     "A ação de extensão tem como tema a aplicação de mineração de dados e *Machine Learning* na "
     "detecção de fraudes em cartões, com recorte no chamado golpe da maquininha, em que o entregador "
     "de um pedido usa uma maquininha de cartão para cobrar valores indevidos na porta da casa do "
     "cliente. O tema foi escolhido a partir de um golpe sofrido pelo autor: três tentativas (duas de "
     "R$ 2.000 e uma de R$ 1.000) foram feitas na função débito de um cartão que só tinha a função crédito, e "
     "foram negadas apenas porque a função não existia. Logo depois, duas compras no crédito, de "
     "R$ 1.010 e R$ 1.011, foram aprovadas. O objetivo geral é aplicar técnicas de mineração de dados "
     "e *Machine Learning* a uma base pública de transações com cartão para identificar padrões de "
     "fraude e propor um modelo de classificação e regras de bloqueio capazes de barrar golpes desse "
     "tipo. A metodologia segue as etapas do *Design Thinking* (ouvir, criar e implementar), com relato "
     "de experiência, pesquisa documental em reclamações públicas de consumidores, análise exploratória "
     "e modelos em Python com Scikit-learn, "
     f"aplicados a uma base do Kaggle com {n(M['base']['linhas'], 0)} transações e {pct(c['taxa_fraude_pct'])} "
     f"de fraudes. O público-alvo reúne usuários de cartões e estudantes da área de dados. Nos resultados "
     f"preliminares, a Regressão Logística alcançou recall de {frac_pct(mlr['limiar_0_5']['recall'])} e "
     f"PR-AUC de {n(mlr['teste_pr_auc'], 3)}. A probabilidade de fraude da compra aprovada subiu de "
     f"{frac_pct(cm['prob_sem_contexto_das_recusas'])} para {frac_pct(cm['prob_com_contexto_das_recusas'])} "
     "quando o histórico de tentativas negadas foi considerado. Um protótipo de regras bloquearia o cartão "
     "já na segunda tentativa, evitando todo o prejuízo. Espera-se, como resultado, um modelo documentado, "
     "regras de negócio replicáveis e material de orientação para que consumidores reconheçam e "
     "contestem esse golpe.")
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
  "maior banco digital brasileiro, era **apenas de crédito**: a função débito nunca havia sido contratada, ativada "
  "ou usada. Mesmo assim, o golpista tentou cobrar **duas vezes R$ 2.000 e uma vez R$ 1.000 no "
  "débito**. As três tentativas foram negadas, mas **apenas por uma questão de "
  "sistema**, porque a função não existia, e não porque algum mecanismo antifraude reconheceu o risco. "
  "Em seguida, **duas compras no crédito, de R$ 1.010 e R$ 1.011, foram aprovadas**. Os valores quase "
  "idênticos sugerem uma tentativa de escapar de regras de duplicidade.")
P("O padrão era grosseiro: várias tentativas seguidas, de valor alto, em uma modalidade que o cliente "
  "nem possuía, feitas por um estabelecimento novo para ele. Esse é um sinal claro de fraude que "
  "deveria ter levado ao bloqueio imediato do cartão. O autor percebeu o problema logo depois que o "
  "entregador foi embora. Com apenas 5% de bateria no celular, entrou no aplicativo do banco e viu o "
  "prejuízo, mas o golpista já tinha ido. As reclamações pelo atendimento do banco, pelo Reclame Aqui e "
  "pelo Procon não resolveram o caso. O valor só foi devolvido cerca de quatro anos depois, por meio "
  "de reclamação ao Banco Central do Brasil, e sem correção monetária.")
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
  "à comunidade tanto o conhecimento técnico quanto a orientação ao consumidor.")

# ================================================================ OBJETIVO GERAL
H("Objetivo geral")
P("Aplicar técnicas de mineração de dados e *Machine Learning* a uma base pública de transações com "
  "cartão para identificar padrões de fraude, com ênfase em fraudes presenciais do tipo golpe da "
  "maquininha, e propor um modelo de classificação e regras de bloqueio capazes de barrar esse tipo de "
  "golpe.")

# ================================================================ OBJETIVOS ESPECÍFICOS
H("Objetivos específicos")
B("**Identificar** (exploratório) as características das transações fraudulentas na base pública e o "
  "comportamento das transações presenciais (maquininha e aproximação).")
B("**Caracterizar** (descritivo) a sequência de eventos do golpe sofrido pelo autor, traduzindo-a em "
  "variáveis e regras: tentativas em modalidade não contratada, recusas técnicas em sequência, valores "
  "decrescentes e valores quase duplicados.")
B("**Avaliar** (explicativo) modelos de classificação com Python e Scikit-learn, usando métricas "
  "adequadas a classes desbalanceadas (recall, precisão e PR-AUC), e analisar o equilíbrio entre "
  "fraudes barradas e falsos positivos.")
B("**Verificar** (explicativo) se o modelo e as regras propostas teriam barrado o caso real, e em "
  "qual tentativa.")
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
  "Por isso, a ação também pretende orientar o público sobre como agir, inclusive pelo canal de "
  "reclamações do Banco Central (BANCO CENTRAL DO BRASIL, 2026).")
P("A **relevância acadêmica** está em tratar um problema real de classificação com classes muito "
  "desbalanceadas, no qual a acurácia engana e a escolha de métricas e limiares é decisiva "
  "(SAITO; REHMSMEIER, 2015; DAL POZZOLO *et al.*, 2015). O projeto também mostra como o conhecimento "
  "do domínio, vindo de um caso real, pode virar variáveis e regras que melhoram a detecção. Para o "
  "público de estudantes, o repositório documentado serve como estudo de caso completo, do dado bruto "
  "à avaliação do modelo.")
P("**Delimitação.** A análise usa uma base pública e didática do Kaggle, que não pertence a nenhuma "
  "instituição específica e cujos valores estão em dólar. A base não tem coluna que separe débito de "
  "crédito, nem identificador de cliente ou data e hora completas. Por isso, o histórico de tentativas "
  "negadas do caso real foi aproximado por variáveis disponíveis, como número de novas tentativas, "
  "transações nas últimas 24 horas, horas desde a última transação e índice de velocidade. As regras "
  "baseadas em sequência de eventos foram prototipadas à parte, sobre a linha do tempo do caso real. "
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
  "registros. Esta ação usa dois modelos clássicos da biblioteca Scikit-learn (PEDREGOSA *et al.*, "
  "2011). A **Regressão Logística** é um modelo linear e interpretável. O **Random Forest** é um "
  "conjunto de árvores de decisão treinadas em amostras aleatórias dos dados e das variáveis "
  "(BREIMAN, 2001).")
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
P("**Responsabilidade das instituições.** O Código de Defesa do Consumidor estabelece, no art. 14, "
  "que o fornecedor de serviços responde, independentemente de culpa, pelos danos causados por "
  "defeitos na prestação do serviço (BRASIL, 1990). A Súmula 479 do STJ aplica esse entendimento às "
  "fraudes e delitos praticados por terceiros em operações bancárias (BRASIL, 2012). Isso reforça "
  "que a prevenção de fraudes é parte do serviço prestado pelo banco.")
P("**Design Thinking.** O *Design Thinking* é uma abordagem de inovação centrada nas pessoas, que "
  "combina empatia com o problema, geração de ideias, prototipação e teste (BROWN, 2008). Nesta ação, "
  "suas etapas organizam a metodologia em três passos: ouvir, criar e implementar.")

# ================================================================ METODOLOGIA
H("Metodologia")
P("A ação segue as etapas do *Design Thinking*, conforme a Figura 1. Todo o código está no repositório "
  "do projeto (src/analise_preliminar.py) e pode ser executado de novo para reproduzir os números e "
  "as figuras deste relatório.")
f_pipe = figura("fig01_pipeline_design_thinking.png",
                "Pipeline da solução inicial organizado nas etapas do Design Thinking", 16,
                "Fonte: elaborada pelo autor (2026).")

H("Ouvir e interpretar o contexto", 2)
B("**Contexto:** ação remota, desenvolvida no semestre 2026/2 na disciplina de Projeto Integrador "
  "de Ciência dos Dados I, a partir de um golpe da maquininha sofrido pelo autor ao receber um pedido "
  "em casa.")
ra = V["reclame_aqui"]
B("**Sujeitos:** o próprio autor, como vítima (relato de experiência), e o público-alvo: usuários de "
  "cartões, representados também pelos consumidores que relataram o golpe em plataformas públicas de "
  "reclamação, e estudantes da área de dados. Nenhum dado pessoal de terceiros foi registrado: as "
  "reclamações foram lidas e contadas, e só números agregados são apresentados.")
B("**Coleta das informações iniciais:** (i) relato estruturado do golpe, com a linha do tempo das "
  "cinco tentativas, reconstruída a partir das notificações e do extrato no aplicativo do banco; "
  "(ii) pesquisa documental em fontes públicas sobre o golpe, sobre prejuízos com fraudes e sobre os "
  "direitos do consumidor; (iii) **pesquisa documental em reclamações públicas**: busca pelo termo "
  f"\"golpe da maquininha\" no Reclame Aqui ({n(ra['total_reclamacoes_busca'], 0)} reclamações), "
  f"agrupamento das {ra['empresas_top']} empresas mais citadas por tipo de instituição e leitura de "
  f"{ra['leitura_qualitativa_n']} relatos sobre o banco do caso; e consulta ao Boletim "
  "Consumidor.gov.br 2025 (BRASIL, 2026); e (iv) leitura do dicionário de variáveis da base do Kaggle "
  "para mapear o que dela se aproxima do caso real (Tabela 1).")

tabela("Tradução do caso real em variáveis e regras",
       [["Sinal observado no caso real", "Variável aproximada na base", "Regra proposta (protótipo)"],
        ["Tentativas no débito, função não contratada", "Não existe na base", "R1: modalidade não contratada"],
        ["3 recusas técnicas em poucos minutos", "cvv_retry_count, txn_count_last_24h",
         "R2: 2 ou mais recusas em 10 min bloqueiam o cartão"],
        ["Valores caindo de R$ 2.000 para R$ 1.000", "velocity_score", "R3: valores decrescentes"],
        ["R$ 1.010 e R$ 1.011 em sequência", "hours_since_last_txn", "R4: valor quase duplicado (< 2%)"],
        ["Maquininha de entregador desconhecido", "channel = POS, is_new_merchant", "Contexto do alerta"],
        ["Compra na casa do cliente, com senha", "distance_from_home_km, auth_method = PIN",
         "Sinais que dão falsa segurança"]],
       [5.2, 5.0, 5.8])

H("Criar e prototipar", 2)
B("**Preparação dos dados:** conversão de seis colunas numéricas gravadas como texto no formato "
  "brasileiro (por exemplo, \"$1.080,71\"), verificação de ausentes e duplicados e medição do "
  "desbalanceamento das classes.")
B("**Análise exploratória quantitativa:** taxas de fraude por canal, categoria, método de "
  "autenticação, hora e número de tentativas, com recorte das transações presenciais "
  "(maquininha e aproximação), que representam o cenário do golpe.")
B("**Modelos:** Regressão Logística e Random Forest no Scikit-learn, com codificação *one-hot* das "
  "variáveis categóricas, padronização das numéricas e pesos por classe para compensar o "
  f"desbalanceamento. Os dados foram divididos em treino ({n(M['divisao']['treino'], 0)}) e teste "
  f"({n(M['divisao']['teste'], 0)}), mantendo a proporção de fraudes. No treino, usou-se validação "
  "cruzada estratificada com 5 partes, com PR-AUC como métrica principal.")
B("**Protótipo de regras:** um motor de regras simples (R1 a R4 da Tabela 1), aplicado à linha do "
  "tempo do caso real, para testar a ideia de transformar recusas técnicas em sinal de risco.")

H("Implementar e testar", 2)
B("**Teste do modelo:** avaliação no conjunto de teste, que o modelo não viu no treino, com recall, "
  "precisão, F1, ROC-AUC, PR-AUC e matriz de confusão, além de uma análise de limiares que mostra "
  "quantas fraudes são barradas e quantos clientes legítimos seriam incomodados.")
B("**Teste com o caso real:** a compra aprovada de R$ 1.010 foi montada no formato da base e avaliada "
  "pelo modelo em duas visões. Na primeira, **sem** o histórico das tentativas negadas, que é o que o "
  "sistema \"vê\" quando a recusa técnica não vira dado. Na segunda, **com** esse histórico, "
  "aproximado pelas variáveis de tentativas e velocidade. Hipóteses: câmbio de "
  f"R$ {n(cm['cambio_hipotese_brl_por_usd'])} por dólar, horário diurno ({cm['hora_hipotese']}h, já que "
  "o golpe ocorreu durante o dia e a hora exata não foi registrada), cerca de um minuto entre as "
  "tentativas e demais variáveis na mediana da base.")
B("**Devolutivas:** até a entrega deste relatório parcial, a solução inicial ainda não havia recebido "
  "devolutivas formais do tutor nem dos colegas. Elas serão incorporadas ao relatório final. Nesta "
  "etapa, as devolutivas vieram de duas fontes. (i) **Validação pelo próprio autor, como vítima:** a "
  "linha do tempo e as regras foram conferidas com o relato e o extrato. Essa conferência corrigiu "
  "pontos importantes: a função débito nunca foi contratada, as três tentativas no débito foram negadas "
  "só por regra de sistema, e não pelo antifraude, e o golpe ocorreu durante o dia. Também levou à "
  "regra R1, de modalidade não contratada. (ii) **Retorno indireto do público-alvo:** as reclamações "
  "públicas mostraram que o padrão do caso se repete, com tentativas seguidas, recusa seguida de nova "
  "tentativa e contestação negada. Mostraram também que a entrega por aplicativo, ausente da base, é "
  "um dos contextos mais citados do golpe. Por isso, a categoria restaurantes passou a ser tratada "
  "como limitação, e a análise por horário passou a separar as compras presenciais das não "
  "presenciais. Está prevista a apresentação dos resultados e do material de orientação ao "
  "público-alvo.")
B("**Melhorias já indicadas:** ajustar o limiar do Random Forest, testar modelos de *gradient "
  "boosting*, buscar uma base com histórico por cliente e modalidade (débito e crédito), montar um "
  "painel no Power BI e produzir uma cartilha sobre o golpe.")

# ================================================================ RESULTADOS PRELIMINARES
H("Resultados preliminares: solução inicial")
P("Os resultados a seguir foram obtidos com a execução do código do projeto e estão organizados nos "
  "três passos da metodologia.")

H("Resultado do passo Ouvir: o caso real", 2)
P("A Figura 2 reconstrói o golpe. As três primeiras tentativas foram feitas no débito, uma função "
  "que o cartão não tinha, e foram negadas por regra de sistema. As duas seguintes, no crédito, foram "
  f"aprovadas e somaram **R$ {n(caso['prejuizo_real_brl'])}** de prejuízo. A linha tracejada marca "
  "onde o protótipo de regras teria bloqueado o cartão.")
f_caso = figura("fig10_caso_real_linha_do_tempo.png",
                "Linha do tempo do golpe da maquininha sofrido pelo autor", 16,
                "Fonte: elaborada pelo autor (2026), com base no relato e no extrato do aplicativo.")

linhas = [["Tentativa", "Modalidade", "Valor (R$)", "Resposta real", "Regras acionadas", "Decisão proposta"]]
for e in caso["eventos"]:
    ac = [k.split("_")[0] for k in ("R1_modalidade_nao_contratada", "R2_recusas_tecnicas_em_sequencia",
                                     "R3_valores_decrescentes", "R4_valor_quase_duplicado") if e[k]]
    linhas.append([f"{e['tentativa']}ª", e["modalidade"], n(e["valor_brl"]),
                   e["resposta_real"].replace(" - função débito inexistente", " (função inexistente)"),
                   ", ".join(ac) or "–", e["decisao_proposta"].capitalize()])
tabela("Caso real avaliado pelo protótipo de regras", linhas, [1.7, 2.0, 2.0, 3.6, 2.6, 3.4],
       destaque=(4, 5))
P(f"Com as regras, o cartão seria bloqueado na **{caso['tentativa_do_bloqueio_proposto']}ª tentativa**, "
  "a segunda feita em uma modalidade não contratada. O prejuízo cairia de "
  f"R$ {n(caso['prejuizo_real_brl'])} para **R$ {n(caso['prejuizo_com_regras_brl'])}**. Nenhuma "
  "dessas regras exige um modelo complexo, apenas que a recusa técnica seja registrada e usada como "
  "sinal de risco.")

pt_ = ra["por_tipo"]
bc = ra["banco_do_caso"]
bol = V["boletim_consumidor_gov_2025"]
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
linhas.append(["**Total**", f"**{ra['empresas_top']}**", f"**{n(ra['reclamacoes_top50'], 0)}**",
               "**100,0%**"])
t_rec = tabela("Reclamações sobre o golpe da maquininha por tipo de instituição (50 empresas mais "
               "citadas)", linhas, [7.4, 2.4, 3.0, 2.6],
               fonte_txt="Fonte: elaborada pelo autor (2026), com base no Reclame Aqui (RECLAME AQUI, 2026).")
P(f"A leitura de {ra['leitura_qualitativa_n']} relatos sobre o banco do caso que citam maquininha, "
  "tentativas e débito mostrou o mesmo padrão do caso do autor: cartão passado várias vezes seguidas, "
  "compra recusada seguida de nova tentativa, uso das funções débito e crédito na mesma sequência e "
  "contestação negada pelo banco. Os problemas mais marcados nas reclamações gerais são cobrança "
  f"indevida ({n(ra['problemas_top']['Cobrança indevida'], 0)}) e pedido de estorno "
  f"({n(ra['problemas_top']['Estorno do valor pago'], 0)}). Esses números contam reclamações que "
  "mencionam os termos, não golpes confirmados, e o próprio site substitui a palavra \"golpe\" por "
  "uma marca de edição nos títulos, o que limita a busca.")
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
  "legítimas (Figura 3). O valor, isoladamente, separa mal as classes.")
figura("fig04_distribuicao_valor.png", "Distribuição do valor das transações fraudulentas e legítimas", 13.5)

tc = M["taxa_por_canal_pct"]
rp = M["recorte_presencial"]
ta = M["taxa_por_autenticacao_pct"]
P("Um achado importante é que as transações presenciais têm taxas de fraude **abaixo da média**: "
  f"{pct(tc['POS'])} na maquininha e {pct(tc['Contactless'])} na aproximação, contra "
  f"{pct(tc['Online'])} no canal on-line (Figura 4). Do mesmo modo, compras com senha (PIN) têm "
  f"taxa de {pct(ta['PIN'])}, contra {pct(ta['No Authentication'])} nas sem autenticação. Ou seja, "
  "no agregado, uma compra presencial com senha **parece segura**, e é exatamente essa aparência que "
  "o golpe da maquininha explora.")
figura("fig02_fraude_por_canal.png", "Taxa de fraude por canal da transação", 13.5)

st_ = M["sinais_tentativas"]
P("O cenário muda quando se olham os sinais de tentativas repetidas (Figura 5). A taxa de fraude "
  f"passa de {pct(st_['cvv_retry_count']['0']['taxa_pct'])} sem novas tentativas para "
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
  f"{pct(M['hora']['taxa_dia_6_21_pct'])} no restante do dia. Uma hipótese seria que esse efeito "
  "viesse do canal on-line, com fraudes feitas enquanto as vítimas dormem. A Figura 6 separa as "
  "compras presenciais das não presenciais e mostra que **não é isso**: nas presenciais, o efeito da "
  f"noite é ainda maior ({pct(hp['taxa_noite_22_5_pct'])} à noite contra "
  f"{pct(hp['taxa_dia_6_21_pct'])} de dia) do que nas não presenciais "
  f"({pct(hr['taxa_noite_22_5_pct'])} contra {pct(hr['taxa_dia_6_21_pct'])}). As duas diferenças são "
  "estatisticamente significativas (teste qui-quadrado, p < 0,01). A menor taxa da Figura 6 está "
  f"nas compras presenciais entre 12h e 15h ({pct(hp['faixas']['12-15h']['taxa_pct'])}). Ou seja, "
  "uma compra presencial, com senha e durante o dia, como a do caso do autor, é o perfil de **menor "
  "risco** da base. Um modelo treinado com esses dados tende a aprová-la, e o alerta só poderia vir "
  "da sequência de recusas.")
figura("fig06_fraude_por_hora.png",
       "Taxa de fraude por faixa horária: compras presenciais e não presenciais", 12.5)
P(f"Entre as categorias, destacam-se corretoras de criptomoedas ({pct(tcat['Crypto Exchange'])}) e "
  f"cartões-presente ({pct(tcat['Gift Cards'])}). A base não tem categoria de entrega por aplicativo. "
  f"A mais próxima, restaurantes, fica em {pct(tcat['Restaurants'])} no total e em "
  f"{pct(rp['taxa_restaurantes_pct'])} nas compras presenciais, mas são só "
  f"{rp['fraudes_restaurantes']} fraudes em {n(rp['n_restaurantes'], 0)} transações, e a base é "
  "sintética. Esse número **não** indica que o delivery seja seguro. As reclamações públicas "
  f"(Tabela {t_rec}) mostram o contrário: os aplicativos de entrega e serviços estão entre os contextos "
  "mais citados do golpe. A diferença ilustra a principal limitação da base: ela não registra o "
  "contexto em que o golpe acontece.")

H("Resultado do passo Implementar: modelos e testes", 2)
mrf = M["modelos"][RF]
linhas = [["Métrica", LR, RF]]
for rot, f in [("PR-AUC média na validação cruzada (5 partes)",
                lambda m: f"{n(m['cv5_pr_auc_media'], 3)} ± {n(m['cv5_pr_auc_dp'], 3)}"),
               ("PR-AUC no teste", lambda m: n(m["teste_pr_auc"], 3)),
               ("ROC-AUC no teste", lambda m: n(m["teste_roc_auc"], 3)),
               ("Recall (limiar 0,5)", lambda m: frac_pct(m["limiar_0_5"]["recall"])),
               ("Precisão (limiar 0,5)", lambda m: frac_pct(m["limiar_0_5"]["precisao"])),
               ("F1 (limiar 0,5)", lambda m: n(m["limiar_0_5"]["f1"], 3)),
               ("Fraudes barradas / não barradas",
                lambda m: f"{m['limiar_0_5']['vp']} / {m['limiar_0_5']['fn']}"),
               ("Falsos positivos", lambda m: n(m["limiar_0_5"]["fp"], 0))]:
    linhas.append([rot, f(mlr), f(mrf)])
t_mod = tabela(f"Desempenho dos modelos no conjunto de teste ({n(M['divisao']['teste'], 0)} transações, "
               f"{M['divisao']['fraudes_teste']} fraudes)", linhas, [7.0, 4.5, 4.5])
P(f"A **Regressão Logística** teve o melhor desempenho (Tabela {t_mod}): PR-AUC de {n(mlr['teste_pr_auc'], 3)} "
  f"no teste, cerca de {n(mlr['teste_pr_auc'] / (c['taxa_fraude_pct'] / 100), 0)} vezes a de um "
  f"classificador aleatório (que seria igual à taxa de fraude, {n(c['taxa_fraude_pct'] / 100, 3)}). "
  f"No limiar de 0,5, barrou {mlr['limiar_0_5']['vp']} das {M['divisao']['fraudes_teste']} fraudes. "
  f"O Random Forest teve ROC-AUC parecida ({n(mrf['teste_roc_auc'], 3)}), mas, no limiar de 0,5, "
  f"barrou só {mrf['limiar_0_5']['vp']} fraude. Suas probabilidades ficam concentradas em valores "
  "baixos, e o limiar padrão não serve para ele. Esse ajuste fica como melhoria para a próxima etapa "
  "(DAL POZZOLO *et al.*, 2015).")

lim = M["limiares_melhor_modelo"]
linhas = [["Limiar", "Recall", "Precisão", "Fraudes barradas", "Falsos positivos", "Transações alertadas"]]
for t_, v in lim.items():
    linhas.append([n(float(t_), 1), frac_pct(v["recall"]), frac_pct(v["precisao"]), str(v["vp"]),
                   n(v["fp"], 0), pct(v["pct_transacoes_alertadas"])])
t_lim = tabela("Efeito do limiar de decisão na Regressão Logística", linhas, [2.0, 2.4, 2.4, 3.0, 3.0, 3.2])
P(f"A Tabela {t_lim} e a Figura 7 mostram o equilíbrio entre bloquear fraudes e incomodar clientes, citado "
  f"no planejamento do Módulo 1. Com limiar de 0,7, o modelo barra {frac_pct(lim['0.7']['recall'])} "
  f"das fraudes e alerta {pct(lim['0.7']['pct_transacoes_alertadas'])} das transações. Com 0,3, "
  f"barra {frac_pct(lim['0.3']['recall'])}, mas alerta {pct(lim['0.3']['pct_transacoes_alertadas'])}. "
  "A escolha depende do custo de cada erro para o banco e para o cliente. Por isso, as regras "
  "determinísticas, que não dependem de limiar, são um complemento importante.")
figura("fig07_limiar_recall_precisao.png", "Recall e precisão da Regressão Logística em função do limiar", 13.5)
figura("fig08_matriz_confusao.png", "Matriz de confusão da Regressão Logística no limiar 0,5", 8.5)

imp = M["importancia_permutacao_top12"]
top3 = list(imp)[:3]
P(f"Na importância por permutação (Figura 9), a variável mais relevante foi **{top3[0]}** (número de "
  f"novas tentativas), seguida de {top3[1]} e {top3[2]}. Isso confirma, com dados, a tese do relato: "
  "**tentativas repetidas são o sinal mais forte de fraude** na base analisada.")
figura("fig09_importancia_variaveis.png", "Variáveis mais importantes para a Regressão Logística", 13.5)

P("**Teste com o caso real.** Avaliada **sem** o histórico das tentativas negadas, a compra aprovada "
  f"de R$ 1.010 (cerca de US$ {n(cm['valor_usd'])}) recebeu probabilidade de fraude de "
  f"**{frac_pct(cm['prob_sem_contexto_das_recusas'])}**, mais baixa que a de "
  f"{n(100 - cm['percentil_risco_sem_contexto'], 0)}% das transações do teste. Para o modelo, ela "
  "parecia uma compra comum: presencial, com senha, perto de casa e durante o dia. Avaliada **com** esse histórico, a "
  f"probabilidade subiu para **{frac_pct(cm['prob_com_contexto_das_recusas'])}**, acima de "
  f"{n(cm['percentil_risco_com_contexto'], 1)}% das transações do teste. O resultado mostra que o "
  "problema não é a falta de um modelo, e sim a falta de **dado**: se a recusa técnica não é "
  "registrada como evento de risco, nenhum modelo consegue usá-la.")

P("**Síntese da solução inicial.** A solução inicial combina três partes: (i) um modelo de "
  "Regressão Logística com limiar ajustável, que já barra a maioria das fraudes da base; (ii) quatro "
  "regras de negócio derivadas do caso real, que teriam evitado todo o prejuízo; e (iii) um "
  "repositório documentado que pode ser reproduzido. Para o relatório final, estão previstos o ajuste "
  "dos modelos baseados em árvores, um painel no Power BI e uma cartilha sobre o golpe da maquininha, com os sinais de alerta (\"sem visor, sem senha\") e os "
  "caminhos de reclamação, do SAC até o Banco Central.")

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
    "GOLPE do entregador causou R$ 600 mil em prejuízo, diz Procon-SP. **Tecnoblog**, 2020. Disponível "
    "em: https://tecnoblog.net/356896/golpe-do-entregador-causou-r-600-mil-em-prejuizo-diz-procon-sp/. "
    "Acesso em: 8 nov. 2026.",
    "GOLPES causaram prejuízo de R$ 10,1 bi em 2024, diz Febraban. **Poder360**, Brasília, DF, 2025. "
    "Disponível em: https://www.poder360.com.br/poder-economia/golpes-causaram-prejuizo-de-r-101-bi-em-2024-diz-febraban/. "
    "Acesso em: 8 nov. 2026.",
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
]
for ref in refs:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_after = Pt(10)
    runs(p, ref)

doc.save(OUT)
print("OK", OUT, "figuras:", FIGN[0], "tabelas:", TABN[0])
