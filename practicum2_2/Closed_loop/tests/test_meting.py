"""Zonder hardware: python -m unittest discover -s tests -v."""

import csv
import importlib
import json
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


class Clock:
    now = 0

    def sleep(self, seconds):
        self.now += seconds

    def monotonic(self):
        return self.now


class Arduino:
    def __init__(self, clock, scenario):
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
            if self.scenario == "sensor":
                return b"ERROR:SENSOR_OR_ANGLE\n"
            if self.scenario == "bad_data":
                return b"not,a,measurement\n"
        if self.count > 12:
            return b"DONE\n"
        pwm = 0 if "CHECK" in self.commands else 20
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
        self.assertEqual(rows[0], m.KOLOMMEN)
        self.assertEqual(rows[1], ["0.1", "40.0", "10.0", "20.0"])
        meta = json.loads(next(self.output.glob("*.json")).read_text())
        self.assertEqual(meta["status"], "voltooid")
        self.assertEqual(meta["ki"], 0)

    def test_sensor_check_does_not_start_pid(self):
        arduino = self.run_case("normal", check=True)
        self.assertIn("CHECK", arduino.commands)
        self.assertNotIn("START", arduino.commands)

    def test_interrupt_preserves_data(self):
        self.run_case("interrupt")
        meta = json.loads(next(self.output.glob("*.json")).read_text())
        self.assertEqual(meta["status"], "onderbroken")

    def test_errors_stop_and_preserve_partial_data(self):
        for scenario in ("sensor", "bad_data"):
            with self.subTest(scenario=scenario):
                self.run_case(scenario, RuntimeError)
        self.assertEqual(len(list(self.output.glob("*.csv"))), 2)
        for path in self.output.glob("*.json"):
            self.assertEqual(json.loads(path.read_text())["status"], "fout")

    def test_silence_times_out(self):
        self.run_case("silence", TimeoutError)
        self.assertFalse(list(self.output.glob("*.csv")))

    def test_rejected_configuration_never_starts(self):
        arduino = self.run_case("config", RuntimeError)
        self.assertNotIn("START", arduino.commands)

    def test_invalid_parameters_do_not_open_port(self):
        with patch.object(m.serial, "Serial") as port:
            for kwargs in ({"kp": -1}, {"max_pwm": 121}, {"doelhoek": 90},
                           {"meetduur": float("nan")}, {"meetduur": 0}):
                with self.assertRaises(ValueError):
                    m.voer_pid_meting_uit(**kwargs)
            port.assert_not_called()


if __name__ == "__main__":
    unittest.main()
