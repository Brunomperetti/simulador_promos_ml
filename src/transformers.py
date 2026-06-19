"""Transformaciones para cruzar promociones de Mercado Libre con Tienda Nube."""

from __future__ import annotations

import pandas as pd

from src.loaders import ML_REQUIRED_COLUMNS, TN_COLUMN_ALIASES
from src.ml_rows import filter_real_ml_publications
from src.utils import add_normalized_sku, format_currency, format_percentage, format_plain_text, parse_optional_number

OUTPUT_COLUMNS = [
    "_ROW_ID",
    "SKU",
    "ITEM_ID",
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
    "Modificado",
    "Campo modificado",
    "Margen estimado",
    "Margen %",
    "Alerta margen",
    "STATUS",
    "ERRORS",
]
SORT_COLUMNS = ["Categorías", "Marca", "SKU"]
TEXT_COLUMNS = ["Código de barras / EAN"]
PRICE_COLUMNS = ["Costo", "ORIGINAL_PRICE", "FINAL_PRICE", "Margen estimado"]
PERCENTAGE_POINT_COLUMNS = ["DISCOUNT_PERCENTAGE"]
RATIO_PERCENTAGE_COLUMNS = ["Margen %"]
INTERNAL_COLUMNS = ["_ROW_ID", "_HAS_MATCH", "_matched_tn"]
READ_ONLY_COLUMNS = [column for column in OUTPUT_COLUMNS if column not in {"DISCOUNT_PERCENTAGE", "FINAL_PRICE"}]


def build_row_identifier(row: pd.Series) -> str:
    """Construye un identificador estable: ITEM_ID si existe; si no, SKU + TITLE."""
    item_id = format_plain_text(row.get("ITEM_ID")) if "ITEM_ID" in row.index else ""
    if item_id:
        return f"ITEM_ID::{item_id}"
    sku = str(row.get("SKU") or "").strip()
    title = str(row.get("TITLE") or "").strip()
    return f"SKU_TITLE::{sku}::{title}"



def build_row_identifiers(df: pd.DataFrame) -> pd.Series:
    """Devuelve identificadores únicos basados en ITEM_ID o SKU + TITLE."""
    base_ids = df.apply(build_row_identifier, axis=1)
    duplicates = base_ids.groupby(base_ids).cumcount()
    return base_ids.where(duplicates.eq(0), base_ids + "::" + duplicates.astype(str))


def has_number_changed(original_value: object, edited_value: object) -> bool:
    """Compara valores numéricos editables tolerando formatos equivalentes."""
    original = parse_optional_number(original_value)
    edited = parse_optional_number(edited_value)
    if original is None or edited is None:
        return original != edited
    return abs(original - edited) > 1e-9


def describe_modified_fields(discount_changed: bool, final_changed: bool) -> str:
    """Devuelve la etiqueta visible de campos modificados."""
    if discount_changed and final_changed:
        return "Descuento y precio final"
    if discount_changed:
        return "Descuento"
    if final_changed:
        return "Precio final"
    return ""


def filter_modified_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Conserva únicamente filas marcadas como modificadas."""
    if "Modificado" not in df.columns:
        return df.copy()
    return df[df["Modificado"].fillna("").astype(str).eq("Sí")].copy()


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
    matched_tn = row.get("_matched_tn", row.get("_HAS_MATCH", False))
    matched_tn = False if pd.isna(matched_tn) else bool(matched_tn)
    if not matched_tn:
        return "Sin cruce"
    if parse_optional_number(row.get("Costo")) is None:
        return "Sin costo"
    if not format_plain_text(row.get("Código de barras / EAN")):
        return "Sin EAN"

    margin_percentage = row.get("Margen %")
    if margin_percentage is not None and not pd.isna(margin_percentage):
        if margin_percentage < 0:
            return "Margen negativo"
        if margin_percentage < 0.15:
            return "Margen bajo"
    return ""


def _ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = df.copy()
    for column in columns:
        if column not in result.columns:
            result[column] = pd.NA
    return result


def merge_ml_with_tienda_nube(ml_df: pd.DataFrame, tn_df: pd.DataFrame) -> pd.DataFrame:
    """Cruza Mercado Libre con Tienda Nube por SKU normalizado."""
    ml_prepared = filter_real_ml_publications(_ensure_columns(ml_df, ML_REQUIRED_COLUMNS))
    ml_prepared["ACTION"] = "No participar"
    tn_prepared = _ensure_columns(tn_df, list(TN_COLUMN_ALIASES.keys()))

    ml_prepared = add_normalized_sku(ml_prepared, "SKU")
    tn_prepared = add_normalized_sku(tn_prepared, "SKU")
    tn_prepared = tn_prepared.drop_duplicates(subset=["_SKU_NORMALIZED"], keep="first")

    enrichment_columns = ["_SKU_NORMALIZED", "Costo", "Código de barras / EAN", "Nombre", "Categorías", "Marca"]
    matched_skus = set(tn_prepared["_SKU_NORMALIZED"].dropna()) - {""}
    merged = ml_prepared.merge(tn_prepared[enrichment_columns], on="_SKU_NORMALIZED", how="left")
    merged["Código de barras / EAN"] = merged["Código de barras / EAN"].map(format_plain_text)
    merged["_matched_tn"] = merged["_SKU_NORMALIZED"].isin(matched_skus)
    merged["_HAS_MATCH"] = merged["_matched_tn"]
    return merged


def add_simulation_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega columnas calculadas para simulación de promociones."""
    table = df.copy()
    table["Margen estimado"] = table.apply(lambda row: calculate_margin(row.get("FINAL_PRICE"), row.get("Costo")), axis=1)
    table["Margen %"] = table.apply(lambda row: calculate_margin_percentage(row.get("FINAL_PRICE"), row.get("Costo")), axis=1)
    table["Alerta margen"] = table.apply(build_margin_alert, axis=1)
    return table


