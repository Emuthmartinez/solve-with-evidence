"""FEED-311 and the rest of docs/api.md that the shipped pager broke. Uses cursors only as opaque values."""
import unittest

from feed.pager import page
from feed.store import Post, Store


def ids(posts):
    return [post.id for post in posts]


def walk(store, size, between=lambda: None):
    seen, cursor, pages = [], None, 0
    while True:
        current = page(store, cursor=cursor, size=size)
        seen += ids(current.items)
        pages += 1
        cursor = current.next_cursor
        if cursor is None or pages > 1000:
            return seen, pages
        between()


class Regression(unittest.TestCase):
    def test_feed_311_a_new_post_does_not_repeat_the_end_of_page_one(self):
        store = Store([Post(n, 1000 + n, f'post {n}') for n in range(1, 26)])
        first = page(store, size=10)
        store.add(Post(26, 1026, 'new post'))
        second = page(store, cursor=first.next_cursor, size=10)
        self.assertEqual(ids(second.items), list(range(15, 5, -1)))

    def test_deleting_returned_posts_skips_nothing(self):
        store = Store([Post(n, 1000 + n, f'post {n}') for n in range(1, 26)])
        first = page(store, size=10)
        store.delete(25)
        store.delete(16)
        second = page(store, cursor=first.next_cursor, size=10)
        self.assertEqual(ids(second.items), list(range(15, 5, -1)))

    def test_equal_timestamps_are_ordered_by_id_across_pages(self):
        store = Store([Post(n, 500, f'post {n}') for n in (3, 1, 5, 2, 4)] + [Post(9, 400, 'older')])
        self.assertEqual(walk(store, 2)[0], [5, 4, 3, 2, 1, 9])

    def test_a_feed_ending_at_a_page_boundary_has_no_empty_page(self):
        store = Store([Post(n, 1000 + n, f'post {n}') for n in range(1, 21)])
        self.assertEqual(walk(store, 10), (list(range(20, 0, -1)), 2))

    def test_hidden_posts_neither_shorten_pages_nor_add_one(self):
        posts = [Post(n, 1000 + n, f'post {n}', hidden=n % 3 == 0) for n in range(1, 13)]
        store = Store(posts + [Post(99, 1, 'hidden tail', hidden=True)])
        first = page(store, size=4)
        self.assertEqual(ids(first.items), [11, 10, 8, 7])
        second = page(store, cursor=first.next_cursor, size=4)
        self.assertEqual((ids(second.items), second.next_cursor), ([5, 4, 2, 1], None))

    def test_invalid_size_and_cursor_raise_value_error(self):
        store = Store([Post(1, 1001, 'post')])
        for size in (0, 101, '20', True):
            self.assertRaises(ValueError, page, store, size=size)
        for cursor in ('', 'not-a-cursor', 42):
            self.assertRaises(ValueError, page, store, cursor=cursor)


if __name__ == '__main__':
    unittest.main()
