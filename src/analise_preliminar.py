"""
Análise preliminar - Projeto Integrador de Ciência dos Dados I (UFMS Digital)
MACHINE LEARNING E INTELIGÊNCIA DE NEGÓCIOS NA DETECÇÃO DE FRAUDES EM CARTÕES DE CRÉDITO

Etapas cobertas (Relatório Parcial - Módulo 2):
  1. Preparação e tratamento dos dados
  2. Análise exploratória, com recorte de transações presenciais (golpe da maquininha)
  3. Modelos baseline (Scikit-learn) e análise de limiar
  4. Teste do caso real (golpe da maquininha) no modelo e num protótipo de regras

Uso:  python -I src/analise_preliminar.py   (a partir da raiz do repositório)
Saídas: figures/*.png e results/metricas.json
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED = 42
ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "Base de Dados - Projeto Integrador - credit_card_fraud_2026.csv"
FIG = ROOT / "figures"
RES = ROOT / "results"
FIG.mkdir(exist_ok=True)
RES.mkdir(exist_ok=True)

# Paleta: azul = legítima, laranja = fraude
C_LEG, C_FRA, C_NEU = "#2E5E8C", "#D9622B", "#8A8F98"
plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 200, "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.titlesize": 11,
})

R: dict = {}  # todos os números que vão para o relatório

# ---------------------------------------------------------------------------
# 1. Preparação e tratamento dos dados
# ---------------------------------------------------------------------------
raw = pd.read_csv(CSV)
R["base"] = {"linhas": int(raw.shape[0]), "colunas": int(raw.shape[1])}

NUM_TXT = ["amount_usd", "hours_since_last_txn", "distance_from_home_km",
           "account_balance_usd", "velocity_score", "merchant_risk_score"]


def br_to_float(s: pd.Series) -> pd.Series:
    """Converte texto no formato '$1.080,71' / '13,54' para float."""
    return (s.astype(str).str.replace("$", "", regex=False)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False).astype(float))


df = raw.copy()
for c in NUM_TXT:
    df[c] = br_to_float(df[c])

R["qualidade"] = {
    "colunas_texto_convertidas": NUM_TXT,
    "valores_ausentes": int(df.isna().sum().sum()),
    "linhas_duplicadas": int(df.drop(columns="transaction_id").duplicated().sum()),
    "ids_duplicados": int(df["transaction_id"].duplicated().sum()),
}
n_fraud = int(df["is_fraud"].sum())
R["classe"] = {"fraudes": n_fraud, "legitimas": int(len(df) - n_fraud),
               "taxa_fraude_pct": round(100 * n_fraud / len(df), 2)}
R["valor_usd"] = {
    "mediana_legitima": round(df.loc[df.is_fraud == 0, "amount_usd"].median(), 2),
    "mediana_fraude": round(df.loc[df.is_fraud == 1, "amount_usd"].median(), 2),
    "p95_geral": round(df["amount_usd"].quantile(0.95), 2),
    "max": round(df["amount_usd"].max(), 2),
}

# ---------------------------------------------------------------------------
# 2. Análise exploratória
# ---------------------------------------------------------------------------
TRAD = {"Online": "Online", "POS": "POS (maquininha)", "Contactless": "Aproximação",
        "In-App": "No app", "ATM": "Caixa eletrônico"}


def taxa(col: str) -> pd.DataFrame:
    t = df.groupby(col)["is_fraud"].agg(["mean", "sum", "count"])
    t["mean"] *= 100
    return t.sort_values("mean", ascending=False)


def barh_taxa(t: pd.DataFrame, titulo: str, arq: str, rotulos=None, destaque=()):
    fig, ax = plt.subplots(figsize=(6.4, 0.42 * len(t) + 1.1))
    labels = [rotulos.get(i, i) if rotulos else str(i) for i in t.index]
    cores = [C_FRA if i in destaque else C_LEG for i in t.index]
    ax.barh(labels[::-1], t["mean"].values[::-1], color=cores[::-1])
    for y, (v, n) in enumerate(zip(t["mean"].values[::-1], t["count"].values[::-1])):
        ax.text(v + 0.05, y, f"{v:.2f}%  (n={n:,})".replace(",", "."), va="center", fontsize=8)
    ax.axvline(R["classe"]["taxa_fraude_pct"], color=C_NEU, ls="--", lw=1)
    ax.text(R["classe"]["taxa_fraude_pct"], -0.85, f" média geral ({R['classe']['taxa_fraude_pct']:.2f}%)"
            .replace(".", ","), color=C_NEU, fontsize=8)
    ax.set_ylim(-1.1, len(t) - 0.5)
    ax.set_xlabel("Taxa de fraude (%)")
    ax.set_title(titulo)
    ax.set_xlim(0, t["mean"].max() * 1.45)
    fig.tight_layout()
    fig.savefig(FIG / arq)
    plt.close(fig)


t_canal = taxa("channel")
barh_taxa(t_canal, "Taxa de fraude por canal da transação", "fig02_fraude_por_canal.png",
          rotulos=TRAD, destaque=("POS", "Contactless"))
t_cat = taxa("merchant_category")
barh_taxa(t_cat, "Taxa de fraude por categoria do estabelecimento", "fig03_fraude_por_categoria.png",
          destaque=("Restaurants",))
t_auth = taxa("auth_method")
t_dev = taxa("device_type")
R["taxa_por_canal_pct"] = t_canal["mean"].round(2).to_dict()
R["taxa_por_categoria_pct"] = t_cat["mean"].round(2).to_dict()
R["taxa_por_autenticacao_pct"] = t_auth["mean"].round(2).to_dict()
R["taxa_por_dispositivo_pct"] = t_dev["mean"].round(2).to_dict()

# Valor: distribuição (escala log)
fig, ax = plt.subplots(figsize=(6.4, 3.4))
bins = np.logspace(np.log10(max(df.amount_usd.min(), 0.5)), np.log10(df.amount_usd.max()), 50)
ax.hist(df.loc[df.is_fraud == 0, "amount_usd"], bins=bins, density=True, alpha=0.6, color=C_LEG, label="Legítima")
ax.hist(df.loc[df.is_fraud == 1, "amount_usd"], bins=bins, density=True, alpha=0.7, color=C_FRA, label="Fraude")
ax.set_xscale("log")
ax.set_xlabel("Valor da transação (US$, escala logarítmica)")
ax.set_ylabel("Densidade")
ax.set_title("Distribuição do valor: fraudes x legítimas")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(FIG / "fig04_distribuicao_valor.png")
plt.close(fig)

# Sinais de "tentativas repetidas" (análogos ao caso real)
fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.1))
sinais = [("cvv_retry_count", "Nº de novas tentativas (CVV)"),
          ("txn_count_last_24h", "Transações nas últimas 24 h"),
          ("prior_disputes", "Contestações anteriores")]
R["sinais_tentativas"] = {}
for ax, (col, lab) in zip(axes, sinais):
    g = df.copy()
    if col == "txn_count_last_24h":
        g[col] = g[col].clip(upper=8)
    if col == "prior_disputes":
        g[col] = g[col].clip(upper=2)  # 3 e 4 têm poucos casos (n=63)
    t = g.groupby(col)["is_fraud"].agg(["mean", "count"])
    t["mean"] *= 100
    R["sinais_tentativas"][col] = {str(k): {"taxa_pct": round(v, 2), "n": int(n)}
                                   for k, v, n in zip(t.index, t["mean"], t["count"])}
    top = {"txn_count_last_24h": 8, "prior_disputes": 2}.get(col)
    ax.bar([f"{i}+" if i == top else str(i) for i in t.index], t["mean"], color=C_LEG)
    ax.set_title(lab, fontsize=9.5)
    ax.set_ylabel("Taxa de fraude (%)" if col == sinais[0][0] else "")
fig.suptitle("Tentativas repetidas e histórico elevam a taxa de fraude", fontweight="bold", fontsize=11)
fig.tight_layout()
fig.savefig(FIG / "fig05_sinais_tentativas.png")
plt.close(fig)

# Hora do dia: presencial (maquininha + aproximação) x não presencial (on-line + app)
# Faixas de 4 h em vez de hora a hora: no presencial há de 1 a 22 fraudes por hora (muito ruído).
def wilson(k: int, n_: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de confiança de Wilson (95%) para uma proporção, em %."""
    p = k / n_
    centro = (p + z**2 / (2 * n_)) / (1 + z**2 / n_)
    meia = z * np.sqrt(p * (1 - p) / n_ + z**2 / (4 * n_**2)) / (1 + z**2 / n_)
    return 100 * (centro - meia), 100 * (centro + meia)


