import subprocess
import schedule
import time
import signal
import sys
import argparse
import os

SPLAT = "run_splat.py"
MAP_GENERATION = "generate_maps.py"
IGRA = "calculate_igra.py"
DOWNLOAD_TERRAIN = "download_terrain.py"
CONVERT_HGT = "convert_hgt_to_sdf.sh"
STATS = "study-correlation/main_stats.py"
ERA5 = "era5_gradients.py"

# Définir l'argument --logs
parser = argparse.ArgumentParser(description="Logs option")
parser.add_argument("--logs", action="store_true", help="Activate logs")
args = parser.parse_args()

subprocesses = []
with open("configs/.subdomain", "r") as f:
    subdomain = f.readline()

def run_all():
    run_terrain()

    run_igra()
    run_era5()
    run_map()
    
def run_terrain():
    p0 = subprocess.Popen(["python3", "-u", DOWNLOAD_TERRAIN])
    subprocesses.append(p0)
    p0.wait()
    p00 = subprocess.Popen(["bash", "-u", CONVERT_HGT])
    subprocesses.append(p00)
    p00.wait()

def run_map():
    if args.logs:
        p3 = subprocess.Popen(["python3", SPLAT, "--logs"])
    else:
        p3 = subprocess.Popen(["python3", SPLAT])
    p3.wait()
    if args.logs:
        p4 = subprocess.Popen(["python3", MAP_GENERATION, "--logs"])
    else:
        p4 = subprocess.Popen(["python3", MAP_GENERATION])
    subprocesses.append(p4)

def run_igra():
    if args.logs:
        p5 = subprocess.Popen(["python3", IGRA, "--logs"])
    else:
        p5 = subprocess.Popen(["python3", IGRA])
    subprocesses.append(p5)
    p5.wait()

def run_era5():
    p6 = subprocess.Popen(["python3", "-u", ERA5])
    subprocesses.append(p6)

def run_stats():
    p6 = subprocess.Popen(["python3", STATS])
    subprocesses.append(p6)

def cleanup(signum=None, frame=None):
    for p in subprocesses:
        if p.poll() is None:  # Si le process est encore actif
            try:
                p.terminate()  # Envoie SIGTERM
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"Process {p.pid} does not respond, we kill it.")
                p.kill()  # Envoie SIGKILL
    sys.exit(0)

def fix_output_ownership():
    uid = os.environ.get("HOST_UID")
    gid = os.environ.get("HOST_GID")
    if uid and gid:
        subprocess.run(["chown", "-R", f"{uid}:{gid}", "output"])


# Enregistre les signaux (Ctrl+C et autres terminaisons)
signal.signal(signal.SIGINT, cleanup)   # Ctrl+C
signal.signal(signal.SIGTERM, cleanup)  # kill ou shutdown

try:
    run_all()
    fix_output_ownership()

    run_stats()

    # Lance le calcul splat et la génération de map toutes les 5 minutes
    schedule.every(5).minutes.do(run_map)

    # Lance le calcul des stations IGRA 2 fois par jour
    schedule.every(12).hours.do(run_igra)

    # Lance les statistiques une fois par jour
    schedule.every(24).hours.do(run_stats)
    schedule.every(24).hours.do(run_era5)

    while True:
        schedule.run_pending()
        time.sleep(1)

except KeyboardInterrupt:
    # Catch redondant au cas où le signal ne capte pas tout
    cleanup()
