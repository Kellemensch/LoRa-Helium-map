# lettura dati ricevuti via http applicazione test_Grove_Wio_E5 attraverso https://console.helium-iot.xyz/front/
# Viene usata la porta 5000
# Creazione di un file csv con i dati
# Versione che calcola la distanza del nodo dal gateway e lo inserisce nel csv

# Author : Marco Rainone

import csv
import os
import math
from flask import Flask, request, jsonify, send_from_directory, send_file, render_template, url_for, Response
import argparse
from datetime import datetime
import pandas as pd
import json
import gzip
from functools import lru_cache
import threading
from collections import defaultdict
import numpy as np
import subprocess
from configs.config_coords import END_DEVICE_LAT, END_DEVICE_LON

# Désactive les logs de requêtes Werkzeug (Flask)
import logging
log = logging.getLogger('werkzeug')
log.disabled = True

parser = argparse.ArgumentParser()
parser.add_argument("--logs", action="store_true")
args = parser.parse_args()

def log(*messages):
    if args.logs:
        print("[LOG]", *messages)

app = Flask(__name__, template_folder='web', static_folder='web/static', static_url_path='/static')

STATS_FOLDER = os.path.join(app.static_folder, 'stats')

# File di log per i messaggi originali
LOG_FILE = "/app/output/data/helium_data_msg.txt"

# Nome del file CSV
CSV_FILE = "/app/output/data/helium_gateway_data.csv"

# Definizione dell'header del CSV
CSV_HEADER = ["gwTime", "gatewayId", "gateway_name", "gateway_id", 
              "node_long", "node_lat", "gateway_long", "gateway_lat", 
              "dist_km", "rssi", "snr", "visibility"]

IGRA_LINKS_JSON = "/app/output/igra-datas/map_links.json"

JSON_INDEX = "/app/output/data/gateways_index.json.gz"

LOG_FILE = "/app/output/app.log"

csv_lock = threading.Lock()
index_lock = threading.Lock()

# ----------------------------------------------------------------------------
# **POSIZIONE DEL NODO (Da impostare manualmente)**
# posizione del logger installato sul GGH (45.70377, 13.72040)
# NODE_LAT = 45.70377         # Sostituisci con la latitudine reale del nodo
# NODE_LONG = 13.72040        # Sostituisci con la longitudine reale del nodo
# posizione di test del 04/03/2025
# NODE_LAT = 45.70445       # Sostituisci con la latitudine reale del nodo
# NODE_LONG = 13.71931      # Sostituisci con la longitudine reale del nodo
# ----------------------------------------------------------------------------

# Creazione del file CSV se non esiste
os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode='x', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(CSV_HEADER)  # Scrive l'intestazione del file CSV

# Funzione per calcolare la distanza tra nodo e gateway
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Raggio della Terra in km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c  # Distanza in km

# Route pour test localtunnel
@app.route("/")
def home():
    return "<html><body>OK</body></html>"

def create_index():
    """Create optimized JSON index from CSV"""
    df = pd.read_csv(CSV_FILE, parse_dates=['gwTime'])
    df['date'] = df['gwTime'].dt.strftime('%Y-%m-%d')
    
    index = {}
    for date, group in df.groupby('date'):
        index[date] = {}
        for gw_id, gw_group in group.groupby('gatewayId'):
            first = gw_group.iloc[0]
            index[date][gw_id] = {
                'name': first['gateway_name'],
                'lat': first['gateway_lat'],
                'lon': first['gateway_long'],
                'visibility': first['visibility'],
                'distance': first['dist_km'],
                'measurements': gw_group[['gwTime', 'rssi', 'snr']].apply(
                    lambda r: [r['gwTime'].strftime('%H:%M'), r['rssi'], r['snr']], 
                    axis=1
                ).tolist()
            }
    
    with open(JSON_INDEX, 'w') as f:
        json.dump(index, f, separators=(',', ':'))



