# 🐋 SEAMAP · Observatoire des Cétacés

Ce projet est une application web interactive et un pipeline d'ingestion de données (ETL) dédiés à la visualisation et à l'analyse des observations de cétacés et autres mammifères marins. L'application est construite avec **Streamlit**, **Plotly**, et **Folium** pour offrir un tableau de bord premium et dynamique basé sur les données d'observations mondiales.

---

## 🚀 Fonctionnalités principales

- **Vue Globale & Cartographie interactive** : Visualisation géographique des observations à l'aide de cartes interactives (basées sur Mapbox et Folium) avec échantillonnage intelligent pour optimiser les performances d'affichage.
- **Analyse Temporelle & Saisonnière** : Évolution annuelle du nombre d'observations et répartition saisonnière par trimestre.
- **Standardisation de l'Effort (CPUE / SPUE)** :
  - **Méthodes Systématiques (ptobs)** : Calcul des individus par kilomètre parcouru (Effort Spatial).
  - **Photo-Identification (ptphoto)** : Calcul des individus par jour d'observation (Effort Temporel).
- **Filtres Avancés** : Filtrage par région géographique, groupe d'espèces (Baleine / Non baleine), espèce précise, année, type de plateforme d'observation.
- **Tests sans Filtre de Déduplication** : Module scientifique permettant de comparer les données filtrées officielles avec les données brutes non dédupliquées.
- **Gestion des Régions & Datasets** : Analyse de la couverture spatiale et temporelle de chaque dataset importé dans le système.

---

## 📁 Structure du projet

```text
seamap-cetacean-observatory/
│
├── main.py                          # Application principale Streamlit (Dashboard)
├── data_loader.py                   # Fonctions de chargement et traitement des données
├── ETL_v6.py                        # Pipeline principal d'extraction, transformation et chargement (ETL)
├── Dockerfile                       # Configuration de conteneurisation Docker
├── docker-compose.yaml              # Orchestration multi-conteneurs (ex: Streamlit + Airflow)
├── requirements.txt                 # Dépendances Python nécessaires au projet
│
├── dags/                            # Tâches planifiées (Airflow)
│   └── seamap_sync_dag.py           # DAG Airflow de synchronisation des pipelines SEAMAP
│
├── scripts/                         # Scripts d'ETL spécialisés
│   ├── ETL_spatial.py               # Traitement et standardisation spatiale
│   └── ETL_temporal.py              # Traitement et standardisation temporelle
│
├── data_source/                     # Dossier d'entrée pour les données brutes (exclut de Git)
├── gold_data/                       # Dossier de sortie pour les données nettoyées et agrégées (exclut de Git)
└── plugins/                         # Plugins additionnels d'Airflow / Streamlit
```

---

## 🛠️ Installation et Lancement Local

### Prérequis
- Python 3.10 ou supérieur
- Le gestionnaire de paquets `pip`

### 1. Cloner le projet et se positionner dedans
```bash
git clone <URL_DE_VOTRE_DEPOT_GITHUB>
cd seamap-cetacean-observatory
```

### 2. Créer et activer un environnement virtuel
- **Sur Windows (PowerShell) :**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **Sur macOS / Linux :**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Télécharger les données (requis)
Pour que l'application puisse tourner, vous devez télécharger et extraire les jeux de données (fichiers CSV de `gold_data/` et `data_source/`). Un script d'automatisation est fourni :
```bash
python download_data.py
```

### 5. Lancer le Dashboard Streamlit
```bash
streamlit run main.py
```
Le tableau de bord s'ouvrira automatiquement dans votre navigateur par défaut à l'adresse `http://localhost:8501`.

---

## 💾 Gestion et mise à jour des données (Pour le mainteneur)

Pour mettre à jour les données partagées ou si vous configurez ce projet pour la première fois :
1. Compressez vos dossiers `data_source/` et `gold_data/` dans une archive nommée `data.zip`.
2. Importez ce fichier `data.zip` sur votre Google Drive.
3. Partagez le fichier en mode **"Tous les utilisateurs disposant du lien"** (lecteur).
4. Récupérez l'ID du fichier dans le lien de partage (ex: si le lien est `https://drive.google.com/file/d/XYZ123/view`, l'ID est `XYZ123`).
5. Ouvrez le fichier [download_data.py](file:///c:/MyPc/master/s4/stage-ird/dashboard/seamap-cetacean-observatory/download_data.py) et modifiez la variable `GOOGLE_DRIVE_FILE_ID` avec votre ID.


---

## 🐳 Déploiement avec Docker

Si vous préférez exécuter l'application dans un conteneur isolé :

```bash
# Construire et lancer le conteneur
docker-compose up --build
```

L'application Streamlit sera accessible sur le port configuré (généralement `8501`).

---

## ⚙️ Pipeline ETL (Extraction, Transformation, Chargement)

Les données brutes situées dans `data_source/` sont transformées et agrégées dans `gold_data/` via le script `ETL_v6.py`.
Ce processus est orchestré automatiquement grâce au DAG Apache Airflow situé dans `dags/seamap_sync_dag.py`.

Pour exécuter manuellement une synchronisation ou un nettoyage :
```bash
python ETL_v6.py
```
*(Remarque : les gros fichiers CSV générés dans `gold_data/` et `data_source/` sont configurés pour être ignorés par Git afin d'optimiser le dépôt sur GitHub).*
