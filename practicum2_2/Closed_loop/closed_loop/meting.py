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


def test_hoek(com_poort="COM3", meetduur=10.0, delta_t=0.1):
    """Meet de ruwe hoek met stap 3 of de nieuwe stap 4-basis; PWM blijft nul.

    Retourneert tijd/hoek-paren. Tijd komt van de Arduino, relatief aan het
    eerste meetpunt. CSV wordt automatisch opgeslagen in Closed_loop/data.
    """
    metingen, _ = voer_open_loop_meting_uit(
        com_poort=com_poort, pwm=0, meetduur=meetduur, delta_t=delta_t,
        stabilisatietijd=0, opslaan=True, toon_metingen=True)
    return metingen


KOLOMMEN = ["tijd_s", "hoek_deg", "pwm"]


def _stuur(arduino, commando):
    arduino.write(f"{commando}\n".encode("ascii"))


def _lees(arduino):
    regel = arduino.readline().decode("ascii", errors="strict").strip()
    if regel == "ERROR:MAX_HOEK":
        raise RuntimeError("Hoekbeveiliging: de werkhoek overschrijdt max_hoek of is ongeldig. Motor uit; controleer de opstelling voordat je opnieuw start.")
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
        # Commentaarheader: een instelling per regel, in hetzelfde CSV-bestand.
        for sleutel, waarde in {**instellingen, "status": status}.items():
            schrijver.writerow([f"# {sleutel}", waarde])
        schrijver.writerow(KOLOMMEN)
        schrijver.writerows((tijd, hoek, pwm) for tijd, doel, hoek, pwm in metingen)
    print(f"Meetdata en instellingen: {pad}")
    return pad


def voer_pid_stap4_uit(com_poort="COM4", doelhoek=40.0, kp=0.0, ki=0.0,
                       kd=0.0, max_pwm=120, meetduur=30.0, sensorcontrole=False,
                       delta_t=0.02, mode="fixed", beginhoek=90.0,
                       toon_metingen=True, max_hoek=180.0):
    """Stap 4: PID zonder PWM-veranderingsbegrenzing; upload Stap_4_PID.ino."""
    return _voer_pid_meting_uit(
        com_poort, doelhoek, kp, ki, kd, max_pwm, meetduur, sensorcontrole,
        delta_t, mode, beginhoek, toon_metingen, max_hoek,
        max_pwm_stap=None, _stap=4)


def voer_pid_stap5_uit(com_poort="COM4", doelhoek=40.0, kp=0.0, ki=0.0,
                       kd=0.0, max_pwm=120, meetduur=30.0, sensorcontrole=False,
                       delta_t=0.02, mode="fixed", beginhoek=90.0,
                       toon_metingen=True, max_hoek=180.0, max_pwm_stap=None):
    """Stap 5: PID met PWM-limiter; upload Stap_5_PWM_begrenzing.ino.

    max_pwm_stap is de maximale positieve sprong per regelstap (geheel getal 1-255).
    Laat max_pwm_stap weg voor een proef zonder limiter: er wordt geen PWMSTAP verstuurd.
    Geef een positieve waarde op om de limiter in te schakelen; max_pwm is de amplitudegrens.
    """
    return _voer_pid_meting_uit(
        com_poort, doelhoek, kp, ki, kd, max_pwm, meetduur, sensorcontrole,
        delta_t, mode, beginhoek, toon_metingen, max_hoek,
        max_pwm_stap=max_pwm_stap, _stap=5)


# Compatibiliteit voor bestaande verdiepingsnotebooks: dit is uitsluitend stap 4.
voer_pid_meting_uit = voer_pid_stap4_uit


