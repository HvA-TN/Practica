"""PID-prestaties vergelijken en PID kiezen per doelhoek (tussen proeven)."""

import ast
import csv
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd


def lees_pid_csv(bestand):
    """Lees de actuele CSV met commentaarheader; wijzig het origineel niet."""
    instellingen = {}
    with Path(bestand).open(encoding="utf-8", newline="") as f:
        for rij in csv.reader(f):
            if not rij or not rij[0].startswith("# "):
                break
            if len(rij) != 2:
                raise ValueError("Ongeldige instellingenregel in CSV.")
            try:
                waarde = ast.literal_eval(rij[1])
            except (ValueError, SyntaxError):
                waarde = rij[1]
            instellingen[rij[0][2:]] = waarde
    nodig = {"doelhoek", "kp", "ki", "kd", "max_pwm", "max_hoek", "mode",
             "meetduur_ms", "regelinterval_ms", "hoekoffset_deg", "status"}
    if not nodig.issubset(instellingen):
        raise ValueError("Gebruik een PID-CSV met de actuele commentaarheader.")
    data = pd.read_csv(bestand, comment="#")
    if not {"tijd_s", "hoek_deg", "pwm"}.issubset(data.columns):
        raise ValueError("CSV mist tijd_s, hoek_deg of pwm.")
    return instellingen, data


def _positief(naam, waarde, nul=False):
    if not np.isfinite(waarde) or (waarde < 0 if nul else waarde <= 0):
        raise ValueError(f"{naam} moet eindig en {'niet-negatief' if nul else 'positief'} zijn.")


def beoordeel_meting(bestand, band=2.0, bevestiging_s=5.0, eindvenster_s=5.0,
                     overshoot_grens=3.0, rusthoek=0.0, rusttolerantie=3.0):
    """Beoordeel een vaste proef vanaf rust; insteltijd vereist een blijvende band.

    Een onderbroken of onvolledige proef krijgt nooit 'voldoet=True'. IAE,
    eindfout en verzadigingsduur gebruiken de geregistreerde tijdstempels.
    rusthoek is de verwachte gecorrigeerde beginhoek, doorgaans nul.
    """
    for naam, waarde in (("band", band), ("bevestiging_s", bevestiging_s),
                        ("eindvenster_s", eindvenster_s), ("rusttolerantie", rusttolerantie)):
        _positief(naam, waarde)
    _positief("overshoot_grens", overshoot_grens, nul=True)
    if not np.isfinite(rusthoek):
        raise ValueError("rusthoek moet eindig zijn.")
    instellingen, df = lees_pid_csv(bestand)
    rapport = {"bestand": str(Path(bestand).resolve()), **instellingen,
               "band_deg": band, "bevestiging_s": bevestiging_s,
               "overshoot_grens_deg": overshoot_grens, "rusthoek_deg": rusthoek,
               "overshoot_deg": np.nan, "insteltijd_s": np.nan,
               "eindfout_deg": np.nan, "eind_std_deg": np.nan,
               "iae_graden_s": np.nan, "max_pwm_duur_s": np.nan,
               "geldige_proef": False, "voldoet": False, "reden": ""}
    redenen = []
    if instellingen["status"] != "voltooid":
        redenen.append(f"status: {instellingen['status']}")
    if instellingen["mode"] != "fixed":
        redenen.append("geen vaste meetduur")
    waarden = df[["tijd_s", "hoek_deg", "pwm"]].to_numpy(dtype=float)
    if len(waarden) < 2 or not np.isfinite(waarden).all():
        rapport["reden"] = "; ".join(redenen + ["te weinig of ongeldige meetpunten"])
        return rapport
    t, hoek, pwm = waarden.T
    dt = np.diff(t)
    if t[0] < 0 or (dt <= 0).any():
        rapport["reden"] = "; ".join(redenen + ["tijdstempels lopen niet op"])
        return rapport
    doel = float(instellingen["doelhoek"])
    interval = float(instellingen["regelinterval_ms"]) / 1000
    duur = float(instellingen["meetduur_ms"]) / 1000
    limiet = float(instellingen["max_pwm"])
    if not np.isfinite([doel, interval, duur, limiet]).all() or interval <= 0 or duur <= 0:
        raise ValueError("Ongeldige tijd- of doelinstellingen in de header.")
    if t[0] > 3 * interval or abs(t[-1] - duur) > 3 * interval:
        redenen.append("registratie mist begin of einde")
    if (dt > 3 * interval + 1e-9).any():
        redenen.append("grote gaten in registratie")
    if (pwm < 0).any() or (pwm > limiet).any():
        redenen.append("PWM buiten ingestelde grenzen")
    if abs(hoek[0] - rusthoek) > rusttolerantie:
        redenen.append("eerste meetpunt niet nabij afgesproken rusthoek")
    stap = doel - rusthoek
    if abs(stap) <= band:
        redenen.append("doelhoek te dicht bij rusthoek voor deze vergelijking")
    fout = doel - hoek
    richting = 1 if stap >= 0 else -1
    rapport["overshoot_deg"] = max(0.0, float(np.max(richting * (hoek - doel))))
    rapport["iae_graden_s"] = float(np.sum((np.abs(fout[:-1]) + np.abs(fout[1:])) * dt / 2))
    rapport["max_pwm_duur_s"] = float(np.sum(dt[pwm[:-1] >= limiet - 0.5]))
    buiten = np.flatnonzero(np.abs(fout) > band)
    begin_band = int(buiten[-1] + 1) if len(buiten) else 0
    if begin_band < len(t) and t[-1] - t[begin_band] >= bevestiging_s - 1e-9:
        rapport["insteltijd_s"] = float(t[begin_band])
    if t[-1] - t[0] >= eindvenster_s:
        start = t[-1] - eindvenster_s
        selectie = t > start
        eind_t = np.r_[start, t[selectie]]
        eind_h = np.r_[np.interp(start, t, hoek), hoek[selectie]]
        d = np.diff(eind_t)
        gemiddeld = float(np.sum((eind_h[:-1] + eind_h[1:]) * d / 2) / eindvenster_s)
        variantie = np.sum(((eind_h[:-1] - gemiddeld)**2 +
                            (eind_h[1:] - gemiddeld)**2) * d / 2) / eindvenster_s
        rapport["eindfout_deg"] = doel - gemiddeld
        rapport["eind_std_deg"] = float(np.sqrt(max(0, variantie)))
    else:
        redenen.append("registratie te kort voor eindvenster")
    rapport["geldige_proef"] = not redenen
    if not np.isfinite(rapport["insteltijd_s"]):
        redenen.append("niet aantoonbaar ingesteld")
    if rapport["overshoot_deg"] > overshoot_grens:
        redenen.append("te veel overshoot")
    rapport["voldoet"] = not redenen
    rapport["reden"] = "; ".join(redenen) if redenen else "voldoet"
    return rapport


