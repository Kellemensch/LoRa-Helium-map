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

                    # Converti latitudine e longitudine in float per il calcolo della distanza
                    try:
                        gateway_lat = float(gateway_lat)
                        gateway_long = float(gateway_long)
                    except ValueError:
                        gateway_lat, gateway_long = None, None

                    # Calcola la distanza solo se tutti i valori sono validi
                    if gateway_lat is not None and gateway_long is not None:
                        dist_km = haversine(END_DEVICE_LAT, END_DEVICE_LON, gateway_lat, gateway_long)
                    else:
                        dist_km = "N/A"

                    # Scrive una riga nel CSV
                    writer.writerow([gwTime, gatewayId, gateway_name, gateway_id, 
                                    END_DEVICE_LON, END_DEVICE_LAT, gateway_long, gateway_lat, 
                                    dist_km, rssi, snr, "N/A"])
                    

        return jsonify({"status": "success", "message": "Dati ricevuti e salvati in CSV"}), 200

    except Exception as e:
        log("Errore:", e)
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/dynamic-map')
def index():
    return render_template('dynamic_map.html',
                         end_device_lat=END_DEVICE_LAT,
                         end_device_lon=END_DEVICE_LON)


@app.route('/get-dates')
def get_dates():
    """Renvoie les dates disponibles"""
    try:
        if not os.path.exists(JSON_INDEX):
            create_index()
        
        # Lecture du fichier compressé
        with gzip.open(JSON_INDEX, 'rt', encoding='utf-8') as f:
            index = json.load(f)
            
        return jsonify({
            'status': 'success',
            'dates': sorted(index.keys())
        })
        
    except Exception as e:
        app.logger.error(f"Error in get_dates: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Could not load dates'
        }), 500


@app.route('/get-gateways/<date>')
def get_gateways(date):
    """Renvoie les gateways pour une date donnée"""
    try:
        if not os.path.exists(JSON_INDEX):
            create_index()
        
        # Lecture du fichier compressé
        with gzip.open(JSON_INDEX, 'rt', encoding='utf-8') as f:
            index = json.load(f)
            
        if date not in index:
            return jsonify({
                'status': 'error',
                'message': 'Date not found'
            }), 404
            
        return jsonify({
            'status': 'success',
            'date': date,
            'gateways': index[date]
        })
        
    except Exception as e:
        app.logger.error(f"Error in get_gateways: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Could not load gateways'
        }), 500



@app.route('/map', methods=['GET'])
def map_server():
    try:
        return send_from_directory('/app/output', 'map.html')
    except FileNotFoundError:
        return jsonify({"status": "error", "message": "Map file not found"}), 404
    
@app.route('/app/output/igra-datas/derived/<path:filename>')
def serve_images(filename):
    return send_from_directory('/app/output/igra-datas/derived', filename)

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
