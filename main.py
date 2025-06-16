import subprocess
import schedule
import time
import signal
import sys
import argparse

LOCALTUNNEL = "run_localtunnel.sh"
WEBHOOK = "webhook_server.py"
SPLAT = "run_splat.py"
MAP_GENERATION = "generate_maps.py"
IGRA = "calculate_igra.py"

# Définir l'argument --logs
parser = argparse.ArgumentParser(description="Logs option")
parser.add_argument("--logs", action="store_true", help="Activate logs")
args = parser.parse_args()

subprocesses = []
with open("configs/.subdomain", "r") as f:
    subdomain = f.readline()

def run_all():
    if args.logs:
        p = subprocess.Popen(["bash", LOCALTUNNEL, subdomain, "--logs"])
    else:
        p = subprocess.Popen(["bash", LOCALTUNNEL, subdomain])
    subprocesses.append(p)
    time.sleep(2)
    if args.logs:
        p2 = subprocess.Popen(["python3", WEBHOOK, "--logs"])
    else:
        p2 = subprocess.Popen(["python3", WEBHOOK])
    subprocesses.append(p2)

    run_igra()
    run_map()
    

def run_map():
    print("(Re)running SPLAT calculation and map generation on new data...")
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
    print("Running calculate_igra on data...")
    if args.logs:
        p5 = subprocess.Popen(["python3", IGRA, "--logs"])
    else:
        p5 = subprocess.Popen(["python3", IGRA])
    subprocesses.append(p5)
    p5.wait()

def cleanup(signum=None, frame=None):
    print("Stopping all subprocesses...")
    for p in subprocesses:
        if p.poll() is None:  # Si le process est encore actif
            try:
                p.terminate()  # Envoie SIGTERM
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"Process {p.pid} does not respond, we kill it.")
                p.kill()  # Envoie SIGKILL
    sys.exit(0)

# Enregistre les signaux (Ctrl+C et autres terminaisons)
signal.signal(signal.SIGINT, cleanup)   # Ctrl+C
signal.signal(signal.SIGTERM, cleanup)  # kill ou shutdown

try:
    run_all()

    # Lance le calcul splat et la génération de map toutes les 5 minutes
    schedule.every(5).minutes.do(run_map)

    # Lance le calcul des stations IGRA 2 fois par jour
    schedule.every(12).hours.do(run_igra)

    while True:
        schedule.run_pending()
        time.sleep(1)

except KeyboardInterrupt:
    # Catch redondant au cas où le signal ne capte pas tout
    cleanup()
