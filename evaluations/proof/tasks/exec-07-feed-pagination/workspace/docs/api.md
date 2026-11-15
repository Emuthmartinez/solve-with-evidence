# Feed paging contract

`feed.pager.page(store, cursor=None, size=20)` returns one page of the home feed as `Page(items, next_cursor)`. `items` is a list of `Post` objects from the store. A client scrolls by passing `next_cursor` back as `cursor`. Following cursors from the first page until `next_cursor` is None is a walk.

The mobile apps, `feed/api.py` and `feed/export.py` rely on every rule in this document.

## Order

The feed is newest first: a post with a larger `created_at` comes before a post with a smaller one. Posts with equal `created_at` are ordered by `id`, higher id first. Ids are unique, so for any two posts this order says which comes first.

## Hidden posts

A post whose `hidden` is True was removed by moderation. `page` never returns it, and it does not count toward `size`. Everywhere below, "post" means a post that is not hidden.

## Page size

`size` must be an int from 1 to 100. A bool is not accepted. Any other value raises ValueError.

A page holds `size` posts, unless fewer than `size` posts remain after the position the page starts from. Then it holds all of them. So a page shorter than `size` is always the last page of a walk.

## End of a walk

`next_cursor` is None exactly when no post remains after the last item of the page. A walk therefore never ends with an extra empty page: when the feed ends exactly at a page boundary, that full page already has `next_cursor` None.

An empty feed returns a page with no items and `next_cursor` None. The same holds when nothing remains after a cursor's position, for example because the remaining posts were deleted after the cursor was issued.

## Cursors

A cursor marks a position in the feed: just after the last item of the page that returned it. It is an opaque string. Callers must not take it apart, build one, or depend on its form, which may change in any release.

`cursor=None` asks for the first page. Any other `cursor` must be a string that `page` returned as a `next_cursor`. A value that `page` could never have returned as a `next_cursor` raises ValueError. These, for example, must raise ValueError:

- the empty string `''`, which `feed/api.py` passes for `?cursor=`;
- text that `page` never returned, such as `'not-a-cursor'`;
- a value that is not a string, such as the int `42`.

A cursor marks a position, not a page. It can be used any number of times, and with a different `size` from the call that returned it. The page always starts just after the cursor's position. A cursor stays valid while the feed changes, including after the post it was taken from is deleted.

## Walks while the feed changes

Posts are added and deleted while clients scroll. A walk stays consistent:

- Every post that exists for the whole walk is returned exactly once, in feed order.
- A post added during the walk is returned exactly when it sorts after the walk's position, that is, after the last item already returned. A post that sorts before the position is not returned in this walk. The client shows it on its next refresh.
- A post deleted before the walk reached it is not returned.
- Deleting a post the walk already returned, the last one included, does not change the rest of the walk.

## Side effects

`page` only reads the store. It does not change the store, and that includes the list `Store.all()` returns.
