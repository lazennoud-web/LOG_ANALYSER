import sys
from pathlib import Path
import pymysql
sys.path.append(str(Path(__file__).resolve().parent.parent))#racine du projet : log_analysis
from storage import store
from log_config import get_logger

"""
    Requêtes SQL du dashboard
    in : connexion pymysql (table auth_logs : month, day, time, ip, user, status, country, message...)
    out : list[tuple] (résultat de cursor.fetchall())
"""
logger = get_logger('serving')

def get_connection():
    config = store.load_config()#mêmes paramètres que storage (mysql_config.json / variables MYSQL_*)
    try:
        connection = pymysql.connect(host=config['host'], port=config['port'], user=config['user'],
                                     password=config['password'], database=config['database'],
                                     charset='utf8mb4', connect_timeout=3)
        logger.info(f"Connecté à la base {config['database']} ({config['host']}:{config['port']})")
        return connection
    except pymysql.Error as e:
        logger.error(f"Base indisponible ({config['host']}:{config['port']}) : {e}")
        return None

def indicators(connection)->list[tuple]:
    try:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT COUNT(*), COUNT(DISTINCT ip), SUM(status = 'Failed')
                              FROM auth_logs""")
            data = cursor.fetchall()
    except pymysql.Error as e:
        logger.error(f'Requête indicators échouée : {e}')
        return []
    if not data or data[0][0] == 0:
        logger.warning('Résultat vide : indicators (table auth_logs vide)')
        return []
    return data

def failed_by_country(connection, limit:int=15)->list[tuple]:
    try:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT IF(country IS NULL OR country = '', 'Inconnu', country) AS pays, COUNT(*) AS total
                              FROM auth_logs
                              WHERE status = 'Failed'
                              GROUP BY pays
                              ORDER BY total DESC
                              LIMIT %s""", (limit,))
            data = cursor.fetchall()
    except pymysql.Error as e:
        logger.error(f'Requête failed_by_country échouée : {e}')
        return []
    if not data:
        logger.warning('Résultat vide : failed_by_country')
    return data

def success_by_user(connection)->list[tuple]:
    try:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT user, COUNT(*) AS total
                              FROM auth_logs
                              WHERE status = 'Success'
                              GROUP BY user
                              ORDER BY total DESC""")
            data = cursor.fetchall()
    except pymysql.Error as e:
        logger.error(f'Requête success_by_user échouée : {e}')
        return []
    if not data:
        logger.warning('Résultat vide : success_by_user')
    return data

def invalid_users(connection, limit:int=15)->list[tuple]:
    try:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT user, COUNT(*) AS total
                              FROM auth_logs
                              WHERE status = 'Failed' AND message LIKE %s
                              GROUP BY user
                              ORDER BY total DESC
                              LIMIT %s""", ('Failed password for invalid user%', limit))
            data = cursor.fetchall()
    except pymysql.Error as e:
        logger.error(f'Requête invalid_users échouée : {e}')
        return []
    if not data:
        logger.warning('Résultat vide : invalid_users')
    return data

def top_ips(connection, limit:int=10)->list[tuple]:
    try:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT ip, COUNT(*) AS total
                              FROM auth_logs
                              WHERE status = 'Failed'
                              GROUP BY ip
                              ORDER BY total DESC
                              LIMIT %s""", (limit,))
            data = cursor.fetchall()
    except pymysql.Error as e:
        logger.error(f'Requête top_ips échouée : {e}')
        return []
    if not data:
        logger.warning('Résultat vide : top_ips')
    return data

def events_by_hour(connection)->list[tuple]:
    try:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT HOUR(time) AS heure, COUNT(*) AS total
                              FROM auth_logs
                              GROUP BY heure
                              ORDER BY heure""")
            data = cursor.fetchall()
    except pymysql.Error as e:
        logger.error(f'Requête events_by_hour échouée : {e}')
        return []
    if not data:
        logger.warning('Résultat vide : events_by_hour')
    return data

def events_by_day(connection)->list[tuple]:
    try:
        with connection.cursor() as cursor:
            #FIELD() remet les mois dans l'ordre du calendrier (sinon Apr < Jan < May...)
            cursor.execute("""SELECT CONCAT(day, ' ', month) AS jour, COUNT(*) AS total
                              FROM auth_logs
                              GROUP BY month, day
                              ORDER BY FIELD(month, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                             'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'), day""")
            data = cursor.fetchall()
    except pymysql.Error as e:
        logger.error(f'Requête events_by_day échouée : {e}')
        return []
    if not data:
        logger.warning('Résultat vide : events_by_day')
    return data

if __name__ == '__main__':
    connection = get_connection()
    if connection:
        with connection:
            print('indicators :', indicators(connection))
            print('failed_by_country :', failed_by_country(connection))
            print('success_by_user :', success_by_user(connection))
            print('invalid_users :', invalid_users(connection))
            print('top_ips :', top_ips(connection))
            print('events_by_hour :', events_by_hour(connection))
            print('events_by_day :', events_by_day(connection))
    else:
        print('Base indisponible : voir logs/serving.log')
