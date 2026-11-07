import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
from typing import Callable, List, Optional
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
sys.path.append(str(Path(__file__).resolve().parent.parent))#racine du projet : log_analysis
from storage import store
from serving import stats

"""
    Dashboard (tkinter + matplotlib)
    in : logs from storage (MySQL ou csv)
    out : interface : pages avec stats, graphiques, données, recherche ip, base de données
"""

# ---------- thème ----------
FONT = 'Segoe UI'
ICON_FONT = 'Segoe UI Symbol'
PAGE = '#f5f6f8'
CARD = '#ffffff'
BORDER = '#e4e6eb'
INK = '#0b0b0b'
INK_2 = '#52514e'
MUTED = '#898781'
GRID = '#e1e0d9'
BASELINE = '#c3c2b7'
ACCENT = '#2a78d6'
ACCENT_DARK = '#1c5cab'
SIDEBAR = '#111827'
SIDEBAR_HOVER = '#1f2937'
SIDEBAR_TEXT = '#9ca3af'
SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']
STATUS_COLORS = {'Failed': '#d03b3b', 'Invalid': '#ec835a', 'Success': '#0ca30c'}
STATUS_LABELS = {'Failed': 'Échecs', 'Invalid': 'Utilisateurs invalides', 'Success': 'Réussies'}
SEQUENTIAL = LinearSegmentedColormap.from_list('blue', ['#f3f7fd', '#cde2fb', '#86b6ef', '#3987e5', '#1c5cab', '#0d366b'])
GOOD, WARNING = '#0ca30c', '#d97706'

PAD = 40     #marge de la page
GAP = 24     #espace entre les cartes
PAGE_SIZE = 100

PAGES = [
    ('overview', '⌂', "Vue d'ensemble", 'Synthèse des tentatives de connexion SSH'),
    ('countries', '◉', 'Pays', 'Origine géographique des attaques (ipinfo)'),
    ('timeline', '◷', 'Chronologie', 'Évolution des tentatives par jour et par heure'),
    ('attackers', '⚠', 'Attaquants', 'IP et comptes les plus ciblés'),
    ('data', '☰', 'Données', 'Consulter, filtrer, importer et exporter les logs'),
    ('ip', '⌕', 'Recherche IP', 'Informations ipinfo et activité d\'une adresse IP'),
    ('database', '⛁', 'Base de données', 'Connexion MySQL et synchronisation'),
]

#état de l'application
app = {'root': None, 'logs': [], 'source': '', 'page': 'overview', 'nav': {}, 'canvas': None,
       'body': None, 'title': None, 'subtitle': None, 'status': None, 'figures': [], 'ip': ''}

# ---------- outils ----------

def fmt(n:float)->str:
    return f'{n:,.0f}'.replace(',', ' ')

def pct(part:float, total:float)->str:
    return f'{part / total * 100:.1f} %'.replace('.', ',') if total else '0 %'

def label(parent, text:str, size:int=10, color:str=INK, bold:bool=False, bg:str=CARD, **kwargs)->tk.Label:
    return tk.Label(parent, text=text, font=(FONT, size, 'bold' if bold else 'normal'), fg=color, bg=bg, **kwargs)

def button(parent, text:str, command:Callable, primary:bool=False)->ttk.Button:
    return ttk.Button(parent, text=text, command=command, style='Primary.TButton' if primary else 'Ghost.TButton', cursor='hand2')

def grid_columns(frame:tk.Frame, n:int)->None:
    for i in range(n):
        frame.columnconfigure(i, weight=1, uniform='col')

def row(parent, columns:int)->tk.Frame:
    frame = tk.Frame(parent, bg=PAGE)
    frame.pack(fill='x', pady=(0, GAP))
    grid_columns(frame, columns)
    return frame

def card(parent, title:str='', subtitle:str='', column:int=0, span:int=1, columns:int=1)->tk.Frame:
    outer = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightcolor=BORDER, highlightthickness=1)
    left = 0 if column == 0 else GAP // 2
    right = 0 if column + span >= columns else GAP // 2
    outer.grid(row=0, column=column, columnspan=span, sticky='nsew', padx=(left, right))
    if title:
        label(outer, title, 12, bold=True).pack(anchor='w', padx=24, pady=(20, 0))
    if subtitle:
        label(outer, subtitle, 9, MUTED).pack(anchor='w', padx=24, pady=(2, 0))
    body = tk.Frame(outer, bg=CARD)
    body.pack(fill='both', expand=True, padx=24, pady=(12, 20))
    return body

def kpi(parent, column:int, columns:int, title:str, value:str, caption:str='', color:Optional[str]=None)->None:
    outer = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightcolor=BORDER, highlightthickness=1)
    left = 0 if column == 0 else GAP // 2
    right = 0 if column == columns - 1 else GAP // 2
    outer.grid(row=0, column=column, sticky='nsew', padx=(left, right))
    tk.Frame(outer, bg=color or BORDER, height=4).pack(fill='x')
    body = tk.Frame(outer, bg=CARD)
    body.pack(fill='both', expand=True, padx=24, pady=(18, 20))
    label(body, title.upper(), 9, MUTED, bold=True).pack(anchor='w')
    label(body, value, 26, bold=True).pack(anchor='w', pady=(6, 2))
    label(body, caption, 9, INK_2).pack(anchor='w')

def kpi_row(parent, items:List[tuple])->None:
    frame = row(parent, len(items))
    for i, item in enumerate(items):
        kpi(frame, i, len(items), *item)

def empty_state(parent, text:str)->None:
    body = card(row(parent, 1))
    label(body, 'Aucune donnée', 14, bold=True).pack(pady=(40, 6))
    label(body, text, 10, INK_2).pack()
    button(body, 'Importer les logs', start_import, primary=True).pack(pady=(20, 40))

