import unittest

import pandas as pd

from src.transformers import (
    add_simulation_columns,
    build_margin_alert,
    calculate_margin,
    calculate_margin_percentage,
    recalculate_discount_percentage,
    recalculate_final_price,
)


class PromotionSimulationTest(unittest.TestCase):
    def test_recalculate_final_price_from_discount_percentage(self):
        self.assertAlmostEqual(recalculate_final_price(1000, 25), 750)

    def test_recalculate_discount_percentage_from_final_price(self):
        self.assertEqual(recalculate_discount_percentage(1000, 749), 25)

    def test_calculate_estimated_margin(self):
        self.assertAlmostEqual(calculate_margin(750, 500), 250)

    def test_calculate_margin_percentage(self):
        self.assertAlmostEqual(calculate_margin_percentage(750, 500), 250 / 750)

    def test_detect_negative_and_low_margin_alerts(self):
        negative = pd.Series({"_HAS_MATCH": True, "Costo": 120, "Margen %": -0.2})
        low = pd.Series({"_HAS_MATCH": True, "Costo": 90, "Margen %": 0.1})

        self.assertIn("Margen negativo", build_margin_alert(negative))
        self.assertIn("Margen menor al 15%", build_margin_alert(low))

    def test_add_simulation_columns_marks_missing_data(self):
        df = pd.DataFrame(
            [
                {"FINAL_PRICE": 100, "Costo": None, "_HAS_MATCH": True},
                {"FINAL_PRICE": 100, "Costo": 70, "_HAS_MATCH": False},
            ]
        )

        result = add_simulation_columns(df)

        self.assertIn("Sin costo", result.loc[0, "Alerta margen"])
        self.assertIn("Sin cruce", result.loc[1, "Alerta margen"])


if __name__ == "__main__":
    unittest.main()
