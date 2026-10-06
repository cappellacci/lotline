#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Compliance check for the Housing Data and Technology Innovation Challenge.

Checks a submission repo against the Official Rules (sections 7-8) and the
Participant Handbook. Check IDs match HANDOFF.md.

    python compliance_check.py [--run] [--github] [--deps] [--all] [--root PATH]

Uses only the standard library on Python 3.11+ (3.10 needs `tomli`). Exits 1 if any check FAILs.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # Python 3.10: pip install tomli
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        sys.exit("compliance_check.py needs Python 3.11+, or `pip install tomli` on 3.10")
from dataclasses import dataclass
from pathlib import Path

BENCHMARK = {"adu", "missing_middle", "tod", "parking", "fees"}
METRICS = {"permits", "starts", "completions", "stock_growth"}
APPROVED_LICENSES = {
    "Apache-2.0": [r"Apache License", r"Version 2\.0"],
    "MIT": [r"Permission is hereby granted, free of charge"],
    "BSD-3-Clause": [r"Redistribution and use in source and binary forms",
                     r"Neither the name of"],
    "BSD-2-Clause": [r"Redistribution and use in source and binary forms"],
}
BANNED_LICENSE_PATTERNS = [
    r"GNU (Affero |Lesser )?General Public License", r"Mozilla Public License",
    r"European Union Public Licen[cs]e", r"CC0", r"This is free and unencumbered software",
]
BAD_DEP_LICENSE = re.compile(
    r"\b(A?GPL|LGPL|MPL|EUPL|SSPL|BUSL|Business Source|Commons Clause|"
    r"Non-?Commercial|CC-BY-NC|Elastic License|UNKNOWN)\b", re.I)
SECRET_PATTERNS = {
    "AWS access key": r"AKIA[0-9A-Z]{16}",
    "GitHub token": r"gh[pousr]_[A-Za-z0-9]{36,}",
    "Private key": r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    "Slack token": r"xox[baprs]-[A-Za-z0-9-]{10,}",
    "Google API key": r"AIza[0-9A-Za-z_\-]{35}",
    "Generic secret assignment": r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][A-Za-z0-9_\-/+=]{16,}['\"]",
}
DOC_SECTIONS = {
    "model_overview": {  # Rules 7a(4)
        "purpose and scope": r"purpose|scope",
        "core assumptions and rationale": r"assumption",
        "data sources and cleaning steps": r"data sources?|cleaning",
        "methodological approach": r"method",
        "limitations and edge cases": r"limitation|edge case",
        "sensitivity notes": r"sensitivity",
        "intended users and use cases": r"intended users?|use cases?",
    },
    "scenario_comparison": {  # Rules 7a(6)
        "comparison to baseline": r"baseline",
        "drivers of differences": r"driver",
        "critical assumptions": r"assumption",
        "model limitations": r"limitation",
    },
    "data_provenance": {  # Handbook: Data and Resources
        "source": r"source", "version": r"version", "access date": r"access(ed)? date|accessed",
        "license": r"licen[cs]e", "cleaning": r"clean", "known limitations": r"limitation",
    },
    "disclosures": {  # Rules 7c
        "AI code-generation tools": r"\bAI\b|code[- ]generation|copilot|claude|chatgpt|cursor",
        "pretrained models/weights/embeddings": r"pretrained|model weights|embedding|no pretrained",
        "external APIs/hosted services": r"\bAPIs?\b|hosted service",
        "third-party code/deps/datasets + licenses": r"third[- ]party|dependenc",
    },
}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache",
             ".pytest_cache", "dist", "build", ".tox", "data/raw", "data/cache"}


@dataclass
class Result:
    cid: str
    status: str  # PASS | FAIL | WARN | MANUAL | SKIP
    msg: str