# ---------- graphiques ----------

def style_axes(ax, grid_axis:str='y')->None:
    ax.set_facecolor(CARD)
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color(BASELINE)
    ax.tick_params(colors=MUTED, labelsize=9, length=0, pad=6)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)

def chart(parent, draw:Callable, height:float=3.4, grid_axis:str='y'):
    fig = Figure(figsize=(4, height), dpi=100, facecolor=CARD, layout='constrained')
    ax = fig.add_subplot(111)
    style_axes(ax, grid_axis)
    canvas = FigureCanvasTkAgg(fig, master=parent)
    draw(ax, canvas)
    widget = canvas.get_tk_widget()
    widget.configure(bg=CARD, highlightthickness=0)
    widget.pack(fill='both', expand=True)
    app['figures'].append(fig)
    return ax

def tooltip(canvas, ax, find:Callable, crosshair:bool=False)->None:
    """find(event) -> (x, y, texte) ou None"""
    annot = ax.annotate('', xy=(0, 0), xytext=(14, 14), textcoords='offset points', fontsize=9, color=INK, zorder=10,
                        bbox=dict(boxstyle='round,pad=0.6', fc=CARD, ec=BORDER, lw=1))
    annot.set_visible(False)
    line = ax.axvline(0, color=BASELINE, lw=1, zorder=1, visible=False) if crosshair else None

    def on_move(event):
        hit = find(event) if event.inaxes == ax else None
        if hit:
            x, y, text = hit
            right = event.x > ax.figure.bbox.width * 0.65
            annot.xy = (x, y)
            annot.xyann = (-14 if right else 14, 14)
            annot.set_ha('right' if right else 'left')
            annot.set_text(text)
            annot.set_visible(True)
            if line:
                line.set_xdata([x, x])
                line.set_visible(True)
            canvas.draw_idle()
        elif annot.get_visible():
            annot.set_visible(False)
            if line:
                line.set_visible(False)
            canvas.draw_idle()
    canvas.mpl_connect('motion_notify_event', on_move)

def bar_finder(bars:list, texts:List[str], horizontal:bool=False)->Callable:
    def find(event):
        for bar, text in zip(bars, texts):
            if bar.contains(event)[0]:
                if horizontal:
                    return bar.get_x() + bar.get_width(), bar.get_y() + bar.get_height() / 2, text
                return bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height(), text
    return find