noite = df.time_of_day_hour.isin([22, 23, 0, 1, 2, 3, 4, 5])
GRUPOS = {"Presencial (maquininha e aproximação)": ["POS", "Contactless"],
          "Não presencial (on-line e app)": ["Online", "In-App"]}
FAIXAS = [(0, 3), (4, 7), (8, 11), (12, 15), (16, 19), (20, 23)]
R["hora"] = {"taxa_noite_22_5_pct": round(100 * df.loc[noite, "is_fraud"].mean(), 2),
             "taxa_dia_6_21_pct": round(100 * df.loc[~noite, "is_fraud"].mean(), 2),
             "por_grupo": {}}
fig, ax = plt.subplots(figsize=(6.4, 3.3))
xs = np.arange(len(FAIXAS))
for (nome, canais), cor, desl in zip(GRUPOS.items(), [C_FRA, C_LEG], [-0.06, 0.06]):
    g = df[df.channel.isin(canais)]
    taxas, lo, hi, info = [], [], [], {}
    for a, b in FAIXAS:
        s = g[g.time_of_day_hour.between(a, b)]
        k, m = int(s.is_fraud.sum()), len(s)
        ci = wilson(k, m)
        taxas.append(100 * k / m); lo.append(ci[0]); hi.append(ci[1])
        info[f"{a}-{b}h"] = {"taxa_pct": round(100 * k / m, 2), "fraudes": k, "n": m,
                             "ic95_pct": [round(ci[0], 2), round(ci[1], 2)]}
    taxas, lo, hi = map(np.array, (taxas, lo, hi))
    ax.errorbar(xs + desl, taxas, yerr=[taxas - lo, hi - taxas], color=cor, marker="o", lw=2,
                capsize=3, label=nome)
    gn = g.time_of_day_hour.isin([22, 23, 0, 1, 2, 3, 4, 5])
    ct = pd.crosstab(gn, g.is_fraud)
    R["hora"]["por_grupo"][nome] = {
        "faixas": info,
        "taxa_noite_22_5_pct": round(100 * g.loc[gn, "is_fraud"].mean(), 2),
        "taxa_dia_6_21_pct": round(100 * g.loc[~gn, "is_fraud"].mean(), 2),
        "p_valor_qui2_noite_x_dia": float(stats.chi2_contingency(ct)[1]),
    }
