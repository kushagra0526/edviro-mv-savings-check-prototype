import sys, pathlib, unittest
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mvcheck.sim import build
from mvcheck.methods import naive, reg, mvcheck


class T(unittest.TestCase):
    def test_simulation_is_reproducible(self):
        self.assertTrue((build(5)["kwh"] == build(5)["kwh"]).all())

    def test_true_savings_are_what_was_planted(self):
        d = build(1, s=0.10)
        self.assertAlmostEqual(1 - d["kwh"][d["post"]].sum() / d["cf"][d["post"]].sum(), 0.10, places=6)

    def test_naive_blames_the_weather_regression_does_not(self):
        n_claims = r_claims = 0
        for seed in range(30):
            d = build(seed, s=0.0, shift=5.0)
            n_claims += naive(d)["claim"]
            r_claims += reg(d)["claim"]
        self.assertGreater(n_claims, 25)
        self.assertLess(r_claims, 8)

    def test_real_savings_are_verified(self):
        hits = sum(mvcheck(build(seed, s=0.12))["verdict"] == "VERIFIED" for seed in range(20))
        self.assertGreaterEqual(hits, 18)

    def test_out_of_range_weather_is_not_verified(self):
        d = build(3, s=0.12, shift=-12.0)
        self.assertEqual(mvcheck(d)["verdict"], "INSUFFICIENT")


if __name__ == "__main__":
    unittest.main()
