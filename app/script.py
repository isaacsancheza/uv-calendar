#!/usr/bin/env python3
import logging
from os import environ
from pytz import timezone
from typing import Any
from datetime import datetime

from boto3 import resource
from requests import get

from uv.ics import create_calendar
from uv.scraper import get_events


class TooManyCalendarsException(Exception):
    pass


SEA = 'https://www.uv.mx/escolar/calendarios/{year}/sea.html'
ESCOLARIZADO = 'https://www.uv.mx/escolar/calendarios/{year}/escolarizado.html'

logging.basicConfig(level='INFO')
logger = logging.getLogger('script')


s3 = resource('s3')
bucket = s3.Bucket(environ['BUCKET_NAME'])
calendars_bucket = s3.Bucket(environ['CALENDARS_BUCKET_NAME'])


def get_dates(events: dict):
    return [event['date'] for event in events if 'Descansos' not in event['name']]


today = datetime.now(timezone('America/Mexico_City'))
current_year = today.year
next_year = current_year + 1

next_year_data: dict[str, dict[str, Any]] = {}
current_year_data: dict[str, dict[str, Any]] = {}
for year in [current_year, next_year]:
    logger.info(f'year: {year}')
    
    # validate url exists
    sea_url = SEA.format(year=year)
    sea_response = get(sea_url)

    logger.info(f'sea url: {sea_url}')
    if sea_response.ok:
        sea = get_events(sea_url)
        sea_spring, sea_fall = sea

        logger.info(f'spring events: {len(sea_spring["events"])}')
        logger.info(f'fall events: {len(sea_fall["events"])}')
        
        if year == next_year:
            logger.info(f'{year} is next year')
            
            next_year_data['sea'] = {
                'fall': sea_fall,
                'spring': sea_spring,
            }
        else:
            logger.info(f'{year} is current year')
            
            current_year_data['sea'] = {
                'fall': sea_fall,
                'spring': sea_spring,
            }
    else:
        logger.info('sea url not found')

    # validate url exists
    escolarizado_url = ESCOLARIZADO.format(year=year)
    escolarizado_response = get(escolarizado_url)

    logger.info(f'escolarizado url: {escolarizado_url}')
    if escolarizado_response.ok:            
        escolarizado = get_events(escolarizado_url)
        if len(escolarizado) == 4:
            escolarizado_spring, escolarizado_fall, *_ = escolarizado    
        elif len(escolarizado) == 5:
            escolarizado_spring, escolarizado_fall, *_ = escolarizado
        else:
            logger.error(f'too many calendars: {len(escolarizado)}')
            raise TooManyCalendarsException()

        logger.info(f'spring events: {len(escolarizado_spring["events"])}')
        logger.info(f'fall events: {len(escolarizado_fall["events"])}')

        if year == next_year:
            logger.info(f'{year} is next year')

            next_year_data['escolarizado'] = {
                'fall': escolarizado_fall,
                'spring': escolarizado_spring,
            }
        else:
            logger.info(f'{year} is current year')

            current_year_data['escolarizado'] = {
                'fall': escolarizado_fall,
                'spring': escolarizado_spring,
            }
    else:
        logger.info('escolarizado url not found')

# sea
sea_spring_dates = get_dates(current_year_data['sea']['spring']['events']) 
sea_begin_spring = min(sea_spring_dates)
sea_end_spring = max(sea_spring_dates)

sea_fall_dates = get_dates(current_year_data['sea']['fall']['events'])
sea_begin_fall = min(sea_fall_dates)
sea_end_fall = max(sea_fall_dates)

if today < sea_begin_fall:
    logger.info('today is before sea_begin_fall')
    logger.info('including spring plus fall events')
    events = current_year_data['sea']['spring']['events']
    events += current_year_data['sea']['fall']['events']
    
    logger.info(f'events: {len(events)}')

    calendar = create_calendar(events)
    calendars_bucket.put_object(
        Key='ics/sea/calendario.ics',
        Body=calendar,
    )
elif today >= sea_end_fall:
    logger.info('today is after sea_end_fall')
    logger.info('including fall events')
   
    events = current_year_data['sea']['fall']['events']
    if next_year_data:
        logger.info('including next year spring events')
        events += next_year_data['sea']['spring']['events']
    
    logger.info(f'events: {len(events)}')
    
    calendar = create_calendar(events)
    calendars_bucket.put_object(
        Key='ics/sea/calendario.ics',
        Body=calendar,
    )

# escolarizado
escolarizado_spring_dates = get_dates(current_year_data['escolarizado']['spring']['events'])
escolarizado_begin_spring = min(escolarizado_spring_dates)
escolarizado_end_spring = max(escolarizado_spring_dates)

escolarizado_fall_dates = get_dates(current_year_data['escolarizado']['fall']['events'])
escolarizado_begin_fall = min(escolarizado_fall_dates)
escolarizado_end_fall = max(escolarizado_fall_dates)

if today < escolarizado_begin_fall:
    logger.info('today is before escolarizado_begin_fall')
    logger.info('including spring plus fall events')

    events = current_year_data['escolarizado']['spring']['events']
    events += current_year_data['escolarizado']['fall']['events']

    logger.info(f'events: {len(events)}')
    
    calendar = create_calendar(events)
    calendars_bucket.put_object(
        Key='ics/escolarizado/calendario.ics',
        Body=calendar,
    )
elif today > escolarizado_end_fall:
    logger.info('today is after escolarizado_end_fall')
    logger.info('including fall events')

    events = current_year_data['escolarizado']['fall']['events']
    if next_year_data:
        logger.info('including next year spring events')
        events += next_year_data['escolarizado']['spring']['events']
    
    logger.info(f'events: {len(events)}')

    calendar = create_calendar(events)
    calendars_bucket.put_object(
        Key='ics/escolarizado/calendario.ics',
        Body=calendar,
    )
