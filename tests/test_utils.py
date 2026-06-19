import unittest

from src.utils import format_currency, parse_currency_amount


class CurrencyParsingTest(unittest.TestCase):
    def test_parse_currency_amount_supported_formats(self):
        cases = {
            "8,762.64": 8762.64,
            "27,667.76": 27667.76,
            "1,365.74": 1365.74,
            "101,350.00": 101350.00,
            "8.762,64": 8762.64,
            "101.350,00": 101350.00,
            8762.64: 8762.64,
        }

        for raw_value, expected in cases.items():
            with self.subTest(raw_value=raw_value):
                self.assertAlmostEqual(parse_currency_amount(raw_value), expected)

    def test_format_currency_uses_argentine_format(self):
        cases = {
            "8,762.64": "$ 8.762,64",
            "27,667.76": "$ 27.667,76",
            "1,365.74": "$ 1.365,74",
            "101,350.00": "$ 101.350,00",
            "8.762,64": "$ 8.762,64",
            "101.350,00": "$ 101.350,00",
            8762.64: "$ 8.762,64",
        }

        for raw_value, expected in cases.items():
            with self.subTest(raw_value=raw_value):
                self.assertEqual(format_currency(raw_value), expected)


if __name__ == "__main__":
    unittest.main()