ax.axvspan(2.6, 3.4, color=C_NEU, alpha=0.15, lw=0)
ax.text(3, ax.get_ylim()[1], "hipótese do\ncaso (14h)", ha="center", va="top",
        fontsize=7.5, color="#555555")
ax.axhline(R["classe"]["taxa_fraude_pct"], color=C_NEU, ls="--", lw=1,
           label=f"Média geral ({R['classe']['taxa_fraude_pct']:.2f}%)".replace(".", ","))
ax.set_xticks(xs, [f"{a}h–{b}h" for a, b in FAIXAS])
ax.set_xlabel("Faixa horária")
ax.set_ylabel("Taxa de fraude (%)")
ax.set_title("Taxa de fraude por faixa horária e canal (IC 95%)")
ax.legend(frameon=False, fontsize=8, loc="lower left")
fig.tight_layout()
fig.savefig(FIG / "fig06_fraude_por_hora.png")
plt.close(fig)

# Coerência da base sintética: combinações impossíveis no mundo real
R["coerencia_base"] = {
    "atm_machine_no_canal_online": int(((df.device_type == "ATM Machine") & (df.channel == "Online")).sum()),
    "pos_terminal_no_canal_online": int(((df.device_type == "POS Terminal") & (df.channel == "Online")).sum()),
    "categorias": sorted(df.merchant_category.unique().tolist()),
}

