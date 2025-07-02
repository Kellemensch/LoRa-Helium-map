import os
import math
import zipfile
import requests
import time
from configs.config_coords import END_DEVICE_LAT, END_DEVICE_LON

# === CONFIGURATION UTILISATEUR ===
RADIUS_DEG = 3  # Rayon en degrés autour du point

# === CONSTANTES ===
BASE_URL = "https://srtm.kurviger.de/SRTM3"
DOWNLOAD_DIR = "/app/srtm_hgt_files"
UNZIP_DIR = "/app/maps"

# === FONCTIONS ===
def guess_srtm_region():
    if -35 <= END_DEVICE_LAT <= 37 and -18 <= END_DEVICE_LON <= 52:
        print("Guessed region : Africa")
        return "Africa"
    elif 0 <= END_DEVICE_LAT <= 83 and -10 <= END_DEVICE_LON <= 180:
        print("Guessed region : Eurasia")
        return "Eurasia"
    elif 7 <= END_DEVICE_LAT <= 84 and -168 <= END_DEVICE_LON <= -52:
        print("Guessed region : North America")
        return "North_America"
    elif -57 <= END_DEVICE_LAT <= 13 and -82 <= END_DEVICE_LON <= -34:
        print("Guessed region : South America")
        return "South_America"
    elif -50 <= END_DEVICE_LAT <= -10 and 110 <= END_DEVICE_LON <= 180:
        print("Guessed region : Australia")
        return "Australia"
    else:
        print("Guessed region : Islands")
        return "Islands"  # par défaut

def format_tile_name(lat, lon):
    ns = 'N' if lat >= 0 else 'S'
    ew = 'E' if lon >= 0 else 'W'
    base_name = f"{ns}{abs(lat):02.0f}{ew}{abs(lon):03.0f}"
    return base_name

def download_file(url, dest_path, hgt_name, retries=3):
    unzipped_path = os.path.join(UNZIP_DIR, hgt_name + ".hgt")
    if os.path.exists(unzipped_path):
        print(f"Already unziped : {os.path.basename(unzipped_path)}")
        return False

    for attempt in range(retries):
        try:
            print(f"Downloading : {os.path.basename(dest_path)} (attempt {attempt+1})")
            response = requests.get(url, stream=True, timeout=30)
            if response.status_code == 200:
                with open(dest_path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return True
            else:
                print(f"Cannot find ({response.status_code}) : {url}")
                return False
        except Exception as e:
            print(f"Error attempt {attempt+1}: {e}")
            time.sleep(3)  # attend 3s avant retry
    return False


def unzip_file(zip_path, output_dir):
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(output_dir)
        print(f"Unziped : {os.path.basename(zip_path)}")
        os.remove(zip_path)
    except Exception as e:
        print(f"Error unzipping : {e}")

def get_tiles_around(lat, lon, radius=1):
    tiles = []
    for la in range(math.floor(lat - radius), math.floor(lat + radius) + 1):
        for lo in range(math.floor(lon - radius), math.floor(lon + radius) + 1):
            tiles.append((la, lo))
    return tiles

# === SCRIPT PRINCIPAL ===
if __name__ == "__main__":
    print("Downloading terrain data for good use of Splat! tool...")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(UNZIP_DIR, exist_ok=True)

    tiles = get_tiles_around(END_DEVICE_LAT, END_DEVICE_LON, RADIUS_DEG)
    region = guess_srtm_region()

    for lat_tile, lon_tile in tiles:
        base_name = format_tile_name(lat_tile, lon_tile)
        file_name = base_name + ".hgt.zip"
        url = f"{BASE_URL}/{region}/{file_name}"
        zip_path = os.path.join(DOWNLOAD_DIR, file_name)

        if download_file(url, zip_path, base_name):
            unzip_file(zip_path, UNZIP_DIR)
            # print("Waiting 5s to respect Web Archive quota, please wait...")
            # time.sleep(5)  # 5 secondes de pause pour éviter les blocages
