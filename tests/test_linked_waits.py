"""Artificial fixtures verify exact survey joins; never used as research data."""
from copy import deepcopy
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from etl_linked_waits import merge_survey, records


def survey():
    return {
        'Etapa': [
            {'Hogar': 10, 'Persona': 1, 'Viaje': 2, 'Etapa': 1, 'ModoEtapa': 3,
             'TiempoEspera': 0, 'RecorridoBus': 6},
            {'Hogar': 11, 'Persona': 1, 'Viaje': 2, 'Etapa': 1, 'ModoEtapa': 4,
             'TiempoEspera': 7, 'EstacionMetroIni': 1},
        ],
        'Viaje': [
            {'Hogar': 10, 'Persona': 1, 'Viaje': 2, 'HoraIni': '1899-12-30 07:00:00'},
            {'Hogar': 11, 'Persona': 1, 'Viaje': 2, 'HoraIni': '1899-12-30 09:00:00'},
        ],
        'Hogar': [
            {'Hogar': 10, 'Fecha': '2014-11-25 00:00:00', 'DiaAsig': 2},
            {'Hogar': 11, 'Fecha': '2014-12-02 00:00:00', 'DiaAsig': 2},
        ],
        'ModoEtapa': [{'id modo': 3, 'Modo ext': 'Bus urbano '}, {'id modo': 4, 'Modo ext': 'Metro Valparaiso '}],
        'EstacionMetro Ori': [{'Id': 1, 'EstacionMetro': 'Puerto'}],
        'RecorridoBus': [{'ID': 6, 'RecorridoBus': '101'}],
    }


def test_exact_household_person_trip_join_preserves_reported_wait_and_zero():
    result, audit = merge_survey(survey())
    bus, train = result['Bus'][0], result['Train'][0]
    assert bus['Reported Waiting Time (minutes)'] == 0
    assert train['Reported Waiting Time (minutes)'] == 7
    assert bus['Whole-trip Start Time'] == '07:00:00'
    assert train['Whole-trip Start Time'] == '09:00:00'
    assert train['Boarding Station (train only)'] == 'Puerto'
    assert bus['Boarding Station (train only)'] is None
    assert bus['Bus Route'] == '101'
    assert not {'Passenger Volume', 'Vehicle Frequency', 'Actual Waiting Time', 'Observation Date'} & bus.keys()
    assert audit['matched_trip_rows'] == audit['unique_output_records'] == 2


@pytest.mark.parametrize('table', ['Viaje', 'Hogar', 'Etapa', 'EstacionMetro Ori', 'RecorridoBus'])
def test_duplicate_join_keys_fail_instead_of_multiplying_rows(table):
    tables = survey()
    tables[table].append(deepcopy(tables[table][0]))
    with pytest.raises(ValueError, match='Duplicate source key'):
        merge_survey(tables)


def test_unmatched_trip_does_not_borrow_wait_from_another_household():
    tables = survey()
    tables['Viaje'].pop()
    with pytest.raises(ValueError, match='Unmatched survey key'):
        merge_survey(tables)


@pytest.mark.parametrize('wait', [None, -1, float('nan'), 'unknown'])
def test_missing_wait_is_never_imputed(wait):
    tables = survey()
    tables['Etapa'][0]['TiempoEspera'] = wait
    with pytest.raises(ValueError, match='reported waiting'):
        merge_survey(tables)


def test_incomplete_parser_columns_fail():
    with pytest.raises(ValueError, match='column lengths'):
        records({'id': [1, 2], 'wait': [4]})


def test_unknown_station_not_replaced_by_city_or_route():
    tables = survey()
    tables['Etapa'][1]['EstacionMetroIni'] = 999
    with pytest.raises(ValueError, match='Unknown station'):
        merge_survey(tables)