# Recorte "golpe da maquininha": transações presenciais (POS + aproximação)
pres = df[df.channel.isin(["POS", "Contactless"])]
R["recorte_presencial"] = {
    "n": int(len(pres)), "fraudes": int(pres.is_fraud.sum()),
    "taxa_fraude_pct": round(100 * pres.is_fraud.mean(), 2),
    "taxa_por_autenticacao_pct": (pres.groupby("auth_method")["is_fraud"].mean() * 100).round(2).to_dict(),
    "taxa_novo_estabelecimento_pct": round(100 * pres.loc[pres.is_new_merchant, "is_fraud"].mean(), 2),
    "taxa_estabelecimento_conhecido_pct": round(100 * pres.loc[~pres.is_new_merchant, "is_fraud"].mean(), 2),
    "mediana_distancia_fraude_km": round(pres.loc[pres.is_fraud == 1, "distance_from_home_km"].median(), 2),
    "mediana_distancia_legitima_km": round(pres.loc[pres.is_fraud == 0, "distance_from_home_km"].median(), 2),
    "taxa_restaurantes_pct": round(100 * pres.loc[pres.merchant_category == "Restaurants", "is_fraud"].mean(), 2),
    "n_restaurantes": int((pres.merchant_category == "Restaurants").sum()),
    "fraudes_restaurantes": int(pres.loc[pres.merchant_category == "Restaurants", "is_fraud"].sum()),
}

# Comparação de médias (fraude x legítima) nas variáveis numéricas
numcols = ["amount_usd", "hours_since_last_txn", "txn_count_last_24h", "distance_from_home_km",
           "velocity_score", "merchant_risk_score", "cvv_retry_count", "card_age_months"]
R["medianas_fraude_x_legitima"] = {
    c: {"legitima": round(df.loc[df.is_fraud == 0, c].median(), 2),
        "fraude": round(df.loc[df.is_fraud == 1, c].median(), 2)} for c in numcols}

# ---------------------------------------------------------------------------
# 3. Modelos baseline
# ---------------------------------------------------------------------------
CAT = ["merchant_category", "card_type", "auth_method", "channel", "device_type"]
BOOL = ["is_foreign_transaction", "is_new_merchant", "used_vpn", "ip_country_mismatch",
        "billing_shipping_mismatch", "is_ai_generated_scam_attempt"]
NUM = ["amount_usd", "hours_since_last_txn", "txn_count_last_24h", "distance_from_home_km",
       "card_age_months", "customer_age", "account_balance_usd", "cvv_retry_count",
       "velocity_score", "time_of_day_hour", "day_of_week", "merchant_risk_score", "prior_disputes"]
X = df[CAT + BOOL + NUM].copy()
X[BOOL] = X[BOOL].astype(int)
y = df["is_fraud"].values

X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, stratify=y, random_state=SEED)
R["divisao"] = {"treino": int(len(X_tr)), "teste": int(len(X_te)),
                "fraudes_treino": int(y_tr.sum()), "fraudes_teste": int(y_te.sum())}

pre = ColumnTransformer([
    ("cat", OneHotEncoder(handle_unknown="ignore"), CAT),
    ("num", StandardScaler(), NUM + BOOL),
])
modelos = {
    "Regressão Logística": Pipeline([("pre", pre), ("clf", LogisticRegression(
        class_weight="balanced", max_iter=2000, random_state=SEED))]),
    "Random Forest": Pipeline([("pre", pre), ("clf", RandomForestClassifier(
        n_estimators=400, min_samples_leaf=3, class_weight="balanced_subsample",
        n_jobs=-1, random_state=SEED))]),
}

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
R["modelos"] = {}
probas = {}
for nome, m in modelos.items():
    cv_pr = cross_val_score(m, X_tr, y_tr, cv=cv, scoring="average_precision", n_jobs=-1)
    m.fit(X_tr, y_tr)
    p = m.predict_proba(X_te)[:, 1]
    probas[nome] = p
    yhat = (p >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_te, yhat).ravel()
    R["modelos"][nome] = {
        "cv5_pr_auc_media": round(cv_pr.mean(), 4), "cv5_pr_auc_dp": round(cv_pr.std(), 4),
        "teste_roc_auc": round(roc_auc_score(y_te, p), 4),
        "teste_pr_auc": round(average_precision_score(y_te, p), 4),
        "limiar_0_5": {"recall": round(recall_score(y_te, yhat), 4),
                       "precisao": round(precision_score(y_te, yhat, zero_division=0), 4),
                       "f1": round(f1_score(y_te, yhat), 4),
                       "vp": int(tp), "fp": int(fp), "fn": int(fn), "vn": int(tn)},
    }

