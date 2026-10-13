"""CLI — thin shell over bot services. `qa-bot <command>`."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(help="QA Bot v0.2 — standalone autonomous QA pipeline.", no_args_is_help=True)
console = Console()


@app.callback()
def _main_callback() -> None:
    """Configure logging (QA_BOT_LOG_LEVEL) once for every `qa-bot` invocation."""
    import logging

    from bot.settings import get_settings

    settings = get_settings()
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        stream=sys.stderr,  # keep stdout clean for machine-readable output
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    if settings.DEBUG:
        logging.getLogger("bot").setLevel(logging.DEBUG)


def _infer_root(manifest_path: Path) -> Path:
    """Artifacts root from a manifest at <root>/<slug>/site_manifest.json."""
    return manifest_path.resolve().parent.parent


def _page_dir_from_manifest(manifest_path: Path, root: Path) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ref = manifest["pages"][0]["artifacts"]["shared_dir"]
    page_dir = (root / ref).resolve()
    if page_dir.name == "shared":
        page_dir = page_dir.parent
    return page_dir


@app.command()
def crawl(url: str, backend: str = typer.Option("fake", help="fake|playwright"),
          out: Path = typer.Option(Path("artifacts"), help="artifacts root")) -> None:
    """Crawl one URL -> planner_input.json + manifest."""
    from bot.crawl import run_crawl
    manifest = run_crawl(url, out, backend=backend)
    console.print(f"[green]crawled[/green] {manifest['base_url']} "
                  f"({manifest['pages'][0]['components_count']} components, backend={manifest['backend']})")
    console.print(f"manifest: {out / manifest['pages'][0]['slug'] / 'site_manifest.json'}")


@app.command()
def ground(manifest: Path) -> None:
    """Audit planner_input + fold bindings."""
    from bot.ground import run_ground
    page_dir = _page_dir_from_manifest(manifest, _infer_root(manifest))
    result, audit = run_ground(page_dir)
    status = "[green]PASS[/green]" if not result.issues else f"[red]{len(result.issues)} issues[/red]"
    console.print(f"ground: {result.ok_count}/{result.total} ok — {status} -> {audit}")


@app.command()
def plan(manifest: Path) -> None:
    """Generate a grounded QA plan (mock provider by default)."""
    from bot.plan import run_plan
    page_dir = _page_dir_from_manifest(manifest, _infer_root(manifest))
    plan, path = run_plan(page_dir)
    console.print(f"[green]plan[/green] {len(plan['test_cases'])} case(s) -> {path}")


@app.command()
def all(url: str, backend: str = typer.Option("fake"),
        out: Path = typer.Option(Path("artifacts"))) -> None:
    """Run crawl -> ground -> plan in one shot."""
    from bot.crawl import run_crawl
    from bot.ground import run_ground
    from bot.plan import run_plan
    manifest = run_crawl(url, out, backend=backend)
    slug = manifest["pages"][0]["slug"]
    manifest_path = out / slug / "site_manifest.json"
    page_dir = _page_dir_from_manifest(manifest_path, out.resolve())
    ground, _ = run_ground(page_dir, run_id=manifest["run_id"])
    plan, _ = run_plan(page_dir, run_id=manifest["run_id"])
    console.print(f"[green]done[/green] crawl={manifest['pages'][0]['components_count']} "
                  f"ground_ok={ground.ok_count}/{ground.total} plan_cases={len(plan['test_cases'])}")


# Public, safe-to-test demo targets — see README "Demo & test links".
DEMO_URLS = [
    "https://httpbin.org/html",
    "https://quotes.toscrape.com/",
    "https://the-internet.herokuapp.com/login",
    "https://example.com",
    "https://demoqa.com/login",
]


@app.command()
def demo(url: str = typer.Option("", help="single demo URL (default: run all built-in demo links)"),
         backend: str = typer.Option("fake", help="fake|playwright"),
         out: Path = typer.Option(Path("artifacts"))) -> None:
    """Run the full flow (crawl -> ground -> plan) over the built-in demo links."""
    urls = [url] if url else DEMO_URLS
    failures = 0
    for u in urls:
        console.print(f"\n[bold cyan]demo[/bold cyan] {u}")
        try:
            all(u, backend=backend, out=out)
        except Exception as exc:  # keep looping; report at the end
            failures += 1
            console.print(f"[red]FAILED[/red] {u}: {exc}")
    console.print(f"\n[green]{len(urls) - failures}/{len(urls)} demo runs ok[/green]")
    if failures:
        raise typer.Exit(code=1)


@app.command()
def execute(manifest: Path) -> None:
    """Execute the plan (fake backend)."""
    import json
    from bot.execute import run_execution
    root = _infer_root(manifest)
    page_dir = _page_dir_from_manifest(manifest, root)
    plan = json.loads((page_dir / "phase_3_plan" / "qa_plan.json").read_text())
    ex = run_execution(plan, backend="fake")
    s = ex["summary"]
    console.print(f"[green]execute[/green] {s['passed_cases']}p/{s['failed_cases']}f, "
                  f"{s['candidate_findings_count']} candidate finding(s)")


@app.command()
def report(manifest: Path) -> None:
    """Execute -> verify -> report on the plan (fake backend)."""
    import json
    from bot.execute import run_execution
    from bot.report import run_report
    from bot.verify import run_verification
    page_dir = _page_dir_from_manifest(manifest, _infer_root(manifest))
    plan = json.loads((page_dir / "phase_3_plan" / "qa_plan.json").read_text())
    ex = run_execution(plan, backend="fake")
    verification = run_verification(ex, plan, page_dir=page_dir)
    rep = run_report(verification, plan, page_dir=page_dir)
    s = rep["summary"]
    console.print(f"[green]report[/green] verified={s['total_verified']} "
                  f"merged={s['duplicates_merged']} repros={s['repro_count']} "
                  f"dismissed={s['dismissed_count']} matrix={s['severity_matrix']}")


if __name__ == "__main__":
    sys.exit(app())
