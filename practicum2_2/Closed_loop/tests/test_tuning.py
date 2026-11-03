"""Prestatiematen en gain scheduling, uitsluitend met synthetische data."""
import csv
import importlib
from pathlib import Path
import sys
import types
import unittest
from uuid import uuid4

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    import serial
except ImportError:
    sys.modules.setdefault("serial", types.SimpleNamespace(Serial=None, SerialException=OSError))
m = importlib.import_module("closed_loop.tuning")


class TuningTests(unittest.TestCase):
    def setUp(self):
        self.map = ROOT / ".test_output" / uuid4().hex
        self.map.mkdir(parents=True)
        self.addCleanup(self.cleanup)
        self.t = np.arange(101) / 10
        self.h = np.minimum(20 * self.t, 60)

    def cleanup(self):
        for p in self.map.iterdir():
            p.unlink()
        self.map.rmdir()
        if not any(self.map.parent.iterdir()):
            self.map.parent.rmdir()

    def schrijf(self, hoek=None, tijd=None, **instellingen):
        meta = dict(doelhoek=60, kp=2, ki=0, kd=0, max_pwm=120, max_hoek=100,
                    mode="fixed", meetduur_ms=10000, regelinterval_ms=100,
                    hoekoffset_deg=89, status="voltooid")
        meta.update(instellingen)
        p = self.map / (uuid4().hex + ".csv")
        with p.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for k, v in meta.items():
                writer.writerow(["# " + k, v])
            writer.writerow(["tijd_s", "hoek_deg", "pwm"])
            writer.writerows(zip(self.t if tijd is None else tijd,
                                 self.h if hoek is None else hoek,
                                 [60] * len(self.t if tijd is None else tijd)))
        return p

    def test_ramp_settles_and_integral(self):
        r = m.beoordeel_meting(self.schrijf())
        self.assertTrue(r["voldoet"], r["reden"])
        self.assertAlmostEqual(r["insteltijd_s"], 2.9)
        self.assertEqual(r["overshoot_deg"], 0)
        self.assertAlmostEqual(r["iae_graden_s"], 90)
        self.assertEqual(r["eindfout_deg"], 0)

    def test_overshoot_and_late_excursion(self):
        h = self.h.copy(); h[40] = 66
        r = m.beoordeel_meting(self.schrijf(h))
        self.assertEqual(r["overshoot_deg"], 6)
        self.assertFalse(r["voldoet"])
        self.assertAlmostEqual(r["insteltijd_s"], 4.1)
        h[90] = 65
        r = m.beoordeel_meting(self.schrijf(h))
        self.assertTrue(np.isnan(r["insteltijd_s"]))

    def test_downward_overshoot(self):
        h = np.maximum(20, 60 - 20 * self.t); h[30] = 15
        r = m.beoordeel_meting(self.schrijf(h, doelhoek=20), rusthoek=60)
        self.assertEqual(r["overshoot_deg"], 5)
        self.assertFalse(r["voldoet"])

    def test_failures_incomplete_data_and_nonmonotonic(self):
        for status in ("onderbroken", "fout"):
            self.assertFalse(m.beoordeel_meting(self.schrijf(status=status))["voldoet"])
        p = self.schrijf(self.h[:-20], self.t[:-20])
        self.assertFalse(m.beoordeel_meting(p)["geldige_proef"])
        t = self.t.copy(); t[5] = t[4]
        self.assertFalse(m.beoordeel_meting(self.schrijf(tijd=t))["voldoet"])
        self.assertFalse(m.beoordeel_meting(self.schrijf(self.h + 10))["geldige_proef"])

    def test_ranking_requires_repeats_and_rejects_failed_repeat(self):
        paden = [self.schrijf() for _ in range(3)]
        _, rang = m.vergelijk_metingen(paden + [paden[0]])
        self.assertEqual(rang.iloc[0]["aantal"], 3)
        self.assertTrue(rang.iloc[0]["geschikt"])
        schema = m.maak_gain_schema(rang)
        self.assertEqual(schema.iloc[0]["kp"], 2)
        _, rang = m.vergelijk_metingen(paden[:2])
        self.assertFalse(rang.iloc[0]["geschikt"])
        _, rang = m.vergelijk_metingen(paden + [self.schrijf(status="fout")])
        with self.assertRaises(ValueError): m.maak_gain_schema(rang)

    def test_unfair_comparison_rejected(self):
        with self.assertRaises(ValueError):
            m.vergelijk_metingen([self.schrijf(), self.schrijf(max_pwm=100)])

    def test_plan_deduplicates_and_repeats(self):
        plan = m.maak_meetplan(60, [1, 2], [0], [0, 0], 3)
        self.assertEqual(len(plan), 6)
        self.assertEqual(plan.herhaling.tolist(), [1, 1, 2, 2, 3, 3])

    def test_scheduling_interpolation_nearest_and_bounds(self):
        schema = pd.DataFrame([dict(doelhoek=40, kp=2, ki=0, kd=1),
                               dict(doelhoek=60, kp=4, ki=2, kd=3)])
        self.assertEqual(m.kies_pid(50, schema, "lineair"), dict(kp=3, ki=1, kd=2))
        self.assertEqual(m.kies_pid(51, schema)["kp"], 4)
        self.assertEqual(m.kies_pid(40, schema)["kp"], 2)
        with self.assertRaises(ValueError): m.kies_pid(70, schema)
        with self.assertRaises(ValueError): m.kies_pid(50, pd.concat([schema, schema]))

    def test_first_sample_already_near_target_does_not_win(self):
        r = m.beoordeel_meting(self.schrijf(np.full_like(self.t, 60)))
        self.assertFalse(r["voldoet"])


if __name__ == "__main__":
    unittest.main()
