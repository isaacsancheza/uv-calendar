from os import environ
from json import dumps
from pytz import timezone
from requests import get
from datetime import datetime

from boto3 import resource
from botocore.exceptions import ClientError

from uv.ics import create_calendar
from uv.scraper import get_events


class TooManyCalendarsException(Exception):
    pass


SEA = 'https://www.uv.mx/escolar/calendarios/{year}/sea.html'
ESCOLARIZADO = 'https://www.uv.mx/escolar/calendarios/{year}/escolarizado.html'


s3 = resource('s3')
bucket = s3.Bucket(environ['BUCKET_NAME'])
calendars_bucket = s3.Bucket(environ['CALENDARS_BUCKET_NAME'])


def get_dates(events: dict):
    return [datetime.fromisoformat(event['date']) for event in events if 'Descansos' not in event['name']]


def dump_object(key: str, data: bytes) -> None:
    bucket.put_object(Key=key, Body=data)


today = datetime.now(timezone('America/Mexico_City'))
current_year = today.year
next_year = current_year + 1

sea_begin_fall = None
sea_end_fall = None

sea_begin_spring = None
sea_end_spring = None

escolarizado_begin_fall = None
escolarizado_end_fall = None

escolarizado_begin_spring = None
escolarizado_end_spring = None

for year in [current_year, next_year]:
    # validate url exists
    sea_url = SEA.format(year=year)
    sea_response = get(sea_url)

    if sea_response.ok:
        sea = get_events(sea_url)
        sea_primavera, sea_otono = sea

        if year == current_year:
            sea_fall_dates = get_dates(sea_otono['events'])
            sea_begin_fall = min(sea_fall_dates)
            sea_end_fall = max(sea_fall_dates)
            
            sea_spring_dates = get_dates(sea_primavera['events']) 
            sea_begin_spring = min(sea_spring_dates)
            sea_end_spring = max(sea_spring_dates)

        dump_object(f'data/{year}/sea/otono.json', dumps(sea_otono).encode())
        dump_object(f'data/{year}/sea/primavera.json', dumps(sea_primavera).encode())

        sea_otono_calendar = create_calendar(sea_otono['events'])
        sea_primavera_calendar = create_calendar(sea_primavera['events'])

        dump_object(f'calendarios/{year}/sea/otono.ics', sea_otono_calendar)
        dump_object(f'calendarios/{year}/sea/primavera.ics', sea_primavera_calendar)

    escolarizado_url = ESCOLARIZADO.format(year=year)
    escolarizado_response = get(escolarizado_url)

    if escolarizado_response.ok:            
        escolarizado = get_events(escolarizado_url)
        if len(escolarizado) == 4:
            escolarizado_primavera, escolarizado_otono, escolarizado_verano, escolarizado_invierno = escolarizado    
        elif len(escolarizado) == 5:
            escolarizado_primavera, escolarizado_otono, escolarizado_verano, _, escolarizado_invierno = escolarizado
        else:
            raise TooManyCalendarsException()

        if year == current_year:
            escolarizado_fall_dates = get_dates(escolarizado_otono['events'])
            escolarizado_begin_fall = min(escolarizado_fall_dates)
            escolarizado_end_fall = max(escolarizado_fall_dates)

            escolarizado_spring_dates = get_dates(escolarizado_primavera['events'])
            escolarizado_begin_spring = min(escolarizado_spring_dates)
            escolarizado_end_spring = max(escolarizado_spring_dates)

        dump_object(f'data/{year}/escolarizado/otono.json', dumps(escolarizado_otono).encode())
        dump_object(f'data/{year}/escolarizado/verano.json', dumps(escolarizado_verano).encode())
        dump_object(f'data/{year}/escolarizado/invierno.json', dumps(escolarizado_invierno).encode())
        dump_object(f'data/{year}/escolarizado/primavera.json', dumps(escolarizado_primavera).encode())

        escolarizado_otono_calendar = create_calendar(escolarizado_otono['events'])
        escolarizado_verano_calendar = create_calendar(escolarizado_verano['events'])
        escolarizado_invierno_calendar = create_calendar(escolarizado_invierno['events'])
        escolarizado_primavera_calendar = create_calendar(escolarizado_primavera['events'])

        dump_object(f'calendarios/{year}/escolarizado/otono.ics', escolarizado_otono_calendar)
        dump_object(f'calendarios/{year}/escolarizado/verano.ics', escolarizado_verano_calendar)
        dump_object(f'calendarios/{year}/escolarizado/invierno.ics', escolarizado_invierno_calendar)
        dump_object(f'calendarios/{year}/escolarizado/primavera.ics', escolarizado_primavera_calendar)

