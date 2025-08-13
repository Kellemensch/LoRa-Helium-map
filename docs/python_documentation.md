# Portable python version Documentation

The portable python version is the precursor to the next version made in Docker [here](README_docker.md).

A Python toolkit to retrieve real-time datas from a LoRaWan end-node connected to the Helium network and to process IGRA v2 radiosonde data, compute atmospheric refractivity gradients, and visualize potential tropospheric ducts.

## Features

Here are the features it contains:

* Retrieve packets information and gateways received from the end-node
* Compute [Splat!](https://www.qsl.net/kd2bd/splat.pdf) terrain point-to-point analysis to detect LOS/NLOS
* Find the nearest [IGRA radiosonde](https://www.ncei.noaa.gov/products/weather-balloon/integrated-global-radiosonde-archive) from the gateway <-> end-node link's midpoint.
* Parse raw IGRA v2 data files (multi-level radiosonde observations)
* Compute refractivity (N) and its vertical gradient (ΔN/Δh)
* Detect tropospheric ducts
* Generate vertical gradient graphs in PNG format
* Generate an interactive map showing all the gateways receiving the packets with their corresponding graphs

---

## Repository Structure

```bash
/data/                      # Contains data retrieved from Helium
├──  terrain/               # QTH files for SPLAT
├──  helium_data_msg.txt
└──  helium_gateway_data.csv
/igra-datas/                # Contains IGRA downloaded data and builded information for map
├── derived/                # Contains refractivity graphs from derived measurements
├── igra2-station-list.txt
└── map_links.json
/maps/                      # Contains .sdf and .hgt files for SPLAT's map
/splat-runs/                # Contains .txt report files from SPLAT
├── img/                    # Contains terrain profiles and LOS between end-node and gateways
└── EndNode-to-gatewayName.txt
/venv/                      # Python's virtual environment containing dependencies
calculate_igra.py
convert_hgt_to_sdf.sh
generate_maps.py
main.py
map.html
README.md
requirements.txt
run_localtunnel.sh
run_splat.py
setup.sh
webhook_server.py
```