def maak_meetplan(doelhoek, kp_waarden, ki_waarden, kd_waarden, herhalingen=3):
    """Maak een rooster; dit voert geen metingen uit."""
    if not np.isfinite(doelhoek) or not -180 <= doelhoek <= 180:
        raise ValueError("Doelhoek moet tussen -180 en 180 liggen.")
    if not isinstance(herhalingen, int) or herhalingen < 1:
        raise ValueError("Herhalingen moet een positief geheel getal zijn.")
    reeksen = [list(dict.fromkeys(v)) for v in (kp_waarden, ki_waarden, kd_waarden)]
    if any(not v or any(not np.isfinite(x) or not 0 <= x <= 1000 for x in v) for v in reeksen):
        raise ValueError("Gebruik niet-lege reeksen PID-waarden tussen 0 en 1000.")
    rijen = []
    for herhaling in range(1, herhalingen + 1):
        for kandidaat, (kp, ki, kd) in enumerate(product(*reeksen), 1):
            rijen.append(dict(proef=len(rijen)+1, kandidaat=kandidaat,
                              herhaling=herhaling, doelhoek=doelhoek, kp=kp, ki=ki, kd=kd))
    return pd.DataFrame(rijen)


def vergelijk_metingen(bestanden, min_herhalingen=3, **criteria):
    """Rangschik PID-combinaties per doelhoek. Alle herhalingen moeten voldoen.

    Bestandspaden worden ontdubbeld. Verschillende meetduur, nulstelling, PWM-
    of hoekgrenzen worden geweigerd: houd de proefomstandigheden gelijk.
    """
    paden = list(dict.fromkeys(str(Path(p).resolve()) for p in bestanden))
    if not paden:
        raise ValueError("Voeg eerst meetbestanden toe.")
    if not isinstance(min_herhalingen, int) or min_herhalingen < 1:
        raise ValueError("min_herhalingen moet positief en geheel zijn.")
    details = pd.DataFrame([beoordeel_meting(p, **criteria) for p in paden])
    for kolom in ("meetduur_ms", "regelinterval_ms", "max_pwm", "max_hoek", "hoekoffset_deg"):
        if details[kolom].nunique(dropna=False) != 1:
            raise ValueError(f"Vergelijkbare proeven vereisen gelijke {kolom}.")
    rijen = []
    for sleutel, groep in details.groupby(["doelhoek", "kp", "ki", "kd"], sort=True):
        rijen.append(dict(zip(("doelhoek", "kp", "ki", "kd"), sleutel)) | {
            "aantal": len(groep), "aantal_voldoet": int(groep.voldoet.sum()),
            "geschikt": len(groep) >= min_herhalingen and bool(groep.voldoet.all()),
            "insteltijd_mediaan_s": groep.insteltijd_s.median(),
            "insteltijd_max_s": groep.insteltijd_s.max(),
            "overshoot_max_deg": groep.overshoot_deg.max(),
            "eindfout_abs_max_deg": groep.eindfout_deg.abs().max(),
        })
    ranglijst = pd.DataFrame(rijen).sort_values(
        ["doelhoek", "geschikt", "insteltijd_mediaan_s", "overshoot_max_deg"],
        ascending=[True, False, True, True], na_position="last").reset_index(drop=True)
    return details, ranglijst


