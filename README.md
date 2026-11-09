# Log Analysis - Analyseur de logs SSH

Ce projet est un pipeline d’analyse de logs SSH qui lit les fichiers de type `auth.log`, extrait les tentatives de connexion, les transforme, les charge dans PostgreSQL et affiche un dashboard Matplotlib avec les statistiques demandées.

L’objectif principal est de détecter :
- les tentatives SSH échouées par pays,
- les tentatives réussies par utilisateur,
- les échecs liés à des utilisateurs invalides,
- le taux global d’échec.

Le projet est pensé pour être exécutable localement depuis un terminal, avec un stockage PostgreSQL et une sortie visuelle simple sous forme de dashboard.

## 1. Description du projet

Le pipeline suit 4 étapes principales :

1. Ingestion des logs
   - lecture des fichiers présents dans `data/`
   - extraction des lignes structurées depuis `auth.log`

2. Transformation du contenu
   - identification des événements SSH `Failed` / `Accepted`
   - extraction des champs utiles : date, heure, machine, service, statut, utilisateur, IP, port
   - gestion des cas `invalid user`

3. Stockage dans PostgreSQL
   - création de la base si nécessaire
   - création de la table `t_ssh_events`
   - insertion des événements

4. Dashboard
   - lecture des données PostgreSQL
   - affichage de graphiques avec `matplotlib`
   - moyenne / total / taux d’échec

## 2. Structure du projet

- `main.py` : point d’entrée principal
- `config.py` : paramètres de configuration PostgreSQL et variables d’environnement
- `log_config.py` : configuration des logs applicatifs
- `ingestion/raw.py` : lecture des fichiers logs
- `processing/extract_transforme.py` : extraction des lignes utiles
- `processing/geo_location.py` : géolocalisation des IP via l’API IPInfo
- `storage/database.py` : connexion PostgreSQL
- `storage/schema.py` : création de la base et des tables
- `storage/dal.py` : transformation et insertion des événements
- `storage/queries.py` : requêtes SQL du dashboard
- `serving/services.py` : préparation des données pour l’affichage
- `serving/figure.py` : génération du dashboard Matplotlib
- `data/` : fichiers de logs à analyser
- `logs/` : fichiers journaux du projet

## 3. Prérequis

Avant de lancer le projet, il faut avoir :

- Python 3.11 ou supérieur
- PostgreSQL installé et démarré localement
- un utilisateur PostgreSQL valide
- le paquet `matplotlib`
- le paquet `psycopg2`

Le projet est conçu pour fonctionner avec les bibliothèques minimales nécessaires :
- `matplotlib`
- `re` (bibliothèque standard)
- `psycopg2` pour PostgreSQL

## 4. Installation

