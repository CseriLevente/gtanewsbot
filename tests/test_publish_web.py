"""
Tests for the multi-host publisher.

The aggregation rule is the whole reason this module exists, so it is what gets
tested: every target is attempted even when an earlier one fails, and the
command succeeds as long as one host got the page. Chaining the two deploys in
a shell would have failed both of those.

The publishers themselves are network- and credential-shaped and are stubbed.
"""
from __future__ import annotations

import pytest

publish_web = pytest.importorskip("tools.publish_web")
Result = publish_web.Result


@pytest.fixture()
def stub(monkeypatch):
    """Replace the real publishers with recorded, scripted outcomes."""
    calls = []

    def make(name, ok, detail="stub", exc=None):
        def fn():
            calls.append(name)
            if exc:
                raise exc
            return Result(name, ok, detail)
        return fn

    def install(spec):
        monkeypatch.setattr(publish_web, "PUBLISHERS",
                            {n: make(n, *a) for n, a in spec.items()})
        return calls
    return install


def test_a_failing_target_does_not_skip_the_next(stub):
    calls = stub({"github": (False,), "cloudflare": (True,)})
    results = publish_web.run_targets(["github", "cloudflare"])
    assert calls == ["github", "cloudflare"], "second target was skipped"
    assert [r.ok for r in results] == [False, True]


def test_an_exception_becomes_a_failed_result_not_a_crash(stub):
    stub({"github": (True, "stub", RuntimeError("boom")), "cloudflare": (True,)})
    results = publish_web.run_targets(["github", "cloudflare"])
    assert results[0].ok is False
    assert "RuntimeError" in results[0].detail
    assert results[1].ok is True, "a raising publisher took down the working one"


def test_unknown_target_is_reported_not_ignored(stub):
    stub({"github": (True,)})
    results = publish_web.run_targets(["github", "nope"])
    assert results[1].target == "nope"
    assert results[1].ok is False
    assert "unknown" in results[1].detail


@pytest.mark.parametrize(("outcomes", "expected_exit"), [
    ([True, True], 0),
    # Partial gets its OWN code rather than 0. Redundancy still means the run
    # stands -- the caller in src/runner.py treats 2 as published -- but a
    # standby that quietly stopped working must not be indistinguishable from a
    # clean run, which is exactly how it went unnoticed before.
    ([True, False], 2),
    ([False, True], 2),
    ([False, False], 1),   # nothing published anywhere
])
def test_exit_code_distinguishes_all_ok_from_partial_from_total_failure(
        monkeypatch, tmp_path, outcomes, expected_exit):
    page = tmp_path / "index.html"
    page.write_text("<!doctype html><title>x</title>", encoding="utf-8")
    monkeypatch.setattr(publish_web, "PAGE", page)
    monkeypatch.setenv("GTA6_PUBLISH_TARGETS", "github,cloudflare")
    names = ["github", "cloudflare"]
    monkeypatch.setattr(publish_web, "PUBLISHERS", {
        n: (lambda n=n, ok=ok: Result(n, ok, "stub"))
        for n, ok in zip(names, outcomes)
    })
    assert publish_web.main() == expected_exit


def test_missing_page_fails_before_touching_any_host(monkeypatch, tmp_path):
    monkeypatch.setattr(publish_web, "PAGE", tmp_path / "does-not-exist.html")
    called = []
    monkeypatch.setattr(publish_web, "PUBLISHERS",
                        {"github": lambda: called.append(1) or Result("github", True, "")})
    assert publish_web.main() == 1
    assert not called, "attempted a deploy with no page built"


# ---------------------------------------------------------------------------
# The machine-readable RESULT line
#
# Its absence is what made a months-long publish failure read as healthy: the
# caller kept out.splitlines()[-1], and cmd_build_web prints two fixed reminder
# lines after the deploy, so the recorded "status" was a constant sentence.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(("outcomes", "expected"), [
    ([True, True], "RESULT github=ok cloudflare=ok"),
    ([True, False], "RESULT github=ok cloudflare=FAIL"),
    ([False, False], "RESULT github=FAIL cloudflare=FAIL"),
])
def test_the_last_line_reports_every_host(monkeypatch, tmp_path, capsys,
                                          outcomes, expected):
    page = tmp_path / "index.html"
    page.write_text("<!doctype html><title>x</title>", encoding="utf-8")
    monkeypatch.setattr(publish_web, "PAGE", page)
    monkeypatch.setenv("GTA6_PUBLISH_TARGETS", "github,cloudflare")
    names = ["github", "cloudflare"]
    monkeypatch.setattr(publish_web, "PUBLISHERS", {
        n: (lambda n=n, ok=ok: Result(n, ok, "stub"))
        for n, ok in zip(names, outcomes)
    })
    publish_web.main()
    lines = [l for l in capsys.readouterr().out.strip().splitlines() if l.strip()]
    assert lines[-1] == expected, "the RESULT line must be last on stdout"


@pytest.mark.parametrize(("outcomes", "code"), [
    ([True, True], 0),
    ([True, False], 2),    # partial: live somewhere, but say so
    ([False, False], 1),
])
def test_partial_success_has_its_own_exit_code(monkeypatch, tmp_path,
                                              outcomes, code):
    page = tmp_path / "index.html"
    page.write_text("<!doctype html><title>x</title>", encoding="utf-8")
    monkeypatch.setattr(publish_web, "PAGE", page)
    monkeypatch.setenv("GTA6_PUBLISH_TARGETS", "github,cloudflare")
    names = ["github", "cloudflare"]
    monkeypatch.setattr(publish_web, "PUBLISHERS", {
        n: (lambda n=n, ok=ok: Result(n, ok, "stub"))
        for n, ok in zip(names, outcomes)
    })
    assert publish_web.main() == code


def test_wrangler_is_pinned_not_latest():
    """
    @latest would refetch npm on every unattended deploy, and wrangler's Node
    floor moves -- 4.127 needs Node 22 while Ubuntu 24.04's apt node is 18.
    """
    src = (publish_web.ROOT / "tools" / "publish_web.py").read_text(encoding="utf-8")
    assert "wrangler@latest" not in src
    assert 'CF_WRANGLER_VERSION' in src


def test_the_outer_timeout_exceeds_the_sum_of_the_inner_ones():
    from src import runner
    import inspect
    sig = inspect.signature(runner._publish_web_edition)
    outer = sig.parameters["timeout_s"].default
    assert outer >= publish_web.GITHUB_TIMEOUT_S + publish_web.CLOUDFLARE_TIMEOUT_S, (
        "the caller would kill a healthy-but-slow deploy and report a phantom timeout")


# ---------------------------------------------------------------------------
# The caller's interpretation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(("result_line", "url", "expect_broken"), [
    ("RESULT github=ok cloudflare=FAIL", "https://gta6-news.pages.dev/", "cloudflare"),
    ("RESULT github=FAIL cloudflare=ok", "https://gta6-news.pages.dev/", None),
    ("RESULT github=FAIL cloudflare=ok",
     "https://cserilevente.github.io/gtanewsbot/", "github"),
    ("RESULT github=ok cloudflare=ok", "https://gta6-news.pages.dev/", None),
    ("RESULT github=ok cloudflare=FAIL", "", None),          # nothing linked yet
])
def test_only_a_failure_of_the_LINKED_host_is_escalated(
        monkeypatch, result_line, url, expect_broken):
    """
    A broken standby is a warning. A broken linked host means every digest from
    now on sends members to a page that has stopped updating.
    """
    from src import runner
    monkeypatch.setenv("DIGEST_WEB_URL", url)
    assert runner._linked_host_failed(result_line) == expect_broken
