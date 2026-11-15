"""Pages the home feed. docs/api.md is the contract."""
import base64
import json
from collections import namedtuple

Page = namedtuple('Page', 'items next_cursor')


def page(store, cursor=None, size=20):
    """One page of the feed, newest first, as Page(items, next_cursor)."""
    if type(size) is not int or not 1 <= size <= 100:
        raise ValueError(f'size must be an int from 1 to 100: {size!r}')
    after = None if cursor is None else decode(cursor)
    posts = sorted((post for post in store.all() if not post.hidden and (after is None or key(post) < after)),
                   key=key, reverse=True)
    items = posts[:size]
    return Page(items, encode(key(items[-1])) if len(posts) > size else None)


def key(post):
    return (post.created_at, post.id)


def encode(position):
    return base64.urlsafe_b64encode(json.dumps(list(position)).encode()).decode()


def decode(cursor):
    if not isinstance(cursor, str):
        raise ValueError(f'not a cursor: {cursor!r}')
    try:
        position = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
    except ValueError:
        raise ValueError(f'not a cursor: {cursor!r}') from None
    if not (isinstance(position, list) and len(position) == 2 and all(type(v) is int for v in position)):
        raise ValueError(f'not a cursor: {cursor!r}')
    return tuple(position)
