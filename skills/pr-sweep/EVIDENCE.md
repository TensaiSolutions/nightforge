# pr-sweep - evidence log

Dated case law behind the pipeline rules. **No run reads this file top to bottom.** `SKILL.md`
holds the procedure; this holds the observations each rule came from. Grep it when a rule looks
wrong, or before changing a rule you did not write.

Repos are named by stable aliases (`alpha` is the first repo swept). Never a private repo's real
name, file contents, or data — this repo is public.

---

## 2026-10-17 — first sweep, `alpha`, 8 open PRs (5 merged, 3 closed, 1 follow-up merged)

**Overlap found late (Step 2, "another open PR overlaps it").** Two PRs both changed the signed-out
homepage: one wrapped it in its own frame to add a footer, the other moved it into the shared
layout, which already rendered that footer. The overlap surfaced only when the second PR's prep
report came back, after the owner had been asked about the first. Cross-PR overlap is now checked
for the whole queue before asking about any one PR.

**Half-done by main (Step 2, "did main already do this?").** The footer PR's extraction of a shared
footer component had already landed on main as part of a footer redesign. Merging main in, the PR's
versions of both files conflicted; main's were taken wholesale, and what the PR still added was
three files.

**A fix for a bug that did not reproduce (Step 2, "reproduce the bug without the fix").** A PR turned
off router transitions so a card click would leave the old page. Its own verification only ran
*with* the change. Run without it, with the route chunk delayed 2.5s in both dev and a production
build, the old page was gone and the loading state showed within 400ms — the layout already keyed
its error boundary on the pathname, so every navigation got a fresh Suspense boundary. Closed as
obsolete; the likely real cause (a cached service-worker shell) had been removed on main.

**Migration version collision (Step 3).** A PR's migration reused a timestamp main had since taken
for a different migration. A clean textual merge; a broken deploy. Renumbered after main's newest.

**Review findings that did not hold (Step 4, "drop").** Across the sweep roughly a third of review
findings were dropped with a reason: pre-existing behaviour, a refactor wider than the PR, or a fix
whose cost exceeded what it prevented. One bot finding marked "Major" (late-generated reports could
miss a since-deleted approval) matched an existing limitation of the same system and would have
needed a new table, trigger and backfill; replied with the trace, left open for the owner, and the
bot agreed. Another proposed publishing a table to realtime to refresh a stale counter — rejected
because that table carries private columns the repo deliberately keeps out of client reads.

**Fragile heuristics are an owner's call (Step 4).** A PR stripped "flavour" sentences from an
external changelog feed with a dozen regexes copied from past entries. Some were broad enough to
delete real content, and new phrasings would pass. Offered: keep only the deterministic half (drop a
fixed footer URL), or merge as a stopgap. Owner chose the deterministic half and asked for an issue
to fix the feed at its source.

**The owner redesigns mid-sweep (Step 7, "change").** A large feature PR (points for approved
photos) was reworked to the owner's narrower rule, then closed when the owner dropped the concept and
asked for a default quest instead. The replacement shipped as a new small PR in the same sweep. Lesson
kept: state your reading of a redesign in one line before building it — "extra point" was read as
replacing the per-photo points, and saying so let the owner correct it.

**Our own review caught what the name promised (Step 4).** The new default quest was first named
"Shared a Game Photo", but quest evidence in that app is a private upload, never the gallery. The
review flagged that the name promised sharing the flow does not do; renamed to "Photographed a Game".

**Merge only on all-green (Step 7).** Every "merge it" waited for the e2e job (~14 minutes), not just
the fast build/unit job, which finishes ~10 minutes earlier. Two merges would otherwise have gone in
on a half-finished run.

**Parallel prep paid for itself (Step 1).** Seven background agents prepped the queue while the owner
read the first write-up; every later PR was presented minutes after the previous decision instead of
after a fresh 10–15 minute analysis. Costs seen: two prepped PRs needed a fresh merge-tree check after
earlier merges (both still clean), and a db-state test timed out under the combined load and passed
alone.

**Verification run on a merged fix (Step 5b).** The default-quest fix was driven with the repo's
own verify skill after it merged. Its stock Help drive passed, but it checked only a sentence the PR
never touched. A throwaway check for the PR's claim (the new quest is on the page, listed first in
the starter set, no writes) was what actually verified it. Two environment gaps: the container's
Chromium was older than the Playwright pin, fixed with an uncommitted `executablePath` edit in the
throwaway worktree. With no Docker daemon there was no local backend for the signed-in quest board,
and the CI screenshot host was blocked. So the signed-in half was reported as unverified here and
covered by the database suite and CI's e2e run, not by green unit tests.

## 2026-10-17 — second sweep, `beta`, 13 open PRs (12 merged, 1 held)

**Two holds, and why a held PR stays watched (Step 7, "hold").** The owner said "not now" on one
PR, swept on, and said "merge" on it hours later; the base had moved, so it was merged in again and
re-validated before the merge. A second PR, a large feature, was held because the owner would merge
it from another session. Over the next day it took one automatic and three owner-requested bot
reviews, four real findings, three fix commits, and a CI run per push. The old Step 7 unsubscribed from every finished
PR, which would have dropped all of that. Neither PR was merged by the sweep without a fresh "merge".

**Full bot reviews kept finding real bugs after our review passed (Step 4).** On the held feature
PR, an incremental bot review found two real issues: the draft page showed a generated image on a
site whose address was not https, while the posts would carry none; and an unranged read could
silently stop at the API's row cap. Then the owner asked for full reviews. The first found that a
settings save rewrote every queued post even when only branding changed, undoing an operator's
"retry as text only". The second found that a failure in the optional image step aborted the
update that removes deleted media from queued posts, so a deleted screenshot could still publish.
Two of the four sat in code our own fix rounds had added. The third full review came back clean.

**Fixes got tests that fail without them (Step 5).** A narrow-width header scrolled the page
sideways only between 561 and 577 pixels; a browser test at those widths now fails without the
fix. A Back-button fix got a real browser test, and writing it taught its own lesson: Chrome drops
the history entry for a navigation that has no user gesture, so the first version of the test
landed on about:blank. It now holds the response until the page is clicked. A shared https check
that two code paths now call got unit tests for https, http, and a trailing slash.

**Direction lives in docs, not commits (Step 2).** The repo's CLAUDE.md recorded a change of target
user two days before the sweep, with rules for product copy. No commit to the PRs' files reflected
it, so the base-commit list could not surface it; each PR's user-facing copy was read against the
current rules directly.

**Migration history out of reach (Step 3).** The held PR adds two migrations, and the repo applies
migrations to production when a PR merges. The connected database tool was scoped to a different
project, so the migration history could not be read. The write-up asked the owner whether the first
migration had already been run by hand, rather than assuming it had not.

**Bot noise (Noise to ignore).** Every fix pushed drew a review-bot edit marking its thread
"Addressed in commit …" and an autofix bot's new thread saying the finding was already handled.
Each autofix thread was resolved without a reply. The account-wide review allowance ran out after
each full review, and its "review limit reached" notice needed no action.
