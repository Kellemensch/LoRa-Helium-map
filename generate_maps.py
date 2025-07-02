import folium
import pandas as pd
import argparse
import json
import html
from datetime import datetime
from configs.config_coords import END_DEVICE_LAT, END_DEVICE_LON

# === Paramètres ===
LOS_CSV = "/app/output/data/helium_gateway_data.csv"
IGRA_LINKS_JSON = "/app/output/igra-datas/map_links.json"
OUTPUT_MAP = "/app/output/map.html"

# === Argument ligne de commande ===
parser = argparse.ArgumentParser()
parser.add_argument("--logs", action="store_true")
args = parser.parse_args()

def log(*messages):
    if args.logs:
        print("[LOG]", *messages)

def escape_js(s):
    """\
    Échappe le HTML pour injection sécurisée dans un attribut onclick JS
    """
    return html.escape(s).replace("\n", "").replace("`", "\\`")

# === Chargement des données ===
df = pd.read_csv(LOS_CSV)
map_center = [END_DEVICE_LAT, END_DEVICE_LON]

# === Chargement des liens IGRA ===
try:
    with open(IGRA_LINKS_JSON, "r") as f:
        igra_links = json.load(f)
except FileNotFoundError:
    igra_links = {}
    log(f"File {IGRA_LINKS_JSON} not found. No graph will be linked")

# === Préparation des dates ===
df['date'] = pd.to_datetime(df['gwTime'], format='ISO8601').dt.strftime('%Y-%m-%d')
all_dates = sorted(df['date'].unique())



# === Création de la carte ===
m = folium.Map(location=map_center, zoom_start=12)

# === End device (toujours visible) ===
folium.Marker(
    location=map_center,
    icon=folium.Icon(color="blue"),
    tooltip="End Device"
).add_to(m)

# === Affichage des stations IGRA (toujours visibles) ===
added_stations = set()
for gw_info in igra_links.values():
    st_lat, st_lon = gw_info["station_coords"]
    st_id = gw_info["station_id"]

    if st_id in added_stations:
        continue
    added_stations.add(st_id)

    folium.CircleMarker(
        location=[st_lat, st_lon],
        radius=5,
        color="purple",
        fill=True,
        fill_color="purple",
        fill_opacity=0.8,
        tooltip=f"IGRA station {st_id}"
    ).add_to(m)

# === Dictionnaire pour stocker les FeatureGroups ===
date_groups = {}

# === Création des FeatureGroups pour chaque date ===
for date in all_dates:
    date_groups[date] = folium.FeatureGroup(name=f"Date: {date}", show=False)
    date_groups[date].add_to(m)

# === Affichage des gateways ===
# Grouper toutes les mesures par gatewayId + date
grouped = df.groupby(["gatewayId", "date"])

for (gw_id, date), group in grouped:
    row = group.iloc[0]  # Pour l'emplacement et les infos statiques
    color = "green" if row["visibility"] == "LOS" else "red"
    lat = round(row["gateway_lat"], 5)
    lon = round(row["gateway_long"], 5)

    # Construction HTML avec toutes les mesures
    info_html = f"""
    <b>Gateway Name:</b> {row['gateway_name']}<br>
    <b>Gateway ID:</b> {gw_id}<br>
    <b>Latitude:</b> {lat}<br>
    <b>Longitude:</b> {lon}<br>
    <b>Visibility:</b> {row['visibility']}<br>
    <hr><b>Measurements for {date}:</b><br>
    """

    for _, r in group.iterrows():
        info_html += f"""
        <b>- {pd.to_datetime(r['gwTime']).strftime('%H:%M')} :</b> RSSI={r.get('rssi', 'N/A')}, SNR={r.get('snr', 'N/A')}<br>
        """

    # Ajout du graphe IGRA s'il existe
    graph_path = igra_links.get(gw_id, {}).get("graphs", {}).get(date)
    if graph_path:
        graph_path = graph_path.replace("./", "")
        info_html += f"""
        <br><button onclick=\"window.open('{graph_path}', '_blank', 'width=700,height=800')\">
            See IGRA graph of this day
        </button>
        """
    else:
        if color == "red":
            info_html += """
            <br><span style="color:red;"><i>Graph not available yet. Waiting for updated IGRA station data to generate it.</i></span>
            """

    safe_html = escape_js(info_html)
    full_js = f"showSidebar(`{safe_html}`);"

    # Marqueurs + interaction
    folium.CircleMarker(
        location=[lat, lon],
        radius=6,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.8,
        tooltip=f"{row['gateway_name']} - {date}",
    ).add_to(date_groups[date])

    folium.Marker(
        location=[lat, lon],
        icon=folium.DivIcon(html=f"""
            <div onclick=\"{full_js}\" style=\"width:12px;height:12px;border-radius:6px;background:{color};cursor:pointer;\"></div>
        """)
    ).add_to(date_groups[date])

    folium.PolyLine(
        locations=[[lat, lon], map_center],
        color=color,
        weight=2,
        opacity=0.6
    ).add_to(date_groups[date])


