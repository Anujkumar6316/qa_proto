# Plan: Replace agent-browser with Playwright

**Scope:** Phase 1 (crawl), Phase 4 (execute), Phase 5 (replay), health probe, cache hashing
**Goal:** cut per-step latency, remove stale-ref failures, and make browser failures classifiable, without changing planner or judge behaviour.
**Source of truth for current state:** `ARCHITECTURE.md` and `QA_Bot_Testing.xlsx`. Module names below come from those two files, not from reading the code. Section 12 lists what to confirm first.

---

## 0. Summary

1. Introduce a `BrowserDriver` seam first. Wrap agent-browser behind it with no behaviour change.
2. Measure where per-step time goes before rewriting anything.
3. Build `PlaywrightDriver` and migrate in this order: **execute (P4) → replay (P5) → crawl (P1)**. Execution holds the latency. Crawl is last because `planner_input.json` is the SSOT contract and carries the most risk.
4. Run both backends in shadow mode on the same plan and diff verdicts before cutover.
5. Change one variable at a time. **Do not add parallelism, new test levels or new planner logic during the swap.**

---

## 1. Why: baseline from your sheet

Screenshots barely change the numbers (Saucedemo "none" was slower than "full"). That points to fixed per-action overhead, not evidence capture.

| Target | Steps | Wall time (range across modes) | Approx. s/step |
|---|---|---|---|
| Saucedemo | 39 | 149 – 194 s | 3.8 – 5.0 |
| Books | 58 | 284 – 332 s | 4.9 – 5.7 |
| Demowebshop | 55 | 330 – 472 s | 6.0 – 8.6 |
| Herokuapp | 9 | 324 – 631 s | 36 – 70 |
| Blinkit | 4 | ~112 s | ~28 |

- The first three rows look like per-step subprocess and snapshot overhead.
- Herokuapp and Blinkit look like timeouts waiting for elements that never resolve. Both need hard budgets as well as a faster driver.
- This is inferred from totals. Milestone M1 adds per-action timing to confirm it.

---

## 2. Scope

**In scope**
- Browser layer for Phases 1, 4 and 5
- Locator strategy (replace positional `@eN` resolution at execution time)
- Failure classification at the driver boundary
- Bot-challenge **detection** (preflight)
- Cache-key and schema changes needed to make the swap safe

**Out of scope (separate plans)**
- Multi-level test orchestration and DAG scheduling
- Planner and judge changes
- Parallel workers (add only after parity is proven)
- Any stealth or challenge-evasion technique

---

## 3. Current-state inventory

| Area | Today | Replacement |
|---|---|---|
| Availability probe | `health.record_probe()` checks agent-browser | Launch probe: chromium binary exists, launches, opens `about:blank` within 5 s |
| Open page / viewport | `open(url, 1536×900)` | `browser.new_context(viewport=...)` + `page.goto()` |
| Metadata | `METADATA_SCRIPT` eval | `page.evaluate()`, reusing the JS verbatim |
| Fold loop | `scrollTo`, 600 ms wait, screenshot, `GEOMETRY_SCRIPT` | Same scripts via `page.evaluate()`. Fixed 600 ms wait becomes an adaptive settle (4.5) |
| Snapshot | `agent-browser snapshot -i -u -c` | `locator.aria_snapshot()` + in-page evaluate for interactive elements and hrefs |
| Sessions | Shared warm session + sterile purge, per-case isolated, readiness gate | One browser per run, **one context per case**. A fresh context makes the purge unnecessary |
| Step execution | Selector reconciliation, click/fill/assert/navigate | `driver.act()` with resolved locators |
| Telemetry | console_errors, network_errors, dom_mutations | Event listeners (4.6) + one `evaluate` census |
| Video | `record_case_video` | `record_video_dir` on the case context |
| Replay | `IsolatedReplayer` opens a fresh session | Fresh context from the same browser |
| Repro specs | Already generated as Playwright `.spec.ts` | Reuse the same locator descriptors, so repro and execution agree |
| Tunnel profile | workers=1, shared session, patient timeouts, pre-warm | Same profile expressed as `SessionProfile` values (4.2) |

