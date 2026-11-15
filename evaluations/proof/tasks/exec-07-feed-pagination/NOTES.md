# exec-07-feed-pagination: fairness notes

The solver never sees this file, the grader, the exemplars or `impls/`.

## What the task is

Fix a reported duplicate in a cursor-paged feed, make `feed.pager.page` follow the whole paging contract in `docs/api.md`, and deliver a regression test that fails on the shipped pager, passes on the fix, and passes on any pager that follows the contract.

## Why it is harder than the tasks it replaces

The replaced tasks gave one function and a complete numbered specification. Here the bug report shows one symptom, the offset cursor, while the shipped pager breaks the contract in five more independent ways: ties are left in insertion order, hidden posts are dropped after the page is cut so pages run short, a feed that ends at a page boundary gets an extra empty page, and neither `size` nor the cursor is validated. The rules sit in prose sections of `docs/api.md` and in the `Store.all` docstring. The visible tests pass on the shipped pager and on every mistake below. The regression test is a second deliverable that the grader runs against three pagers, one of which uses a cursor form the solver never sees.

## What the bad exemplar does

It is the first fix a quick solver writes: the cursor becomes the last item's `created_at` and the next page takes posts older than that. The reported duplicate is gone. Posts that share a timestamp across a page boundary are skipped, ties are still in insertion order, and the other shipped defects stay. Its regression test reproduces `BUG.md` only. It passes `test_feed.py`.

## Hidden checks and the sentence each follows from

| Check | Stated rule | Where |
|---|---|---|
| posts are newest first with ties by higher id | "The feed is newest first ... Posts with equal `created_at` are ordered by `id`, higher id first." `all()` returns posts "in the order they were added. That is not time order" | `docs/api.md`, Order; `Store.all` docstring |
| ties split across a page boundary are neither skipped nor repeated | "Every post that exists for the whole walk is returned exactly once, in feed order." | `docs/api.md`, Walks while the feed changes |
| the reported new post does not repeat an item | "Expected: page 2 starts with the post after the one that ended page 1." | `BUG.md` |
| a post added during a walk appears exactly when it sorts after the position | "A post added during the walk is returned exactly when it sorts after the walk's position, that is, after the last item already returned. A post that sorts before the position is not returned in this walk." Ties with the position follow from the Order section | `docs/api.md`, Walks while the feed changes; Order |
| a post deleted before it is reached does not appear | "A post deleted before the walk reached it is not returned." and "The same holds when nothing remains after a cursor's position, for example because the remaining posts were deleted after the cursor was issued." | `docs/api.md`, Walks while the feed changes; End of a walk |
| deleting returned posts does not break the walk | "Deleting a post the walk already returned, the last one included, does not change the rest of the walk." and "A cursor stays valid ... including after the post it was taken from is deleted." | `docs/api.md`, Walks while the feed changes; Cursors |
| a feed ending at a page boundary has no empty last page | "when the feed ends exactly at a page boundary, that full page already has `next_cursor` None." | `docs/api.md`, End of a walk |
| an empty feed has no items and no cursor | "An empty feed returns a page with no items and `next_cursor` None." | `docs/api.md`, End of a walk |
| a feed that fits one page has no cursor | "`next_cursor` is None exactly when no post remains after the last item of the page." | `docs/api.md`, End of a walk |
| hidden posts are never returned | "`page` never returns it" | `docs/api.md`, Hidden posts |
| hidden posts do not shorten a page | "it does not count toward `size`" and "A page holds `size` posts, unless fewer than `size` posts remain" | `docs/api.md`, Hidden posts; Page size |
| hidden posts after the last visible post add no page | "Everywhere below, \"post\" means a post that is not hidden." with "`next_cursor` is None exactly when no post remains after the last item of the page." | `docs/api.md`, Hidden posts; End of a walk |
| size outside 1 to 100 raises ValueError | "`size` must be an int from 1 to 100. ... Any other value raises ValueError." | `docs/api.md`, Page size |
| a size that is not an int raises ValueError | The same sentences and "A bool is not accepted." The values tested are `20.0`, `'20'`, `True` and `None` | `docs/api.md`, Page size |
| size 1 and size 100 are accepted | "`size` must be an int from 1 to 100." | `docs/api.md`, Page size |
| malformed cursors raise ValueError | "These, for example, must raise ValueError: the empty string `''` ...; text that `page` never returned, such as `'not-a-cursor'`; a value that is not a string, such as the int `42`." Only these three values are tested. A forged cursor in a valid form is something `page` could have returned, so nothing tests it, and the reference pager accepts it | `docs/api.md`, Cursors |
| a cursor can be used twice | "It can be used any number of times" | `docs/api.md`, Cursors |
| a cursor works with another size | "and with a different `size` from the call that returned it. The page always starts just after the cursor's position." | `docs/api.md`, Cursors |
| page does not change the store | "It does not change the store, and that includes the list `Store.all()` returns." and "This returns the store's own list, not a copy, so callers must not change it." | `docs/api.md`, Side effects; `Store.all` docstring |
| export_all returns every post once | "Keep the signature of `page`" and "`feed/api.py` and `feed/export.py` call `page` and must keep working." `export_all` passes the cursor and size by position | `prompt.md`; `feed/export.py` |
| regression test fails on the shipped pager | "It must fail on the code as shipped today" | `prompt.md` |
| regression test passes on the delivered pager | "and pass on your fix" | `prompt.md` |
| regression test passes on a reference pager | "It must also pass on any pager that follows `docs/api.md`, so it must not depend on what a cursor looks like." The reference in `impls/pager.py` follows the contract with a plain-text cursor | `prompt.md`; `impls/pager.py` |

The grader's store is the workspace's `Store`, copied line for line, plus a read counter that turns an endless walk into a failed check. Every walk the grader makes starts from `cursor=None` and uses only cursors the delivered pager returned. The grader calls `page` with `cursor=` and `size=` keywords, so only `export_all` depends on parameter order, which the prompt fixes.

`variants/exec-07-feed-pagination.py` holds one plausible mistake per rule. `test_bench.py` checks that each fails exactly the checks it lists.

The prompt states the limit that applies to each run of the delivered test: "It must be deterministic and finish in a few seconds. A run is stopped after 30 seconds."
