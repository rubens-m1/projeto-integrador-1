# Machine Learning na detecção de fraudes em cartões: o golpe da maquininha

Projeto Integrador de Ciência dos Dados I (UFMS Digital, 2026/2). Ação de extensão de Rubens Lima Araújo.

O projeto parte de um golpe real. Um entregador tentou cobrar três vezes no **débito** de um cartão que
só tinha **crédito**. As tentativas foram negadas só porque a função não existia, e logo depois duas
compras no crédito foram aprovadas. A análise mostra que o modelo, sozinho, vê essa compra como de baixo
risco. O alerta só aparece quando a **recusa técnica vira dado**. Cinco regras simples teriam bloqueado o
cartão já na segunda tentativa.

## O que tem aqui

| Caminho | Conteúdo |
|---|---|
| [`notebook/deteccao_fraudes_golpe_maquininha.ipynb`](notebook/deteccao_fraudes_golpe_maquininha.ipynb) | **Comece por aqui.** Análise completa e narrada, já executada (também em `.html`) |
| `src/analise_preliminar.py` | EDA, modelos e caso real do relatório parcial (Módulo 2) → `results/metricas.json` |
| `src/solucao_final.py` | Melhorias da solução final: limiar ajustado, Gradient Boosting, regras R1–R5 em cenários → `results/metricas_final.json` |
| `src/cartilha/cartilha_golpe_maquininha.html`, `src/gera_cartilha.py` | Cartilha em HTML (A4). O script exporta o PDF e a figura pelo Edge/Chrome headless |
| `src/varredura_reclamacoes.py` | Agrega reclamações públicas por tipo de instituição (dados brutos privados; ver abaixo) |
| `src/gera_notebook.py` | Monta e executa o notebook |
| `src/gera_relatorio.py`, `src/gera_relatorio_final.py` | Geram os relatórios dos Módulos 2 e 3 (.docx) |
| `relatorio/Cartilha_Golpe_da_Maquininha.pdf` | Cartilha para o consumidor: sinais de alerta e como reclamar |
| `figures/` | Figuras dos relatórios |

## Como reproduzir

```bash
pip install -r requirements.txt
python -I src/analise_preliminar.py
python -I src/solucao_final.py
python -I src/gera_cartilha.py
python -I src/gera_notebook.py
python -I src/gera_relatorio_final.py
```

A base vem do Kaggle (*Credit Card Fraud Detection 2026*, usuário `uditjain13`). O arquivo
`Base de Dados - Projeto Integrador - credit_card_fraud_2026.csv` precisa estar na raiz.

## Principais resultados

| | Regressão Logística | Random Forest | Gradient Boosting |
|---|---|---|---|
| PR-AUC (validação cruzada) | **0,389** | 0,237 | 0,341 |
| PR-AUC (teste) | **0,436** | 0,228 | 0,338 |

- Compra do caso real sem o histórico de recusas: 1,6% de probabilidade de fraude. Com o histórico: 99,0%.
- Regras R1–R5: barram 4 de 5 golpes simulados. O prejuízo cai de R$ 6.926 para R$ 1.980, e nenhum cliente legítimo é bloqueado.

## Privacidade

Nenhuma instituição é identificada. Os CSVs brutos do Reclame Aqui e o mapa empresa → tipo têm nomes de
empresas e ficam **fora** do repositório (`.gitignore`). Só o resultado agregado por tipo,
`results/varredura_reclamacoes.json`, é público. Nenhum dado pessoal foi coletado.
