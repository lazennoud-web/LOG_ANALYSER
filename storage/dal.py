import re
import sys
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values
sys.path.append(str(Path(__file__).resolve().parent.parent))#racine du projet : log_analysis
from storage.database import Database, rollback, logger

"""
    Insertion dans t_ssh_events
    in : list of dict from processing (month, day, time, server, service, message)
    out : lignes dans PostgreSQL
"""
BATCH_SIZE = 5000
#"Failed password for invalid user admin from 1.2.3.4 port 22 ssh2" / "Accepted password for root from ... port ..."
EVENT = re.compile(r'(?P<status>Failed|Accepted) \S+ for (?P<invalid>invalid user )?(?P<user>\S*) from (?P<ip>\S+) port (?P<port>\d+)')

#VALUES %s : execute_values remplace ce %s par toutes les lignes du lot (requête paramétrée)
INSERT = """INSERT INTO t_ssh_events (date_time, host, status, username, invalid_user, ip_address, port, country)
            VALUES %s"""

# ---------- transformation ----------

def to_datetime(month:str, day:str, time:str, year:int=None)->datetime:
    """les logs n'ont pas d'année : année en cours (ou précédente si le mois est dans le futur)"""
    now = datetime.now()
    date = datetime.strptime(f'{year or now.year} {month} {day} {time}', '%Y %b %d %H:%M:%S')
    if year is None and date > now:
        date = date.replace(year=now.year - 1)
    return date

def to_event(row:dict, year:int=None, countries:dict=None)->tuple:
    """un dict du processing -> tuple pour l'INSERT, ou None si ce n'est pas un Failed/Accepted sshd
       countries : {ip: pays} (geo_location) ; sinon on prend row['country'] s'il existe"""
    if not row or row.get('service') != 'sshd':
        return None
    match = EVENT.search(row['message'])
    if not match:
        return None
    country = countries.get(match['ip']) if countries else row.get('country')
    return (to_datetime(row['month'], row['day'], row['time'], year),
            row['server'],
            'FAILED' if match['status'] == 'Failed' else 'ACCEPTED',
            match['user'],
            match['invalid'] is not None,
            match['ip'],
            int(match['port']),
            country or None)

def to_events(rows:list[dict], year:int=None, countries:dict=None)->list[tuple]:
    return [event for event in (to_event(row, year, countries) for row in rows) if event]

# ---------- écriture ----------

def clear()->bool:
    """vide la table pour relancer le pipeline sans doublons"""
    connection = Database.getConnection()
    if connection is None:
        return False
    try:
        with connection.cursor() as cursor:
            cursor.execute('TRUNCATE TABLE t_ssh_events RESTART IDENTITY')#RESTART IDENTITY : id repart à 1
        connection.commit()
        logger.info('Table t_ssh_events vidée')
        return True
    except psycopg2.Error as e:
        rollback(connection)
        logger.error(f'TRUNCATE t_ssh_events échoué : {e}')
        return False

def load(events:list[tuple], batch_size:int=BATCH_SIZE)->int:
    """insère les événements par lots ; retourne le nombre de lignes insérées"""
    if not events:
        logger.warning('Liste vide : aucune ligne à insérer')
        return 0
    connection = Database.getConnection()
    if connection is None:
        return 0
    inserted = 0
    for start in range(0, len(events), batch_size):
        batch = events[start:start + batch_size]
        name = f'lot {start}-{start + len(batch)}'
        try:
            with connection.cursor() as cursor:
                execute_values(cursor, INSERT, batch, page_size=len(batch))#un seul INSERT pour tout le lot
            connection.commit()
            inserted += len(batch)
        except psycopg2.IntegrityError as e:
            rollback(connection)#on annule seulement ce lot
            logger.error(f'{name} refusé (doublon, valeur manquante, statut ou port invalide) : {e.pgerror or e}')
        except psycopg2.DataError as e:
            rollback(connection)
            logger.error(f'{name} refusé (type incorrect : date, IP ou nombre) : {e.pgerror or e}')
        except psycopg2.Error as e:
            rollback(connection)
            logger.error(f'{name} : insertion échouée : {e}')
    logger.info(f'{inserted} lignes insérées sur {len(events)} dans t_ssh_events')
    return inserted

def count_rows()->int:
    """Retourne le nombre réel de lignes dans t_ssh_events sur une nouvelle connexion."""
    connection = Database.getConnection()
    if connection is None:
        return 0
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM t_ssh_events')
            count = cursor.fetchone()[0]
        connection.commit()
        logger.info(f'COUNT(*) sur t_ssh_events = {count}')
        return int(count)
    except psycopg2.Error as e:
        rollback(connection)
        logger.error(f'COUNT(*) t_ssh_events échoué : {e}')
        return 0

if __name__ == '__main__':
    rows = [
        {'month': 'May', 'day': '24', 'time': '00:04:36', 'server': 'ns', 'service': 'sshd', 'country': 'CN',
         'message': 'Failed password for invalid user admin from 121.29.89.152 port 22 ssh2'},
        {'month': 'May', 'day': '25', 'time': '10:00:00', 'server': 'ns', 'service': 'sshd',
         'message': 'Accepted password for adminesisa from 10.0.0.5 port 50000 ssh2'},
        {'month': 'May', 'day': '25', 'time': '10:00:01', 'server': 'ns', 'service': 'CRON', 'message': 'session opened for user root'},
    ]
    events = to_events(rows)
    print(events)
    try:
        print('clear :', clear())
        print('Insérées :', load(events))
        print('Nombre de lignes :', count_rows())
    finally:
        Database.close()
