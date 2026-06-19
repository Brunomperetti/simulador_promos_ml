import unittest

import pandas as pd

from src.transformers import (
    add_simulation_columns,
    apply_promotion_edits,
    build_editable_table,
    build_margin_alert,
    calculate_margin,
    calculate_margin_percentage,
    filter_modified_rows,
    format_table_for_display,
    merge_ml_with_tienda_nube,
    recalculate_discount_percentage,
    recalculate_final_price,
)


class PromotionSimulationTest(unittest.TestCase):

    def test_initial_action_is_no_participar_for_real_rows(self):
        ml_df = pd.DataFrame(
            [{"ITEM_ID": "MLA1", "SKU": "SKU1", "TITLE": "Producto", "ORIGINAL_PRICE": 10000, "DISCOUNT_PERCENTAGE": 5, "FINAL_PRICE": 9500, "ACTION": "Participar"}]
        )
        tn_df = pd.DataFrame(
            [{"SKU": "SKU1", "Costo": 5000, "Código de barras / EAN": "7794940000000.0", "Nombre": "Producto", "Categorías": "Cat", "Marca": "Marca"}]
        )

        editable = build_editable_table(merge_ml_with_tienda_nube(ml_df, tn_df))

        self.assertEqual(editable.loc[0, "ACTION"], "No participar")
        self.assertEqual(editable.loc[0, "Modificado"], "No")

    def test_discount_change_marks_row_and_recalculates_final_price(self):
        original = build_editable_table(
            pd.DataFrame(
                [{"ITEM_ID": "MLA1", "SKU": "SKU1", "TITLE": "Producto", "ORIGINAL_PRICE": 10000, "DISCOUNT_PERCENTAGE": 5, "FINAL_PRICE": 9500, "ACTION": "Participar"}]
            )
        )
        edited = original.copy()
        edited.loc[0, "DISCOUNT_PERCENTAGE"] = 10

        result = apply_promotion_edits(original, edited)

        self.assertEqual(result.loc[0, "ACTION"], "Participar")
        self.assertEqual(result.loc[0, "Modificado"], "Sí")
        self.assertEqual(result.loc[0, "Campo modificado"], "Descuento")
        self.assertEqual(result.loc[0, "FINAL_PRICE"], 9000)

    def test_final_price_change_marks_row_and_recalculates_discount(self):
        original = build_editable_table(
            pd.DataFrame(
                [{"ITEM_ID": "MLA1", "SKU": "SKU1", "TITLE": "Producto", "ORIGINAL_PRICE": 10000, "DISCOUNT_PERCENTAGE": 5, "FINAL_PRICE": 9500}]
            )
        )
        edited = original.copy()
        edited.loc[0, "FINAL_PRICE"] = 8000

        result = apply_promotion_edits(original, edited)

        self.assertEqual(result.loc[0, "ACTION"], "Participar")
        self.assertEqual(result.loc[0, "Modificado"], "Sí")
        self.assertEqual(result.loc[0, "Campo modificado"], "Precio final")
        self.assertEqual(result.loc[0, "DISCOUNT_PERCENTAGE"], 20)

    def test_unchanged_rows_remain_unmodified(self):
        original = build_editable_table(
            pd.DataFrame(
                [{"SKU": "SKU1", "TITLE": "Producto", "ORIGINAL_PRICE": 10000, "DISCOUNT_PERCENTAGE": 5, "FINAL_PRICE": 9500}]
            )
        )

        result = apply_promotion_edits(original, original.copy())

        self.assertEqual(result.loc[0, "ACTION"], "No participar")
        self.assertEqual(result.loc[0, "Modificado"], "No")
        self.assertEqual(result.loc[0, "Campo modificado"], "")

    def test_both_changed_fields_are_labeled_and_discount_takes_priority(self):
        original = build_editable_table(
            pd.DataFrame(
                [{"SKU": "SKU1", "TITLE": "Producto", "ORIGINAL_PRICE": 10000, "DISCOUNT_PERCENTAGE": 5, "FINAL_PRICE": 9500}]
            )
        )
        edited = original.copy()
        edited.loc[0, "DISCOUNT_PERCENTAGE"] = 10
        edited.loc[0, "FINAL_PRICE"] = 8000

        result = apply_promotion_edits(original, edited)

        self.assertEqual(result.loc[0, "Campo modificado"], "Descuento y precio final")
        self.assertEqual(result.loc[0, "FINAL_PRICE"], 9000)

    def test_filter_modified_rows_keeps_only_modified(self):
        df = pd.DataFrame([{"SKU": "A", "Modificado": "Sí"}, {"SKU": "B", "Modificado": "No"}])

        result = filter_modified_rows(df)

        self.assertEqual(result["SKU"].tolist(), ["A"])

    def test_ean_is_cleaned_in_editable_table(self):
        editable = build_editable_table(
            pd.DataFrame(
                [{"SKU": "SKU1", "TITLE": "Producto", "Código de barras / EAN": "7.79494e12", "ORIGINAL_PRICE": 10000, "DISCOUNT_PERCENTAGE": 5, "FINAL_PRICE": 9500}]
            )
        )

        self.assertEqual(editable.loc[0, "Código de barras / EAN"], "7794940000000")

    def test_recalculate_final_price_from_discount_percentage(self):
        self.assertAlmostEqual(recalculate_final_price(1000, 25), 750)

    def test_recalculate_discount_percentage_from_final_price(self):
        self.assertEqual(recalculate_discount_percentage(1000, 749), 25)

    def test_calculate_estimated_margin(self):
        self.assertAlmostEqual(calculate_margin(750, 500), 250)

    def test_calculate_margin_percentage(self):
        self.assertAlmostEqual(calculate_margin_percentage(750, 500), 250 / 750)

    def test_recalculated_display_table_formats_money_and_percentages(self):
        df = pd.DataFrame(
            [
                {
                    "Costo": 33470,
                    "ORIGINAL_PRICE": 101350,
                    "FINAL_PRICE": 50733.6,
                    "DISCOUNT_PERCENTAGE": 50,
                    "Margen estimado": 17263.6,
                    "Margen %": 0.3403,
                    "Código de barras / EAN": "7794940000000",
                }
            ]
        )

        result = format_table_for_display(df)

        self.assertEqual(result.loc[0, "Costo"], "$ 33.470,00")
        self.assertEqual(result.loc[0, "FINAL_PRICE"], "$ 50.733,60")
        self.assertEqual(result.loc[0, "Margen %"], "34,03%")

    def test_detect_negative_and_low_margin_alerts(self):
        negative = pd.Series({"_matched_tn": True, "Costo": 120, "Código de barras / EAN": "779", "Margen %": -0.2})
        low = pd.Series({"_matched_tn": True, "Costo": 90, "Código de barras / EAN": "779", "Margen %": 0.1})

        self.assertEqual(build_margin_alert(negative), "Margen negativo")
        self.assertEqual(build_margin_alert(low), "Margen bajo")

    def test_add_simulation_columns_marks_missing_data_by_alert_priority(self):
        df = pd.DataFrame(
            [
                {"FINAL_PRICE": 100, "Costo": 70, "Código de barras / EAN": "779", "_matched_tn": True},
                {"FINAL_PRICE": 100, "Costo": 70, "Código de barras / EAN": "779", "_matched_tn": False},
                {"FINAL_PRICE": 100, "Costo": None, "Código de barras / EAN": "779", "_matched_tn": True},
                {"FINAL_PRICE": 100, "Costo": 70, "Código de barras / EAN": "", "_matched_tn": True},
            ]
        )

        result = add_simulation_columns(df)

        self.assertNotEqual(result.loc[0, "Alerta margen"], "Sin cruce")
        self.assertEqual(result.loc[1, "Alerta margen"], "Sin cruce")
        self.assertEqual(result.loc[2, "Alerta margen"], "Sin costo")
        self.assertEqual(result.loc[3, "Alerta margen"], "Sin EAN")

    def test_merge_marks_real_sku_match_even_when_enriched_values_are_missing(self):
        ml_df = pd.DataFrame(
            [{"ITEM_ID": "MLA1", "SKU": "SKU1", "TITLE": "Producto", "ORIGINAL_PRICE": 100, "DISCOUNT_PERCENTAGE": 10, "FINAL_PRICE": 90}]
        )
        tn_df = pd.DataFrame(
            [{"SKU": "SKU1", "Costo": None, "Código de barras / EAN": None, "Nombre": None, "Categorías": None, "Marca": None}]
        )

        result = merge_ml_with_tienda_nube(ml_df, tn_df)

        self.assertTrue(result.loc[0, "_matched_tn"])
        self.assertTrue(result.loc[0, "_HAS_MATCH"])


if __name__ == "__main__":
    unittest.main()
