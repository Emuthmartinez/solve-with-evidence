# FEED-311: a post shows up twice while scrolling

Reported by support, from three user tickets this week.

## Steps

1. Open the home feed. The app loads page 1 with 10 posts.
2. A friend publishes a post.
3. Scroll down. Page 2 starts with the post that ended page 1.

Expected: page 2 starts with the post after the one that ended page 1.

## Reproduction

All posts here have different `created_at` values.

```python
from feed.pager import page
from feed.store import Post, Store

store = Store([Post(n, 1000 + n, f'post {n}') for n in range(1, 26)])
first = page(store, size=10)                 # posts 25 down to 16
store.add(Post(26, 1026, 'new post'))
second = page(store, first.next_cursor, size=10)
print(second.items[0].id)                    # prints 16, already on page 1; expected 15
```
