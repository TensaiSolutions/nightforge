---
name: ga-traffic-report
description: Pulls a week of GA4 traffic for every OpenSEO project, triages what needs fixing, keeps site audits on a cadence, and republishes one report artifact. Use from a scheduled task whose card names the data folder and the artifact; see docs/ga-traffic-report-card-template.md.
---

# ga-traffic-report

<!-- @doc:ga-traffic-report-card -->

Build the owner's GA traffic report and republish it to its artifact. The scheduled task holds a
**report card** (template: `docs/ga-traffic-report-card-template.md`). Read it first: every
**bold field** below comes from it. If the card is missing a field this file needs, stop and say
which one. Do not guess.

Read-only toward every account: never change anything in OpenSEO, GA4 or Search Console, and never
call an OpenSEO tool that spends credits (no get_serp_results, rank tracker runs, backlinks, keyword
research). One exception: the site audits in Step 1.4 (run_site_audit, plus whoami to watch credits).

This skill's folder (the one holding this file, `build.py` and `template.html`) is the **skill
folder**. The card's **Data folder** holds this run's files: `report.json`, `history.json` and
`report.html`.

## Step 1 - gather data (free OpenSEO reads, plus the audits in 1.4)

Load the tools with ONE ToolSearch call:
select:mcp__openseo__list_projects,mcp__openseo__get_google_analytics_traffic_acquisition,mcp__openseo__get_google_analytics_page_performance,mcp__openseo__get_google_analytics_organic_overview,mcp__openseo__get_google_analytics_key_events,mcp__openseo__get_google_analytics_measurement_health,mcp__openseo__get_search_opportunities,mcp__openseo__list_site_audits,mcp__openseo__get_audit_issues,mcp__openseo__run_site_audit,mcp__openseo__whoami

