import csv
import os
import subprocess

GATEWAY_CSV = "data/helium_gateway_data.csv"
END_NODE_FILE = "data/terrain/galileo_end_node.qth"
OUTPUT_CSV = "splat-runs/results/los_results.csv"
QTH_DIR = "data/terrain"
SDF_DIR = "maps"

os.makedirs(QTH_DIR, exist_ok=True)
os.makedirs("./data/results", exist_ok=True)

def parse_end_node():
    with open(END_NODE_FILE, "r") as f:
        lat, lon = f.read().strip().split(",")
    return float(lat), float(lon), 2  # altitude en mètres (à adapter si nécessaire)

def generate_qth(name, lat, lon, alt, path):
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    with open(path, "w") as f:
        f.write(f"{name}\n{lat}\n{lon}\n{alt}")
        print(f"Generated QTH file: {path}")

def run_splat(tx_qth, rx_qth, output_png):
    # Exécute SPLAT en mode profil de terrain
    result = subprocess.run(
        ["splat", "-t", tx_qth, "-r", rx_qth, "-d", SDF_DIR, "-metric", "-f", "5800", "-H", output_png],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

def is_nlos(splat_output):
    # Détecte la présence de NLOS dans le retour Splat Galileo-to-gw_name
    try:
        with open(splat_output, "r") as f:
            content = f.read().lower()
            return "detected obstructions at" not in content
    except FileNotFoundError:
        print(f"File {splat_output} not found.")
        return False

def main():
    results = []
    with open(GATEWAY_CSV, newline="") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            try:
                gw_id = row[1]
                gw_name = row[2]
                gw_lat = float(row[7])
                gw_lon = 360 - float(row[6]) # Pour bonne lecture de fichier SDL
                gw_alt = 3  # approximatif

                gw_qth = f"{QTH_DIR}/{gw_name}.qth"
                generate_qth(gw_name, gw_lat, gw_lon, gw_alt, gw_qth)

                print(f"Analysing {gw_name}...")

                run_splat(f"{QTH_DIR}/galileo_end_node.qth", gw_qth, f"{gw_name}.png")
                has_nlos = is_nlos(f"Galileo-to-{gw_name}")

                results.append([gw_id, gw_name, gw_lat, gw_lon, "NLOS" if has_nlos else "LOS"])

            except Exception as e:
                print(f"Error on {row}: {e}")

    with open(OUTPUT_CSV, "w", newline="") as outcsv:
        writer = csv.writer(outcsv)
        writer.writerow(["Gateway ID", "Name", "Latitude", "Longitude", "Visibility"])
        writer.writerows(results)

    print(f"Results saved in {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
