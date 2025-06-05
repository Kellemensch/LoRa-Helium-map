import csv
import os
import subprocess

GATEWAY_CSV = "data/helium_gateway_data.csv"
END_NODE_FILE = "data/terrain/galileo_end_node.qth"
OUTPUT_CSV = "data/results/los_results.csv"
QTH_DIR = "data/terrain/terrain"

os.makedirs(QTH_DIR, exist_ok=True)
os.makedirs("./data/results", exist_ok=True)

def parse_end_node():
    with open(END_NODE_FILE, "r") as f:
        lat, lon = f.read().strip().split(",")
    return float(lat), float(lon), 2  # altitude en mètres (à adapter si nécessaire)

def generate_qth(name, lat, lon, alt, path):
    with open(path, "w") as f:
        f.write(f"{name}\n{lat}\n{lon}\n{alt}")

def run_splat(tx_qth, rx_qth):
    # Exécute SPLAT en mode profil de terrain
    result = subprocess.run(
        ["splat", "-d", tx_qth, rx_qth],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return result.stdout

def is_los(splat_output):
    # Détecte la présence de NLOS dans le retour SPLAT
    return "line-of-sight" in splat_output.lower()

def main():
    results = []
    with open(GATEWAY_CSV, newline="") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            try:
                gw_id = row[1]
                gw_name = row[2]
                gw_lat = float(row[4])
                gw_lon = float(row[5])
                gw_alt = 10  # hauteur d'antenne approximative, à adapter

                gw_qth = f"{QTH_DIR}/{gw_id}.qth"
                generate_qth(gw_name, gw_lat, gw_lon, gw_alt, gw_qth)

                print(f"🔍 Analyse de {gw_name}...")

                output = run_splat(gw_qth, f"{QTH_DIR}/endnode.qth")
                has_los = is_los(output)

                results.append([gw_id, gw_name, gw_lat, gw_lon, "LOS" if has_los else "NLOS"])

            except Exception as e:
                print(f"⚠️ Erreur sur {row}: {e}")

    with open(OUTPUT_CSV, "w", newline="") as outcsv:
        writer = csv.writer(outcsv)
        writer.writerow(["Gateway ID", "Name", "Latitude", "Longitude", "Visibility"])
        writer.writerows(results)

    print(f"✅ Résultats enregistrés dans {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
