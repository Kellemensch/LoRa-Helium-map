# Download
# import cdsapi

# dataset = "reanalysis-era5-pressure-levels"
# request = {
#     "product_type": ["reanalysis"],
#     "variable": [
#         "relative_humidity",
#         "temperature"
#     ],
#     "year": ["2025"],
#     "month": ["07"],
#     "day": [
#         "01", "02", "03",
#         "04", "05", "06",
#         "07", "08", "09",
#         "10", "11", "12",
#         "13", "14", "15",
#         "16", "17", "18"
#     ],
#     "time": ["00:00", "12:00"],
#     "pressure_level": [
#         "800", "825", "850",
#         "875", "900", "925",
#         "950", "975", "1000"
#     ],
#     "data_format": "grib",
#     "download_format": "zip"
# }

# client = cdsapi.Client()
# client.retrieve(dataset, request).download()







# import cdsapi

# dataset = "reanalysis-era5-pressure-levels"
# request = {
#     "product_type": ["reanalysis"],
#     "variable": [
#         "geopotential",
#         "relative_humidity",
#         "temperature"
#     ],
#     "year": ["2025"],
#     "month": ["07"],
#     "day": ["15"],
#     "time": [
#         "00:00", "01:00", "02:00",
#         "03:00", "04:00", "05:00",
#         "06:00", "07:00", "08:00",
#         "09:00", "10:00", "11:00",
#         "12:00", "13:00", "14:00",
#         "15:00", "16:00", "17:00",
#         "18:00", "19:00", "20:00",
#         "21:00", "22:00", "23:00"
#     ],
#     "pressure_level": [
#         "800", "825", "850",
#         "875", "900", "925",
#         "950", "975", "1000"
#     ],
#     "data_format": "grib",
#     "download_format": "zip",
#     "area": [90, -180, -90, 180]
# }

# client = cdsapi.Client()
# client.retrieve(dataset, request).download()





# import xarray as xr
# import numpy as np
# import matplotlib.pyplot as plt
# import cartopy.crs as ccrs
# import cartopy.feature as cfeature
# from datetime import datetime

# # === Paramètres ===
# GRIB_FILE = "6fec2b315499ecaaa7b80c2e686b4f6d/data.grib"  # chemin vers ton fichier .grib
# TARGET_DATETIME = "2023-07-15T12:00"  # date/heure à analyser
# LAT_MIN, LAT_MAX = 35, 70
# LON_MIN, LON_MAX = -15, 40

# # === Lecture GRIB ===
# ds = xr.open_dataset(GRIB_FILE, engine="cfgrib")

# # Vérifie les noms
# print(ds)

# print("Dates disponibles :", ds.time.values)

# # === Extraction date/heure + zone géo ===
# # 1. Sélectionner l'heure la plus proche (sans toucher à lat/lon)
# ds_time = ds.sel(time=np.datetime64(TARGET_DATETIME), method='nearest')

# # 2. Sélectionner la région ensuite
# ds_t = ds_time.sel(latitude=slice(LAT_MAX, LAT_MIN),
#                    longitude=slice(LON_MIN, LON_MAX))


# # === Récupération des variables ===
# T = ds_t['t']  # Température en K
# RH = ds_t['r']  # Humidité relative en %
# P = ds_t['isobaricInhPa'].values  # niveaux de pression en hPa

# # === Altitudes approximées par niveau de pression ===
# P0 = 1013.25  # hPa
# Hs = 7500     # échelle de pression
# z = -np.log(P / P0) * Hs  # altitude en m

# # === Calcul de N (réfractivité) ===
# T_C = T - 273.15
# es = 6.112 * np.exp((17.67 * T_C) / (T_C + 243.5))  # hPa
# e = (RH / 100.0) * es
# N = 77.6 * P[:, None, None] / T + 3.73e5 * e / T**2  # même shape que T

# # === Calcul du gradient vertical dN/dh (entre 2 niveaux ex: 1000 et 925 hPa) ===
# level_top = 925
# level_bottom = 1000

# idx_top = np.where(P == level_top)[0][0]
# idx_bot = np.where(P == level_bottom)[0][0]

# N_top = N[idx_top, :, :]
# N_bot = N[idx_bot, :, :]
# dz = z[idx_top] - z[idx_bot]

