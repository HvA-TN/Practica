"""Exercise the actual step-5 firmware using a simulated Arduino and PID target."""
from pathlib import Path
import shutil
import subprocess
import unittest
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


class FirmwareTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("g++"), "g++ is required for firmware simulation")
    def test_rate_limits_and_all_stop_paths(self):
        sketch = ROOT / "arduino/Stap_5_PWM_begrenzing/Stap_5_PWM_begrenzing.ino"
        source = "\n".join(line for line in sketch.read_text(encoding="utf-8").splitlines()
                           if not line.startswith("#include"))
        stub = (ROOT / "tests/arduino_stub.h").read_text(encoding="utf-8")
        cases = r"""
void startTest(){
 testTime=0;testTarget=120;setup();verwerkCommando("HELLO");
 verwerkCommando("CONFIG:20,2,0,0,120,30000,20,0,180");
 verwerkCommando("PWMSTAP:20");verwerkCommando("START");assert(pidActief && motor==0);
}
int main(){
 assert(maxPWMStap==0);
 startTest();verwerkCommando("HELLO");assert(maxPWMStap==0);
 verwerkCommando("CONFIG:20,2,0,0,120,30000,20,0,180");
 verwerkCommando("START");testTime=20;loop();assert(pwm==120);
 startTest();verwerkCommando("STOP");
 verwerkCommando("CONFIG:20,2,0,0,120,30000,20,0,180");assert(maxPWMStap==0);
 startTest();testTime=20;loop();assert(pwm==20);
 testTime=40;loop();assert(pwm==40);
 testTime=90;loop();assert(pwm==60); // Actual elapsed time: 50 ms.
 testTarget=5;testTime=110;loop();assert(pwm==5); // Large downward step immediate.
 testTarget=120;testTime=130;loop();assert(pwm==25); // Upward limit still applies after falling.
 testTarget=0;testTime=150;loop();assert(pwm==0); // Down to zero immediately.
 verwerkCommando("STOP");assert(motor==0 && toegepastePWM==0 && !pidActief);
 startTest();testTarget=7;testTime=20;loop();assert(pwm==7); // Small change immediate.
 startTest();maxPWMStap=1;testTime=20;loop();assert(pwm==1);
 testTime=40;loop();assert(pwm==2);
 startTest();maxPWMStap=0;testTime=20;loop();assert(pwm==120);
 startTest();testTime=20;loop();testTime=4000;loop();
 assert(motor==0 && toegepastePWM==0 && !meten && !pidActief); // Watchdog.
 startTest();testTime=20;loop();maxHoek=-1;testTime=40;loop();
 assert(motor==0 && toegepastePWM==0 && hoekStop); // Maximum angle.
 startTest();meetduur_ms=40;testTime=20;loop();testTime=40;loop();
 assert(motor==0 && toegepastePWM==0 && !meten); // End of measurement.
 startTest();testTime=20;loop();verwerkCommando("HELLO");assert(motor==0 && toegepastePWM==0);
 startTest();testTime=20;loop();verwerkCommando("OFFSET:90");assert(motor==0 && toegepastePWM==0);
 startTest();testTime=20;loop();verwerkCommando("CONFIG:20,2,0,0,120,30000,20,0,180");
 assert(motor==0 && toegepastePWM==0);
 startTest();testTime=20;loop();verwerkCommando("PWMSTAP:1");assert(maxPWMStap==20);
 return 0;
}
"""
        output = ROOT / ".test_output"
        output.mkdir(exist_ok=True)
        binary = output / ("firmware_" + uuid4().hex + ".exe")
        try:
            compiled = subprocess.run(["g++", "-std=c++17", "-x", "c++", "-", "-o", str(binary)],
                                      input=stub + source + cases, text=True, capture_output=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(executed.returncode, 0, executed.stderr)
        finally:
            if binary.exists():
                binary.unlink()
            if output.exists() and not any(output.iterdir()):
                output.rmdir()
