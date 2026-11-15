"""Nightly export of the whole feed to the data warehouse."""
from feed.pager import page


def export_all(store, size=100):
    """Every post the feed shows, newest first, read one page at a time until next_cursor is None."""
    posts, cursor = [], None
    while True:
        current = page(store, cursor, size)
        posts.extend(current.items)
        cursor = current.next_cursor
        if cursor is None:
            return posts
