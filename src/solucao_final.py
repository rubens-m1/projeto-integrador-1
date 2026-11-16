"""
Solução final - Projeto Integrador de Ciência dos Dados I (UFMS Digital) - Módulo 3

Melhorias em relação à solução inicial (Relatório Parcial, Módulo 2):
  1. Modelos: ajuste do limiar do Random Forest e teste de Gradient Boosting
     (HistGradientBoostingClassifier), com o limiar escolhido SÓ no treino
     (probabilidades fora da dobra da validação cruzada), sem olhar o teste.
  2. Motor de regras ampliado (R1-R5) aplicado a cenários de golpe e de clientes
     legítimos, para medir em que tentativa cada golpe seria barrado e quantos
     alarmes falsos as regras gerariam.
  3. (A cartilha ao consumidor é gerada à parte, por src/gera_cartilha.py.)

Usa a MESMA divisão treino/teste do Módulo 2 (test_size=0,25, estratificada, semente 42).

Uso:  python -I src/solucao_final.py   (a partir da pasta proj-integrador-1)
Saídas: figures/fig11, fig12 e fig14 (*.png),
        results/metricas_final.json
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch, Patch
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, confusion_matrix, f1_score,
                             precision_recall_curve, precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SEED = 42
ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "Base de Dados - Projeto Integrador - credit_card_fraud_2026.csv"
FIG = ROOT / "figures"
RES = ROOT / "results"
for d in (FIG, RES):
    d.mkdir(exist_ok=True)

C_LEG, C_FRA, C_NEU = "#2E5E8C", "#D9622B", "#8A8F98"
plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 200, "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "bold", "axes.titlesize": 11,
})
R: dict = {}

# ---------------------------------------------------------------------------
# 0. Dados (mesma preparação do Módulo 2)
# ---------------------------------------------------------------------------
NUM_TXT = ["amount_usd", "hours_since_last_txn", "distance_from_home_km",
           "account_balance_usd", "velocity_score", "merchant_risk_score"]
CAT = ["merchant_category", "card_type", "auth_method", "channel", "device_type"]
BOOL = ["is_foreign_transaction", "is_new_merchant", "used_vpn", "ip_country_mismatch",
        "billing_shipping_mismatch", "is_ai_generated_scam_attempt"]
NUM = ["amount_usd", "hours_since_last_txn", "txn_count_last_24h", "distance_from_home_km",
       "card_age_months", "customer_age", "account_balance_usd", "cvv_retry_count",
       "velocity_score", "time_of_day_hour", "day_of_week", "merchant_risk_score", "prior_disputes"]


def br_to_float(s: pd.Series) -> pd.Series:
    return (s.astype(str).str.replace("$", "", regex=False).str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False).astype(float))


df = pd.read_csv(CSV)
for c in NUM_TXT:
    df[c] = br_to_float(df[c])
X = df[CAT + BOOL + NUM].copy()
X[BOOL] = X[BOOL].astype(int)
y = df["is_fraud"].values
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, stratify=y, random_state=SEED)


def pre():
    return ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), CAT),
                              ("num", StandardScaler(), NUM + BOOL)])


# ---------------------------------------------------------------------------
# 1. Modelos: limiar ajustado no treino + Gradient Boosting
# ---------------------------------------------------------------------------
LR, RF, GB = "Regressão Logística", "Random Forest", "Gradient Boosting"
modelos = {
    LR: Pipeline([("pre", pre()), ("clf", LogisticRegression(
        class_weight="balanced", max_iter=2000, random_state=SEED))]),
    RF: Pipeline([("pre", pre()), ("clf", RandomForestClassifier(
        n_estimators=400, min_samples_leaf=3, class_weight="balanced_subsample",
        n_jobs=-1, random_state=SEED))]),
}
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)


def gb(lr_, folhas, msl):
    return Pipeline([("pre", pre()), ("clf", HistGradientBoostingClassifier(
        learning_rate=lr_, max_iter=300 if lr_ < 0.1 else 120, max_leaf_nodes=folhas,
        min_samples_leaf=msl, l2_regularization=1.0, class_weight="balanced", random_state=SEED))])


# Pequena grade de hiperparâmetros do Gradient Boosting, avaliada SÓ no treino (CV 5 partes)
grade = []
for lr_ in (0.03, 0.1):
    for folhas in (4, 15):
        for msl in (20, 100):
            s = cross_val_score(gb(lr_, folhas, msl), X_tr, y_tr, cv=cv, scoring="average_precision", n_jobs=-1)
            grade.append({"learning_rate": lr_, "max_leaf_nodes": folhas, "min_samples_leaf": msl,
                          "cv5_pr_auc": round(float(s.mean()), 4)})
melhor_gb = max(grade, key=lambda g: g["cv5_pr_auc"])
R["gb_grade"] = {"configuracoes": grade, "melhor": melhor_gb}
modelos[GB] = gb(melhor_gb["learning_rate"], melhor_gb["max_leaf_nodes"], melhor_gb["min_samples_leaf"])


def metricas(y_true, p, t):
    yhat = (p >= t).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, yhat).ravel()
    return {"limiar": round(float(t), 4), "recall": round(recall_score(y_true, yhat), 4),
            "precisao": round(precision_score(y_true, yhat, zero_division=0), 4),
            "f1": round(f1_score(y_true, yhat, zero_division=0), 4),
            "vp": int(tp), "fp": int(fp), "fn": int(fn), "vn": int(tn),
            "pct_transacoes_alertadas": round(100 * yhat.mean(), 2)}


def limiar_max_f1(y_true, p):
    prec, rec, thr = precision_recall_curve(y_true, p)
    f1 = 2 * prec[:-1] * rec[:-1] / np.clip(prec[:-1] + rec[:-1], 1e-12, None)
    return float(thr[np.nanargmax(f1)])


def limiar_recall(y_true, p, alvo=0.80):
    """Maior limiar que ainda garante recall >= alvo (menos alarmes para o mesmo recall)."""
    prec, rec, thr = precision_recall_curve(y_true, p)
    ok = np.where(rec[:-1] >= alvo)[0]
    return float(thr[ok.max()])


R["modelos"] = {}
probas_te = {}
for nome, m in modelos.items():
    oof = cross_val_predict(m, X_tr, y_tr, cv=cv, method="predict_proba", n_jobs=-1)[:, 1]
    cv_pr = [average_precision_score(y_tr[te], oof[te]) for _, te in cv.split(X_tr, y_tr)]
    t_f1, t_r80 = limiar_max_f1(y_tr, oof), limiar_recall(y_tr, oof, 0.80)
    m.fit(X_tr, y_tr)
    p = m.predict_proba(X_te)[:, 1]
    probas_te[nome] = p
    R["modelos"][nome] = {
        "cv5_pr_auc_media": round(float(np.mean(cv_pr)), 4),
        "cv5_pr_auc_dp": round(float(np.std(cv_pr)), 4),
        "teste_pr_auc": round(average_precision_score(y_te, p), 4),
        "teste_roc_auc": round(roc_auc_score(y_te, p), 4),
        "limiar_0_5": metricas(y_te, p, 0.5),
        "limiar_max_f1_treino": metricas(y_te, p, t_f1),
        "limiar_recall80_treino": metricas(y_te, p, t_r80),
    }
    print(f"{nome:20s} CV PR-AUC {np.mean(cv_pr):.3f}  teste PR-AUC {R['modelos'][nome]['teste_pr_auc']:.3f}"
          f"  t_f1={t_f1:.3f} t_r80={t_r80:.3f}")

# Escolha do modelo final pela validação cruzada (o teste fica só para medir)
final = max(R["modelos"], key=lambda k: R["modelos"][k]["cv5_pr_auc_media"])
R["modelo_final"] = final
R["divisao"] = {"treino": int(len(X_tr)), "teste": int(len(X_te)), "fraudes_teste": int(y_te.sum())}
R["taxa_fraude_teste"] = round(float(y_te.mean()), 4)

# Figura 11: curvas precisão-recall dos três modelos no teste
fig, ax = plt.subplots(figsize=(6.4, 3.8))
estilo = {LR: (C_LEG, "-", "o"), RF: (C_NEU, "--", "s"), GB: (C_FRA, "-.", "^")}
for nome, p in probas_te.items():
    prec, rec, _ = precision_recall_curve(y_te, p)
    cor, ls, mk = estilo[nome]
    ax.plot(rec, prec, color=cor, ls=ls, lw=2,
            label=f"{nome} (PR-AUC {R['modelos'][nome]['teste_pr_auc']:.3f})".replace(".", ","))
    op = R["modelos"][nome]["limiar_recall80_treino"]
    ax.plot(op["recall"], op["precisao"], marker=mk, ms=8, color=cor, mec="white", mew=1.5, ls="none")
ax.axhline(y_te.mean(), color=C_NEU, lw=1, ls=":")
ax.text(0.01, y_te.mean() + 0.015, f"classificador aleatório ({100 * y_te.mean():.2f}%)".replace(".", ","),
        fontsize=7.5, color="#555555")
ax.set_xlabel("Recall (fração das fraudes barradas)")
ax.set_ylabel("Precisão (alertas corretos)")
ax.set_xlim(0, 1.01); ax.set_ylim(0, 1.01)
virg = matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.1f}".replace(".", ","))
ax.xaxis.set_major_formatter(virg); ax.yaxis.set_major_formatter(virg)
ax.set_title("Curvas precisão-recall no teste (marcadores: limiar com recall ≥ 80% no treino)",
             fontsize=9.5)
ax.legend(frameon=False, fontsize=8, loc="upper right")
ax.grid(alpha=0.25, lw=0.6)
fig.tight_layout()
fig.savefig(FIG / "fig11_modelos_precisao_recall.png")
plt.close(fig)

# Caso real nos três modelos (mesmas hipóteses do Módulo 2)
CAMBIO, HORA_CASO = 5.0, 14
mediana = df[NUM].median()
base_row = {"merchant_category": "Restaurants", "card_type": "Mastercard", "auth_method": "PIN",
            "channel": "POS", "device_type": "POS Terminal",
            "is_foreign_transaction": 0, "is_new_merchant": 1, "used_vpn": 0, "ip_country_mismatch": 0,
            "billing_shipping_mismatch": 0, "is_ai_generated_scam_attempt": 0,
            **{c: mediana[c] for c in NUM}}
base_row.update({"amount_usd": 1010 / CAMBIO, "distance_from_home_km": 0.1,
                 "time_of_day_hour": HORA_CASO, "prior_disputes": 0})
com = dict(base_row)
com.update({"cvv_retry_count": 3, "txn_count_last_24h": float(mediana["txn_count_last_24h"] + 3),
            "hours_since_last_txn": 1 / 60, "velocity_score": float(df["velocity_score"].quantile(0.99))})
cen = pd.DataFrame([base_row, com])[CAT + BOOL + NUM]
R["caso_real_nos_modelos"] = {}
for nome, m in modelos.items():
    s = m.predict_proba(cen)[:, 1]
    lim = R["modelos"][nome]["limiar_recall80_treino"]["limiar"]
    R["caso_real_nos_modelos"][nome] = {
        "prob_sem_contexto": round(float(s[0]), 4), "prob_com_contexto": round(float(s[1]), 4),
        "alerta_sem_contexto": bool(s[0] >= lim), "alerta_com_contexto": bool(s[1] >= lim)}

# ---------------------------------------------------------------------------
# 2. Motor de regras ampliado (R1-R5) em cenários
# ---------------------------------------------------------------------------
# Cada tentativa é avaliada ANTES da autorização, com o histórico das anteriores
# (mesmo cartão e mesmo terminal, janela de 10 minutos). Cenários de golpe inspirados
# nos padrões relatados nas reclamações públicas; os de clientes legítimos servem
# para medir alarmes falsos. Valores e tempos são hipotéticos, exceto no caso real.
NEG_MOD, NEG_SALDO, NEG_SENHA, APROV = ("negada: modalidade inexistente", "negada: saldo/limite",
                                       "negada: senha incorreta", "aprovada")
FATOR_TICKET = 5  # R5: valor acima de 5x o ticket médio do cliente

CENARIOS = [
    # nome, tipo, modalidades contratadas, ticket médio (R$), [(min, modalidade, valor, resposta)]
    ("G1 Caso real do autor", "golpe", {"Crédito"}, 60,
     [(0, "Débito", 2000, NEG_MOD), (1, "Débito", 2000, NEG_MOD), (2, "Débito", 1000, NEG_MOD),
      (3, "Crédito", 1010, APROV), (4, "Crédito", 1011, APROV)]),
    ("G2 Sondagem de saldo no débito", "golpe", {"Débito", "Crédito"}, 60,
     [(0, "Débito", 3000, NEG_SALDO), (1, "Débito", 2000, NEG_SALDO), (2, "Débito", 950, APROV)]),
    ("G3 Troca de modalidade após recusa", "golpe", {"Crédito"}, 60,
     [(0, "Débito", 1500, NEG_MOD), (1, "Crédito", 1490, APROV)]),
    ("G4 \"Não passou, passa de novo\"", "golpe", {"Débito", "Crédito"}, 60,
     [(0, "Crédito", 480, APROV), (1, "Crédito", 485, APROV)]),
    ("G5 Cobrança única alta", "golpe", {"Débito", "Crédito"}, 60,
     [(0, "Crédito", 1500, APROV)]),
    ("L1 Pedido comum", "legítimo", {"Débito", "Crédito"}, 60,
     [(0, "Crédito", 62, APROV)]),
    ("L2 Erra a senha uma vez", "legítimo", {"Débito", "Crédito"}, 60,
     [(0, "Débito", 62, NEG_SENHA), (1, "Débito", 62, APROV)]),
    ("L3 Duas compras no mesmo local", "legítimo", {"Débito", "Crédito"}, 60,
     [(0, "Crédito", 62, APROV), (5, "Crédito", 25, APROV)]),
    ("L4 Compra alta planejada", "legítimo", {"Débito", "Crédito"}, 60,
     [(0, "Crédito", 900, APROV)]),
]
REGRAS = {
    "R1": "Modalidade não contratada",
    "R2": "2 ou mais falhas em 10 min (recusas anteriores + tentativa atual em modalidade inexistente)",
    "R3": "Valores decrescentes após recusa (sondagem)",
    "R4": "Valor quase igual (< 2%) a uma tentativa anterior",
    "R5": f"Valor acima de {FATOR_TICKET}x o ticket médio do cliente",
}


def motor_regras(contratadas, ticket, eventos, janela=10):
    hist, out, bloqueado = [], [], False
    for (minuto, mod, valor, resp) in eventos:
        jan = [h for h in hist if minuto - h[0] <= janela]
        recusas = [h for h in jan if h[3] != APROV]
        r1 = mod not in contratadas
        r2 = len(recusas) + int(r1) >= 2
        r3 = bool(recusas) and len(jan) >= 2 and valor < max(h[2] for h in jan)
        r4 = any(abs(valor - h[2]) / h[2] < 0.02 for h in jan)
        r5 = valor > FATOR_TICKET * ticket
        if r2 or (r3 + r4 + r5) >= 2:
            bloqueado = True
        if bloqueado:
            dec = "Bloquear cartão"
        elif r1 or r3 or r4 or r5:
            dec = "Alerta: confirmar no app"
        else:
            dec = "Seguir"
        out.append({"minuto": minuto, "modalidade": mod, "valor_brl": valor, "resposta_real": resp,
                    "R1": r1, "R2": r2, "R3": r3, "R4": r4, "R5": r5, "decisao": dec})
        hist.append((minuto, mod, valor, resp))
    return out


R["regras"] = REGRAS
R["fator_ticket"] = FATOR_TICKET
R["cenarios"] = []
for nome, tipo, contr, ticket, ev in CENARIOS:
    res = motor_regras(contr, ticket, ev)
    perda_real = sum(e["valor_brl"] for e in res if e["resposta_real"] == APROV) if tipo == "golpe" else 0
    # Conservador: só o bloqueio impede a transação; o alerta pede confirmação no app.
    perda_bloq = sum(e["valor_brl"] for e in res
                     if e["resposta_real"] == APROV and e["decisao"] != "Bloquear cartão") if tipo == "golpe" else 0
    # Se o alerta retiver a transação até o cliente confirmar no app (e a vítima recusar):
    perda_alerta = sum(e["valor_brl"] for e in res
                       if e["resposta_real"] == APROV and e["decisao"] == "Seguir") if tipo == "golpe" else 0
    primeira = lambda d: next((i + 1 for i, e in enumerate(res) if e["decisao"].startswith(d)), None)
    R["cenarios"].append({
        "nome": nome, "tipo": tipo, "contratadas": sorted(contr), "ticket_medio_brl": ticket,
        "tentativas": res, "n_tentativas": len(res),
        "primeiro_alerta": primeira("Alerta") or primeira("Bloquear"), "primeiro_bloqueio": primeira("Bloquear"),
        "perda_real_brl": perda_real, "perda_so_bloqueio_brl": perda_bloq,
        "perda_bloqueio_e_alerta_brl": perda_alerta,
        "alarmes_falsos": (sum(e["decisao"] != "Seguir" for e in res) if tipo == "legítimo" else 0),
        "bloqueio_falso": bool(tipo == "legítimo" and any(e["decisao"] == "Bloquear cartão" for e in res)),
    })
golpes = [c for c in R["cenarios"] if c["tipo"] == "golpe"]
legit = [c for c in R["cenarios"] if c["tipo"] == "legítimo"]
R["resumo_regras"] = {
    "golpes": len(golpes), "legitimos": len(legit),
    "golpes_com_bloqueio": sum(c["primeiro_bloqueio"] is not None for c in golpes),
    "golpes_com_alerta": sum(c["primeiro_alerta"] is not None for c in golpes),
    "perda_real_total_brl": sum(c["perda_real_brl"] for c in golpes),
    "perda_so_bloqueio_total_brl": sum(c["perda_so_bloqueio_brl"] for c in golpes),
    "perda_bloqueio_e_alerta_total_brl": sum(c["perda_bloqueio_e_alerta_brl"] for c in golpes),
    "legitimos_com_alerta": sum(c["alarmes_falsos"] > 0 for c in legit),
    "legitimos_bloqueados": sum(c["bloqueio_falso"] for c in legit),
}

# Figura 12: matriz cenário x tentativa com a decisão do motor de regras
COR_DEC = {"Seguir": "#E7F2EA", "Alerta: confirmar no app": "#F6D7A7", "Bloquear cartão": "#C8432B"}
fig, ax = plt.subplots(figsize=(9.6, 4.6))
maxt = max(c["n_tentativas"] for c in R["cenarios"])
for i, c in enumerate(R["cenarios"]):
    yy = len(R["cenarios"]) - 1 - i
    for j, e in enumerate(c["tentativas"]):
        ax.add_patch(FancyBboxPatch((j + 0.06, yy + 0.1), 0.88, 0.8, boxstyle="round,pad=0,rounding_size=0.08",
                                    fc=COR_DEC[e["decisao"]], ec="white", lw=2))
        aprov = e["resposta_real"] == APROV
        txt_cor = "white" if e["decisao"] == "Bloquear cartão" else "#222222"
        ax.text(j + 0.5, yy + 0.62, f"{e['modalidade'][:3]}. R$ {e['valor_brl']:,.0f}".replace(",", "."),
                ha="center", va="center", fontsize=7.6, color=txt_cor, fontweight="bold")
        regras_on = ",".join(k for k in ("R1", "R2", "R3", "R4", "R5") if e[k]) or "–"
        ax.text(j + 0.5, yy + 0.33, f"{'aprovada' if aprov else 'negada'} · {regras_on}",
                ha="center", va="center", fontsize=6.6, color=txt_cor)
    ax.text(-0.1, yy + 0.5, c["nome"], ha="right", va="center", fontsize=8.3,
            color=C_FRA if c["tipo"] == "golpe" else C_LEG, fontweight="bold")
ax.set_xlim(-0.05, maxt + 0.02)
ax.set_ylim(-0.05, len(R["cenarios"]))
ax.set_xticks(np.arange(maxt) + 0.5, [f"{k + 1}ª tentativa" for k in range(maxt)], fontsize=8.5)
ax.set_yticks([])
for s in ("left", "bottom"):
    ax.spines[s].set_visible(False)
ax.tick_params(axis="x", length=0)
ax.set_title("Decisão das regras em cada tentativa\n(cenários de golpe em laranja; de clientes legítimos em azul)",
             fontsize=10, loc="center", x=0.42)
ax.legend(handles=[Patch(fc=v, label=k) for k, v in COR_DEC.items()], frameon=False, fontsize=8,
          loc="upper center", bbox_to_anchor=(0.5, -0.07), ncol=3)
fig.tight_layout()
fig.savefig(FIG / "fig12_regras_cenarios.png")
plt.close(fig)

# ---------------------------------------------------------------------------
# 3. Cartilha de orientação ao consumidor: desenhada em HTML (src/cartilha/) e exportada por
#    src/gera_cartilha.py para figures/fig13_cartilha_golpe_maquininha.png e o PDF.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 4. Pipeline da solução final (Design Thinking)
# ---------------------------------------------------------------------------
etapas = [("OUVIR", "Relato do golpe\nreclamações públicas\nbase Kaggle (20 mil)"),
          ("PREPARAR", "Conversão de tipos\nqualidade dos dados\ndesbalanceamento"),
          ("EXPLORAR", "EDA, recorte\npresencial e\nhorário (IC 95%)"),
          ("MODELAR", "RL, RF e Gradient\nBoosting + limiar\nescolhido no treino"),
          ("REGRAS", "R1–R5 no caso real\ne em 9 cenários\n(golpe e legítimo)"),
          ("DEVOLVER", "Cartilha, notebook,\nrepositório e\napresentação")]
fases = ["Ouvir"] + ["Criar / Prototipar"] * 3 + ["Implementar / Testar"] * 2
fig, ax = plt.subplots(figsize=(9.6, 2.4))
ax.axis("off")
w, h, gap = 1.42, 1.05, 0.24
for k, ((tit, txt), fase) in enumerate(zip(etapas, fases)):
    x = k * (w + gap)
    cor = {"Ouvir": "#E8EEF5", "Criar / Prototipar": "#FBEDE5", "Implementar / Testar": "#E7F2EA"}[fase]
    ax.add_patch(FancyBboxPatch((x, 0), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=cor, ec="#4A4F57", lw=1))
    ax.text(x + w / 2, h - 0.18, tit, ha="center", va="center", fontweight="bold", fontsize=9.5)
    ax.text(x + w / 2, 0.4, txt, ha="center", va="center", fontsize=7.6)
    ax.text(x + w / 2, -0.15, fase, ha="center", va="center", fontsize=7.6, color="#4A4F57", style="italic")
    if k < len(etapas) - 1:
        ax.annotate("", xy=(x + w + gap - 0.02, h / 2), xytext=(x + w + 0.02, h / 2),
                    arrowprops=dict(arrowstyle="-|>", color="#4A4F57", lw=1.3))
ax.annotate("devolutivas", xy=(3 * (w + gap) + w / 2, h + 0.03), xytext=(5 * (w + gap) + w / 2, h + 0.03),
            ha="center", fontsize=7.5, color="#4A4F57",
            arrowprops=dict(arrowstyle="-|>", color="#4A4F57", lw=1, ls="--", connectionstyle="arc3,rad=0.25"))
ax.set_xlim(-0.1, 6 * w + 5 * gap + 0.1)
ax.set_ylim(-0.3, h + 0.45)
ax.set_title("Pipeline da solução final nas etapas do Design Thinking", fontsize=11)
fig.tight_layout()
fig.savefig(FIG / "fig14_pipeline_solucao_final.png")
plt.close(fig)

# ---------------------------------------------------------------------------
with open(RES / "metricas_final.json", "w", encoding="utf-8") as f:
    json.dump(R, f, ensure_ascii=False, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(json.dumps({k: R[k] for k in ("modelo_final", "resumo_regras", "caso_real_nos_modelos")},
                 ensure_ascii=False, indent=1))
