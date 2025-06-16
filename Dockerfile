FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Installer tout ce qu'il faut dans l'image
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv \
    build-essential gfortran libpng-dev wget unzip \
    gnuplot nodejs npm curl tar bzip2 \
 && npm install -g localtunnel \
 && rm -rf /var/lib/apt/lists/*

# Installer SPLAT sans interaction
RUN mkdir -p /usr/src/splat && cd /usr/src/splat && \
    wget 'https://www.qsl.net/kd2bd/splat-1.4.2.tar.bz2' && \
    tar xvjf splat-1.4.2.tar.bz2 && cd splat-1.4.2 && \
    printf "4\n4\n4\n" | ./configure && \
    ./utils/install srtm2sdf


# Définir le dossier de travail
WORKDIR /app

# Copier le code du projet
COPY . /app

# Donner les permissions d’exécution aux scripts
RUN chmod +x docker-entrypoint.sh

# Créer venv + installer requirements
RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Exposer le port du webhook
EXPOSE 5000

# Script d’entrée
ENTRYPOINT ["./docker-entrypoint.sh"]
