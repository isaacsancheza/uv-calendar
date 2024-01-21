from typing import TypedDict
from datetime import datetime, timedelta

from ics import Event, Calendar


class EventDict(TypedDict):
    name: str
    date: str


def create_calendar(events: list[EventDict]) -> bytes:
    calendar = Calendar()
    unique_events = {}
    for event in events:
        if event['name'] not in unique_events:
            unique_events[event['name']] = []
        unique_events[event['name']].append(datetime.fromisoformat(event['date']))

    # sort events
    for event_name in unique_events:
        unique_events[event_name].sort()

    # separate them by group of no more than 1 day of difference
    event_groups = []
    for event_name in unique_events:
        group = []
        for date in unique_events[event_name]:
            if not group:
                group.append(date)
            
            # dates separated by more than 1 day are part of another group
            if (date - group[-1]) > timedelta(days=1):
                event_groups.append({
                    'name': event_name.strip(),
                    'begin': min(group),
                    'end': max(group),
                })
                group = [date]
            else:
                group.append(date)
        
        # last appended group equals current group
        if event_groups[-1]['begin'] == min(group) and event_groups[-1]['end'] == max(group):
            pass
        else:
            event_groups.append({
                'name': event_name.strip(),
                'begin': min(group),
                'end': max(group),
            })

    # create calendar
    for event_group in event_groups:
        if event_group['name'] == 'Descansos':
            continue
        calendar_event = Event(name=event_group['name'], begin=event_group['begin'], end=event_group['end'])
        calendar_event.make_all_day() 
        calendar.events.add(calendar_event)
    return calendar.serialize().encode()
