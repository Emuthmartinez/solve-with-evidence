def sessionize(events, gap_seconds):
    if gap_seconds < 0:
        raise ValueError('gap_seconds must be >= 0')
    kept = {}
    for event in events:
        old = kept.get(event['id'])
        if old is None or event['seq'] > old['seq']:
            kept[event['id']] = event
    by_user = {}
    for event in kept.values():
        by_user.setdefault(event['user'], []).append(event)
    sessions = []
    for user, user_events in by_user.items():
        user_events.sort(key=lambda e: e['ts'])
        current = None
        for event in user_events:
            if current is None or event['ts'] - current['end'] > gap_seconds:
                current = {'user': user, 'start': event['ts'], 'end': event['ts'], 'ids': []}
                sessions.append(current)
            current['end'] = event['ts']
            current['ids'].append(event['id'])
    sessions.sort(key=lambda s: (s['start'], s['user']))
    return sessions
