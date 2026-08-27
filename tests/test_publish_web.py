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
    ([True, False], 0),    # redundancy is the point: one host is enough
    ([False, True], 0),
    ([False, False], 1),   # nothing published anywhere
])
def test_exit_code_succeeds_when_at_least_one_host_published(
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
