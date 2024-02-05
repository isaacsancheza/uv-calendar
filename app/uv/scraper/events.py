import logging
from re import compile
from pytz import utc, timezone
from locale import setlocale, LC_TIME
from calendar import month_name
from datetime import datetime

from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.color import Color


setlocale(LC_TIME, 'es_MX.UTF-8')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('scraper')

MONTH_NAMES = list(month_name)

RGX_RGB = compile(r'rgb\(\d+, \d+, \d+\)')
RGX_MONTH = compile(r'^Imprimir\(\'(?P<id>.*)\'\)$')
RGX_BACKGROUND = compile(r'background: (?P<color>rgb\(\d+, \d+, \d+\))')


def get_events(url: str) -> list:
    options = ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-dev-shm-usage')
    chrome = Chrome(options=options)
    
    entries = []
    symbology = dict()

    try:
        chrome.get(url)

        # get colors
        pivot = chrome.find_element(By.XPATH, '//b[contains(text(), "Simbología")]')
        rows = pivot.find_element(By.XPATH, './parent::div/parent::div')
        for i, row in enumerate(rows.find_elements(By.XPATH, './div')):
            if i == 0:
                continue
            for div in row.find_elements(By.XPATH, './div'):
                span = div.find_element(By.XPATH, './span')
                label = div.find_element(By.XPATH, './label')
                
                name = label.text
                color = span.value_of_css_property('background-color') 


                color = Color.from_string(color)
                symbology[color.hex] = name.strip()
        
        # get days
        btn_group = chrome.find_element(By.XPATH, '//button[@id="btn_all"]/parent::div')
        buttons = btn_group.find_elements(By.XPATH, './button')
        for i, btn in enumerate(buttons):            
            
            # ignore all calendar
            if i == len(buttons) - 1:
                break
            btn.click()
            
            # calendar's name
            entry = {
                'name': btn.text.strip(),
                'from': {},
                'to': {},
                'events': [],
            }

            value = btn.get_attribute('onclick')
            match = RGX_MONTH.match(value)
            div_id = match.group('id').strip()
            
            # Super weird that it's wrong
            if div_id == 'aug_jan':
                div_id = 'ago_jan'

            calendar = chrome.find_element(By.XPATH, f'//div[@id="{div_id}"]') 
            d_month = calendar.find_element(By.XPATH, './/span[@class="d-month"]')
            d_year = calendar.find_element(By.XPATH, './/span[@class="d-year"]')

            from_month, to_month = [MONTH_NAMES.index(m.strip().lower()) for m in d_month.text.split('-')]
            from_year = d_year.text
            if '/' in from_year:
                from_year, to_year = [y.strip() for y in from_year.split('/')]
            else:
                to_year = from_year

            # year is only two digits
            to_year = int(to_year) + 2000
            from_year = int(from_year) + 2000

            entry['to']['year'] = to_year
            entry['to']['month'] = to_month
            
            entry['from']['year'] = from_year
            entry['from']['month'] = from_month

            months = calendar.find_elements(By.XPATH, './/div[@class="d-table"]')
            last_month = None
            year_changed = False

            inicio_fin_dates: set[datetime] = set()
            for month in months:
                month_name = month.get_attribute('data-month')
                month_number = MONTH_NAMES.index(month_name.strip().lower())

                year = from_year   
                if last_month is not None:
                    if month_number < last_month:
                        year_changed = True
                last_month = month_number

                if year_changed:
                    year = to_year

                days = month.find_elements(By.XPATH, './/label')
                for day in days:
                    if day.get_attribute('class') == 'd-hidden':
                        continue

                    day_number = day.text.strip()
                    if not day_number:
                        continue
                    day_number = int(day_number)
                    
                    try:
                        date = datetime(year=year, month=month_number, day=day_number, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone('America/Mexico_City'))
                    except ValueError:
                        logger.error(f'value error: {day_number}/{month_number}/{year}')
                        continue

                    style = day.get_attribute('style')
                    if 'linear' in style:
                        match = RGX_RGB.findall(style)
                        for color in match:
                            color = Color.from_string(color)
                            if color.hex not in symbology:
                                continue

                            name = symbology.get(color.hex)
                            if name == 'Fin clases':
                                inicio_fin_dates.add(date)
                                continue

                            entry['events'].append({
                                'url': url,
                                'date': date,
                                'name': name,
                            })
                        continue

                    match = RGX_BACKGROUND.search(style)
                    if match:
                        color = match.group('color')
                        color = Color.from_string(color)
                        if color.hex not in symbology:
                            continue
                        
                        name = symbology.get(color.hex)
                        if name == 'Fin clases':
                            inicio_fin_dates.add(date)
                            continue
                        
                        entry['events'].append(
                            {
                                'url': url,
                                'date': date,
                                'name': name,
                            },
                        )
            if len(inicio_fin_dates) % 2 == 0:
                sorted_dates = sorted(inicio_fin_dates)
                for inicio, fin in [sorted_dates[i:i + 2] for i in range(0, len(sorted_dates), 2)]:
                    print('inicio', inicio, 'fin', fin)
                    entry['events'].append(
                        {
                            'url': url,
                            'date': inicio,
                            'name': 'Inicio clases',
                        }
                    )
                    entry['events'].append(
                        {
                            'url': url,
                            'date': fin,
                            'name': 'Fin clases',
                        }
                    )
            entries.append(entry)
    finally:
        try:
            chrome.quit()
        except:
            pass

    return entries