Depuis le dossier du projet :

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install matplotlib psycopg2-binary
```

Si le projet est installé sous forme de package local, une alternative est :

```bash
python -m pip install -e .
```

## 5. Configuration PostgreSQL

1. Créer une base PostgreSQL locale (ou utiliser une base existante)
2. Copier le fichier `.env.example` en `.env`
3. Modifier les valeurs de connexion :

```env
PG_HOST=localhost
PG_PORT=5432
PG_DBNAME=log_analysis
PG_USER=lina123
PG_PASSWORD=lina123
PG_SSLMODE=disable
```

Important :
- `PG_DBNAME` correspond au nom de la base de données que le projet va créer ou utiliser
- le mot de passe ne doit jamais être publié dans Git
- le fichier `.env` doit rester local

## 6. Lancer le projet

### 6.1. Afficher le dashboard

```bash
python main.py
```

Cela charge les données depuis PostgreSQL si la base est disponible et si la table contient des données. Sinon, le projet revient automatiquement à une lecture locale des fichiers `data/` et affiche les métriques sur la base des logs disponibles.

### 6.2. Importer les logs dans PostgreSQL

```bash
python main.py import
```

### 6.3. Importer les logs sans géolocalisation IP

```bash
python main.py import --no-geo
```

Cette option évite les appels externes à l’API IPInfo et accélère le chargement si vous ne voulez pas utiliser la géolocalisation.

## 7. Dashboard demandé

Le dashboard affiche les 3 éléments suivants :

1. Nombre de tentatives échouées par pays
   - regroupement par `country`
   - données agrégées pour le statut `FAILED`

2. Nombre de tentatives réussies par utilisateur
   - regroupement par `username`
   - statut `ACCEPTED`

3. Tentatives échouées avec `invalid user`
   - comparaison des utilisateurs invalides
   - agrégation sur `invalid_user = true`

Un KPI global est également affiché :
- nombre total de tentatives,
- nombre d’IP uniques,
- nombre de tentatives échouées,
- taux d’échec.

## 8. Modèle de données PostgreSQL

La table principale est :

```sql
CREATE TABLE IF NOT EXISTS t_ssh_events (
    id SERIAL PRIMARY KEY,
    date_time TIMESTAMP NOT NULL,
    host VARCHAR(100),
    status VARCHAR(10) NOT NULL CHECK (status IN ('FAILED', 'ACCEPTED')),
    username VARCHAR(255),
    invalid_user BOOLEAN NOT NULL DEFAULT FALSE,
    ip_address INET NOT NULL,
    port INTEGER CHECK (port BETWEEN 0 AND 65535),
    country VARCHAR(100)
);
```

Cette structure permet de stocker une tentative SSH unique avec les métadonnées nécessaires à l’analyse et au dashboard.

## 9. Journaux applicatifs

Le projet enregistre les erreurs et événements importants dans le dossier `logs/`.

Chaque module a son propre journal :
- `logs/storage.log`
- `logs/serving.log`
- `logs/ingestion.log`
- éventuellement `logs/geo.log`

Les logs contiennent :
- date / heure,
- niveau (INFO, WARNING, ERROR, CRITICAL),
- nom du module,
- message détaillé.

Cela facilite le débogage en cas de problème de connexion PostgreSQL, d’import, ou de transformation des logs.

## 10. Règles de gestion des erreurs

Le projet a été conçu pour ne pas planter complètement si une donnée est absente ou si la base PostgreSQL n’est pas disponible.

Exemples de gestion :
- fichier de logs introuvable → log d’erreur, liste vide
- PostgreSQL inaccessible → utilisation des données locales `data/`
- erreur de type SQL → rollback et message dans le journal
- affichage Matplotlib impossible → la fenêtre ne s’ouvre pas mais le programme ne bloque pas

## 11. Exemple de flux d’utilisation

### Étape 1 : vérifier PostgreSQL

```bash
pg_isready
```

### Étape 2 : configurer le `.env`

```bash
cp .env.example .env
```

### Étape 3 : importer les logs

```bash
python main.py import --no-geo
```

### Étape 4 : lancer le dashboard

```bash
python main.py
```

## 12. Dépannage

### Problème : `ModuleNotFoundError: No module named 'matplotlib'`

```bash
python -m pip install matplotlib
```

### Problème : `relation "t_ssh_events" does not exist`

Cela signifie que la table PostgreSQL n’a pas encore été créée ou que la base n’est pas la bonne.

Vérifier :
- le `.env`
- la base cible
- la commande d’import exécutée

### Problème : base PostgreSQL indisponible

Vérifier :
- que PostgreSQL est démarré,
- que l’utilisateur de connexion a les droits,
- que la base existe,
- que le mot de passe du `.env` est correct.

## 13. Conclusion

Ce projet permet de transformer des logs SSH bruts en données exploitables pour l’analyse de sécurité, la détection de tentatives d’intrusion et le suivi des attaques par origine géographique et utilisateur.

Il combine :
- ingestion de fichiers logs,
- transformation structurelle,
- stockage PostgreSQL,
- requêtes analytiques,
- dashboard visuel.

C’est un exemple complet de pipeline de données orienté sécurité informatique, avec un flux simple à intégrer dans un environnement de production ou de laboratoire.
