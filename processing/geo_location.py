import requests

URL_INFO='https://ipinfo.io'

def get_location(ip):
    response = requests.get(URL_INFO+'/'+ip+'/json')
    if response.status_code == 200 :
        return response.json()


if __name__ == '__main__' :
    print(get_location('121.29.89.152'))