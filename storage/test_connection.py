import sys
from pathlib import Path
import psycopg2
sys.path.append(str(Path(__file__).resolve().parent.parent))#racine du projet : log_analysis
from storage.database import Database, logger

"""
    Test de connexion PostgreSQL
    out : affiche le résultat de SELECT version();
"""

def test_connection()->bool:
    connection = Database.getConnection()
    if connection is None:#l'erreur est déjà dans logs/storage.log
        print('Connexion impossible : voir logs/storage.log')
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT version();')
            print('Connexion OK :', cursor.fetchone()[0])
        connection.commit()
        return True
    except psycopg2.Error as e:
        logger.error(f'Requête SELECT version() échouée : {e}')
        return False
    finally:
        Database.close()

def check_connection():
    connection = Database.getConnection()
    if connection is None:
        logger.error('Connexion PostgreSQL impossible')
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            result = cursor.fetchone()
        logger.info(f'Connexion PostgreSQL OK : {result}')
        return True
    finally:
        Database.close()


if __name__ == '__main__':
    print('Connexion OK ? ', check_connection())
