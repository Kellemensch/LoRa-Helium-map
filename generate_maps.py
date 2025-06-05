import folium
import pandas as pd

df = pd.read_csv("data/packets.csv")
map_center = [lat_end_device, lon_end_device]

m = folium.Map(location=map_center, zoom_start=12)

for _, row in df.iterrows():
    color = "green" if row["reachable"] else "red"
    folium.CircleMarker(
        location=[row["gw_lat"], row["gw_lon"]],
        radius=6,
        color=color,
        fill=True,
        tooltip=row["gateway_id"]
    ).add_to(m)

folium.Marker(location=map_center, icon=folium.Icon(color="blue"), tooltip="End Device").add_to(m)

m.save("maps/output_map.html")