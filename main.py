#connection echoué par pays et par mois
#nbre d'echoue par jours si possible une courbe
#python main.py          -> dashboard matplotlib (une fenêtre)
#python main.py app      -> application complète (pages, données, recherche ip, MySQL)
#python main.py import   -> ingestion -> processing -> storage (MySQL + csv) sans interface
#python main.py dashboard -> dashboard matplotlib depuis MySQL (serving/dashboard.py + serving/services.py)
import sys
from storage import store
from serving import application, dashboard, figure

if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ''
    if command == 'import':
        logs, source = store.import_data(lambda step, i, n: print(f'\r{step} : {i}/{n}', end='', flush=True))
        print(f'\n{len(logs)} lignes enregistrées ({source})')
    elif command == 'app':
        application.run()
    elif command == 'dashboard':
        dashboard.run()
    else:
        figure.run()
