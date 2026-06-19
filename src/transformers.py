"""Transformaciones para cruzar promociones de Mercado Libre con Tienda Nube."""

from __future__ import annotations

import pandas as pd

from src.loaders import ML_REQUIRED_COLUMNS, TN_COLUMN_ALIASES
from src.ml_rows import filter_real_ml_publications
from src.utils import add_normalized_sku, format_currency, format_percentage, format_plain_text, parse_optional_number

OUTPUT_COLUMNS = [
    "_ROW_ID",
    "SKU",
    "TITLE",
    "Nombre",
    "Categorías",
    "Marca",
    "Costo",
    "Código de barras / EAN",
    "ORIGINAL_PRICE",
    "DISCOUNT_PERCENTAGE",
    "FINAL_PRICE",
    "ACTION",
    "Margen estimado",
    "Margen %",
    "Alerta margen",
]
SORT_COLUMNS = ["Categorías", "Marca", "SKU"]
TEXT_COLUMNS = ["Código de barras / EAN"]
PRICE_COLUMNS = ["Costo", "ORIGINAL_PRICE", "FINAL_PRICE", "Margen estimado"]
READ_ONLY_COLUMNS = [column for column in OUTPUT_COLUMNS if column not in {"DISCOUNT_PERCENTAGE", "FINAL_PRICE"}]


def recalculate_final_price(original_price: object, discount_percentage: object) -> float | None:
    """Calcula el precio final desde precio original y descuento."""
    original = parse_optional_number(original_price)
    discount = parse_optional_number(discount_percentage)
    if original is None or discount is None:
        return None
    return original * (1 - discount / 100)


def recalculate_discount_percentage(original_price: object, final_price: object) -> int | None:
    """Calcula el porcentaje de descuento redondeado desde el precio final."""
    original = parse_optional_number(original_price)
    final = parse_optional_number(final_price)
    if original is None or original == 0 or final is None:
        return None
    return round((1 - final / original) * 100)


def calculate_margin(final_price: object, cost: object) -> float | None:
    """Calcula el margen estimado en moneda."""
    final = parse_optional_number(final_price)
    parsed_cost = parse_optional_number(cost)
    if final is None or parsed_cost is None:
        return None
    return final - parsed_cost


def calculate_margin_percentage(final_price: object, cost: object) -> float | None:
    """Calcula el margen porcentual como ratio."""
    final = parse_optional_number(final_price)
    margin = calculate_margin(final_price, cost)
    if final is None or final == 0 or margin is None:
        return None
    return margin / final


def build_margin_alert(row: pd.Series) -> str:
    """Construye una alerta legible para problemas de margen o datos faltantes."""
    alerts: list[str] = []
    if not bool(row.get("_HAS_MATCH", False)):
        alerts.append("Sin cruce")
    if parse_optional_number(row.get("Costo")) is None:
        alerts.append("Sin costo")

    margin_percentage = row.get("Margen %")
    if margin_percentage is not None and not pd.isna(margin_percentage):
        if margin_percentage < 0:
            alerts.append("Margen negativo")
        elif margin_percentage < 0.15:
            alerts.append("Margen menor al 15%")
    return " | ".join(alerts)


def _ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = df.copy()
    for column in columns:
        if column not in result.columns:
            result[column] = pd.NA
    return result


def merge_ml_with_tienda_nube(ml_df: pd.DataFrame, tn_df: pd.DataFrame) -> pd.DataFrame:
    """Cruza Mercado Libre con Tienda Nube por SKU normalizado."""
    ml_prepared = filter_real_ml_publications(_ensure_columns(ml_df, ML_REQUIRED_COLUMNS))
    tn_prepared = _ensure_columns(tn_df, list(TN_COLUMN_ALIASES.keys()))

    ml_prepared = add_normalized_sku(ml_prepared, "SKU")
    tn_prepared = add_normalized_sku(tn_prepared, "SKU")
    tn_prepared = tn_prepared.drop_duplicates(subset=["_SKU_NORMALIZED"], keep="first")

    enrichment_columns = ["_SKU_NORMALIZED", "Costo", "Código de barras / EAN", "Nombre", "Categorías", "Marca"]
    merged = ml_prepared.merge(tn_prepared[enrichment_columns], on="_SKU_NORMALIZED", how="left")
    merged["_HAS_MATCH"] = merged["Nombre"].notna() | merged["Costo"].notna() | merged["Código de barras / EAN"].notna()
    return merged


