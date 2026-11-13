# Communicatie_Meetapparatuur

# Practicum: Apparatuurcommunicatie met Python

Dit practicum richt zich op het automatisch aansturen en uitlezen van laboratoriumapparatuur met Python.  
Je leert werken met PyVISA, SCPI-commando’s en een overzichtelijke software-structuur voor instrumentcommunicatie.  
Daarnaast bouw je een passief RC-filter en meet je de frequentierespons (Bode-plot) zowel handmatig als geautomatiseerd.

---

## 📚 Leerdoelen

- Kan communiceren met basis labapparatuur via Python.
- Kan uitleggen welke stappen nodig zijn voor communicatie met meetinstrumenten.
- Kan werken met de Python-package **PyVISA**.
- Kan een overzichtelijke **map- en modulestuctuur** opzetten voor instrumentcommunicatie binnen een groter Python-project.

---

## ⚠️ Veiligheid

- We werken met elektrische schakelingen. Controleer altijd je breadboard-opstelling voordat je spanning aanlegt.
- Laat je schakeling **altijd checken** door een practicumbegeleider voordat je metingen uitvoert.

---

## 🕰️ Korte historische context

Apparaatcommunicatie ontwikkelde zich van handmatige bediening naar geautomatiseerde protocollen:

- Vroeger via **RS-232** en **GPIB**, vaak handmatig geprogrammeerd in C, Fortran of LabVIEW.
- Moderne meetinstrumenten gebruiken microcontrollers en standaardprotocollen.
- Met **VISA** en **PyVISA** kunnen instrumenten (USB, GPIB, LAN) op uniforme wijze worden aangestuurd.
- Python maakt het nu mogelijk om met korte scripts professionele meetautomatisering te gebruiken.

---

## 🔧 RC-filters (basis)

Een passief RC-filter bestaat uit een weerstand en condensator.

Voor een laagdoorlaatfilter geldt:

$$
H(\omega) = \frac{1}{1 + i\omega RC}, \qquad f_c = \frac{1}{2\pi RC}
$$

De amplitude en fase voor een Bode-plot zijn:

$$
|H(\omega)|_\mathrm{dB} = 20\log_{10}|H(\omega)|, \qquad
\phi(\omega) = -\arctan(\omega RC)
$$


---

## 📁 Projectstructuur

Tijdens dit practicum gebruik je een overzichtelijke softwareboom:

```
Communicatie/
├── instruments/
│   ├── __init__.py
│   ├── hardware.py
│   ├── rigol_dg1022.py
│   └── rigol_dm3058e.py
├── utils/
│   ├── __init__.py
│   ├── functions.py
│   └── constants.py
├── data/
│   ├── raw/
│   └── plots/
├── rc_filter.ipynb
├── README.md
└── .gitignore
```

- `instruments/` bevat de drivers (SCPI-aansturing).
- `utils/` bevat hulpfuncties (laden/opslaan van data, I/O).
- `data/` bevat meetdata en gegenereerde figuren.

---