def apply_promotion_edits(original_df: pd.DataFrame, edited_df: pd.DataFrame) -> pd.DataFrame:
    """Aplica ediciones, marca cambios y recalcula la columna dependiente."""
    original_by_row = original_df.set_index("_ROW_ID")
    result = edited_df.copy()
    for index, row in result.iterrows():
        row_id = row.get("_ROW_ID")
        if row_id not in original_by_row.index:
            continue

        original_row = original_by_row.loc[row_id]
        discount_changed = has_number_changed(original_row.get("DISCOUNT_PERCENTAGE"), row.get("DISCOUNT_PERCENTAGE"))
        final_changed = has_number_changed(original_row.get("FINAL_PRICE"), row.get("FINAL_PRICE"))
        edited_discount = parse_optional_number(row.get("DISCOUNT_PERCENTAGE"))
        edited_final = parse_optional_number(row.get("FINAL_PRICE"))

        result.at[index, "ACTION"] = "Participar" if discount_changed or final_changed else "No participar"
        result.at[index, "Modificado"] = "Sí" if discount_changed or final_changed else "No"
        result.at[index, "Campo modificado"] = describe_modified_fields(discount_changed, final_changed)

        if discount_changed and edited_discount is not None:
            # Streamlit no expone de forma confiable el último campo editado por celda en data_editor.
            # Cuando cambian ambas columnas en la misma fila priorizamos DISCOUNT_PERCENTAGE para mantener
            # una regla determinística y estable.
            recalculated_final = recalculate_final_price(row.get("ORIGINAL_PRICE"), edited_discount)
            if recalculated_final is not None:
                result.at[index, "FINAL_PRICE"] = recalculated_final
        elif final_changed and edited_final is not None:
            recalculated_discount = recalculate_discount_percentage(row.get("ORIGINAL_PRICE"), edited_final)
            if recalculated_discount is not None:
                result.at[index, "DISCOUNT_PERCENTAGE"] = recalculated_discount

    return add_simulation_columns(result)


def build_editable_table(merged_df: pd.DataFrame) -> pd.DataFrame:
    """Prepara la tabla principal editable con valores numéricos calculables."""
    columns = [column for column in OUTPUT_COLUMNS if column != "_ROW_ID"] + ["_HAS_MATCH", "_matched_tn"]
    table = _ensure_columns(merged_df, columns)[columns].copy()
    table.insert(0, "_ROW_ID", build_row_identifiers(merged_df))
    for column in ["Costo", "ORIGINAL_PRICE", "DISCOUNT_PERCENTAGE", "FINAL_PRICE"]:
        table[column] = table[column].map(parse_optional_number)
    table["ACTION"] = "No participar"
    table["Modificado"] = "No"
    table["Campo modificado"] = ""
    table["Código de barras / EAN"] = table["Código de barras / EAN"].map(format_plain_text)
    table = add_simulation_columns(table)
    return table.sort_values(SORT_COLUMNS, na_position="last", kind="stable").reset_index(drop=True)


def format_percentage_points(value: object) -> str:
    """Formatea porcentajes guardados como puntos porcentuales."""
    number = parse_optional_number(value)
    if number is None:
        return ""
    return f"{number:g}%".replace(".", ",")


def format_table_for_display(df: pd.DataFrame, drop_internal: bool = True) -> pd.DataFrame:
    """Aplica formato visual sin mutar la tabla numérica usada para cálculos."""
    table = df.copy()
    for column in TEXT_COLUMNS:
        if column in table.columns:
            table[column] = table[column].map(format_plain_text)
    for column in PRICE_COLUMNS:
        if column in table.columns:
            table[column] = table[column].map(format_currency)
    for column in PERCENTAGE_POINT_COLUMNS:
        if column in table.columns:
            table[column] = table[column].map(format_percentage_points)
    for column in RATIO_PERCENTAGE_COLUMNS:
        if column in table.columns:
            table[column] = table[column].map(format_percentage)
    if drop_internal:
        table = table.drop(columns=INTERNAL_COLUMNS, errors="ignore")
    return table


def build_display_table(merged_df: pd.DataFrame) -> pd.DataFrame:
    """Selecciona y ordena las columnas visibles en la app."""
    columns = OUTPUT_COLUMNS + ["_HAS_MATCH", "_matched_tn"]
    table = add_simulation_columns(_ensure_columns(merged_df, columns)[columns].copy())
    table = table.sort_values(SORT_COLUMNS, na_position="last", kind="stable")
    return format_table_for_display(table).reset_index(drop=True)
