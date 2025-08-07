import os
import glob
import sys
import pygrib
import cdsapi
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnchoredText
from datetime import datetime
import pandas as pd
from math import radians, cos, sin, sqrt, atan2, degrees
from configs.config_coords import END_DEVICE_LAT, END_DEVICE_LON

# ==== CONFIG ====
CSV_LINKS = "/app/output/data/helium_gateway_data.csv"
GRIB_DIR = "/app/output/era5/grib"
PLOT_DIR = "/app/output/era5/plots"
os.makedirs(GRIB_DIR, exist_ok=True)
os.makedirs(PLOT_DIR, exist_ok=True)

delta = 5  # rayon en degré autour du end-node
ERA5_AREA = [END_DEVICE_LAT + delta, END_DEVICE_LON - delta , END_DEVICE_LAT - delta, END_DEVICE_LON + delta]     # [N, W, S, E] (zone utile)
ERA5_PRESSURE_LEVELS = [1000, 950, 900, 850, 800, 750, 700]  # en hPa
ERA5_VARIABLES = ['geopotential', 'temperature', 'relative_humidity']

CDSAPI_RC_PATH = os.path.expanduser("~/.cdsapirc")

EARTH_RADIUS = 6371.0


# ==== SETUP ====

def setup_cdsapi_config():
    """Vérifie et crée le fichier de configuration CDS API si nécessaire."""
    if not os.path.exists(CDSAPI_RC_PATH):
        print(f"[INFO] Creating config file for CDS API: {CDSAPI_RC_PATH}")
        cds_url = "https://cds.climate.copernicus.eu/api"
        cds_key = "799f5ea7-0b16-4242-8056-0b6ba2568107"
        
        config_content = f"""url: {cds_url}
key: {cds_key}"""
        
        try:
            with open(CDSAPI_RC_PATH, 'w') as f:
                f.write(config_content)
            print("[SUCCESS] Config file created.")
            # Sécurité des permissions
            os.chmod(CDSAPI_RC_PATH, 0o600)
        except Exception as e:
            print(f"[ERROR] Cannot create config file: {e}")
            sys.exit(1)
    else:
        print(f"[INFO] Config file CDS API found: {CDSAPI_RC_PATH}")

# Appel de la fonction de configuration avant tout
setup_cdsapi_config()

# Supprimer les anciens graphes créés pour libérer de la place
for file_path in glob.glob(os.path.join(PLOT_DIR, "*ondemand*.png")):
    try:
        os.remove(file_path)
        print(f"Deleted : {file_path}")
    except OSError as e:
        print(f"Error deleting {file_path} : {e}")




def spherical_midpoint(lat1, lon1):
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, END_DEVICE_LAT, END_DEVICE_LON])

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

def download_era5_for_day(day_str):
    """Télécharge ERA5 pour un jour donné si non déjà présent."""
    target_file = os.path.join(GRIB_DIR, f"era5_{day_str}.grib")
    if os.path.exists(target_file):
        print(f"[SKIP] ERA5 already downloaded {day_str}")
        return target_file

    print(f"[DL] Downloading ERA5 file for {day_str}...")
    c = cdsapi.Client()
    c.retrieve(
        'reanalysis-era5-pressure-levels',
        {
            'product_type': ['reanalysis'],
            'variable': ERA5_VARIABLES,
            'year': day_str[:4],
            'month': day_str[5:7],
            'day': day_str[8:10],
            'time': [ # Une heure sur deux
                "00:00", "02:00", "04:00",
                "06:00", "08:00", "10:00",
                "12:00", "14:00", "16:00",
                "18:00", "20:00", "22:00"
            ],
            'data_format': 'grib',
            'pressure_level': ERA5_PRESSURE_LEVELS,
            'area': ERA5_AREA
        },
        target_file
    )
    print(f"[OK] Saved file : {target_file}")
    return target_file

def compute_real_heights(temp, rh, pressure_levels):
    """Calcule les hauteurs géopotentielles réelles."""
    # Conversion en numpy arrays
    temp = np.asarray(temp)
    rh = np.asarray(rh)
    pressure_levels = np.asarray(pressure_levels) * 100  # Convert hPa to Pa
    
    # Calcul de la pression de vapeur saturante (Pa)
    e_s = 6.112 * np.exp(17.67 * (temp - 273.15) / (temp - 273.15 + 243.5)) * 100
    e = (rh / 100.0) * e_s
    
    # Rapport de mélange (kg/kg)
    q = (0.622 * e) / (pressure_levels - e)
    
    # Température virtuelle (K)
    T_v = temp * (1 + 0.61 * q)
    
    # Calcul des hauteurs (m)
    z = np.zeros_like(temp)
    for i in range(1, len(temp)):
        delta_z = (287.05 * (T_v[i-1] + T_v[i]) / 2 / 9.80665 * 
                 np.log(pressure_levels[i-1] / pressure_levels[i]))
        z[i] = z[i-1] + delta_z
    
    return z

