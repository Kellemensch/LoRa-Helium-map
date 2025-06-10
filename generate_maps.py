import folium
import pandas as pd

LOS_CSV = "./data/helium_gateway_data.csv"
END_DEVICE_LAT = 45.7038
END_DEVICE_LON = 13.7204


df = pd.read_csv(LOS_CSV)
map_center = [END_DEVICE_LAT, END_DEVICE_LON]

m = folium.Map(location=map_center, zoom_start=12)

# Ajouter l'end device
folium.Marker(
    location=map_center,
    icon=folium.Icon(color="blue"),
    tooltip="End Device"
).add_to(m)

# Panneau latéral vide (sera rempli via JS)
html = """
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

<script>
function showSidebar(content) {
    document.getElementById("info-content").innerHTML = content;
    document.getElementById("sidebar").style.display = "block";
}
</script>
"""
m.get_root().html.add_child(folium.Element(html))


# Grouper les données par Gateway ID
grouped = df.groupby("gatewayId")

for gw_id, group in grouped:
    # On prend la première ligne comme représentative pour les coordonnées
    first = group.iloc[0]
    color = "green" if first["visibility"] == "LOS" else "red"
    lat = first["gateway_lat"]
    lon = first["gateway_long"]  # remettre la vraie longitude
    dist = first["dist_km"]

    # Générer le bloc d'infos HTML avec les différentes dates
    info_html = f"""
    <b>Gateway Name:</b> {first['gateway_name']}<br>
    <b>Gateway ID:</b> {gw_id}<br>
    <b>Latitude:</b> {lat}<br>
    <b>Longitude:</b> {lon}<br>
    <b>Distance:</b> {dist} km<br>
    <b>Visibility:</b> {first['visibility']}<br>
    <hr>
    <b>Measurements:</b><br>
    <ul>
    """
    for _, row in group.sort_values("gwTime").iterrows():
        try:
            raw_date = pd.to_datetime(row["gwTime"])
            readable_date = raw_date.strftime("%d %B %Y at %H:%M")  # ex : 06 june 2025 at 13:41
        except Exception:
            readable_date = "Invalid date"
        
        rssi = row.get("rssi", "N/A")
        snr = row.get("snr", "N/A")
        info_html += f"<li><b>{readable_date}</b>: RSSI = {rssi}, SNR = {snr}</li>"


    # Ajout du point cliquable (cercle)
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

    # Ajout du marqueur interactif (JS pour sidebar)
    folium.Marker(
        location=[lat, lon],
        icon=folium.DivIcon(html=f"""
            <div onclick="showSidebar(`{info_html}`)" style="width:12px;height:12px;border-radius:6px;background:{color};cursor:pointer;"></div>
        """)
    ).add_to(m)

    # Trait vers le end device
    folium.PolyLine(
        locations=[[lat, lon], map_center],
        color=color,
        weight=2,
        opacity=0.6
    ).add_to(m)


# Sauvegarde
m.save("map.html")
print("Map saved in map.html !")