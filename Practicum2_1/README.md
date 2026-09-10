# Beeldanalyse met Python

In dit onderdeel gebruiken we **Python en OpenCV** om beelden van een camera uit te lezen en te analyseren. De camera wordt hierbij behandeld als een meetinstrument: een afbeelding is een NumPy-array met pixelwaarden die we numeriek kunnen verwerken.

## Benodigde packages

Activeer eerst de juiste conda-omgeving en installeer indien nodig:

```text
conda install opencv scikit-image numpy matplotlib -y
```

We gebruiken:

* **OpenCV** voor het uitlezen van de camera;
* **NumPy** voor numerieke bewerkingen;
* **scikit-image** voor beeldverwerking;
* **Matplotlib** voor het weergeven van afbeeldingen en grafieken.

## Wat gaan we doen?

We bouwen de analyse stapsgewijs op:

1. Camera verbinden en een beeld uitlezen.
2. Begrijpen hoe een afbeelding als NumPy-array wordt opgeslagen.
3. RGB-afbeeldingen omzetten naar grijswaarden.
4. Pixelintensiteiten analyseren.
5. Een 2D-camerabeeld omzetten naar een 1D-intensiteitsprofiel.
6. De pixelpositie uiteindelijk koppelen aan een fysische grootheid, zoals **golflengte**.

Het uiteindelijke doel is om een camerabeeld van een spectrum om te zetten naar een grafiek van de vorm

$$
I(\lambda),
$$

waarbij \(I\) de gemeten intensiteit is en \(\lambda\) de golflengte.
