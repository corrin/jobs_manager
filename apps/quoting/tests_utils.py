"""Tests for quoting utility functions."""

from django.test import TestCase

from apps.quoting.utils import calculate_sheet_tenths


class TestCalculateSheetTenths(TestCase):
    """Tests for the calculate_sheet_tenths function."""

    def test_single_tenth(self):
        """Part that fits in one section."""
        assert calculate_sheet_tenths(400, 300) == 1
        assert calculate_sheet_tenths(600, 480) == 1  # Exactly one section
        assert calculate_sheet_tenths(599, 479) == 1  # Just under one section

    def test_two_tenths_horizontal(self):
        """Part that spans two sections horizontally."""
        assert calculate_sheet_tenths(650, 450) == 2  # 2 wide x 1 tall
        assert calculate_sheet_tenths(601, 400) == 2  # Just over section width

    def test_two_tenths_vertical(self):
        """Part that spans two sections vertically."""
        assert calculate_sheet_tenths(500, 500) == 2  # 1 wide x 2 tall
        assert calculate_sheet_tenths(400, 481) == 2  # Just over section height

    def test_four_tenths(self):
        """Part that spans four sections (2x2)."""
        assert calculate_sheet_tenths(700, 700) == 4  # 2 wide x 2 tall
        assert calculate_sheet_tenths(601, 481) == 4  # Just over both dimensions

    def test_full_width_parts(self):
        """Parts that span the full width of the sheet."""
        assert calculate_sheet_tenths(1100, 500) == 4  # 2 wide x 2 tall
        assert calculate_sheet_tenths(1200, 480) == 2  # Full width, 1 tall
        assert calculate_sheet_tenths(1200, 481) == 4  # Full width, 2 tall

    def test_full_height_parts(self):
        """Parts that span the full height of the sheet."""
        assert calculate_sheet_tenths(600, 2400) == 5  # 1 wide x 5 tall (full height)
        assert calculate_sheet_tenths(601, 2400) == 10  # 2 wide x 5 tall

    def test_example_from_user(self):
        """Test the specific example: 700x700 should be 4 tenths."""
        result = calculate_sheet_tenths(700, 700)
        assert result == 4, f"Expected 4 tenths for 700x700, got {result}"

    def test_custom_sheet_size(self):
        """Test with non-standard sheet dimensions."""
        # 1000x1000 sheet divided into 5x2 = sections of 500x200
        assert calculate_sheet_tenths(250, 100, 1000, 1000) == 1
        assert calculate_sheet_tenths(501, 100, 1000, 1000) == 2

    def test_invalid_dimensions(self):
        """Test error handling for invalid inputs."""
        with self.assertRaisesRegex(ValueError, "must be positive"):
            calculate_sheet_tenths(0, 100)

        with self.assertRaisesRegex(ValueError, "must be positive"):
            calculate_sheet_tenths(100, -50)

        with self.assertRaisesRegex(ValueError, "exceed sheet dimensions"):
            calculate_sheet_tenths(1300, 500)  # Wider than sheet

        with self.assertRaisesRegex(ValueError, "exceed sheet dimensions"):
            calculate_sheet_tenths(500, 2500)  # Taller than sheet

    def test_edge_case_exactly_on_boundary(self):
        """Parts that are exactly on section boundaries."""
        # Exactly 1 section
        assert calculate_sheet_tenths(600, 480) == 1

        # Exactly 2 sections wide
        assert calculate_sheet_tenths(1200, 480) == 2

        # Exactly 5 sections tall
        assert calculate_sheet_tenths(600, 2400) == 5

        # Exactly full sheet
        assert calculate_sheet_tenths(1200, 2400) == 10

    def test_very_small_part(self):
        """Very small parts should use 1 tenth."""
        assert calculate_sheet_tenths(10, 10) == 1
        assert calculate_sheet_tenths(1, 1) == 1
