"""Gradio Studio — phased, one tab per pipeline phase (mirrors the root studio).

Thin shell: every control calls a `bot` service and renders its result. Zero
pipeline logic here. Launch: `python -m bot.interfaces.studio` or `uv run poe studio`.

Design decisions (v0.2):
- No slug inputs: Phase 1 computes the slug from the URL and keeps it in a gr.State
  shared by all later tabs (session flow). The REST API still accepts slug/run_id
  directly for easy programmatic integration.
- Example websites + page preview on Phase 1 for manual validation of the crawl.
- Phase 3 planning is LLM-only (langchain-openai, OpenAI-compatible). There is no
  mock fallback; missing/failed configuration surfaces as a clear error.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bot.interfaces.studio_cards import _TC_CSS, render_summary_bar, render_test_cases_html
from bot.settings import get_settings

PHASE_TABS = (
    "Phase 1 — Crawl", "Phase 2 — Ground", "Phase 3 — Plan",
    "Phase 4 — Execute", "Phase 5 — Verify", "Phase 6 — Report",
)
STRATEGIES = ["comprehensive", "journey", "negative_edge", "positive_flow",
              "security_injection", "strict_adversarial"]
# Public, safe demo targets for quick manual validation (crawl with playwright backend).
# Each entry: url -> short label shown in the Phase 1 dropdown.
DEMO_URLS = {
    "https://the-internet.herokuapp.com/login": "The Internet — login form (herokuapp)",
    "https://quotes.toscrape.com/": "Quotes to Scrape — forms + pagination",
    "https://demoqa.com/login": "DemoQA — login / QA playground",
    "https://example.com": "Example.com — minimal static page",
    "https://httpbin.org/html": "HTTPBin — small HTML sample",
}

# Sentinel for the Phase 3 model dropdown: selecting it (or leaving everything blank)
# loads the model from .env (QA_BOT_PLANNER_MODEL).
DEFAULT_MODEL_CHOICE = "(default — from .env)"

# Phase 3 model catalog: dropdown of OpenAI-compatible ids from settings.MODEL_CATALOG
# (comma-separated, overridable via QA_BOT_MODEL_CATALOG in .env — Ollama models can be
# listed there too). The first entry is the Default option, which loads the model from
# .env. Anything else goes through the "Custom model id" box.
def _model_choices() -> list[str]:
    catalog = [m.strip() for m in get_settings().MODEL_CATALOG.split(",") if m.strip()] \
        or ["gpt-4o-mini"]
    return [DEFAULT_MODEL_CHOICE] + catalog


def _model_catalog_rows() -> list[list[str]]:
    """Rows for the Model Catalog sub-tab table: default first, then the .env catalog."""
    settings = get_settings()
    rows = [[str(0), settings.PLANNER_MODEL,
             ".env default (QA_BOT_PLANNER_MODEL)"]]
    for i, m in enumerate([x.strip() for x in settings.MODEL_CATALOG.split(",") if x.strip()], 1):
        source = ".env default (also in catalog)" if m == settings.PLANNER_MODEL else ".env catalog (QA_BOT_MODEL_CATALOG)"
        rows.append([str(i), m, source])
    return rows


def _preview_for_slug(slug: str):
    """Annotated screenshot if present, else the raw page shot, else None."""
    shots = _page_dir(slug) / "phase_1_crawl" / "screenshots"
    for name in ("page_annotated.png", "page.png"):
        p = shots / name
        if p.exists():
            return str(p)
    return None


def _root() -> Path:
    return get_settings().resolved_artifacts_dir()


def _page_dir(slug: str) -> Path:
    return _root() / slug / "pages" / slug


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _component_rows(planner: dict) -> list[list[str]]:
    return [[c.get("ref", ""), c.get("role", ""), c.get("name") or "(unnamed)", str(c.get("box", ""))]
            for c in planner.get("components", [])]


def _case_rows(plan: dict) -> list[list[str]]:
    return [[tc.get("id", ""), tc.get("severity", ""), tc.get("category", ""),
             tc.get("title", ""), tc.get("target_ref") or "", str(len(tc.get("steps", [])))]
            for tc in plan.get("test_cases", [])]


def _ref_choices(slug: str):
    import gradio as gr
    planner = _load_json(_page_dir(slug) / "shared" / "planner_input.json")
    refs = [c.get("ref") for c in planner.get("components", []) if c.get("ref")]
    return gr.update(choices=refs or ["none"], value=(refs[0] if refs else "none"))


def _resolve_slug(identifier: str, state_slug: str) -> str:
    """Accept a slug OR an 8-hex run_id (API parity); blank falls back to the session slug."""
    identifier = (identifier or "").strip()
    if not identifier:
        return state_slug
    root = _root()
    if (root / identifier / "site_manifest.json").exists():
        return identifier
    if root.exists():
        for d in sorted(root.iterdir()):
            mani = d / "site_manifest.json"
            if d.is_dir() and mani.exists():
                try:
                    if json.loads(mani.read_text(encoding="utf-8")).get("run_id") == identifier:
                        return d.name
                except Exception:
                    continue
    return identifier  # let downstream raise a clear "not crawled yet" error


def build_studio():
    import gradio as gr

    settings = get_settings()

    # ---- handlers ----
    def do_crawl(url, backend, scope, slug_state):
        from bot.crawl import run_crawl
        if not url.strip():
            return "Enter a URL.", None, [], "{}", slug_state, gr.update()
        try:
            manifest = run_crawl(url, _root(), backend=backend, scope=scope)
        except Exception as exc:
            return f"**Error:** {exc}", None, [], "{}", slug_state, gr.update()
        slug = manifest["pages"][0]["slug"]
        planner = _load_json(_page_dir(slug) / "shared" / "planner_input.json")
        preview = _preview_for_slug(slug)
        status = (f"**Crawled:** `{manifest['base_url']}`  \n"
                  f"**Backend:** `{manifest['backend']}` · **Slug:** `{slug}` — kept internally, "
                  f"later tabs use this session automatically (no input needed)  \n"
                  f"**Components:** {len(planner.get('components', []))} · "
                  f"**Screenshot:** {'captured' if preview else 'not captured'}")
        # Re-point the example dropdown at whatever we just crawled, so the preview
        # always matches the current session page.
        label = DEMO_URLS.get(url.strip()) or f"{url.strip()} (current session)"
        return (status, preview, _component_rows(planner), json.dumps(manifest, indent=2),
                slug, gr.update(choices=[label], value=label))

    def do_ground(run_id, slug_state):
        from bot.ground import run_ground
        slug = _resolve_slug(run_id, slug_state)
        if not slug:
            return ("Run **Phase 1 — Crawl** first — this tab uses the crawl from your session.",
                    [], _ref_choices(""))
        try:
            result, _ = run_ground(_page_dir(slug))
        except Exception as exc:
            return f"**Error:** {exc}", [], _ref_choices("")
        md = (f"### Session crawl: `{slug}`  \nGrounding: {result.ok_count}/{result.total} ok · "
              f"by_type `{result.by_type}`")
        return md, result.rows, _ref_choices(slug)

    def inspect(run_id, ref, slug_state):
        slug = _resolve_slug(run_id, slug_state)
        planner = _load_json(_page_dir(slug) / "shared" / "planner_input.json")
        comp = next((c for c in planner.get("components", []) if c.get("ref") == ref), None)
        if not comp:
            return f"No component `{ref}`."
        return (f"### `{comp.get('ref')}` — {comp.get('name') or '(unnamed)'}\n\n"
                f"**Role:** `{comp.get('role')}` · **Box:** `{comp.get('box')}` · "
                f"**Folds:** `{comp.get('visible_in_folds')}`\n\n"
                f"**Selector:** `{comp.get('fingerprint', '')}`")

    def do_plan(run_id, strategy, model_sel, model_custom, api_key, base_url, slug_state):
        from bot.plan import run_plan
        slug = _resolve_slug(run_id, slug_state)
        if not slug:
            return ("Run **Phase 1 — Crawl** first — this tab uses the crawl from your session.",
                    "", "", [], "{}")
        # Model selection order: custom id box -> catalog dropdown -> .env default.
        # The "(default — from .env)" sentinel (or a blank dropdown) means: no override,
        # run_plan falls back to QA_BOT_PLANNER_MODEL from .env.
        sel = (model_sel or "").strip()
        if sel == DEFAULT_MODEL_CHOICE:
            sel = ""
        chosen = (model_custom.strip() if model_custom and model_custom.strip()
                  else sel) or None
        try:
            plan, _ = run_plan(_page_dir(slug), strategy=strategy,
                               model=chosen,
                               api_key=api_key.strip() or None,
                               base_url=base_url.strip() or None)
        except Exception as exc:
            hint = ("\n\n> Planning is **LLM-only** (langchain-openai, OpenAI-compatible — "
                    "no mock fallback). Pick a model above (or add your OpenAI-compatible "
                    "model id in \"Custom model id\" with key/base URL), or set "
                    "`QA_BOT_LLM_API_KEY` / `QA_BOT_LLM_BASE_URL` / `QA_BOT_PLANNER_MODEL` "
                    "in `.env` (see `.env.example`), then retry.")
            return f"**Error:** {exc}{hint}", "", "", [], "{}"
        summary = _TC_CSS + render_summary_bar(plan)
        cards = _TC_CSS + render_test_cases_html(plan)
        used_model = plan.get("_provider_model") or chosen or settings.PLANNER_MODEL
        return (f"**Plan:** {len(plan['test_cases'])} case(s) · strategy `{strategy}` · "
                f"model `{used_model}` · session crawl `{slug}`", summary, cards, _case_rows(plan),
                json.dumps(plan, indent=2))

    def do_execute(run_id, slug_state):
        from bot.execute import run_execution
        slug = _resolve_slug(run_id, slug_state)
        if not slug:
            return "Run **Phase 1 — Crawl** first.", [], []
        plan = _load_json(_page_dir(slug) / "phase_3_plan" / "qa_plan.json")
        if not plan:
            return "**Error:** no plan yet — run Plan first.", [], []
        ex = run_execution(plan, backend="fake")
        s = ex["summary"]
        case_rows = [[r.get("id"), r.get("status"), str(len(r.get("steps", []))), r.get("title", "")]
                     for r in ex.get("test_case_results", [])]
        find_rows = [[f.get("id"), f.get("severity"), f.get("failure_class"), f.get("title"),
                      f.get("error_message", "")[:80]] for f in ex.get("candidate_findings", [])]
        md = (f"### Execute (`{slug}`): {s['passed_cases']}p / {s['failed_cases']}f · "
              f"{s['candidate_findings_count']} candidate finding(s)")
        return md, case_rows, find_rows

    def do_verify(run_id, slug_state):
        from bot.execute import run_execution
        from bot.verify import run_verification
        slug = _resolve_slug(run_id, slug_state)
        if not slug:
            return "Run **Phase 1 — Crawl** first.", [], []
        plan = _load_json(_page_dir(slug) / "phase_3_plan" / "qa_plan.json")
        if not plan:
            return "**Error:** no plan yet.", [], []
        ex = run_execution(plan, backend="fake")
        v = run_verification(ex, plan, page_dir=_page_dir(slug))
        s = v["summary"]
        ver = [[f.get("id"), f.get("severity"), f.get("confidence"), f.get("title")]
               for f in v.get("verified_findings", [])]
        dis = [[f.get("id"), f.get("severity"), f.get("reasoning", "")[:80]]
               for f in v.get("dismissed_findings", [])]
        md = (f"### Verify (`{slug}`): {s['verified_count']} verified · {s['dismissed_count']} dismissed · "
              f"rate {s['verification_rate']}")
        return md, ver, dis

    def do_report(run_id, slug_state):
        from bot.execute import run_execution
        from bot.report import run_report
        from bot.verify import run_verification
        slug = _resolve_slug(run_id, slug_state)
        if not slug:
            return "Run **Phase 1 — Crawl** first.", [], "{}"
        plan = _load_json(_page_dir(slug) / "phase_3_plan" / "qa_plan.json")
        if not plan:
            return "**Error:** no plan yet.", [], "{}"
        ex = run_execution(plan, backend="fake")
        v = run_verification(ex, plan, page_dir=_page_dir(slug))
        rep = run_report(v, plan, page_dir=_page_dir(slug))
        specs = rep.pop("_specs", {})
        s = rep["summary"]
        defect_rows = [[d.get("id"), d.get("severity"), d.get("title"), d.get("repro_spec")]
                       for d in rep.get("defects", [])]
        md = (f"### Report (`{slug}`): {s['total_verified']} verified · {s['duplicates_merged']} merged · "
              f"{s['repro_count']} repros · matrix `{s['severity_matrix']}`")
        return md, defect_rows, json.dumps({**rep, "repro_specs": specs}, indent=2)

    # ---- UI: one tab per phase ----
    with gr.Blocks(title="QA Bot v0.2 — Phased Studio") as demo:
        gr.Markdown(
            "# QA Bot v0.2 — Phased Studio\n"
            "Standalone autonomous QA pipeline. One tab per phase.\n\n"
            "**Session flow:** crawl a URL in Phase 1 and every later tab runs on that crawl "
            "automatically — there is no slug to copy around. (The REST API still accepts "
            "slug/run_id directly for integrations.)")
        slug_state = gr.State("")

        with gr.Tab(PHASE_TABS[0]) as tab_crawl:
            example_pick = gr.Dropdown(list(DEMO_URLS.values()),
                                       value=list(DEMO_URLS.values())[0],
                                       label="Example websites",
                                       info="Safe public targets — pick one, press “Fill example”, "
                                            "then Crawl with the **playwright** backend to see a "
                                            "real annotated page preview below.")
            fill_example = gr.Button("Fill example ↓", size="sm")
            url = gr.Textbox(label="URL", placeholder="https://example.com/login")
            with gr.Row():
                backend = gr.Radio(["fake", "playwright"], value="fake", label="Backend")
                scope = gr.Dropdown(["all", "forms", "catalog", "navigation"], value="all", label="Scope")
            crawl_btn = gr.Button("Crawl", variant="primary")
            crawl_status = gr.Markdown()
            with gr.Row():
                with gr.Column(scale=3):
                    preview = gr.Image(type="filepath", height=560,
                                       label="Page preview — manual validation "
                                             "(annotated screenshot: @eN boxes on the real page)")
                with gr.Column(scale=2):
                    comp_table = gr.Dataframe(headers=["Ref", "Role", "Name", "Box"],
                                              label="Detected components", interactive=False)
            with gr.Accordion("Manifest (debug)", open=False):
                manifest_json = gr.Code(language="json")

        with gr.Tab(PHASE_TABS[1], interactive=False) as tab_ground:
            g_run = gr.Textbox(label="Identifier override (optional)",
                               placeholder="blank = session crawl · or paste a slug/run_id (API parity)")
            g_btn = gr.Button("Audit grounding", variant="primary")
            g_out = gr.Markdown()
            ground_table = gr.Dataframe(headers=["Ref", "Role", "Name", "Box", "Folds", "Status"],
                                        label="Grounding", interactive=False)
            with gr.Row():
                g_ref = gr.Dropdown(choices=["none"], label="Component")
                g_detail = gr.Markdown()

        with gr.Tab(PHASE_TABS[2], interactive=False) as tab_plan:
            with gr.Tabs():
                with gr.Tab("Plan"):
                    p_run = gr.Textbox(label="Identifier override (optional)",
                                       placeholder="blank = session crawl · or paste a slug/run_id (API parity)")
                    with gr.Row():
                        p_strategy = gr.Dropdown(STRATEGIES, value="comprehensive", label="Strategy")
                        p_model_sel = gr.Dropdown(_model_choices(),
                                                  value=DEFAULT_MODEL_CHOICE,
                                                  label="Model (catalog)",
                                                  info="Catalog from QA_BOT_MODEL_CATALOG (.env); Ollama "
                                                       "models included when configured there. "
                                                       "\"(default — from .env)\" or blank = QA_BOT_PLANNER_MODEL.")
                        p_model_custom = gr.Textbox(label="Custom model id (your OpenAI-compatible model)",
                                                    placeholder="e.g. llama-3.1-70b / gpt-4o-mini-azure — overrides the dropdown",
                                                    info="Leave blank to use the dropdown/.env. No mock fallback — "
                                                         "failures surface below as errors.")
                    with gr.Accordion("LLM credentials (optional override — else loaded from .env)",
                                      open=False):
                        with gr.Row():
                            p_api_key = gr.Textbox(label="API key", type="password",
                                                   placeholder="sk-… (leave blank to use QA_BOT_LLM_API_KEY)")
                            p_base_url = gr.Textbox(label="Base URL",
                                                    placeholder="https://api.openai.com/v1 or your gateway "
                                                                "(blank = QA_BOT_LLM_BASE_URL)")
                    p_btn = gr.Button("Generate plan", variant="primary")
                    p_out = gr.Markdown()
                    p_summary = gr.HTML()
                    p_cards = gr.HTML()
                    p_cases = gr.Dataframe(headers=["ID", "Severity", "Category", "Title", "Ref", "Steps"],
                                           label="Cases", interactive=False)
                    with gr.Accordion("Plan JSON (qa_plan.json)", open=False):
                        p_json = gr.Code(language="json")

                with gr.Tab("Model Catalog"):
                    gr.Markdown(
                        "### Model Catalog\n"
                        "Models listed here come from `QA_BOT_MODEL_CATALOG` in `.env` "
                        "(comma-separated; includes Ollama models when configured). "
                        "The **Default** option loads the model from `QA_BOT_PLANNER_MODEL` in `.env`.")
                    mc_table = gr.Dataframe(
                        headers=["#", "Model id", "Source"],
                        value=_model_catalog_rows(),
                        label="Available models",
                        interactive=False)
                    gr.Markdown(
                        f"> Current `.env` default: `{settings.PLANNER_MODEL}` "
                        f"(base URL: `{settings.LLM_BASE_URL or 'https://api.openai.com/v1'}`)")

        with gr.Tab(PHASE_TABS[3], interactive=False) as tab_exec:
            e_run = gr.Textbox(label="Identifier override (optional)",
                               placeholder="blank = session crawl · or paste a slug/run_id (API parity)")
            e_btn = gr.Button("Execute", variant="primary")
            e_out = gr.Markdown()
            e_cases = gr.Dataframe(headers=["ID", "Status", "Steps", "Title"], interactive=False)
            e_findings = gr.Dataframe(headers=["ID", "Severity", "Class", "Title", "Error"], interactive=False)

        with gr.Tab(PHASE_TABS[4], interactive=False) as tab_verify:
            v_run = gr.Textbox(label="Identifier override (optional)",
                               placeholder="blank = session crawl · or paste a slug/run_id (API parity)")
            v_btn = gr.Button("Verify", variant="primary")
            v_out = gr.Markdown()
            v_verified = gr.Dataframe(headers=["ID", "Severity", "Confidence", "Title"], interactive=False)
            v_dismissed = gr.Dataframe(headers=["ID", "Severity", "Reason"], interactive=False)

        with gr.Tab(PHASE_TABS[5], interactive=False) as tab_report:
            r_run = gr.Textbox(label="Identifier override (optional)",
                               placeholder="blank = session crawl · or paste a slug/run_id (API parity)")
            r_btn = gr.Button("Run report", variant="primary")
            r_out = gr.Markdown()
            r_defects = gr.Dataframe(headers=["ID", "Severity", "Title", "Repro"], interactive=False)
            with gr.Accordion("Report JSON + repro specs", open=False):
                r_json = gr.Code(language="json")

        # ---- wiring ----
        later_tabs = [tab_ground, tab_plan, tab_exec, tab_verify, tab_report]
        crawl_outputs = ([crawl_status, preview, comp_table, manifest_json]
                         + later_tabs + [slug_state])

        def do_crawl_wrapped(url, backend, scope, slug_state):
            status, shot_path, rows, manifest_json_text, slug, example_update = \
                do_crawl(url, backend, scope, slug_state)
            unlocked = [gr.update(interactive=True)] * len(later_tabs) if slug else \
                       [gr.update()] * len(later_tabs)
            return (status, shot_path, rows, manifest_json_text, *unlocked, slug, example_update)

        crawl_btn.click(do_crawl_wrapped, [url, backend, scope, slug_state],
                        crawl_outputs + [example_pick])
        # Label -> URL mapping for the "Fill example" button.
        _label_to_url = {label: u for u, label in DEMO_URLS.items()}
        fill_example.click(lambda ex: _label_to_url.get(ex, ex), [example_pick], [url])

        g_btn.click(do_ground, [g_run, slug_state], [g_out, ground_table, g_ref])
        g_ref.change(inspect, [g_run, g_ref, slug_state], [g_detail])
        p_btn.click(do_plan, [p_run, p_strategy, p_model_sel, p_model_custom,
                              p_api_key, p_base_url, slug_state],
                    [p_out, p_summary, p_cards, p_cases, p_json])
        e_btn.click(do_execute, [e_run, slug_state], [e_out, e_cases, e_findings])
        v_btn.click(do_verify, [v_run, slug_state], [v_out, v_verified, v_dismissed])
        r_btn.click(do_report, [r_run, slug_state], [r_out, r_defects, r_json])

    return demo


def main() -> None:
    demo = build_studio()
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)


if __name__ == "__main__":
    main()
