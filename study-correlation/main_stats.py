import subprocess
import sys
import signal


subprocesses = []

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

def main():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    try:
        p1 = subprocess.Popen(["python3", "study-correlation/igra_ducts.py"])
        subprocesses.append(p1)
        p2 = subprocess.Popen(["python3", "study-correlation/daily_stats.py"])
        subprocesses.append(p2)
        p1.wait(), p2.wait()
        p3 = subprocess.Popen(["python3", "study-correlation/merge_data.py"])
        subprocesses.append(p3)
        p3.wait()
        p4 = subprocess.Popen(["python3", "study-correlation/correlation.py"])
        subprocesses.append(p4)
    except KeyboardInterrupt:
        # Catch redondant au cas où le signal ne capte pas tout
        cleanup()

if __name__ == "__main__":
    main()