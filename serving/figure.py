import re
import sys
from collections import Counter
from pathlib import Path
from typing import List
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
sys.path.append(str(Path(__file__).resolve().parent.parent))#racine du projet : log_analysis
from ingestion import raw
from processing import extract_transforme
from storage import store

"""
    Dashboard SSH (une seule fenêtre matplotlib)
    in : fichiers de data/ (tous les événements) + pays depuis storage (MySQL ou csv)
    out : figure : 4 indicateurs + 6 graphiques
"""
BG = '#16213a'
PANEL = '#24344f'
TEXT = '#f1f5f9'
MUTED = '#94a3b8'
GRID = '#3b4d6b'
CYAN, GREEN, RED, ORANGE, PINK = '#22d3ee', '#4ade80', '#f87171', '#fb923c', '#f0abfc'

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
EVENT_TYPES = [
    ('Accepted login', r'^Accepted'),
    ('Failed password', r'Failed password'),
    ('Invalid user', r'^Invalid user'),
    ('Auth failure', r'authentication failure'),
    ('Connection closed', r'Connection closed'),
    ('Disconnect', r'[Dd]isconnect'),
]
COUNTRY_NAMES = {
    'AR': 'Argentina', 'AU': 'Australia', 'BD': 'Bangladesh', 'BE': 'Belgium', 'BG': 'Bulgaria', 'BR': 'Brazil',
    'CA': 'Canada', 'CH': 'Switzerland', 'CL': 'Chile', 'CN': 'China', 'CO': 'Colombia', 'CZ': 'Czechia',
    'DE': 'Germany', 'DZ': 'Algeria', 'EG': 'Egypt', 'ES': 'Spain', 'FI': 'Finland', 'FR': 'France',
    'GB': 'United Kingdom', 'GR': 'Greece', 'HK': 'Hong Kong', 'ID': 'Indonesia', 'IE': 'Ireland', 'IL': 'Israel',
    'IN': 'India', 'IR': 'Iran', 'IT': 'Italy', 'JP': 'Japan', 'KR': 'South Korea', 'KZ': 'Kazakhstan',
    'LT': 'Lithuania', 'MA': 'Morocco', 'MX': 'Mexico', 'MY': 'Malaysia', 'NL': 'The Netherlands', 'NG': 'Nigeria',
    'PE': 'Peru', 'PH': 'Philippines', 'PK': 'Pakistan', 'PL': 'Poland', 'PT': 'Portugal', 'RO': 'Romania',
    'RU': 'Russia', 'SA': 'Saudi Arabia', 'SC': 'Seychelles', 'SE': 'Sweden', 'SG': 'Singapore', 'SI': 'Slovenia',
    'TH': 'Thailand', 'TN': 'Tunisia', 'TR': 'Turkey', 'TW': 'Taiwan', 'UA': 'Ukraine', 'US': 'United States',
    'VN': 'Vietnam', 'ZA': 'South Africa',
}

# ---------- données ----------

def event_type(message:str)->str:
    for name, pattern in EVENT_TYPES:
        if re.search(pattern, message):
            return name
    return 'Other'

def get_ip(message:str)->str:
    match = re.search(r'(\d+\.\d+\.\d+\.\d+)', message)
    return match.group(1) if match else ''

"""
    in : rows from ingestion
    out : list of dict (month, day, hour, ip, user, type) : tous les événements
"""
def load_events()->List[dict]:
    events = []
    for row in raw.to_rows():
        match = extract_transforme.exctract_from_row(row)
        if match:
            message = match['message']
            events.append({'month': match['month'], 'day': int(match['day']), 'hour': int(match['time'][:2]),
                           'ip': get_ip(message), 'user': store.get_user(message), 'type': event_type(message)})
    return events

def load_countries()->dict:
    logs, _ = store.load()
    countries = {log['ip']: log['country'] for log in logs if log['country']}
    countries.update({ip: info['country'] for ip, info in store.ip_cache.items() if info.get('country')})
    return countries

# ---------- graphiques ----------

