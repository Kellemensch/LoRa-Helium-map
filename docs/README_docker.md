# LoRa-Helium-Map – Installation & Configuration Guide (Docker)

## Requirements

Your computer or server must have an active internet connection to download dependencies and receive Helium network data.

### Docker installation

This application requires [Docker](https://www.docker.com/) to run in a containerized environment. It is recommended to use a Debian-based OS (such as Ubuntu), but it can also work on Windows or macOS.  
See the documentation on how to install at : https://docs.docker.com/engine/install/

[Installation for Windows](https://docs.docker.com/desktop/setup/install/windows-install/)

Or if you want a fast and automatic script which self download the proper version on your OS, see : [get-docker](https://get.docker.com/)

Once installed, test Docker by running :
```bash
docker --version
docker run --rm hello-world
```

---

### Helium network setup

To receive LoRa data, you must register your device with the [Helium](https://www.helium.com/) network.

1.  Register an account on the [console](https://console.helium-iot.xyz/front/) : this is your main console where you can see all your registered devices and applications
2.  Go to `Applications` on the left side menu
3.  Click on `Add application` and fill the name you want
3. Go to `Device Profiles` and click `Add`.
   - Enter a name.
   - Choose the correct MAC version (e.g. **1.0.3** for LoRa-E5).
   - Choose the proper Regional Parameters (e.g. **RP002-1.0.3 - EU868**).
   - Revision: **B**
   - Expected uplink interval: `360`
   - Device-status request frequency: `1`
   - RX1 Delay: `0`
   - Enable “Flush queue on activation”
   - Select the Default ADR algorithm
   - Select OTAA or ABP, depending on your device
5. Back in your Application, click `Add Device`.
   - Enter a device name
   - Provide the **DevEUI** (on your device label)
   - Use `"0000000000000000"` as the Join EUI
   - Choose the device profile you just created
6. Click `Create`
7. Now, you need to configure your LoRa module to connect to the network using AT commands (you can generate a AppKey from your device in your application on the console), please put the good EUI and AppKey :

```bash
AT+ID=DevEui,"put your EUI here"
AT+KEY=APPKEY,"put your AppKey here"
AT+DR=EU868 \\ OR 915 for USA
AT+JOIN
```
8.  Upon succes, you should see :
```bash
+JOIN: Network joined successfully
```

---

### HTTP integration in Helium Console

Now that you have registered your device on the Helium Network, you will need to create an HTTP integration in order to retrieve data with the LoRa-Helium-map application.

1. In the [Helium Console](https://console.helium-iot.xyz/front/), go to `Applications` → your app → `Integrations`.
2. Click `Add Integration`, then choose `HTTP`.
3. Set:
   - **Payload encoding**: `JSON`
   - **Endpoint URL**: your localtunnel URL, ending with `/helium-data`  
     Example: `https://yourlaboratory.loca.lt/helium-data`
   - **Headers**:
     - Key: `Content-Type`
     - Value: `application/json`
4. Click `Create Integration`

---

## Download

Download the latest version [here](https://github.com/Kellemensch/LoRa-Helium-map/releases/download/v3.0.0/lora-helium-map.zip) and unzip the package.

---

## Launch

To launch the application you must know your end-device's __latitude and longitude__ in degrees, and you __url subdomain__ (in the example above : __yourlaboratory__)

If you are on Linux, you can then launch the application by simply typing :
```bash
./run.sh
```
You will be asked to provide the latitude, longitude and subdomain.

It will then automatically download terrain files around your end-device's place and begin to retrieve data from the Helium Network.

It is recommended to leave the application running all day and night long on a running server in order to get the maximum of data.

## Results

Results can be found in the `output/` folder in your current directory.

The application writes every 5 minutes a map in `output/map.html` using the [Splat!](https://www.qsl.net/kd2bd/splat.html) tool.

It also runs twice a day (every 12 hours) an [IGRA](https://www.ncei.noaa.gov/products/weather-balloon/integrated-global-radiosonde-archive) calculation using radiosonde balloons observations. It is important to note that new data from this dataset is not necessary available everyday, so you might wait a few days before new data are available and processed by the application.

Be aware that all the dataset retrieved from you Helium end-node is stored in `output/data/helium_gateway_data.csv` and that no other version of this file does exist elsewhere. You might want to do regular saves of this file on another disk for backup (old data cannot be retrieved anymore).

Finally, you can see the resulted __map__ on your dedicated website ! It is available at the address with the subdomain you chose : *`http://subdomain.loca.lt/map`*, for example : *`http://yourlaboratory.loca.lt/map`*

Logs are available with the command : `docker logs -f lora-map`  
You can stop the application with the command : `docker compose down`

A container named `watchtower` is used to pull updates of this application from the cloud. If an update is available, the application will be restarted without destroying any file and dataset.

If the tunnel is unavailable, don't panic, it will be relaunched automatically by the application. It is probably due to localtunnel's servers, it might take some time.  
If the problem still persists, be sure that your connection to internet is authorized.

## Documentation

You can find all the documentation for the files in the [dedicated section](docker_documentation.md).