# === Contrôle des calques (à gauche) ===
folium.LayerControl(collapsed=False, position='topleft').add_to(m)

# === HTML pour panneau latéral (à droite) ===
sidebar_html = """
<div id="sidebar" style="
    position: fixed;
    top: 10px;
    right: 10px;
    width: 300px;
    height: 90%;
    background-color: white;
    z-index: 1000;
    overflow-y: auto;
    padding: 10px;
    box-shadow: -2px 0 5px rgba(0,0,0,0.4);
">
    <button onclick="document.getElementById('sidebar').style.display='none'" 
            style="float: right; margin-bottom: 10px; background: none; border: none; font-size: 18px; cursor: pointer;">×</button>
    <h4>Gateway Information</h4>
    <div id="info-content">
        <p><i>Click on any gateway to view detailed information</i></p>
        <p><small>You can close this panel with the [×] button</small></p>
    </div>
</div>
"""
m.get_root().html.add_child(folium.Element(sidebar_html))

# HTML de la légende
legend_html = '''
    <div style="
    position: fixed; 
    bottom: 30px; left: 30px;
    max-height: 200px;
    width: 250px;
    overflow-y: auto;
    background-color: white;
    border:2px solid grey;
    z-index:9999;
    font-size:14px;
    border-radius:8px;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.3);
    padding: 10px;
    line-height: 1.5;
">
    <b>Legend</b><br>
    <i class="fa fa-info-circle fa-lg" style="color:deepskyblue;"></i> End Node<br>
    <svg width="12" height="12"><circle cx="6" cy="6" r="6" fill="green" /></svg> In Line-Of-Sight (LOS) LoRaWan Gateway<br>
    <svg width="12" height="12"><circle cx="6" cy="6" r="6" fill="red" /></svg> Not in Line-Of-Sight (NLOS) LoRaWan Gateway<br>
    <svg width="12" height="12"><circle cx="6" cy="6" r="6" fill="grey" /></svg> LoRaWan Gateway not receiving the end-node<br>
    <svg width="12" height="12"><circle cx="6" cy="6" r="6" fill="purple" /></svg> <a href="https://www.ncei.noaa.gov/products/weather-balloon/integrated-global-radiosonde-archive">IGRA</a> radiosonde station
    </div>
    '''

m.get_root().html.add_child(folium.Element(legend_html))

