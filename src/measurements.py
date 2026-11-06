"""Explicit unit conversions for dataset preparation; never applied silently by MLR."""
import math

STUDY_FREQUENCY_UNIT = 'vehicles/hour'
STUDY_DISTANCE_UNIT = 'km'


def observed_frequency(vehicle_count, window_minutes):
    """Observed service events per hour in a documented counting window."""
    count, window = float(vehicle_count), float(window_minutes)
    if not math.isfinite(count) or count < 0 or not count.is_integer():
        raise ValueError('Observed vehicle count must be a nonnegative integer.')
    if not math.isfinite(window) or window <= 0:
        raise ValueError('A positive observed counting window in minutes is required.')
    return 60.0 * count / window


def scheduled_frequency(headway_seconds):
    """Scheduled service rate from a documented GTFS headway, not observed wait."""
    seconds = float(headway_seconds)
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('Scheduled headway must be positive seconds.')
    return 3600.0 / seconds
