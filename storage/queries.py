import sys
from pathlib import Path
import psycopg2
sys.path.append(str(Path(__file__).resolve().parent.parent))
from storage.database import Database, rollback, logger

"""
    Requêtes de lecture pour le dashboard
    in : table t_ssh_events
    out : list[tuple] (cursor.fetchall())
"""


def select(query: str, params: tuple, name: str) -> list[tuple]:
    """exécute un SELECT paramétré (%s) ; [] en cas d'erreur"""
    connection = Database.getConnection()
    if connection is None:
        return []
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            data = cursor.fetchall()
        connection.commit()#termine la transaction ouverte par le SELECT (sinon elle bloque TRUNCATE)
    except psycopg2.Error as e:
        rollback(connection)#après une erreur, PostgreSQL refuse toute requête tant qu'on n'a pas fait rollback
        logger.error(f'Requête {name} échouée : {e}')
        return []
    if not data:
        logger.warning(f'Résultat vide : {name}')
    return data


def failed_by_country() -> list[tuple]:
    """(pays, total) des tentatives échouées"""
    return select("""SELECT COALESCE(NULLIF(country, ''), 'Inconnu') AS pays, COUNT(*) AS total
                     FROM t_ssh_events
                     WHERE status = %s
                     GROUP BY pays
                     ORDER BY total DESC""", ('FAILED',), 'failed_by_country')


def success_by_user() -> list[tuple]:
    """(username, total) des tentatives réussies"""
    return select("""SELECT username, COUNT(*) AS total
                     FROM t_ssh_events
                     WHERE status = %s
                     GROUP BY username
                     ORDER BY total DESC""", ('ACCEPTED',), 'success_by_user')


def failed_invalid_users(limit: int = 15) -> list[tuple]:
    """(username, total) des échecs "Failed password for invalid user" (top 15)"""
    return select("""SELECT username, COUNT(*) AS total
                     FROM t_ssh_events
                     WHERE status = %s AND invalid_user = %s
                     GROUP BY username
                     ORDER BY total DESC
                     LIMIT %s""", ('FAILED', True, limit), 'failed_invalid_users')


def summary() -> list[tuple]:
    """(total événements, IP uniques, échecs, taux d'échec en %)"""
    return select("""SELECT COUNT(*), COUNT(DISTINCT ip_address),
                            COUNT(*) FILTER (WHERE status = %s),
                            ROUND(COUNT(*) FILTER (WHERE status = %s) * 100.0 / NULLIF(COUNT(*), 0), 2)
                     FROM t_ssh_events""", ('FAILED', 'FAILED'), 'summary')


if __name__ == '__main__':
    print('failed_by_country :', failed_by_country())
    print('success_by_user :', success_by_user())
    print('failed_invalid_users :', failed_invalid_users())
    print('summary :', summary())
    Database.close()
