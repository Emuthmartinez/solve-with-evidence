def find(records, query):
    """Return the ids of records whose name contains every word of the query, in ascending order."""
    words = query.lower().split()
    return sorted(record['id'] for record in records
                  if all(word in record['name'].lower() for word in words))
