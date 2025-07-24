import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
import matplotlib.pyplot as plt
import numpy as np
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import time
from itertools import islice


# === PARAMÈTRES GÉNÉRAUX ===
LAT_C, LON_C = 45.70377, 13.7204
START_DATE = "2025-07-15"
END_DATE = "2025-07-15"
CHUNKS = 100
STEP_DEG = 0.01
RADIUS_DEG = 2.0


def generate_surrounding_points(lat_center, lon_center, step_deg=0.5, radius_deg=1.0):
    """
    Génère une grille de points autour du point central avec un pas plus fin.

    :param lat_center: Latitude du point central
    :param lon_center: Longitude du point central
    :param step_deg: Pas en degrés (plus petit = plus dense)
    :param radius_deg: Distance maximale depuis le centre (en degrés)
    :return: liste de (lat, lon)
    """
    lats = np.arange(lat_center - radius_deg, lat_center + radius_deg + step_deg, step_deg)
    lons = np.arange(lon_center - radius_deg, lon_center + radius_deg + step_deg, step_deg)
    points = [(lat, lon) for lat in lats for lon in lons]
    return points


def chunk_points(points, n=10):
    """Découpe la liste en sous-listes de n points maximum."""
    it = iter(points)
    return iter(lambda: list(islice(it, n)), [])


# Grille autour du point central (3x3)
LAT_POINTS = [LAT_C + dy for dy in [-0.5, 0, 0.5]]
LON_POINTS = [LON_C + dx for dx in [-0.5, 0, 0.5]]
# POINTS = [(lat, lon) for lat in LAT_POINTS for lon in LON_POINTS]
POINTS = generate_surrounding_points(LAT_C, LON_C, STEP_DEG, RADIUS_DEG)

# API Open-Meteo
cache_session = requests_cache.CachedSession('.cache', expire_after=86400)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
client = openmeteo_requests.Client(session=retry_session)

# Pressions disponibles
pressure_levels = ['1000hPa', '975hPa', '950hPa', '925hPa', '900hPa', '850hPa']
pressures = [1000, 975, 950, 925, 900, 850]
num_levels = len(pressures)

# Fonction de récupération des données pour un point
def get_point_data(lat, lon):
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": [f"temperature_{p}" for p in pressure_levels] +
                  [f"geopotential_height_{p}" for p in pressure_levels] +
                  [f"relative_humidity_{p}" for p in pressure_levels],
        "start_date": START_DATE,
        "end_date": END_DATE,
        "timezone": "UTC",
    }
    response = client.weather_api(url, params=params)[0]
    hourly = response.Hourly()
    time_range = pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left"
    )
    num_times = len(time_range)
    data = np.empty((num_times, num_levels, 4))
    data.fill(np.nan)

    for i, level in enumerate(pressure_levels):
        T = hourly.Variables(i).ValuesAsNumpy() + 273.15
        H = hourly.Variables(i + num_levels).ValuesAsNumpy()
        RH = hourly.Variables(i + 2 * num_levels).ValuesAsNumpy()
        data[:, i, 0] = np.where(T == -9999, np.nan, T)
        data[:, i, 1] = np.where(H == -9999, np.nan, H)
        data[:, i, 2] = np.where(RH == -9999, np.nan, RH)

    # Calcul de N (indice de réfractivité)
    for t in range(num_times):
        for j in range(num_levels):
            T = data[t, j, 0]
            RH = data[t, j, 2]
            P = pressures[j]
            if not np.isnan(T) and not np.isnan(RH):
                es = 6.112 * np.exp((17.67 * (T - 273.15)) / ((T - 273.15) + 243.5))
                e = (RH / 100) * es
                N = (77.6 * P / T) + (64.8 * e / T) + (3.776e5 * e / (T**2))
                data[t, j, 3] = N

    return time_range, data

