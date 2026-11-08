import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))#racine du projet : log_analysis
from storage import queries
from storage.database import Database
from storage import dal
from ingestion import raw
from processing import extract_transforme
from log_config import get_logger

"""
    Pont entre serving et storage (PostgreSQL, table t_ssh_events)
    in : requêtes de storage/queries.py
    out : dict de list[tuple] pour serving/figure.py
"""
logger = get_logger('serving')


def _fallback_data()->dict:
    """Charge les logs depuis le dossier data quand la base PostgreSQL est indisponible."""
    rows = [extract_transforme.exctract_from_row(line) for line in raw.to_rows()]
    rows = [row for row in rows if row]
    events = dal.to_events(rows)
    if not events:
        return {'summary': [], 'failed_by_country': [], 'success_by_user': [], 'invalid_users': []}

    failed = sum(1 for event in events if event[2] == 'FAILED')
    total = len(events)
    unique_ips = len({event[5] for event in events})
    rate = round((failed * 100.0 / total), 2) if total else 0.0

    failed_by_country = {}
    for event in events:
        if event[2] != 'FAILED':
            continue
        country = event[7] or 'Inconnu'
        failed_by_country[country] = failed_by_country.get(country, 0) + 1

    success_by_user = {}
    for event in events:
        if event[2] == 'ACCEPTED':
            username = event[3] or 'Inconnu'
            success_by_user[username] = success_by_user.get(username, 0) + 1

    invalid_users = {}
    for event in events:
        if event[2] == 'FAILED' and event[4]:
            username = event[3] or 'Inconnu'
            invalid_users[username] = invalid_users.get(username, 0) + 1

    return {
        'summary': [(total, unique_ips, failed, rate)],
        'failed_by_country': sorted(failed_by_country.items(), key=lambda x: x[1], reverse=True)[:15],
        'success_by_user': sorted(success_by_user.items(), key=lambda x: x[1], reverse=True),
        'invalid_users': sorted(invalid_users.items(), key=lambda x: x[1], reverse=True)[:15],
    }


def load_data()->dict:
    """Charge d'abord les logs locaux, puis retombe sur PostgreSQL si disponible et exploitable."""
    fallback = _fallback_data()
    if not fallback['summary']:
        logger.warning('Aucune donnée locale détectée dans data/ : retour vide')
        return fallback

    db = Database.getConnection()
    if db is None:
        logger.warning('Base PostgreSQL indisponible : utilisation des données locales data/.')
        return fallback

    data = {
        'summary': queries.summary(),
        'failed_by_country': queries.failed_by_country()[:15],
        'success_by_user': queries.success_by_user(),
        'invalid_users': queries.failed_invalid_users(15),
    }
    Database.close()

    if not data['summary'] and not data['failed_by_country'] and not data['success_by_user'] and not data['invalid_users']:
        logger.warning('PostgreSQL vide ou cassé : utilisation des données locales data/.')
        return fallback

    for name, rows in data.items():
        if not rows:
            logger.warning(f'Résultat vide : {name}')
    return data


if __name__ == '__main__':
    for name, rows in load_data().items():
        print(name, ':', rows)
