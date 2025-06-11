#!/bin/bash

install_python() {
    echo "Installing Python 3..."
    if command -v apt &> /dev/null; then
        sudo apt update
        sudo apt install -y python3
    fi
}

install_splat() {
    echo "Installing Splat!..."
    if command -v apt &> /dev/null; then
        sudo apt update
        sudo apt install -y build-essential gfortran libpng-dev wget unzip

        # Create a directory for source code
        mkdir -p ~/splat_install
        cd ~/splat_install

        # Download Splat! source code
        echo "Downloading Splat!..."
        wget 'https://www.qsl.net/kd2bd/splat-1.4.2.tar.bz2'

        # Extract and build
        echo "Extracting..."
        cd /usr/src
        sudo tar xvjf ~/splat_install/splat-1.4.2.tar.bz2 -C .
        cd splat-1.4.2

        echo "Building Splat!..."
        sudo ./configure

        # Cleanup
        cd ~
        rm -rf ~/splat_install

        echo "Splat! installation complete."
    fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "This script needs to be launched with 'source' :"
    echo "   source $0"
    exit 1
fi

echo "Initialisation..."

# Vérifie que Python est installé
if ! command -v python3 &> /dev/null
then
    echo "Python 3 is not installed."
    read -p "Do you want to install Python 3 now? (y/n): " choice
    case "$choice" in 
        y|Y ) install_python ;;
        * ) echo "Python 3 is required. Exiting." ; exit 1 ;;
    esac
fi

echo "Installing localtunnel..."
sudo apt install npm
sudo npm install -g localtunnel

# Création du venv
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Installation des dépendances Python
echo "Installing dependencies..."
pip install -r ./requirements.txt

# Vérification SPLAT
if ! command -v splat &> /dev/null
then
    echo " SPLAT! is not installed."
    read -p "Do you want to install Splat! ? (y/n): " choice
    case "$choice" in 
        y|Y ) install_splat ;;
        * ) echo "Splat! is required. Exiting." ; exit 1 ;;
    esac
else
    echo "SPLAT! is installed."
fi

# Installation de l'outil srtm2sdf
echo "Installing gnuplot"
sudo apt install gnuplot
# 
if ! command -v srtm2sdf &> /dev/null
then
    echo "Installing srtm2sdf util"
    sudo /usr/src/splat-1.4.2/utils/install srtm2sdf
else
    echo "srtm2sdf util is installed."
fi


echo "✅ Setup finished. Launch the project with:"
echo "      python3 main.py"
# source venv/bin/activate
