"""Publicatiefiguren voor de PID-meting."""

from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator, MaxNLocator

FIGUREN_MAP = Path(__file__).resolve().parent.parent / "figuren"


def plot_pid_meting(metingen, csv_pad=None, opslaan=True):
    """Plot onbewerkte hoek en PWM; exporteer als vector-PDF en PNG (600 dpi)."""
    if not metingen:
        raise ValueError("Geen meetpunten beschikbaar om te plotten.")
    tijden, doelen, hoeken, pwm_waarden = zip(*metingen)
    stijl = {
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.labelsize": 11, "legend.fontsize": 9,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": 0.8, "lines.linewidth": 1.6,
        "xtick.direction": "out", "ytick.direction": "out",
        "pdf.fonttype": 42, "ps.fonttype": 42,
        "figure.facecolor": "white", "savefig.facecolor": "white",
    }
    with plt.rc_context(stijl):
        fig, ax = plt.subplots(2, 1, sharex=True, figsize=(7.2, 5.2),
                               layout="constrained")
        ax[0].plot(tijden, hoeken, color="#0072B2", label="Gemeten hoek")
        ax[0].plot(tijden, doelen, color="#D55E00", linestyle="--",
                   linewidth=1.4, label="Doelhoek")
        ax[0].set_ylabel("Hoek vanaf rust (°)")
        ax[0].legend(loc="best", frameon=False, ncol=2)
        ax[0].margins(y=0.15)
        ax[0].yaxis.set_major_locator(MaxNLocator(nbins=6))

        ax[1].step(tijden, pwm_waarden, where="post", color="#0072B2")
        ax[1].set_ylabel("PWM (telwaarde)")
        ax[1].set_xlabel("Tijd sinds start (s)")
        ax[1].set_ylim(-5, 265)  # Marge zodat PWM=0 en PWM=255 zichtbaar blijven.
        ax[1].set_yticks([0, 64, 128, 192, 255])
        ax[1].xaxis.set_major_locator(MaxNLocator(nbins=8))
        ax[1].xaxis.set_minor_locator(AutoMinorLocator(2))
        if tijden[-1] > tijden[0]:
            ax[1].set_xlim(min(0, tijden[0]), tijden[-1])
        for paneel, letter in zip(ax, ("a", "b")):
            paneel.set_title(f"({letter})", loc="left", fontsize=10, fontweight="bold")
            paneel.set_axisbelow(True)
            paneel.grid(axis="both", which="major", color="0.88", linewidth=0.6)
            paneel.tick_params(which="major", length=4)

        if opslaan:
            FIGUREN_MAP.mkdir(parents=True, exist_ok=True)
            naam = Path(csv_pad).stem if csv_pad else datetime.now().strftime("pid_%Y%m%d_%H%M%S_%f")
            for extensie in ("pdf", "png"):
                pad = FIGUREN_MAP / f"{naam}.{extensie}"
                fig.savefig(pad, dpi=600, bbox_inches="tight", pad_inches=0.08)
                print(f"Figuur opgeslagen: {pad}")
    return fig, ax
