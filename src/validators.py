"""Validaciones, alertas y métricas de la app."""

from __future__ import annotations

import pandas as pd

from src.loaders import ML_REQUIRED_COLUMNS, TN_COLUMN_ALIASES
from src.utils import first_existing_column
from src.utils import parse_optional_number


def find_missing_columns(df: pd.DataFrame, required_columns: list[str]) -> list[str]:
    """Devuelve las columnas requeridas que no están presentes."""
    return [column for column in required_columns if column not in df.columns]


def validate_ml_columns(df: pd.DataFrame) -> list[str]:
    """Valida columnas mínimas del archivo de Mercado Libre."""
    return find_missing_columns(df, ML_REQUIRED_COLUMNS)


def validate_tienda_nube_columns(df: pd.DataFrame) -> list[str]:
    """Valida columnas mínimas del archivo de Tienda Nube tras aplicar aliases."""
    missing = []
    for canonical, aliases in TN_COLUMN_ALIASES.items():
        if canonical not in df.columns and first_existing_column(df.columns, aliases) is None:
            missing.append(canonical)
    return missing


def is_blank(series: pd.Series) -> pd.Series:
    """Detecta valores vacíos considerando nulos y strings en blanco."""
    return series.isna() | series.astype(str).str.strip().eq("")


def build_metrics(merged_df: pd.DataFrame) -> dict[str, int]:
    """Construye las métricas principales del cruce."""
    has_match = merged_df.get("_HAS_MATCH", pd.Series(False, index=merged_df.index)).fillna(False)
    cost = merged_df.get("Costo", pd.Series(pd.NA, index=merged_df.index))
    ean = merged_df.get("Código de barras / EAN", pd.Series(pd.NA, index=merged_df.index))

    return {
        "Total publicaciones ML": int(len(merged_df)),
        "Total productos cruzados": int(has_match.sum()),
        "Total sin cruce": int((~has_match).sum()),
        "Total sin costo": int(is_blank(cost).sum()),
        "Total sin EAN": int(is_blank(ean).sum()),
    }


def validate_editable_promotions(df: pd.DataFrame) -> list[str]:
    """Valida los campos editables de la simulación sin interrumpir la ejecución."""
    errors: list[str] = []
    for position, row in df.reset_index(drop=True).iterrows():
        label = row.get("SKU") or row.get("TITLE") or f"fila {position + 1}"
        discount = parse_optional_number(row.get("DISCOUNT_PERCENTAGE"))
        final_price = parse_optional_number(row.get("FINAL_PRICE"))

        if discount is None:
            errors.append(f"{label}: DISCOUNT_PERCENTAGE debe ser numérico.")
        elif discount < 5 or discount > 80:
            errors.append(f"{label}: DISCOUNT_PERCENTAGE debe estar entre 5 y 80.")

        if final_price is None:
            errors.append(f"{label}: FINAL_PRICE debe ser numérico.")
        elif final_price <= 0:
            errors.append(f"{label}: FINAL_PRICE debe ser mayor a 0.")
    return errors
