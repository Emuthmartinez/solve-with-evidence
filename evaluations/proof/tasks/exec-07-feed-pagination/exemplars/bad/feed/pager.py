"""Pages the home feed. docs/api.md is the contract."""
from collections import namedtuple

Page = namedtuple('Page', 'items next_cursor')


def page(store, cursor=None, size=20):
    """One page of the feed, newest first, as Page(items, next_cursor)."""
    posts = sorted(store.all(), key=lambda post: post.created_at, reverse=True)
    if cursor is not None:
        older_than = int(cursor)
        posts = [post for post in posts if post.created_at < older_than]
    chunk = posts[:size]
    items = [post for post in chunk if not post.hidden]
    next_cursor = str(chunk[-1].created_at) if len(chunk) == size else None
    return Page(items, next_cursor)
