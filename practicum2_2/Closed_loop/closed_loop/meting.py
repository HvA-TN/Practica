"""PID-instellingen versturen en metingen opslaan; de Arduino regelt."""

import csv
import json
import math
import time
from datetime import datetime
from pathlib import Path

import serial

DATA_MAP = Path(__file__).resolve().parent.parent / "data"
KOLOMMEN = ["tijd_s", "doelhoek_deg", "hoek_deg", "pwm"]


def _stuur(arduino, commando):
    arduino.write(f"{commando}\n".encode("ascii"))


def _lees(arduino):
    regel = arduino.readline().decode("ascii", errors="strict").strip()
    if regel.startswith("ERROR:"):
        raise RuntimeError(f"Arduino heeft de meting gestopt: {regel}")
    return regel


def _commando(arduino, commando, antwoord):
    _stuur(arduino, commando)
    einde = time.monotonic() + 3
    while time.monotonic() < einde:
        regel = _lees(arduino)
        if regel == antwoord:
            return
        if regel:
            raise RuntimeError(f"Onverwacht Arduino-antwoord: {regel!r}")
    raise TimeoutError(f"Geen {antwoord} ontvangen. Controleer poort en PID-sketch.")


def _bewaar(metingen, instellingen, status):
    DATA_MAP.mkdir(parents=True, exist_ok=True)
    naam = f"pid_{datetime.now():%Y%m%d_%H%M%S_%f}"
    pad = DATA_MAP / f"{naam}.csv"
    with pad.open("x", newline="", encoding="utf-8") as bestand:
        schrijver = csv.writer(bestand)
        schrijver.writerow(KOLOMMEN)
        schrijver.writerows(metingen)
    with pad.with_suffix(".json").open("x", encoding="utf-8") as bestand:
        json.dump({**instellingen, "status": status}, bestand, indent=2)
    print(f"Meetdata: {pad}\nInstellingen: {pad.with_suffix('.json')}")
    return pad


def voer_pid_meting_uit(com_poort="COM3", doelhoek=40.0, kp=2.0, ki=0.0,
                       kd=0.0, max_pwm=120, meetduur=30.0, sensorcontrole=False):
    """Retourneer (meetpunten, csv_pad); sla data en instellingen automatisch op.

    De Arduino voert de PID uit op nominaal 50 Hz. Bij sensorcontrole blijft
    de motor uit. Onderbreken bewaart de ontvangen data en probeert STOP te sturen.
    Grenzen voor hoek en PWM worden ook door de Arduino gecontroleerd.
    """
    waarden = (doelhoek, kp, ki, kd, meetduur)
    if not all(math.isfinite(v) for v in waarden):
        raise ValueError("Alle instellingen moeten eindige getallen zijn.")
    if not -10 <= doelhoek <= 80:
        raise ValueError("Doelhoek moet tussen -10 en 80 graden liggen.")
    if not all(0 <= v <= 1000 for v in (kp, ki, kd)):
        raise ValueError("PID-parameters moeten tussen 0 en 1000 liggen.")
    if not isinstance(max_pwm, int) or not 1 <= max_pwm <= 120:
        raise ValueError("max_pwm moet een geheel getal tussen 1 en 120 zijn.")
    if not 0.02 <= meetduur <= 600:
        raise ValueError("Meetduur moet tussen 0.02 en 600 seconden liggen.")
    duur_ms = round(meetduur * 1000)
    instellingen = dict(com_poort=com_poort, doelhoek=doelhoek, kp=kp, ki=ki,
                        kd=kd, max_pwm=max_pwm, meetduur_ms=duur_ms,
                        sensorcontrole=sensorcontrole, regelinterval_ms=20,
                        hoekoffset_deg=90, hoekgrenzen_deg=[-10, 80])
    metingen = []
    csv_pad = None
    status = "fout"
    try:
        with serial.Serial(com_poort, 115200, timeout=0.1, write_timeout=1) as arduino:
            try:
                time.sleep(2)
                arduino.reset_input_buffer()
                _commando(arduino, "HELLO", "PID_READY")
                config = f"CONFIG:{doelhoek},{kp},{ki},{kd},{max_pwm},{duur_ms}"
                _commando(arduino, config, "CONFIG_OK")
                _commando(arduino, "CHECK" if sensorcontrole else "START", "STARTED")
                print("Sensorcontrole gestart." if sensorcontrole else "PID-meting gestart.")
                begin = laatste_ping = laatste_data = time.monotonic()
                while True:
                    nu = time.monotonic()
                    if nu - begin > meetduur + 3:
                        raise TimeoutError("De Arduino heeft geen DONE gemeld.")
                    if nu - laatste_data > 2:
                        raise TimeoutError("Langer dan 2 seconden geen meetgegevens ontvangen.")
                    if nu - laatste_ping >= 0.5:
                        _stuur(arduino, "PING")
                        laatste_ping = nu
                    regel = _lees(arduino)
                    if regel == "DONE":
                        if not metingen:
                            raise RuntimeError("De Arduino heeft geen meetpunten verstuurd.")
                        status = "voltooid"
                        break
                    if not regel:
                        continue
                    try:
                        tijd_ms, doel, hoek, pwm = map(float, regel.split(","))
                    except ValueError as exc:
                        raise RuntimeError(f"Ongeldige meetregel: {regel!r}") from exc
                    if not all(math.isfinite(v) for v in (tijd_ms, doel, hoek, pwm)):
                        raise RuntimeError("Niet-eindige waarde ontvangen.")
                    if (tijd_ms < 0 or tijd_ms > duur_ms or
                            (metingen and tijd_ms / 1000 <= metingen[-1][0]) or
                            not 0 <= pwm <= max_pwm or (sensorcontrole and pwm != 0)):
                        raise RuntimeError("Ongeldig tijdstip of ongeldige PWM ontvangen.")
                    metingen.append([tijd_ms / 1000, doel, hoek, pwm])
                    laatste_data = time.monotonic()
            except KeyboardInterrupt:
                status = "onderbroken"
                print("Meting handmatig gestopt.")
            finally:
                try:
                    _stuur(arduino, "STOP")
                    arduino.flush()
                except (serial.SerialException, OSError) as exc:
                    print(f"STOP kon niet worden verzonden: {exc}")
    finally:
        if metingen:
            csv_pad = _bewaar(metingen, instellingen, status)
    print(f"Aantal meetpunten: {len(metingen)}")
    return metingen, csv_pad


def controleer_sensor(com_poort="COM3", meetduur=5.0):
    """Lees de werkhoek uit met de motor uit; sla de controlemeting op."""
    return voer_pid_meting_uit(com_poort=com_poort, meetduur=meetduur,
                              sensorcontrole=True)