def add_simulation_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega columnas calculadas para simulación de promociones."""
    table = df.copy()
    table["Margen estimado"] = table.apply(lambda row: calculate_margin(row.get("FINAL_PRICE"), row.get("Costo")), axis=1)
    table["Margen %"] = table.apply(lambda row: calculate_margin_percentage(row.get("FINAL_PRICE"), row.get("Costo")), axis=1)
    table["Alerta margen"] = table.apply(build_margin_alert, axis=1)
    return table


def apply_promotion_edits(original_df: pd.DataFrame, edited_df: pd.DataFrame) -> pd.DataFrame:
    """Aplica ediciones de descuento/precio final y recalcula la columna dependiente."""
    original_by_row = original_df.set_index("_ROW_ID")
    result = edited_df.copy()
    for index, row in result.iterrows():
        row_id = row.get("_ROW_ID")
        if row_id not in original_by_row.index:
            continue

        original_row = original_by_row.loc[row_id]
        original_discount = parse_optional_number(original_row.get("DISCOUNT_PERCENTAGE"))
        original_final = parse_optional_number(original_row.get("FINAL_PRICE"))
        edited_discount = parse_optional_number(row.get("DISCOUNT_PERCENTAGE"))
        edited_final = parse_optional_number(row.get("FINAL_PRICE"))

        discount_changed = edited_discount != original_discount
        final_changed = edited_final != original_final

        if discount_changed and edited_discount is not None:
            recalculated_final = recalculate_final_price(row.get("ORIGINAL_PRICE"), edited_discount)
            if recalculated_final is not None:
                result.at[index, "FINAL_PRICE"] = recalculated_final
                result.at[index, "ACTION"] = "Participar"
        elif final_changed and edited_final is not None:
            recalculated_discount = recalculate_discount_percentage(row.get("ORIGINAL_PRICE"), edited_final)
            if recalculated_discount is not None:
                result.at[index, "DISCOUNT_PERCENTAGE"] = recalculated_discount
                result.at[index, "ACTION"] = "Participar"

    return add_simulation_columns(result)


def build_editable_table(merged_df: pd.DataFrame) -> pd.DataFrame:
    """Prepara la tabla principal editable con valores numéricos calculables."""
    table = _ensure_columns(merged_df, OUTPUT_COLUMNS)[[column for column in OUTPUT_COLUMNS if column != "_ROW_ID"]].copy()
    table.insert(0, "_ROW_ID", table.index)
    for column in ["Costo", "ORIGINAL_PRICE", "DISCOUNT_PERCENTAGE", "FINAL_PRICE"]:
        table[column] = table[column].map(parse_optional_number)
    table = add_simulation_columns(table)
    return table.sort_values(SORT_COLUMNS, na_position="last", kind="stable").reset_index(drop=True)


def build_display_table(merged_df: pd.DataFrame) -> pd.DataFrame:
    """Selecciona y ordena las columnas visibles en la app."""
    table = add_simulation_columns(_ensure_columns(merged_df, OUTPUT_COLUMNS)[OUTPUT_COLUMNS].copy())
    table = table.sort_values(SORT_COLUMNS, na_position="last", kind="stable")
    for column in TEXT_COLUMNS:
        table[column] = table[column].map(format_plain_text)
    for column in PRICE_COLUMNS:
        table[column] = table[column].map(format_currency)
    table["Margen %"] = table["Margen %"].map(format_percentage)
    table = table.drop(columns=["_ROW_ID"], errors="ignore")
    return table.reset_index(drop=True)