@app.route('/helium-data', methods=['POST'])
def helium_webhook():
    try:
        data = request.get_json()

        # Salva il messaggio originale nel file di log
        with open(LOG_FILE, mode='a') as log_file:
            log_file.write(str(data) + "\n")

        # Stampa tutto il payload ricevuto per debugging
        log("Dati ricevuti:", data)

        # Estrai i dati dei gateway dalla lista 'rxInfo'
        rx_info_list = data.get("rxInfo", [])

        with csv_lock:
            # Apri il file CSV in modalità append per aggiungere i nuovi dati
            with open(CSV_FILE, mode='a', newline='') as file:
                writer = csv.writer(file)

                for gateway in rx_info_list:
                    # Estrai i dati richiesti con valori di default se mancano
                    gwTime = gateway.get("gwTime", "N/A")
                    gatewayId = gateway.get("gatewayId", "N/A")
                    metadata = gateway.get("metadata", {})

                    gateway_name = metadata.get("gateway_name", "N/A")
                    gateway_id = metadata.get("gateway_id", "N/A")
                    gateway_long = metadata.get("gateway_long", "N/A")
                    gateway_lat = metadata.get("gateway_lat", "N/A")
                    rssi = gateway.get("rssi", "N/A")
                    snr = gateway.get("snr", "N/A")

                    # Vérification : champs essentiels présents et valides
                    if not all([gwTime, gatewayId, gateway_name, gateway_id, gateway_lat, gateway_long]):
                        log("[IGNORED] Missing required data for gateway:", gatewayId or "Unknown")
                        continue

                    # Converti latitudine e longitudine in float per il calcolo della distanza
                    try:
                        gateway_lat = float(gateway_lat)
                        gateway_long = float(gateway_long)
                    except (ValueError, TypeError):
                        log(f"[IGNORED] Invalid coordinates for gateway {gatewayId}")
                        continue

                    # Calcola la distanza solo se tutti i valori sono validi
                    if gateway_lat is not None and gateway_long is not None:
                        dist_km = haversine(END_DEVICE_LAT, END_DEVICE_LON, gateway_lat, gateway_long)
                    else:
                        dist_km = "N/A"

                    # Scrive una riga nel CSV
                    writer.writerow([gwTime, gatewayId, gateway_name, gateway_id, 
                                    END_DEVICE_LON, END_DEVICE_LAT, gateway_long, gateway_lat, 
                                    dist_km, rssi, snr, "N/A"])
                    
        generate_optimized_json()
        return jsonify({"status": "success", "message": "Dati ricevuti e salvati in CSV"}), 200

    except Exception as e:
        log("Errore:", e)
        return jsonify({"status": "error", "message": str(e)}), 500
    

JSON_OPTIMIZED_PATH = "/app/output/data/optimized_gateways_data.json"

def generate_optimized_json():
    df = pd.read_csv(CSV_FILE, parse_dates=['gwTime'])
    df['date'] = pd.to_datetime(df['gwTime'], format='ISO8601').dt.strftime('%Y-%m-%d')
    # Nettoyage des données
    df = df.replace([np.nan, 'NaN', 'N/A'], None)
    
    # Charger les liens IGRA une seule fois
    with open(IGRA_LINKS_JSON, 'r') as f:
        igra_links = json.load(f)
    
    # Structurer les données par date → gateway
    optimized_data = {}
    for date, group in df.groupby('date'):
        optimized_data[date] = {}
        for gw_id, gw_data in group.groupby('gatewayId'):
            optimized_data[date][gw_id] = {
                'name': gw_data['gateway_name'].iloc[0],
                'lat': round(gw_data['gateway_lat'].iloc[0], 5),
                'lon': round(gw_data['gateway_long'].iloc[0], 5),
                'dist_km': round(gw_data['dist_km'].iloc[0], 2),
                'visibility': gw_data['visibility'].iloc[0],
                'measurements': gw_data[['gwTime', 'rssi', 'snr']].to_dict('records'),
                'graph_path': igra_links.get(gw_id, {}).get('graphs', {}).get(date, '').replace('./', '')
            }
    
    # Sauvegarder le fichier
    with open(JSON_OPTIMIZED_PATH, 'w') as f:
        json.dump(optimized_data, f, indent=2)

@app.route('/api/optimized_gateways')
def get_optimized_gateways():
    if not os.path.exists(JSON_OPTIMIZED_PATH):
        generate_optimized_json()
    return send_from_directory('/app/output/data', 'optimized_gateways_data.json')


# Chargement des données (peut être optimisé avec un cache)
def load_data():
    df = pd.read_csv(CSV_FILE)
    df['date'] = pd.to_datetime(df['gwTime'], format='ISO8601').dt.strftime('%Y-%m-%d')
    return df

@app.route('/api/dates')
def get_dates():
    with open(JSON_OPTIMIZED_PATH, 'r') as f:
        data = json.load(f)
    return jsonify(sorted(data.keys()))
# Route pour obtenir les dates disponibles
# @app.route('/api/dates')
# def get_dates():
#     df = load_data()
#     dates = sorted(df['date'].unique().tolist())
#     return jsonify(dates)

