# GoogleMapsParser

## Описание

Консольное приложение для поиска мест в Google Maps по ключевому слову и выгрузки их в excel-файл.

## Технологии

Poetry, pandas, requests, googlemaps

## Как запустить

Создать .env файл в корне проекта вида:

```env
API_KEY = <ваш google place api key>
GEONAMES_USERNAME=<ваш geonames username>
```

Установить все зависимости

```bash
poetry install
poetry shell
```

Из корневой директории запустить main.py

```bash
python main.py
```
