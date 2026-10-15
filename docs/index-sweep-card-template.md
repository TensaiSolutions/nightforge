# Fleet card template (index-sweep)

<!-- docKey: index-sweep-card -->

A **fleet card** is the only input the `index-sweep` skill needs. Everything else lives in the
shared skill: the credit and dedup checks, Search Console inspection through OpenSEO, the live
check, the Omega Indexer campaign shape, and the report format.

Put the card in the scheduled task's `SKILL.md`. There is one card for every site you sweep. The
site order is the priority order, and it decides who gets credits when the balance runs short.

**Keep the card out of a public repo.** It names your sites and your OpenSEO project IDs, and
its run log path is your local filesystem. None of that is a credential, but it is not worth
publishing.

---

```markdown
---
name: index-sweep
description: Weekly sweep that sends unindexed sitemap pages to Omega Indexer, one drip campaign per site.
---

**Run the `index-sweep` skill against the fleet card below.** The pipeline lives at
`<path to>/skills/index-sweep/SKILL.md`. Read it first: it is the whole procedure. If that file
does not exist, stop and report exactly that. Do not improvise a sweep.

## Fleet card

| Field | Value |
|---|---|
| **Per-site cap** | **<n>** pages per site per run |
| **Drip days** | **<1-30>** |
| **Minimum gap** | <n> days: skip the whole run if a matching campaign is newer |
| **Resend limit** | skip URLs already in **<n>** or more campaigns |
| **Cool-off** | skip URLs sent in the last **<n>** days |
| **Campaign name** | `<domain> unindexed <YYYY-MM-DD>` |
| **Low-credit floor** | warn under **<n>** credits |
| **Run log** | `<abs path>` (optional) |

### Sites, in priority order

| # | Domain | OpenSEO project ID | Sitemap | Skip patterns | Notes |
|---|---|---|---|---|---|
| 1 | `<domain>` | `<uuid from list_projects>` | `<sitemap URL>` | `<path globs>` | <host quirks, trailing slashes> |
```

---

## Fields

- **Per-site cap.** It bounds credit spend: one credit per link. A cap of 20 across three sites
  costs 60 credits a week at most.
- **Drip days.** Omega spreads submissions over this many days. Match it to the schedule, so a
  drip finishes before the next run looks at its pages.
- **Minimum gap.** It stops a double send on the day the task is created, or after a manual run.
  For a weekly task, 6 days works.
- **Resend limit.** It is set in campaigns, not attempts. A page that two campaigns failed to
  get crawled usually has a content or linking problem that resubmitting will not fix.
- **Cool-off.** It keeps a page out while its last drip may still be running. Set it to at least
  the drip days.
- **Sitemap.** Use the URL exactly as the site serves it. A `www` site must keep `www`, or every
  inspection comes back for the wrong host.
- **Skip patterns.** Use these for pages you never want indexed by force: legal pages, changelog
  posts, login pages.

## Where a gotcha goes

If it is about one site, put it in that site's **Notes** cell. If it is about the tools, put it
in the shared skill.
