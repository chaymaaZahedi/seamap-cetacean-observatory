# Plan d'Automatisation du Dashboard Baleine SEAMAP

Ce plan détaille la mise en place d'une automatisation robuste pour le dashboard `baleine-seamap_v6_finale`. L'objectif est de détecter les mises à jour sur le site SEAMAP de l'Université de Duke, de télécharger les nouveaux jeux de données et de mettre à jour automatiquement le dashboard via Apache Airflow.

## Architecture de l'Automatisation

L'écosystème sera conteneurisé avec **Docker** et orchestré par **Apache Airflow**.

1. **Dockerisation** : Le pipeline (Airflow + Scripts ETL) tournera dans un container pour garantir la portabilité et la gestion des dépendances (Geopandas, etc.).
2. **Scraping Ciblé** : Détection uniquement des datasets contenant des "Marine mammals".
3. **Ingestion & Filtrage** : Téléchargement et décompression sélective selon la présence d'effort.
4. **Mise à jour des métadonnées** : Actualisation complète de `index.csv`.
5. **ETL Modulaire** : Déclenchement de scripts ETL distincts selon le type de données (`ptobs` vs `ptphoto`).
6. **Dashboard** : Mise à jour automatique des fichiers Gold.

---

## Étapes de l'Implémentation

### 1. Développement du DAG Airflow
Le DAG sera programmé pour s'exécuter périodiquement (ex: hebdomadairement).

#### Task 1 : `check_for_updates` (PythonOperator)
- Se connecte à `https://seamap.env.duke.edu/dataset/list`.
- **Filtre** : Ne retient que les datasets marqués "Marine mammals".
- Pour chaque candidat, visite la page de métadonnées HTML :
    - Extrait la **Version** (ex: "1.0.0").
    - Extrait les dates (`Date Begin`, `Date End`), le nombre d'enregistrements (`Records`), la zone (`Latitude`, `Longitude`), le `Provider`, la `Platform`, le `Data type` et la `Region`.
    - Vérifie si `Effort` est "yes" ou "no".
- Compare avec `index.csv` pour décider du téléchargement.

#### Task 2 : `download_new_data` (PythonOperator)
- Utilise la requête fournie : `http://seamap.env.duke.edu//downloads/datasets/dataset_{id}/obis_seamap_dataset_{id}_csv_v{version}.zip`.
- Stocke les zips dans un dossier temporaire `bronze_data/zips/`.

#### Task 3 : `process_extraction` (PythonOperator)
- Extrait les fichiers contenus dans les zips.
- **Points** : Déplace les fichiers `.csv` vers `data_source/data_sources_point/`.
- **Tracks** : SI `Effort: yes`, déplace les dossiers `.gdb` vers `data_source/data_sources_survey_tracks/`. Sinon, ignore cette étape.

#### Task 4 : `update_index` (PythonOperator)
- Met à jour `index.csv` en remplissant TOUTES les colonnes :
    - `ID`, `Title`, `Title Hyperlink`, `Provider`, `Data type`, `Platform`, `Dataset`, `Version`, `Date Begin`, `Date End`, `Records`, `Latitude`, `Longitude`, `Effort`, `Region`.

#### Task 5 : `trigger_etl_logic` (BranchPythonOperator)
- Analyse le `Data type` du dataset mis à jour.
- **Branche A** : Si `Data type` est `ptobs` (et `Effort: yes`), déclenche `ETL_spatial.py`.
- **Branche B** : Si `Data type` est `ptphoto`, déclenche `ETL_temporal.py`.
- **Branche C** : Autres cas (déclenche un script générique si besoin).

---

## Setup de l'Environnement Airflow (Pas à Pas)

Pour démarrer le pipeline dans un container Docker, suivez ces étapes :

### 1. Structure du Projet
Créez l'arborescence suivante dans votre dossier de travail :
```text
baleine-seamap_v6_finale/
├── dags/                  # Dossier pour les DAGs Airflow
├── scripts/               # Scripts ETL_spatial.py, ETL_temporal.py
├── plugins/               # (Optionnel)
├── logs/                  # Logs Airflow
├── data_source/           # Montage volume pour les fichiers SEAMAP
├── gold_data/             # Montage volume pour les sorties CSV
├── Dockerfile             # Image personnalisée
├── docker-compose.yaml    # Orchestration
└── requirements.txt       # Dépendances Python
```

### 2. Configuration Docker

#### Dockerfile
Utilisez une image de base Airflow et installez les dépendances système pour Geopandas :
```dockerfile
FROM apache/airflow:2.7.1-python3.10
USER root
RUN apt-get update && apt-get install -y \
    libgdal-dev g++ --no-install-recommends \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
USER airflow
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

#### requirements.txt
```text
pandas
geopandas
beautifulsoup4
requests
pyogrio
```

### 3. Initialisation et Lancement

1. **Fixer l'UID** (pour éviter les problèmes de permissions sur Windows/Linux) :
   ```bash
   echo -e "AIRFLOW_UID=$(id -u)" > .env
   ```
2. **Initialiser la DB Airflow** :
   ```bash
   docker-compose up airflow-init
   ```
3. **Lancer Airflow** :
   ```bash
   docker-compose up -d
   ```

### 4. Création du Premier DAG
Placez le fichier `seamap_sync_dag.py` dans le dossier `dags/`. Ce fichier contiendra la définition des tâches (PythonOperator pour le scraping, BashOperator pour lancer les scripts ETL).

---

## Transformation des Données (Scripts Séparés)

L'ancien script `ETL_v6.py` sera scindé pour une meilleure maintenance :

| Script | Type Ciblé | Logique Clé |
| :--- | :--- | :--- |
| **ETL_spatial.py** | `ptobs` (Effort: yes) | Traitement des GDB, calcul des KM, CPUE spatial. |
| **ETL_temporal.py** | `ptphoto` | Déduplication par "organism_name" + "annee", SPUE temporel. |

---

## Plan de Vérification

### Tests Automatisés
- **Validation du Scraping** : Vérifier que le script extrait correctement la version "1.0.0" d'un dataset test.
- **Check de l'Index** : S'assurer qu'aucune ligne n'est dupliquée dans `index.csv` après mise à jour.
- **Intégrité des Données Gold** : Comparer le nombre d'observations avant et après mise à jour.

### Vérification Manuelle
- Lancement du DAG en mode manuel sur l'interface Airflow.
- Vérification que le nouveau dataset apparaît bien dans les filtres du Dashboard Streamlit.
