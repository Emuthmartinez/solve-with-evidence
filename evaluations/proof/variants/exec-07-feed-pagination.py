"""Plausible mistakes for exec-07-feed-pagination. Each is the good exemplar with one edit."""
PAGER = 'feed/pager.py'
TEST = 'test_regression.py'
AFTER = "    after = None if cursor is None else decode(cursor)\n"
SELECT = ("    posts = sorted((post for post in store.all() if not post.hidden and (after is None or key(post) < after)),\n"
          "                   key=key, reverse=True)\n")
CUT = "    items = posts[:size]\n"
NEXT = "    return Page(items, encode(key(items[-1])) if len(posts) > size else None)\n"
SIZE = "    if type(size) is not int or not 1 <= size <= 100:\n"
DELIVERED = 'regression test passes on the delivered pager'

VARIANTS = [
    ('equal times ordered by lower id first',
     {PAGER: [("    return (post.created_at, post.id)\n", "    return (post.created_at, -post.id)\n")]},
     ['posts are newest first with ties by higher id', 'a post added during a walk appears exactly when it sorts after the position',
      'export_all returns every post once', DELIVERED]),
    ('the position keeps the time only',
     {PAGER: [("    return (post.created_at, post.id)\n", "    return (post.created_at,)\n"),
              ("len(position) == 2", "len(position) == 1")]},
     ['posts are newest first with ties by higher id', 'ties split across a page boundary are neither skipped nor repeated',
      'a post added during a walk appears exactly when it sorts after the position', 'export_all returns every post once',
      DELIVERED]),
    ('an offset cursor with the right order and validation',
     {PAGER: [(AFTER, "    start = 0 if cursor is None else decode(cursor)[0]\n"),
              (SELECT, "    posts = sorted((post for post in store.all() if not post.hidden), key=key, reverse=True)[start:]\n"),
              (NEXT, "    return Page(items, encode((start + size, 0)) if len(posts) > size else None)\n")]},
     ['the reported new post does not repeat an item', 'a post added during a walk appears exactly when it sorts after the position',
      'deleting returned posts does not break the walk', DELIVERED]),
    ('the feed is frozen at the first page',
     {PAGER: [("Page = namedtuple", "SNAPSHOT = {}\nPage = namedtuple"),
              (SELECT, "    if after is None:\n"
                       "        SNAPSHOT[id(store)] = sorted((p for p in store.all() if not p.hidden), key=key, reverse=True)\n"
                       "    posts = [post for post in SNAPSHOT[id(store)] if after is None or key(post) < after]\n")]},
     ['a post added during a walk appears exactly when it sorts after the position',
      'a post deleted before it is reached does not appear']),
    ('the cursor names the last post, looked up again on the next call',
     {PAGER: [(AFTER, "    after = None if cursor is None else key(next(p for p in store.all() if p.id == decode(cursor)[0]))\n"),
              (NEXT, "    return Page(items, encode((items[-1].id, 0)) if len(posts) > size else None)\n")]},
     ['deleting returned posts does not break the walk', DELIVERED]),
    ('hidden posts returned',
     {PAGER: [("if not post.hidden and (after", "if (after")]},
     ['hidden posts are never returned', 'hidden posts do not shorten a page',
      'hidden posts after the last visible post add no page', 'export_all returns every post once', DELIVERED]),
    ('hidden posts removed after the page is cut',
     {PAGER: [("if not post.hidden and (after", "if (after"),
              (CUT, "    items = [post for post in posts[:size] if not post.hidden]\n")]},
     ['hidden posts do not shorten a page', 'hidden posts after the last visible post add no page', DELIVERED]),
    ('hidden posts counted when deciding whether more remain',
     {PAGER: [("if not post.hidden and (after", "if (after"),
              (CUT, "    items = [post for post in posts if not post.hidden][:size]\n")]},
     ['hidden posts after the last visible post add no page', DELIVERED]),
    ('a full last page still returns a cursor',
     {PAGER: [("if len(posts) > size", "if len(posts) >= size")]},
     ['a feed ending at a page boundary has no empty last page', 'hidden posts after the last visible post add no page',
      DELIVERED]),
    ('every page with items returns a cursor',
     {PAGER: [("if len(posts) > size", "if items")]},
     ['a feed ending at a page boundary has no empty last page', 'a feed that fits one page has no cursor',
      'hidden posts after the last visible post add no page', 'hidden posts do not shorten a page', DELIVERED]),
    ('the last item read before checking for more',
     {PAGER: [(NEXT, "    last = key(items[-1])\n    return Page(items, encode(last) if len(posts) > size else None)\n")]},
     ['an empty feed has no items and no cursor', 'a post deleted before it is reached does not appear']),
    ('no upper limit on size',
     {PAGER: [(SIZE, "    if type(size) is not int or not 1 <= size:\n")]},
     ['size outside 1 to 100 raises ValueError', DELIVERED]),
    ('a bool accepted as a size',
     {PAGER: [(SIZE, "    if not isinstance(size, int) or not 1 <= size <= 100:\n")]},
     ['a size that is not an int raises ValueError', DELIVERED]),
    ('size 100 rejected',
     {PAGER: [(SIZE, "    if type(size) is not int or not 1 <= size < 100:\n")]},
     ['size 1 and size 100 are accepted', 'posts are newest first with ties by higher id',
      'export_all returns every post once']),
    ('an empty cursor means the first page',
     {PAGER: [(AFTER, "    after = None if not cursor else decode(cursor)\n")]},
     ['malformed cursors raise ValueError', DELIVERED]),
    ('a cursor that is not a string fails with another error',
     {PAGER: [("    if not isinstance(cursor, str):\n        raise ValueError(f'not a cursor: {cursor!r}')\n", "")]},
     ['malformed cursors raise ValueError', DELIVERED]),
    ('server-side cursors freed on first use',
     {PAGER: [("Page = namedtuple", "import itertools\nSAVED, TOKENS = {}, itertools.count()\nPage = namedtuple"),
              ("    return base64.urlsafe_b64encode(json.dumps(list(position)).encode()).decode()\n",
               "    token = f'c{next(TOKENS)}'\n    SAVED[token] = position\n    return token\n"),
              ("    if not isinstance(cursor, str):\n", "    if not isinstance(cursor, str) or cursor not in SAVED:\n"),
              ("        position = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())\n",
               "        position = list(SAVED.pop(cursor))\n")]},
     ['a cursor can be used twice', 'a cursor works with another size']),
    ('the cursor carries the size of the call that made it',
     {PAGER: [(NEXT, "    return Page(items, encode(key(items[-1]) + (size,)) if len(posts) > size else None)\n"),
              (AFTER, AFTER + "    if after is not None:\n        size, after = after[2], after[:2]\n"),
              ("len(position) == 2", "len(position) == 3")]},
     ['a cursor works with another size']),
    ('the store list sorted in place',
     {PAGER: [(SELECT, "    posts = store.all()\n    posts.sort(key=key, reverse=True)\n"
                       "    posts = [post for post in posts if not post.hidden and (after is None or key(post) < after)]\n")]},
     ['page does not change the store']),
    ('parameters reordered',
     {PAGER: [("def page(store, cursor=None, size=20):", "def page(store, size=20, cursor=None):")]},
     ['export_all returns every post once']),
    ('the regression test only walks a feed that does not change',
     {TEST: "import unittest\n\nfrom feed.pager import page\nfrom feed.store import Post, Store\n\n\n"
            "class Walk(unittest.TestCase):\n    def test_walk(self):\n"
            "        store = Store([Post(n, 1000 + n, 'post') for n in range(1, 26)])\n"
            "        first = page(store, size=10)\n"
            "        second = page(store, cursor=first.next_cursor, size=10)\n"
            "        self.assertEqual([p.id for p in second.items], list(range(15, 5, -1)))\n\n\n"
            "if __name__ == '__main__':\n    unittest.main()\n"},
     ['regression test fails on the shipped pager']),
    ('the regression test reads the cursor',
     {TEST: [("import unittest\n", "import base64\nimport json\nimport unittest\n"),
             ("        self.assertEqual(walk(store, 10), (list(range(20, 0, -1)), 2))\n",
              "        self.assertEqual(walk(store, 10), (list(range(20, 0, -1)), 2))\n"
              "        cursor = page(store, size=10).next_cursor\n"
              "        self.assertEqual(json.loads(base64.urlsafe_b64decode(cursor)), [1011, 11])\n")]},
     ['regression test passes on a reference pager']),
    ('the regression test expects the new post on page two',
     {TEST: [("        second = page(store, cursor=first.next_cursor, size=10)\n"
              "        self.assertEqual(ids(second.items), list(range(15, 5, -1)))\n\n    def test_deleting",
              "        second = page(store, cursor=first.next_cursor, size=10)\n"
              "        self.assertEqual(ids(second.items), [26] + list(range(15, 6, -1)))\n\n    def test_deleting")]},
     [DELIVERED, 'regression test passes on a reference pager']),
]