melhor = max(R["modelos"], key=lambda k: R["modelos"][k]["teste_pr_auc"])
R["melhor_modelo"] = melhor
pm = probas[melhor]

# Análise de limiar: recall x precisão e alertas gerados
prec, rec, thr = precision_recall_curve(y_te, pm)
fig, ax = plt.subplots(figsize=(6.4, 3.4))
ax.plot(thr, rec[:-1], color=C_FRA, label="Recall (fraudes barradas)")
ax.plot(thr, prec[:-1], color=C_LEG, label="Precisão (alertas corretos)")
ax.set_xlabel("Limiar de decisão (probabilidade de fraude)")
ax.set_ylabel("Valor")
ax.set_title(f"Escolha do limiar - {melhor}")
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(FIG / "fig07_limiar_recall_precisao.png")
plt.close(fig)

limiares = {}
for t in [0.1, 0.2, 0.3, 0.5, 0.7]:
    yhat = (pm >= t).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_te, yhat).ravel()
    limiares[str(t)] = {"recall": round(recall_score(y_te, yhat), 4),
                        "precisao": round(precision_score(y_te, yhat, zero_division=0), 4),
                        "vp": int(tp), "fp": int(fp), "fn": int(fn),
                        "pct_transacoes_alertadas": round(100 * yhat.mean(), 2)}
R["limiares_melhor_modelo"] = limiares

# Matriz de confusão no limiar 0,5
cm = confusion_matrix(y_te, (pm >= 0.5).astype(int))
fig, ax = plt.subplots(figsize=(3.8, 3.2))
ax.imshow(cm, cmap="Blues")
for (i, j), v in np.ndenumerate(cm):
    ax.text(j, i, f"{v:,}".replace(",", "."), ha="center", va="center",
            color="white" if v > cm.max() / 2 else "black", fontsize=12, fontweight="bold")
ax.set_xticks([0, 1], ["Prevista\nlegítima", "Prevista\nfraude"])
ax.set_yticks([0, 1], ["Real\nlegítima", "Real\nfraude"])
ax.set_title(f"Matriz de confusão\n{melhor} (limiar 0,5)")
for s in ax.spines.values():
    s.set_visible(False)
fig.tight_layout()
fig.savefig(FIG / "fig08_matriz_confusao.png")
plt.close(fig)

# Importância das variáveis (permutação, no conjunto de teste)
imp = permutation_importance(modelos[melhor], X_te, y_te, scoring="average_precision",
                             n_repeats=10, random_state=SEED, n_jobs=-1)
imp_s = pd.Series(imp.importances_mean, index=X_te.columns).sort_values(ascending=False).head(12)
R["importancia_permutacao_top12"] = imp_s.round(4).to_dict()
fig, ax = plt.subplots(figsize=(6.4, 4.0))
ax.barh(imp_s.index[::-1], imp_s.values[::-1], color=C_LEG)
ax.set_xlabel("Queda média na PR-AUC ao embaralhar a variável")
ax.set_title("Importância das variáveis (permutação)")
fig.tight_layout()
fig.savefig(FIG / "fig09_importancia_variaveis.png")
plt.close(fig)

# ---------------------------------------------------------------------------
# 4. Caso real: golpe da maquininha
# ---------------------------------------------------------------------------
# Sequência relatada (ordem real; intervalos de 1 min são hipótese de ilustração)
# O cartão era só de crédito: a função débito não existia na conta.
eventos = pd.DataFrame([
    (1, "Débito", 2000.00, "Negada - função débito inexistente"),
    (2, "Débito", 2000.00, "Negada - função débito inexistente"),
    (3, "Débito", 1000.00, "Negada - função débito inexistente"),
    (4, "Crédito", 1010.00, "Aprovada"),
    (5, "Crédito", 1011.00, "Aprovada"),
], columns=["tentativa", "modalidade", "valor_brl", "resposta_real"])
eventos["minuto"] = eventos["tentativa"] - 1  # hipótese: ~1 min entre tentativas
MODALIDADES_CONTRATADAS = {"Crédito"}


