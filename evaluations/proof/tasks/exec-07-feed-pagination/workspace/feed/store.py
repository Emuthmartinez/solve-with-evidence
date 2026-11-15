"""In-memory post store. The service's database-backed store has the same contract, and tests use this one."""
from collections import namedtuple

Post = namedtuple('Post', 'id created_at title hidden', defaults=(False,))
Post.__doc__ = """One post.

id: int, unique in the store.
created_at: int, seconds since the epoch, when the post was published.
title: str.
hidden: bool, True when moderation removed the post. Hidden posts stay in the store.
"""


class Store:
    def __init__(self, posts=()):
        self._posts = []
        for post in posts:
            self.add(post)

    def add(self, post):
        """Add a post. An id the store already holds raises ValueError."""
        if any(existing.id == post.id for existing in self._posts):
            raise ValueError(f'duplicate post id: {post.id}')
        self._posts.append(post)

    def delete(self, post_id):
        """Remove the post with this id. An unknown id raises KeyError."""
        for index, post in enumerate(self._posts):
            if post.id == post_id:
                del self._posts[index]
                return
        raise KeyError(post_id)

    def all(self):
        """Every post, hidden ones included, in the order they were added.

        That is not time order: imported and delayed posts arrive with an older created_at.
        This returns the store's own list, not a copy, so callers must not change it."""
        return self._posts
