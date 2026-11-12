# Closed loop - aeropendulum

Open **script.ipynb** voor stap 4. Start Jupyter vanuit deze map zodat
het pakket `closed_loop` gevonden wordt. Herstart na een code-update de kernel
en voer de importcel opnieuw uit.

## Actieve bestanden

```text
Closed_loop/
  script.ipynb                     # Stap 4: hoektest, PID en begrenzingen
  arduino/
    Stap_4_Closed_loop/Stap_4_Closed_loop.ino
  closed_loop/                     # Python-aansturing en opslag
  data/                            # Meetgegevens en instellingen
  figuren/                         # Opgeslagen grafieken
  tests/                           # Tests zonder aangesloten motor
  Archief/                         # Oude versies en simulatie-uitvoer
```

## Stap 4: PID

Upload `arduino/Stap_4_Closed_loop/Stap_4_Closed_loop.ino` en gebruik `voer_pid_meting_uit(...)`.
De maximale hoek is standaard 180 graden. Geef `max_hoek=120` mee om deze grens
te veranderen. `test_hoek(...)` leest de ruwe sensorhoek met motoruitgang nul.

## PWM-verandering begrenzen

Gebruik dezelfde geuploade sketch en
`voer_pid_meting_uit(...)`. Zonder argument `max_pwm_stap` wordt geen
limiterinstelling verstuurd en is de limiter uit. Met bijvoorbeeld
`max_pwm_stap=20` begrens je alleen stijgen tot 20 telwaarden per regelstap.
Een eerdere limiterinstelling wordt bij een nieuwe proef gewist.

`max_pwm` is de maximale motoruitgang; `max_pwm=0` houdt de motor uit.
`max_pwm_stap` bepaalt uitsluitend de maximale sprong per regelstap.
STOP, maximale hoek, watchdog en einde meetduur schakelen direct uit.
Python controleert de sketchversie voordat de PID-proef start.

## Gebruik

Installeer zo nodig `pyserial` en `pandas` in de gebruikte
Python-omgeving. COM4 was de gevonden Arduino-poort; controleer deze op je eigen
computer. Sluit Serial Monitor en Serial Plotter voordat Python de poort opent.
Upload en wijzig bedrading met de motorvoeding uit.

Opslaan staat standaard uit (`opslaan=False`). Met `opslaan=True` worden
meetgegevens in `data/` bewaard, met instellingen bovenaan de CSV.
Zonder opslag is het geretourneerde `csv_pad` gelijk aan `None`. Gebruik bij pandas `comment="#"`. `hoek_deg` is de werkhoek; de hoektest
bewaart de ruwe sensorhoek. De meetgegevens en bestaande figuren zijn behouden.

## Archief

- `Ongebruikte_code/`: ongebruikte Python-modules, oude functienamen en bijbehorende tests.

- `Losse_notebooks/`: de eerdere losse stap-4- en stap-5-notebooks; gebruik nu script.ipynb.
- `Testuitvoer/`: oude simulatiegegevens en voorbeeldfiguren uit .test_build.
- `PID_eerste_versie/`: de eerste implementatie.
- `Stap_5_Veiligheidsbegrenzing/`: de voormalige aparte hoekbegrenzingsopdracht.

Het archief is naslag, geen startpunt voor nieuwe metingen.

## Tests

`python -m unittest discover -s tests -q`

De C++-simulatietest gebruikt g++ en slaat die test over als de compiler ontbreekt.
Gebruik alleen `test_hoek` en `voer_pid_meting_uit`. De oude functienamen,
plotfuncties en PID-afstelfuncties staan in `Archief/Ongebruikte_code/`.

De PWM-stapbegrenzing geldt alleen voor stijgende PWM. Dalende PWM wordt direct aangeboden, zonder stapbegrenzing.
