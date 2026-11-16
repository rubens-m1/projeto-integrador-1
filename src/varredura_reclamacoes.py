"""
Pesquisa documental em reclamações públicas (etapa OUVIR do Design Thinking).

Entradas (coletadas manualmente no navegador em 08/11/2026, sem robôs de raspagem):
  results/reclameaqui_golpe_maquininha_empresas.csv   - 50 empresas mais citadas na busca
                                                         "golpe da maquininha" do Reclame Aqui
  results/reclameaqui_golpe_maquininha_problemas_geral.csv
Os números do Boletim Consumidor.gov.br 2025 (Senacon/MJSP) estão transcritos abaixo.

No relatório, nenhuma instituição é nomeada: as empresas são agregadas por TIPO.

Uso:  python -I src/varredura_reclamacoes.py   (a partir da raiz do repositório)
Saída: results/varredura_reclamacoes.json
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"

TOTAL_BUSCA = 6550           # reclamações retornadas pela busca "golpe da maquininha"
RECLAMACOES_BANCO_DO_CASO = 378  # emissor do cartão do autor (não identificado no relatório)

# O mapa empresa -> tipo de instituição (e o nome do banco do caso) fica em
# privado/tipos_empresas.json, fora do repositório público, junto com os CSVs brutos.
# No repositório só vai o resultado agregado: results/varredura_reclamacoes.json.
PRIV = ROOT / "privado" / "tipos_empresas.json"
if not PRIV.exists() or not (RES / "reclameaqui_golpe_maquininha_empresas.csv").exists():
    raise SystemExit("Dados brutos privados ausentes (privado/ e results/reclameaqui_*.csv). "
                     "Use o agregado results/varredura_reclamacoes.json, que já está no repositório.")
_priv = json.loads(PRIV.read_text(encoding="utf-8"))
TIPOS: dict[str, list[str]] = _priv["tipos"]
BANCO_DO_CASO: str = _priv["banco_do_caso"]

emp = pd.read_csv(RES / "reclameaqui_golpe_maquininha_empresas.csv")
mapa = {e: t for t, lista in TIPOS.items() for e in lista}
emp["tipo"] = emp.empresa.map(mapa).fillna("Outros (varejo, serviços e outros)")
g = emp.groupby("tipo").reclamacoes.agg(["sum", "count"]).sort_values("sum", ascending=False)
tot50 = int(emp.reclamacoes.sum())
rank_banco = int(emp.reclamacoes.rank(ascending=False, method="min")[emp.empresa == BANCO_DO_CASO].iloc[0])
bancos = emp[emp.tipo == "Bancos e emissores de cartão"].sort_values("reclamacoes", ascending=False)

prob = pd.read_csv(RES / "reclameaqui_golpe_maquininha_problemas_geral.csv")

out = {
    "data_coleta": "2026-11-08",
    "reclame_aqui": {
        "busca": "golpe da maquininha",
        "total_reclamacoes_busca": TOTAL_BUSCA,
        "empresas_top": len(emp),
        "reclamacoes_top50": tot50,
        "por_tipo": {t: {"reclamacoes": int(r["sum"]), "empresas": int(r["count"]),
                         "pct_top50": round(100 * r["sum"] / tot50, 1)} for t, r in g.iterrows()},
        "banco_do_caso": {"reclamacoes": RECLAMACOES_BANCO_DO_CASO, "posicao_geral": rank_banco,
                          "primeiro_entre_bancos": bool(bancos.empresa.iloc[0] == BANCO_DO_CASO),
                          "pct_busca": round(100 * RECLAMACOES_BANCO_DO_CASO / TOTAL_BUSCA, 1)},
        "problemas_top": {r.item: int(r.reclamacoes) for r in prob.head(5).itertuples()},
        "leitura_qualitativa_n": 46,
        "obs": "Busca por texto: conta reclamações que mencionam os termos, não golpes confirmados. "
               "O site substitui a palavra 'golpe' por '[Editado pelo Reclame Aqui]' nos títulos.",
    },
    "boletim_consumidor_gov_2025": {
        "reclamacoes_finalizadas": 2328863,
        "pct_segmento_bancos_financeiras_cartao": 42.84,
        "assunto_cartao_credito_debito_loja": 433240,
        "pct_assunto_cartao": 18.60,
        "pct_grupo_cobranca_contestacao": 52.14,
        "pct_nao_reconhecido_no_segmento_bancario": 5.62,
        "indice_solucao_geral_pct": 81.43,
    },
}
(RES / "varredura_reclamacoes.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(out["reclame_aqui"]["por_tipo"], ensure_ascii=False, indent=1))
print(out["reclame_aqui"]["banco_do_caso"])
