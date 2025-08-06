import csv
import os
import subprocess
from collections import defaultdict
import glob
import shutil
import argparse
from configs.config_coords import END_DEVICE_LAT, END_DEVICE_LON

GATEWAY_CSV = "/app/output/data/helium_gateway_data.csv"
END_NODE_FILE = "/app/data/terrain/end_node.qth"
QTH_DIR = "/app/data/terrain/"
SDF_DIR = "/app/maps/"
RUNS_DIR = "/app/output/splat-runs/"
IMG_DIR = "/app/output/splat-runs/img/"

os.makedirs(QTH_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

parser = argparse.ArgumentParser()
parser.add_argument("--logs", action="store_true")
args = parser.parse_args()

def log(*messages):
    if args.logs:
        print("[LOG]", *messages)


def parse_end_node():
    with open(END_NODE_FILE, "r") as f:
        lat, lon = f.read().strip().split(",")
    return float(lat), float(lon), 2  # altitude en mètres (à adapter si nécessaire)

def generate_end_node():
    if os.path.exists(END_NODE_FILE):
        log(f"QTH file already exists : {END_NODE_FILE}, skip.")
        return
    print
    folder = os.path.dirname(END_NODE_FILE)
    os.makedirs(folder, exist_ok=True)
    with open(END_NODE_FILE, "w") as f:
        f.write(f"End-node\n{END_DEVICE_LAT}\n{360-END_DEVICE_LON}\n{3}") # Pour que ce soit lisible par splat : lon = 360 - lon
        log(f"Generated QTH file: {END_NODE_FILE}")

def generate_qth(name, lat, lon, alt, path):
    if os.path.exists(path):
        log(f"QTH file already exists : {path}, skip.")
        return
    print
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    with open(path, "w") as f:
        f.write(f"{name}\n{lat}\n{360-lon}\n{alt}m") # Pour que ce soit lisible par splat : lon = 360 - lon
        log(f"Generated QTH file: {path}")

def run_splat(tx_qth, rx_qth, output_png, output_txt):
    if os.path.exists(output_txt):
        log(f"SPLAT output already exists: {output_txt}, skip.")
        return 2

    # Exécute SPLAT en mode profil de terrain
    log("Running Splat...")
    result = subprocess.run(
        ["splat", "-t", tx_qth, "-r", rx_qth, "-d", SDF_DIR, "-metric", "-f", "5800", "-H", output_png],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    # log(result.stdout)
    if result.returncode != 0:
        log(f"SPLAT error:\n{result.stderr}")
        return 0
    else:
        log("SPLAT ran successfully")
        return 1

def is_nlos(splat_output):
    # Détecte la présence de NLOS dans le retour Splat Galileo-to-gw_name
    log("Running nlos detection...")
    try:
        with open(splat_output, "r", encoding="latin1") as f:
            content = f.read().lower()
            log("Finished nlos detection")
            return "detected obstructions at" in content
    except FileNotFoundError:
        log(f"File {splat_output} not found.")
        return False

def main():
    generate_end_node()


    with open(GATEWAY_CSV, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)
    
    fieldnames = reader.fieldnames

    # Regrouper les lignes par nom de gateway
    gateways = defaultdict(list)
    for row in rows:
        if row.get("visibility") == "N/A":
            gateways[row["gateway_name"]].append(row)

    for gw_name, gw_rows in gateways.items():
        try:
            sample_row = gw_rows[0]
            gw_lat = float(sample_row["gateway_lat"])
            gw_lon = float(sample_row["gateway_long"])
            gw_alt = 3

            gw_qth = f"{QTH_DIR}{gw_name}.qth"
            generate_qth(gw_name, gw_lat, gw_lon, gw_alt, gw_qth)

            log(f"Analysing {gw_name}...")

            txt_path = f"End-node-to-{gw_name}.txt"
            png_path = f"{gw_name}.png"

            splat = run_splat(f"{END_NODE_FILE}", gw_qth, png_path, f"{RUNS_DIR}{txt_path}")

            if splat:
                if splat == 2:
                    txt_path = f"{RUNS_DIR}{txt_path}" # Le run a déjà été fait

                if not os.path.exists(txt_path):
                    log(f"Splat file missing: {txt_path}")
                    continue

                los_result = "NLOS" if is_nlos(txt_path) else "LOS"
                log(f"{gw_name}: {los_result}")

                # Appliquer à toutes les lignes de cette gateway
                for row in gw_rows:
                    row["visibility"] = los_result

        except Exception as e:
            log(f"Error on gateway '{gw_name}': {e}")


    log("Writing results...")
    with open(GATEWAY_CSV, "w", newline="") as outcsv:
        writer = csv.DictWriter(outcsv, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Results saved in {GATEWAY_CSV}")

    # Déplacer tous les fichiers
    for file in glob.glob('End-node*.txt'):
        dest = os.path.join(RUNS_DIR, os.path.basename(file))
        if os.path.exists(dest):
            os.remove(dest)
        shutil.move(file, dest)

    for file in glob.glob('*.png'):
        dest = os.path.join(IMG_DIR, os.path.basename(file))
        if os.path.exists(dest):
            os.remove(dest)
        shutil.move(file, dest)

    return 0

if __name__ == "__main__":
    main()
