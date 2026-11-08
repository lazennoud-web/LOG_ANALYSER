#connection echoué par pays et par mois
#nbre d'echoue par jours si possible une courbe
#python main.py          -> dashboard matplotlib (serving/figure.py, une fenêtre)
#python main.py import   -> ingestion -> processing -> storage (PostgreSQL, table t_ssh_events, paramètres dans .env)
#python main.py import --no-geo -> idem sans géolocalisation ipinfo (plus rapide, pays vide)
import sys
from ingestion import raw
from processing import extract_transforme, geo_location
from storage import dal, schema
from storage.database import Database


def locate(ips:list[str])->dict:
    """ip -> pays avec ipinfo (un seul appel par ip)"""
    countries = {}
    for i, ip in enumerate(ips):
        location = geo_location.get_location(ip) or {}
        countries[ip] = location.get('country')
        print(f'\rGéolocalisation des IP : {i + 1}/{len(ips)}', end='', flush=True)
    print()
    return countries


def import_data(geo:bool=True)->None:
    rows = [extract_transforme.exctract_from_row(row) for row in raw.to_rows()]
    events = dal.to_events(rows)
    print(f'{len(rows)} lignes lues, {len(events)} événements Failed/Accepted')
    if geo:
        countries = locate(sorted({event[5] for event in events}))
        events = dal.to_events(rows, countries=countries)
    try:
        if schema.create_database():
            inserted = dal.load(events)
            print(f'{inserted} événements insérés dans PostgreSQL (table t_ssh_events)')
            print(f'COUNT(*) sur nouvelle connexion : {dal.count_rows()} lignes présentes dans t_ssh_events')
        else:
            print('Base indisponible : voir logs/storage.log')
    finally:
        Database.close()


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ''
    if command == 'import':
        import_data(geo='--no-geo' not in sys.argv)
    else:
        from serving import figure
        figure.run()
