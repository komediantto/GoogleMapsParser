import json
import os

import time

import requests
import googlemaps
from dotenv import load_dotenv
from loguru import logger
import pandas as pd
import datetime

from tqdm import tqdm
from pick import pick
from googlemaps.exceptions import ApiError

load_dotenv()

API_KEY = os.getenv('API_KEY')
USERNAME = os.getenv('GEONAMES_USERNAME')
CLIENT = googlemaps.Client(key=API_KEY)


def choose_cities_or_country():
    title = 'Выберите вид поиска мест: '
    options = ['Страна', 'Город']
    option, _ = pick(options, title)
    return option


def get_districts(city: str, username: str):
    '''Получение районов города'''
    url = 'http://api.geonames.org/searchJSON?'\
          f'username={username}&q={city}&type=ADM5'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        district_list = []
        for item in data['geonames']:
            if 'city' in item['fclName']:
                district_list.append(f'{item["name"]}, \
                    {item["adminCodes1"]["ISO3166_2"]}')
        return district_list
    else:
        print('Ошибка API, сервис недоступен')


def get_language_choice() -> str:
    '''Принимаем язык вывода от пользователя(возможно - бесполезно)'''
    language = input(('Введите язык для выдачи результатов (например, "en"'
                      ' для английского, "ru" для русского и т.д.): '))
    return language


def get_largest_cities(country: str, username: str,
                       number_cities: int) -> list:
    '''Получение крупнейших городов выбранной страны'''
    url = f"http://api.geonames.org/searchJSON?country={country}&featureCode" \
          f"=PPLA&maxRows={number_cities}&lang=ru&username={username}"
    response = requests.get(url)
    data = response.json()

    cities = []
    for city in data['geonames']:
        cities.append(city['name'])

    return cities


def get_counry_codes():
    '''Получение списка международных кодов стран из JSON'''
    with open('countries.json', 'r', encoding='utf-8') as file:
        country_codes = json.load(file)
    return country_codes


def get_cities_in_choosen_country(location: str, number_cities: int):
    country_codes = get_counry_codes()
    if location.capitalize() in country_codes:
        cities = get_largest_cities(country_codes[location.capitalize()],
                                    USERNAME, number_cities)
        return cities
    print('Данной страны нет в нашей базе, либо вы опечатались. '
          'Все страны описаны в countries.json')


def get_districts_for_city(cities: list):
    districts = []
    for city in cities:
        districts += get_districts(city, USERNAME)
    return districts


def get_work_hours(details):
    raw_time = details['result'].get('opening_hours')
    if raw_time is not None:
        work_hour = ''
        work_hour_list = raw_time.get('weekday_text')
        for line in work_hour_list:
            work_hour += f'{line} | '
    else:
        work_hour = ''
    return work_hour


def get_full_address(details):
    full_address = details['result'].get('formatted_address')
    address_components = CLIENT.geocode(full_address)[0]['address_components']

    country, region, city, address, postal_code = "", "", "", "", ""
    for component in address_components:
        if 'country' in component['types']:
            country = component['long_name']
        elif 'administrative_area_level_1' in component['types']:
            region = component['long_name']
        elif 'locality' in component['types']:
            city = component['long_name']
        elif 'route' in component['types']:
            address = component['long_name']
        elif 'postal_code' in component['types']:
            postal_code = component['long_name']
    return country, region, city, address, postal_code


def get_places_for_district(districts: list, lang: str, query: str):
    final_result = []
    for district in tqdm(districts, desc="Searching..."):
        places_result = CLIENT.places(f"{query} {district}", language=language)

        while places_result:
            for place in places_result['results']:
                place_id = place['place_id']
                try:
                    details = CLIENT.place(place_id, language=language)
                except ApiError:
                    logger.warning('Place ID обновился')

                country, region, city, address, postal_code = get_full_address(
                    details=details)

                result = {
                    "ID": place_id,
                    "Название": details['result'].get('name'),
                    "Страна": country,
                    "Регион": region,
                    "Город": city,
                    "Адрес": address,
                    "Индекс": postal_code,
                    "Телефон": details['result'].get('formatted_phone_number'),
                    "Сайт": details['result'].get('website'),
                    "Время работы": get_work_hours(details),
                    "Широта": details['result']['geometry']['location'].get(
                        'lat'),
                    "Долгота": details['result']['geometry']['location'].get(
                        'lng'),
                }

                final_result.append(result)

            next_page_token = places_result.get('next_page_token')

            if next_page_token:
                time.sleep(1)
                places_result = CLIENT.places(f"{query} {district}",
                                              language=lang,
                                              page_token=next_page_token)
            else:
                places_result = None

    return final_result


def get_cities() -> list:
    input_cities = input('Введите один или больше городов через запятую :')
    cities = [location.strip() for location in input_cities.split(',')]
    return cities


def get_xlsx(places, country):
    df = pd.DataFrame.from_dict(places)
    df = df.drop_duplicates()
    date = datetime.datetime.now().strftime('%H:%M_%d-%m-%Y')
    df.to_excel(f'{query}->{country}---{date}.xlsx', index=False)
    print(f'Файл {query}->{country}---{date}.xlsx создан')


def get_country_name_and_cities_quantity():
    location = input('Введите название страны: ')
    number_cities = int(input('Введите количество городов для выдачи: '))
    return location, number_cities


def get_places_for_country(language, query):
    country, quantity = get_country_name_and_cities_quantity()
    cities = get_cities_in_choosen_country(country, quantity)
    districts = get_districts_for_city(cities)
    places = get_places_for_district(districts, language, query)
    get_xlsx(places, country)


def get_places_for_city(language, query):
    cities = get_cities()
    name = '-'.join(cities)
    districts = get_districts_for_city(cities)
    places = get_places_for_district(districts, language, query)
    get_xlsx(places, country=name)


if __name__ == '__main__':

    choosen = choose_cities_or_country()
    query = input('Введите ваш запрос: ').lower()
    language = get_language_choice()
    if choosen == 'Страна':
        get_places_for_country(language=language, query=query)
    elif choosen == 'Город':
        get_places_for_city(language=language, query=query)