**Find every call site before starting:**
```bash
grep -rniE "agent[-_ ]?browser|subprocess\.(run|Popen)|asyncio\.create_subprocess" core/ api/ *.py
```

---

## 4. Target design

### 4.1 Driver seam (port and adapter)

All pipeline code depends on the interface. Neither backend leaks into runners.

```python
class BrowserDriver(Protocol):
    async def start(self, profile: SessionProfile) -> None: ...
    async def new_case_session(self, storage_state: dict | None = None) -> CaseSession: ...
    async def stop(self) -> None: ...

class CaseSession(Protocol):
    async def goto(self, url: str) -> NavResult            # status, final_url, headers
    async def resolve(self, comp: Component) -> Resolved   # unique, visible-or-not, strategy_used
    async def act(self, step: Step, target: Resolved | None) -> ActionResult
    async def snapshot(self) -> PageSnapshot
    async def screenshot(self, path: str) -> None
    async def drain_telemetry(self) -> Telemetry           # console, pageerrors, network, dialogs
    async def save_state(self) -> dict                     # storage_state
    async def close(self) -> None
```

- `AgentBrowserDriver` stays until the exit criteria in Section 8 hold across several consecutive runs.
- Backend is selected by `BROWSER_BACKEND=agent_browser|playwright`. Default stays `agent_browser` until cutover.

### 4.2 Browser and context lifecycle

- **One browser per run, one `BrowserContext` per test case.** Cheap isolation, no relaunch, no cookie purge.
- Execution runs in its own **worker process** that owns the Playwright instance.
  - Sync-API objects are bound to the creating thread and async objects to the event loop. Sharing them with FastAPI or Gradio is a common source of hangs.
  - A process boundary also gives a hard kill for runaway runs.
  - On Windows, the async API needs the Proactor event loop, and reload-style dev servers can trip on it. The separate process avoids this too.
- `SessionProfile` holds all timing and environment knobs:

| Field | Default | Tunnel profile (trycloudflare/ngrok) |
|---|---|---|
| `action_timeout_ms` | 5 000 | 10 000 |
| `nav_timeout_ms` | 30 000 | 60 000 |
| `case_budget_s` | 60 | 120 |
| `run_budget_s` | configurable | configurable |
| `ignore_https_errors` | false | true |
| `prewarm` | off | HEAD + GET before first case |

- Crash handling: listen to `page.on("crash")` and `browser.on("disconnected")`. Mark the case `harness_error(infra)`, relaunch the browser, retry that case **once**.
- Always use `try/finally` or context managers. A run-level watchdog kills the worker if `run_budget_s` is exceeded.

### 4.3 Locator strategy (the main robustness change)

Today `@eN` is positional and dies when the DOM shifts (the likely cause of many Demowebshop failures). Keep `@eN` for LLM-facing prompts and the grounding gate (`^@e\d+$` unchanged), but **resolve through descriptors, never through index**.

Crawl records an ordered locator chain per component (additive to `planner-input-v1`):

```json
{
  "ref": "@e26",
  "role": "link",
  "name": "A Light in the Attic",
  "fingerprint": "sha1(role|name|nearest-landmark|dom-path)",
  "locator_quality": "strong",
  "locators": [
    {"kind": "role",   "role": "link", "name": "A Light in the Attic", "exact": true, "nth": 0, "of": 1},
    {"kind": "testid", "value": "product-link-1"},
    {"kind": "css",    "value": "article.product_pod:nth-of-type(1) h3 > a"}
  ]
}
```

Resolution rules:
1. Try candidates in order. Accept only if the match count is **exactly 1** (or the recorded `nth` is within `of`). Never let Playwright's strict-mode exception reach the action.
2. Record `locator_strategy_used`. If only a fallback matched, emit `locator_degraded` and keep going.
3. Duplicates (e.g. 20 "Add to basket" on Books, 6 "Add to cart" on Demowebshop) are disambiguated by `nth` plus nearest-landmark or card-text context.
4. Unnamed elements (many `(unnamed)` links on Books, Demowebshop) get `locator_quality: weak` (CSS only). The planner should deprioritise them.
5. 0 matches: re-snapshot once, retry resolution, then `harness_error(locator_not_found)`. This is never an app defect.

### 4.4 Action mapping

