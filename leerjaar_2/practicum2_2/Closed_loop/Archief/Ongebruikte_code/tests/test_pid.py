"""Zonder hardware: python -m unittest discover -s tests -v."""

import csv
import io
from contextlib import redirect_stdout
import importlib
import ast
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    import serial
except ImportError:
    sys.modules["serial"] = types.SimpleNamespace(Serial=None, SerialException=OSError)
m = importlib.import_module("closed_loop.meting")


def lees_header(pad):
    instellingen = {}
    with pad.open(newline="", encoding="utf-8") as f:
        for rij in csv.reader(f):
            if not rij or not rij[0].startswith("# "):
                break
            try:
                waarde = ast.literal_eval(rij[1])
            except (ValueError, SyntaxError):
                waarde = rij[1]
            instellingen[rij[0][2:]] = waarde
    return instellingen


class Clock:
    now = 0

    def sleep(self, seconds):
        self.now += seconds

    def monotonic(self):
        return self.now


class Arduino:
    def __init__(self, clock, scenario, step=None):
        self.step = step
        self.clock, self.scenario = clock, scenario
        self.commands, self.queue = [], []
        self.count, self.active = 0, False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def flush(self):
        pass

    def reset_input_buffer(self):
        self.queue.clear()

    def write(self, data):
        command = data.decode().strip()
        self.commands.append(command)
        if command == "HELLO":
            self.queue.append("PID_READY")
        elif command == "VERSIE":
            self.queue.append("PID_UNIFIED_V1" if self.step is None else f"PID_STAP{self.step}")
        elif command.startswith("OFFSET:"):
            self.queue.append("OFFSET_OK")
        elif command == "ANGLE":
            self.queue.append("ERROR:COMMAND" if self.scenario == "old" else "ANGLE:123.5")
        elif command.startswith("PWMSTAP:"):
            if self.scenario != "old_slew":
                self.queue.append("PWMSTAP_OK")
        elif command.startswith("CONFIG:"):
            self.queue.append("ERROR:CONFIG" if self.scenario == "config" else "CONFIG_OK")
        elif command in ("START", "CHECK"):
            self.queue.append("STARTED")
            self.active = True
        elif command == "STOP":
            self.active = False

    def readline(self):
        self.clock.now += 0.1
        if self.queue:
            return (self.queue.pop(0) + "\n").encode()
        if not self.active or self.scenario == "silence":
            return b""
        self.count += 1
        if self.count == 2:
            if self.scenario == "interrupt":
                raise KeyboardInterrupt
            if self.scenario == "angle_limit":
                return b"ERROR:MAX_HOEK\n"
            if self.scenario == "sensor":
                return b"ERROR:SENSOR_OR_ANGLE\n"
            if self.scenario == "bad_data":
                return b"not,a,measurement\n"
        if self.count > 12:
            return b"DONE\n"
        limit = float(next(c for c in self.commands if c.startswith("CONFIG:")).split(",")[4])
        pwm = min(20, limit)
        return f"{self.count * 100},40,10,{pwm}\n".encode()


