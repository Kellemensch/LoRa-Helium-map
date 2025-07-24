import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time
import os
import json
from tqdm import tqdm

# Constantes globales
CENTRAL_POINT = (45.70377, 13.7204)  # point central
RADIUS_DEGREES = 0.0  # Réduit le rayon pour moins de points
GRID_STEP = 1  # Pas plus grand pour moins de points
ALTITUDES = [0, 100, 300, 500, 1000]  # Moins d'altitudes
DUCTING_THRESHOLD = -157  # Seuil de gradient pour le ducting (N-units/km)

# Paramètres temporels (réduit la période)
START_DATE = datetime.now().date()
END_DATE = START_DATE # + timedelta(days=3)
HOURS = [0, 6, 12, 18]  # Moins d'heures

# Configuration API
API_DELAY = 1  # Délai en secondes entre les requêtes
CACHE_FILE = "weather_cache.json"
MAX_RETRIES = 3

# Charger le cache existant ou en créer un nouveau
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, 'r') as f:
        weather_cache = json.load(f)
else:
    weather_cache = {}

def save_cache():
    """Sauvegarde le cache dans le fichier"""
    with open(CACHE_FILE, 'w') as f:
        json.dump(weather_cache, f)

def calculate_refractivity(pressure, temperature, humidity, altitude):
    """Calcule l'indice de réfractivité N"""
    es = 6.112 * np.exp((17.67 * (temperature - 273.15)) / ((temperature - 273.15) + 243.5))
    e = (humidity / 100) * es
    N = (77.6 * pressure / temperature) - (5.6 * e / temperature) + (3.75e5 * e / (temperature ** 2))
    print("refractivity : ", N)
    return N

def fetch_weather_data(lat, lon, altitude, date):
    """Récupère les données météo avec gestion du cache et des erreurs"""
    cache_key = f"{lat}_{lon}_{altitude}_{date}"
    
    # Vérifier le cache d'abord
    if cache_key in weather_cache:
        return weather_cache[cache_key]
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        'latitude': lat,
        'longitude': lon,
        'elevation': altitude,
        'hourly': 'temperature_2m,relativehumidity_2m,pressure_msl',
        'start_date': date.strftime('%Y-%m-%d'),
        'end_date': date.strftime('%Y-%m-%d'),
        'timezone': 'auto'
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(API_DELAY)  # Respecter le taux de requêtes
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()['hourly']
            
            # Stocker toutes les heures pour ce jour/altitude
            weather_cache[cache_key] = data
            save_cache()
            return data
            
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:  # Too Many Requests
                wait_time = 10 * (attempt + 1)  # Backoff exponentiel
                print(f"Attente {wait_time}s avant réessai...")
                time.sleep(wait_time)
                continue
            print(f"Erreur HTTP pour {lat},{lon} à {altitude}m: {str(e)}")
        except Exception as e:
            print(f"Erreur pour {lat},{lon} à {altitude}m: {str(e)}")
        
        return None

def analyze_ducting_for_location(lat, lon, date, hour):
    """Analyse la possibilité de ducting pour une localisation et un moment"""
    results = []
    
    for altitude in ALTITUDES:
        data = fetch_weather_data(lat, lon, altitude, date)
        if not data:
            continue
            
        # Trouver l'index de l'heure demandée
        time_index = None
        for i, time_str in enumerate(data['time']):
            if datetime.fromisoformat(time_str).hour == hour:
                time_index = i
                break
                
        if time_index is None:
            continue
            
        try:
            temp = data['temperature_2m'][time_index] + 273.15
            humidity = data['relativehumidity_2m'][time_index]
            pressure = data['pressure_msl'][time_index]
            
            N = calculate_refractivity(pressure, temp, humidity, altitude)
            results.append({
                'altitude': altitude,
                'N': N,
                'temperature': temp,
                'humidity': humidity,
                'pressure': pressure
            })
            print("append results")
        except (KeyError, IndexError) as e:
            print(f"Données manquantes pour {lat},{lon} à {altitude}m: {str(e)}")
    
    if not results:
        return None
        
    # Trier par altitude et calculer les gradients
    results.sort(key=lambda x: x['altitude'])
    ducting_conditions = []
    
    for i in range(1, len(results)):
        delta_N = results[i]['N'] - results[i-1]['N']
        delta_h = (results[i]['altitude'] - results[i-1]['altitude']) / 1000
        gradient = delta_N / delta_h
        print("gradient : ", gradient)
        
        ducting_conditions.append({
            'altitude_bottom': results[i-1]['altitude'],
            'altitude_top': results[i]['altitude'],
            'gradient': gradient,
            'is_ducting': gradient < DUCTING_THRESHOLD
        })
    
    return {
        'coordinates': (lat, lon),
        'date': date,
        'hour': hour,
        'refractivity_profile': results,
        'gradients': ducting_conditions,
        'has_ducting': any([cond['is_ducting'] for cond in ducting_conditions])
    }