Confirm the full action set from the runner. The assertions listed below appear in your plans.

| Plan action | Playwright |
|---|---|
| `navigate` | `page.goto(url, wait_until="domcontentloaded")`, record status and headers |
| `click` | `locator.click()` (auto-waits for actionability) |
| `fill` | `locator.fill()` |
| `type` | `locator.press_sequentially()` |
| `select` | `locator.select_option()` |
| `check` / `uncheck` | `locator.check()` / `.uncheck()` |
| `hover` | `locator.hover()` |
| `press` | `page.keyboard.press()` |
| `scroll` | `locator.scroll_into_view_if_needed()` or `mouse.wheel()` |
| `assert_visible` / `assert_hidden` | `expect(locator).to_be_visible()` / `.to_be_hidden()` with a short timeout |
| `assert_text` | `expect(locator).to_contain_text()` (page-level if `target_ref` is null) |
| `assert_url_contains` | `expect(page).to_have_url(re.compile(...))` |

### 4.5 Waiting and timeouts (no fixed sleeps)

- Rely on Playwright's actionability auto-waits for actions.
- After navigation or a mutating action, **settle** = no DOM mutations for 250 ms **and** in-flight request count is 0, capped at 3 s. Mutations come from a `MutationObserver` injected via `add_init_script`. In-flight count comes from request listeners.
- Avoid `networkidle`. It is discouraged and unreliable on ad-heavy pages.
- Every step has `action_timeout_ms`. Every case has `case_budget_s`. Every run has `run_budget_s`. Exceeding any of them yields a classified result, never a hang.
- Pages that are slow by design (e.g. "Slow Resources") get an explicit `expect_slow: true` hint on the case, not a global timeout increase.

### 4.6 Telemetry capture (replaces CLI capture)

Attach listeners when the context is created. Buffer them per step and flush into `qa_execution.json` exactly as today.

| Signal | Source |
|---|---|
| `console_errors` | `page.on("console")` filtered to `error` |
| Uncaught exceptions | `page.on("pageerror")` |
| `network_errors` | `page.on("requestfailed")` + `page.on("response")` with status ≥ 400 |
| Dialogs | `page.on("dialog")`. **Must always be handled** or the page hangs (JS Alerts page) |
| Popups / new tabs | `context.on("page")` |
| DOM mutations | Pre/post census via one `page.evaluate()`, same shape as today |

These double as passive checks that need no LLM and no per-case oracle.

### 4.7 Domain and guardrail enforcement

- `ActionPolicyGuardrail` still runs **before** `driver.act()`, and its behaviour is unchanged during this migration. Follow-up (separate change): the baseline shows Flipkart (23/23) and Amazon (25/25) cases fully safety-gated with 0 steps executed, so the gate should block only the irreversible step, not the whole case, with policy set per target (`sandbox` vs `read-only`).
- Add network-level enforcement: `context.route("**/*", guard)` aborts **navigation requests** to off-origin URLs (`blockedbyclient`) and records `guardrail_block`.
- Playwright docs note that enabling routing disables the HTTP cache. Measure this in M2. If it costs too much, fall back to a `framenavigated` listener plus a post-step origin check.

### 4.8 Failure classification (at the driver boundary)

Every non-pass result gets exactly one class. Only `app_failure` becomes a Phase 4 `candidate_finding`.

| Signal | Class | To Phase 5? |
|---|---|---|
| 0 locator matches after one re-snapshot | `harness_error: locator_not_found` | No |
| >1 matches after disambiguation | `harness_error: ambiguous_locator` (fix at crawl) | No |
| Page crash, browser disconnected, context closed | `harness_error: infra` (relaunch, retry case once) | No |
| Uniquely resolved but not actionable in time, when the case expects it to be | `app_failure` | Yes |
| `expect(...)` mismatch | `app_failure` | Yes |
| `net::ERR_*`, DNS, TLS failure | `env_error` | No |
| 403 / 429 / challenge markers | `blocked_bot` | No |
| Off-origin navigation aborted | `guardrail_block` | No |
| Step, case or run budget exceeded | `timeout` (record which budget) | No |

**Retries:** only for `harness_error: infra` and navigation-level `env_error`, maximum one retry. Never retry an assertion failure. Phase 5 handles confirmation.

