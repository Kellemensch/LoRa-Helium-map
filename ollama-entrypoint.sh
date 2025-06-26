#!/bin/bash

# Démarrer le serveur Ollama en arrière-plan
ollama serve &

# Attendre qu’il soit prêt
until curl -s http://localhost:11434 > /dev/null; do
    echo "Waiting for Ollama..."
    sleep 1
done

# Télécharger le modèle souhaité
echo "Downmoading AI model llama3..."
ollama pull llama3

# Garder le serveur au premier plan (important pour Docker)
wait
