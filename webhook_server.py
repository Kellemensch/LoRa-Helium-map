# lettura dati ricevuti via http applicazione test_Grove_Wio_E5 attraverso https://console.helium-iot.xyz/front/
# Viene usata la porta 5000
# Creazione di un file csv con i dati
# Versione che calcola la distanza del nodo dal gateway e lo inserisce nel csv

# Author : Marco Rainone

import csv
import os
import math
from flask import Flask, request, jsonify
import argparse
from configs.config_coords import END_DEVICE_LAT, END_DEVICE_LON

parser = argparse.ArgumentParser()
parser.add_argument("--logs", action="store_true")
args = parser.parse_args()

def log(*messages):
    if args.logs:
        print("[LOG]", *messages)

app = Flask(__name__)

# File di log per i messaggi originali
LOG_FILE = "/app/output/data/helium_data_msg.txt"

# Nome del file CSV
CSV_FILE = "/app/output/data/helium_gateway_data.csv"

# Definizione dell'header del CSV
CSV_HEADER = ["gwTime", "gatewayId", "gateway_name", "gateway_id", 
              "node_long", "node_lat", "gateway_long", "gateway_lat", 
              "dist_km", "rssi", "snr", "visibility"]

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
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode='w', newline='') as file:
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
