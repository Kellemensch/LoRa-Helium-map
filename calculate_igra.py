import os
import subprocess
import datetime
import pandas as pd
from math import radians, cos, sin, sqrt, atan2, degrees

CURRENT_YEAR = datetime.datetime.now().year

IGRA_FTP = "ftp://ftp.ncei.noaa.gov/pub/data/igra/data/data-y2d/"
IGRA_STATIONS_FILE = "ftp://ftp.ncei.noaa.gov/pub/data/igra/igra2-station-list.txt"
LOCAL_DIR = "./igra-datas/"
INPUT_CSV = "./data/helium_gateway_data.csv"
OUTPUT_CSV = "./igra-datas/weather-data.csv"
STATIONS_FILE = "./igra-datas/igra2-station-list.txt"

END_NODE_LAT = 45.70377
END_NODE_LON = 13.7204
EARTH_RADIUS = 6371.0

os.makedirs(LOCAL_DIR, exist_ok=True)

def get_stations():
    # Télécharge le fichier des stations
    # try:
    #     subprocess.run(["wget", "-O", STATIONS_FILE, IGRA_STATIONS_FILE], check=True)
    # except subprocess.CalledProcessError:
    #     print(f"Error downloading file {IGRA_STATIONS_FILE}")
    #     subprocess.run(["rm", f"{STATIONS_FILE}"], check=True)
    #     return
        
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
    filename = f"{id}-data-beg2021.txt.zip"
    local_path = os.path.join(LOCAL_DIR, f"{id}-data.txt")
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
        print(f"Error downloading {url}")
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

def extract_weather_for_date(txt_path: str, target_date: datetime.date) -> list[dict]:
    """
    Extrait les enregistrements IGRA correspondant à une date cible.
    
    Args:
        txt_path: chemin vers le fichier IGRA .txt.
        target_date: date (datetime.date) à chercher dans les enregistrements.
    
    Returns:
        Une liste de dictionnaires avec les données météo extraites.
    """
    results = []

    with open(txt_path, 'r') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("#"):
            try:
                year = int(line[13:17])
                month = int(line[18:20])
                day = int(line[21:23])
                hour = int(line[24:26])
                n_levels = int(line[32:36])
                lat = int(line[55:62]) / 1000
                lon = int(line[63:71]) / 1000
                station_id = line[1:12].strip()
            except Exception as e:
                i += 1
                continue

            record_date = datetime.date(year, month, day)

            if record_date == target_date:
                weather_data = {
                    "station_id": station_id,
                    "date": record_date.isoformat(),
                    "hour_utc": hour,
                    "lat": lat,
                    "lon": lon,
                }

                # Lecture des niveaux associés
                levels = []
                for j in range(1, n_levels + 1):
                    if i + j >= len(lines):
                        break
                    lvl_line = lines[i + j]
                    try:
                        pressure = int(lvl_line[9:15])
                        geopot = int(lvl_line[16:21])
                        temp = int(lvl_line[22:27]) / 10 if int(lvl_line[22:27]) != -9999 else None
                        rh = int(lvl_line[28:33]) / 10 if int(lvl_line[28:33]) != -9999 else None
                        wspd = int(lvl_line[46:51]) / 10 if int(lvl_line[46:51]) != -9999 else None
                        wdir = int(lvl_line[40:45]) if int(lvl_line[40:45]) != -9999 else None

                        levels.append({
                            "pressure": pressure,
                            "geopot": geopot,
                            "temp_C": temp,
                            "rh_pct": rh,
                            "wind_speed_mps": wspd,
                            "wind_dir_deg": wdir
                        })
                    except Exception:
                        continue

                weather_data["levels"] = levels
                results.append(weather_data)

            i += n_levels + 1
        else:
            i += 1

    return results

def main():
    df = pd.read_csv(INPUT_CSV)
    df["gwTime"] = pd.to_datetime(df["gwTime"], format='ISO8601')
    stations = get_stations()

    weather_data = []

    for _, row in df.iterrows():
        lat, lon = row["gateway_lat"], row["gateway_long"]
        mid_lat, mid_lon = spherical_midpoint(lat, lon, END_NODE_LAT, END_NODE_LON)
        date = row["gwTime"].date()

        closest = find_closest_station(mid_lat, mid_lon, stations)
        if not closest:
            weather_data.append((None, None, None))
            continue

        igra_file = download_igra_file(closest["id"])
        results = extract_weather_for_date(igra_file, date)
        # weather_data.append((closest["id"], results))

        if results:
            primary_result = results[0]  # ou fais un tri si tu veux l'heure la plus proche
            data = row.to_dict()
            # data["igra_station"] = closest["id"]
            for k, v in primary_result.items():
                if k != "levels":  # tu peux ignorer les niveaux détaillés si tu veux
                    data[k] = v
        else:
            data = row.to_dict()
            # data["igra_station"] = closest["id"]
            data["date"] = None  # ou autre valeur par défaut
            data["hour_utc"] = None

        weather_data.append(data)


        
    # print(weather_data)
    new_df = pd.DataFrame(weather_data)
    new_df.to_csv(OUTPUT_CSV, index=False)
    print(f"File saved in {OUTPUT_CSV}")

main()