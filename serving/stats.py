from collections import Counter
from typing import List, Tuple

"""
    Compute dashboard statistics
    in : list of dict (logs from storage)
    out : counters / lists ready to plot
"""
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
MONTHS_FR = dict(zip(MONTHS, ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.']))
STATUSES = ['Failed', 'Invalid', 'Success']

def by_status(logs:List[dict], status:str)->List[dict]:
    return [log for log in logs if log['status'] == status]

def country(log:dict)->str:
    return log['country'] or 'Inconnu'

def day_key(log:dict)->Tuple[int, int]:
    return MONTHS.index(log['month']), log['day']

def day_label(key:Tuple[int, int])->str:
    return f'{key[1]:02d} {MONTHS_FR[MONTHS[key[0]]]}'

def kpis(logs:List[dict])->dict:
    failed = by_status(logs, 'Failed')
    per_day = Counter(day_key(log) for log in failed)
    peak = per_day.most_common(1)[0] if per_day else None
    countries = Counter(country(log) for log in failed)
    top_country = countries.most_common(1)[0] if countries else None
    return {
        'total': len(logs),
        'failed': len(failed),
        'invalid': len(by_status(logs, 'Invalid')),
        'success': len(by_status(logs, 'Success')),
        'ips': len({log['ip'] for log in logs}),
        'countries': len({log['country'] for log in logs if log['country']}),
        'users': len({log['user'] for log in logs if log['user']}),
        'days': len({day_key(log) for log in logs}),
        'avg_per_day': len(failed) / len(per_day) if per_day else 0,
        'peak_day': (day_label(peak[0]), peak[1]) if peak else ('-', 0),
        'top_country': top_country or ('-', 0),
    }

def per_day(logs:List[dict], status:str='Failed')->Tuple[List[str], List[int]]:
    counts = Counter(day_key(log) for log in by_status(logs, status))
    days = sorted({day_key(log) for log in logs})
    return [day_label(day) for day in days], [counts[day] for day in days]

def per_hour(logs:List[dict], status:str='Failed')->List[int]:
    counts = Counter(int(log['time'][:2]) for log in by_status(logs, status))
    return [counts[hour] for hour in range(24)]

def heatmap(logs:List[dict], status:str='Failed')->Tuple[List[str], List[List[int]]]:
    counts = Counter((day_key(log), int(log['time'][:2])) for log in by_status(logs, status))
    days = sorted({day_key(log) for log in logs})
    return [day_label(day) for day in days], [[counts[(day, hour)] for hour in range(24)] for day in days]

def top_countries(logs:List[dict], n:int=10, status:str='Failed')->List[Tuple[str, int]]:
    return Counter(country(log) for log in by_status(logs, status)).most_common(n)

def countries_table(logs:List[dict])->List[Tuple[str, int, int, int, int]]:
    """pays, échecs, invalides, succès, ip uniques"""
    rows = {}
    for log in logs:
        row = rows.setdefault(country(log), {'Failed': 0, 'Invalid': 0, 'Success': 0, 'ips': set()})
        row[log['status']] += 1
        row['ips'].add(log['ip'])
    return sorted(((c, r['Failed'], r['Invalid'], r['Success'], len(r['ips'])) for c, r in rows.items()),
                  key=lambda row: row[1], reverse=True)

def top_ips(logs:List[dict], n:int=10)->List[Tuple[str, str, int]]:
    counts = Counter(log['ip'] for log in by_status(logs, 'Failed'))
    countries = {log['ip']: country(log) for log in logs}
    return [(ip, countries[ip], count) for ip, count in counts.most_common(n)]

def top_users(logs:List[dict], n:int=10)->List[Tuple[str, int]]:
    return Counter(log['user'] for log in logs if log['user'] and log['status'] != 'Success').most_common(n)

def status_split(logs:List[dict])->List[Tuple[str, int]]:
    counts = Counter(log['status'] for log in logs)
    return [(status, counts[status]) for status in STATUSES]

def ip_activity(logs:List[dict], ip:str)->dict:
    ip_logs = [log for log in logs if log['ip'] == ip]
    if not ip_logs:
        return {}
    ordered = sorted(ip_logs, key=lambda log: (day_key(log), log['time']))
    return {
        'total': len(ip_logs),
        'statuses': Counter(log['status'] for log in ip_logs),
        'users': Counter(log['user'] for log in ip_logs if log['user']).most_common(8),
        'first': f"{day_label(day_key(ordered[0]))} {ordered[0]['time']}",
        'last': f"{day_label(day_key(ordered[-1]))} {ordered[-1]['time']}",
        'per_day': per_day(ip_logs, 'Failed'),
    }

if __name__ == '__main__':
    logs = [
        {'month': 'May', 'day': 24, 'time': '00:04:36', 'ip': '1.1.1.1', 'user': 'root', 'status': 'Failed', 'country': 'CN'},
        {'month': 'May', 'day': 24, 'time': '01:10:00', 'ip': '1.1.1.1', 'user': 'admin', 'status': 'Invalid', 'country': 'CN'},
        {'month': 'May', 'day': 25, 'time': '10:00:00', 'ip': '2.2.2.2', 'user': 'root', 'status': 'Failed', 'country': ''},
    ]
    print(kpis(logs))
    print(per_day(logs))
    print(top_countries(logs))
    print(countries_table(logs))
    print(top_ips(logs))
    print(ip_activity(logs, '1.1.1.1'))
