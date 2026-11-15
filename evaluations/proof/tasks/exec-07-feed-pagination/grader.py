import importlib
import sys
from collections import namedtuple
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from gradelib import main, raises, tests_pass

Post = namedtuple('Post', 'id created_at title hidden', defaults=(False,))


class Store:
    """The contract in the workspace's feed/store.py, plus a read limit that turns an endless walk into a failure."""

    def __init__(self, posts=()):
        self._posts = []
        self.reads = 0
        for post in posts:
            self.add(post)

    def add(self, post):
        if any(existing.id == post.id for existing in self._posts):
            raise ValueError(f'duplicate post id: {post.id}')
        self._posts.append(post)

    def delete(self, post_id):
        for index, post in enumerate(self._posts):
            if post.id == post_id:
                del self._posts[index]
                return
        raise KeyError(post_id)

    def all(self):
        self.reads += 1
        if self.reads > 20000:
            raise RuntimeError('the walk does not end')
        return self._posts


def numbered(numbers, hidden=()):
    """Posts with distinct times: post n was published at 1000 + n."""
    return Store([Post(n, 1000 + n, f'post {n}', n in hidden) for n in numbers])


def ids(posts):
    return [post.id for post in posts]


def call(s, store, cursor=None, size=20):
    return s.page(store, cursor=cursor, size=size)


def walk(s, store, size, between=None):
    """Follow cursors from the first page. between(number, page) runs after each page that has a cursor."""
    pages, cursor = [], None
    while len(pages) < 500:
        current = call(s, store, cursor, size)
        pages.append(current)
        cursor = current.next_cursor
        if cursor is None:
            break
        if between:
            between(len(pages), current)
    return pages


def walked(pages):
    return [post.id for current in pages for post in current.items]


def order_with_ties(s):
    store = Store([Post(5, 100, 'e'), Post(2, 100, 'b'), Post(9, 50, 'i'), Post(1, 200, 'a'),
                   Post(7, 100, 'g'), Post(3, 50, 'c'), Post(4, 300, 'imported late')])
    return ids(call(s, store, size=100).items) == [4, 1, 7, 5, 2, 9, 3]


def ties_across_boundary(s):
    store = Store([Post(n, 500, f'tie {n}') for n in range(1, 8)] + [Post(20, 900, 'new'), Post(30, 100, 'old')])
    seen = walked(walk(s, store, 3))
    return sorted(seen) == [1, 2, 3, 4, 5, 6, 7, 20, 30] and len(seen) == 9


def bug_report(s):
    store = numbered(range(1, 26))
    first = call(s, store, size=10)
    store.add(Post(26, 1026, 'new post'))
    second = call(s, store, first.next_cursor, 10)
    return ids(first.items) == list(range(25, 15, -1)) and ids(second.items) == list(range(15, 5, -1))


def inserts(s):
    # Posts 10, 20, .., 300 published at 1000 + id. Page one ends at post 210.
    store = numbered(range(10, 301, 10))

    def add(number, current):
        if number == 1:
            for post in (Post(999, 5000, 'newer'), Post(215, 1210, 'same second, higher id'),
                         Post(205, 1210, 'same second, lower id'), Post(55, 1001, 'imported, older')):
                store.add(post)

    seen = walked(walk(s, store, 10, add))
    return seen == list(range(300, 209, -10)) + [205] + list(range(200, 9, -10)) + [55]


def delete_ahead(s):
    store = numbered(range(1, 31))

    def delete(number, current):
        if number == 1:
            store.delete(14)
            store.delete(3)
    ahead = walked(walk(s, store, 10, delete)) == [n for n in range(30, 0, -1) if n not in (14, 3)]
    store = numbered(range(1, 16))
    first = call(s, store, size=10)
    for n in range(1, 6):
        store.delete(n)
    rest = call(s, store, first.next_cursor, 10)
    return ahead and ids(rest.items) == [] and rest.next_cursor is None


def delete_returned(s):
    store = numbered(range(1, 31))

    def delete(number, current):
        store.delete(current.items[-1].id)
        store.delete(current.items[0].id)
    return walked(walk(s, store, 10, delete)) == list(range(30, 0, -1))


def exact_boundary(s):
    pages = walk(s, numbered(range(1, 21)), 10)
    single = call(s, numbered(range(1, 21)), size=20)
    return (len(pages) == 2 and walked(pages) == list(range(20, 0, -1))
            and len(single.items) == 20 and single.next_cursor is None)


def empty_feed(s):
    current = call(s, Store())
    return list(current.items) == [] and current.next_cursor is None


