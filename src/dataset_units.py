"""Conservative unit defaults from explicit workbook declarations, never values."""
from pathlib import Path
import pandas as pd

FIELDS = {'vehicle frequency': 'vehicle_frequency_unit', 'observed vehicle frequency': 'vehicle_frequency_unit'}
UNITS = {
    'vehicle_frequency_unit': {
        'vehicles/hour': 'vehicles/hour', 'vehicles per hour': 'vehicles/hour',
    },
}


def documented_units(path):
    """Read exact Variable/Unit columns in Sources_Methodology. Conflicts stay blank."""
    if Path(path).suffix.lower() != '.xlsx':
        return {}
    with pd.ExcelFile(path) as book:
        sheet = next((s for s in book.sheet_names if s.lower() == 'sources_methodology'), None)
        if not sheet:
            return {}
        rows = pd.read_excel(book, sheet_name=sheet, header=None, nrows=200, keep_default_na=False)
    columns = None
    declared = {key: set() for key in UNITS}
    for row in rows.itertuples(index=False, name=None):
        cells = [str(value).strip().lower() for value in row]
        if 'variable' in cells and 'unit' in cells:
            columns = (cells.index('variable'), cells.index('unit'))
            continue
        if columns:
            variable, unit = cells[columns[0]], cells[columns[1]]
            key = FIELDS.get(variable)
            if key and unit:
                # Unknown declarations also count as conflicts; never silently replace them.
                declared[key].add(UNITS[key].get(unit, 'unsupported:' + unit))
    if any(any(v.startswith('unsupported:') for v in values) for values in declared.values()):
        raise ValueError('Vehicle Frequency must be documented as actual recorded operations in vehicles/hour. The workbook declares an incompatible unit.')
    return {key: next(iter(values)) for key, values in declared.items()
            if len(values) == 1 and not next(iter(values)).startswith('unsupported:')}