def style(ax, title:str)->None:
    ax.set_facecolor(PANEL)
    ax.set_title(title, color=TEXT, fontsize=12, fontweight='bold', loc='left', pad=10)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors=TEXT, labelsize=8, length=0)
    ax.grid(color=GRID, linewidth=0.7)
    ax.set_axisbelow(True)

def barh(ax, items:list, color:str, title:str)->None:
    style(ax, title)
    ax.grid(axis='y', visible=False)
    labels = [str(label) for label, _ in items]
    ax.barh(labels, [value for _, value in items], color=color, height=0.65)
    ax.invert_yaxis()

def kpi(fig, x:float, value:str, name:str, color:str)->None:
    fig.text(x, 0.855, value, color=color, fontsize=30, fontweight='bold')
    fig.text(x, 0.825, name, color=TEXT, fontsize=12)

def plot_dashboard(events:List[dict], countries:dict)->None:
    failed = sum(1 for event in events if event['type'] == 'Failed password')
    ips = Counter(event['ip'] for event in events if event['ip'])

    fig = plt.figure(figsize=(16, 9), facecolor=BG)
    fig.canvas.manager.set_window_title('Log Analyser - Dashboard SSH')
    fig.suptitle('Log Analyser - Dashboard SSH', color=TEXT, fontsize=20, fontweight='bold', y=0.97)
    kpi(fig, 0.10, f'{len(events)}', 'Événements', CYAN)
    kpi(fig, 0.32, f'{len(ips)}', 'IP uniques', GREEN)
    kpi(fig, 0.54, f'{failed}', 'Mots de passe échoués', RED)
    kpi(fig, 0.76, f"{failed / len(events) * 100:.1f} %" if events else '0 %', "Taux d'échec", ORANGE)

    grid = GridSpec(2, 3, figure=fig, left=0.10, right=0.97, top=0.74, bottom=0.08, hspace=0.45, wspace=0.42)

    barh(fig.add_subplot(grid[0, 0]), ips.most_common(10), CYAN, 'Top 10 IP les plus actives')

    types = Counter(event['type'] for event in events)
    barh(fig.add_subplot(grid[0, 1]), sorted(types.items(), key=lambda item: item[1], reverse=True), PINK, "Types d'événements")

    users = Counter(event['user'] for event in events if event['user'] and event['type'] in ('Failed password', 'Invalid user'))
    barh(fig.add_subplot(grid[0, 2]), users.most_common(8), ORANGE, 'Comptes les plus ciblés')

    ax = fig.add_subplot(grid[1, 0])
    style(ax, 'Événements par heure')
    hours = Counter(event['hour'] for event in events)
    ax.bar(range(24), [hours[h] for h in range(24)], color=GREEN, width=0.75)
    ax.set_xticks(range(0, 24, 3))
    ax.grid(axis='x', visible=False)

    ax = fig.add_subplot(grid[1, 1])
    style(ax, 'Événements par jour')
    days = Counter((MONTHS.index(event['month']), event['day']) for event in events)
    ordered = sorted(days)
    ax.plot(range(len(ordered)), [days[d] for d in ordered], color=ORANGE, lw=2, marker='o', markersize=4)
    step = max(1, len(ordered) // 7)
    ax.set_xticks(range(0, len(ordered), step))
    ax.set_xticklabels([f'{MONTHS[m]} {d}' for m, d in ordered[::step]], rotation=30, ha='right')
    ax.set_ylim(bottom=0)

    by_country = Counter(COUNTRY_NAMES.get(countries[event['ip']], countries[event['ip']])
                         for event in events if event['type'] == 'Failed password' and event['ip'] in countries)
    barh(fig.add_subplot(grid[1, 2]), by_country.most_common(5), CYAN, 'Pays des IP (top)')

    try:
        fig.canvas.manager.window.state('zoomed')#plein écran (backend TkAgg)
    except Exception:
        pass
    plt.show()

def run()->None:
    plot_dashboard(load_events(), load_countries())

if __name__ == '__main__':
    run()