### 4.9 Bot-challenge preflight (detection only)

`preflight(url)` runs before crawl and before planning:
- HTTP status 403 / 429, or a challenge response header
- Title matches patterns such as "Just a moment" or "Attention Required"
- DOM markers: challenge forms, captcha iframes, `data-sitekey`
- A very low interactive-component count combined with any marker above

On a match, stop with `blocked_bot`. **Do not plan against the challenge page**, and make Phase 2 verdicts `INVALID` actually halt the run (a gate that does not stop anything is not a gate).

Out of scope: stealth plugins, fingerprint spoofing, captcha solvers. For apps you own or are authorised to test, use an allowlisted harness (token header or WAF rule) or a staging environment. For auth walls, use **human-in-the-loop auth capture**: log in once in headed mode, save `storage_state`, reuse it per case. Treat state files as secrets (file mode 600, git-ignored, excluded from report bundles, never logged).

### 4.10 Crawl replacement (Phase 1)

- Keep `METADATA_SCRIPT` and `GEOMETRY_SCRIPT` unchanged, run via `page.evaluate()`. This minimises behavioural drift.
- Replace `snapshot -i -u -c` with `aria_snapshot()` plus an evaluate pass for interactive elements and hrefs. Verify the exact semantics of `-i -u -c` in M4 by diffing component sets.
- Pin the Playwright version and confirm `aria_snapshot` is available (it appeared in recent releases).
- Add the locator chain and `fingerprint` per component during the same pass. `fingerprint` also enables cross-run matching.
- Keep the fold loop and `annotate_image()` output as-is for now, but swap the fixed 600 ms wait for the adaptive settle.
- Keep `planner-input-v1` valid. New fields are additive. If the planner prompt is token-sensitive, strip `locators` from the LLM-facing view and keep them in the artifact only.

### 4.11 Replay (Phase 5) and repro specs

- `IsolatedReplayer` opens a fresh context from the same browser and replays only the failing step chain, restoring any required `storage_state`.
- Replay deterministically **twice** before the LLM judge sees anything. A failure that does not reproduce is dismissed without a judge call.
- Phase 6 repro `.spec.ts` should emit the same locator chain (first strong candidate), so a developer's repro matches what the harness did.

### 4.12 Cache keys and schemas

- **Add `backend` and `driver_version` to `cache_meta.input_hash` for Phases 1 and 4.** Otherwise old agent-browser results will be served as cache hits after cutover.
- Add `backend`, `driver_version`, `status_class`, `locator_strategy_used` to `qa_execution.json`. These are additive, with no breaking schema bump.
- New events in `events.jsonl`: `driver.started`, `driver.crashed`, `preflight.blocked`, `locator.degraded`.

---

## 5. Page-feature coverage

Use The Internet's pages as a ready checklist. Each must have a fixture test in M2.

| Feature | Playwright handling |
|---|---|
| JS alerts / confirms / prompts | `page.on("dialog")` always registered |
| Multiple windows / new tabs | `context.on("page")`, track active page |
| iframes and nested frames | `frame_locator()`; resolver records `frame_path` |
| Shadow DOM | Role and CSS locators pierce open shadow roots |
| File upload / download | `set_input_files()`, `expect_download()` |
| Drag and drop | `locator.drag_to()` |
| Hover menus | `hover()` then assert |
| Basic / digest auth | `http_credentials` on the context |
| Geolocation | Context `permissions` + `geolocation` |
| Infinite scroll | Scroll loop bounded by max iterations |
| Dynamic loading / disappearing elements | Expected-state assertions, no sleeps |
| Slow resources | `expect_slow` hint on the case |
| Status codes | Capture from `response.status` |

---

## 6. Migration phases

Effort: S = small, M = medium, L = large.

### M0: Baseline and safety net (S)
- Freeze golden outputs from the current system on **Saucedemo, Books, Example, The Internet** (deterministic targets). Save `planner_input.json`, `qa_plan.json`, `qa_execution.json`.
- Record baseline component counts (Saucedemo 3, Example 1, Herokuapp 45, Books 100) and the timing table from Section 1.
- Add JSON-schema contract tests for `planner-input-v1`, `qa-execution-v1`, `qa-verification-v1`.
- **Exit:** baselines committed. Contract tests green on the current code.

