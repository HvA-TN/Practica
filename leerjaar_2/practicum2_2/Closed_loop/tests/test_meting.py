import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import types
try:
    import serial
except ImportError:
    sys.modules["serial"] = types.SimpleNamespace(Serial=None)
from leerjaar_2.practicum2_2.Closed_loop.closed_loop import meting

class HoekTest(unittest.TestCase):
    def test_hoek_gebruikt_stap3_met_motor_uit(self):
        with patch.object(meting, "voer_open_loop_meting_uit", return_value=([[0, 90]], None)) as run:
            self.assertEqual(meting.test_hoek("COM5", 10, 0.1), [[0, 90]])
        self.assertEqual(run.call_args.kwargs["pwm"], 0)
        self.assertEqual(run.call_args.kwargs["meetduur"], 10)
        self.assertEqual(run.call_args.kwargs["delta_t"], 0.1)

    def test_hoek_doorloopt_meting_en_verstuurt_stop(self):
        import io
        from contextlib import redirect_stdout
        class Clock:
            now = 0
            def monotonic(self): return self.now
            def sleep(self, seconds): self.now += seconds
        clock = Clock()
        class Arduino:
            def __init__(self): self.commands = []; self.actief = False
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def reset_input_buffer(self): pass
            def flush(self): pass
            def write(self, data):
                command = data.decode().strip()
                self.commands.append(command)
                if command == "START": self.actief = True
                if command == "STOP": self.actief = False
            def readline(self):
                clock.now += 0.1
                if not self.actief: return b""
                return f"{round(clock.now * 1000)},123.5\n".encode()
        arduino = Arduino()
        with patch.object(meting.serial, "Serial", return_value=arduino), \
                patch.object(meting, "time", clock), \
                patch.object(meting, "sla_csv_op", return_value=None) as save, \
                redirect_stdout(io.StringIO()):
            points = meting.test_hoek("COM4", meetduur=1, delta_t=0.1)
        self.assertTrue(points)
        self.assertEqual(points[0], [0, 123.5])
        self.assertIn("PWM:0", arduino.commands)
        self.assertIn("DT:100", arduino.commands)
        self.assertIn("START", arduino.commands)
        self.assertEqual(arduino.commands[-1], "STOP")
        self.assertFalse(any(c.startswith("CONFIG:") for c in arduino.commands))
        save.assert_called_once()
