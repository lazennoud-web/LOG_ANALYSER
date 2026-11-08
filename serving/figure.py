import sys
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch
from matplotlib.colors import to_rgba
from datetime import datetime
from matplotlib.ticker import MaxNLocator
sys.path.append(str(Path(__file__).resolve().parent.parent))#racine du projet : log_analysis
from serving import services
from log_config import get_logger

"""
    Dashboard SSH (une seule fenêtre matplotlib)
    in : données PostgreSQL (serving/services.py -> storage/queries.py)
    out : figure : 4 indicateurs + 3 graphiques demandés
          - tentatives échouées par pays
          - tentatives réussies par user
          - tentatives échouées avec invalid user
"""
logger = get_logger('serving')

#thème clair "papier" : fond crème, cartes blanches, encre sombre, couleurs franches
BG = '#f3efe6'
PANEL = '#ffffff'
TEXT = '#1f2430'
MUTED = '#7a7468'
GRID = '#e7e1d4'
BORDER = '#e2dccf'
CYAN, GREEN, RED, ORANGE, PINK = '#1d6fa5', '#2f8f5b', '#c8442f', '#d98a1c', '#8a4fb5'
plt.rcParams['font.sans-serif'] = ['Segoe UI', 'DejaVu Sans']#Segoe UI sous Windows, DejaVu Sans sinon

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

# ---------- graphiques ----------

def style(ax, title:str)->None:
    ax.set_facecolor(PANEL)
    ax.set_title(title, color=TEXT, fontsize=12.5, fontweight='bold', loc='left', pad=14)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors=TEXT, labelsize=9, length=0, pad=6)
    ax.tick_params(axis='x', colors=MUTED)
    ax.grid(color=GRID, linewidth=0.9, linestyle='--')
    ax.set_axisbelow(True)


def card(fig, ax, color:str)->None:
    """carte blanche arrondie derrière un graphique + bande de couleur en haut"""
    box = ax.get_position()
    x, y, w, h = box.x0 - 0.075, box.y0 - 0.06, box.width + 0.09, box.height + 0.115
    fig.patches.append(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0,rounding_size=0.012',
                                      transform=fig.transFigure, facecolor=PANEL, edgecolor=BORDER,
                                      linewidth=1, zorder=-1))
    fig.patches.append(FancyBboxPatch((x + 0.012, y + h - 0.008), 0.05, 0.004, boxstyle='round,pad=0',
                                      transform=fig.transFigure, facecolor=color, edgecolor='none', zorder=0))


def no_data(ax)->None:
    ax.text(0.5, 0.5, 'Aucune donnée', ha='center', va='center', fontsize=14, color=MUTED, transform=ax.transAxes)
    ax.set_xticks([])
    ax.set_yticks([])


def barh(ax, items:list, color:str, title:str, xlabel:str)->None:
    """barres horizontales (label, total), la plus grande en haut, valeur au bout de chaque barre"""
    style(ax, title)
    ax.grid(axis='y', visible=False)
    if not items:
        no_data(ax)
        return
    labels = [str(label) for label, _ in items]
    values = [int(value) for _, value in items]
    colors = [to_rgba(color, 1 - 0.6 * i / max(len(values) - 1, 1)) for i in range(len(values))]
    ax.barh(labels, values, color=colors, height=0.6)
    ax.set_ylim(max(len(values), 8) - 0.5, -0.5)
    for i, value in enumerate(values):
        ax.text(value, i, f'  {value}', va='center', fontsize=8.5, color=TEXT,
                fontweight='bold' if i == 0 else 'normal')
    ax.set_xlim(0, max(values) * 1.15)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlabel(xlabel, color=MUTED, fontsize=9)


def draw(ax, items:list, color:str, title:str, xlabel:str)->None:
    """dessine un graphique ; une erreur matplotlib est enregistrée sans fermer le dashboard"""
    card(ax.figure, ax, color)
    try:
        barh(ax, items, color, title, xlabel)
    except Exception as e:
        logger.error(f'Erreur matplotlib ({title}) : {e}')
        ax.cla()
        style(ax, title)
        no_data(ax)


def kpi(fig, x:float, value:str, name:str, color:str)->None:
    """carte indicateur : pastille de couleur, libellé, grande valeur"""
    fig.patches.append(FancyBboxPatch((x, 0.765), 0.205, 0.105, boxstyle='round,pad=0,rounding_size=0.012',
                                      transform=fig.transFigure, facecolor=PANEL, edgecolor=BORDER, linewidth=1))
    fig.patches.append(FancyBboxPatch((x, 0.765), 0.006, 0.105, boxstyle='round,pad=0',
                                      transform=fig.transFigure, facecolor=color, edgecolor='none'))
    fig.text(x + 0.02, 0.835, name.upper(), color=MUTED, fontsize=9.5, fontweight='bold')
    fig.text(x + 0.02, 0.783, value, color=TEXT, fontsize=26, fontweight='bold')


def plot_dashboard(data:dict)->None:
    total, ips, failed, rate = data['summary'][0] if data['summary'] else (0, 0, 0, None)

    fig = plt.figure(figsize=(16, 9), facecolor=BG)
    fig.canvas.manager.set_window_title('Log Analyser - Dashboard SSH')
    fig.text(0.035, 0.935, 'Log Analyser', color=TEXT, fontsize=22, fontweight='bold')
    fig.text(0.035, 0.905, 'Dashboard SSH  ·  tentatives de connexion extraites de auth.log  ·  PostgreSQL',
             color=MUTED, fontsize=10.5)
    fig.text(0.965, 0.935, datetime.now().strftime('%d/%m/%Y %H:%M'), color=MUTED, fontsize=10, ha='right')
    kpi(fig, 0.035, f'{total:,}'.replace(',', ' '), 'Tentatives', CYAN)
    kpi(fig, 0.2783, f'{ips:,}'.replace(',', ' '), 'IP uniques', GREEN)
    kpi(fig, 0.5216, f'{failed or 0:,}'.replace(',', ' '), 'Tentatives échouées', RED)
    kpi(fig, 0.765, f'{rate} %' if rate is not None else '—', "Taux d'échec", ORANGE)

    grid = GridSpec(1, 3, figure=fig, left=0.11, right=0.955, top=0.635, bottom=0.10, wspace=0.5)

    countries = [(COUNTRY_NAMES.get(code, code), total) for code, total in data['failed_by_country']]
    draw(fig.add_subplot(grid[0, 0]), countries, CYAN, 'Tentatives échouées par pays', 'Échecs')
    draw(fig.add_subplot(grid[0, 1]), data['success_by_user'], GREEN, 'Tentatives réussies par user', 'Réussites')
    draw(fig.add_subplot(grid[0, 2]), data['invalid_users'], PINK, 'Échecs avec "invalid user" (top 15)', 'Échecs')

    try:
        fig.canvas.manager.window.state('zoomed')
    except Exception:
        pass
    plt.show()


def run()->None:
    try:
        plot_dashboard(services.load_data())
    except Exception as e:
        logger.exception(f'Erreur du dashboard : {e}')


if __name__ == '__main__':
    run()
