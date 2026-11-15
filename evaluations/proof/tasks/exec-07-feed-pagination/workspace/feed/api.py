"""Handler for GET /feed. Query-string values arrive as strings."""
from feed.pager import page


def get_feed(store, query):
    """query: dict of query-string values, with optional 'cursor' and 'size'. Returns (status, body)."""
    try:
        size = int(query.get('size', '20'))
        current = page(store, query.get('cursor'), size)
    except ValueError as exc:
        return 400, {'error': str(exc)}
    posts = [{'id': post.id, 'created_at': post.created_at, 'title': post.title} for post in current.items]
    return 200, {'posts': posts, 'next': current.next_cursor}
