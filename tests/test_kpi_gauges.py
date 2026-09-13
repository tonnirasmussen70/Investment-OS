import unittest

from modules.gauge_components import build_kpi_gauge_html, gauge_status_color


class KpiGaugeTests(unittest.TestCase):
    def test_standard_gauge_uses_good_high_end(self):
        html = build_kpi_gauge_html(
            "Datakvalitet",
            100,
            "100%",
            "Høj",
            "Forklaring",
            gauge_id="quality-gradient",
        )

        self.assertIn('stroke-dasharray="100.0 100"', html)
        self.assertLess(html.index("#ef4444"), html.index("#22c55e"))
        self.assertIn('title="Forklaring"', html)

    def test_risk_gauge_reverses_color_scale(self):
        html = build_kpi_gauge_html(
            "Macro/Rate Risk",
            77,
            "77/100",
            "Meget høj",
            "Forklaring",
            inverse=True,
            gauge_id="risk-gradient",
        )

        self.assertIn('stroke-dasharray="77.0 100"', html)
        self.assertLess(html.index("#22c55e"), html.index("#ef4444"))
        self.assertEqual(gauge_status_color(77, inverse=True), "#ef4444")

    def test_missing_value_has_no_active_arc(self):
        html = build_kpi_gauge_html(
            "Konfidens",
            float("nan"),
            "N/A",
            "Ukendt",
            "Forklaring",
            gauge_id="confidence-gradient",
        )

        self.assertIn('opacity="0"', html)
        self.assertIn("N/A", html)

    def test_tooltip_content_is_escaped(self):
        html = build_kpi_gauge_html(
            "KPI",
            65,
            "65",
            "Acceptabel",
            'Forklaring med "citation" & tegn',
            gauge_id="safe-gradient",
        )

        self.assertIn("&quot;citation&quot; &amp; tegn", html)


if __name__ == "__main__":
    unittest.main()