def sparse_ticks(ax, labels:List[str], every:int=0)->None:
    every = every or max(1, len(labels) // 10)
    ax.set_xticks(range(0, len(labels), every))
    ax.set_xticklabels(labels[::every])

def draw_line(labels:List[str], values:List[int], color:str, name:str)->Callable:
    def draw(ax, canvas):
        x = range(len(values))
        ax.plot(x, values, color=color, lw=2)
        ax.fill_between(x, values, color=color, alpha=0.08, lw=0)
        ax.set_xlim(-0.5, len(values) - 0.5)
        ax.set_ylim(bottom=0)
        sparse_ticks(ax, labels)

        def find(event):
            i = min(max(round(event.xdata), 0), len(values) - 1)
            return i, values[i], f'{labels[i]}\n{name} : {fmt(values[i])}'
        tooltip(canvas, ax, find, crosshair=True)
    return draw

def draw_barh(items:List[tuple], color:str, name:str)->Callable:
    """items : (label, valeur)"""
    def draw(ax, canvas):
        labels = [str(item[0]) for item in items]
        values = [item[1] for item in items]
        bars = ax.barh(range(len(items)), values, color=color, height=0.62, edgecolor=CARD, linewidth=1)
        ax.set_yticks(range(len(items)))
        ax.set_yticklabels(labels, color=INK_2)
        ax.invert_yaxis()
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(True)
        ax.spines['left'].set_color(BASELINE)
        tooltip(canvas, ax, bar_finder(bars, [f'{l}\n{name} : {fmt(v)}' for l, v in zip(labels, values)], horizontal=True))
    return draw

def draw_status_by_day(logs:List[dict])->Callable:
    def draw(ax, canvas):
        bottom = None
        bars, texts = [], []
        for status in stats.STATUSES:
            labels, values = stats.per_day(logs, status)
            bottom = bottom or [0] * len(values)
            group = ax.bar(range(len(values)), values, bottom=bottom, color=STATUS_COLORS[status], width=0.72,
                           edgecolor=CARD, linewidth=1, label=STATUS_LABELS[status])
            bars += list(group)
            texts += [f'{l}\n{STATUS_LABELS[status]} : {fmt(v)}' for l, v in zip(labels, values)]
            bottom = [b + v for b, v in zip(bottom, values)]
        sparse_ticks(ax, labels)
        ax.legend(loc='upper left', frameon=False, fontsize=9, ncols=3, labelcolor=INK_2, bbox_to_anchor=(0, 1.12))
        tooltip(canvas, ax, bar_finder(bars, texts))
    return draw

def draw_hours(values:List[int])->Callable:
    def draw(ax, canvas):
        bars = ax.bar(range(24), values, color=ACCENT, width=0.72, edgecolor=CARD, linewidth=1)
        ax.set_xticks(range(0, 24, 2))
        ax.set_xticklabels([f'{h}h' for h in range(0, 24, 2)])
        tooltip(canvas, ax, bar_finder(bars, [f'{h}h – {h + 1}h\nÉchecs : {fmt(v)}' for h, v in enumerate(values)]))
    return draw

def draw_heatmap(days:List[str], matrix:List[List[int]])->Callable:
    def draw(ax, canvas):
        image = ax.imshow(matrix, aspect='auto', cmap=SEQUENTIAL, interpolation='nearest')
        ax.grid(False)
        ax.spines['bottom'].set_visible(False)
        ax.set_xticks(range(0, 24, 2))
        ax.set_xticklabels([f'{h}h' for h in range(0, 24, 2)])
        ax.set_yticks(range(len(days)))
        ax.set_yticklabels(days, fontsize=8)
        bar = ax.figure.colorbar(image, ax=ax, fraction=0.025, pad=0.01)
        bar.outline.set_visible(False)
        bar.ax.tick_params(colors=MUTED, labelsize=8, length=0)

        def find(event):
            col, line = round(event.xdata), round(event.ydata)
            if 0 <= line < len(days) and 0 <= col < 24:
                return col, line, f'{days[line]} · {col}h – {col + 1}h\nÉchecs : {fmt(matrix[line][col])}'
        tooltip(canvas, ax, find)
    return draw

def draw_country_month(logs:List[dict], n:int=10)->Callable:
    def draw(ax, canvas):
        failed = stats.by_status(logs, 'Failed')
        countries = [c for c, _ in stats.top_countries(logs, n)]
        months = sorted({log['month'] for log in failed}, key=stats.MONTHS.index)
        counts = {}
        for log in failed:
            key = (stats.country(log), log['month'])
            counts[key] = counts.get(key, 0) + 1
        width = 0.72 / max(len(months), 1)
        bars, texts = [], []
        for i, month in enumerate(months[:len(SERIES)]):
            x = [j + (i - (len(months) - 1) / 2) * width for j in range(len(countries))]
            values = [counts.get((c, month), 0) for c in countries]
            group = ax.bar(x, values, width, color=SERIES[i], edgecolor=CARD, linewidth=1, label=stats.MONTHS_FR[month])
            bars += list(group)
            texts += [f'{c} · {stats.MONTHS_FR[month]}\nÉchecs : {fmt(v)}' for c, v in zip(countries, values)]
        ax.set_xticks(range(len(countries)))
        ax.set_xticklabels(countries)
        ax.legend(loc='upper right', frameon=False, fontsize=9, labelcolor=INK_2)
        tooltip(canvas, ax, bar_finder(bars, texts))
    return draw

# ---------- tableaux ----------

def table(parent, columns:List[tuple], rows:List[tuple], height:int=10, on_open:Optional[Callable]=None)->ttk.Treeview:
    """columns : (titre, largeur, alignement)"""
    frame = tk.Frame(parent, bg=CARD)
    frame.pack(fill='both', expand=True)
    tree = ttk.Treeview(frame, columns=[str(i) for i in range(len(columns))], show='headings', height=height)
    for i, (title, width, anchor) in enumerate(columns):
        tree.heading(str(i), text=title, anchor=anchor)
        tree.column(str(i), width=width, anchor=anchor, stretch=True)
    scroll = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side='left', fill='both', expand=True)
    scroll.pack(side='right', fill='y')
    tree.tag_configure('odd', background='#fafafb')
    fill_table(tree, rows)
    if on_open:
        tree.bind('<Double-1>', lambda e: tree.selection() and on_open(tree.item(tree.selection()[0], 'values')))
    return tree

def fill_table(tree:ttk.Treeview, rows:List[tuple])->None:
    tree.delete(*tree.get_children())
    for i, values in enumerate(rows):
        tree.insert('', 'end', values=values, tags=('odd',) if i % 2 else ())

def open_ip(ip:str)->None:
    app['ip'] = ip
    show_page('ip')

# ---------- pages ----------

def page_overview(body:tk.Frame)->None:
    logs = app['logs']
    k = stats.kpis(logs)
    kpi_row(body, [
        ('Tentatives', fmt(k['total']), f"sur {k['days']} jours", ACCENT),
        ('Échecs', fmt(k['failed']), f"{pct(k['failed'], k['total'])} des tentatives", STATUS_COLORS['Failed']),
        ('Utilisateurs invalides', fmt(k['invalid']), f"{pct(k['invalid'], k['total'])} des tentatives", STATUS_COLORS['Invalid']),
        ('Connexions réussies', fmt(k['success']), f"{pct(k['success'], k['total'])} des tentatives", STATUS_COLORS['Success']),
    ])
    kpi_row(body, [
        ('IP uniques', fmt(k['ips']), 'adresses distinctes'),
        ('Pays', fmt(k['countries']), f"n°1 : {k['top_country'][0]} ({fmt(k['top_country'][1])} échecs)"),
        ('Échecs / jour', fmt(k['avg_per_day']), 'en moyenne'),
        ('Jour de pic', k['peak_day'][0], f"{fmt(k['peak_day'][1])} échecs"),
    ])
    labels, values = stats.per_day(logs, 'Failed')
    chart(card(row(body, 1), 'Échecs par jour', 'Survolez la courbe pour voir le détail'),
          draw_line(labels, values, STATUS_COLORS['Failed'], 'Échecs'), height=3.6)

    line = row(body, 2)
    chart(card(line, 'Top 10 pays', 'Nombre d\'échecs par pays d\'origine', 0, 1, 2),
          draw_barh(stats.top_countries(logs, 10), ACCENT, 'Échecs'), height=3.8, grid_axis='x')
    split = stats.status_split(logs)
    def draw_split(ax, canvas):
        bars = ax.barh(range(3), [v for _, v in split], color=[STATUS_COLORS[s] for s, _ in split], height=0.55,
                       edgecolor=CARD, linewidth=1)
        ax.set_yticks(range(3))
        ax.set_yticklabels([STATUS_LABELS[s] for s, _ in split], color=INK_2)
        ax.invert_yaxis()
        ax.spines['bottom'].set_visible(False)
        for bar, (_, v) in zip(bars, split):
            ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2, f'  {fmt(v)} · {pct(v, k["total"])}',
                    va='center', fontsize=9, color=INK_2)
        ax.set_xlim(0, max(v for _, v in split) * 1.35)
        ax.set_xticks([])
        ax.grid(False)
    chart(card(line, 'Répartition par statut', 'Part de chaque type de tentative', 1, 1, 2), draw_split, height=3.8, grid_axis='x')

