# Code Review — Improvement Opportunities

_Arizona Power Outage Archive. Full-codebase review of logic correctness, performance,_
_code quality, security, and robustness. Line references are approximate to the reviewed revision._

Findings are grouped by area and ordered by severity within each group.
Each item lists the location, the problem, the impact, and a suggested fix.

---

## 1. Correctness / Logic bugs

### 1.1 — Snapshot deduplication is silently broken (HIGH)

**Where:** `scripts/archive.py:30-52`, `scripts/utils.py:31-44`, `providers/base.py:13-19`

`save_snapshot()` tries to avoid writing an identical snapshot by comparing hashes:

```python
if calculate_hash(old_data) == calculate_hash(data):
    return False, latest
```

But `calculate_hash()` hashes the **entire** `data` dict, which includes
`metadata.scraped_at = current_time()` — a fresh wall-clock timestamp on every run.
Two scrapes with byte-for-byte identical outages therefore always produce different
hashes, so the equality check is never true and a new file is **always** written.

**Verified empirically:** scanning the committed archive, APS has 10 and SRP has 5
consecutive snapshot pairs whose `summary` + `outages` are identical but were saved as
separate files anyway. The "No changes detected" branch in `scripts/run.py:38` is
effectively dead code.

**Impact:** the archive grows with redundant snapshots (an hourly cron never dedups),
git history bloats, and the dashboard double-counts identical records in historical mode.

**Fix:** hash only the content that defines a "change" — exclude the volatile timestamp.
For example hash `{"summary": ..., "outages": ...}` (or strip `metadata.scraped_at`
before hashing). Add a regression test with two identical payloads and assert the
second `save_snapshot` returns `(False, path)`.

---

### 1.2 — Inconsistent snapshot validation across providers (MEDIUM)

**Where:** `providers/tep.py:42-90` (and `providers/ues.py` via inheritance)

Most providers call `self.validate_snapshot(...)` inside `fetch_data`/`parse_*`
(`aps.py:66`, `ssvec.py:68`, `ed3.py:65`, `srp.py:85`, `nisc.py:247`). **TEP and UES
do not** — `TEPProvider.parse_data` returns a raw dict. Validation only happens because
`scripts/run.py:21` calls `validate_snapshot` externally.

Two problems fall out of this:

1. Providers that validate internally are validated **twice** per run (once inside,
   once in `run.py`) — wasted work and a confusing contract.
2. Anyone who calls `TEPProvider().fetch_data()` directly (e.g. a future script or test)
   gets an **unvalidated** snapshot, unlike every other provider.

**Fix:** pick one contract. Either (a) have every `fetch_data` return validated data and
drop the redundant `validate_snapshot` call in `run.py`, or (b) never validate inside
providers and always validate in `run.py`. Option (a) is safer because it keeps each
provider self-contained.

---

### 1.3 — `/api/timeline` reimplements outage filtering and ignores display mode (MEDIUM)

**Where:** `app.py:162-273` vs `dashboard/filters.py:150-196`

The timeline endpoint hand-rolls the same outage-level filtering (cause, active_only,
min/max customers, unknown-customer handling, time-of-day) that already lives in
`apply_filters`. The two copies have already drifted:

- `apply_filters` respects `display_mode` (latest / snapshot_at_time / historical /
  unique_outages); the timeline endpoint always treats data as a date-range scan and
  ignores `display_mode` entirely.
- The min/max customer integer coercion is duplicated a third time
  (`app.py:216-222`, `filters.py:64-71`).

**Impact:** the timeline chart and the map/table can silently disagree because they run
different filtering code. Any future filter fix must be made in two places.

**Fix:** extract the per-outage predicate into one shared helper (e.g.
`filters.outage_matches(outage, parsed_params)`) and have both `apply_filters` and the
timeline endpoint call it. Parse the numeric params once in `parse_filter_params`.

---

### 1.4 — MDT timestamps are relabeled as MST without converting the time (LOW)

**Where:** `dashboard/normalizer.py:14-26`, `dashboard/filters.py:4-15`

`normalize_time` strips a `" MDT"`/`" UTC"`/`" GMT"` suffix and unconditionally
re-appends `" MST"` without adjusting the underlying hours. If any upstream feed ever
emits a UTC or MDT string, the stored time is silently wrong (off by hours) while
*looking* authoritative. Arizona is MST year-round so this is currently latent, but the
suffix list explicitly includes UTC/GMT/MDT, implying such inputs are expected.

**Fix:** either drop UTC/GMT from the accepted suffixes (fail loudly instead), or
actually convert to Arizona time when a non-MST zone is detected.

---

### 1.5 — Empty-archive path can crash the frontend metadata load (LOW)

**Where:** `static/js/app.js:98-108`

