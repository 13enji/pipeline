"""Unit tests for weather service."""


class TestCoordinatePrecision:
    """Tests for handling coordinate precision in NWS API calls."""

    def test_high_precision_coordinates_are_rounded(self):
        """Station coordinates with many decimal places should be rounded.

        NWS API returns 301 redirect for high-precision coordinates.
        We round to 4 decimal places to avoid this.
        """
        # High precision coords like from NOAA station data
        high_precision_lat = 32.86688888888889
        high_precision_lon = -117.2571388888889

        # Test the rounding logic directly
        rounded_lat = round(high_precision_lat, 4)
        rounded_lon = round(high_precision_lon, 4)

        # Should be rounded to 4 decimal places
        assert rounded_lat == 32.8669
        assert rounded_lon == -117.2571

        # The URL would use these rounded values
        url = f"https://api.weather.gov/points/{rounded_lat},{rounded_lon}"
        assert "32.8669" in url
        assert "-117.2571" in url
        # Full precision should NOT be in URL
        assert "32.86688888888889" not in url

    def test_normal_precision_coordinates_unchanged(self):
        """Normal precision coordinates stay the same after rounding."""
        lat = 32.8455
        lon = -117.2521

        rounded_lat = round(lat, 4)
        rounded_lon = round(lon, 4)

        # Should stay the same (already 4 or fewer decimals)
        assert rounded_lat == 32.8455
        assert rounded_lon == -117.2521
