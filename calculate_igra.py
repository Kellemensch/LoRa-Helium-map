import os
import sys
import subprocess
import datetime
import pandas as pd
from math import radians, cos, sin, sqrt, atan2, degrees
import matplotlib.pyplot as plt
import argparse
import json
import glob
from configs.config_coords import END_DEVICE_LAT, END_DEVICE_LON

last_message_type = None  # Global tracker for logs

CURRENT_YEAR = datetime.datetime.now().year

IGRA_FTP = "ftp://ftp.ncei.noaa.gov/pub/data/igra/derived/derived-por/"
IGRA_STATIONS_FILE = "ftp://ftp.ncei.noaa.gov/pub/data/igra/igra2-station-list.txt"
LOCAL_DIR = "/app/output/igra-datas/derived/"
INPUT_CSV = "/app/output/data/helium_gateway_data.csv"
OUTPUT_CSV = "/app/output/igra-datas/weather-data.csv"
STATIONS_FILE = "/app/output/igra-datas/igra2-station-list.txt"
OUTPUT_JSON = "/app/output/igra-datas/map_links.json"
GRADIENT_CACHE_FILE = "/app/output/processed_gradients.json"

EARTH_RADIUS = 6371.0

parser = argparse.ArgumentParser()
parser.add_argument("--logs", action="store_true")
args = parser.parse_args()


def log(message):
    global last_message_type

    is_repeat = message.startswith("Already processed") or message.startswith("No sounding")

    if is_repeat:
        if last_message_type == "repeat":
            # Écrase proprement la ligne précédente
            print(f"\r[LOG] {message.ljust(80)}", end="", flush=True)
        else:
            print(f"[LOG] {message}", end="", flush=True)
        last_message_type = "repeat"
    else:
        # Si on sort d'une répétition, terminer proprement la ligne précédente
        if last_message_type == "repeat":
            print()  # pour forcer un retour à la ligne
        print(f"[LOG] {message}")
        last_message_type = "other"


os.makedirs(LOCAL_DIR, exist_ok=True)
# Supprime les anciens fichiers pour être sûr d'avoir les infos les plus récentes (png et données IGRA)
for file in glob.glob(f"{LOCAL_DIR}ITM*-drvd.txt"):
    os.remove(file)
log("Removed old IGRA data files")


def load_processed_gradients():
    if os.path.exists(GRADIENT_CACHE_FILE):
        try:
            with open(GRADIENT_CACHE_FILE, "r") as f:
                raw = json.load(f)
                return {gw: set(dates) for gw, dates in raw.items()}
        except Exception as e:
            log(f"[CACHE ERROR] Could not load gradient cache: {str(e)}")
    return {}


def save_processed_gradients(cache):
    try:
        with open(GRADIENT_CACHE_FILE, "w") as f:
            json.dump({gw: sorted(list(dates)) for gw, dates in cache.items()}, f, indent=2)
        log(f"[CACHE] Saved processed gradients for {len(cache)} gateways")
    except Exception as e:
        log(f"[CACHE ERROR] Could not save gradient cache: {str(e)}")



def get_stations():
    # Télécharge le fichier des stations
    if not os.path.exists(STATIONS_FILE):
        try:
            subprocess.run(["wget", "-O", STATIONS_FILE, IGRA_STATIONS_FILE], check=True)
        except subprocess.CalledProcessError:
            log(f"Error downloading {IGRA_STATIONS_FILE}")
            return None
        
    # column LSTYEAR is 78-81
    stations = []
    with open(STATIONS_FILE, "r") as f:
        for line in f:
            if int(line[77:81]) == CURRENT_YEAR:
                # On garde que les stations intéressantes pour nous
                stations.append({"id": line[0:11].strip(), "lat": float(line[12:20].strip()), "lon": float(line[21:30].strip())})

    return stations

def download_igra_file(id):
    # télécharge le zip, décompresse et nettoie pour un id demandé
    
    filename = f"{id}-drvd.txt.zip"
    local_path = os.path.join(LOCAL_DIR, f"{id}-drvd.txt")
    local_path_zip = f"{local_path}.zip"
    if os.path.exists(local_path):
        return local_path
    
    url = f"{IGRA_FTP}{filename}"
    try:
        subprocess.run(["wget", "-O", local_path_zip, url], check=True)
        subprocess.run(["unzip", "-j", local_path_zip, "-d", LOCAL_DIR], check=True) # unzip sans créer de répertoire
        subprocess.run(["rm", local_path_zip])
        return local_path
    except subprocess.CalledProcessError:
        log(f"Error downloading {url}")
        subprocess.run(["rm", local_path_zip])
        return None
    
