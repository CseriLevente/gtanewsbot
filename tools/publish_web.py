"""
Publish the web edition to every configured host.

Two hosts on purpose. Cloudflare Pages is the one the digest links to; GitHub
Pages is the standby, so that a Cloudflare OAuth token expiring -- which it
will, silently, on a machine nobody logs into -- leaves a current copy of the
page reachable instead of a dead link posted to a Discord channel every night.

The contract that makes that worth having:

  * every target is attempted, independently. A failure in one must not skip
    the other, which is exactly what chaining them in a shell with && would do;
  * the command succeeds if AT LEAST ONE target published. Redundancy is the
    whole point -- failing the run because the standby broke would be backwards;
  * a partial failure is still reported loudly, on stderr, naming the target.
    Silent degradation to one host is how you discover months later that the
    fallback was never working.

Configure with:
  GTA6_PUBLISH_TARGETS   comma-separated: github,cloudflare  (default: both)
  CF_PAGES_PROJECT       Cloudflare Pages project name (default: gta6-news)

Run:  python tools/publish_web.py
"""
from __future__ import annotations

import dataclasses
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / "web" / "index.html"

GITHUB_TIMEOUT_S = 180
CLOUDFLARE_TIMEOUT_S = 300

# The final line of stdout, so a caller reading only the tail can still tell
# what happened per host. src/runner.py parses this; keep the shape stable.
RESULT_PREFIX = "RESULT"

# Exit codes. Distinguishing partial from total is the point: the caller keeps
# running either way, but a partial failure must be reportable rather than
# indistinguishable from a clean run.
EXIT_ALL_OK = 0
EXIT_TOTAL_FAILURE = 1
EXIT_PARTIAL = 2


@dataclasses.dataclass
class Result:
    target: str
    ok: bool
    detail: str
    url: str = ""


def _publish_github() -> Result:
    """Delegate to the GitHub Pages helper rather than reimplementing it."""
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "deploy_pages.py")],
        cwd=ROOT, capture_output=True, text=True, timeout=GITHUB_TIMEOUT_S,
    )
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    url = next((l.strip() for l in out.splitlines()
                if l.strip().startswith("https://")), "")
    tail = out.splitlines()[-1] if out else "no output"
    return Result("github", r.returncode == 0, tail[:200], url)


def _publish_cloudflare() -> Result:
    project = os.environ.get("CF_PAGES_PROJECT", "gta6-news")
    # PINNED, not @latest. Two reasons, both learned the hard way:
    #   * @latest refetches from npm on every deploy, so an unattended nightly
    #     job runs whatever was published to npm that day -- a supply-chain
    #     exposure we would not accept anywhere else in this project;
    #   * wrangler's Node floor moves. 4.127 needs Node >= 22, and a distro
    #     whose apt node is 18 (Ubuntu 24.04 ships 18.19) cannot run it at all.
    #     Pinning makes that a decision rather than a surprise upgrade.
    version = os.environ.get("CF_WRANGLER_VERSION", "4.127.0")
    env = dict(os.environ)
    # Discourage any interactive prompt: under Task Scheduler there is no
    # console, so a prompt is an invisible hang rather than a visible question.
    env["CI"] = "1"
    env["WRANGLER_SEND_METRICS"] = "false"
    cmd = ["npx", "--yes", f"wrangler@{version}", "pages", "deploy", "web",
           "--project-name=" + project, "--commit-dirty=true"]
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           timeout=CLOUDFLARE_TIMEOUT_S, env=env,
                           shell=(os.name == "nt"))
    except subprocess.TimeoutExpired:
        return Result("cloudflare", False,
                      f"timed out after {CLOUDFLARE_TIMEOUT_S}s")
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    url = ""
    for line in out.splitlines():
        if "https://" in line and ".pages.dev" in line:
            url = line[line.index("https://"):].split()[0].rstrip(".,")
    tail = out.splitlines()[-1] if out else "no output"
    return Result("cloudflare", r.returncode == 0, tail[:200], url)


PUBLISHERS = {"github": _publish_github, "cloudflare": _publish_cloudflare}


def run_targets(names: list[str]) -> list[Result]:
    """
    Attempt each target, isolating failures.

    An exception from one publisher becomes that target's failed Result rather
    than aborting the loop -- otherwise the first broken host would take the
    working one down with it.
    """
    results = []
    for name in names:
        fn = PUBLISHERS.get(name)
        if fn is None:
            results.append(Result(name, False, "unknown target"))
            continue
        try:
            results.append(fn())
        except Exception as exc:  # noqa: BLE001 - report, never propagate
            results.append(Result(name, False, type(exc).__name__ + ": " + str(exc)[:150]))
    return results


def main() -> int:
    if not PAGE.exists():
        print("missing " + str(PAGE) + " -- run build-web first", file=sys.stderr)
        return 1

    raw = os.environ.get("GTA6_PUBLISH_TARGETS") or "github,cloudflare"
    names = [n.strip() for n in raw.split(",") if n.strip()]
    if not names:
        print("no publish targets configured", file=sys.stderr)
        return 1

    results = run_targets(names)
    for r in results:
        state = "ok  " if r.ok else "FAIL"
        print("  " + state + " " + r.target + ": " + r.detail)
        if r.url:
            print("       " + r.url)

    failed = [r for r in results if not r.ok]
    if failed:
        # stderr, so it lands in the log even when stdout is being parsed.
        print("published to " + str(len(results) - len(failed)) + " of "
              + str(len(results)) + " hosts; failed: "
              + ", ".join(r.target for r in failed), file=sys.stderr)

    # LAST line, deliberately. The caller in src/runner.py used to keep only
    # out.splitlines()[-1] as its status, which meant it recorded whatever
    # sentence happened to be printed last -- a constant string -- and logged
    # "web publish ok" every day regardless of what happened.
    print(RESULT_PREFIX + " " + " ".join(
        r.target + "=" + ("ok" if r.ok else "FAIL") for r in results))

    if not failed:
        return EXIT_ALL_OK
    return EXIT_TOTAL_FAILURE if len(failed) == len(results) else EXIT_PARTIAL


if __name__ == "__main__":
    raise SystemExit(main())
