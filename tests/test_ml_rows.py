import unittest

import pandas as pd

from src.ml_rows import filter_real_ml_publications
from src.transformers import build_editable_table, merge_ml_with_tienda_nube
from src.validators import validate_editable_promotions


class MercadoLibreTechnicalRowsTest(unittest.TestCase):
    def test_technical_and_empty_rows_are_not_validated_as_products(self):
        df = pd.DataFrame(
            [
                {
                    "ITEM_ID": None,
                    "SKU": "No modifiques esta columna",
                    "TITLE": "No modifiques esta columna",
                    "DISCOUNT_PERCENTAGE": "No modifiques esta columna",
                    "FINAL_PRICE": "No modifiques esta columna",
                },
                {"ITEM_ID": None, "SKU": "SKU", "TITLE": "Título", "DISCOUNT_PERCENTAGE": "SKU", "FINAL_PRICE": "Precio final"},
                {"ITEM_ID": float("nan"), "SKU": float("nan"), "TITLE": float("nan"), "DISCOUNT_PERCENTAGE": None, "FINAL_PRICE": None},
                {"ITEM_ID": "MLA123", "SKU": "ABC123", "TITLE": "Producto real", "DISCOUNT_PERCENTAGE": 10, "FINAL_PRICE": 900},
            ]
        )

        filtered = filter_real_ml_publications(df)
        errors = validate_editable_promotions(df)

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered.iloc[0]["ITEM_ID"], "MLA123")
        self.assertEqual(errors, [])

    def test_main_editable_table_excludes_technical_rows_before_validation(self):
        ml_df = pd.DataFrame(
            [
                {"ITEM_ID": None, "SKU": "SKU", "TITLE": "Título", "ORIGINAL_PRICE": None, "DISCOUNT_PERCENTAGE": "SKU", "FINAL_PRICE": "Precio final", "ACTION": None},
                {"ITEM_ID": None, "SKU": "No modifiques esta columna", "TITLE": "", "ORIGINAL_PRICE": None, "DISCOUNT_PERCENTAGE": "No modifiques esta columna", "FINAL_PRICE": None, "ACTION": None},
                {"ITEM_ID": "MLA123", "SKU": "ABC123", "TITLE": "Producto real", "ORIGINAL_PRICE": 1000, "DISCOUNT_PERCENTAGE": 10, "FINAL_PRICE": 900, "ACTION": "Participar"},
            ]
        )
        tn_df = pd.DataFrame([{"SKU": "ABC123", "Costo": 500, "Nombre": "Producto TN", "Código de barras / EAN": "779", "Categorías": "Cat", "Marca": "Marca"}])

        merged = merge_ml_with_tienda_nube(ml_df, tn_df)
        editable = build_editable_table(merged)

        self.assertEqual(len(editable), 1)
        self.assertEqual(editable.iloc[0]["SKU"], "ABC123")
        self.assertEqual(validate_editable_promotions(editable), [])


if __name__ == "__main__":
    unittest.main()