def haversine(lat1, lon1, lat2, lon2):
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return EARTH_RADIUS * 2 * atan2(sqrt(a), sqrt(1 - a))

def spherical_midpoint(lat1, lon1, lat2, lon2):
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlon = lon2 - lon1

    Bx = cos(lat2) * cos(dlon)
    By = cos(lat2) * sin(dlon)

    lat3 = atan2(
        sin(lat1) + sin(lat2),
        sqrt((cos(lat1) + Bx)**2 + By**2)
    )
    lon3 = lon1 + atan2(By, cos(lat1) + Bx)

    # Convert back to degrees
    return degrees(lat3), degrees(lon3)

def find_closest_station(lat, lon, stations):
    closest = None
    min_dist = float("inf")
    for s in stations:
        dist = haversine(lat, lon, s["lat"], s["lon"])
        if dist < min_dist:
            min_dist = dist
            closest = s

    return closest


def parse_igra_derived_file(filepath, target_year, target_month, target_day):
    with open(filepath, 'r') as file:
        lines = file.readlines()

    data = []
    current_sounding = None
    inside_target_day = False

    for line in lines:
        if line.startswith('#'):
            year = int(line[13:17])
            month = int(line[18:20])
            day = int(line[21:23])

            if year == target_year and month == target_month and day == target_day:
                inside_target_day = True
                if current_sounding:
                    data.append(current_sounding)
                current_sounding = {'date': (year, month, day), 'levels': []}
            else:
                inside_target_day = False
        elif inside_target_day and current_sounding:
            try:
                height = int(line[16:23].strip())
                N = int(line[144:151].strip())
                if height != -99999 and N != -99999:
                    current_sounding['levels'].append((height, N))
            except ValueError:
                continue

    if current_sounding and current_sounding['levels']:
        data.append(current_sounding)

    return data

def compute_gradients(levels):
    gradients = []
    for i in range(len(levels) - 1):
        h1, N1 = levels[i]
        h2, N2 = levels[i + 1]
        if h2 != h1:
            dN_dh = (N2 - N1) / (h2 - h1) * 1000  # N/km
            gradients.append((h1, dN_dh))
    return gradients

def plot_gradients(gradients, output_file, title_date, gateway_name, station_id):
    heights = [h for h, _ in gradients]
    dn_dh = [v for _, v in gradients]

    # Appel à l'IA locale (Ollama)
    zones = detect_duct_zones(gradients)
    # prompt = generate_prompt_from_zones(zones)
    # description = call_ollama(station_id, title_date, prompt)
    description = describe_ducting_case(zones)

    # Créer la figure avec 2 zones : graphe + texte
    fig, axs = plt.subplots(2, 1, figsize=(6, 10), gridspec_kw={'height_ratios': [3, 1]})

    # Partie haute : le graphe
    axs[0].plot(dn_dh, heights, label='dN/dh (km⁻¹)', color='blue')
    axs[0].axvline(-157, color='red', linestyle='--', label='Ducting threshold (-157 km⁻¹)')
    axs[0].invert_yaxis()
    axs[0].set_xlabel('Refractivity gradient (km⁻¹)')
    axs[0].set_ylabel('Height (m)')
    axs[0].set_title(f'Refractivity gradient of {gateway_name} – {title_date} (Station {station_id})', wrap=True)
    axs[0].grid(True)
    axs[0].legend()

    # Partie basse : le texte généré
    axs[1].axis('off')
    # axs[1].text(0.01, 0.9, "IA's analysis :", fontsize=10, fontweight='bold', transform=axs[1].transAxes)
    axs[1].text(0.01, 0.7, description, fontsize=9, wrap=True, transform=axs[1].transAxes)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    plt.close()
    log(f"Graph with analysis saved in {output_file}")



def detect_duct_zones(gradients, threshold=-157):
    duct_zones = []
    for i, (h, g) in enumerate(gradients[1:], start=1):
        if g < threshold:
            h_start = gradients[i - 1][0]
            h_end = gradients[i][0]
            duct_zones.append((h_start, h_end, g))
    return duct_zones