# dN_dh = (N_top - N_bot) / dz * 1000  # en N/km

# # === Détection ducting (seuil = -157 N/km) ===
# ducting_mask = dN_dh < -157

# # === Carte ===
# fig = plt.figure(figsize=(10, 8))
# ax = plt.axes(projection=ccrs.PlateCarree())
# ax.set_extent([LON_MIN, LON_MAX, LAT_MIN, LAT_MAX], crs=ccrs.PlateCarree())
# ax.coastlines()
# ax.add_feature(cfeature.BORDERS, linestyle=':')

# lon2d, lat2d = np.meshgrid(ds_t.longitude, ds_t.latitude)

# cf = ax.contourf(lon2d, lat2d, ducting_mask, levels=[0, 0.5, 1],
#                  colors=["white", "red"], alpha=0.6)

# plt.title(f"Ducting détecté ({level_bottom}-{level_top} hPa)\n{TARGET_DATETIME}")
# plt.colorbar(cf, ax=ax, label="Ducting")
# plt.show()


import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import imageio
from datetime import datetime
from io import BytesIO

# === PARAMÈTRES ===
ERA5_GRIB_FILE = "July15-AllHours/data.grib"  # ton fichier GRIB
TARGET_DATE = "2025-07-15"
PRESSURE_LEVELS = [1000, 975, 950, 925, 900, 850]
R_DUCTING = -157  # seuil de ducting (N/km)

# Domaine européen
LAT_MIN, LAT_MAX = 30, 70
LON_MIN, LON_MAX = -15, 40

# === CHARGEMENT ===
ds = xr.open_dataset(ERA5_GRIB_FILE, engine="cfgrib")
ds = ds.sel(isobaricInhPa=PRESSURE_LEVELS)

# Filtrage sur l'Europe
ds = ds.sel(latitude=slice(LAT_MAX, LAT_MIN), longitude=slice(LON_MIN, LON_MAX))

# Filtrage sur une seule journée
all_times = ds.time.sel(time=ds.time.dt.date == np.datetime64(TARGET_DATE)).values

print(f" {len(all_times)} timestamps trouvés pour {TARGET_DATE}")

# === PRÉPARATION GIF ===
frames = []

for t in all_times:
    # Sous-ensemble temporel
    d = ds.sel(time=t)

    T = d['t'] - 273.15  # [K] → [°C]
    RH = d['r']          # [%]
    P = d['isobaricInhPa']       # [hPa]

    # === Calcul de N ===
    es = 6.112 * np.exp((17.67 * T) / (T + 243.5))              # pression de vapeur saturante [hPa]
    e = RH / 100 * es                                           # pression de vapeur réelle
    N = (77.6 * P / (T + 273.15)) + (64.8 * e / (T + 273.15)) + (3.776e5 * e / (T + 273.15) ** 2)

    # === Gradient vertical ΔN/Δh ===
    H = d['z'] / 9.80665  # géopotentiel → géopotentiel height [m]
    dN = np.gradient(N, axis=0)
    dH = np.gradient(H, axis=0)
    dN_dH = dN / dH * 1000  # [N/km]

    # === Ducting mask ===
    ducting_mask = (dN_dH.min(axis=0) < R_DUCTING)

    # === Carte ===
    fig = plt.figure(figsize=(8, 6))
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.set_extent([LON_MIN, LON_MAX, LAT_MIN, LAT_MAX])
    ax.add_feature(cfeature.BORDERS, linewidth=0.5)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
    ax.add_feature(cfeature.LAND, facecolor='lightgray')
    ax.add_feature(cfeature.OCEAN, facecolor='lightblue')

    duct = ducting_mask.astype(int)
    lat = ds.latitude.values
    lon = ds.longitude.values
    Lon, Lat = np.meshgrid(ds.longitude, ds.latitude)

    cs = ax.pcolormesh(Lon, Lat, duct, cmap='Reds', shading='auto', alpha=0.6)
    ax.set_title(f"Ducting – {np.datetime_as_string(t, unit='h')} UTC")

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    frames.append(imageio.v2.imread(buf))
    plt.close(fig)

# === Sauvegarde GIF ===
imageio.mimsave("ducting_europe_july15.gif", frames, duration=0.6)
print(" GIF généré : ducting_europe.gif")
