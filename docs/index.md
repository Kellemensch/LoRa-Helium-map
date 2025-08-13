# Lora-Helium-Map Documentation

For full project detail visit the [GitHub page](https://github.com/Kellemensch/LoRa-Helium-map).

## Project overview

LoRa-Helium-Map is a Python toolkit to retrieve real-time data from a LoRaWAN end-node connected to the Helium Network, process radiosonde observations (IGRA v2 or ERA5), compute atmospheric refractivity gradients, visualize potential tropospheric ducts, and make statistics.

This project is a continuation of the previous project done by [Abdus Salam International Centre for Theoretical Physics](https://www.ictp.it) (ICTP) researchers Pr. Marco Zennaro, Pr. Ermanno Pietrosemoli and Pr. Marco Rainone.  
See their paper [here](https://arxiv.org/pdf/2004.02802).

It was also based on their project _TAT.py: Tropospheric Analysis Tools in Python_.
See their paper [here](https://ieeexplore.ieee.org/document/9606437).

This project is built on the [Helium Network](https://www.helium.com/), a global decentralized LoRaWAN infrastructure. After initial testing with [The Things Network](https://www.thethingsnetwork.org/) (TTN), Helium was chosen due to its significantly larger community and higher density of gateways, which improves the chances of capturing and analyzing signals over long distances.  
This broader coverage is particularly important to our research focus: studying abnormal radio wave propagation in the troposphere, a phenomenon that can extend communication ranges far beyond normal line-of-sight limits.

The motivation behind this work is to better understand how environmental conditions in the lower atmosphere influence long-range wireless communications.  
While LoRaWAN networks are typically designed for predictable line-of-sight coverage, rare tropospheric phenomena—such as ducting—can create unexpected, extended communication links.  
By systematically collecting and correlating real-world network data with atmospheric measurements, this project aims to identify, quantify, and visualize these events.  
The resulting insights could help refine radio propagation models, assist network planners in optimizing infrastructure, and contribute to the broader scientific study of atmospheric effects on wireless technologies.

---

## Latest release

You can find the documentation of the latest release for this project [here](docker_documentation.md).