def generate_grid_around_point(lat, lon, radius, step):
    """Génère une grille de points autour d'une coordonnée centrale"""
    latitudes = np.arange(lat - radius, lat + radius + step, step)
    longitudes = np.arange(lon - radius, lon + radius + step, step)
    grid = [(round(la, 2), round(lo, 2)) for la in latitudes for lo in longitudes]
    return list(set(grid))  # Éliminer les doublons

def main():
    grid_points = generate_grid_around_point(
        CENTRAL_POINT[0], CENTRAL_POINT[1], 
        RADIUS_DEGREES, GRID_STEP
    )
    
    dates = [START_DATE + timedelta(days=i) for i in range((END_DATE - START_DATE).days + 1)]
    all_results = []
    
    print(f"Analyse de {len(grid_points)} points, {len(dates)} jours, {len(HOURS)} heures...")
    
    progress_bar = tqdm(total=len(grid_points)*len(dates)*len(HOURS))
    
    for lat, lon in grid_points:
        for date in dates:
            # D'abord récupérer toutes les altitudes pour ce point/date
            # (plus efficace que de faire une requête par altitude)
            for altitude in ALTITUDES:
                fetch_weather_data(lat, lon, altitude, date)
                
            for hour in HOURS:
                result = analyze_ducting_for_location(lat, lon, date, hour)
                if result:
                    all_results.append(result)
                progress_bar.update(1)
    
    progress_bar.close()
    
    if not all_results:
        print("Aucun résultat valide obtenu. Vérifiez les erreurs.")
        return
    
    df = pd.DataFrame(all_results)
    df.to_csv(f"ducting_analysis_{START_DATE}_{END_DATE}.csv", index=False)
    
    print("Analyse terminée. Génération des graphiques...")
    plot_results(df)

def plot_results(df):
    """Génère des visualisations des résultats"""
    # Carte de ducting pour une date/heure
    sample_date = START_DATE
    sample_hour = 12
    
    subset = df[(df['date'] == sample_date) & (df['hour'] == sample_hour)]
    
    if len(subset) > 0:
        lats = [loc[0] for loc in subset['coordinates']]
        lons = [loc[1] for loc in subset['coordinates']]
        ducting = subset['has_ducting'].astype(int)
        
        plt.figure(figsize=(10, 8))
        sc = plt.scatter(lons, lats, c=ducting, cmap='coolwarm', 
                        vmin=0, vmax=1, s=100)
        plt.scatter(CENTRAL_POINT[1], CENTRAL_POINT[0], c='black', marker='*', s=200)
        plt.title(f"Présence de ducting\nDate: {sample_date} Heure: {sample_hour}h")
        plt.xlabel("Longitude")
        plt.ylabel("Latitude")
        plt.colorbar(sc, label='Ducting (0=Non, 1=Oui)')
        plt.grid(True)
        plt.savefig(f"ducting_map_{sample_date}_{sample_hour}h.png")
        plt.close()
    
    # Profil de réfractivité pour un point avec ducting
    if len(df[df['has_ducting']]) > 0:
        sample_point = df[df['has_ducting']].iloc[0]
        altitudes = [x['altitude'] for x in sample_point['refractivity_profile']]
        N_values = [x['N'] for x in sample_point['refractivity_profile']]
        
        plt.figure(figsize=(8, 6))
        plt.plot(N_values, altitudes, 'b-o')
        
        # Marquer les couches avec ducting
        for grad in sample_point['gradients']:
            if grad['is_ducting']:
                plt.axhspan(grad['altitude_bottom'], grad['altitude_top'], 
                           color='red', alpha=0.2)
        
        plt.xlabel("Indice de réfractivité N")
        plt.ylabel("Altitude (m)")
        plt.title(f"Profil avec ducting\n{sample_point['date']} {sample_point['hour']}h")
        plt.grid(True)
        plt.savefig("refractivity_profile_with_ducting.png")
        plt.close()

if __name__ == "__main__":
    main()