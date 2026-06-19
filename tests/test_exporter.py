from io import BytesIO
import unittest

import pandas as pd
from openpyxl import Workbook, load_workbook

from src.exporter import export_mercado_libre_excel


class MercadoLibreExporterTest(unittest.TestCase):
    def build_template(self):
        wb = Workbook()
        ayuda = wb.active
        ayuda.title = "Ayuda"
        ayuda["A1"] = "contenido ayuda intacto"
        hidden = wb.create_sheet("hidden")
        hidden["A1"] = "contenido hidden intacto"
        promos = wb.create_sheet("Promociones")
        promos.append(["Instrucción general", None, None, None, None, None, None, "NO TOCAR"])
        promos.append(["ITEM_ID", "SKU", "TITLE", "ORIGINAL_PRICE", "DISCOUNT_PERCENTAGE", "FINAL_PRICE", "ACTION", "STATUS"])
        promos.append(["MLA1", "SKU1", "Producto 1", 1000, 5, 950, "No participar", "ok"])
        promos.append(["MLA2", "SKU2", "Producto 2", 2000, 10, 1800, "Participar", "ok"])
        promos.append([None, "SKU3", "Producto 3", 3000, 15, 2550, "Participar", "ok"])
        promos["E3"].number_format = "0%"
        buf = BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def test_export_preserves_sheets_columns_instruction_rows_and_only_updates_allowed_cells(self):
        template = self.build_template()
        simulated = pd.DataFrame(
            [
                {
                    "_ROW_ID": "ITEM_ID::MLA1",
                    "ITEM_ID": "MLA1",
                    "SKU": "SKU1",
                    "TITLE": "Producto 1 editado internamente",
                    "DISCOUNT_PERCENTAGE": 20,
                    "FINAL_PRICE": 800,
                    "ACTION": "Participar",
                    "Modificado": "Sí",
                    "Costo": 100,
                },
                {
                    "_ROW_ID": "ITEM_ID::MLA2",
                    "ITEM_ID": "MLA2",
                    "SKU": "SKU2",
                    "TITLE": "Producto 2",
                    "DISCOUNT_PERCENTAGE": 10,
                    "FINAL_PRICE": 1800,
                    "ACTION": "No participar",
                    "Modificado": "No",
                },
                {
                    "_ROW_ID": "SKU_TITLE::SKU3::Producto 3",
                    "SKU": "SKU3",
                    "TITLE": "Producto 3",
                    "DISCOUNT_PERCENTAGE": 25,
                    "FINAL_PRICE": 2250,
                    "ACTION": "Participar",
                    "Modificado": "Sí",
                },
            ]
        )

        exported = export_mercado_libre_excel(template, simulated)
        wb = load_workbook(BytesIO(exported))
        promos = wb["Promociones"]

        self.assertIn("Ayuda", wb.sheetnames)
        self.assertIn("hidden", wb.sheetnames)
        self.assertIn("Promociones", wb.sheetnames)
        self.assertEqual(wb["Ayuda"]["A1"].value, "contenido ayuda intacto")
        self.assertEqual(wb["hidden"]["A1"].value, "contenido hidden intacto")
        self.assertEqual(promos.max_column, 8)
        self.assertEqual([cell.value for cell in promos[1]], ["Instrucción general", None, None, None, None, None, None, "NO TOCAR"])

        self.assertEqual(promos["A3"].value, "MLA1")
        self.assertEqual(promos["B3"].value, "SKU1")
        self.assertEqual(promos["C3"].value, "Producto 1")
        self.assertEqual(promos["D3"].value, 1000)
        self.assertEqual(promos["H3"].value, "ok")
        self.assertEqual(promos["E3"].value, 20)
        self.assertEqual(promos["F3"].value, 800)
        self.assertEqual(promos["G3"].value, "Participar")

        self.assertEqual(promos["E4"].value, 10)
        self.assertEqual(promos["F4"].value, 1800)
        self.assertEqual(promos["G4"].value, "No participar")

        self.assertEqual(promos["E5"].value, 25)
        self.assertEqual(promos["F5"].value, 2250)
        self.assertEqual(promos["G5"].value, "Participar")


if __name__ == "__main__":
    unittest.main()
