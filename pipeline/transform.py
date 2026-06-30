"""
pipeline/transform.py
---------------------
Mescla os dados brutos novos (data_raw/*.parquet) no parquet acumulado.
Nunca sobrescreve historico; deduplicacao por chave de negocio.

Schema do parquet (modo real, CIMT):
  date         str   "YYYY-MM"
  trade_type   str   "Import" | "Export"
  hs2          str   "01" .. "99"
  country_code str   "US", "CN", "BR", etc.
  country_name str   "United States", "China", "Brazil", etc.
  province     str   "ON", "QC", etc. (NaN para exportacoes)
  value_cad    int   Dolares canadenses

Schema legado (modo DEMO / fase inicial):
  month, flow, partner, value_cad  (normalizado automaticamente)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
LOG = logging.getLogger(__name__)

PARQUET_PATH = Path(os.environ.get("PARQUET_PATH", "data/canada_trade_full.parquet"))
RAW_DIR = Path("data_raw")

# Chave de negocio para deduplicacao (schema CIMT)
CHAVE_CIMT = ["date", "trade_type", "hs2", "country_code", "province"]
# Chave de negocio para deduplicacao (schema legado/demo)
CHAVE_DEMO = ["date", "trade_type", "country_name"]


def _e_schema_demo(df: pd.DataFrame) -> bool:
    return "date" not in df.columns and "month" in df.columns


def _normalizar_demo(df: pd.DataFrame) -> pd.DataFrame:
    """Converte schema legado (month/flow/partner) para schema padrao."""
    df = df.copy()
    if "month" in df.columns:
        df = df.rename(columns={"month": "date"})
    if "flow" in df.columns:
        df["trade_type"] = df["flow"].str.capitalize()
        df = df.drop(columns=["flow"])
    if "partner" in df.columns:
        df = df.rename(columns={"partner": "country_name"})
    for c in ["hs2", "country_code", "province"]:
        if c not in df.columns:
            df[c] = None
    if "row_type" in df.columns:
        df = df.drop(columns=["row_type"])
    return df


def carregar_brutos() -> pd.DataFrame:
    """Carrega todos os parquets brutos de data_raw/ e normaliza o schema."""
    arquivos = sorted(RAW_DIR.glob("*.parquet"))
    if not arquivos:
        LOG.info("[transform] Nenhum bruto novo em data_raw/.")
        return pd.DataFrame()

    partes = []
    for a in arquivos:
        df = pd.read_parquet(a)
        if _e_schema_demo(df):
            df = _normalizar_demo(df)
        partes.append(df)

    novos = pd.concat(partes, ignore_index=True)
    novos["value_cad"] = pd.to_numeric(novos["value_cad"], errors="coerce").fillna(0).astype("int64")
    LOG.info("[transform] %d linha(s) brutas novas.", len(novos))
    return novos


def main() -> None:
    novos = carregar_brutos()

    if PARQUET_PATH.exists():
        antigo = pd.read_parquet(PARQUET_PATH)
        LOG.info("[transform] Parquet atual: %d linha(s).", len(antigo))
    else:
        antigo = pd.DataFrame()
        LOG.info("[transform] Sem parquet anterior. Criando do zero.")

    if novos.empty and antigo.empty:
        LOG.info("[transform] Nada para gravar. Encerrando.")
        return

    if novos.empty:
        LOG.info("[transform] Nenhum dado novo. Parquet inalterado.")
        return

    combinado = pd.concat([antigo, novos], ignore_index=True)

    # Detecta schema e aplica deduplicacao pela chave correta
    chave = CHAVE_CIMT if "hs2" in combinado.columns else CHAVE_DEMO
    chave_valida = [c for c in chave if c in combinado.columns]
    antes = len(combinado)
    combinado = combinado.drop_duplicates(subset=chave_valida, keep="last").reset_index(drop=True)
    LOG.info("[transform] Dedup: %d -> %d linha(s).", antes, len(combinado))

    PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)
    combinado.to_parquet(PARQUET_PATH, index=False)
    LOG.info("[transform] Parquet gravado em %s (%d linhas).", PARQUET_PATH, len(combinado))


if __name__ == "__main__":
    main()