def compute_gradient_profile(temp, rh, pressure_levels):
    """Calcule les gradients de réfractivité atmosphérique."""
    # Pression de vapeur (hPa)
    e = rh / 100.0 * 6.112 * np.exp(17.67 * (temp - 273.15) / (temp - 273.15 + 243.5))
    
    # Indice de réfractivité
    N = 77.6 * (pressure_levels / temp) + 3.73e5 * (e / temp**2)
    
    # Hauteurs et gradients
    heights = compute_real_heights(temp, rh, pressure_levels)
    gradients = np.gradient(N, heights) * 1000 # Pour avoir du N/km et non N/m
    
    return heights, gradients

def process_day(grib_file, day_str):
    """Produit le graphe global pour un jour."""
    try:
        grbs = pygrib.open(grib_file)
        
        # Extraire tous les messages
        messages = grbs.select()
        
        # Organiser les données par niveau et variable
        data = {}
        for msg in messages:
            level = msg['level']
            if level not in data:
                data[level] = {}
            data[level][msg['shortName']] = msg
        
        # Récupérer les coordonnées (on prend celles du premier message)
        lats, lons = messages[0].latlons()
        
        # Créer le graphique
        plt.figure(figsize=(12, 6))

        has_ducting = False
        has_noducting = False
        ducting_coords = []
        
        # Pour chaque point de grille
        for i in range(0, lats.shape[0], 2):  # Pas de 2 pour réduire le nombre
            for j in range(0, lats.shape[1], 2):
                # Extraire les profils verticaux
                temp_profile = []
                rh_profile = []
                
                for level in sorted(ERA5_PRESSURE_LEVELS, reverse=True):
                    if level in data:
                        temp_profile.append(data[level]['t'].values[i,j])
                        rh_profile.append(data[level]['r'].values[i,j])
                
                if len(temp_profile) == len(ERA5_PRESSURE_LEVELS):
                    heights, gradients = compute_gradient_profile(
                        np.array(temp_profile),
                        np.array(rh_profile),
                        ERA5_PRESSURE_LEVELS
                    )

                    if np.any(gradients < -157):
                        plt.plot(gradients, heights, color='red', alpha=0.7, linewidth=0.7,
                                 label='Ducting' if not has_ducting else "")
                        has_ducting = True
                        lat = round(float(lats[i, j]), 2)
                        lon = round(float(lons[i, j]), 2)
                        ducting_coords.append(f"{lat}, {lon}")
                    else:
                        plt.plot(gradients, heights, color='gray', alpha=0.3, linewidth=0.7,
                                 label='No Ducting' if not has_noducting else "")
                        has_noducting = True
        
        plt.axvline(x=-157, color='red', linestyle='--', label='Ducting threshold -157 N/km')
        plt.xlabel('Refractivity gradient (N/km)')
        plt.ylabel('Height (m)')
        plt.title(f"Refractivity gradients of all coordinates for each hour of the day {day_str}")
        plt.legend()
        plt.grid(True)
        
        # Encadré des profils ducting
        if ducting_coords:
            coord_text = "\n".join(ducting_coords[:10])  # max 10 pour lisibilité
            if len(ducting_coords) > 10:
                coord_text += f"\n... (+{len(ducting_coords) - 10} more)"
            anchored_text = AnchoredText(f"Profiles with ducting at:\n{coord_text}",
                                         loc='upper right', prop={'size': 8}, frameon=True)
            plt.gca().add_artist(anchored_text)
        
        plot_file = os.path.join(PLOT_DIR, f'gradient_{day_str}.png')
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()
        grbs.close()
        
        print(f"[OK] Saved graph: {plot_file}")
        return plot_file
        
    except Exception as e:
        print(f"[ERROR] Processing {grib_file}: {str(e)}")
        if 'grbs' in locals():
            grbs.close()
        return None

