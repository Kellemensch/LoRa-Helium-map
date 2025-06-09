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
    print("Running Splat...")
    result = subprocess.run(
        ["splat", "-t", tx_qth, "-r", rx_qth, "-d", SDF_DIR, "-metric", "-f", "5800", "-H", output_png],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode != 0:
        print(f"SPLAT error:\n{result.stderr}")
    else:
        print("SPLAT ran successfully")

def is_nlos(splat_output):
    # Détecte la présence de NLOS dans le retour Splat Galileo-to-gw_name
    print("Running nlos detection...")
    try:
        with open(splat_output, "r", encoding="latin1") as f:
            content = f.read().lower()
            print("Finished nlos detection")
            return "detected obstructions at" in content
    except FileNotFoundError:
        print(f"File {splat_output} not found.")
        return False

def main():
    results = []
    with open(GATEWAY_CSV, newline="") as csvfile:
        reader = csv.reader(csvfile)
        next(reader)
        for row in reader:
            try:
                gw_id = row[1]
                gw_name = row[2]
                gw_lat = float(row[7])
                gw_lon = 360 - float(row[6]) # Pour bonne lecture de fichier SDL
                gw_alt = 3  # approximatif
                gw_distance = float(row[8])

                gw_qth = f"{QTH_DIR}/{gw_name}.qth"
                generate_qth(gw_name, gw_lat, gw_lon, gw_alt, gw_qth)

                print(f"Analysing {gw_name}...")

                run_splat(f"{QTH_DIR}/galileo_end_node.qth", gw_qth, f"{gw_name}.png")

                txt_path = f"Galileo-to-{gw_name}.txt"
                if not os.path.exists(txt_path):
                    print(f"Splat file missing : {txt_path}")
                    continue

                has_nlos = is_nlos(txt_path)

                results.append([gw_id, gw_name, gw_lat, gw_lon, round(gw_distance, 2), "NLOS" if has_nlos else "LOS"])

            except Exception as e:
                print(f"Error on {row}: {e}")

    print("Writing results...")
    with open(OUTPUT_CSV, "w", newline="") as outcsv:
        writer = csv.writer(outcsv)
        writer.writerow(["Gateway ID", "Name", "Latitude", "Longitude", "Distance(km)", "Visibility"])
        writer.writerows(results)

    print(f"Results saved in {OUTPUT_CSV}")

    # Déplacer tous les fichiers
    os.system("mv ./Galileo*.txt splat-runs/")
    os.system("mv *.png ./splat-runs/img/")
    print("Moved files to splat-runs/")

if __name__ == "__main__":
    main()
