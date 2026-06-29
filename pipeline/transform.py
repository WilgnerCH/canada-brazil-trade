"""
pipeline/transform.py
---------------------
Mescla os dados brutos novos (data_raw/) no parquet acumulado (merge, NUNCA
overwrite) e regrava o parquet. Resolve o problema de "overwrite em vez de
merge": o historico antigo e sempre preservado.

Deduplicacao: usa o mecanismo `row_type` + chave de negocio para nao duplicar
linhas quando um mes e reprocessado.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

PARQUET_PATH = Path(os.environ.get("PARQUET_PATH", "data/canada_trade_full.parquet"))
RAW_DIR = Path("data_raw")

# Colunas que identificam uma linha unica. Ajuste se a sua extracao real tiver
# mais granularidade (ex.: incluir codigo HS, provincia, etc.).
CHAVE = ["month", "flow", "partner"]


def carregar_brutos() -> pd.DataFrame:
    arquivos = sorted(RAW_DIR.glob("*.parquet"))
    if not arquivos:
        print("[transform] Nenhum bruto novo em data_raw/. Nada a mesclar.")
        return pd.DataFrame()
    partes = [pd.read_parquet(a) for a in arquivos]
    novos = pd.concat(partes, ignore_index=True)
    print(f"[transform] {len(novos)} linha(s) bruta(s) nova(s).")
    return novos


def main() -> None:
    novos = carregar_brutos()

    if PARQUET_PATH.exists():
        antigo = pd.read_parquet(PARQUET_PATH)
        print(f"[transform] Parquet atual: {len(antigo)} linha(s).")
    else:
        antigo = pd.DataFrame()
        print("[transform] Sem parquet anterior. Criando do zero.")

    if novos.empty and antigo.empty:
        print("[transform] Nada para gravar. Encerrando.")
        return

    combinado = pd.concat([antigo, novos], ignore_index=True)

    # Dedup: mantem a ultima ocorrencia de cada chave (reprocessamento vence).
    chave = [c for c in CHAVE if c in combinado.columns]
    antes = len(combinado)
    combinado = combinado.drop_duplicates(subset=chave, keep="last").reset_index(drop=True)
    print(f"[transform] Dedup: {antes} -> {len(combinado)} linha(s).")

    PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)
    combinado.to_parquet(PARQUET_PATH, index=False)
    print(f"[transform] Parquet gravado em {PARQUET_PATH}.")


if __name__ == "__main__":
    main()
