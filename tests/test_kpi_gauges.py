import unittest

from modules.gauge_components import (
    build_kpi_gauge_figure,
    build_kpi_gauge_label_html,
    gauge_status_color,
)


class KpiGaugeTests(unittest.TestCase):
    def test_standard_gauge_uses_good_high_end(self):
        figure = build_kpi_gauge_figure("Datakvalitet", 100, "Høj")
        indicator = figure.data[0]

        self.assertEqual(indicator.mode, "gauge+number")
        self.assertEqual(indicator.number.suffix, "%")
        self.assertEqual(indicator.gauge.steps[0].color, "#ff4b55")
        self.assertEqual(indicator.gauge.steps[-1].color, "#00d084")
        self.assertEqual(indicator.gauge.threshold.value, 100)

    def test_risk_gauge_reverses_color_scale(self):
        figure = build_kpi_gauge_figure(
            "Macro/Rate Risk", 77, "Meget høj", inverse=True
        )
        indicator = figure.data[0]

        self.assertEqual(indicator.number.suffix, "/100")
        self.assertEqual(indicator.gauge.steps[0].color, "#00d084")
        self.assertEqual(indicator.gauge.steps[-1].color, "#ff4b55")
        self.assertEqual(gauge_status_color(77, inverse=True), "#ff4b55")

    def test_missing_value_has_no_active_arc(self):
        figure = build_kpi_gauge_figure(
            "Konfidens", float("nan"), "Ukendt"
        )

        self.assertEqual(figure.data[0].mode, "gauge")
        self.assertTrue(any(annotation.text == "<b>N/A</b>" for annotation in figure.layout.annotations))

    def test_tooltip_content_is_escaped(self):
        html = build_kpi_gauge_label_html(
            "KPI", 'Forklaring med "citation" & tegn'
        )

        self.assertIn("&quot;citation&quot; &amp; tegn", html)


if __name__ == "__main__":
    unittest.main()
