import unittest
from backend.app.main import calculate_heat_index, calculate_risk_index

class TestStadiumPulseMath(unittest.TestCase):
    def test_heat_index_low_temp(self):
        # Temp < 80 should return temperature directly
        self.assertEqual(calculate_heat_index(75.0, 50.0), 75.0)

    def test_heat_index_high_temp(self):
        # Temp >= 80, RH >= 40. E.g. T=94, RH=72. (Scenario A apparent temp should be ~121F)
        hi = calculate_heat_index(94.0, 72.0)
        self.assertGreater(hi, 115.0)
        self.assertLess(hi, 125.0)

    def test_heat_index_below_humidity_threshold(self):
        # Humidity < 40% should return temperature directly
        self.assertEqual(calculate_heat_index(90.0, 30.0), 90.0)

    def test_heat_index_low_humidity_adjustment(self):
        # T=95.0, RH=10.0 (RH < 13% and 80 <= T <= 112)
        # Should apply subtraction adjustment. Without adjustment H ~ 95.8, with adjustment ~ 95.1
        hi = calculate_heat_index(95.0, 10.0)
        self.assertLess(hi, 96.0)
        self.assertGreater(hi, 94.0)

    def test_heat_index_high_humidity_adjustment(self):
        # T=84.0, RH=90.0 (RH > 85% and 80 <= T <= 87)
        # Should apply addition adjustment.
        hi = calculate_heat_index(84.0, 90.0)
        self.assertGreater(hi, 95.0)
        self.assertLess(hi, 105.0)

    def test_risk_index_normal(self):
        # Low density, normal heat index -> Safe R
        # D = 30%, H = 75F -> HI_factor = 0. D_factor = 0.3. R = 0.6 * 0.3 + 0.4 * 0 = 0.18
        r = calculate_risk_index(30.0, 75.0)
        self.assertEqual(r, 0.18)

    def test_risk_index_critical(self):
        # Scenario A: Density = 91%, Heat Index = 112F
        # D_factor = 0.91, HI_factor = 1.0 (since 112 > 105).
        # R = 0.6 * 0.91 + 0.4 * 1.0 = 0.546 + 0.4 = 0.946
        r = calculate_risk_index(91.0, 112.0)
        self.assertEqual(r, 0.946)
        self.assertGreaterEqual(r, 0.85)

if __name__ == '__main__':
    unittest.main()
