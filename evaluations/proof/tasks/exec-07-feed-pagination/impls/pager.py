"""A second pager that follows docs/api.md with another cursor form. The grader runs the
solver's regression test against it: a test that depends on the cursor's form fails here."""
import re
from collections import namedtuple

Page = namedtuple('Page', 'items next_cursor')


def page(store, cursor=None, size=20):
    if isinstance(size, bool) or not isinstance(size, int) or size < 1 or size > 100:
        raise ValueError('bad size')
    if cursor is None:
        position = None
    else:
        match = re.fullmatch(r'at:(-?(?:0|[1-9][0-9]*))/(-?(?:0|[1-9][0-9]*))', cursor) if isinstance(cursor, str) else None
        if match is None:
            raise ValueError('bad cursor')
        position = (int(match.group(1)), int(match.group(2)))
    feed = sorted((p for p in store.all() if not p.hidden), key=lambda p: (-p.created_at, -p.id))
    if position is not None:
        feed = [p for p in feed if (p.created_at, p.id) < position]
    if len(feed) <= size:
        return Page(feed, None)
    last = feed[size - 1]
    return Page(feed[:size], f'at:{last.created_at}/{last.id}')
