import subprocess
import schedule
import time

def run_all():
    subprocess.Popen(["bash", "run_localtunnel.sh"])
    time.sleep(2)
    subprocess.Popen(["python3", "webhook_server.py"])
    # subprocess.run(["python3", "generate_maps.py"])

# Lancer une fois ou régulièrement :
run_all()
# schedule.every(1).hour.do(run_all)