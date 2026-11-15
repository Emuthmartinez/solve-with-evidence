import unittest

from feed.api import get_feed
from feed.export import export_all
from feed.pager import Page, page
from feed.store import Post, Store


def store(count=25):
    return Store([Post(n, 1000 + n, f'post {n}') for n in range(1, count + 1)])


def ids(posts):
    return [post.id for post in posts]


class Paging(unittest.TestCase):
    def test_first_page_is_newest_first(self):
        first = page(store(), size=3)
        self.assertIsInstance(first, Page)
        self.assertEqual(ids(first.items), [25, 24, 23])
        self.assertIsNotNone(first.next_cursor)

    def test_walk_returns_every_post(self):
        feed, seen, cursor = store(), [], None
        while True:
            current = page(feed, cursor, 10)
            seen += ids(current.items)
            cursor = current.next_cursor
            if cursor is None:
                break
        self.assertEqual(seen, list(range(25, 0, -1)))

    def test_export(self):
        self.assertEqual(ids(export_all(store(), size=7)), list(range(25, 0, -1)))

    def test_api(self):
        status, body = get_feed(store(), {'size': '2'})
        self.assertEqual(status, 200)
        self.assertEqual([post['id'] for post in body['posts']], [25, 24])
        status, body = get_feed(store(), {'size': '2', 'cursor': body['next']})
        self.assertEqual([post['id'] for post in body['posts']], [23, 22])


if __name__ == '__main__':
    unittest.main()
