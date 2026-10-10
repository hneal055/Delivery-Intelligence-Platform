import os
from datetime import datetime, timezone

import pytest

from src.backend.core.storage import LocalProofStorage, filename_timestamp


def test_timestamp_from_current_filename():
    stamp = filename_timestamp("PKG1_D001_20261010T143000Z.jpg")
    assert stamp == datetime(2026, 10, 10, 14, 30, tzinfo=timezone.utc)


def test_timestamp_from_legacy_simulator_filename():
    stamp = filename_timestamp("PKG-D001-1770914907-5763_D001.jpg")
    assert stamp == datetime.fromtimestamp(1770914907, timezone.utc)


def test_no_timestamp_returns_none():
    assert filename_timestamp("pkg_driver.jpg") is None


@pytest.mark.asyncio
async def test_list_recent_newest_first_and_limited(tmp_path):
    store = LocalProofStorage()
    store.base_dir = str(tmp_path)
    for name in [
        "A_D1_20261001T000000Z.jpg",
        "B_D1_20261003T000000Z.jpg",
        "PKG-D001-1000000000-1_D001.jpg",  # 2001, oldest
        "C_D1_20261002T000000Z.jpg",
        "notes.txt",
    ]:
        (tmp_path / name).write_bytes(b"x")

    items = await store.list_recent(limit=2)

    assert [i["packageId"] for i in items] == ["B", "C"]
    assert items[0]["url"] == "/delivery/proof/B_D1_20261003T000000Z.jpg"


@pytest.mark.asyncio
async def test_list_recent_falls_back_to_mtime(tmp_path):
    store = LocalProofStorage()
    store.base_dir = str(tmp_path)
    path = tmp_path / "pkg_driver.jpg"
    path.write_bytes(b"x")
    os.utime(path, (1_800_000_000, 1_800_000_000))

    items = await store.list_recent()

    assert items[0]["timestamp"] == datetime.fromtimestamp(1_800_000_000, timezone.utc).isoformat()


def test_proof_filenames_are_unique_within_a_second():
    from src.backend.core.storage import build_proof_filename
    names = {build_proof_filename("PKG1", "driver2") for _ in range(50)}
    assert len(names) == 50


def test_timestamp_parsed_from_suffixed_filename():
    stamp = filename_timestamp("PKG1_driver2_20261010T143000Z-1a2b3c4d.jpg")
    assert stamp == datetime(2026, 10, 10, 14, 30, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_two_saves_in_the_same_second_keep_both_photos(tmp_path):
    store = LocalProofStorage()
    store.base_dir = str(tmp_path)
    first = await store.save_proof("PKG1", "driver2", b"first")
    second = await store.save_proof("PKG1", "driver2", b"second")
    assert first != second
    assert await store.get_proof(first) == b"first"
    assert await store.get_proof(second) == b"second"
