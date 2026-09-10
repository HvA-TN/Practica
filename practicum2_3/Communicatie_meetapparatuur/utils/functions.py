import csv
import numpy as np

def load_from_csv(filename):
    """
    Laad een CSV-bestand dat gemaakt is door save_as_csv()
    en zet het om terug naar dezelfde 'results'-datastructuur.

    Outputstructuur:
    results[freq_hz] = {
        "samples": np.array([...]),
        "mean": float,
        "std": float,
        "n": int
    }
    """

    results = {}

    with open(filename, "r") as f:
        reader = csv.DictReader(f)

        for row in reader:
            freq = float(row["freq_hz"])
            mean_v = float(row["mean_vrms"])
            std_v = float(row["std_vrms"])
            n = int(row["n_samples"])

            # Samples terug naar numpy-array
            # Samples worden opgeslagen als één string: "0.9123 0.9131 0.9129 ..."
            samples_str = row["samples"].strip()

            if samples_str == "":
                samples = np.array([])
            else:
                samples = np.array([float(v) for v in samples_str.split()])

            results[freq] = {
                "samples": samples,
                "mean": mean_v,
                "std": std_v,
                "n": n,
            }

    print(f"[OK] CSV geladen: {filename}")
    return results

def print_measurement_result(freq, result):
    """
    Mooi geformatteerde uitvoer van één meetpunt.
    result is een dict met keys: samples, mean, std, n
    """

    mean_v = result["mean"]
    std_v = result["std"]
    n     = result["n"]
    vals  = result["samples"]

    # Eerste regel: overzicht
    print(f"{freq:>8} Hz | "
          f"mean = {mean_v:.6f} Vrms | "
          f"std = {std_v:.6f} Vrms | "
          f"n = {n:2d}")

    # Samples compact tonen
    samples_str = ", ".join(f"{v:.4f}" for v in vals)
    print(f"    samples: [{samples_str}]")

def save_as_csv(results, filename="results.csv"):
    """
    Sla een 'results'-dict (freq -> {samples, mean, std, n}) op als CSV-bestand.

    Parameters
    ----------
    results : dict
        Dictionary van de vorm:
        results[freq] = {
            "samples": np.array([...]),
            "mean": float,
            "std": float,
            "n": int
        }

    filename : str
        Pad naar het CSV-bestand dat geschreven wordt.
    """

    # Open het CSV-bestand
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)

        # Header
        writer.writerow(["freq_hz", "mean_vrms", "std_vrms", "n_samples", "samples"])

        # Iedere frequentie als één rij
        for freq, data in results.items():
            samples_as_str = " ".join(f"{v:.6f}" for v in data["samples"])

            writer.writerow([
                freq,
                data["mean"],
                data["std"],
                data["n"],
                samples_as_str
            ])

    print(f"[OK] CSV opgeslagen als: {filename}")
