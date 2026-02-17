import unittest

from scripts.validate_openmeteo_api import estimate_call_budget, evaluate_gate


class ValidateOpenMeteoApiTests(unittest.TestCase):
    def test_estimate_call_budget_matches_plan(self):
        budget = estimate_call_budget(point_count=1628, batch_size=100, apis_per_batch=2, updates_per_day=24)
        self.assertEqual(budget["batches"], 17)
        self.assertEqual(budget["requests_per_cycle"], 34)
        self.assertEqual(budget["requests_per_day"], 816)

    def test_gate_passes_with_target_coverage_and_latency(self):
        result = evaluate_gate(
            weather_coverage={
                "temperature": 99.0,
                "humidity": 98.0,
                "precipitation": 97.0,
                "uv_index": 96.0,
            },
            pm25_coverage=90.0,
            total_minutes=12.0,
            rate_limit_ratio=0.0,
            weather_target=90.0,
            pm25_target=80.0,
            max_minutes=30.0,
            max_rate_limit_ratio=0.05,
        )
        self.assertTrue(result["pass"])

    def test_gate_fails_when_pm25_and_runtime_below_threshold(self):
        result = evaluate_gate(
            weather_coverage={
                "temperature": 99.0,
                "humidity": 98.0,
                "precipitation": 97.0,
                "uv_index": 96.0,
            },
            pm25_coverage=45.0,
            total_minutes=35.0,
            rate_limit_ratio=0.12,
            weather_target=90.0,
            pm25_target=80.0,
            max_minutes=30.0,
            max_rate_limit_ratio=0.05,
        )
        self.assertFalse(result["pass"])
        self.assertIn("pm25_coverage", result["fail_reasons"])
        self.assertIn("total_runtime_minutes", result["fail_reasons"])
        self.assertIn("rate_limit_ratio", result["fail_reasons"])


if __name__ == "__main__":
    unittest.main()