def get_point_data_chunck() :
    ducting_by_time = {}

    for group in chunk_points(POINTS, CHUNKS):
        # print(group)
        # Construire les chaînes de latitude et longitude séparées par des virgules
        latitudes = ','.join(str(lat) for lat, _ in group)
        longitudes = ','.join(str(lon) for _, lon in group)

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitudes,
            "longitude": longitudes,
            "hourly": [f"temperature_{p}" for p in pressure_levels] +
                    [f"geopotential_height_{p}" for p in pressure_levels] +
                    [f"relative_humidity_{p}" for p in pressure_levels],
            "start_date": START_DATE,
            "end_date": END_DATE,
            "timezone": "UTC",
        }

        responses = client.weather_api(url, params=params)
        for i, response in enumerate (responses):
            lat, lon = group[i]
            hourly = response.Hourly()
            time_range = pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left"
            )
            num_times = len(time_range)
            data = np.empty((num_times, num_levels, 4))
            data.fill(np.nan)

            for i, level in enumerate(pressure_levels):
                T = hourly.Variables(i).ValuesAsNumpy() + 273.15
                H = hourly.Variables(i + num_levels).ValuesAsNumpy()
                RH = hourly.Variables(i + 2 * num_levels).ValuesAsNumpy()
                data[:, i, 0] = np.where(T == -9999, np.nan, T)
                data[:, i, 1] = np.where(H == -9999, np.nan, H)
                data[:, i, 2] = np.where(RH == -9999, np.nan, RH)

            # Calcul de N (indice de réfractivité)
            for t in range(num_times):
                for j in range(num_levels):
                    T = data[t, j, 0]
                    RH = data[t, j, 2]
                    P = pressures[j]
                    if not np.isnan(T) and not np.isnan(RH):
                        es = 6.112 * np.exp((17.67 * (T - 273.15)) / ((T - 273.15) + 243.5))
                        e = (RH / 100) * es
                        N = (77.6 * P / T) + (64.8 * e / T) + (3.776e5 * e / (T**2))
                        data[t, j, 3] = N
            
            for t_idx, dt in enumerate(time_range):
                profile = data[t_idx, :, :]
                df = pd.DataFrame({
                    "pressure": pressures,
                    "T": profile[:, 0],
                    "H": profile[:, 1],
                    "RH": profile[:, 2],
                    "N": profile[:, 3]
                }).dropna().sort_values("H")

                if len(df) < 2:
                    continue

                dN_dh = np.diff(df["N"]) / np.diff(df["H"]) * 1000  # en N/km
                min_gradient = np.min(dN_dh)
                ducting = min_gradient < -157
                if ducting : print(f"at {lat};{lon} : ducting at {dt} : {min_gradient}")

                if dt not in ducting_by_time:
                    ducting_by_time[dt] = []
                ducting_by_time[dt].append((lat, lon, ducting))
        # time.sleep(10.1)

    return ducting_by_time

# Récupération et analyse des points
ducting_by_time = {}
# # print(POINTS)
ducting_by_time = get_point_data_chunck()


# for lat, lon in POINTS:
#     time_range, data = get_point_data(lat, lon)
#     np.savez_compressed(f"cache/data_{lat:.4f}_{lon:.4f}.npz", time=pd.Series(time_range).astype(str).values, data=data)
#     for t_idx, dt in enumerate(time_range):
#         profile = data[t_idx, :, :]
#         df = pd.DataFrame({
#             "pressure": pressures,
#             "T": profile[:, 0],
#             "H": profile[:, 1],
#             "RH": profile[:, 2],
#             "N": profile[:, 3]
#         }).dropna().sort_values("H")

#         if len(df) < 2:
#             continue

#         dN_dh = np.diff(df["N"]) / np.diff(df["H"]) * 1000  # en N/km
#         min_gradient = np.min(dN_dh)
#         ducting = min_gradient < -157
#         if ducting : print(f"at {lat};{lon} : ducting at {dt} : {min_gradient}")

#         if dt not in ducting_by_time:
#             ducting_by_time[dt] = []
#         ducting_by_time[dt].append((lat, lon, ducting))
    # time.sleep(2)

