import json
import urllib.error
import urllib.request
from log_config import get_logger

logger = get_logger('geo')
URL_INFO = 'https://ipinfo.io'

"""
in : ip
out : dict (ip, city, region, country, loc, org, timezone) or None
"""

def get_location(ip):
    if not ip:
        return None
    url = f'{URL_INFO}/{ip}/json'
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
        if isinstance(data, dict):
            return data
        return None
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        logger.warning(f'Géolocalisation IP indisponible pour {ip} : {exc}')
        return None


if __name__ == '__main__':
    print(get_location('121.29.89.152'))
