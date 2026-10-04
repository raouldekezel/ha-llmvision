"""BUG-02 regression pins: snapshot cleanup across several Timeline instances."""

import asyncio
import datetime
import errno
import logging
import os
from collections import Counter
from functools import partial
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from custom_components.llmvision.timeline import Timeline

TIMELINE_LOGGER = "custom_components.llmvision.timeline"
ORPHANS = [f"orphan-{i}.jpg" for i in range(6)]
RENDEZVOUS_TIMEOUT = 0.5


class _Rendezvous:
    """Holds each arriving task until `parties` tasks arrived or the timeout expires."""

    def __init__(self, parties: int, timeout: float):
        self._parties = parties
        self._timeout = timeout
        self._all_arrived = asyncio.Event()
        self.arrivals = 0

    async def arrive(self) -> None:
        self.arrivals += 1
        if self.arrivals >= self._parties:
            self._all_arrived.set()
            return
        try:
            await asyncio.wait_for(self._all_arrived.wait(), self._timeout)
        except TimeoutError:
            pass


class _Executor:
    """Runs each job inline, then yields to the event loop like a real executor.

    When a rendezvous is set, a task that has just listed a directory waits
    there for the other tasks to list it too.
    """

    def __init__(self):
        self.listing_rendezvous: _Rendezvous | None = None

    @staticmethod
    def _is_listdir(func) -> bool:
        target = func.func if isinstance(func, partial) else func
        return target is os.listdir

    async def __call__(self, func, *args):
        result = func(*args)
        if self.listing_rendezvous is not None and self._is_listdir(func):
            await self.listing_rendezvous.arrive()
        await asyncio.sleep(0)
        return result


@pytest.fixture
def env(tmp_path, monkeypatch):
    """One mock hass shared by every Timeline built from it, plus a snapshots folder."""
    config_path = tmp_path / "config"
    config_path.mkdir()
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()

    real_makedirs = os.makedirs

    def safe_makedirs(path, exist_ok=False):
        # The production snapshots path is hard-coded under /media.
        if str(path).startswith("/media/llmvision"):
            return
        return real_makedirs(path, exist_ok=exist_ok)

    monkeypatch.setattr(
        "custom_components.llmvision.timeline.os.makedirs", safe_makedirs
    )

    executor = _Executor()
    hass = Mock()
    hass.data = {}
    hass.config = Mock()
    hass.config.path = lambda *parts: str(config_path.joinpath(*parts))
    hass.loop = Mock()
    hass.loop.run_in_executor = lambda _executor, func, *args: executor(func, *args)
    hass.async_add_executor_job = executor
    hass.async_create_task = lambda coro: coro.close()

    def build() -> Timeline:
        entry = Mock()
        entry.entry_id = "settings-entry"
        entry.data = {"provider": "Settings", "retention_time": 7}
        entry.options = {}
        timeline = Timeline(hass, entry)
        timeline._media_path = str(snapshots)
        timeline._migrating = False
        return timeline

    old = datetime.datetime.now().timestamp() - 100
    for name in ORPHANS:
        path = snapshots / name
        path.write_bytes(b"fake")
        os.utime(path, (old, old))

    return SimpleNamespace(executor=executor, snapshots=snapshots, build=build)


@pytest.fixture
def removals(monkeypatch):
    """Counts removal attempts per file name; removals still happen for real."""
    attempts: Counter = Counter()
    real_remove = os.remove

    def counting_remove(path, *args, **kwargs):
        attempts[os.path.basename(path)] += 1
        return real_remove(path, *args, **kwargs)

    monkeypatch.setattr(os, "remove", counting_remove)
    monkeypatch.setattr(os, "unlink", counting_remove)
    return attempts


def _warnings(caplog) -> list[logging.LogRecord]:
    return [
        r
        for r in caplog.records
        if r.name == TIMELINE_LOGGER and r.levelno >= logging.WARNING
    ]


class TestBug02CleanupConcurrency:
    """Cleanup passes started from distinct Timeline instances on one hass."""

    async def test_bug02_concurrent_passes_remove_each_orphan_once(
        self, env, removals, caplog
    ):
        caplog.set_level(logging.DEBUG, logger=TIMELINE_LOGGER)
        first = env.build()
        second = env.build()
        await first._initialize_db()
        rendezvous = _Rendezvous(parties=2, timeout=RENDEZVOUS_TIMEOUT)
        env.executor.listing_rendezvous = rendezvous

        await asyncio.gather(first._cleanup(), second._cleanup())

        assert rendezvous.arrivals == 2
        assert os.listdir(env.snapshots) == []
        assert removals == Counter({name: 1 for name in ORPHANS})
        assert _warnings(caplog) == []

    async def test_bug02_file_vanishing_before_removal_is_not_a_warning(
        self, env, monkeypatch, caplog
    ):
        caplog.set_level(logging.DEBUG, logger=TIMELINE_LOGGER)
        timeline = env.build()
        await timeline._initialize_db()
        real_remove = os.remove

        def removed_by_someone_else_first(path, *args, **kwargs):
            real_remove(path)
            return real_remove(path, *args, **kwargs)

        monkeypatch.setattr(os, "remove", removed_by_someone_else_first)
        monkeypatch.setattr(os, "unlink", removed_by_someone_else_first)

        await timeline._cleanup()

        assert os.listdir(env.snapshots) == []
        assert _warnings(caplog) == []

    async def test_bug02_other_removal_errors_stay_warnings(
        self, env, monkeypatch, caplog
    ):
        caplog.set_level(logging.DEBUG, logger=TIMELINE_LOGGER)
        timeline = env.build()
        await timeline._initialize_db()

        def permission_denied(path, *args, **kwargs):
            raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), path)

        monkeypatch.setattr(os, "remove", permission_denied)
        monkeypatch.setattr(os, "unlink", permission_denied)

        await timeline._cleanup()

        warned = " ".join(r.getMessage() for r in _warnings(caplog))
        assert sorted(os.listdir(env.snapshots)) == sorted(ORPHANS)
        for name in ORPHANS:
            assert name in warned
