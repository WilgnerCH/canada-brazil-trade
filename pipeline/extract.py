"""
pipeline/extract.py
-------------------
Baixa da Statistics Canada APENAS os meses que ainda nao estao no parquet
acumulado (extracao incremental) e grava os dados brutos novos em data_raw/.

Como sabe o que ja existe: le os meses ja presentes no parquet recuperado da
Release. Se um mes ja esta la, nao baixa de novo -> resolve o "re-download
completo a cada execucao".

MODO DEMO (env DEMO=1): nao acessa a internet. Gera um arquivo bruto sintetico
para o pipeline rodar inteiro de ponta a ponta (e o Pages publicar) antes de
voce colar a logica real. Com DEMO=0, roda a extracao de verdade.
"""

from __future__ import annotations

import os
import random
from datetime import date
from pathlib import Path

import pandas as pd

PARQUET_PATH = Path(os.environ.get("PARQUET_PATH", "data/canada_trade_full.parquet"))
RAW_DIR = Path("data_raw")
DEMO = os.environ.get("DEMO", "1") == "1"


def meses_ja_no_parquet() -> set[str]:
    """Retorna o conjunto de meses (YYYY-MM) ja presentes no parquet acumulado."""
    if not PARQUET_PATH.exists():
        return set()
    df = pd.read_parquet(PARQUET_PATH, columns=["month"])
    return set(df["month"].astype(str).unique())


def baixar_demo(meses_existentes: set[str]) -> None:
    """Gera um mes sintetico novo (Canada<->Brasil) para o smoke test."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Cria ~12 meses ate o mes atual; mantem so os que ainda nao existem.
    hoje = date.today().replace(day=1)
    candidatos = []
    for i in range(12, 0, -1):
        ano = hoje.year
        mes = hoje.month - i
        while mes <= 0:
            mes += 12
            ano -= 1
        candidatos.append(f"{ano:04d}-{mes:02d}")

    novos = [m for m in candidatos if m not in meses_existentes]
    if not novos:
        print("[extract/DEMO] Nenhum mes novo. Nada a baixar.")
        return

    rng = random.Random(42)
    linhas = []
    for m in novos:
        exp = rng.randint(450, 900) * 1_000_000          # exportacoes Canada->Brasil (CAD)
        imp = rng.randint(500, 1100) * 1_000_000          # importacoes Brasil->Canada (CAD)
        linhas.append({"month": m, "flow": "export", "partner": "Brazil", "value_cad": exp, "row_type": "raw"})
        linhas.append({"month": m, "flow": "import", "partner": "Brazil", "value_cad": imp, "row_type": "raw"})

    out = RAW_DIR / "statcan_demo.parquet"
    pd.DataFrame(linhas).to_parquet(out, index=False)
    print(f"[extract/DEMO] Gerados {len(novos)} mes(es) novos -> {out}")


def baixar_real(meses_existentes: set[str]) -> None:
    """
    >>> COLE AQUI A SUA LOGICA REAL <<<
    Reaproveite o que ja funciona no repo antigo `canada-trade-data`:

      1. Liste os anos/meses disponiveis em www150.statcan.gc.ca.
      2. Para cada mes NAO presente em `meses_existentes`, baixe os ZIPs de
         importacoes e exportacoes (requests).
      3. Extraia, normalize as colunas (use o seu CNAMES de 222 entradas para
         resolver nomes de pais e o seu hs_lookup para os HS) e grave em
         data_raw/<mes>.parquet com uma coluna `month` no formato YYYY-MM.

    Mantenha a coluna `row_type` para a deduplicacao continuar funcionando.
    """
    raise NotImplementedError(
        "Extracao real ainda nao colada. Mantenha DEMO=1 ate portar a logica do "
        "repo canada-trade-data para esta funcao."
    )


def main() -> None:
    existentes = meses_ja_no_parquet()
    print(f"[extract] {len(existentes)} mes(es) ja no parquet.")
    if DEMO:
        baixar_demo(existentes)
    else:
        baixar_real(existentes)


if __name__ == "__main__":
    main()