### M1: Seam and instrumentation (M)
- Define `BrowserDriver` / `CaseSession`. Implement `AgentBrowserDriver` as a thin wrapper over the existing calls.
- Route Phases 1, 4 and 5 through the interface. **No behaviour change.**
- Time each action: spawn, resolve, act, settle, screenshot, telemetry, census.
- **Exit:** golden diffs are empty. A per-action latency breakdown exists and shows where the ~5 s per step goes.

### M2: Playwright executor, shadow mode (L)
- Implement `PlaywrightDriver`: lifecycle, locator resolver, action map, settle, telemetry, classification, dialogs, route guard, video.
- Build the local fixture app (Section 7) and make the Section 5 table pass.
- Shadow mode: run the **same `qa_plan.json`** on both backends and diff per-step verdicts and timings.
- Phase 4 resolves `@eN` through the existing `load_component_registry()` first (role + name + nth). This lets Phase 4 move before the crawl produces locator chains.
- **Exit:** acceptance criteria 1–5 (Section 8) met on shadow runs. Every verdict diff is triaged as a bug in old, a bug in new, or flake.

### M3: Replay on Playwright (S)
- Move `IsolatedReplayer` to fresh contexts. Add the double deterministic replay before the judge.
- **Exit:** replay of known-good and known-bad fixture cases is correct. Judge call count does not increase.

### M4: Crawl on Playwright (L)
- Port `collect()` and `snapshot`. Add locator chains, fingerprints and `locator_quality`. Add `preflight()`.
- Make a failing Phase 2 gate halt the run.
- **Exit:** component sets match baseline on static targets (or each difference is explained). Planner output quality on the same targets is not worse. Blinkit stops at preflight with `blocked_bot`.

### M5: Cutover and cleanup (S)
- Flip the default to `playwright`. Keep the agent-browser adapter for one release behind the flag.
- Update `health.record_probe()`, README, Docker/CI (`playwright install --with-deps chromium`), and the cache-hash change.
- After the exit window, delete the adapter and the dead code.
- **Exit:** N consecutive clean runs on Playwright only.

### M6 (after cutover): Parallel contexts (M)
- Worker pool with one browser per worker and a semaphore sized to CPU. Only now, so any regression is attributable to one change.

---

## 7. How to verify the migration itself

1. **Driver contract tests.** The same test suite runs against `AgentBrowserDriver` and `PlaywrightDriver`, plus a `FakeDriver` for unit-testing the runner and classifier without a browser.
2. **Local fixture app (CI).** A small local server with deterministic pages: duplicate-name buttons, unnamed links, iframe, shadow DOM, alert dialogs, a popup, a slow resource, a 429 page, a fake challenge page, a broken image, a console error. CI never depends on public sites.
3. **Shadow-mode diffs.** Same plan, both backends, per-step verdict and timing diff.
4. **Nightly real-site benchmark.** The Internet and Saucedemo for known-bug recall. Example and Books as clean controls for false positives. Amazon, Flipkart and Blinkit only as `blocked_bot` and preflight checks.
5. **Chaos checks.** Kill the browser mid-case, drop the network, abort the worker. Verify classification, retry-once and no orphan processes.

---

## 8. Acceptance criteria

Initial targets. Calibrate them against the M1 measurements.

1. Median per-step latency (excluding explicit waits) ≤ 1 s on Saucedemo and Books. Baseline: 3.8 – 5.7 s.
2. Saucedemo 10-case suite ≤ 45 s on a single worker. Baseline: 149 – 194 s.
3. Verdict parity ≥ 95% against baseline on deterministic targets. Every difference is triaged.
4. Stale-ref failures on Demowebshop attributable to locator staleness: 0.
5. `harness_error` rate ≤ 2% of steps on the fixture suite.
6. No case exceeds `case_budget_s`. No run exceeds `run_budget_s`.
7. 0 orphan chromium processes after 100 consecutive runs and after a forced worker kill.
8. Every artifact records `backend` and `driver_version`. Old-backend cache entries are never served.
9. Blinkit-style challenge pages stop at preflight with `blocked_bot`, and no plan is generated.