Date windows (in the card's **Time zone**):
- Current = last 7 complete days, ending yesterday. Previous = the 7 days before that.

1. list_projects. For EVERY project call traffic_acquisition (channel_group, comparePreviousPeriod true).
   Error code `ga4_not_connected` = put it in `notConnected` with its actionUrl, not an error.
2. For each connected site, call (in parallel where you can):
   - traffic_acquisition, source_medium, current window, limit 5.
   - page_performance, channel "all", current window, limit 8.
   - organic_overview over the last 28 days ending yesterday, trend daily (sparkline only).
   - key_events, breakdown event, channel "all", current window, comparePreviousPeriod true.
   - measurement_health (GA setup problems).
   - search_opportunities, default 28-day window, limit 5. If it errors because Search Console
     is not connected, set health.searchConsole=false; that is not a run error.
   - list_site_audits; if one exists, get_audit_issues severity critical and severity warning,
     limit 1 each, just to read the counts from `summary`.
3. Any other failed call: add {site, call, message (exact error text)} to `errors` and keep going.
4. Site audits (the one credit-spending step; cadence from the card's **Audits** fields). For
   EVERY project that has a `domain` (GA connected or not; skip projects with no domain), call
   list_site_audits. Skip a site with an audit in progress. Otherwise decide, at most ONE audit
   per site per run:
   a. Full audit, due when the newest completed audit with `ranLighthouse: true` finished
      **Full audit every** days ago or more (or there is none): run_site_audit with
      renderJavaScript true, runLighthouse true, maxPages 1000 (the JS-render cap). This is the
      costly one: OpenSEO bills JS rendering per page rendered (its estimate: $0.07-$0.39 per 100 pages).
   b. Plain audit, due when the newest completed audit of any kind finished **Plain audit every**
      days ago or more (or there is none): run_site_audit with renderJavaScript false,
      runLighthouse false, maxPages 5000.
      Exception: on a site whose last plain crawl found more than 1000 pages, a full audit cannot
      cover every page, so only plain audits reset its plain-audit clock.
   If both are due, run (a) this time; (b) follows on a later run if still due.
   url = the `startUrl` of the site's newest audit (some sites redirect to www), else "https://<domain>/".
   Never change these settings otherwise. Start at most **Max audits per run**, most overdue
   first; the rest wait for the next run. Call whoami before the first start; if creditsRemaining
   is under **Credit floor**, start no full audits and add a "now" action saying credits are low.
   Do not wait for audits to finish; this run reads the previous audit, and the next run picks up
   the new one. Add an "fyi" action per started audit: id `<site>:audit-started:<auditId>`,
   title says plain or full, why = last audit date -> today, link = the run's `meta.url`.
   Call whoami again at the end and put credits used this run in an "fyi" action
   (`all:credits:audits`). If run_site_audit errors (for example, not enough credits), add it
   to `errors` and keep going.

How to read the tool output (learned on the first run, 2026-10-05):
- Site totals: no call returns one. Sum `comparison.rows[].metrics.sessions.{current,previous}`
  from the channel_group call (null = 0). Site engagement rate = sum(engagedSessions) / sum(sessions)
  from the same block. Site keyEvents [cur, prev] = sum of keyEvents across those channel rows.
- Channel `engagementRate` = current week only (null if the channel had no sessions this week).
- organic_overview `trend[]` skips zero days and uses YYYYMMDD dates: zero-fill to 28 values.
- page_performance rows carry `hostName`: put it in topPages[].host.
- search_opportunities has no query field and its window ends ~3 days back (Search Console lag);
  ignore the `source_time_zones_differ` warning. Rows with joinStatus "gsc_only" have score null.
  Set health.searchConsole=false only when the call errors for a missing connection; 0 rows means
  connected but nothing in positions 4-20.
- get_audit_issues `summary` is an array of {issueType, title, severity, count}: sum `count` for
  the total; empty array = 0. Audit date = `completedAt` from list_site_audits.
- measurement_health `keyEvents[].createTime` tells you when a key event was set up.
- Links: GA and opportunity tools return no URL. Use the project `url` from list_projects;
  for audit actions use `meta.url` from list_site_audits.

## Step 2 - triage (the "Needs you" list)

Make one `actions` entry per thing the owner should do. Give each a stable `id` built as
`<site>:<kind>:<target>` (e.g. `shop:bot:direct`, `shop:seo-opportunity:/guides/sizing/`)
so the same problem keeps the same id on every run. build.py rewrites the site part from `site`,
so only kind and target must stay the same. That id is how the page shows NEW vs "open since".

priority "now" (something is broken or losing data):
- tracking: a connected site with 0 sessions this week, or measurement_health reports issues.
- traffic-drop: total sessions down 30%+ week over week, when the previous week had 50+.
- conversions: a key event that had 3+ last week and 0 this week. Skip events whose
  createTime falls inside either window (new setup, not a real change).
- site-health: the latest site audit has critical issues (name the top issue type). The audit can
  be older than the fix: if a merged PR since `completedAt` clearly addresses the issue, say so in
  `why` and set priority "fyi" (the next audit will confirm it).
priority "soon" (worth doing this week):
- seo-opportunity: at most 2 per site from search_opportunities: the top 2 by impressions among
  pages ranking 4-10 with CTR under 2% and 200+ impressions. Fix = open the page's queries in
  Search Console and rewrite the title and meta description to match the top query; name the path.
- bot: a channel whose sessions jumped 40%+ with engagement rate under 5% (Direct is the usual
  one), or that sits under 5% engagement with 100+ sessions in both weeks (ongoing bot share).
  Call it "likely bot or spam traffic", never real growth, and leave it out of the headline growth
  story. Fix = check source/medium and hostnames in GA4; add a data filter only if it keeps happening.
- tracking-hygiene: top pages include a host that is not the live site (localhost,
  deploy-preview-*, *.netlify.app, *.pages.dev). GA is counting dev or preview visits.
  Fix = only load the GA tag on the production hostname (gate the `gtag('config', …)` call on
  `location.hostname`).
- site-health: no completed site audit in twice **Plain audit every** days even though Step 1.4
  should have started one (it failed or keeps getting skipped). Fix = check the audit page for the error.
priority "fyi": anything else the owner should know but need not act on.

Every action needs: title (one short sentence), why (the number that triggered it, with
before -> after), fix (one concrete step, plain words), link (the OpenSEO project or tool URL
from the tool's `meta.url`). Do not invent problems to fill the list. An empty list is a good result.
Do not raise tagging for any site in the card's **Parked sites**. They may still appear in
`notConnected`, with "parked": true.

## Step 3 - write report.json

Write `report.json` in the **Data folder**, UTF-8, exactly this shape ([current, previous] pairs):

{
  "generatedAt": "<ISO timestamp with offset>",
  "window": {"current": ["YYYY-MM-DD","YYYY-MM-DD"], "previous": ["YYYY-MM-DD","YYYY-MM-DD"]},
  "headline": "1-2 plain sentences: the real story across all sites this week (bots excluded)",
  "doThisNext": "the single most useful action across all sites, or null",
  "actions": [{"id","priority","site","kind","title","why","fix","link"}],
  "sites": [{
    "name", "domain", "projectUrl", "status": "ok" | "error", "error": null,
    "sessions": [cur, prev], "engagementRate": [cur, prev], "keyEvents": [cur, prev],
    "organicDaily": [28 daily organic session counts, oldest first],
    "channels": [{"name", "sessions": [cur, prev], "engagementRate", "bot": true|false}],
    "sources": [{"name": "source / medium", "sessions"}],
    "topPages": [{"host", "path", "views", "users"}],
    "events": [{"name", "count": [cur, prev]}],
    "opportunities": [{"page": "/path", "position", "impressions", "clicks", "ctr", "score", "note"}],
    "health": {"gaIssues": ["..."], "audit": {"date","critical","warning"} | null, "searchConsole": true|false},
    "standouts": ["1-3 plain bullets: biggest real changes and a best guess why"]
  }],
  "notConnected": [{"name", "domain", "actionUrl", "parked": true|false}],
  "errors": [{"site", "call", "message"}]
}

Rates are 0-1 fractions. Order sites by current sessions, highest first. Plain English in every
string: short sentences, define jargon in a few words. `note` on an opportunity says why it is
worth it in under 12 words.

## Step 4 - build and publish

1. Run: python "<skill folder>/build.py" "<Data folder>"
   Non-zero exit = stop, report the exact error, do not publish.
2. Artifact tool, action "read", url = the card's **Artifact** (a publish to an unread artifact
   is refused).
3. Artifact tool publish with that url and file_path `<Data folder>/report.html`.
   Never publish without the url (that makes a duplicate). Do not pass icon or title.
   Do not edit template.html or build.py unless the build is actually broken; if you do, say
   what and why, and edit them in a nightforge worktree with a PR, never the installed copy.

## Step 5 - reply in 4 lines or fewer

- Total sessions across sites, change vs last week.
- Action counts (fix now / this week), naming every "fix now" item.
- Anything that failed, named.
- The artifact link.
