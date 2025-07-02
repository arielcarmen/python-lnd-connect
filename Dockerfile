# Étape 1 : image de base
FROM python:3.10-slim

# Étape 2 : définir le dossier de travail
WORKDIR /app

# Étape 3 : copier les fichiers du projet local
COPY . .

# Étape 4 : rendre les scripts exécutables
RUN chmod +x setup.sh run.sh

# Étape 5 : exécuter le script de setup
RUN ./setup.sh

# Étape 6 : installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Étape 7 : exposer le port
EXPOSE 8000

# Étape 8 : exécuter le serveur
CMD ["./run.sh"]
