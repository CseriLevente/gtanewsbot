"""
Publish web/index.html to GitHub Pages.

Why git plumbing instead of a checkout
--------------------------------------
This builds the commit with hash-object/mktree/commit-tree and moves the ref
directly. Nothing is checked out, so the deploy never touches the working tree
or the current branch -- it is safe to run while you are mid-edit, and safe to
run unattended from Task Scheduler.

Each deploy is a fresh ORPHAN commit that force-replaces the branch, so the
branch holds exactly one commit. The page is regenerated daily; keeping its
history would add a ~170KB blob per day to a repo that is otherwise under a
megabyte, for a file whose old versions nobody will ever read.

Unattended safety
-----------------
GIT_TERMINAL_PROMPT=0 is set so that expired credentials fail immediately with
a clear error instead of blocking forever on a prompt that no one can see: under
Task Scheduler there is no console, so a hanging push would look exactly like a
slow one until the task's time limit killed it.

Run:  python tools/deploy_pages.py
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGE = ROOT / "web" / "index.html"
BRANCH = "gh-pages"
REMOTE = "origin"


def git(*args: str, check: bool = True) -> str:
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    r = subprocess.run(("git",) + args, cwd=ROOT, capture_output=True,
                       text=True, env=env)
    if check and r.returncode != 0:
        raise RuntimeError(
            "git " + " ".join(args) + " failed (exit " + str(r.returncode)
            + "): " + (r.stderr or r.stdout).strip()[:500])
    return r.stdout.strip()


def public_url() -> str | None:
    """Derive the Pages URL from the remote, so a fork gets its own URL."""
    try:
        url = git("remote", "get-url", REMOTE)
    except RuntimeError:
        return None
    m = re.search(r"github\.com[:/]([^/]+)/(.+?)(?:\.git)?$", url)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    return "https://" + owner.lower() + ".github.io/" + repo + "/"


def main() -> int:
    if not PAGE.exists():
        print("missing " + str(PAGE) + " -- run build-web first", file=sys.stderr)
        return 1

    blob = git("hash-object", "-w", str(PAGE))
    # .nojekyll: the page is a single self-contained file, so Jekyll has nothing
    # to do -- but it would still run, and its build is one more thing that can
    # fail between a successful push and a live page.
    empty = subprocess.run(
        ("git", "hash-object", "-w", "--stdin"), cwd=ROOT, input="",
        capture_output=True, text=True, check=True).stdout.strip()

    # Fed as BYTES, deliberately. With text=True, Python's newline translation
    # turns each "\n" into "\r\n" on Windows, git mktree takes the CR as part of
    # the filename, and the branch ends up holding "index.html\r" -- which
    # GitHub Pages cannot find, so the site 404s while the push, the branch and
    # the file contents all look perfectly correct.
    tree_spec = ("100644 blob " + blob + "\tindex.html\n"
                 "100644 blob " + empty + "\t.nojekyll\n").encode("utf-8")
    r = subprocess.run(("git", "mktree"), cwd=ROOT, input=tree_spec,
                       capture_output=True)
    if r.returncode != 0:
        print("git mktree failed: " + r.stderr.decode("utf-8", "replace").strip(),
              file=sys.stderr)
        return 1
    tree = r.stdout.decode("ascii").strip()

    # Assert the names came back exactly right. This is the failure above: every
    # other signal (exit code, push output, blob contents) stayed green while the
    # published site was a 404.
    listing = git("ls-tree", "--name-only", tree)
    names = listing.split("\n") if listing else []
    if sorted(names) != [".nojekyll", "index.html"]:
        print("refusing to publish: unexpected tree entries " + repr(names),
              file=sys.stderr)
        return 1

    # Skip a pointless push when the page has not changed. Saves a force-push
    # (and a Pages rebuild) on any day the bot runs but nothing new landed.
    try:
        current = git("rev-parse", BRANCH + "^{tree}", check=False)
    except RuntimeError:
        current = ""
    remote_same = False
    if current == tree:
        ls = git("ls-remote", REMOTE, "refs/heads/" + BRANCH, check=False)
        local_head = git("rev-parse", BRANCH, check=False)
        remote_same = bool(ls) and ls.split()[0] == local_head
    if remote_same:
        print("page unchanged and already published; nothing to do")
        url = public_url()
        if url:
            print(url)
        return 0

    size = PAGE.stat().st_size
    msg = "Deploy Vice City Wire (" + str(size) + " bytes)"
    commit = git("commit-tree", tree, "-m", msg)
    git("update-ref", "refs/heads/" + BRANCH, commit)
    git("push", "-f", REMOTE, BRANCH + ":" + BRANCH)

    url = public_url()
    print("published " + commit[:10] + " to " + BRANCH)
    if url:
        print(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
