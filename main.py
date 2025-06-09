import subprocess
import schedule
import time
import signal
import sys

subprocesses = []

def run_all():
    p = subprocess.Popen(["bash", "run_localtunnel.sh"])
    subprocesses.append(p)
    time.sleep(2)
    p2 = subprocess.Popen(["python3", "webhook_server.py"])
    subprocesses.append(p2)

    run_map()
    

def run_map():
    print("(Re)running SPLAT calculation and map generation on new data...")
    p3 = subprocess.Popen(["python3", "run_splat.py"])
    p3.wait()
    p4 = subprocess.Popen(["python3","generate_maps.py"])
    subprocesses.append(p4)


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

    while True:
        schedule.run_pending()
        time.sleep(1)

except KeyboardInterrupt:
    # Catch redondant au cas où le signal ne capte pas tout
    cleanup()
