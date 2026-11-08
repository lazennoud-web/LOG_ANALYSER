import sys
from pathlib import Path
import psycopg2
sys.path.append(str(Path(__file__).resolve().parent.parent))#racine du projet : log_analysis
import config
from log_config import get_logger

"""
    Connexion PostgreSQL (psycopg2)
    in : paramètres du .env (config.py)
    out : connexion réutilisable + logs dans logs/storage.log
"""
logger = get_logger('storage')#logging.getLogger("storage") + fichier logs/storage.log

REQUIRED = ['PG_HOST', 'PG_PORT', 'PG_DBNAME', 'PG_USER']

def connect(dbname:str):
    """ouvre une connexion vers la base dbname ; None si impossible (erreur dans le log)"""
    missing = [name for name in REQUIRED if not getattr(config, name)]
    if missing:
        logger.critical(f"Paramètres manquants dans .env : {', '.join(missing)}")
        return None
    where = f'{config.PG_USER}@{config.PG_HOST}:{config.PG_PORT}/{dbname}'
    try:
        connection = psycopg2.connect(host=config.PG_HOST, port=config.PG_PORT, dbname=dbname,
                                      user=config.PG_USER, password=config.PG_PASSWORD,
                                      sslmode=config.PG_SSLMODE, connect_timeout=3)
        logger.info(f'Connexion réussie à PostgreSQL ({where})')
        return connection
    except psycopg2.OperationalError as e:
        #mauvais host/port, serveur arrêté, mauvais user/mot de passe, base inexistante
        message = ' '.join(str(e).split())#message psycopg2 sur une seule ligne dans le log
        logger.critical(f'Connexion PostgreSQL impossible ({where}) : {message}')
    except UnicodeDecodeError:
        #sous Windows, un serveur PostgreSQL en français peut renvoyer un message d'erreur illisible
        logger.critical(f'Connexion PostgreSQL impossible ({where}) : vérifier mot de passe, base et serveur')
    return None

def rollback(connection)->None:
    """annule la transaction en cours (sans planter si la connexion est déjà perdue)"""
    try:
        connection.rollback()
    except psycopg2.Error as e:
        logger.error(f'Rollback impossible : {e}')

class Database:
    connection = None

    @staticmethod
    def getConnection():
        #connection.closed == 0 : la connexion est encore ouverte, on la réutilise
        if Database.connection is not None and Database.connection.closed == 0:
            return Database.connection
        Database.connection = connect(config.PG_DBNAME)
        return Database.connection

    @staticmethod
    def close()->None:
        if Database.connection is not None and Database.connection.closed == 0:
            try:
                Database.connection.close()
                logger.info('Connexion PostgreSQL fermée')
            except psycopg2.Error as e:
                logger.error(f'Fermeture de la connexion impossible : {e}')
        Database.connection = None

if __name__ == '__main__':
    connection = Database.getConnection()
    print('Connexion :', connection is not None)
    if connection:
        print('Version du serveur :', connection.server_version)
    Database.close()
