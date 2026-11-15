"""Pages the home feed. docs/api.md is the contract."""
from collections import namedtuple

Page = namedtuple('Page', 'items next_cursor')


def page(store, cursor=None, size=20):
    """One page of the feed, newest first, as Page(items, next_cursor)."""
    offset = int(cursor) if cursor else 0
    posts = sorted(store.all(), key=lambda post: post.created_at, reverse=True)
    chunk = posts[offset:offset + size]
    items = [post for post in chunk if not post.hidden]
    next_cursor = str(offset + size) if len(chunk) == size else None
    return Page(items, next_cursor)