Inside `if (meta.date_bounds)`, the code does
`meta.date_bounds.earliest.split(' ')[0]` without checking that `earliest`/`latest` are
non-null. On a fresh/empty archive both are `null` (`app.py:84-85`), so `.split` throws
and metadata init aborts.

**Fix:** guard `if (meta.date_bounds && meta.date_bounds.earliest && meta.date_bounds.latest)`.

---

## 2. Performance / Scaling

### 2.1 — Every API request re-scans the whole archive; a page load triggers 3 full scans (HIGH)

**Where:** `app.py:75, 151, 172, 282` all call `scan_archive(DATA_DIR)`

A single dashboard load calls `/api/metadata`, `/api/outages`, and `/api/timeline`, each
of which independently walks the data directory and rebuilds the full in-memory snapshot
list (`dashboard/archive_reader.py:125-162`). The per-file parse is cached by mtime
(good), but the directory walk, `getmtime` per file, and list assembly happen on every
request. With thousands of snapshots × multiple endpoints × multiple polling clients this
is a lot of repeated O(N) work.

**Fix:** cache the assembled `(snapshots, stats)` result keyed by a cheap directory
fingerprint (file count + max mtime — you already compute exactly this in
`/api/file-status`). Invalidate when the fingerprint changes. Also consider computing
`snapshots` once per request and threading it into the metadata/outages/timeline handlers
rather than scanning three times.

### 2.2 — `/api/file-status` walks the entire tree on every poll (MEDIUM)

**Where:** `app.py:39-66`, polled every `AUTO_REFRESH_SECONDS` (default 60s) by
`static/js/app.js:541`

`os.walk` + `getmtime` over every `.json` file, per client, per minute. It duplicates the
fingerprint logic that a cached scan (2.1) would already maintain.

**Fix:** share one fingerprint function between `file_status` and the scan cache.

### 2.3 — Unbounded in-memory cache holds the entire archive (MEDIUM)

**Where:** `dashboard/cache.py:4-51`

`global_cache` never evicts except when a file disappears. Every parsed snapshot (full
normalized outage lists) stays resident, so process memory grows roughly linearly with
the archive forever. On a small always-on host (the README targets a Raspberry Pi) this
will eventually matter.

**Fix:** add an LRU bound (e.g. `functools.lru_cache`-style or `OrderedDict` with a cap),
or store only what the endpoints actually need.

### 2.4 — Archive/git repo grows without bound (LOW, design)

Snapshots are committed to git hourly and never pruned. Combined with 1.1 (redundant
snapshots), repo size and clone time grow indefinitely. Consider a retention/rollup
policy (e.g. thin older snapshots to daily) or storing raw snapshots outside git.

---

## 3. Code quality / Cleanliness

### 3.1 — Dead / unused code

- `providers/tep.py:92-97` — `_to_int` is never called (customers go through
  `parse_customer_count`, floats through `_to_float`).
- `providers/__init__.py` — empty file (fine, but the real provider registry lives in
  `scripts/run.py:45-55`; consider centralizing the provider list here so `app`/tests can
  import one canonical list).

### 3.2 — Retry logic is applied inconsistently (MEDIUM)

**Where:** `scripts/http.py` vs `providers/tep.py:28-33`

`request_with_retries` wraps APS, SRP, SSVEC, ED3. **TEP/UES call `requests.post`
directly** with no retry/backoff, so a transient 502 fails the whole run for those
providers while the others self-heal. NISC has its own bespoke retry loop
(`nisc.py:24-34`) because it drives Selenium — acceptable, but the HTTP providers should
be uniform.

**Fix:** route TEP/UES through `request_with_retries` (it accepts `requests.post` as the
`request` callable and forwards `**kwargs`).

### 3.3 — Duplicated integer-parsing and timestamp-suffix logic

- min/max customer coercion duplicated 3×: `app.py:216-222`, `filters.py:64-71`.
- suffix stripping duplicated: `normalizer.strip`-style loop in
  `dashboard/normalizer.py:15-18` and `dashboard/filters.py:12-14`. Factor into one
  `TZ_SUFFIXES` constant + helper in a shared module.

### 3.4 — Near-identical `format_time` implementations

`providers/nisc.py:292-317` and `providers/tep.py:106-132` share the same "guess the year
within a 183-day window" algorithm almost verbatim. Lift it into a shared helper (e.g.
`base.py` or a `providers/timeparse.py`) parameterized by the accepted formats.

### 3.5 — Logging configured twice

`scripts/logger.py:3` and `app.py:13` both call `logging.basicConfig(...)`. The second is
a silent no-op (handlers already exist), and the two use different logger names
(`power-outage-archive` vs `outage_dashboard`). Pick one configuration point and one
logger naming convention.

