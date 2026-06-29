"""
analytics/aggregate.py
----------------------
Le o parquet acumulado e gera os CSVs que o dashboard consome em site/data_csv/.
O dashboard (site/index.html) le esses CSVs por caminho RELATIVO (./data_csv/...),
entao funciona em qualquer conta/repo no GitHub Pages.

Hoje gera monthly.csv (exportacoes/importacoes/saldo por mes). Os outros recortes
(paises, produtos/HS2, provincias, matriz Brasil) entram aqui da mesma forma:
um groupby -> um to_csv. Veja os TODO no fim.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

PARQUET_PATH = Path(os.environ.get("PARQUET_PATH", "data/canada_trade_full.parquet"))
OUT_DIR = Path("site/data_csv")


def gerar_monthly(df: pd.DataFrame) -> None:
    """Exportacoes x importacoes x saldo por mes (relacao Canada<->Brasil)."""
    piv = (
        df.pivot_table(index="month", columns="flow", values="value_cad", aggfunc="sum")
        .fillna(0)
        .reset_index()
        .sort_values("month")
    )
    piv = piv.rename(columns={"export": "exports_cad", "import": "imports_cad"})
    for col in ("exports_cad", "imports_cad"):
        if col not in piv.columns:
            piv[col] = 0
    piv["balance_cad"] = piv["exports_cad"] - piv["imports_cad"]
    out = OUT_DIR / "monthly.csv"
    piv.to_csv(out, index=False)
    print(f"[aggregate] {out} ({len(piv)} linha(s)).")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if not PARQUET_PATH.exists():
        print("[aggregate] Parquet inexistente. Nada a agregar.")
        return

    df = pd.read_parquet(PARQUET_PATH)
    print(f"[aggregate] {len(df)} linha(s) carregada(s).")

    gerar_monthly(df)

    # TODO: replicar o padrao acima para os demais CSVs do dashboard, reaproveitando
    # a sua logica de agregacao do repo canada-trade-kpi-lab (src/):
    #   - countries.csv         (groupby partner)
    #   - products.csv          (groupby HS2, via hs_lookup)
    #   - provinces.csv,
    #     provinces_monthly.csv,
    #     provinces_hs2.csv      (groupby provincia)
    #   - brazil_opportunity.csv (matriz de oportunidade)
    # Cada um e: df.groupby(...).sum() -> .to_csv(OUT_DIR / "<nome>.csv").


if __name__ == "__main__":
    main()
