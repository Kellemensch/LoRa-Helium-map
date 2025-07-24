// Configuration (sera rempli dynamiquement)
let MAP_CONFIG = {
    center: null, // Valeurs par défaut temporaires
    zoom: 12
};

// Variables globales
let map;
let currentDateIndex = 0;
let allDates = [];
let currentLayer = null;
let allGatewayData = {}; // Nouveau cache global pour toutes les données

// Fonction pour charger la configuration depuis le serveur
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        if (!response.ok) throw new Error('Network response was not ok');
        
        const config = await response.json();
        
        // Validation des données
        if (typeof config.end_device_lat !== 'number' || 
            typeof config.end_device_lon !== 'number') {
            throw new Error('Invalid coordinates format');
        }
        
        return config;
    } catch (error) {
        console.error("Error loading configuration:", error);
        // Valeurs par défaut de secours
        return {
            end_device_lat: 48.8566,  // Paris par défaut
            end_device_lon: 2.3522,   // Paris par défaut
            zoom_level: 12
        };
    }
}

// Initialisation de la carte
async function initMap() {
    // D'abord récupérer la configuration
    const config = await loadConfig();

    // Mettre à jour la configuration
    MAP_CONFIG.center = [config.end_device_lat, config.end_device_lon];
    MAP_CONFIG.zoom = config.zoom_level;
    
    console.log("Initializing map with center:", MAP_CONFIG.center);
    
    // Puis initialiser la carte avec la configuration
    map = L.map('map').setView(MAP_CONFIG.center, MAP_CONFIG.zoom);
    
    // Ajout du fond de carte
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    
    // Ajout de l'end device (toujours visible)
    L.marker(MAP_CONFIG.center, {
        icon: L.divIcon({
            html: `<svg viewBox="0 0 24 24" style="width:24px;height:24px;color:#3498db">
                    <path fill="currentColor" d="M12,2C8.13,2,5,5.13,5,9c0,5.25,7,13,7,13s7-7.75,7-13C19,5.13,15.87,2,12,2z"/>
                </svg>`,
            iconSize: [24, 24],
            className: 'end-node-icon'
        }),
        title: "End Device",
        zIndexOffset: 1000
    }).addTo(map);
    
    // Charger TOUTES les données en une seule requête
    try {
        const response = await fetch('/api/optimized_gateways');
        allGatewayData = await response.json();
        allDates = Object.keys(allGatewayData).sort();
        
        // Afficher la première date
        if (allDates.length > 0) {
            updateDateControls();
            loadDateData(allDates[0]);
        }
    } catch (error) {
        console.error('Error loading optimized data:', error);
    }
    
    // Chargement des stations IGRA (toujours visibles)
    fetch('/api/igra_stations')
        .then(response => response.json())
        .then(stations => {
            stations.forEach(station => {
                L.circleMarker([station.lat, station.lon], {
                    radius: 5,
                    color: "purple",
                    fillColor: "purple",
                    fillOpacity: 0.8,
                    title: `IGRA station ${station.id}`
                }).addTo(map);
            });
        })
        .catch(error => console.error('Error loading IGRA stations:', error));
}

// Nouvelle version optimisée de loadDateData
function loadDateData(date) {
    // Supprimer le layer précédent s'il existe
    if (currentLayer) {
        map.removeLayer(currentLayer);
    }
    
    // Créer un nouveau layer group
    currentLayer = L.layerGroup().addTo(map);
    
    // Afficher la date en cours
    document.getElementById('currentDate').textContent = date;
    
    // Récupérer les données depuis le cache
    const dateData = allGatewayData[date];
    if (!dateData) return;
    
    // Traiter chaque gateway
    for (const [gw_id, gw] of Object.entries(dateData)) {
        const color = gw.visibility === "LOS" ? "green" : "red";
        const gwLocation = [gw.lat, gw.lon];
        
        // Créer le contenu HTML pour le popup
        let infoHtml = `
            <b>Gateway Name:</b> ${gw.name}<br>
            <b>Gateway ID:</b> ${gw_id}<br>
            <b>Latitude:</b> ${gw.lat.toFixed(5)}<br>
            <b>Longitude:</b> ${gw.lon.toFixed(5)}<br>
            <b>Distance:</b> ${gw.dist_km.toFixed(2)} km<br>
            <b>Visibility:</b> ${gw.visibility}<br>
            <hr><b>Measurements for ${date}:</b><br>
        `;
        
        // Ajouter les mesures
        gw.measurements.forEach(m => {
            const time = new Date(m.gwTime).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            infoHtml += `<b>- ${time} :</b> RSSI=${m.rssi || 'N/A'}, SNR=${m.snr !== null ? m.snr : 'N/A'}<br>`;
        });
        
        // Ajouter le bouton IGRA si disponible
        if (gw.graph_path) {
            infoHtml += `
                <br><button onclick="window.open('${gw.graph_path}', '_blank', 'width=700,height=800')">
                    See IGRA graph of this day
                </button>
            `;
        } else if (color === "red") {
            infoHtml += `
                <br><span style="color:red;"><i>Graph not available yet. Waiting for updated IGRA station data to generate it.</i></span>
            `;
        }
        
        // Marqueur principal (visible)
        L.circleMarker(gwLocation, {
            radius: 6,
            color: color,
            fillColor: color,
            fillOpacity: 0.8,
            title: `${gw.name} - ${date}`
        }).addTo(currentLayer);
        
        // Marqueur cliquable (simplifié)
        L.circleMarker(gwLocation, {
            radius: 8,
            color: color,
            fillColor: color,
            fillOpacity: 0.8,
            weight: 2,
            className: 'gateway-marker'
        }).on('click', () => {
            document.getElementById('info-content').innerHTML = infoHtml;
            document.getElementById('sidebar').style.display = 'block';
        }).addTo(currentLayer);
        
        // Ligne vers l'end device
        L.polyline([gwLocation, MAP_CONFIG.center], {
            color: color,
            weight: 1.5,
            opacity: 0.7
        }).addTo(currentLayer);
    }
}

// Mise à jour des contrôles de date (inchangée)
function updateDateControls() {
    const slider = document.getElementById('dateSlider');
    slider.max = allDates.length - 1;
    slider.value = currentDateIndex;
    
    if (allDates.length > 0) {
        document.getElementById('currentDate').textContent = allDates[currentDateIndex];
    } else {
        document.getElementById('currentDate').textContent = "No dates available";
    }
}

// Gestion des événements (adaptée pour utiliser le cache)
document.addEventListener('DOMContentLoaded', async () => {
    await initMap();
    
    // Boutons de navigation
    document.getElementById('prevDate').addEventListener('click', () => {
        if (allDates.length > 0) {
            currentDateIndex = Math.max(0, currentDateIndex - 1);
            updateDateControls();
            loadDateData(allDates[currentDateIndex]);
        }
    });
    
    document.getElementById('nextDate').addEventListener('click', () => {
        if (allDates.length > 0) {
            currentDateIndex = Math.min(allDates.length - 1, currentDateIndex + 1);
            updateDateControls();
            loadDateData(allDates[currentDateIndex]);
        }
    });
    
    document.getElementById('dateSlider').addEventListener('input', (e) => {
        currentDateIndex = parseInt(e.target.value);
        updateDateControls();
        loadDateData(allDates[currentDateIndex]);
    });
});