def motor_regras(ev: pd.DataFrame, janela_min: int = 10) -> pd.DataFrame:
    """Protótipo de regras que transformam a recusa técnica em sinal de risco."""
    out = []
    bloqueado = False
    for i, e in ev.iterrows():
        jan = ev[(ev.minuto <= e.minuto) & (ev.minuto >= e.minuto - janela_min)]
        nao_contratada = jan[~jan.modalidade.isin(MODALIDADES_CONTRATADAS)]
        r1 = e.modalidade not in MODALIDADES_CONTRATADAS          # modalidade não contratada
        r2 = len(nao_contratada) >= 2                              # recusas técnicas em sequência
        vals = jan.valor_brl.tolist()
        r3 = len(vals) >= 3 and vals[-1] < max(vals[:-1])           # valores decrescentes (sondagem)
        r4 = any(abs(e.valor_brl - v) / v < 0.02 and j != i         # quase duplicado
                 for j, v in zip(jan.index, jan.valor_brl))
        if r2:
            bloqueado = True
        decisao = "BLOQUEAR CARTÃO" if bloqueado else ("ALERTA" if (r1 or r3 or r4) else "seguir")
        out.append({"tentativa": int(e.tentativa), "R1_modalidade_nao_contratada": bool(r1),
                    "R2_recusas_tecnicas_em_sequencia": bool(r2), "R3_valores_decrescentes": bool(r3),
                    "R4_valor_quase_duplicado": bool(r4), "decisao_proposta": decisao})
    return pd.DataFrame(out)


regras = motor_regras(eventos)
caso = eventos.merge(regras, on="tentativa")
primeiro_bloqueio = int(caso.loc[caso.decisao_proposta == "BLOQUEAR CARTÃO", "tentativa"].min())
R["caso_real"] = {
    "eventos": caso.to_dict(orient="records"),
    "prejuizo_real_brl": float(eventos.loc[eventos.resposta_real == "Aprovada", "valor_brl"].sum()),
    "tentativa_do_bloqueio_proposto": primeiro_bloqueio,
    "prejuizo_com_regras_brl": float(eventos.loc[(eventos.resposta_real == "Aprovada")
                                                 & (eventos.tentativa < primeiro_bloqueio), "valor_brl"].sum()),
}

# Caso real no modelo: transação aprovada de R$ 1.010 em duas "visões"
CAMBIO = 5.0  # hipótese: R$ 5,00 por US$ (a base está em dólar)
HORA_CASO = 14  # hipótese: o golpe ocorreu durante o dia (hora exata não registrada)
mediana = df[NUM].median()
base_row = {
    "merchant_category": "Restaurants", "card_type": "Mastercard", "auth_method": "PIN",
    "channel": "POS", "device_type": "POS Terminal",
    "is_foreign_transaction": 0, "is_new_merchant": 1, "used_vpn": 0, "ip_country_mismatch": 0,
    "billing_shipping_mismatch": 0, "is_ai_generated_scam_attempt": 0,
    **{c: mediana[c] for c in NUM},
}
base_row.update({"amount_usd": 1010 / CAMBIO, "distance_from_home_km": 0.1,
                 "time_of_day_hour": HORA_CASO, "prior_disputes": 0})
sem_contexto = dict(base_row)  # o que o sistema "vê" se a recusa técnica não vira dado
com_contexto = dict(base_row)
com_contexto.update({
    "cvv_retry_count": 3,                                        # 3 tentativas negadas no débito
    "txn_count_last_24h": float(mediana["txn_count_last_24h"] + 3),
    "hours_since_last_txn": 1 / 60,                              # ~1 minuto
    "velocity_score": float(df["velocity_score"].quantile(0.99)),
})
cenarios = pd.DataFrame([sem_contexto, com_contexto])[CAT + BOOL + NUM]
score = modelos[melhor].predict_proba(cenarios)[:, 1]
pct_rank = [(pm < s).mean() * 100 for s in score]
R["caso_real_no_modelo"] = {
    "cambio_hipotese_brl_por_usd": CAMBIO, "hora_hipotese": HORA_CASO,
    "valor_usd": round(1010 / CAMBIO, 2),
    "prob_sem_contexto_das_recusas": round(float(score[0]), 4),
    "prob_com_contexto_das_recusas": round(float(score[1]), 4),
    "percentil_risco_sem_contexto": round(pct_rank[0], 1),
    "percentil_risco_com_contexto": round(pct_rank[1], 1),
    "obs": "A base não tem coluna débito/crédito nem histórico por cliente; as recusas técnicas "
           "foram aproximadas por cvv_retry_count, txn_count_last_24h, hours_since_last_txn e velocity_score.",
}

