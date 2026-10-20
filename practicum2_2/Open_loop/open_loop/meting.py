"""Seriële aansturing, hoekmetingen en CSV-opslag."""

import csv
import math
import time
from datetime import datetime
from pathlib import Path

import serial

DATA_MAP = Path(__file__).resolve().parent.parent / "data"


def stuur_commando(arduino, commando):
    """Verstuur één commando naar de Arduino."""
    arduino.write(f"{commando}\n".encode("utf-8"))


def _wacht_met_heartbeat(arduino, duur):
    einde = time.monotonic() + duur
    while time.monotonic() < einde:
        stuur_commando(arduino, "PING")
        time.sleep(min(0.5, max(0, einde - time.monotonic())))


def _lees_metingen(arduino, metingen, meetduur, toon_metingen):
    starttijd = time.monotonic()
    laatste_ping = starttijd
    tijd_nul = None
    while True:
        nu = time.monotonic()
        if meetduur is not None and nu - starttijd >= meetduur:
            return
        if nu - laatste_ping >= 0.5:
            stuur_commando(arduino, "PING")
            laatste_ping = nu
        regel = arduino.readline().decode("utf-8", errors="ignore").strip()
        if not regel:
            continue
        if regel == "DEBUG_WATCHDOG":
            raise RuntimeError("De Arduino-watchdog heeft de motor en meting gestopt.")
        try:
            tijd_ms, hoek = map(float, regel.split(","))
        except ValueError:
            if regel.startswith("DEBUG_"):
                print(regel)
            continue
        if tijd_nul is None:
            tijd_nul = tijd_ms
        tijd_s = ((tijd_ms - tijd_nul) % (2**32)) / 1000
        metingen.append([tijd_s, hoek])
        if toon_metingen:
            print(f"{tijd_s:8.3f} s | {hoek:8.3f} graden")


def sla_csv_op(metingen, bestandsnaam=None):
    """Sla metingen in de data-map op en retourneer het bestandspad."""
    DATA_MAP.mkdir(parents=True, exist_ok=True)
    if bestandsnaam is None:
        bestandsnaam = f"aeropendulum_{datetime.now():%Y%m%d_%H%M%S_%f}.csv"
    naam = Path(bestandsnaam)
    if naam.name != str(bestandsnaam) or naam.suffix.lower() != ".csv":
        raise ValueError("Gebruik een bestandsnaam met .csv, zonder mappad.")
    pad = DATA_MAP / naam
    with pad.open("x", newline="", encoding="utf-8") as bestand:
        schrijver = csv.writer(bestand)
        schrijver.writerow(["tijd_s", "hoek_deg"])
        schrijver.writerows(metingen)
    print(f"CSV opgeslagen: {pad}")
    return pad


def voer_open_loop_meting_uit(com_poort="COM3", baudrate=115200, pwm=20, meetduur=5.0,
         delta_t=0.01, stabilisatietijd=2.0, opslaan=True,
         bestandsnaam=None, toon_metingen=True):
    """Meet gedurende meetduur seconden; None meet tot een interrupt.

    Retourneert (metingen, csv_pad). Bij een interrupt blijven de verzamelde
    metingen bewaard. De motor wordt ook bij fouten uitgeschakeld en reeds
    ontvangen data wordt opgeslagen als opslaan=True.
    """
    if not isinstance(pwm, int) or not 0 <= pwm <= 255:
        raise ValueError("PWM moet een geheel getal tussen 0 en 255 zijn.")
    if meetduur is not None and (not math.isfinite(meetduur) or meetduur <= 0):
        raise ValueError("Meetduur moet positief zijn, of None voor continu meten.")
    if not math.isfinite(delta_t) or not 0.01 <= delta_t <= 60:
        raise ValueError("Delta_t moet tussen 0.01 en 60 seconden liggen.")
    if not math.isfinite(stabilisatietijd) or stabilisatietijd < 0:
        raise ValueError("Stabilisatietijd moet nul of positief zijn.")

    metingen = []
    csv_pad = None
    try:
        with serial.Serial(com_poort, baudrate, timeout=0.1) as arduino:
            try:
                time.sleep(2)  # Arduino start opnieuw bij openen van de poort.
                stuur_commando(arduino, f"DT:{round(delta_t * 1000)}")
                stuur_commando(arduino, f"PWM:{pwm}")
                print(f"PWM: {pwm}; stabiliseren: {stabilisatietijd} s")
                _wacht_met_heartbeat(arduino, stabilisatietijd)
                arduino.reset_input_buffer()
                stuur_commando(arduino, "START")
                print("Meting gestart. Onderbreek de notebookcel om te stoppen.")
                _lees_metingen(arduino, metingen, meetduur, toon_metingen)
            except KeyboardInterrupt:
                print("Meting handmatig gestopt.")
            finally:
                stuur_commando(arduino, "STOP")
                arduino.flush()
                time.sleep(0.1)
                print("STOP verzonden naar de Arduino.")
    finally:
        if opslaan and metingen:
            csv_pad = sla_csv_op(metingen, bestandsnaam)
    print(f"Aantal metingen: {len(metingen)}")
    return metingen, csv_pad