# Route pour obtenir les stations IGRA
@app.route('/api/igra_stations')
def get_igra_stations():
    try:
        with open(IGRA_LINKS_JSON, "r") as f:
            igra_links = json.load(f)
        
        # Extraire les stations uniques
        stations = {}
        for gateway_data in igra_links.values():
            station_id = gateway_data["station_id"]
            if station_id not in stations:
                stations[station_id] = {
                    "id": station_id,
                    "lat": gateway_data["station_coords"][0],
                    "lon": gateway_data["station_coords"][1]
                }
        
        return jsonify(list(stations.values()))
    
    except FileNotFoundError:
        return jsonify({"error": "IGRA links file not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

# Route pour obtenir les gateways d'une date spécifique
@app.route('/api/gateways')
def get_gateways():
    date = request.args.get('date')
    if not date:
        return jsonify({"error": "Date parameter is required"}), 400
    
    df = load_data()
    df_date = df[df['date'] == date]
    
    if df_date.empty:
            return jsonify({"error": "No data for this date"}), 404
        
    # Nettoyage des données
    df_date = df_date.replace([np.nan, 'NaN', 'N/A'], None)
    
    # Grouper par gateway
    grouped = df_date.groupby(["gatewayId", "date"])
    
    result = []
    for (gw_id, _), group in grouped:
        row = group.iloc[0]  # Première ligne pour les infos statiques
        
        gateway_data = {
            "gatewayId": gw_id,
            "gateway_name": row['gateway_name'],
            "lat": round(row['gateway_lat'], 5),
            "lon": round(row['gateway_long'], 5),
            "dist_km": round(row['dist_km'], 2),
            "visibility": row['visibility'],
            "measurements": [],
            "graph_path": None
        }
        
        # Ajouter les mesures
        for _, r in group.iterrows():
            gateway_data["measurements"].append({
                "gwTime": r['gwTime'],
                "rssi": r.get('rssi'),
                "snr": r.get('snr')
            })
        
        # Vérifier s'il y a un graphique IGRA
        try:
            with open(IGRA_LINKS_JSON, "r") as f:
                igra_links = json.load(f)
                graph_path = igra_links.get(gw_id, {}).get("graphs", {}).get(date)
                if graph_path:
                    gateway_data["graph_path"] = graph_path.replace("./", "")
        except FileNotFoundError:
            pass
        
        result.append(gateway_data)
    
    return jsonify(result)

@app.route('/dynamic-map')
def index():
    return render_template("dynamic_map.html")

@app.route('/api/config')
def get_config():
    return jsonify({
        "end_device_lat": END_DEVICE_LAT,
        "end_device_lon": END_DEVICE_LON,
        "zoom_level": 12
    })

@app.route('/dynamic_map.js')
def serve_map_js():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'dynamic_map.js')

@app.route("/api/era5_graph")
def get_graph():
    gateway_name = request.args.get("gateway_name")
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    date = request.args.get("date")
    time = request.args.get("time")

    if None in [gateway_name, lat, lon, date, time]:
        return jsonify({"error": "Missing parameters"}), 400


    try:
        # Lancer le script qui génère l'image
        result = subprocess.run(
            [
                "python3", "era5_gradients.py",
                "--on-demand", str(gateway_name), str(lat), str(lon), str(date), str(time)
            ],
            capture_output=True, text=True, check=True, timeout=300
        )

         # Nettoyer la sortie en prenant la dernière ligne
        output_lines = result.stdout.strip().split('\n')
        image_path = output_lines[-1]  # Prend seulement la dernière ligne (pas les print)

        image_url = image_path.replace('/app/output/era5/plots/', '/plots/')
        
        return jsonify({"image_url": image_url})

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Processing timeout"}), 504
    except subprocess.CalledProcessError as e:
        logging.error(f"Script failed: {e.stderr}")
        return jsonify({"error": f"Processing failed: {e.stderr}"}), 500
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/api/era5_daily_graph")
def get_daily_graph():
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"error": "Date parameter required"}), 400
    
    try:
        # Valider et formater la date
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%Y-%m-%d")
        
        # Construire le nom de fichier attendu
        filename = f"gradient_{formatted_date}.png"
        image_path = os.path.join("/app/output/era5/plots", filename)
        
        # Vérifier que le fichier existe
        if not os.path.exists(image_path):
            return jsonify({"error": "ERA5 graph not available for this date"}), 404
            
        # Renvoyer directement l'image
        return send_from_directory(
            directory="/app/output/era5/plots",
            path=filename,
            mimetype="image/png"
        )
        
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/map', methods=['GET'])
def map_server():
    try:
        return send_from_directory('/app/output', 'map.html')
    except FileNotFoundError:
        return jsonify({"status": "error", "message": "Map file not found"}), 404
    
@app.route('/app/output/igra-datas/derived/<path:filename>')
def serve_images(filename):
    return send_from_directory('/app/output/igra-datas/derived', filename)

@app.route('/plots/<path:filename>')
def serve_era5(filename):
    return send_from_directory('/app/output/era5/plots', filename)

@app.route('/logs', methods=['GET'])
def get_logs():
    if os.path.exists(LOG_FILE):
        return send_file(LOG_FILE, mimetype="text/plain", as_attachment=True)
    else:
        return "Log file not found", 404




@app.route('/stats', methods=['GET'])
def stats():
    images = [f for f in os.listdir(STATS_FOLDER) if f.endswith('.png')]
    
    return render_template('stats.html', images=images)


if __name__ == '__main__':
    if not os.path.exists(JSON_INDEX):
        try:
            create_index()
        except Exception as e:
            log(f"Initial index creation failed: {e}")

    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
