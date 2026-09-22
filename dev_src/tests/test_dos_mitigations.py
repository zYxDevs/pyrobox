"""Unit tests for DoS mitigations: bounded QR generator, subtitle cache eviction, and directory walk bounds."""

import os
import pytest

from _fs_utils import get_tree_count_n_size
from server import (
	MAX_SUBTITLE_ENTRIES,
	_generate_qr_svg_bytes,
	store_subtitle,
	subtitle_location_map,
)
from pyroboxCore import config as CoreConfig


class TestQrGenerationCache:
	def test_qr_generation_in_memory_and_cached(self):
		url = "http://127.0.0.1:8000/test"
		svg1 = _generate_qr_svg_bytes(url)
		assert isinstance(svg1, bytes)
		assert b"<svg" in svg1
		assert b"</svg>" in svg1

		# Cache hit test
		hits_before = _generate_qr_svg_bytes.cache_info().hits
		svg2 = _generate_qr_svg_bytes(url)
		assert svg1 == svg2
		assert _generate_qr_svg_bytes.cache_info().hits == hits_before + 1


class TestSubtitleMapEviction:
	def test_subtitle_map_bounded_eviction(self, tmp_path):
		# Clean slate
		subtitle_location_map.clear()

		# Create mock temp files in CoreConfig.temp_dir
		temp_dir = CoreConfig.temp_dir
		os.makedirs(temp_dir, exist_ok=True)

		first_file = os.path.join(temp_dir, "evict_me_test.vtt")
		with open(first_file, "w") as f:
			f.write("WEBVTT\n")

		store_subtitle("sub_0", first_file)
		assert "sub_0" in subtitle_location_map
		assert os.path.exists(first_file)

		# Fill up to capacity
		for i in range(1, MAX_SUBTITLE_ENTRIES):
			store_subtitle(f"sub_{i}", f"/dummy/path_{i}.vtt")

		assert len(subtitle_location_map) == MAX_SUBTITLE_ENTRIES
		assert "sub_0" in subtitle_location_map

		# Adding one more item should evict sub_0 and delete its temp file
		store_subtitle("sub_overflow", "/dummy/overflow.vtt")
		assert len(subtitle_location_map) == MAX_SUBTITLE_ENTRIES
		assert "sub_0" not in subtitle_location_map
		assert "sub_overflow" in subtitle_location_map
		assert not os.path.exists(first_file)


class TestDirectoryTreeWalkBound:
	def test_tree_walk_stops_at_max_count(self, tmp_path):
		# Create 10 files in tmp_path
		for i in range(10):
			p = tmp_path / f"file_{i}.txt"
			p.write_text("data")

		# With max_count=5, should stop after counting 5 files
		count, total = get_tree_count_n_size(str(tmp_path), max_count=5)
		assert count == 5
		assert total > 0

		# With max_count=20, should count all 10 files
		count, total = get_tree_count_n_size(str(tmp_path), max_count=20)
		assert count == 10