def one_page(s):
    current = call(s, numbered(range(1, 6)))
    return ids(current.items) == [5, 4, 3, 2, 1] and current.next_cursor is None


def hidden_never(s):
    store = numbered(range(1, 21), hidden={20, 13, 7, 1})
    return walked(walk(s, store, 3)) == [n for n in range(20, 0, -1) if n not in (20, 13, 7, 1)]


def hidden_full_pages(s):
    store = numbered(range(1, 16), hidden={14, 12, 9, 8, 3})
    pages = walk(s, store, 4)
    return [ids(current.items) for current in pages] == [[15, 13, 11, 10], [7, 6, 5, 4], [2, 1]]


def hidden_tail(s):
    store = numbered(range(1, 8), hidden={1, 2, 3})
    pages = walk(s, store, 4)
    return len(pages) == 1 and ids(pages[0].items) == [7, 6, 5, 4] and pages[0].next_cursor is None


def size_range(s):
    store = numbered(range(1, 5))
    return all(raises(ValueError, call, s, store, None, size) for size in (0, -1, 101, 1000))


def size_type(s):
    store = numbered(range(1, 5))
    return all(raises(ValueError, call, s, store, None, size) for size in (20.0, '20', True, None))


def size_limits(s):
    store = numbered(range(1, 151))
    return (ids(call(s, store, size=100).items) == list(range(150, 50, -1))
            and ids(call(s, store, size=1).items) == [150])


def malformed_cursor(s):
    store = numbered(range(1, 30))
    return all(raises(ValueError, call, s, store, cursor, 10) for cursor in ('', 'not-a-cursor', 42))


def cursor_reuse(s):
    store = numbered(range(1, 30))
    cursor = call(s, store, size=5).next_cursor
    once = call(s, store, cursor, 5)
    twice = call(s, store, cursor, 5)
    return ids(once.items) == ids(twice.items) == [24, 23, 22, 21, 20]


def cursor_other_size(s):
    store = numbered(range(1, 30))
    cursor = call(s, store, size=5).next_cursor
    return (ids(call(s, store, cursor, 7).items) == list(range(24, 17, -1))
            and ids(call(s, store, cursor, 2).items) == [24, 23])


def store_unchanged(s):
    posts = [Post(n, 1000 + (n * 7) % 13, f'post {n}', n % 5 == 0) for n in range(1, 30)]
    store = Store(posts)
    walk(s, store, 4)
    return store.all() == posts


def export(s):
    export_all = importlib.import_module('feed.export').export_all
    posts = [Post(n, 1000 + n // 3, f'post {n}', n % 7 == 0) for n in range(1, 251)]
    want = [post.id for post in sorted(posts, key=lambda p: (p.created_at, p.id), reverse=True) if not post.hidden]
    return ids(export_all(Store(posts), size=50)) == want and ids(export_all(Store(posts))) == want


def regression_shipped(s):
    return not tests_pass('test_regression.py', replace={'feed/pager.py': (HERE / 'workspace/feed/pager.py').read_text()})


def regression_delivered(s):
    return tests_pass('test_regression.py')


def regression_reference(s):
    return tests_pass('test_regression.py', replace={'feed/pager.py': (HERE / 'impls/pager.py').read_text()})


CHECKS = [
    ('posts are newest first with ties by higher id', order_with_ties),
    ('ties split across a page boundary are neither skipped nor repeated', ties_across_boundary),
    ('the reported new post does not repeat an item', bug_report),
    ('a post added during a walk appears exactly when it sorts after the position', inserts),
    ('a post deleted before it is reached does not appear', delete_ahead),
    ('deleting returned posts does not break the walk', delete_returned),
    ('a feed ending at a page boundary has no empty last page', exact_boundary),
    ('an empty feed has no items and no cursor', empty_feed),
    ('a feed that fits one page has no cursor', one_page),
    ('hidden posts are never returned', hidden_never),
    ('hidden posts do not shorten a page', hidden_full_pages),
    ('hidden posts after the last visible post add no page', hidden_tail),
    ('size outside 1 to 100 raises ValueError', size_range),
    ('a size that is not an int raises ValueError', size_type),
    ('size 1 and size 100 are accepted', size_limits),
    ('malformed cursors raise ValueError', malformed_cursor),
    ('a cursor can be used twice', cursor_reuse),
    ('a cursor works with another size', cursor_other_size),
    ('page does not change the store', store_unchanged),
    ('export_all returns every post once', export),
    ('regression test fails on the shipped pager', regression_shipped),
    ('regression test passes on the delivered pager', regression_delivered),
    ('regression test passes on a reference pager', regression_reference),
]

if __name__ == '__main__':
    main(CHECKS, 'feed.pager')