def describe_ducting_case(duct_zones):
    if not duct_zones:
        return (
            "Standard atmospheric conditions — no ducting layer detected.\n"
            "Signal propagation is expected to follow normal line-of-sight or slightly refracted paths."
        )

    # Générer une description des hauteurs de chaque zone
    zone_descriptions = []
    for i, (h_start, h_end, gradient) in enumerate(duct_zones, 1):
        zone_descriptions.append(f"  Layer {i}: from {h_start:.1f} m to {h_end:.1f} m (gradient = {gradient:.2f} N/km)")

    zones_text = "\nDucting layers detected at the following altitudes:\n" + "\n".join(zone_descriptions)

    # Analyse des types de ducting
    surface_based = any(h_start <= 100 for h_start, h_end, g in duct_zones)
    elevated = any(h_start > 100 for h_start, h_end, g in duct_zones)

    if surface_based and elevated:
        main_desc = (
            "Multiple ducting layers detected — both surface-based and elevated ducts are present.\n"
            "Radio signals may experience strong atmospheric trapping at multiple altitudes."
        )
    elif surface_based:
        main_desc = (
            "Surface-based duct detected — strong negative gradient near the ground.\n"
            "Radio signals may travel much farther than usual along the surface due to atmospheric trapping."
        )
    elif elevated:
        main_desc = (
            "Elevated duct layer identified — negative refractivity gradient above ground level.\n"
            "Radio signals may be trapped between atmospheric layers, enabling long-range propagation over the horizon."
        )
    else:
        main_desc = (
            "Potential ducting conditions — negative refractivity gradient observed, but marginal.\n"
            "Unstable or transitional atmospheric layer may cause intermittent signal trapping."
        )

    return f"{main_desc}{zones_text}"



def main(test_index=None):
    df = pd.read_csv(INPUT_CSV)
    df["gwTime"] = pd.to_datetime(df["gwTime"], format='ISO8601')

    stations = get_stations()

    # Mode test unitaire : traiter seulement une ligne
    if test_index is not None:
        df = df.iloc[[test_index]]

    already_processed = load_processed_gradients()
    json_output = {}

    for _, row in df.iterrows():
        lat, lon = row["gateway_lat"], row["gateway_long"]
        mid_lat, mid_lon = spherical_midpoint(lat, lon, END_DEVICE_LAT, END_DEVICE_LON)
        date = row["gwTime"]
        gw_name = row["gateway_name"]
        gw_id = row["gatewayId"]
        visibility = row["visibility"]
        output_image = f"{LOCAL_DIR}gradient_{gw_name}_{date.strftime('%Y-%m-%d')}.png"


        date_str = date.date().isoformat()

        if visibility == "LOS":
            # passer les LOS pour pas avoir de graphes inutiles
            continue

        if gw_name in already_processed and date_str in already_processed[gw_name]:
            log(f"Already processed : ({gw_name}, {date_str})")
            continue

        # Ajoute l'entrée au cache
        # already_processed.setdefault(gw_name, set()).add(date_str)


        closest = find_closest_station(mid_lat, mid_lon, stations)
        if not closest:
            log("No near station found.")
            continue

        igra_file = download_igra_file(closest["id"])
        if not igra_file or not os.path.exists(igra_file):
            log(f"IGRA file not found : {igra_file}")
            continue

        results = parse_igra_derived_file(
            igra_file,
            date.year,
            date.month,
            date.day
        )

        if results:
            # Ajoute l'entrée au cache seulement si des résultats sont trouvés
            already_processed.setdefault(gw_name, set()).add(date_str)

            gradients = compute_gradients(results[0]['levels'])
            # gateway_name_safe = row["gateway_name"].replace(" ", "_").replace("/", "_")
            plot_gradients(gradients, output_image, date.strftime('%Y-%m-%d'), gw_name, closest["id"])

            if gw_id not in json_output:
                json_output[gw_id] = {
                    "gateway_name": gw_name,
                    "gateway_coords": [lat, lon],
                    "station_id": closest["id"],
                    "station_coords": [closest["lat"], closest["lon"]],
                    "midpoint": [mid_lat, mid_lon],
                    "graphs": {}  # <- nouveau dictionnaire par date
                }

            # Ajouter le graphe du jour à "graphs"
            date_key = pd.to_datetime(date).strftime("%Y-%m-%d")

            # Seulement si la gateway est en NLOS car plus intéressant
            # if visibility == "NLOS":
            json_output[gw_id]["graphs"][date_key] = output_image


            log("Results found and saved in json")

        else:
            log(f"No sounding found for this date. {date}, for {gw_name}")

    # Écriture du fichier JSON
    if json_output:
        with open(OUTPUT_JSON, "w") as f:
            json.dump(json_output, f, indent=4)

    save_processed_gradients(already_processed)
    log(f"Cache file saved in {GRADIENT_CACHE_FILE}")

    print(f"IGRA graphs saved in {LOCAL_DIR}")
    log(f"Link file saved to {OUTPUT_JSON}")    

# Pour exécuter le script normalement :
main()

# Pour exécuter en mode test sur la ligne 0 :
# if __name__ == "__main__":
    # main(test_index=1)