def _voer_pid_meting_uit(com_poort="COM3", doelhoek=40.0, kp=0.0, ki=0.0,
                       kd=0.0, max_pwm=120, meetduur=30.0, sensorcontrole=False,
                       delta_t=0.02, mode="fixed", beginhoek=90.0, toon_metingen=True, max_hoek=180.0,
                       max_pwm_stap=None, _stap=4):
    """Retourneer (meetpunten, csv_pad); sla data en instellingen automatisch op.

    Zonder PWM-limiter: Stap_4_PID.ino. Met max_pwm_stap: Stap_5_PWM_begrenzing.ino.
    Stap 4 gebruikt geen limiter; stap 5 verstuurt PWMSTAP alleen bij een opgegeven instelling.
    Bij stap 5 schakelt 0 de limiter uit.
    De begrenzing geldt alleen omhoog; dalende PWM wordt direct overgenomen.
    Gebruik voor de hoekopdrachten Stap_4_PID.ino. max_hoek is standaard 180;
    geef bijvoorbeeld max_hoek=120 mee om de stopgrens te verlagen.
    Delta T bepaalt het meet- en PID-interval (0.02-1 s).
    Fixed stopt na meetduur; continuous loopt tot een celonderbreking.
    toon_metingen toont tijd, werkhoek, doelhoek, PWM en duty cycle.
    max_pwm begrenst de PID-uitgang (0-255; nul houdt de motor uit). Bij sensorcontrole blijft
    de motor uit. Onderbreken bewaart de ontvangen data en probeert STOP te sturen.
    De doelhoek en PWM-grens worden door de Arduino gecontroleerd.
    Werkhoek = sensorhoek - beginhoek, omgerekend naar -180..180 graden.
    """
    if max_pwm_stap is not None and (
            not isinstance(max_pwm_stap, int) or isinstance(max_pwm_stap, bool) or not 0 <= max_pwm_stap <= 255):
        raise ValueError("max_pwm_stap moet een geheel getal van 0 tot 255 zijn, of None.")
    if sensorcontrole:
        raise ValueError("Gebruik test_hoek() voor een meting zonder PID.")
    if mode not in ("fixed", "continuous"):
        raise ValueError("mode moet fixed of continuous zijn.")
    waarden = (doelhoek, kp, ki, kd, meetduur, delta_t, beginhoek, max_hoek)
    if not all(math.isfinite(v) for v in waarden):
        raise ValueError("Alle instellingen moeten eindige getallen zijn.")
    if not -10 < max_hoek <= 180:
        raise ValueError("max_hoek moet groter dan -10 en maximaal 180 graden zijn.")
    if not -10 <= doelhoek <= max_hoek:
        raise ValueError("Doelhoek moet tussen minHoek (-10) en max_hoek liggen.")
    if not all(0 <= v <= 1000 for v in (kp, ki, kd)):
        raise ValueError("PID-parameters moeten tussen 0 en 1000 liggen.")
    if not isinstance(max_pwm, int) or not 0 <= max_pwm <= 255:
        raise ValueError("max_pwm moet een geheel getal tussen 0 en 255 zijn.")
    if not 0.02 <= meetduur <= 600:
        raise ValueError("Meetduur moet tussen 0.02 en 600 seconden liggen.")
    if not 0.02 <= delta_t <= 1:
        raise ValueError("delta_t moet tussen 0.02 en 1 seconde liggen.")
    if not 0 <= beginhoek < 360:
        raise ValueError("Beginhoek moet tussen 0 en 360 graden liggen (360 uitgesloten).")
    duur_ms = round(meetduur * 1000)
    interval_ms = round(delta_t * 1000)
    if mode == "fixed" and duur_ms < interval_ms:
        raise ValueError("Meetduur moet minstens delta_t zijn.")
    instellingen = dict(com_poort=com_poort, doelhoek=doelhoek, kp=kp, ki=ki,
                        kd=kd, max_pwm=max_pwm, meetduur_ms=duur_ms,
                        sensorcontrole=sensorcontrole, regelinterval_ms=interval_ms, mode=mode,
                        max_hoek=max_hoek, hoekoffset_deg=beginhoek, hoekgrenzen_deg=[-180, 180], toon_metingen=toon_metingen)
    if max_pwm_stap is not None:
        instellingen["max_pwm_stap"] = max_pwm_stap
    instellingen["stap"] = _stap
    print(f"Stap {_stap}: max_pwm={max_pwm}, limiter="
          f"{max_pwm_stap if max_pwm_stap is not None else 'uit'} telwaarden/regelstap")
    if max_pwm == 0:
        print("max_pwm=0: communicatieproef; motoruitgang blijft nul.")
    metingen = []
    csv_pad = None
    status = "fout"
    try:
        with serial.Serial(com_poort, 115200, timeout=0.1, write_timeout=1) as arduino:
            try:
                time.sleep(2)
                arduino.reset_input_buffer()
                _commando(arduino, "HELLO", "PID_READY")
                try:
                    _commando(arduino, "VERSIE", f"PID_STAP{_stap}")
                except (RuntimeError, TimeoutError) as exc:
                    sketch = "Stap_4_PID.ino" if _stap == 4 else "Stap_5_PWM_begrenzing.ino"
                    raise RuntimeError(
                        f"Verkeerde of verouderde sketch: stap {_stap} verwacht {sketch}. "
                        "Upload de bijgewerkte sketch. De motor is niet gestart."
                    ) from exc
                _commando(arduino, f"OFFSET:{beginhoek}", "OFFSET_OK")
                config = (f"CONFIG:{doelhoek},{kp},{ki},{kd},{max_pwm},{duur_ms},"
                          f"{interval_ms},{int(mode == 'continuous')},{max_hoek}")
                try:
                    _commando(arduino, config, "CONFIG_OK")
                except RuntimeError as exc:
                    if "ERROR:CONFIG" in str(exc):
                        raise RuntimeError(
                            f"PID-configuratie geweigerd: {config}. "
                            "Controleer instellingen en upload de gezamenlijke Stap_4_PID-sketch."
                        ) from exc
                    raise
                if max_pwm_stap is not None:
                    try:
                        _commando(arduino, f"PWMSTAP:{max_pwm_stap}", "PWMSTAP_OK")
                    except (RuntimeError, TimeoutError) as exc:
                        raise RuntimeError(
                            "PWM-limiter niet bevestigd. Upload Stap_5_PWM_begrenzing.ino."
                        ) from exc
                _commando(arduino, "START", "STARTED")
                print("Sensorcontrole gestart." if sensorcontrole else "PID-meting gestart.")
                begin = laatste_ping = laatste_data = time.monotonic()
                while True:
                    nu = time.monotonic()
                    if mode == "fixed" and nu - begin > meetduur + 3:
                        raise TimeoutError("De Arduino heeft geen DONE gemeld.")
                    if nu - laatste_data > 2:
                        raise TimeoutError("Langer dan 2 seconden geen meetgegevens ontvangen.")
                    if nu - laatste_ping >= 0.5:
                        _stuur(arduino, "PING")
                        laatste_ping = nu
                    regel = _lees(arduino)
                    if regel == "DONE":
                        if mode == "continuous":
                            raise RuntimeError("Onverwachte DONE in continuous mode.")
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
                    if (tijd_ms < 0 or (mode == "fixed" and tijd_ms > duur_ms) or
                            (metingen and tijd_ms / 1000 <= metingen[-1][0]) or
                            not 0 <= pwm <= max_pwm or (sensorcontrole and pwm != 0)):
                        raise RuntimeError("Ongeldig tijdstip of ongeldige PWM ontvangen.")
                    metingen.append([tijd_ms / 1000, doel, hoek, pwm])
                    if toon_metingen:
                        print(f"{tijd_ms / 1000:8.3f} s | hoek {hoek:8.3f} graden | "
                              f"doel {doel:8.3f} graden | PWM {pwm:3.0f} "
                              f"({100 * pwm / 255:5.1f}%)", flush=True)
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


