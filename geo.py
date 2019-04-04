import requests
from math import sin, cos, sqrt, atan2, radians


def get_geo_info(city, type):
    url = "https://geocode-maps.yandex.ru/1.x/"

    params = {
        'geocode': city,
        'format': 'json'
    }

    response = requests.get(url, params)
    json = response.json()

    if type == 'country':
        return json['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['metaDataProperty'][
            'GeocoderMetaData']['AddressDetails']['Country']['CountryName']
    elif type == 'coordinates':
        point_str = json['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
        point_array = [float(x) for x in point_str.split(' ')]

        return point_array


def get_distance(p1, p2):
    R = 6373.0

    lon1 = radians(p1[0])
    lat1 = radians(p1[1])
    lon2 = radians(p2[0])
    lat2 = radians(p2[1])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c

    return distance


def is_address(address):
    url = "https://geocode-maps.yandex.ru/1.x/"

    params = {
        'geocode': address,
        'format': 'json'
    }

    response = requests.get(url, params)
    json = response.json()

    if int(json['response']['GeoObjectCollection']['metaDataProperty']['GeocoderResponseMetaData']['found']) > 0:
        return True
    return False

def find_coords(address):
    url = "https://geocode-maps.yandex.ru/1.x/"

    params = {
        'geocode': address,
        'format': 'json'
    }

    response = requests.get(url, params)
    json = response.json()

    toponym = json["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
    toponym_coordinates = ','.join(toponym["Point"]["pos"].split()) + address


    return toponym_coordinates