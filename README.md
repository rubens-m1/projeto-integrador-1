# Machine Learning na detecção de fraudes em cartões: o golpe da maquininha

Projeto Integrador de Ciência dos Dados I (UFMS Digital, 2026/2). Ação de extensão de Rubens Lima Araújo.

O projeto parte de um golpe real. Um entregador tentou cobrar três vezes no **débito** de um cartão que
só tinha **crédito**. As tentativas foram negadas só porque a função não existia, e logo depois duas
compras no crédito foram aprovadas. A análise mostra que o modelo, sozinho, vê essa compra como de baixo
risco. O alerta só aparece quando a **recusa técnica vira dado**. Cinco regras simples teriam bloqueado o
cartão já na segunda tentativa.

## Estrutura

```
projeto-integrador-1/
├── Cartilha_Golpe_da_Maquininha.pdf   # cartilha para o consumidor (sinais de alerta e como reclamar)
├── notebook/
│   ├── deteccao_fraudes_golpe_maquininha.ipynb   # comece por aqui: análise completa, já executada
│   └── deteccao_fraudes_golpe_maquininha.html    # o mesmo notebook, para ler no navegador
├── results/
│   └── varredura_reclamacoes.json     # reclamações públicas agregadas por tipo de instituição
├── src/
│   ├── analise_preliminar.py          # EDA, modelos e caso real (Módulo 2)
│   ├── solucao_final.py               # limiar ajustado, Gradient Boosting, regras R1–R5 (Módulo 3)
│   ├── varredura_reclamacoes.py       # gera results/varredura_reclamacoes.json (precisa dos dados privados)
│   ├── gera_cartilha.py               # exporta a cartilha HTML para PDF e PNG
│   ├── cartilha/cartilha_golpe_maquininha.html
│   ├── gera_notebook.py               # monta e executa o notebook
│   ├── gera_relatorio.py              # relatório parcial (Módulo 2, .docx)
│   └── gera_relatorio_final.py        # relatório final (Módulo 3, .docx)
├── requirements.txt
└── README.md
```

As pastas abaixo **não estão no repositório**: são criadas pelos scripts ao reproduzir o projeto.

| Pasta / arquivo gerado | Gerado por |
|---|---|
| `figures/fig01`–`fig10` e `results/metricas.json` | `src/analise_preliminar.py` |
| `figures/fig11`, `fig12`, `fig14` e `results/metricas_final.json` | `src/solucao_final.py` |
| `figures/fig13_cartilha_golpe_maquininha.png` e `Cartilha_Golpe_da_Maquininha.pdf` | `src/gera_cartilha.py` |
| `relatorio/Relatorio_Parcial_Modulo2_Rubens.docx` | `src/gera_relatorio.py` |
| `relatorio/Relatorio_Final_Modulo3_Rubens.docx` | `src/gera_relatorio_final.py` |

## Como reproduzir

1. Baixe a base do Kaggle (*Credit Card Fraud Detection 2026*, usuário `uditjain13`) e salve na raiz do
   repositório com o nome `Base de Dados - Projeto Integrador - credit_card_fraud_2026.csv`
   (o arquivo fica fora do Git pelo `.gitignore`).
2. Rode, a partir da raiz e nesta ordem (os relatórios usam as figuras e métricas dos passos anteriores):

```bash
pip install -r requirements.txt
python -I src/analise_preliminar.py
python -I src/solucao_final.py
python -I src/gera_cartilha.py
python -I src/gera_notebook.py
python -I src/gera_relatorio.py
python -I src/gera_relatorio_final.py
```

`src/gera_cartilha.py` precisa do Microsoft Edge ou do Google Chrome instalado.
`src/varredura_reclamacoes.py` não faz parte da reprodução: depende dos dados brutos privados (ver
[Privacidade](#privacidade)), e o resultado dele já está em `results/varredura_reclamacoes.json`.

## Principais resultados

| | Regressão Logística | Random Forest | Gradient Boosting |
|---|---|---|---|
| PR-AUC (validação cruzada) | **0,389** | 0,237 | 0,341 |
| PR-AUC (teste) | **0,436** | 0,228 | 0,338 |

- Compra do caso real sem o histórico de recusas: 1,6% de probabilidade de fraude. Com o histórico: 99,0%.
- Regras R1–R5: barram 4 de 5 golpes simulados. O prejuízo cai de R$ 6.926 para R$ 1.980, e nenhum cliente legítimo é bloqueado.

## Privacidade

Nenhuma instituição é identificada.
