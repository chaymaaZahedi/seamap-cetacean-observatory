FROM apache/airflow:2.7.1-python3.10

USER root

# Installation des dépendances système pour Geopandas (GDAL, PROJ, etc.)
RUN apt-get update && apt-get install -y \
    libgdal-dev \
    g++ \
    --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configurer les variables d'environnement pour GDAL si nécessaire
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

USER airflow

# Installation des dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
