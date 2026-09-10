
def set_fixed_sine(gen, freq=1000, vrms=0.5, channel=1):
    """
    Stel de functiegenerator in op een vaste sinusgolf.

    Studenten zien stap-voor-stap hoe je via SCPI-commando’s
    de golfvorm, amplitude en frequentie instelt.

    Parameters
    ----------
    gen : PyVISA instrument
        De geopende functiegenerator (DG1022/DG1022Z).
    freq : float
        Gewenste frequentie in Hz.
    vrms : float
        Amplitude in Vrms.
    channel : int
        Kanaalnummer (1 of 2) dat je wilt instellen.
    """

    # -------------------------------
    # 1) Kies het kanaal
    # -------------------------------
    # De meeste SCPI-commando’s voor de DG1022 beginnen met SOUR1 of SOUR2,
    # afhankelijk van welk kanaal je wilt gebruiken.
    chan = f"SOUR{channel}"

    # -------------------------------
    # 2) Golfvorm instellen
    # -------------------------------
    # FUNC SIN betekent: genereer een sinusgolf.
    gen.write(f"{chan}:FUNC SIN")

    # -------------------------------
    # 3) Amplitude instellen (Vrms)
    # -------------------------------
    # Eerst kiezen we de amplitude-eenheid (VRMS i.p.v. VPP of dBm).
    gen.write(f"{chan}:VOLT:UNIT VRMS")

    # Dan stellen we de daadwerkelijke amplitude in.
    gen.write(f"{chan}:VOLT {vrms}")

    # -------------------------------
    # 4) Frequentie instellen
    # -------------------------------
    gen.write(f"{chan}:FREQ {freq}")

    # -------------------------------
    # 5) Uitgang inschakelen
    # -------------------------------
    # De DG1022 genereert pas een signaal zodra de output aan staat.
    gen.write(f"OUTP{channel} ON")