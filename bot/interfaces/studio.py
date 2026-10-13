"""Gradio Studio — phased, one tab per pipeline phase (mirrors the root studio).

Thin shell: every control calls a `bot` service and renders its result. Zero
pipeline logic here. Launch: `python -m bot.interfaces.studio` or `uv run poe studio`.
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


def build_studio():
    import gradio as gr

    # ---- handlers ----
    def do_crawl(url, backend, scope):
        from bot.crawl import run_crawl
        if not url.strip():
            return "Enter a URL.", "", [], "{}"
        try:
            manifest = run_crawl(url, _root(), backend=backend, scope=scope)
        except Exception as exc:
            return f"**Error:** {exc}", "", [], "{}"
        slug = manifest["pages"][0]["slug"]
        planner = _load_json(_page_dir(slug) / "shared" / "planner_input.json")
        status = (f"**Crawled:** `{manifest['base_url']}`  \n**Slug:** `{slug}`  \n"
                  f"**Components:** {len(planner.get('components', []))}")
        return status, slug, _component_rows(planner), json.dumps(manifest, indent=2)

    def do_ground(slug):
        from bot.ground import run_ground
        if not slug.strip():
            return "Enter a slug.", [], _ref_choices("")
        try:
            result, _ = run_ground(_page_dir(slug))
        except Exception as exc:
            return f"**Error:** {exc}", [], _ref_choices("")
        md = f"### Grounding: {result.ok_count}/{result.total} ok · by_type `{result.by_type}`"
        return md, result.rows, _ref_choices(slug)

    def inspect(slug, ref):
        planner = _load_json(_page_dir(slug) / "shared" / "planner_input.json")
        comp = next((c for c in planner.get("components", []) if c.get("ref") == ref), None)
        if not comp:
            return f"No component `{ref}`."
        return (f"### `{comp.get('ref')}` — {comp.get('name') or '(unnamed)'}\n\n"
                f"**Role:** `{comp.get('role')}` · **Box:** `{comp.get('box')}` · "
                f"**Folds:** `{comp.get('visible_in_folds')}`\n\n"
                f"**Selector:** `{comp.get('fingerprint', '')}`")

    def do_plan(slug, strategy):
        from bot.plan import run_plan
        if not slug.strip():
            return "Enter a slug.", "", "", [], "{}"
        try:
            plan, _ = run_plan(_page_dir(slug))
        except Exception as exc:
            return f"**Error:** {exc}", "", "", [], "{}"
        summary = _TC_CSS + render_summary_bar(plan)
        cards = _TC_CSS + render_test_cases_html(plan)
        return (f"**Plan:** {len(plan['test_cases'])} case(s) · strategy `{strategy}`",
                summary, cards, _case_rows(plan), json.dumps(plan, indent=2))

    def do_execute(slug):
        from bot.execute import run_execution
        if not slug.strip():
            return "Enter a slug.", [], []
        plan = _load_json(_page_dir(slug) / "phase_3_plan" / "qa_plan.json")
        if not plan:
            return "**Error:** no plan yet — run Plan first.", [], []
        ex = run_execution(plan, backend="fake")
        s = ex["summary"]
        case_rows = [[r.get("id"), r.get("status"), str(len(r.get("steps", []))), r.get("title", "")]
                     for r in ex.get("test_case_results", [])]
        find_rows = [[f.get("id"), f.get("severity"), f.get("failure_class"), f.get("title"),
                      f.get("error_message", "")[:80]] for f in ex.get("candidate_findings", [])]
        md = (f"### Execute: {s['passed_cases']}p / {s['failed_cases']}f · "
              f"{s['candidate_findings_count']} candidate finding(s)")
        return md, case_rows, find_rows

    def do_verify(slug):
        from bot.execute import run_execution
        from bot.verify import run_verification
        if not slug.strip():
            return "Enter a slug.", [], []
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
        md = (f"### Verify: {s['verified_count']} verified · {s['dismissed_count']} dismissed · "
              f"rate {s['verification_rate']}")
        return md, ver, dis

    def do_report(slug):
        from bot.execute import run_execution
        from bot.report import run_report
        from bot.verify import run_verification
        if not slug.strip():
            return "Enter a slug.", [], "{}"
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
        md = (f"### Report: {s['total_verified']} verified · {s['duplicates_merged']} merged · "
              f"{s['repro_count']} repros · matrix `{s['severity_matrix']}`")
        return md, defect_rows, json.dumps({**rep, "repro_specs": specs}, indent=2)

    # ---- UI: one tab per phase ----
    with gr.Blocks(title="QA Bot v0.2 — Phased Studio") as demo:
        gr.Markdown("# QA Bot v0.2 — Phased Studio\nStandalone autonomous QA pipeline. One tab per phase.")
        slug_state = gr.State("")

        with gr.Tab(PHASE_TABS[0]):
            url = gr.Textbox(label="URL", placeholder="https://example.com/login")
            with gr.Row():
                backend = gr.Radio(["fake", "playwright"], value="fake", label="Backend")
                scope = gr.Dropdown(["all", "forms", "catalog", "navigation"], value="all", label="Scope")
            crawl_btn = gr.Button("Crawl", variant="primary")
            crawl_status = gr.Markdown()
            slug_box = gr.Textbox(label="Slug (used by later tabs)")
            comp_table = gr.Dataframe(headers=["Ref", "Role", "Name", "Box"], label="Components", interactive=False)
            with gr.Accordion("Manifest (debug)", open=False):
                manifest_json = gr.Code(language="json")
            crawl_btn.click(do_crawl, [url, backend, scope],
                            [crawl_status, slug_box, comp_table, manifest_json])

        with gr.Tab(PHASE_TABS[1]):
            g_slug = gr.Textbox(label="Slug")
            g_btn = gr.Button("Audit grounding", variant="primary")
            g_out = gr.Markdown()
            ground_table = gr.Dataframe(headers=["Ref", "Role", "Name", "Box", "Folds", "Status"],
                                        label="Grounding", interactive=False)
            with gr.Row():
                g_ref = gr.Dropdown(choices=["none"], label="Component")
                g_detail = gr.Markdown()
            g_btn.click(do_ground, [g_slug], [g_out, ground_table, g_ref])
            g_ref.change(inspect, [g_slug, g_ref], [g_detail])

        with gr.Tab(PHASE_TABS[2]):
            p_slug = gr.Textbox(label="Slug")
            p_strategy = gr.Dropdown(STRATEGIES, value="comprehensive", label="Strategy")
            p_btn = gr.Button("Generate plan", variant="primary")
            p_out = gr.Markdown()
            p_summary = gr.HTML()
            p_cards = gr.HTML()
            p_cases = gr.Dataframe(headers=["ID", "Severity", "Category", "Title", "Ref", "Steps"],
                                   label="Cases", interactive=False)
            with gr.Accordion("Plan JSON (qa_plan.json)", open=False):
                p_json = gr.Code(language="json")
            p_btn.click(do_plan, [p_slug, p_strategy],
                        [p_out, p_summary, p_cards, p_cases, p_json])

        with gr.Tab(PHASE_TABS[3]):
            e_slug = gr.Textbox(label="Slug")
            e_btn = gr.Button("Execute", variant="primary")
            e_out = gr.Markdown()
            e_cases = gr.Dataframe(headers=["ID", "Status", "Steps", "Title"], interactive=False)
            e_findings = gr.Dataframe(headers=["ID", "Severity", "Class", "Title", "Error"], interactive=False)
            e_btn.click(do_execute, [e_slug], [e_out, e_cases, e_findings])

        with gr.Tab(PHASE_TABS[4]):
            v_slug = gr.Textbox(label="Slug")
            v_btn = gr.Button("Verify", variant="primary")
            v_out = gr.Markdown()
            v_verified = gr.Dataframe(headers=["ID", "Severity", "Confidence", "Title"], interactive=False)
            v_dismissed = gr.Dataframe(headers=["ID", "Severity", "Reason"], interactive=False)
            v_btn.click(do_verify, [v_slug], [v_out, v_verified, v_dismissed])

        with gr.Tab(PHASE_TABS[5]):
            r_slug = gr.Textbox(label="Slug")
            r_btn = gr.Button("Run report", variant="primary")
            r_out = gr.Markdown()
            r_defects = gr.Dataframe(headers=["ID", "Severity", "Title", "Repro"], interactive=False)
            with gr.Accordion("Report JSON + repro specs", open=False):
                r_json = gr.Code(language="json")
            r_btn.click(do_report, [r_slug], [r_out, r_defects, r_json])

    return demo


def main() -> None:
    demo = build_studio()
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)


if __name__ == "__main__":
    main()