def on_demand(gateway_name, lat, lon, date_str, time_str):
    """Génère un graphique on-demand double (gateway + midpoint)."""
    try:
        grib_file = os.path.join(GRIB_DIR, f'era5_{date_str}.grib')
        if not os.path.exists(grib_file):
            raise FileNotFoundError(f"GRIB file not found: {grib_file}")
        
        grbs = pygrib.open(grib_file)
        
        # Trouver l'heure la plus proche
        hour = int(time_str.split(':')[0])
        closest_hour = min(range(0, 24, 2), key=lambda h: abs(h - hour))
        closest_time = closest_hour * 100  # format ERA5 dans pygrib

        # Filtrer
        temp_msgs = grbs.select(shortName='t', dataTime=closest_time)
        rh_msgs = grbs.select(shortName='r', dataTime=closest_time)
        lats, lons = temp_msgs[0].latlons()

        def extract_profile(lat_, lon_):
            """Sous-fonction pour extraire un profil pour une coordonnée."""
            dist = (lats - lat_)**2 + (lons - lon_)**2
            i, j = np.unravel_index(dist.argmin(), dist.shape)
            temp_profile, rh_profile = [], []
            for level in sorted(ERA5_PRESSURE_LEVELS, reverse=True):
                t_msg = next((m for m in temp_msgs if m['level'] == level), None)
                rh_msg = next((m for m in rh_msgs if m['level'] == level), None)
                if t_msg and rh_msg:
                    temp_profile.append(t_msg.values[i, j])
                    rh_profile.append(rh_msg.values[i, j])
            if len(temp_profile) != len(ERA5_PRESSURE_LEVELS):
                raise ValueError(f"Missing data for some pressure levels at {lat_:.2f},{lon_:.2f}")
            return np.array(temp_profile), np.array(rh_profile)

        # --- Gateway ---
        temp_gw, rh_gw = extract_profile(lat, lon)
        heights_gw, gradients_gw = compute_gradient_profile(temp_gw, rh_gw, ERA5_PRESSURE_LEVELS)

        # --- Point milieu sphérique ---
        lat_mid, lon_mid = spherical_midpoint(lat, lon)
        temp_mid, rh_mid = extract_profile(lat_mid, lon_mid)
        heights_mid, gradients_mid = compute_gradient_profile(temp_mid, rh_mid, ERA5_PRESSURE_LEVELS)

        # --- Affichage ---
        fig, axs = plt.subplots(1, 2, figsize=(12, 6), sharey=True)

        axs[0].plot(gradients_gw, heights_gw, color='blue', label=f'Gateway ({lat:.2f}, {lon:.2f})')
        axs[0].axvline(x=-157, color='red', linestyle='--', label='Ducting threshold -157 N/km')
        axs[0].set_title('Refractivity gradient on gateway point')
        axs[0].set_xlabel('Refractivity gradient (N/km)')
        axs[0].set_ylabel('Height (m)')
        axs[0].invert_yaxis()
        axs[0].grid(True)
        axs[0].legend()

        axs[1].plot(gradients_mid, heights_mid, color='green', label=f'Midpoint ({lat_mid:.2f}, {lon_mid:.2f})')
        axs[1].axvline(x=-157, color='red', linestyle='--', label='Ducting threshold -157 N/km')
        axs[1].set_title('Refractivity gradient on spherical midpoint with end-node')
        axs[1].set_xlabel('Refractivity gradient (N/km)')
        axs[1].invert_yaxis()
        axs[1].grid(True)
        axs[1].legend()

        fig.suptitle(f'ERA5 refractivity gradient - {gateway_name}\n{date_str} at {closest_hour}:00H', fontsize=14)
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])

        plot_file = os.path.join(
            PLOT_DIR,
            f'ondemand_{gateway_name}_{date_str}_{lat:.2f}_{lon:.2f}_vs_midpoint.png'
        )
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()
        grbs.close()

        print(f"[OK] Saved on-demand graph: {plot_file}")
        return plot_file

    except Exception as e:
        print(f"[ERROR] On-demand processing failed: {str(e)}")
        if 'grbs' in locals():
            grbs.close()
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--on-demand":
        if len(sys.argv) != 7:
            print("Usage: era5_gradients.py --on-demand gateway_name lat lon date hour")
            sys.exit(1)
        
        gateway_name = sys.argv[2]
        lat = float(sys.argv[3])
        lon = float(sys.argv[4])
        date_str = sys.argv[5]
        time_str = sys.argv[6]
        
        result = on_demand(gateway_name, lat, lon, date_str, time_str)
        if result:
            print(result)
        sys.exit(0 if result else 1)
    
    # Traitement normal pour tous les jours
    df = pd.read_csv(CSV_LINKS)
    df['date'] = pd.to_datetime(df['gwTime'], format='ISO8601')
    today = datetime.utcnow().date()
    days_needed = sorted(set(d.date().isoformat() for d in df['date']
                        if (today - d.date()).days > 5))
    
    for day_str in days_needed:
        download_era5_for_day(day_str)
        grib_file = os.path.join(GRIB_DIR, f'era5_{day_str}.grib')
        if os.path.exists(grib_file):
            process_day(grib_file, day_str)

    print("[FINISHED] Finished ERA5 computing !")