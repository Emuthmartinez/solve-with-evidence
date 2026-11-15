import unittest

from feed.pager import page
from feed.store import Post, Store


class Feed311(unittest.TestCase):
    def test_a_new_post_does_not_repeat_the_end_of_page_one(self):
        store = Store([Post(n, 1000 + n, f'post {n}') for n in range(1, 26)])
        first = page(store, size=10)
        store.add(Post(26, 1026, 'new post'))
        second = page(store, first.next_cursor, size=10)
        self.assertEqual([post.id for post in second.items], list(range(15, 5, -1)))


if __name__ == '__main__':
    unittest.main()