class MeasurementTests(unittest.TestCase):
    def setUp(self):
        self.output = ROOT / ".test_output" / uuid4().hex
        self.output.mkdir(parents=True)
        self.addCleanup(self.cleanup)

    def cleanup(self):
        for path in self.output.iterdir():
            path.unlink()
        self.output.rmdir()
        if not any(self.output.parent.iterdir()):
            self.output.parent.rmdir()

    def run_case(self, scenario, error=None, check=False):
        clock = Clock()
        arduino = Arduino(clock, scenario)
        with patch.object(m.serial, "Serial", return_value=arduino), \
                patch.object(m, "time", clock), patch.object(m, "DATA_MAP", self.output):
            call = lambda: m.voer_pid_meting_uit(meetduur=2, sensorcontrole=check)
            if error:
                with self.assertRaises(error):
                    call()
            else:
                points, path = call()
                self.assertTrue(points)
                self.assertEqual(path.parent, self.output)
        self.assertEqual(arduino.commands[-1], "STOP")
        return arduino

    def test_complete_and_heartbeat(self):
        arduino = self.run_case("normal")
        self.assertIn("PING", arduino.commands)
        with next(self.output.glob("*.csv")).open() as f:
            rows = list(csv.reader(f))
        data = [rij for rij in rows if not rij[0].startswith("# ")]
        self.assertEqual(data[0], m.KOLOMMEN)
        self.assertEqual(data[1], ["0.1", "10.0", "20.0"])
        self.assertEqual(len(data), 13)
        self.assertFalse(list(self.output.glob("*.json")))
        meta = lees_header(next(self.output.glob("*.csv")))
        self.assertEqual(meta["hoekgrenzen_deg"], [-180, 180])
        self.assertEqual(meta["max_hoek"], 180.0)
        self.assertEqual(meta["status"], "voltooid")
        self.assertEqual(meta["ki"], 0)

    def test_interrupt_preserves_data(self):
        self.run_case("interrupt")
        meta = lees_header(next(self.output.glob("*.csv")))
        self.assertEqual(meta["status"], "onderbroken")

    def test_errors_stop_and_preserve_partial_data(self):
        for scenario in ("sensor", "bad_data", "angle_limit"):
            with self.subTest(scenario=scenario):
                self.run_case(scenario, RuntimeError)
        self.assertEqual(len(list(self.output.glob("*.csv"))), 3)
        for path in self.output.glob("*.csv"):
            self.assertEqual(lees_header(path)["status"], "fout")

    def test_silence_times_out(self):
        self.run_case("silence", TimeoutError)
        self.assertFalse(list(self.output.glob("*.csv")))

    def test_rejected_configuration_never_starts(self):
        arduino = self.run_case("config", RuntimeError)
        self.assertNotIn("START", arduino.commands)

    def test_continuous_ignores_duration_and_stops_on_interrupt(self):
        clock = Clock()
        arduino = Arduino(clock, "interrupt")
        with patch.object(m.serial, "Serial", return_value=arduino), \
                patch.object(m, "time", clock), patch.object(m, "DATA_MAP", self.output):
            points, _ = m.voer_pid_meting_uit(meetduur=0.02, delta_t=0.1,
                                            mode="continuous")
        self.assertGreater(points[0][0], 0.02)
        self.assertIn("CONFIG:40.0,0.0,0.0,0.0,120,20,100,1,180.0", arduino.commands)
        self.assertEqual(arduino.commands[-1], "STOP")
        meta = lees_header(next(self.output.glob("*.csv")))
        self.assertEqual(meta["mode"], "continuous")
        self.assertEqual(meta["regelinterval_ms"], 100)
        self.assertEqual(meta["status"], "onderbroken")

    def test_bounds_and_print_option(self):
        for limit, goal, show in ((0, -10, False), (255, 120, True)):
            clock = Clock()
            arduino = Arduino(clock, "normal")
            output = io.StringIO()
            with patch.object(m.serial, "Serial", return_value=arduino), \
                    patch.object(m, "time", clock), patch.object(m, "DATA_MAP", self.output), \
                    redirect_stdout(output):
                points, _ = m.voer_pid_meting_uit(meetduur=2, max_pwm=limit,
                                                 doelhoek=goal, beginhoek=89,
                                                 toon_metingen=show)
            self.assertIn("OFFSET:89", arduino.commands)
            self.assertTrue(all(0 <= row[3] <= limit for row in points))
            self.assertEqual("| PWM" in output.getvalue(), show)

    def test_config_transmits_full_angle_range(self):
        for goal, limit in ((-10, 0), (140, 150), (180, 180)):
            clock = Clock()
            arduino = Arduino(clock, "normal")
            with patch.object(m.serial, "Serial", return_value=arduino), \
                    patch.object(m, "time", clock), patch.object(m, "DATA_MAP", self.output):
                m.voer_pid_meting_uit(doelhoek=goal, max_hoek=limit,
                                     meetduur=2, toon_metingen=False)
            config = next(c for c in arduino.commands if c.startswith("CONFIG:"))
            self.assertEqual(float(config.split(":")[1].split(",")[0]), goal)
            self.assertEqual(float(config.split(",")[-1]), limit)

    def test_step_specific_configurations(self):
        for function, count, extra in (
                (m.voer_pid_meting_uit, 9, {}),
                (m.voer_pid_meting_uit, 9, {"max_hoek": 120})):
            with self.subTest(count=count):
                clock = Clock()
                arduino = Arduino(clock, "normal")
                original_write = arduino.write
                def strict_write(data):
                    command = data.decode().strip()
                    if command.startswith("CONFIG:"):
                        self.assertEqual(len(command[7:].split(",")), count)
                    original_write(data)
                with patch.object(arduino, "write", side_effect=strict_write), \
                        patch.object(m.serial, "Serial", return_value=arduino), \
                        patch.object(m, "time", clock), patch.object(m, "DATA_MAP", self.output):
                    points, path = function(meetduur=2, toon_metingen=False, **extra)
                self.assertTrue(points)
                self.assertEqual(arduino.commands[-1], "STOP")
                meta = lees_header(path)
                self.assertEqual(meta["max_hoek"], extra.get("max_hoek", 180.0))

    def test_safety_bounds_do_not_open_port(self):
        with patch.object(m.serial, "Serial") as port:
            for kwargs in ({"max_hoek": 39}, {"max_hoek": 181},
                           {"max_hoek": float("nan")}, {"max_hoek": -10},
                           {"doelhoek": -11}):
                with self.assertRaises(ValueError):
                    m.voer_pid_meting_uit(**kwargs)
            port.assert_not_called()

    def test_pwm_limiter_configuration_and_metadata(self):
        for rate in (0, 20, 1):
            clock = Clock()
            arduino = Arduino(clock, "normal")
            with patch.object(m.serial, "Serial", return_value=arduino), \
                    patch.object(m, "time", clock), patch.object(m, "DATA_MAP", self.output):
                _, path = m.voer_pid_meting_uit(meetduur=2, toon_metingen=False,
                                               max_hoek=120, max_pwm_stap=rate)
            self.assertIn(f"PWMSTAP:{rate}", arduino.commands)
            self.assertLess(arduino.commands.index(f"PWMSTAP:{rate}"),
                            arduino.commands.index("START"))
            self.assertEqual(lees_header(path)["max_pwm_stap"], rate)
            self.assertEqual(lees_header(path)["max_hoek"], 120)
            self.assertEqual(arduino.commands[-1], "STOP")

    def test_old_sketch_never_starts_with_requested_limiter(self):
        clock = Clock()
        arduino = Arduino(clock, "old_slew")
        with patch.object(m.serial, "Serial", return_value=arduino), \
                patch.object(m, "time", clock), patch.object(m, "DATA_MAP", self.output):
            with self.assertRaisesRegex(RuntimeError, "Stap_4_Closed_loop"):
                m.voer_pid_stap5_uit(max_pwm_stap=100)
        self.assertNotIn("START", arduino.commands)
        self.assertEqual(arduino.commands[-1], "STOP")

    def test_invalid_limiter_rate_does_not_open_port(self):
        with patch.object(m.serial, "Serial") as port:
            for rate in (-1, 256, 0.5, float("nan"), float("inf")):
                with self.assertRaises(ValueError):
                    m.voer_pid_stap5_uit(max_pwm_stap=rate)
            port.assert_not_called()

    def test_wrong_step_firmware_never_starts(self):
        for function, firmware_step in ((m.voer_pid_stap4_uit, 5),
                                        (m.voer_pid_stap5_uit, 4)):
            clock = Clock()
            arduino = Arduino(clock, "normal", step=firmware_step)
            with patch.object(m.serial, "Serial", return_value=arduino), \
                    patch.object(m, "time", clock), patch.object(m, "DATA_MAP", self.output):
                with self.assertRaisesRegex(RuntimeError, "Verkeerde of verouderde sketch"):
                    function(meetduur=2)
            self.assertNotIn("START", arduino.commands)
            self.assertEqual(arduino.commands[-1], "STOP")

    def test_step5_without_rate_sends_no_limiter_setting(self):
        clock = Clock()
        arduino = Arduino(clock, "normal")
        with patch.object(m.serial, "Serial", return_value=arduino), \
                patch.object(m, "time", clock), patch.object(m, "DATA_MAP", self.output):
            _, path = m.voer_pid_stap5_uit(meetduur=2, toon_metingen=False)
        self.assertFalse(any(c.startswith("PWMSTAP:") for c in arduino.commands))
        self.assertEqual(lees_header(path)["max_hoek"], 180.0)
        self.assertNotIn("max_pwm_stap", lees_header(path))

    def test_invalid_parameters_do_not_open_port(self):
        with patch.object(m.serial, "Serial") as port:
            for kwargs in ({"kp": -0.1}, {"kp": -1001}, {"max_pwm": 256}, {"max_pwm": -1}, {"doelhoek": 181}, {"doelhoek": -181},
                           {"meetduur": float("nan")}, {"meetduur": 0},
                           {"delta_t": 0.01}, {"delta_t": 1.1},
                           {"delta_t": float("nan")}, {"mode": "other"},
                           {"meetduur": 0.02, "delta_t": 0.1}):
                with self.assertRaises(ValueError):
                    m.voer_pid_meting_uit(**kwargs)
            port.assert_not_called()


if __name__ == "__main__":
    unittest.main()
