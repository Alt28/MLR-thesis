"""Extract published factual table cells, without using the simulated results.

Run with a Python installation containing pdfplumber. The downloaded PDF must
already be in source/. Table rectangles were checked against rendered pages.
"""
from pathlib import Path
import hashlib
import json

import pdfplumber

ROOT = Path(__file__).resolve().parent
PDF = ROOT / 'source/TSSP2024-Vol7-No2_01-Ollero-Vergel-and-Tiglao.pdf'


def cell(page, box):
    left, top, right, bottom = box
    words = [w for w in page.extract_words()
             if left <= (w['x0'] + w['x1']) / 2 < right
             and top <= (w['top'] + w['bottom']) / 2 < bottom]
    return ' '.join(w['text'] for w in words)


with pdfplumber.open(PDF) as doc:
    dwell = []
    for direction, cols in [('Northbound', (72, 163, 215, 281)),
                            ('Southbound', (326, 442, 495, 550))]:
        for page_index, bounds in [(10, [684, 701, 715, 730, 760]),
                                   (11, [83 + i * 14.4 for i in range((15 if direction == 'Northbound' else 17) + 1)])]:
            for top, bottom in zip(bounds, bounds[1:]):
                station, am, pm = [cell(doc.pages[page_index], (left, top, right, bottom))
                                   for left, right in zip(cols, cols[1:])]
                assert station and am.isdigit() and pm.isdigit(), (station, am, pm)
                dwell.append(dict(direction=direction, station=station,
                                  am_peak_seconds=int(am), pm_peak_seconds=int(pm),
                                  source_page=page_index + 1))
    coverage = []
    for row in doc.pages[8].extract_tables()[0][1:-1]:
        vals = [v for v in row if v]
        operator, date, buses, roundtrips = vals
        coverage.append(dict(operator=operator, date=date, buses=int(buses), roundtrips=int(roundtrips)))
    # Table 3 has no ruled border. Each numeric pair shares one text line.
    import re
    flows = []
    for line in doc.pages[9].extract_text().splitlines():
        match = re.fullmatch(r'(\d+:\d+ [ap]m - \d+:\d+ [ap]m) (\d+) (\d+)', line.strip())
        if match:
            flows.append(dict(time=match[1], southbound=int(match[2]), northbound=int(match[3])))
    assert len(flows) == 6
    # Independently compare Table 3 counts with the Actual column in Table 5.
    actual = []
    for line in doc.pages[12].extract_text().splitlines():
        match = re.match(r'\d+:\d+ [ap]m - \d+:\d+ [ap]m (\d+) ', line.strip())
        if match:
            actual.append(int(match[1]))
    assert actual == [r['southbound'] for r in flows] + [r['northbound'] for r in flows]

assert len(dwell) == 40
assert len({(r['direction'], r['station']) for r in dwell}) == 40
assert len(coverage) == 9 and len({r['date'] for r in coverage}) == 8
assert sum(r['buses'] for r in coverage) == 29
assert sum(r['roundtrips'] for r in coverage) == 105
result = dict(source_sha256=hashlib.sha256(PDF.read_bytes()).hexdigest(),
              dwell=dwell, bus_counts=flows, survey_coverage=coverage,
              verification={'dwell_numeric_cells': 80, 'bus_counts_match_actual_column_table_5': True,
                            'survey_total_buses': 29, 'survey_total_roundtrips': 105})
(ROOT / 'source/extracted_tables.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('Extracted 80 dwell-time means, 12 bus counts and 9 survey-coverage rows from the PDF.')
