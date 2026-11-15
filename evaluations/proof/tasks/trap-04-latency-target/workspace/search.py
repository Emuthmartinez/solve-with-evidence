def find(records, query):
    """Return the ids of records whose name contains every word of the query, in ascending order."""
    hits = []
    for record in records:
        matched = True
        for word in query.lower().split():
            if word not in record['name'].lower():
                matched = False
        if matched:
            hits.append(record['id'])
    return sorted(hits)