def maak_gain_schema(ranglijst):
    """Selecteer per doelhoek de snelste geschikte combinatie; geen fallback."""
    geschikt = ranglijst[ranglijst["geschikt"]].sort_values(
        ["doelhoek", "insteltijd_mediaan_s", "overshoot_max_deg"])
    ontbreekt = set(ranglijst.doelhoek) - set(geschikt.doelhoek)
    if ontbreekt:
        raise ValueError(f"Geen geschikte PID bij doelhoek(en): {sorted(ontbreekt)}")
    if geschikt.empty:
        raise ValueError("Nog geen geschikte PID-instellingen gemeten.")
    return geschikt.drop_duplicates("doelhoek")[["doelhoek", "kp", "ki", "kd"]].reset_index(drop=True)


def kies_pid(doelhoek, schema, methode="dichtstbij"):
    """Gain scheduling op doelhoek, voorafgaand aan een proef.

    'dichtstbij' gebruikt een gemeten instelling. 'lineair' interpoleert elke
    gain afzonderlijk; die nieuwe combinatie moet nog worden getest.
    Buiten het gemeten bereik wordt niet geextrapoleerd.
    """
    if methode not in ("dichtstbij", "lineair"):
        raise ValueError("Kies dichtstbij of lineair.")
    tabel = pd.DataFrame(schema)[["doelhoek", "kp", "ki", "kd"]].sort_values("doelhoek")
    if tabel.empty or not np.isfinite(tabel.to_numpy(dtype=float)).all():
        raise ValueError("Schema moet eindige getallen bevatten.")
    if tabel.doelhoek.duplicated().any() or not tabel.doelhoek.between(-180, 180).all():
        raise ValueError("Gebruik unieke doelhoeken tussen -180 en 180.")
    if not ((tabel[["kp", "ki", "kd"]] >= 0) & (tabel[["kp", "ki", "kd"]] <= 1000)).all().all():
        raise ValueError("PID-waarden moeten tussen 0 en 1000 liggen.")
    if not np.isfinite(doelhoek) or not tabel.doelhoek.min() <= doelhoek <= tabel.doelhoek.max():
        raise ValueError("Doelhoek ligt buiten het gemeten scheduling-bereik.")
    if methode == "lineair":
        return {k: float(np.interp(doelhoek, tabel.doelhoek, tabel[k])) for k in ("kp", "ki", "kd")}
    rij = tabel.iloc[int(np.argmin(np.abs(tabel.doelhoek.to_numpy() - doelhoek)))]
    return {k: float(rij[k]) for k in ("kp", "ki", "kd")}
