import pyvisa

def open_instruments(message = 0):
    rm = pyvisa.ResourceManager()
    devices = rm.list_resources()

    if len(devices) < 1:
        raise RuntimeError("Te weinig VISA-apparaten gevonden.")

    if len(devices) == 1:
        fg = rm.open_resource(devices[0])
        if message == 1:
            print("Apparaat gevonden:", fg.query("*IDN?").strip())
        return rm, fg

    fg = rm.open_resource(devices[0])
    dmm = rm.open_resource(devices[1])
    if message == 1:
        print("Apparaat gevonden:", fg.query("*IDN?").strip())
        print("Apparaat gevonden:", dmm.query("*IDN?").strip())
        print("Controleer goed of de functiegenerator (fg) en de digitale multimeter (dmm) \n " \
        "goed óm zijn aangesloten.")
    return rm, fg,dmm

def close_instruments(*instruments, message=0):
    """
    Sluit alle opgegeven VISA-instrumenten op een nette manier.

    Parameters
    ----------
    *instruments : tuple
        Instrumentobjecten gevolgd door de ResourceManager.
        Voorbeelden:
            close_instruments(rm, fg)
            close_instruments(rm, fg, dmm)
    message : int
        Indien 1: print statusmeldingen.
    """

    # --- Laatste argument moet de ResourceManager zijn ---
    rm = instruments[0]
    inst = instruments[1:]

    # --- Sluit elk instrument afzonderlijk ---
    for dev in inst:
        try:
            if message == 1:
                print("Sluiten:", dev.query("*IDN?").strip())
        except Exception:
            pass  # IDN-query kan mislukken als instrument al in foutstatus staat

        try:
            dev.close()
        except Exception as e:
            if message == 1:
                print("Kon instrument niet sluiten:", e)

    # --- Sluit ResourceManager ---
    try:
        rm.close()
        if message == 1:
            print("ResourceManager gesloten.")
    except Exception as e:
        if message == 1:
            print("Kon ResourceManager niet sluiten:", e)
