import os
from pathlib import Path

"""
    Paramètres de connexion PostgreSQL
    in : fichier .env à la racine du projet (lignes CLE=valeur) ou variables d'environnement
    out : PG_HOST, PG_PORT, PG_DBNAME, PG_USER, PG_PASSWORD, PG_SSLMODE (None si absent)
"""
ENV_FILE = Path(__file__).resolve().parent / '.env'

def load_env(path:Path=ENV_FILE)->None:
    """lit le .env avec la bibliothèque standard et le copie dans os.environ"""
    if not path.exists():
        return
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:#ligne vide ou commentaire
                continue
            key, value = line.split('=', 1)
            #setdefault : une vraie variable d'environnement reste prioritaire sur le .env
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

load_env()
PG_HOST = os.getenv('PG_HOST')
PG_PORT = os.getenv('PG_PORT')
PG_DBNAME = os.getenv('PG_DBNAME')
PG_USER = os.getenv('PG_USER')
PG_PASSWORD = os.getenv('PG_PASSWORD')
PG_SSLMODE = os.getenv('PG_SSLMODE')#disable : serveur local sans SSL

if __name__ == '__main__':
    print(PG_HOST, PG_PORT, PG_DBNAME, PG_USER, PG_SSLMODE, 'mot de passe :', 'oui' if PG_PASSWORD else 'non')
