from typing import TypedDict
from datetime import datetime, timedelta

from ics import Event, Calendar


class EventDict(TypedDict):
    url: str
    name: str
    date: datetime


def create_calendar(events: list[EventDict]) -> bytes:
    calendar = Calendar()
    unique_events = {}
    for event in events:
        if event['name'] not in unique_events:
            unique_events[event['name']] = []
        unique_events[event['name']].append(
            [
                event['url'],
                event['date'],
            ]
        )

    # sort events
    for event_name in unique_events:
        unique_events[event_name].sort(key=lambda x: x[1])  # sort by second element which is a datetime instance

    # separate them by group of no more than 1 day of difference
    event_groups = []
    for event_name in unique_events:
        group = []
        for url, date in unique_events[event_name]:
            if not group:
                group.append(date)
            
            # dates separated by more than 1 day are part of another group
            if (date - group[-1]) > timedelta(days=1):
                event_groups.append(
                    {
                        'url': url,
                        'name': event_name.strip(),
                        'begin': min(group),
                        'end': max(group),
                    }
                )
                group = [date]
            else:
                group.append(date)
        
        # last appended group equals current group
        if event_groups[-1]['begin'] == min(group) and event_groups[-1]['end'] == max(group):
            pass
        else:
            event_groups.append(
                {
                    'url': url,
                    'name': event_name.strip(),
                    'begin': min(group),
                    'end': max(group),
                }
            )

    # create calendar
    for event_group in event_groups:
        if event_group['name'] == 'Descansos':
            continue
        calendar_event = Event(
            name=f'📚 {event_group["name"]}', 
            begin=event_group['begin'], 
            end=event_group['end'],
            description=event_group['url'],
        )
        calendar_event.make_all_day() 
        calendar.events.add(calendar_event)
    return calendar.serialize().encode()
