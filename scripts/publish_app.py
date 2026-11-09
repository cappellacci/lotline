"""Publish the app to GitHub Pages from this machine's results: `python scripts/publish_app.py [--go]`.

No data or results are committed. Instead:

1. Every `reports/results/<st>/bundle.json` is validated and staged as `<st>.bundle.json`, with the data
   dashboard's summary as `data-summary.json` when it exists.
2. The page is built once from exactly those files, so a bundle that won't render is never uploaded.
3. With `--go`: the files become the assets of a GitHub release tagged at the current commit (which must be
   pushed, with a clean working tree), and the Pages workflow (`.github/workflows/pages.yml`) is started. It
   checks out that tag, downloads the assets, rebuilds the page with `scripts/build_app.py --from-release`
   and deploys it to https://cappellacci.github.io/lotline/.

Without `--go` it stops after step 2 and prints what it would publish. Needs the `gh` CLI, signed in.

    uv run python scripts/publish_app.py                          # check only
    uv run python scripts/publish_app.py --go --tag app-2026-11-20
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import tempfile
from pathlib import Path

from lotline.app.build import DATA_SUMMARY, RESULTS_DIR, build_app, release_inputs, stage_release

WORKFLOW = "pages.yml"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout.strip()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--results", type=Path, default=RESULTS_DIR, help="folder of <st>/bundle.json")
    p.add_argument("--data-summary", type=Path, default=DATA_SUMMARY, help="data dashboard summary.json")
    today = dt.date.today().isoformat()
    p.add_argument("--tag", default=f"app-{today}", help="release tag (default app-<date>)")
    p.add_argument("--go", action="store_true", help="create the release and start the Pages deploy")
    a = p.parse_args(argv)

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "release"
        files = stage_release(stage, results_dir=a.results, data_summary=a.data_summary)
        bundles, summary = release_inputs(stage)
        build_app(bundles, out_dir=Path(tmp) / "site", data_summary=summary)  # raises if it won't render
        print(f"Built the page from {len(bundles)} state bundle(s):")
        for f in files:
            print(f"  {f.name}  ({f.stat().st_size / 1e6:.1f} MB)")
        if not a.go:
            print("Check only. Add --go to upload these as release", a.tag, "and deploy the page.")
            return 0

        if _git("status", "--porcelain"):
            p.error("the working tree has uncommitted changes; commit them so the release names the code")
        sha = _git("rev-parse", "HEAD")
        if not _git("branch", "-r", "--contains", sha):
            p.error(f"commit {sha[:7]} is not pushed; push it so the workflow can check it out")
        notes = (
            f"Results bundles behind the published app, published from commit {sha}. "
            "Made by scripts/publish_app.py and deployed by .github/workflows/pages.yml."
        )
        subprocess.run(
            ["gh", "release", "create", a.tag, *map(str, files)]
            + ["--target", sha, "--title", a.tag, "--notes", notes],
            check=True,
        )
        subprocess.run(["gh", "workflow", "run", WORKFLOW, "-f", f"tag={a.tag}"], check=True)
    print(f"Release {a.tag} created and the Pages deploy started: `gh run list --workflow {WORKFLOW}`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
