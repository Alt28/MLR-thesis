import pytest
from src.measurements import observed_frequency, scheduled_frequency


def test_frequency_measurements_have_explicit_basis():
    assert observed_frequency(6, 30) == 12
    assert observed_frequency(0, 60) == 0
    assert scheduled_frequency(240) == 15


@pytest.mark.parametrize('count,window', [(1,None), (1,0), (1,-5), (-1,60), (1.5,60), (1,float('inf')), (float('nan'),60)])
def test_invalid_counting_windows_are_not_reinterpreted(count,window):
    with pytest.raises((ValueError,TypeError)):
        observed_frequency(count,window)


@pytest.mark.parametrize('headway', [0,-1,float('nan'),float('inf')])
def test_headway_is_not_a_waiting_time_target(headway):
    with pytest.raises(ValueError):
        scheduled_frequency(headway)