# sea
# si existen los calendarios del año en curso
if sea_end_spring and sea_begin_spring and sea_end_fall and sea_begin_fall:
    # si estamos dentro del calendario primavera
    if sea_begin_spring <= today <= sea_end_spring:
        # copiamos el calendario primavera como principal
        calendars_bucket.copy(
            CopySource={
                'Key': f'calendarios/{current_year}/sea/primavera.ics',
                'Bucket': bucket.name,
            },
            Key='ics/sea/calendario.ics',
        )
    # si ya paso la ultima fecha del calendario primavera pero aun
    # no comienza el calendario de otoño
    elif sea_end_spring < today < sea_begin_fall:
        # copiamos el calendario otoño como principal
        calendars_bucket.copy(
            CopySource={
                'Key': f'calendarios/{current_year}/sea/otono.ics',
                'Bucket': bucket.name,
            },
            Key='ics/sea/calendario.ics',
        )
    # si estamos dentro del calendario de otoño
    elif sea_begin_fall <= today <= sea_end_fall:
        # copiamos el calendario de otoño como principal
        calendars_bucket.copy(
            CopySource={
                'Key': f'calendarios/{current_year}/sea/otono.ics',
                'Bucket': bucket.name,
            },
            Key='ics/sea/calendario.ics',
        )
    # si ya paso la ultima fecha del calendario de otoño
    elif today > sea_end_fall:
        # copiamos el calendario primavera del siguiente año
        try:
            calendars_bucket.copy(
                CopySource={
                    'Key': f'calendarios/{next_year}/sea/primavera.ics',
                    'Bucket': bucket.name,
                },
                Key='ics/sea/calendario.ics',
            )
        except ClientError:
            pass

# escolarizado
# si existen los calendarios del año en curso
if escolarizado_end_spring and escolarizado_begin_spring and escolarizado_end_fall and escolarizado_begin_fall:
    # si estamos dentro del calendario primavera
    if escolarizado_begin_spring <= today <= escolarizado_end_spring:
        # copiamos el calendario primavera como principal
        calendars_bucket.copy(
            CopySource={
                'Key': f'calendarios/{current_year}/escolarizado/otono.ics',
                'Bucket': bucket.name,
            },
            Key='ics/escolarizado/calendario.ics',
        )
    # si ya paso la ultima fecha del calendario primavera pero aun
    # no comienza el calendario de otoño
    elif escolarizado_end_spring < today < escolarizado_begin_fall:
        # copiamos el calendario otoño como principal
        calendars_bucket.copy(
            CopySource={
                'Key': f'calendarios/{current_year}/escolarizado/otono.ics',
                'Bucket': bucket.name,
            },
            Key='ics/escolarizado/calendario.ics',
        )
    # si estamos dentro del calendario de otoño
    elif escolarizado_begin_fall <= today <= escolarizado_end_fall:
        # copiamos el calendario de otoño como principal
        calendars_bucket.copy(
            CopySource={
                'Key': f'calendarios/{current_year}/escolarizado/otono.ics',
                'Bucket': bucket.name,
            },
            Key='ics/escolarizado/calendario.ics',
        )
    # si ya paso la ultima fecha del calendario de otoño
    elif today > escolarizado_end_fall:
        # copiamos el calendario primavera del siguiente año
        try:
            calendars_bucket.copy(
                CopySource={
                    'Key': f'calendarios/{next_year}/escolarizado/primavera.ics',
                    'Bucket': bucket.name,
                },
                Key='ics/escolarizado/calendario.ics',
            )
        except ClientError:
            pass