# Storyboard / linha do tempo do caso
fig, ax = plt.subplots(figsize=(9.6, 3.6))
for _, e in caso.iterrows():
    aprov = e.resposta_real == "Aprovada"
    cor = C_FRA if aprov else C_NEU
    ax.bar(e.tentativa, e.valor_brl, color=cor, width=0.62)
    ax.text(e.tentativa, e.valor_brl + 40, f"R$ {e.valor_brl:,.0f}".replace(",", "."),
            ha="center", fontsize=8.5, fontweight="bold")
    ax.text(e.tentativa, 80, e.modalidade, ha="center", fontsize=8, color="white", fontweight="bold")
ax.axvline(primeiro_bloqueio + 0.5, color=C_LEG, lw=2, ls="--")
ax.annotate("Bloqueio proposto: 2ª tentativa\nem modalidade não contratada",
            xy=(primeiro_bloqueio + 0.5, 1500), xytext=(2.9, 1620), color=C_LEG, fontsize=8.5,
            fontweight="bold", va="center",
            arrowprops=dict(arrowstyle="-|>", color=C_LEG, lw=1.2))
ax.set_xticks(caso.tentativa, [f"{t}ª" for t in caso.tentativa])
ax.set_xlabel("Tentativas na maquininha do entregador (ordem real)")
ax.set_ylabel("Valor (R$)")
ax.set_ylim(0, 2350)
ax.set_title("Caso real: 3 tentativas negadas no débito (função inexistente) e 2 aprovadas no crédito")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=C_NEU, label="Negada por regra de sistema (não por antifraude)"),
                   Patch(color=C_FRA, label="Aprovada (prejuízo)")], frameon=False, loc="upper right",
          fontsize=8.5)
fig.tight_layout()
fig.savefig(FIG / "fig10_caso_real_linha_do_tempo.png")
plt.close(fig)

# Fluxograma da solução (pipeline)
fig, ax = plt.subplots(figsize=(9.6, 2.4))
ax.axis("off")
etapas = [("OUVIR", "Relato do golpe\n+ reclamações públicas\n+ base Kaggle (20 mil)"),
          ("PREPARAR", "Conversão de tipos\nqualidade dos dados\ndesbalanceamento"),
          ("EXPLORAR", "EDA e recorte\npresencial (POS e\naproximação)"),
          ("MODELAR", "Regressão Logística\nRandom Forest\nvalidação cruzada"),
          ("TESTAR", "Limiar recall x\nfalso positivo +\ncaso real + regras")]
fases = ["Ouvir", "Criar / Prototipar", "Criar / Prototipar", "Criar / Prototipar", "Implementar / Testar"]
w, h, gap = 1.66, 1.05, 0.28
for k, ((tit, txt), fase) in enumerate(zip(etapas, fases)):
    x = k * (w + gap)
    cor = {"Ouvir": "#E8EEF5", "Criar / Prototipar": "#FBEDE5", "Implementar / Testar": "#E7F2EA"}[fase]
    ax.add_patch(FancyBboxPatch((x, 0), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=cor, ec="#4A4F57", lw=1))
    ax.text(x + w / 2, h - 0.18, tit, ha="center", va="center", fontweight="bold", fontsize=10)
    ax.text(x + w / 2, 0.4, txt, ha="center", va="center", fontsize=8.3)
    ax.text(x + w / 2, -0.15, fase, ha="center", va="center", fontsize=8, color="#4A4F57", style="italic")
    if k < len(etapas) - 1:
        ax.annotate("", xy=(x + w + gap - 0.02, h / 2), xytext=(x + w + 0.02, h / 2),
                    arrowprops=dict(arrowstyle="-|>", color="#4A4F57", lw=1.3))
ax.set_xlim(-0.1, 5 * w + 4 * gap + 0.1)
ax.set_ylim(-0.3, h + 0.05)
ax.set_title("Pipeline da solução inicial nas etapas do Design Thinking", fontsize=11)
fig.tight_layout()
fig.savefig(FIG / "fig01_pipeline_design_thinking.png")
plt.close(fig)

# ---------------------------------------------------------------------------
with open(RES / "metricas.json", "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(json.dumps(R, ensure_ascii=False, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