# === Timeline améliorée avec synchronisation des checkbox ===
# === HTML pour la timeline améliorée (centrée en bas) ===
timeline_html = f"""
<div id="timeline-container" style="
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    width: 60%;
    min-width: 400px;
    max-width: 800px;
    background-color: rgba(255, 255, 255, 0.9);
    z-index: 1000;
    padding: 15px 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    border-radius: 10px;
    border: 1px solid #ddd;
">
    <h4 style="margin: 0 0 10px 0; text-align: center; color: #333;">Select a date</h4>
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
        <button id="prevDate" style="
            background: #f0f0f0;
            border: 1px solid #ccc;
            border-radius: 5px;
            padding: 5px 10px;
            cursor: pointer;
        ">&lt; Previous</button>
        
        <input type="range" id="dateSlider" min="0" max="{len(all_dates)-1}" value="0" step="1" 
               style="
                   flex-grow: 1;
                   height: 8px;
                   border-radius: 4px;
                   background: #e0e0e0;
                   outline: none;
                   -webkit-appearance: none;
               ">
        
        <button id="nextDate" style="
            background: #f0f0f0;
            border: 1px solid #ccc;
            border-radius: 5px;
            padding: 5px 10px;
            cursor: pointer;
        ">Next &gt;</button>
    </div>
    <div id="currentDate" style="
        text-align: center;
        font-weight: bold;
        font-size: 16px;
        color: #2c3e50;
        padding: 5px;
        background: #f8f9fa;
        border-radius: 5px;
        margin-top: 5px;
    ">{all_dates[0] if all_dates else "No dates available"}</div>
</div>

<style>
    /* Style amélioré pour le slider */
    #dateSlider::-webkit-slider-thumb {{
        -webkit-appearance: none;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: #3498db;
        cursor: pointer;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }}
    
    #dateSlider::-moz-range-thumb {{
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: #3498db;
        cursor: pointer;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }}
    
    #dateSlider::-webkit-slider-runnable-track {{
        height: 8px;
        background: #e0e0e0;
        border-radius: 4px;
    }}
    
    #dateSlider::-moz-range-track {{
        height: 8px;
        background: #e0e0e0;
        border-radius: 4px;
    }}
</style>
"""
m.get_root().html.add_child(folium.Element(timeline_html))


# === Script JS qui force la synchronisation ===
script = f"""
<script>
// Stocker les dates disponibles
const allDates = {json.dumps(all_dates)};
let currentDateIndex = 0;

// Fonction pour afficher le panneau latéral
function showSidebar(content) {{
    const sidebar = document.getElementById("sidebar");
    document.getElementById("info-content").innerHTML = content;
    sidebar.style.display = "block"; // S'assure qu'il reste visible
}}

// Fermer le panneau si on clique sur le bouton X
document.addEventListener("DOMContentLoaded", function() {{
    document.getElementById("sidebar").style.display = "block"; // Visible par défaut
}});

// Fonction pour forcer le changement de layer
function changeDate(dateIndex) {{
    currentDateIndex = dateIndex;
    const selectedDate = allDates[dateIndex];
    document.getElementById("currentDate").textContent = selectedDate;
    document.getElementById("dateSlider").value = dateIndex;
    
    // Trouver toutes les checkbox de layer
    const checkboxes = document.querySelectorAll('input.leaflet-control-layers-selector');
    
    // Décocher toutes les checkbox sauf celle correspondante
    checkboxes.forEach((checkbox, index) => {{
        if (index === dateIndex + 1) {{ // +1 car la première checkbox est pour le fond de carte
            if (!checkbox.checked) {{
                checkbox.click(); // Simuler un clic pour activer
            }}
        }} else {{
            if (checkbox.checked) {{
                checkbox.click(); // Simuler un clic pour désactiver
            }}
        }}
    }});
}}

// Initialisation après le chargement
document.addEventListener("DOMContentLoaded", function() {{
    // Gestion des boutons et slider
    document.getElementById("prevDate").addEventListener("click", function() {{
        changeDate(Math.max(0, currentDateIndex - 1));
    }});
    
    document.getElementById("nextDate").addEventListener("click", function() {{
        changeDate(Math.min(allDates.length - 1, currentDateIndex + 1));
    }});
    
    document.getElementById("dateSlider").addEventListener("input", function() {{
        changeDate(parseInt(this.value));
    }});
    
    // Activer la première date par défaut
    setTimeout(() => {{ changeDate(0); }}, 500); // Petit délai pour être sûr que les layers sont chargés
}});
</script>
"""
m.get_root().header.add_child(folium.Element(script))


# === Sauvegarde finale ===
m.save(OUTPUT_MAP)
print(f"Map saved in {OUTPUT_MAP} !")