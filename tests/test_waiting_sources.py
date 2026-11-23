"""Guard against fabricated labels, ambiguous extraction and mismatched joins."""
from pathlib import Path
import sys

from openpyxl import Workbook, load_workbook
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from etl_waiting_sources import parse_bus_line, extract_train, fetch_verified, write_review, BUS_CHECK

# Artificial row with the published column layout; never registered as research data.
LINE = '1 7/22/98 M B 7:14 W DN 1 7:17 7:15 7:15 2 10 1 2 3 0.3 1 11'


def test_bus_parser_keeps_departure_wait_distinct_from_system_target():
    row = parse_bus_line(LINE, 84)
    assert row['Recorded Wait to Bus Departure (minutes)'] == 3
    assert row['Station / Stop'] == 'Capitol Center'
    assert row['Day of Week'] == 'Wednesday'
    assert row['Month of Year'] == 'July'
    assert row['Scheduled Headway (minutes)'] == 10
    assert not {'Actual Waiting Time', 'Passenger Volume', 'Vehicle Frequency'} & row.keys()


@pytest.mark.parametrize('line,page', [
    (LINE.replace('7/22/98', '7/22198'), 84),
    (LINE.replace('7:17', '7:18'), 84),
    (LINE.replace('0.3', '0.4'), 84),
    (LINE, 85),
    (' '.join(LINE.split()[:-1]), 84),
])
def test_bus_parser_rejects_ocr_and_arithmetic_ambiguity(line, page):
    with pytest.raises(ValueError): parse_bus_line(line, page)


def survey_fixture(path, wait=8):
    w = Workbook(); s = w.active; s.title = '2927respondents'
    s.append(['ID', 'Sydney', 'Melbourn', 'Brisbane', 'Perth', 'Ampeak', 'Pmpeak', 'wtmins'])
    s.append([123, 1, 0, 0, 0, 1, 0, wait]); w.save(path)


def test_survey_preserves_reported_target_without_inventing_station_date_or_counts(tmp_path):
    path = tmp_path / 'survey.xlsx'; survey_fixture(path)
    rows = extract_train(path)
    assert rows[0]['Self-reported Waiting Time (minutes)'] == 8
    assert rows[0]['City'] == 'Sydney'
    assert not {'Actual Waiting Time', 'Passenger Volume', 'Vehicle Frequency', 'Station / Stop', 'Month of Year'} & rows[0].keys()
    survey_fixture(path, wait=-1)
    with pytest.raises(ValueError, match='Invalid self-reported wait'): extract_train(path)


def test_cached_source_changes_cannot_silently_change_extraction(tmp_path):
    path = tmp_path / 'source.pdf'; path.write_bytes(b'<html>not data</html>')
    with pytest.raises(ValueError, match='differs from the inspected source'):
        fetch_verified('https://example.invalid', path, '0' * 64)


def test_review_workbook_exposes_missing_predictors_and_keeps_raw_text_inert(tmp_path):
    path = tmp_path / 'review.xlsx'
    write_review(path, [parse_bus_line(LINE, 84)], BUS_CHECK, ['Not training-ready'],
                 {'source': 'Artificial fixture'}, [[84, 'Unparsed', '=1+1']], [2])
    w = load_workbook(path, data_only=False)
    assert w.sheetnames[0] == 'Read_First'
    assert w['Unparsed_PDF_Lines']['C2'].data_type == 's'
    assert w['Predictor_Check']['B2'].value == 'MISSING'
    assert w['Predictor_Check']['B3'].value == 'MISSING'
    assert 'Actual Waiting Time' not in [c.value for c in w['Recorded_Rows'][1]]
