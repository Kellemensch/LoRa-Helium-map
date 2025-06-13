import folium
import pandas as pd
import argparse
import json
import html
from configs.config_coords import END_DEVICE_LAT, END_DEVICE_LON

# === Paramètres ===
LOS_CSV = "./data/helium_gateway_data.csv"
IGRA_LINKS_JSON = "./igra-datas/map_links.json"

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

# === Création de la carte ===
m = folium.Map(location=map_center, zoom_start=12)

# End device
folium.Marker(
    location=map_center,
    icon=folium.Icon(color="blue"),
    tooltip="End Device"
).add_to(m)

# === HTML pour panneau latéral ===
sidebar_html = """
<div id="sidebar" style="
    position: absolute;
    top: 50px;
    right: 0;
    width: 300px;
    height: 90%;
    background-color: white;
    z-index: 1000;
    overflow-y: auto;
    padding: 10px;
    box-shadow: -2px 0 5px rgba(0,0,0,0.4);
    display: none;
">
    <h4>Information</h4>
    <div id="info-content">Click on a point</div>
</div>
"""
m.get_root().html.add_child(folium.Element(sidebar_html))

# === Script JS (panneau + ligne) ===
script = """
<script>
function showSidebar(content) {
    document.getElementById("info-content").innerHTML = content;
    document.getElementById("sidebar").style.display = "block";
}

function openModalWithImage(imgPath) {
    window.open(imgPath, '_blank', 'width=700,height=800');
}
</script>
"""
m.get_root().header.add_child(folium.Element(script))

# === Affichage des stations IGRA ===
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
        color="blue",
        fill=True,
        fill_color="blue",
        fill_opacity=0.8,
        tooltip=f"IGRA station {st_id}"
    ).add_to(m)

# === Affichage des gateways ===
grouped = df.groupby("gatewayId")
for gw_id, group in grouped:
    first = group.iloc[0]
    color = "green" if first["visibility"] == "LOS" else "red"
    lat = first["gateway_lat"]
    lon = first["gateway_long"]
    dist = first["dist_km"]

    info_html = f"""
    <b>Gateway Name:</b> {first['gateway_name']}<br>
    <b>Gateway ID:</b> {gw_id}<br>
    <b>Latitude:</b> {lat}<br>
    <b>Longitude:</b> {lon}<br>
    <b>Distance:</b> {dist} km<br>
    <b>Visibility:</b> {first['visibility']}<br>
    <hr><b>Measurements:</b><br><ul>
    """

    js_call = ""
    gw_graphs = igra_links.get(gw_id, {}).get("graphs", {})
    st_coords = igra_links.get(gw_id, {}).get("station_coords")

    for _, row in group.sort_values("gwTime").iterrows():
        try:
            raw_date = pd.to_datetime(row["gwTime"])
            readable_date = raw_date.strftime("%d %B %Y at %H:%M")
            graph_key = raw_date.strftime("%Y-%m-%d")
        except Exception:
            readable_date = "Invalid date"
            graph_key = None

        rssi = row.get("rssi", "N/A")
        snr = row.get("snr", "N/A")
        info_html += f"<li><b>{readable_date}</b>: RSSI = {rssi}, SNR = {snr}"

        if graph_key and graph_key in gw_graphs:
            graph_path = gw_graphs[graph_key].replace("./", "")
            info_html += f"""
            <br><button onclick=\"openModalWithImage('{graph_path}')\">
                See IGRA graph of this day
            </button>
            """

        info_html += "</li>"
    info_html += "</ul>"

    # Injection JS et ajout sur la carte
    safe_html = escape_js(info_html)
    full_js = f"showSidebar(`{safe_html}`);{js_call}"

    folium.CircleMarker(
        location=[lat, lon],
        radius=6,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.8,
        tooltip=first["gateway_name"],
        popup=folium.Popup("Click for more info", max_width=150),
    ).add_to(m)

    folium.Marker(
        location=[lat, lon],
        icon=folium.DivIcon(html=f"""
            <div onclick=\"{full_js}\" style=\"width:12px;height:12px;border-radius:6px;background:{color};cursor:pointer;\"></div>
        """)
    ).add_to(m)

    folium.PolyLine(
        locations=[[lat, lon], map_center],
        color=color,
        weight=2,
        opacity=0.6
    ).add_to(m)

# === Sauvegarde finale ===
m.save("map.html")
print("Map saved in map.html !")
