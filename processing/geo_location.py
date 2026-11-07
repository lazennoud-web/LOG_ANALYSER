import requests

URL_INFO='https://ipinfo.io'

"""
in : ip
out : dict (ip, city, region, country, loc, org, timezone) or None
"""
def get_location(ip):
    try:
        response = requests.get(URL_INFO+'/'+ip+'/json',timeout=5)
    except requests.RequestException as e:
        print(e)
        return
    if response.status_code == 200 :
        return response.json()


if __name__ == '__main__' :
    print(get_location('121.29.89.152'))