### 3.6 — Typos preserved from upstream reduce readability

`providers/ed3.py:46,70` use `"CutomersAffected"` / `"TotalCustomers"` — the first is an
upstream misspelling (`Cutomers`). Add a brief comment noting it mirrors the source XML
so a future reader doesn't "fix" it and break parsing.

---

## 4. Security

### 4.1 — Unescaped external data rendered via `innerHTML` (stored XSS) (MEDIUM)

**Where:** `static/js/map.js:64-96` (`buildPopupHtml`), `static/js/table.js:143-152`
(row template), `static/js/app.js` chip/toast builders

Outage fields (`cause`, `comments`, `boundary`, `city`, etc.) originate from third-party
utility APIs and are injected straight into `innerHTML` with no escaping. If any provider
feed ever contains HTML/script (or is compromised/MITM'd), it executes in the dashboard.
The data is archived verbatim, so a malicious value would persist.

**Fix:** escape values before interpolation (a small `escapeHtml()` helper), or build DOM
nodes with `textContent`. At minimum apply it to the free-text fields (`comments`,
`cause`, `boundary`, `city`).

### 4.2 — Error messages leak internals to API clients (LOW)

**Where:** `app.py:78, 155, 286`

Handlers return `f"... {e}"` (raw exception text, which can include filesystem paths)
directly in JSON/CSV responses. Fine for a LAN tool, but log the detail and return a
generic message if this is ever exposed beyond the local network.

### 4.3 — Anti-bot evasion in the Selenium scraper (INFO)

**Where:** `providers/nisc.py:38-62`

The NISC scraper spoofs a real Chrome UA, hides `navigator.webdriver`, and disables
automation switches to look like a human browser. This is scraping public outage maps, so
it's likely acceptable, but it's worth a comment documenting intent and confirming it
doesn't violate the sites' terms.

---

## 5. Robustness / Edge cases

### 5.1 — `float`-valued customer strings silently become 0

**Where:** `dashboard/normalizer.py:41-48`

`int(customers.replace(",", ""))` throws on `"12.5"` or `"1.2k"` and is swallowed to `0`.
The stricter `base.parse_customer_count` (used at ingest) already rejects these, so this
only matters for re-reading legacy/hand-edited files — but worth aligning the two paths.

### 5.2 — `snapshot_at_time` default uses local server time labeled MST

**Where:** `dashboard/filters.py:94`

`datetime.now().strftime("%Y-%m-%d %H:%M:%S MST")` uses the server's local zone but labels
it MST. On a non-Arizona server the default "now" cutoff is wrong. Use
`datetime.now(ARIZONA_TZ)` (as `current_time()` already does).

### 5.3 — Coordinate marker lookup uses exact float equality

**Where:** `static/js/map.js:180-184`

`zoomToMarker` matches by `layer.getLatLng().lat === lat`. Exact float `===` is fragile;
if Leaflet ever reprojects/rounds, the row-click zoom silently finds nothing. Compare with
a small epsilon, or store the outage id on the marker and match on that.

### 5.4 — `PORT`/`AUTO_REFRESH_SECONDS` accept nonsensical values

**Where:** `app.py:20-29`

`int()` guards `ValueError` but not negatives/zero (`PORT=-1`, `AUTO_REFRESH_SECONDS=0`
→ tight polling loop). Clamp to sane ranges.

---

## 6. Testing gaps

- No test asserts the dedup behavior of `save_snapshot` (which is why 1.1 went unnoticed).
  Add one identical-payload test.
- `dashboard/filters.py` and the `/api/timeline` aggregation carry the most logic but the
  timeline endpoint appears untested (`tests/test_dashboard_api.py` exists — confirm it
  covers timeline + each `display_mode`).
- No provider test for TEP's missing internal validation (1.2).

---

## 7. Quick-win checklist

| # | Item | Effort | Payoff |
|---|------|--------|--------|
| 1.1 | Exclude `scraped_at` from the dedup hash | S | High — stops archive bloat |
| 2.1 | Cache assembled scan by dir fingerprint | M | High — cuts request latency |
| 1.3 | Share one outage-predicate between filters & timeline | M | Med — kills drift |
| 3.2 | Route TEP/UES through `request_with_retries` | S | Med — reliability |
| 4.1 | Escape external strings before `innerHTML` | S | Med — XSS hardening |
| 1.2 | One validation contract across providers | S | Med — consistency |
| 3.1/3.4/3.5 | Remove dead code, dedup `format_time`, single log config | S | Low — cleanliness |

_Highest-value first: fix 1.1 (the dedup bug) and 2.1 (redundant full scans) — together_
_they address the archive's two biggest issues, storage growth and request cost._
