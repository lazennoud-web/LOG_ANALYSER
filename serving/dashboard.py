import sys
from pathlib import Path
from matplotlib import pyplot as pl
sys.path.append(str(Path(__file__).resolve().parent.parent))#racine du projet : log_analysis
from serving import services
from log_config import get_logger

"""
    Dashboard SSH (une seule fenêtre matplotlib)
    in : données MySQL (serving/services.py)
    out : figure : 4 indicateurs + 6 graphiques
"""
logger = get_logger('serving')

TITLE = 'Log Analyser - Dashboard SSH'
BG = '#0f1b33'      #fond bleu nuit
PANEL = '#18284a'   #fond des graphiques
TEXT = '#ffffff'
MUTED = '#8fa3c7'
GRID = '#3a4f7a'
CYAN, GREEN, ORANGE, PINK, RED = '#22d3ee', '#4ade80', '#fb923c', '#f472b6', '#f87171'

def apply_theme()->None:
    pl.rcParams.update({
        'figure.facecolor': BG, 'axes.facecolor': PANEL, 'axes.edgecolor': PANEL,
        'axes.labelcolor': MUTED, 'axes.titlecolor': TEXT, 'axes.titlesize': 11, 'axes.titleweight': 'bold',
        'text.color': TEXT, 'xtick.color': TEXT, 'ytick.color': TEXT, 'font.size': 8,
        'axes.grid': True, 'grid.color': GRID, 'grid.alpha': 0.4, 'axes.axisbelow': True,
    })

# ---------- graphiques ----------

def no_data(title:str)->None:
    pl.title(title)
    pl.text(0.5, 0.5, 'Aucune donnée', ha='center', va='center', fontsize=14, color=MUTED, transform=pl.gca().transAxes)
    pl.xticks([])
    pl.yticks([])

def draw_barh(n:int, data:list[tuple], title:str, color:str, xlabel:str)->None:
    pl.subplot(2, 3, n)
    if not data:
        no_data(title)
        return
    x = [str(label) for label, total in data]
    y = [int(total) for label, total in data]
    pl.barh(x, y, color=color)
    pl.gca().invert_yaxis()#le plus grand en haut
    for i, value in enumerate(y):
        pl.text(value, i, f' {value}', va='center', fontsize=7)
    pl.xlim(0, max(y) * 1.18)#place pour les valeurs
    pl.title(title)
    pl.xlabel(xlabel)

def draw_bar(n:int, data:list[tuple], title:str, color:str, xlabel:str, ylabel:str)->None:
    pl.subplot(2, 3, n)
    if not data:
        no_data(title)
        return
    x = [str(label) for label, total in data]
    y = [int(total) for label, total in data]
    pl.bar(x, y, color=color)
    for i, value in enumerate(y):
        pl.text(i, value, str(value), ha='center', va='bottom', fontsize=7)
    pl.ylim(0, max(y) * 1.15)
    pl.title(title)
    pl.xlabel(xlabel)
    pl.ylabel(ylabel)
    pl.xticks(rotation=45)

def draw_hours(n:int, data:list[tuple])->None:
    title = 'Événements par heure'
    pl.subplot(2, 3, n)
    if not data:
        no_data(title)
        return
    counts = {int(hour): int(total) for hour, total in data}
    x = [hour for hour in range(24)]
    y = [counts.get(hour, 0) for hour in x]#0 pour les heures sans événement
    pl.bar(x, y, color=GREEN)
    pl.title(title)
    pl.xlabel('Heure')
    pl.ylabel('Événements')
    pl.xticks([hour for hour in range(0, 24, 2)], [f'{hour}h' for hour in range(0, 24, 2)], rotation=45)

def draw_days(n:int, data:list[tuple])->None:
    title = 'Événements par jour'
    pl.subplot(2, 3, n)
    if not data:
        no_data(title)
        return
    x = [str(day) for day, total in data]
    y = [int(total) for day, total in data]
    pl.plot(x, y, color=ORANGE, linewidth=2, marker='o', markersize=3)
    peak = y.index(max(y))
    pl.text(peak, y[peak], f' max {y[peak]}', fontsize=7, color=ORANGE)
    step = max(1, len(x) // 10)#une étiquette sur "step" pour rester lisible
    pl.xticks([i for i in range(0, len(x), step)], x[::step], rotation=45)
    pl.ylim(bottom=0)
    pl.title(title)
    pl.xlabel('Jour')
    pl.ylabel('Événements')

def draw_chart(draw, *args)->None:
    """dessine un graphique ; une erreur matplotlib est enregistrée sans arrêter le dashboard"""
    try:
        draw(*args)
    except Exception as e:
        logger.error(f'Erreur matplotlib ({draw.__name__}, graphique {args[0]}) : {e}')
        pl.cla()
        no_data('Erreur')

# ---------- indicateurs ----------

def draw_indicators(fig, data:list[tuple])->None:
    total, ips, failed = [int(value or 0) for value in data[0]] if data else (0, 0, 0)
    rate = f'{failed / total * 100:.1f} %' if total else '—'
    items = [(f'{total}', 'Événements', CYAN), (f'{ips}', 'IP uniques', GREEN),
             (f'{failed}', 'Tentatives échouées', ORANGE), (rate, "Taux d'échec", PINK)]
    for i, (value, name, color) in enumerate(items):
        x = 0.08 + i * 0.23
        fig.text(x, 0.855, value, fontsize=28, fontweight='bold', color=color)
        fig.text(x, 0.825, name, fontsize=11, color=MUTED)

# ---------- fenêtre ----------

def load_data()->dict:
    names = ['indicators', 'failed_by_country', 'success_by_user', 'invalid_users', 'top_ips',
             'events_by_hour', 'events_by_day']
    connection = services.get_connection()
    if connection is None:
        logger.warning('Dashboard affiché sans données (base indisponible)')
        return {name: [] for name in names}
    with connection:#ferme la connexion à la fin
        return {name: getattr(services, name)(connection) for name in names}

def plot_dashboard(data:dict)->None:
    apply_theme()
    fig = pl.figure(figsize=(16, 9))
    try:
        fig.canvas.manager.set_window_title(TITLE)
    except AttributeError:#pas de fenêtre (backend sans affichage)
        pass
    fig.suptitle(TITLE, fontsize=20, fontweight='bold', y=0.97)
    draw_indicators(fig, data['indicators'])

    draw_chart(draw_barh, 1, data['failed_by_country'], 'Tentatives échouées par pays (top 15)', CYAN, 'Échecs')
    draw_chart(draw_bar, 2, data['success_by_user'], 'Connexions réussies par utilisateur', GREEN, 'Utilisateur', 'Réussites')
    draw_chart(draw_barh, 3, data['invalid_users'], '"Invalid user" : top 15 usernames', PINK, 'Échecs')
    draw_chart(draw_barh, 4, data['top_ips'], 'Top 10 IP (tentatives échouées)', RED, 'Échecs')
    draw_chart(draw_hours, 5, data['events_by_hour'])
    draw_chart(draw_days, 6, data['events_by_day'])

    pl.subplots_adjust(left=0.08, right=0.98, top=0.76, bottom=0.10, hspace=0.55, wspace=0.40)

def run()->None:
    try:
        plot_dashboard(load_data())
        pl.show()
    except Exception as e:
        logger.exception(f'Erreur du dashboard : {e}')

if __name__ == '__main__':
    run()