class Checker:
    def __init__(self, root: Path):
        self.root = root
        self.results: list[Result] = []
        cfg_path = root / "challenge.toml"
        self.cfg = tomllib.loads(cfg_path.read_text()) if cfg_path.exists() else {}
        if not self.cfg:
            self.add("CFG", "FAIL", "challenge.toml missing or empty; copy the template and fill it in")

    # helpers -----------------------------------------------------------
    def add(self, cid, status, msg):
        self.results.append(Result(cid, status, msg))

    def get(self, *keys, default=None):
        node = self.cfg
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node

    def rel(self, p: Path | None) -> str:
        if p is None:
            return "(not configured)"
        try:
            return p.relative_to(self.root).as_posix()
        except ValueError:
            return str(p)

    def doc(self, key) -> Path | None:
        rel = self.get("docs", key)
        return (self.root / rel) if rel else None

    def tracked_files(self) -> list[Path]:
        try:
            out = subprocess.run(["git", "ls-files", "-z"], cwd=self.root, capture_output=True,
                                 check=True, text=True).stdout
            files = [self.root / p for p in out.split("\0") if p]
            if files:
                return [f for f in files if f.is_file()]
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        found = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            rel = Path(dirpath).relative_to(self.root).as_posix()
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and f"{rel}/{d}".lstrip("./") not in SKIP_DIRS]
            found += [Path(dirpath) / f for f in filenames]
        return found

    # scope ---------------------------------------------------------------
    def check_scope(self):
        sc = set(self.get("project", "scenarios", default=[]))
        bench = sc & BENCHMARK
        unknown = sc - BENCHMARK - {"baseline"}
        if "baseline" not in sc:
            self.add("S2", "FAIL", "scenarios must include 'baseline'")
        else:
            self.add("S2", "PASS", "baseline included")
        if unknown:
            self.add("S1", "FAIL", f"unknown scenario ids {sorted(unknown)}; put state-specific ones in extra_scenarios")
        elif len(bench) >= 3:
            self.add("S1", "PASS", f"{len(bench)} benchmark scenarios: {', '.join(sorted(bench))}")
        else:
            self.add("S1", "FAIL", f"need >=3 of {sorted(BENCHMARK)}, have {sorted(bench)}")
        h = self.get("project", "horizon_years")
        self.add("S3", "PASS" if h == 5 else "FAIL", f"horizon_years = {h} (Handbook: 5-year projection)")
        m = self.get("project", "outcome_metric", default="")
        j = (self.get("project", "outcome_metric_justification", default="") or "").strip()
        if m not in METRICS:
            self.add("S4", "FAIL", f"outcome_metric '{m}' not one of {sorted(METRICS)}")
        elif len(j) < 40:
            self.add("S4", "FAIL", "outcome_metric_justification missing or too short")
        else:
            self.add("S4", "PASS", f"metric '{m}' with justification")
        st = (self.get("project", "state", default="") or "").strip()
        self.add("S5", "PASS" if len(st) == 2 else "WARN",
                 f"state = '{st}'" + ("" if len(st) == 2 else " (not set yet)"))
        for cid, msg in [("S6", "results shown as ranges/sensitivity, not single numbers"),
                         ("S7", "extra scenarios labeled separately from benchmark ones"),
                         ("S8", "all work created on/after 2026-09-14; pre-existing code disclosed")]:
            self.add(cid, "MANUAL", msg)

    # deliverables ------------------------------------------------------
    def check_docs(self):
        tool = self.get("links", "tool_url", default="")
        self.add("D1", "PASS" if tool else "FAIL", f"tool_url {'set' if tool else 'missing'}; confirm it works (not a mockup)")
        slides = self.doc("slides_pdf")
        if slides and slides.exists():
            n = self.pdf_pages(slides)
            if n is None:
                self.add("D2", "WARN", "slides PDF present; couldn't count pages, confirm <=30")
            else:
                self.add("D2", "PASS" if n <= 30 else "FAIL", f"slides PDF has {n} pages (max 30)")
        else:
            self.add("D2", "FAIL", f"slides PDF not found at {self.rel(slides)}")
        vid = self.get("links", "video_url", default="")
        self.add("D3", "WARN" if vid else "FAIL",
                 "video_url set; confirm <=5 min and viewable without an account" if vid else "video_url missing")
        readme = self.doc("readme")
        self.add("D5", "PASS" if readme and readme.exists() else "FAIL", "README present" if readme and readme.exists() else "README missing")
        ids = {"model_overview": "D4", "scenario_comparison": "D6", "data_provenance": "D7", "disclosures": "D8"}
        for key, cid in ids.items():
            p = self.doc(key)
            if not p or not p.exists():
                self.add(cid, "FAIL", f"{key} not found at {self.rel(p)}")
                continue
            text = p.read_text(errors="ignore")
            missing = [name for name, rx in DOC_SECTIONS[key].items() if not re.search(rx, text, re.I)]
            words = len(text.split())
            note = ""
            if key == "model_overview" and words > 15000:
                note = f"; ~{words} words, check <=25 pages"
            if key == "scenario_comparison" and words > 2600:
                note = f"; ~{words} words, likely over 4 pages"
            self.add(cid, "FAIL" if missing else ("WARN" if note else "PASS"),
                     (f"missing: {', '.join(missing)}" if missing else f"{p.name}: all required topics present") + note)
        self.add("D9", "MANUAL", "Team Leader submits via team link before 11:59 p.m. ET 2026-12-16")

    @staticmethod
    def pdf_pages(path: Path) -> int | None:
        data = path.read_bytes()
        n = len(re.findall(rb"/Type\s*/Page(?!s)\b", data))
        return n or None

    # technical gates -----------------------------------------------------
    def check_license(self):
        lic = next((p for p in self.root.iterdir() if p.is_file() and re.match(r"(?i)licen[cs]e(\.|$)", p.name)), None)
        if not lic:
            self.add("T2", "FAIL", "no LICENSE file at repo root")
            return
        text = lic.read_text(errors="ignore")
        if any(re.search(rx, text, re.I) for rx in BANNED_LICENSE_PATTERNS):
            self.add("T2", "FAIL", f"{lic.name} looks like a banned license (copyleft or public domain)")
            return
        match = None
        for name in ["Apache-2.0", "BSD-3-Clause", "MIT", "BSD-2-Clause"]:
            if all(re.search(rx, text, re.I) for rx in APPROVED_LICENSES[name]):
                match = name
                break
        if not match:
            self.add("T2", "FAIL", f"{lic.name} is not recognizably Apache-2.0/MIT/BSD-3/BSD-2 (full text required)")
            return
        readme = self.doc("readme")
        named = readme and readme.exists() and re.search(re.escape(match).replace(r"\-", "[- ]?") + "|" + match.split("-")[0], readme.read_text(errors="ignore"), re.I)
        self.add("T2", "PASS" if named else "WARN", f"{match} license" + ("" if named else "; name it in the README too"))

    def check_commands(self, run: bool):
        setup, test = self.get("commands", "setup", default=""), self.get("commands", "test", default="")
        readme = self.doc("readme")
        rtext = readme.read_text(errors="ignore") if readme and readme.exists() else ""
        for cid, label, cmd in [("T3", "setup", setup), ("T4", "test", test)]:
            if not cmd:
                self.add(cid, "FAIL", f"commands.{label} not set")
                continue
            doc_note = "" if cmd in rtext else f"; add `{cmd}` to the README"
            if not run:
                self.add(cid, "WARN" if doc_note else "PASS", f"{label} command: `{cmd}`{doc_note} (use --run to execute)")
                continue
            r = subprocess.run(cmd, shell=True, cwd=self.root, capture_output=True, text=True)
            tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
            self.add(cid, "PASS" if r.returncode == 0 and not doc_note else ("WARN" if r.returncode == 0 else "FAIL"),
                     f"`{cmd}` exit {r.returncode}{doc_note}" + (f" | {' / '.join(tail)}" if r.returncode else ""))
        tests = [f for f in self.tracked_files() if re.search(r"(^|/)(tests?/|test_[^/]*\.py$|[^/]*_test\.py$)", f.relative_to(self.root).as_posix())]
        if not tests:
            self.add("T4", "FAIL", "no test files found")

    def check_secrets(self):
        hits = []
        for f in self.tracked_files():
            rel = f.relative_to(self.root).as_posix()
            if re.search(r"(^|/)\.env(\.|$)", rel) and not rel.endswith(".example"):
                hits.append(f"{rel}: .env file committed")
            if f.stat().st_size > 2_000_000 or f.suffix in {".pdf", ".png", ".jpg", ".parquet", ".zip", ".gpkg"}:
                continue
            try:
                text = f.read_text(errors="ignore")
            except OSError:
                continue
            for name, rx in SECRET_PATTERNS.items():
                if f.name == "compliance_check.py":
                    continue
                if re.search(rx, text):
                    hits.append(f"{rel}: {name}")
        self.add("T5", "FAIL" if hits else "PASS", "; ".join(hits[:5]) if hits else "no secret patterns in tracked files")

    def check_data_and_pins(self):
        cap = self.get("data", "max_committed_file_mb", default=25) * 1_000_000
        big = [f"{f.relative_to(self.root)} ({f.stat().st_size/1e6:.0f} MB)" for f in self.tracked_files() if f.stat().st_size > cap]
        scripts = [s for s in self.get("data", "acquisition_scripts", default=[]) if (self.root / s).exists()]
        if big:
            self.add("T10", "FAIL", "large files committed; download them instead: " + ", ".join(big[:5]))
        elif not scripts:
            self.add("T10", "WARN", "no data acquisition script found (data.acquisition_scripts)")
        else:
            self.add("T10", "PASS", f"no large files; acquisition via {', '.join(scripts)}")
        locks = [n for n in ["uv.lock", "poetry.lock", "Pipfile.lock", "pdm.lock", "requirements.lock", "package-lock.json"] if (self.root / n).exists()]
        reqs = sorted(self.root.glob("requirements*.txt"))
        unpinned = []
        for r in reqs:
            for line in r.read_text().splitlines():
                line = line.split("#")[0].strip()
                if line and not line.startswith(("-", "--")) and "==" not in line and "@" not in line:
                    unpinned.append(f"{r.name}:{line}")
        if unpinned:
            self.add("T9", "FAIL", "unpinned: " + ", ".join(unpinned[:8]))
        elif locks or reqs:
            self.add("T9", "PASS", "pinned via " + ", ".join(locks + [r.name for r in reqs]))
        else:
            self.add("T9", "FAIL", "no lock file or pinned requirements found")
        sbom = self.doc("sbom")
        self.add("T7", "PASS" if sbom and sbom.exists() else "WARN",
                 "SBOM committed" if sbom and sbom.exists() else "SBOM not committed yet (export from Insights > Dependency graph before submitting)")
        wf = list((self.root / ".github" / "workflows").glob("*.y*ml")) if (self.root / ".github" / "workflows").exists() else []
        codeql = any("codeql" in w.read_text(errors="ignore").lower() for w in wf)
        dependabot = (self.root / ".github" / "dependabot.yml").exists() or (self.root / ".github" / "dependabot.yaml").exists()
        self.add("T6", "PASS" if (codeql or dependabot) else "WARN",
                 f"CodeQL workflow {'found' if codeql else 'not in repo (OK if default setup is on, use --github)'}; "
                 f"dependabot.yml {'found' if dependabot else 'missing (alerts may still be on, use --github)'}")

    def check_deps(self):
        if not shutil.which("pip-licenses"):
            self.add("T8", "SKIP", "pip-licenses not installed (pip install pip-licenses)")
            return
        r = subprocess.run(["pip-licenses", "--format=json", "--with-system"], capture_output=True, text=True, cwd=self.root)
        try:
            pkgs = json.loads(r.stdout)
        except json.JSONDecodeError:
            self.add("T8", "WARN", "pip-licenses output unreadable")
            return
        flagged = [f"{p['Name']} ({p['License']})" for p in pkgs if BAD_DEP_LICENSE.search(p.get("License", "UNKNOWN") or "UNKNOWN")]
        disc = self.doc("disclosures")
        dtext = disc.read_text(errors="ignore").lower() if disc and disc.exists() else ""
        undisclosed = [f for f in flagged if f.split(" (")[0].lower() not in dtext]
        if undisclosed:
            self.add("T8", "FAIL", "non-permissive or unknown and not disclosed: " + ", ".join(undisclosed[:10]))
        elif flagged:
            self.add("T8", "WARN", "flagged but disclosed: " + ", ".join(flagged[:10]))
        else:
            self.add("T8", "PASS", f"{len(pkgs)} packages, all permissive")

    def check_github(self):
        url = self.get("links", "repo_url", default="")
        m = re.search(r"github\.com[/:]([^/]+)/([^/.]+)", url or "")
        if not m or not shutil.which("gh"):
            self.add("T1", "SKIP", "set links.repo_url and install/auth the gh CLI")
            return
        repo = f"{m.group(1)}/{m.group(2)}"

        def api(path):
            r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
            return r.returncode, (json.loads(r.stdout) if r.stdout.strip().startswith(("{", "[")) else None)

        code, info = api(f"repos/{repo}")
        if code or not info:
            self.add("T1", "FAIL", f"cannot read {repo}")
            return
        self.add("T1", "PASS" if info.get("visibility") == "public" else "FAIL", f"{repo} is {info.get('visibility')}")
        saa = info.get("security_and_analysis") or {}
        ss = (saa.get("secret_scanning") or {}).get("status")
        code, alerts = api(f"repos/{repo}/secret-scanning/alerts?state=open&per_page=100")
        n_open = len(alerts) if isinstance(alerts, list) else None
        ok = ss == "enabled" and n_open == 0
        self.add("T5", "PASS" if ok else "FAIL", f"GitHub secret scanning {ss}; open alerts: {n_open}")
        dep_code, _ = api(f"repos/{repo}/vulnerability-alerts")  # 204/empty = enabled
        _, dalerts = api(f"repos/{repo}/dependabot/alerts?state=open&per_page=100")
        hi = [a for a in (dalerts or []) if (a.get("security_advisory") or {}).get("severity") in {"critical", "high"}]
        _, cs = api(f"repos/{repo}/code-scanning/default-setup")
        _, calerts = api(f"repos/{repo}/code-scanning/alerts?state=open&per_page=100")
        chi = [a for a in (calerts or []) if (a.get("rule") or {}).get("security_severity_level") in {"critical", "high"}]
        codeql_on = (cs or {}).get("state") == "configured" or isinstance(calerts, list)
        msg = (f"Dependabot alerts {'enabled' if dep_code == 0 else 'NOT enabled'} ({len(hi)} open critical/high); "
               f"CodeQL {'on' if codeql_on else 'NOT on'} ({len(chi)} open critical/high)")
        status = "PASS" if dep_code == 0 and codeql_on and not hi and not chi else "FAIL"
        if status == "FAIL" and dep_code == 0 and codeql_on:
            msg += ", fix or document a justification for each"
        self.add("T6", status, msg)

    def manual(self):
        for cid, msg in [
            ("E1", "U.S. legal residency + U.S. bank account for every member through 2027-01-30"),
            ("E2", "every member 18+ as of 2026-09-14"),
            ("E3", "no excluded persons or conflicts"),
            ("E5", "registered before 9:00 a.m. ET 2026-10-07"),
            ("E6", "team of 1-5, Team Leader named, roster locked at registration close"),
            ("E7", "only team members built the Submission"),
            ("T11", "restricted/paid data has a free end-user access path"),
            ("T12", "memory-safe language; tooling gaps documented"),
        ]:
            self.add(cid, "MANUAL", msg)

    def report(self) -> int:
        order = {"FAIL": 0, "WARN": 1, "PASS": 2, "SKIP": 3, "MANUAL": 4}
        tint = {"FAIL": "\033[31m", "WARN": "\033[33m", "PASS": "\033[32m", "SKIP": "\033[90m", "MANUAL": "\033[36m"}
        color = sys.stdout.isatty()
        for r in sorted(self.results, key=lambda r: (order[r.status], r.cid)):
            tag = f"{tint[r.status]}{r.status:<6}\033[0m" if color else f"{r.status:<6}"
            print(f"{tag} {r.cid:<4} {r.msg}")
        counts = {s: sum(r.status == s for r in self.results) for s in order}
        print("\n" + "  ".join(f"{k}: {v}" for k, v in counts.items()))
        return 1 if counts["FAIL"] else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="repo root (default: .)")
    ap.add_argument("--run", action="store_true", help="execute setup and test commands")
    ap.add_argument("--github", action="store_true", help="check GitHub repo settings via gh CLI")
    ap.add_argument("--deps", action="store_true", help="scan dependency licenses via pip-licenses")
    ap.add_argument("--all", action="store_true", help="all of the above")
    a = ap.parse_args()
    c = Checker(Path(a.root).resolve())
    if c.cfg:
        c.check_scope()
        c.check_docs()
        c.check_license()
        c.check_commands(a.run or a.all)
        c.check_secrets()
        c.check_data_and_pins()
        if a.deps or a.all:
            c.check_deps()
        if a.github or a.all:
            c.check_github()
    c.manual()
    sys.exit(c.report())


if __name__ == "__main__":
    main()
