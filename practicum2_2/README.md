# Practicum 2.2 - Aeropendulum: open loop en closed loop

In dit practicum bouw je de opstelling zelf op. Eerst controleer je de hoeksensor, daarna stuur je de motor aan met een vaste PWM. Vervolgens onderzoek je hoe terugkoppeling kan worden gebruikt om een gewenste hoek te bereiken.

| Onderdeel | Wat stel je in? | Wat gebeurt er met de PWM? |
| --- | --- | --- |
| Open loop | Een vaste PWM-waarde | De PWM blijft gelijk; de gemeten hoek wordt alleen uitgelezen. |
| Closed loop | Een gewenste hoek (setpoint) | De regelaar past de PWM aan op basis van het verschil tussen de gewenste en gemeten hoek. |

## Bestanden

```text
practicum2_2/
|-- README.md
|-- Open_loop/
|   |-- arduino/
|   |   |-- Stap_1_Sensor/
|   |   |-- Stap_2_PWM_en_sensor/
|   |   `-- Stap_3_Python_aansturing/
|   |-- script.ipynb
|   |-- open_loop/
|   |-- data/
|   `-- Archief/
`-- Closed_loop/
    |-- arduino/PID_Python_aansturing/
    |-- script.ipynb
    |-- closed_loop/
    `-- data/
```

De instructies voor beide onderdelen staan in deze README. De benodigde Python-omgeving wordt apart door de docent toegelicht.

## Open loop: aansluiten en meten

Bouw de opstelling in twee delen op: test eerst de sensor en voeg daarna de motor met motordriver toe. Zo kun je bij iedere stap controleren of het nieuw aangesloten onderdeel werkt. Gebruik voor alle sketches de Serial Monitor of Serial Plotter op **115200 baud**.

| Stap | Arduino-sketch | Wat doe je? |
| --- | --- | --- |
| 1. Alleen de sensor | `Open_loop/arduino/Stap_1_Sensor/Stap_1_Sensor.ino` | Sluit de AS5600 aan, beweeg de pendel met de hand en lees de hoek uit. |
| 2. PWM en hoek | `Open_loop/arduino/Stap_2_PWM_en_sensor/Stap_2_PWM_en_sensor.ino` | Voeg de motor en driver toe. Kies `pwm_waarde` in de sketch, upload opnieuw en bekijk de hoek. |
| 3. Python-aansturing | `Open_loop/arduino/Stap_3_Python_aansturing/Stap_3_Python_aansturing.ino` | Upload deze sketch, sluit de Serial Monitor en gebruik [script.ipynb](Open_loop/script.ipynb). |

### Stap 1: controleer de sensor

Sluit de sensorvoeding en GND aan volgens het aansluitschema van de opstelling. Verbind SDA en SCL met de gelijknamige I2C-pinnen van het Arduino-board. De motorvoeding blijft uit.

Beweeg de pendel langzaam. Verandert de hoek mee? Wat gebeurt er bij de overgang tussen 359 en 0 graden? De uitvoer is de absolute sensorhoek, zonder nulpuntscorrectie of middeling.

### Stap 2: voeg de motor toe

Schakel de voeding uit voordat je de bedrading uitbreidt. Gebruik dezelfde sensorbedrading en sluit de L298N aan volgens het schema van de opstelling:

- Arduino pin 9 naar ENA (verwijder de ENA-jumper om PWM te gebruiken).
- Arduino pin 10 naar IN1 en pin 11 naar IN2.
- Motor naar de bijbehorende motoruitgangen van de driver.
- Motorvoeding naar de driver; verbind Arduino-GND en driver-GND met elkaar.

Begin met `pwm_waarde = 0`. Upload de sketch en controleer of de hoek nog steeds wordt uitgelezen. Kies daarna een kleine PWM-waarde en upload opnieuw. Laat studenten eerst voorspellen wat er met de hoek gebeurt als PWM groter wordt en dat vervolgens meten. Een PWM-waarde is een instelling tussen 0 en 255, geen hoek in graden.

De motor draait bij deze stap continu op de ingestelde PWM, ook wanneer je de Serial Monitor sluit. Stop door de motorvoeding uit te schakelen; upload met uitgeschakelde motorvoeding `pwm_waarde = 0` voordat je die weer inschakelt. De sketch bevat bewust alleen een vaste PWM en dezelfde hoekmeting als stap 1.

### Stap 3: stuur aan vanuit Python

Upload `Open_loop/arduino/Stap_3_Python_aansturing/Stap_3_Python_aansturing.ino`. De bedrading uit stap 2 blijft hetzelfde. Nu stel je PWM en meetduur vanuit de notebook in en worden de meetgegevens opgeslagen. De Arduino handelt de commando's van Python af.

De eerdere sketches met gemiddelden en een PWM-sweep staan in `Open_loop/Archief/extra_voorbeelden/`. Ze horen niet bij deze drie basisstappen.

### Python-notebook gebruiken

