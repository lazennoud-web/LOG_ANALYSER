# Log Analysis – Analyse des logs SSH

## Présentation du projet

Ce projet consiste à analyser des fichiers de logs SSH pour étudier les tentatives de connexion à un serveur.

L'objectif est de récupérer les informations importantes dans les logs, de les organiser et de les utiliser pour afficher quelques statistiques sous forme de graphiques.

Le projet permet notamment de voir les tentatives de connexion échouées, les connexions réussies et les utilisateurs invalides.

## Organisation du projet

Le projet est organisé en plusieurs dossiers et fichiers :

- `data/` : (les donnees sources , c'est le dossier qui contient les fichiers de logs SSH qu'on veut analyser (auth.log1 , auth.log2 etc))
- `ingestion/` : la recuperation des donnees , afin de pouvoir les traiter ( il contient le code qui: ouvre les fichiers de logs , lit leur contenu , recupere les lignes une par une )
- `processing/` : transformer les lignes brutes en informations structurées et exploitables.
- `storage/` : stocke les donnees ,s'occupe de la connexion à la base de données et de l'enregistrement des données.
- `serving/` : prépare les données et affiche les graphiques.
- `logs/` : contient les journaux de l'application.
- `main.py` : permet de lancer le projet.
- `config.py` : contient les paramètres de configuration.
- `log_config.py` : permet de configurer les logs de l'application.

## Installation

Pour utiliser le projet, il faut avoir Python installé ainsi que PostgreSQL.

Il faut ensuite installer les bibliothèques nécessaires :

```bash
pip install matplotlib psycopg2-binary python-dotenv
matplotlib : c est la biblio python qui permet de creer des graphiques er des visualisations 

psychipg2-binary : c une biblio python qui permet de postgreSQL

python-dotenv : Charger les paramètres du fichier .env 

```

## Configuration

Avant de lancer le projet, il faut configurer la connexion à PostgreSQL dans le fichier `.env`.

Exemple :

```env
PG_HOST=localhost
PG_PORT=5432
PG_DBNAME=log_analysis
PG_USER=lina123
PG_PASSWORD=lina123
PG_SSLMODE=disable
```

Les informations de connexion doivent être adaptées à la configuration de PostgreSQL sur la machine.

## Exécution du projet

Pour lancer le projet et afficher le dashboard :

```bash
python main.py
```

Pour importer les logs dans la base de données :

```bash
python main.py import
```

Pour effectuer l'importation sans géolocalisation des adresses IP :

```bash
python main.py import --no-geo
```

## Résultats

Après l'analyse des fichiers, le projet affiche un dashboard avec plusieurs informations :

- Le nombre de tentatives de connexion échouées par pays.
- Le nombre de connexions réussies par utilisateur.
- Les tentatives effectuées avec des utilisateurs invalides.
- Le nombre total de tentatives.
- Le nombre d'adresses IP différentes.
- Le taux d'échec des connexions.

Les graphiques sont réalisés avec Matplotlib.

## Conclusion

Ce projet m'a permis de travailler sur la lecture et le traitement des fichiers logs, l'utilisation d'une base de données PostgreSQL et la représentation des données avec des graphiques. Il permet également de mieux comprendre comment les logs SSH peuvent être utilisés pour suivre les tentatives de connexion à un serveur.