# # === AFFICHAGE DES CARTES PAR HEURE ===
# for dt, results in ducting_by_time.items():
#     fig = plt.figure(figsize=(6, 6))
#     ax = plt.axes(projection=ccrs.PlateCarree())
#     ax.set_extent([LON_C - 2, LON_C + 2, LAT_C - 2, LAT_C + 2])
#     ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
#     ax.add_feature(cfeature.BORDERS, linewidth=0.5)
#     ax.add_feature(cfeature.LAND, facecolor='lightgray')
#     ax.add_feature(cfeature.OCEAN, facecolor='lightblue')

#     for lat, lon, duct in results:
#         color = 'red' if duct else 'green'
#         ax.plot(lon, lat, marker='o', color=color, markersize=10)

#     ax.set_title(f"Ducting – {dt.strftime('%Y-%m-%d %H:%M UTC')}")
#     plt.tight_layout()
#     plt.show()

import imageio
from io import BytesIO

# Créer une liste d'images à partir des cartes matplotlib
frames = []

for dt, results in sorted(ducting_by_time.items()):
    fig = plt.figure(figsize=(6, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([LON_C - 2, LON_C + 2, LAT_C - 2, LAT_C + 2])
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5)
    ax.add_feature(cfeature.LAND, facecolor='lightgray')
    ax.add_feature(cfeature.OCEAN, facecolor='lightblue')

    for lat, lon, duct in results:
        color = 'red' if duct else 'green'
        ax.plot(lon, lat, marker='o', color=color, markersize=10)

    ax.set_title(f"Ducting – {dt.strftime('%Y-%m-%d %H:%M UTC')}")
    plt.tight_layout()

    # Sauvegarde dans un buffer mémoire
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    frames.append(imageio.v2.imread(buf))
    plt.close(fig)

# Enregistrer le GIF
imageio.mimsave("ducting_map2.gif", frames, duration=0.5)
print("✅ GIF généré : ducting_map2.gif")

import numpy as np
from scipy.interpolate import griddata

frames = []
grid_res = 100  # Résolution de la grille

for dt, results in sorted(ducting_by_time.items()):
    # Préparer les points et valeurs
    lats, lons, values = zip(*results)
    points = np.column_stack((lons, lats))
    values_binary = [1 if v else 0 for v in values]

    # Créer la grille régulière autour du point central
    lon_grid = np.linspace(LON_C - 2, LON_C + 2, grid_res)
    lat_grid = np.linspace(LAT_C - 2, LAT_C + 2, grid_res)
    lon_mesh, lat_mesh = np.meshgrid(lon_grid, lat_grid)

    # Interpolation binaire (méthode "nearest" pour éviter artefacts flottants)
    grid_z = griddata(points, values_binary, (lon_mesh, lat_mesh), method='nearest')

    # Plot
    fig = plt.figure(figsize=(6, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([LON_C - 2, LON_C + 2, LAT_C - 2, LAT_C + 2])
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
    ax.add_feature(cfeature.BORDERS, linewidth=0.5)
    ax.add_feature(cfeature.LAND, facecolor='lightgray')
    ax.add_feature(cfeature.OCEAN, facecolor='lightblue')

    # Affichage de l'interpolation
    cmap = plt.get_cmap('RdYlGn_r')
    cs = ax.pcolormesh(lon_mesh, lat_mesh, grid_z, cmap=cmap, shading='auto', vmin=0, vmax=1, alpha=0.6)

    # Ajout des points originaux
    for lon, lat, val in zip(lons, lats, values_binary):
        ax.plot(lon, lat, 'ko' if val else 'wo', markersize=4)

    ax.set_title(f"Ducting Interpolé – {dt.strftime('%Y-%m-%d %H:%M UTC')}")
    plt.tight_layout()

    # Sauvegarde en buffer pour le GIF
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    frames.append(imageio.v2.imread(buf))
    plt.close(fig)

# Génération du GIF
imageio.mimsave("ducting_interpolated2.gif", frames, duration=0.5)
print("✅ GIF interpolé généré : ducting_interpolated2.gif")
