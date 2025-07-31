---

layout: default
title: LoRa-Helium-Map
----------------------

# 🌐 LoRa-Helium-Map

Welcome to the official documentation and showcase page for **LoRa-Helium-Map**.

This project provides a complete toolkit to:

* Collect real-time LoRaWAN packets from the [Helium Network](https://www.helium.com/)
* Match them with atmospheric data from radiosondes (IGRA or ERA5)
* Compute refractivity gradients
* Detect tropospheric ducts
* Visualize everything with graphs and interactive maps

---

## Versions Overview

We provide **two versions** of the project, both fully maintained:

| Version           | Description                                     | Link                                                                                    |
| ----------------- | ----------------------------------------------- | --------------------------------------------------------------------------------------- |
| Classic Python | Manual execution using Python scripts           | [View on GitHub](https://github.com/Kellemensch/LoRa-Helium-map)                        |
| Docker | Fully containerized version for easy deployment | [Guide](./README_docker.md) |

You can browse each version’s releases and documentation using the links above.

---

## Features at a Glance

Real-time gateway + packet data from Helium
Automatic matching with radiosonde (IGRA/ERA5)
Refractivity gradient (ΔN/Δh) computation
Tropospheric duct detection
Interactive map rendering with SPLAT! data
Graphical outputs in PNG

---

## Screenshots

### Interactive Coverage Map

![Interactive map](./examples/example_map.png)

### Vertical Refractivity Gradient Graph

![Refractivity graph](./examples/example_gradient.png)

---

## Project Repository

Visit the GitHub repository to explore the code, issues, discussions, and contribute:

[github.com/Kellemensch/LoRa-Helium-map](https://github.com/Kellemensch/LoRa-Helium-map)

---

## How to Use

Refer to the [README](./README.md) for full installation, usage, and structure instructions for both versions.

If you prefer Docker:

```bash
bash run.sh
```

Or use the classic Python version:

```bash
bash setup.sh
python3 main.py
```

---

## Live Demos *(Optional)*

> Coming soon: GitHub Pages integration for interactive examples (map previews, graph gallery).

---

## License

Licensed under the MIT License.

---

Made with ❤️ by [Kellemensch](https://github.com/Kellemensch)