---

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Verdict drift from different auto-wait semantics | Shadow mode and triaged diffs before cutover |
| `aria_snapshot` does not match old `snapshot -i -u -c` component sets | Diff on static targets in M4. Keep geometry scripts unchanged |
| Duplicate and unnamed elements still ambiguous | Locator chain with `nth` and landmark context. `weak` quality flag. `ambiguous_locator` is a harness error, never a defect |
| Route guard disables HTTP cache and slows pages | Measure in M2. Fall back to `framenavigated` check |
| Event-loop or thread conflicts with FastAPI/Gradio | Executor runs in its own worker process |
| Browser leaks or zombies | Context managers, run watchdog, process-level kill, chaos tests |
| Stale cache served from the old backend | Backend and driver version in `input_hash` |
| Public-site flakiness causes false regressions | CI on local fixtures. Public sites only in nightly benchmarks |
| Auth state leaks | Secret handling for `storage_state` (4.9) |
| Scope creep during the swap | Section 2 non-goals. Parallelism deferred to M6 |

---

## 10. Rollback

- `BROWSER_BACKEND=agent_browser` restores the old path with no code change until M5 cleanup.
- Artifacts carry `backend`, so mixed-backend runs are distinguishable.
- Do not delete the adapter until the M5 exit window is complete.

---

## 11. Do not

- Add stealth, spoofing or captcha-solving.
- Use fixed `sleep` calls, or `networkidle` as the default wait.
- Share Playwright objects across threads or event loops.
- Retry assertion failures.
- Let a harness error become a candidate defect.
- Ship parallelism in the same release as the backend swap.
- Break `planner-input-v1`, `qa-execution-v1` or `^@e\d+$`. All changes are additive.

---

## 12. Confirm in the code before M1

- [ ] Every agent-browser call site (use the grep in Section 3)
- [ ] The full action set in the runner beyond click/fill/assert/navigate
- [ ] Exact meaning of `snapshot -i -u -c` and what the tunnel profile depends on
- [ ] Whether the runner is sync or async, and the target OS (Windows event-loop caveat)
- [ ] `sandbox_mode` and `reuse_session` semantics, so the new context model preserves them
- [ ] Whether the planner prompt has a token budget that rules out adding `locators` to the LLM-facing view
- [ ] Why the Amazon Phase 6 row shows `Target: flipkart.com` (possible state leak between runs). Check this before building shadow-mode diffs, or it will pollute them.

---

## Appendix A: Illustrative sketches

These are sketches, not drop-in code.

**Case context with guard**
```python
async def new_case_context(browser, profile, allowed_domains, storage_state=None, video_dir=None):
    ctx = await browser.new_context(
        viewport={"width": 1536, "height": 900},
        storage_state=storage_state,
        record_video_dir=video_dir,
        ignore_https_errors=profile.ignore_https_errors,
    )
    ctx.set_default_timeout(profile.action_timeout_ms)
    ctx.set_default_navigation_timeout(profile.nav_timeout_ms)

    async def guard(route):
        req = route.request
        if req.is_navigation_request() and not is_domain_allowed(req.url, allowed_domains):
            await route.abort("blockedbyclient")
        else:
            await route.continue_()

    await ctx.route("**/*", guard)
    return ctx
```

**Locator resolution**
```python
async def resolve(page, comp):
    for kind, make in candidate_builders(comp):          # role -> testid -> css
        loc = make(page)
        n = await loc.count()
        if n == 1:
            return Resolved(loc, strategy=kind, degraded=(kind != "role"))
    # re-snapshot once, retry; then:
    raise HarnessError("locator_not_found", ref=comp.ref)
```

**Classification wrapper**
```python
try:
    target = await session.resolve(comp)          # HarnessError on 0 / >1 matches
    await session.act(step, target)
except HarnessError as e:
    return Result("harness_error", e.code)
except PlaywrightTimeout:
    return Result("app_failure" if step.expects_actionable else "timeout", "actionability")
except AssertionError as e:
    return Result("app_failure", "oracle_mismatch", detail=str(e))
except PlaywrightError as e:
    return classify_infra_or_env(e)               # crash/disconnect -> infra, net::ERR -> env
```
