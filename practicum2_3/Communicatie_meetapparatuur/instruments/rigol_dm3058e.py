import numpy as np
import time
def measure_vrms(dmm):
    """
    Meet 1 keer de AC-RMS spanning met de Rigol DM3058E.

    Parameters
    ----------
    dmm : PyVISA instrument
        De geopende multimeter.

    Returns
    -------
    numpy.ndarray
        Array met gemeten Vrms-waarde.
    """

    dmm.write("*CLS")      # Fouten/resetstatus wissen
    dmm.write("ABORt")     # Stop eventuele eerdere metingen

    # Kies meetmodus: AC-spanning (True RMS)
    dmm.write("CONF:VOLT:AC")

    # Kies een snelle integratietijd (lagere NPLC = sneller, maar iets meer ruis)
    dmm.write("VOLT:AC:NPLC 0.01")

    # Autorange uit (anders wordt elke meting langzamer)
    dmm.write("VOLT:AC:RANG:AUTO OFF")

    # Vast bereik kiezen; 10 V is goed voor signalen tot ca. 7 V RMS
    dmm.write("VOLT:AC:RANG 10")

    return float(dmm.query("MEAS:VOLT:AC?"))

def measure_vrms_n(dmm, n=5):
    """
    Meet n keer de AC-RMS spanning met de Rigol DM3058E.

    Parameters
    ----------
    dmm : pyvisa instrument
        Verbonden multimeterobject.
    n : int
        Aantal metingen dat wordt uitgevoerd.

    Returns
    -------
    numpy.ndarray
        Array met n opeenvolgende RMS-metingen.
    """

    # --- Multimeter instellen ---
    dmm.write("*CLS")             # Wis foutmeldingen
    dmm.write("ABORt")            # Stop eventuele eerdere metingen
    dmm.write("CONF:VOLT:AC")     # Configureer AC Vrms-metingen
    dmm.write("VOLT:AC:NPLC 0.01")# Snel en voldoende nauwkeurig
    dmm.write("VOLT:AC:RANG:AUTO OFF")
    dmm.write("VOLT:AC:RANG 10")  # Vast bereik van 10 V

    # --- Metingen uitvoeren ---
    vals = []
    for _ in range(n):
        v = float(dmm.query("MEAS:VOLT:AC?"))  # Vraag één meting op
        vals.append(v)
        time.sleep(0.02)                       # Korte pauze tussen metingen

    return np.array(vals)
