import folium
import pandas as pd

LOS_CSV = "splat-runs/results/los_results.csv"
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


for _, row in df.iterrows():
    color = "green" if row["Visibility"] == "LOS" else "red"
    lat = row["Latitude"]
    lon = 360 - row["Longitude"]  # on remet la vraie longitude

    info_html = f"""
    <b>Gateway Name:</b> {row['Name']}<br>
    <b>Gateway ID:</b> {row['Gateway ID']}<br>
    <b>Latitude:</b> {lat}<br>
    <b>Longitude:</b> {lon}<br>
    <b>Visibility:</b> {row['Visibility']}<br>
    """

    # Ajout du point cliquable
    folium.CircleMarker(
        location=[lat, lon],
        radius=6,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.8,
        tooltip=row["Name"],
        popup=folium.Popup("Click for more info", max_width=150),
    ).add_to(m)

    # Ajout du script JS d'interaction
    folium.Marker(
        location=[lat, lon],
        icon=folium.DivIcon(html=f"""
            <div onclick="showSidebar(`{info_html}`)" style="width:12px;height:12px;border-radius:6px;background:{color};cursor:pointer;"></div>
        """)
    ).add_to(m)

    # Ligne vers l'end device
    folium.PolyLine(
        locations=[[lat, lon], map_center],
        color=color,
        weight=2,
        opacity=0.6
    ).add_to(m)

# Sauvegarde
m.save("map.html")