1. Upload `Open_loop/arduino/Stap_3_Python_aansturing/Stap_3_Python_aansturing.ino` met de Arduino IDE. De AS5600-library staat ook in `Open_loop/Archief/libraries/AS5600/`.
2. Open [script.ipynb](Open_loop/script.ipynb) en kies de Python-omgeving die bij het practicum hoort.
3. Sluit de Arduino Serial Monitor en voer de notebookcellen op volgorde uit.

In de notebook pas je de COM-poort, PWM, meetduur en tijd tussen meetpunten aan. De motor stabiliseert eerst 2 seconden en meet daarna gedurende de ingestelde meetduur. De opstarttijd van de Arduino is nog eens 2 seconden.

### Waar komen de functies vandaan?

`open_loop` is de package-map naast de notebook. In [Open_loop/open_loop/meting.py](Open_loop/open_loop/meting.py) staat de functie `voer_open_loop_meting_uit`. De notebook laadt deze met:

```python
from open_loop.meting import voer_open_loop_meting_uit
```

De functie stuurt de Arduino aan en retourneert de meetpunten (`tijd_s`, `hoek_deg`) en het pad naar het CSV-bestand. Open de notebook vanuit de map `Open_loop`, zodat Python het package kan vinden.

### Meetgegevens

CSV-bestanden komen automatisch in `Open_loop/data/` met een unieke tijdstempel in de bestandsnaam. Bestaande bestanden worden niet overschreven. De tijd begint bij het eerste ontvangen meetpunt; het laatste tijdstip kan daardoor iets lager zijn dan de ingestelde meetduur.

Onderbreek de meetcel om eerder te stoppen. De functie probeert de motor uit te schakelen en bewaart reeds ontvangen meetpunten. Dit gebeurt ook bij een fout.

## Closed loop: PID bedienen vanuit Python

De Arduino voert de PID-regeling uit op nominaal 50 Hz. Vanuit [Closed_loop/script.ipynb](Closed_loop/script.ipynb) stel je de doelhoek, `kp`, `ki`, `kd`, `max_pwm` en meetduur in. Voor een nieuwe parameterkeuze hoef je de sketch niet opnieuw te uploaden.

1. Upload met uitgeschakelde motorvoeding [PID_Python_aansturing.ino](Closed_loop/arduino/PID_Python_aansturing/PID_Python_aansturing.ino). Deze gebruikt AS5600 en PID_v1; de libraries staan ook in `Open_loop/Archief/libraries/`.
2. Sluit de Serial Monitor en Plotter en open de notebook vanuit `Closed_loop`. Vul de COM-poort in. De communicatie verloopt op 115200 baud.
3. Voer met uitgeschakelde motorvoeding de sensorcontrole uit. De werkhoek is `90 - sensorhoek`; controleer nulstand en richting. De Arduino accepteert werkhoeken van -10 tot 80 graden. Een grotere motoruitgang moet een grotere werkhoek geven.
4. Kies met de begeleider een haalbare doelhoek en PWM-grens. Begin met P (`ki = kd = 0`). Schakel de gecontroleerde motorvoeding in en voer de meetcel uit. De regeling begint na de communicatiecontrole, zonder de stabilisatietijd uit open loop.
5. Onderzoek eerst `kp`, daarna voor PI ook `ki` en voor PID ook `kd`. Laat de arm voor elke proef tot rust komen. Plot de hoek, doelhoek en PWM met de laatste cel.

De functies staan in [closed_loop/meting.py](Closed_loop/closed_loop/meting.py):

```python
from closed_loop.meting import controleer_sensor, voer_pid_meting_uit
```

De Arduino wacht na reset op Python, wist bij iedere start de integrator en stopt na de ingestelde meetduur. De sensorcontrole houdt de motor uit. Een ongeldige sensorstatus, werkhoek buiten het bereik of langer dan 3 seconden geen heartbeat stopt de meting. Bij onderbreken of een fout probeert Python STOP te sturen en bewaart het de al ontvangen data. De fysieke uitschakeling van de motorvoeding blijft bereikbaar.

`max_pwm` kan tussen 1 en 120 worden gekozen; 120 is een voorlopige bovengrens uit de bestaande sketch, geen voor elke opstelling geschikte instelling. De meetduur ligt tussen 0.02 en 600 seconden. Hoekoffset en vaste grenzen staan bovenaan de Arduino-sketch; stem wijzigingen af met de begeleider. Bij wijzigingen aan die vaste waarden moeten ook de controles en opgeslagen kalibratiegegevens in het Python-package worden bijgewerkt.

### Meetgegevens

Iedere proef levert een CSV in `Closed_loop/data/` met `tijd_s`, `doelhoek_deg`, `hoek_deg` en `pwm`. De tijd komt van de Arduino en begint bij het startcommando. Het bijbehorende JSON-bestand bewaart de PID-instellingen, meetduur, kalibratie en afloopstatus. Noteer voedingsspanning en motorstroom apart in het labjournaal.

De [closed-loophandleiding](Periode2/Aero_pendulum_PID.tex) beschrijft de proeven voor P, PI en PID. De eerdere handmatig bediende CSV-sketches onder `Periode2/Arduino/` blijven als oudere voorbeelden beschikbaar; gebruik voor de notebook de nieuwe sketch in `Closed_loop/arduino/`.
