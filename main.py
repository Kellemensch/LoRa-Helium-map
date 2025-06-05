import subprocess
import schedule
import time

def run_all():
    subprocess.run(["python3", "webhook_server.py"])
    subprocess.run(["bash", "run_localtunnel.sh"])
    subprocess.run(["python3", "generate_maps.py"])

# Lancer une fois ou régulièrement :
run_all()
# schedule.every(1).hour.do(run_all)