def page_countries(body:tk.Frame)->None:
    logs = app['logs']
    k = stats.kpis(logs)
    top = stats.top_countries(logs, 5)
    unknown = sum(1 for log in stats.by_status(logs, 'Failed') if not log['country'])
    kpi_row(body, [
        ('Pays d\'origine', fmt(k['countries']), 'pays distincts', ACCENT),
        ('Pays n°1', k['top_country'][0], f"{fmt(k['top_country'][1])} échecs", STATUS_COLORS['Failed']),
        ('Part du top 5', pct(sum(v for _, v in top), k['failed']), ', '.join(c for c, _ in top)),
        ('Non localisés', fmt(unknown), 'échecs sans pays (ipinfo)'),
    ])
    chart(card(row(body, 1), 'Top 15 pays', 'Échecs par pays d\'origine'),
          draw_barh(stats.top_countries(logs, 15), ACCENT, 'Échecs'), height=5.2, grid_axis='x')
    chart(card(row(body, 1), 'Échecs par pays et par mois', 'Top 10 pays, une couleur par mois'),
          draw_country_month(logs), height=3.6)
    rows = [(c, fmt(f), fmt(i), fmt(s), fmt(n)) for c, f, i, s, n in stats.countries_table(logs)]
    table(card(row(body, 1), 'Tous les pays', f'{len(rows)} pays · triés par nombre d\'échecs'),
          [('Pays', 160, 'w'), ('Échecs', 120, 'e'), ('Invalides', 120, 'e'), ('Réussies', 120, 'e'), ('IP uniques', 120, 'e')],
          rows, height=12)

def page_timeline(body:tk.Frame)->None:
    logs = app['logs']
    k = stats.kpis(logs)
    hours = stats.per_hour(logs)
    peak_hour = hours.index(max(hours))
    kpi_row(body, [
        ('Période', f"{k['days']} jours", ' → '.join([stats.per_day(logs)[0][0], stats.per_day(logs)[0][-1]]), ACCENT),
        ('Jour de pic', k['peak_day'][0], f"{fmt(k['peak_day'][1])} échecs", STATUS_COLORS['Failed']),
        ('Heure de pic', f'{peak_hour}h – {peak_hour + 1}h', f'{fmt(max(hours))} échecs sur la période'),
        ('Moyenne', fmt(k['avg_per_day']), 'échecs par jour'),
    ])
    chart(card(row(body, 1), 'Tentatives par jour et par statut', 'Barres empilées : échecs, utilisateurs invalides, réussies'),
          draw_status_by_day(logs), height=3.8)
    chart(card(row(body, 1), 'Échecs par heure de la journée', 'Total sur toute la période'),
          draw_hours(hours), height=3.2)
    days, matrix = stats.heatmap(logs)
    chart(card(row(body, 1), 'Carte de chaleur jour × heure', 'Plus la case est foncée, plus il y a d\'échecs'),
          draw_heatmap(days, matrix), height=max(4.0, len(days) * 0.22))

def page_attackers(body:tk.Frame)->None:
    logs = app['logs']
    ips = stats.top_ips(logs, 25)
    users = stats.top_users(logs, 10)
    kpi_row(body, [
        ('IP n°1', ips[0][0] if ips else '-', f'{fmt(ips[0][2])} échecs · {ips[0][1]}' if ips else '', STATUS_COLORS['Failed']),
        ('Compte le plus visé', users[0][0] if users else '-', f'{fmt(users[0][1])} tentatives' if users else '', STATUS_COLORS['Invalid']),
        ('Comptes testés', fmt(stats.kpis(logs)['users']), 'noms d\'utilisateur distincts'),
    ])
    line = row(body, 2)
    chart(card(line, 'Top 10 IP', 'Échecs par adresse IP', 0, 1, 2),
          draw_barh([(f'{ip} ({c})', v) for ip, c, v in ips[:10]], STATUS_COLORS['Failed'], 'Échecs'), height=4.2, grid_axis='x')
    chart(card(line, 'Top 10 comptes ciblés', 'Échecs + utilisateurs invalides', 1, 1, 2),
          draw_barh(users, ACCENT, 'Tentatives'), height=4.2, grid_axis='x')
    table(card(row(body, 1), 'Top 25 IP', 'Double-cliquez sur une ligne pour ouvrir la fiche de l\'IP'),
          [('#', 50, 'center'), ('Adresse IP', 200, 'w'), ('Pays', 120, 'w'), ('Échecs', 120, 'e')],
          [(i + 1, ip, c, fmt(v)) for i, (ip, c, v) in enumerate(ips)], height=12, on_open=lambda values: open_ip(values[1]))

def page_data(body:tk.Frame)->None:
    logs = app['logs']
    state = {'page': 0, 'rows': logs}
    tools = card(row(body, 1))
    filters = tk.Frame(tools, bg=CARD)
    filters.pack(fill='x')
    search = tk.StringVar()
    status = tk.StringVar(value='Tous')
    country = tk.StringVar(value='Tous')

    def field(text:str, widget_factory:Callable)->None:
        box = tk.Frame(filters, bg=CARD)
        box.pack(side='left', padx=(0, 16))
        label(box, text, 9, MUTED, bold=True).pack(anchor='w', pady=(0, 4))
        widget_factory(box).pack(anchor='w')

    field('RECHERCHE (IP, COMPTE, MESSAGE)', lambda p: ttk.Entry(p, textvariable=search, width=34, font=(FONT, 10)))
    field('STATUT', lambda p: ttk.Combobox(p, textvariable=status, state='readonly', width=22, font=(FONT, 10),
                                           values=['Tous'] + [STATUS_LABELS[s] for s in stats.STATUSES]))
    field('PAYS', lambda p: ttk.Combobox(p, textvariable=country, state='readonly', width=12, font=(FONT, 10),
                                         values=['Tous'] + sorted({stats.country(log) for log in logs})))
    actions = tk.Frame(filters, bg=CARD)
    actions.pack(side='right', anchor='s')
    button(actions, 'Exporter CSV', lambda: export(state['rows'])).pack(side='left', padx=(0, 8))
    button(actions, 'Importer les logs', start_import, primary=True).pack(side='left')

    result = card(row(body, 1))
    info = label(result, '', 10, INK_2)
    info.pack(anchor='w', pady=(0, 12))
    tree = table(result, [('Date', 90, 'w'), ('Heure', 80, 'w'), ('Adresse IP', 140, 'w'), ('Pays', 70, 'center'),
                          ('Compte', 120, 'w'), ('Statut', 150, 'w'), ('Message', 480, 'w')], [], height=PAGE_SIZE // 4,
                 on_open=lambda values: open_ip(values[2]))
    pager = tk.Frame(result, bg=CARD)
    pager.pack(fill='x', pady=(12, 0))
    previous = button(pager, '← Précédent', lambda: move(-1))
    previous.pack(side='left')
    page_label = label(pager, '', 10, INK_2)
    page_label.pack(side='left', padx=16)
    following = button(pager, 'Suivant →', lambda: move(1))
    following.pack(side='left')

    def render()->None:
        pages = max(1, -(-len(state['rows']) // PAGE_SIZE))
        start = state['page'] * PAGE_SIZE
        chunk = state['rows'][start:start + PAGE_SIZE]
        fill_table(tree, [(stats.day_label(stats.day_key(log)), log['time'], log['ip'], log['country'] or '—', log['user'],
                           STATUS_LABELS[log['status']], log['message']) for log in chunk])
        info.configure(text=f"{fmt(len(state['rows']))} lignes sur {fmt(len(logs))} · double-cliquez pour ouvrir la fiche IP")
        page_label.configure(text=f"Page {state['page'] + 1} / {pages}")
        previous.state(['!disabled'] if state['page'] > 0 else ['disabled'])
        following.state(['!disabled'] if state['page'] < pages - 1 else ['disabled'])

    def move(step:int)->None:
        state['page'] += step
        render()

    def apply(*_)->None:
        text = search.get().strip().lower()
        statuses = {v: k for k, v in STATUS_LABELS.items()}
        state['rows'] = [log for log in logs
                         if (status.get() == 'Tous' or log['status'] == statuses[status.get()])
                         and (country.get() == 'Tous' or stats.country(log) == country.get())
                         and (not text or text in log['ip'] or text in log['user'].lower() or text in log['message'].lower())]
        state['page'] = 0
        render()

    for var in (search, status, country):
        var.trace_add('write', apply)
    render()

def page_ip(body:tk.Frame)->None:
    bar = card(row(body, 1))
    form = tk.Frame(bar, bg=CARD)
    form.pack(fill='x')
    label(form, 'ADRESSE IP', 9, MUTED, bold=True).pack(anchor='w', pady=(0, 4))
    ip_var = tk.StringVar(value=app['ip'] or (stats.top_ips(app['logs'], 1) or [('',)])[0][0])
    entry = ttk.Entry(form, textvariable=ip_var, width=30, font=(FONT, 11))
    entry.pack(side='left')
    button(form, 'Rechercher', lambda: lookup(), primary=True).pack(side='left', padx=12)
    message = label(form, '', 10, MUTED)
    message.pack(side='left', padx=8)
    results = tk.Frame(body, bg=PAGE)
    results.pack(fill='x')

    def lookup()->None:
        ip = ip_var.get().strip()
        if not ip:
            return
        app['ip'] = ip
        message.configure(text='Recherche en cours…', fg=MUTED)
        outcome = {}
        threading.Thread(target=lambda: outcome.update(info=store.get_ip_info(ip)), daemon=True).start()

        def wait()->None:
            if 'info' not in outcome:
                app['root'].after(100, wait)
                return
            info = outcome['info']
            if app['source'] == 'MySQL' and info.get('country'):
                store.save_ip_mysql(info)
            message.configure(text='' if info.get('country') else 'ipinfo n\'a rien renvoyé (réseau ou limite atteinte)',
                              fg=WARNING)
            show_ip(results, ip, info)
        wait()

    entry.bind('<Return>', lambda e: lookup())
    if ip_var.get():
        lookup()

def show_ip(parent:tk.Frame, ip:str, info:dict)->None:
    for child in parent.winfo_children():
        child.destroy()
    activity = stats.ip_activity(app['logs'], ip)
    statuses = activity.get('statuses', {})
    kpi_row(parent, [
        ('Tentatives', fmt(activity.get('total', 0)), 'dans les logs', ACCENT),
        ('Échecs', fmt(statuses.get('Failed', 0)), '', STATUS_COLORS['Failed']),
        ('Utilisateurs invalides', fmt(statuses.get('Invalid', 0)), '', STATUS_COLORS['Invalid']),
        ('Réussies', fmt(statuses.get('Success', 0)), '', STATUS_COLORS['Success']),
    ])
    line = row(parent, 2)
    details = card(line, 'Fiche ipinfo', ip, 0, 1, 2)
    fields = [('Pays', info.get('country')), ('Ville', info.get('city')), ('Région', info.get('region')),
              ('Organisation', info.get('org')), ('Nom d\'hôte', info.get('hostname')), ('Coordonnées', info.get('loc')),
              ('Fuseau horaire', info.get('timezone')), ('Première activité', activity.get('first')),
              ('Dernière activité', activity.get('last'))]
    details.columnconfigure(1, weight=1)
    for i, (name, value) in enumerate(fields):
        label(details, name, 10, MUTED).grid(row=i, column=0, sticky='w', pady=6, padx=(0, 24))
        label(details, value or '—', 10, INK, anchor='w', wraplength=420, justify='left').grid(row=i, column=1, sticky='w', pady=6)
    users = card(line, 'Comptes testés', 'Par cette adresse IP', 1, 1, 2)
    if activity.get('users'):
        chart(users, draw_barh(activity['users'], ACCENT, 'Tentatives'), height=3.6, grid_axis='x')
    else:
        label(users, 'Aucun compte dans les logs', 10, MUTED).pack(anchor='w')
    if activity:
        labels, values = activity['per_day']
        chart(card(row(parent, 1), 'Échecs par jour', f'Activité de {ip}'),
              draw_line(labels, values, STATUS_COLORS['Failed'], 'Échecs'), height=3.0)

def page_database(body:tk.Frame)->None:
    config = store.load_config()
    line = row(body, 2)
    form = card(line, 'Connexion MySQL', 'Paramètres enregistrés dans storage/mysql_config.json', 0, 1, 2)
    variables = {}
    for i, (key, name) in enumerate([('host', 'Hôte'), ('port', 'Port'), ('user', 'Utilisateur'),
                                     ('password', 'Mot de passe'), ('database', 'Base de données')]):
        label(form, name.upper(), 9, MUTED, bold=True).grid(row=i * 2, column=0, sticky='w', pady=(8 if i else 0, 4))
        variables[key] = tk.StringVar(value=str(config[key]))
        ttk.Entry(form, textvariable=variables[key], width=40, font=(FONT, 10),
                  show='•' if key == 'password' else '').grid(row=i * 2 + 1, column=0, sticky='w')
    status = label(form, '', 10, MUTED, wraplength=420, justify='left')
    actions = tk.Frame(form, bg=CARD)
    actions.grid(row=11, column=0, sticky='w', pady=(20, 8))
    status.grid(row=12, column=0, sticky='w')

    def current()->dict:
        return {key: var.get().strip() for key, var in variables.items()} | {'port': int(variables['port'].get() or 3306)}

    def report(ok:bool, text:str)->None:
        status.configure(text=('✔ ' if ok else '✖ ') + text, fg=GOOD if ok else STATUS_COLORS['Failed'])

    def test()->None:
        report(*store.test_mysql(current()))

    def save()->None:
        store.save_config(current())
        ok, text = store.test_mysql(current())
        report(ok, 'Paramètres enregistrés. ' + text)

    def init()->None:
        store.save_config(current())
        report(store.init_mysql(current()), f"Base « {current()['database']} » et tables auth_logs, ip_info prêtes")

    def sync()->None:
        store.save_config(current())
        if store.save_mysql(app['logs']):
            app['source'] = 'MySQL'
            report(True, f"{fmt(len(app['logs']))} lignes envoyées dans MySQL")
            update_status()
        else:
            report(False, 'Synchronisation impossible : vérifiez la connexion')

    button(actions, 'Tester', test).pack(side='left', padx=(0, 8))
    button(actions, 'Enregistrer', save).pack(side='left', padx=(0, 8))
    button(actions, 'Créer la base', init).pack(side='left', padx=(0, 8))
    button(actions, 'Synchroniser', sync, primary=True).pack(side='left')

    steps = card(line, 'Mise en place', 'À faire une seule fois', 1, 1, 2)
    for i, text in enumerate([
        'Démarrez MySQL (XAMPP : bouton « Start » sur la ligne MySQL).',
        'Renseignez les paramètres. XAMPP par défaut : root, sans mot de passe, port 3306.',
        'Cliquez sur « Tester », puis « Créer la base » : la base et les tables auth_logs et ip_info sont créées.',
        'Cliquez sur « Synchroniser » pour envoyer les logs actuels, ou « Importer les logs » pour tout recalculer.',
        'Au prochain lancement, le dashboard lit directement MySQL (le CSV reste en secours).',
    ]):
        step = tk.Frame(steps, bg=CARD)
        step.pack(fill='x', pady=8)
        label(step, str(i + 1), 10, CARD, bold=True, bg=ACCENT, width=3).pack(side='left', anchor='n', padx=(0, 14))
        label(step, text, 10, INK_2, wraplength=440, justify='left').pack(side='left', anchor='w')

    kpi_row(body, [
        ('Source active', app['source'] or '—', 'MySQL si disponible, sinon CSV', GOOD if app['source'] == 'MySQL' else WARNING),
        ('Lignes chargées', fmt(len(app['logs'])), 'table auth_logs'),
        ('IP en cache', fmt(len(store.ip_cache)), 'table ip_info'),
    ])

PAGE_BUILDERS = {'overview': page_overview, 'countries': page_countries, 'timeline': page_timeline,
                 'attackers': page_attackers, 'data': page_data, 'ip': page_ip, 'database': page_database}

# ---------- navigation ----------

def show_page(name:str)->None:
    app['page'] = name
    for key, (item, parts) in app['nav'].items():
        active = key == name
        for widget in parts:
            widget.configure(bg=SIDEBAR_HOVER if active else SIDEBAR, fg='#ffffff' if active else SIDEBAR_TEXT)
        item.configure(bg=SIDEBAR_HOVER if active else SIDEBAR)
        item.marker.configure(bg=ACCENT if active else SIDEBAR)
    _, _, title, subtitle = next(page for page in PAGES if page[0] == name)
    app['title'].configure(text=title)
    app['subtitle'].configure(text=subtitle)

    for fig in app['figures']:
        fig.clear()
    app['figures'] = []
    for child in app['body'].winfo_children():
        child.destroy()
    body = scrollable(app['body'])
    content = tk.Frame(body, bg=PAGE)
    content.pack(fill='both', expand=True, padx=PAD, pady=(GAP, PAD))
    if not app['logs'] and name not in ('database', 'data'):
        empty_state(content, 'Importez les fichiers de data/ ou connectez MySQL dans « Base de données ».')
    else:
        PAGE_BUILDERS[name](content)
    app['canvas'].yview_moveto(0)

def scrollable(parent:tk.Frame)->tk.Frame:
    canvas = tk.Canvas(parent, bg=PAGE, highlightthickness=0)
    scroll = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
    inner = tk.Frame(canvas, bg=PAGE)
    window = canvas.create_window((0, 0), window=inner, anchor='nw')
    inner.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
    canvas.bind('<Configure>', lambda e: canvas.itemconfigure(window, width=e.width))
    canvas.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right', fill='y')
    canvas.pack(side='left', fill='both', expand=True)
    app['canvas'] = canvas
    return inner

def on_wheel(event)->None:
    widget = event.widget
    if isinstance(widget, str) or isinstance(widget, (ttk.Treeview, ttk.Combobox)):
        return
    canvas = app['canvas']
    if canvas and canvas.winfo_exists() and canvas.yview() != (0.0, 1.0):
        canvas.yview_scroll(int(-event.delta / 120) * 3, 'units')

def nav_item(parent, key:str, icon:str, text:str)->None:
    item = tk.Frame(parent, bg=SIDEBAR, cursor='hand2')
    item.pack(fill='x', padx=12, pady=2)
    item.marker = tk.Frame(item, bg=SIDEBAR, width=4)
    item.marker.pack(side='left', fill='y')
    icon_label = tk.Label(item, text=icon, font=(ICON_FONT, 13), fg=SIDEBAR_TEXT, bg=SIDEBAR, width=2)
    icon_label.pack(side='left', padx=(14, 10), pady=11)
    text_label = tk.Label(item, text=text, font=(FONT, 10), fg=SIDEBAR_TEXT, bg=SIDEBAR, anchor='w')
    text_label.pack(side='left', fill='x', expand=True)
    parts = (icon_label, text_label)
    app['nav'][key] = (item, parts)

    def hover(inside:bool)->None:
        if app['page'] != key:
            for widget in (item, *parts):
                widget.configure(bg=SIDEBAR_HOVER if inside else SIDEBAR)
    for widget in (item, *parts):
        widget.bind('<Button-1>', lambda e: show_page(key))
        widget.bind('<Enter>', lambda e: hover(True))
        widget.bind('<Leave>', lambda e: hover(False))

def update_status()->None:
    source = app['source']
    color = GOOD if source == 'MySQL' else WARNING
    text = {'MySQL': 'MySQL connecté', 'CSV': 'CSV (MySQL indisponible)'}.get(source, 'Aucune donnée')
    app['status'].configure(text=f'●  {text}', fg=color)
    app['count'].configure(text=f"{fmt(len(app['logs']))} lignes chargées")

# ---------- actions ----------

def reload()->None:
    app['logs'], app['source'] = store.load()
    update_status()
    show_page(app['page'])

def export(rows:List[dict])->None:
    path = filedialog.asksaveasfilename(defaultextension='.csv', filetypes=[('CSV', '*.csv')], initialfile='auth_logs_export.csv')
    if path:
        store.save_csv(rows, Path(path))
        messagebox.showinfo('Export', f'{fmt(len(rows))} lignes exportées dans\n{path}')

def start_import()->None:
    root = app['root']
    window = tk.Toplevel(root, bg=CARD, padx=32, pady=28)
    window.title('Importation')
    window.resizable(False, False)
    window.transient(root)
    window.grab_set()
    label(window, 'Importation des logs', 13, bold=True).pack(anchor='w')
    step = label(window, 'Préparation…', 10, INK_2)
    step.pack(anchor='w', pady=(6, 14))
    bar = ttk.Progressbar(window, length=420, mode='determinate', maximum=1)
    bar.pack()
    detail = label(window, '', 9, MUTED)
    detail.pack(anchor='w', pady=(10, 0))
    window.update_idletasks()
    window.geometry(f'+{root.winfo_x() + root.winfo_width() // 2 - window.winfo_width() // 2}+{root.winfo_y() + 200}')

    state = {'step': '', 'i': 0, 'n': 1, 'done': False, 'result': None, 'error': None}

    def progress(name:str, i:int, n:int)->None:
        state.update(step=name, i=i, n=n)

    def work()->None:
        try:
            state['result'] = store.import_data(progress)
        except Exception as e:
            state['error'] = e
        state['done'] = True

    def poll()->None:
        step.configure(text=state['step'] or 'Préparation…')
        bar.configure(maximum=max(state['n'], 1), value=state['i'])
        detail.configure(text=f"{fmt(state['i'])} / {fmt(state['n'])}" if state['n'] > 1 else '')
        if not state['done']:
            root.after(150, poll)
            return
        window.destroy()
        if state['error']:
            messagebox.showerror('Importation', str(state['error']))
            return
        app['logs'], app['source'] = state['result']
        update_status()
        show_page(app['page'])
        messagebox.showinfo('Importation', f"{fmt(len(app['logs']))} lignes enregistrées ({app['source']})")

    threading.Thread(target=work, daemon=True).start()
    poll()

# ---------- fenêtre ----------

def setup_style(root:tk.Tk)->None:
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('.', font=(FONT, 10), background=CARD)
    style.configure('Treeview', rowheight=32, font=(FONT, 10), background=CARD, fieldbackground=CARD,
                    foreground=INK, bordercolor=BORDER, borderwidth=0)
    style.configure('Treeview.Heading', font=(FONT, 9, 'bold'), background='#f3f4f6', foreground=INK_2,
                    relief='flat', padding=(8, 8), bordercolor=BORDER)
    style.map('Treeview', background=[('selected', '#dbeafe')], foreground=[('selected', INK)])
    style.map('Treeview.Heading', background=[('active', '#e5e7eb')])
    style.configure('Primary.TButton', font=(FONT, 10, 'bold'), background=ACCENT, foreground='#ffffff',
                    borderwidth=0, padding=(18, 9), focusthickness=0)
    style.map('Primary.TButton', background=[('active', ACCENT_DARK), ('disabled', '#9ec5f4')])
    style.configure('Ghost.TButton', font=(FONT, 10), background=CARD, foreground=INK, bordercolor=BORDER,
                    borderwidth=1, padding=(16, 8), focusthickness=0, relief='solid')
    style.map('Ghost.TButton', background=[('active', '#f3f4f6')], foreground=[('disabled', MUTED)])
    style.configure('TEntry', padding=(10, 7), bordercolor=BORDER, fieldbackground=CARD)
    style.configure('TCombobox', padding=(10, 7), bordercolor=BORDER, fieldbackground=CARD, background=CARD, arrowsize=14)
    style.map('TCombobox', fieldbackground=[('readonly', CARD)], selectbackground=[('readonly', CARD)],
              selectforeground=[('readonly', INK)], background=[('active', '#f3f4f6'), ('readonly', CARD)])
    style.configure('Vertical.TScrollbar', background='#d1d5db', troughcolor=PAGE, bordercolor=PAGE,
                    arrowcolor=MUTED, gripcount=0, arrowsize=12)
    style.configure('TProgressbar', background=ACCENT, troughcolor='#e5e7eb', bordercolor='#e5e7eb', thickness=10)

def build(root:tk.Tk)->None:
    sidebar = tk.Frame(root, bg=SIDEBAR, width=250)
    sidebar.pack(side='left', fill='y')
    sidebar.pack_propagate(False)
    brand = tk.Frame(sidebar, bg=SIDEBAR)
    brand.pack(fill='x', padx=28, pady=(30, 32))
    tk.Label(brand, text='Log Analysis', font=(FONT, 15, 'bold'), fg='#ffffff', bg=SIDEBAR).pack(anchor='w')
    tk.Label(brand, text='Surveillance des accès SSH', font=(FONT, 9), fg=SIDEBAR_TEXT, bg=SIDEBAR).pack(anchor='w', pady=(2, 0))
    tk.Label(sidebar, text='MENU', font=(FONT, 8, 'bold'), fg='#6b7280', bg=SIDEBAR).pack(anchor='w', padx=28, pady=(0, 8))
    for key, icon, text, _ in PAGES:
        nav_item(sidebar, key, icon, text)
    footer = tk.Frame(sidebar, bg=SIDEBAR)
    footer.pack(side='bottom', fill='x', padx=28, pady=28)
    app['status'] = tk.Label(footer, font=(FONT, 9, 'bold'), bg=SIDEBAR, anchor='w')
    app['status'].pack(anchor='w')
    app['count'] = tk.Label(footer, font=(FONT, 9), fg=SIDEBAR_TEXT, bg=SIDEBAR, anchor='w')
    app['count'].pack(anchor='w', pady=(4, 0))

    main = tk.Frame(root, bg=PAGE)
    main.pack(side='left', fill='both', expand=True)
    header = tk.Frame(main, bg=CARD, highlightbackground=BORDER, highlightcolor=BORDER, highlightthickness=1)
    header.pack(fill='x')
    titles = tk.Frame(header, bg=CARD)
    titles.pack(side='left', padx=PAD, pady=22)
    app['title'] = label(titles, '', 18, bold=True)
    app['title'].pack(anchor='w')
    app['subtitle'] = label(titles, '', 10, MUTED)
    app['subtitle'].pack(anchor='w', pady=(2, 0))
    actions = tk.Frame(header, bg=CARD)
    actions.pack(side='right', padx=PAD)
    button(actions, '⟳  Actualiser', reload).pack(side='left', padx=(0, 10))
    button(actions, 'Importer les logs', start_import, primary=True).pack(side='left')
    app['body'] = tk.Frame(main, bg=PAGE)
    app['body'].pack(fill='both', expand=True)

def run()->None:
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)#texte net sur les écrans haute résolution
    except Exception:
        pass
    root = tk.Tk()
    app['root'] = root
    root.title('Log Analysis — Dashboard SSH')
    root.configure(bg=PAGE)
    root.geometry('1440x900')
    root.minsize(1100, 700)
    try:
        root.state('zoomed')
    except tk.TclError:
        pass
    setup_style(root)
    build(root)
    root.bind_all('<MouseWheel>', on_wheel)
    app['logs'], app['source'] = store.load()
    update_status()
    show_page('overview')
    root.mainloop()

if __name__ == '__main__':
    run()
