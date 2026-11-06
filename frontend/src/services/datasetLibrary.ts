// Every selection uses normal upload validation; incomplete references are rejected.
export interface LibraryDataset {
  id: string; title: string; mode: string; records: number; filename: string;
  kind: 'demo' | 'prototype' | 'reference'; recordLabel: string;
  note?: string; sourceUrl?: string; sourceLabel?: string; licenseFile?: string;
}
export const datasetLibrary: LibraryDataset[] = [
  {id: 'bus-demo', title: 'Bus waiting-time demo', mode: 'Bus', records: 180,
    filename: 'transit_bus_SYNTHETIC_DEMO.xlsx', kind: 'demo', recordLabel: 'observations'},
  {id: 'train-demo', title: 'Train waiting-time demo', mode: 'Train', records: 180,
    filename: 'transit_train_SYNTHETIC_DEMO.xlsx', kind: 'demo', recordLabel: 'observations'},
  {id: 'earlier-500', title: 'Earlier 500-row transportation demo', mode: 'Unspecified', records: 500,
    filename: 'transportation_dataset_500_demo_validated.xlsx', kind: 'demo', recordLabel: 'observations'},
  {id: 'earlier-200', title: 'Earlier 200-row transportation prototype', mode: 'Unspecified', records: 200,
    filename: 'transportation_dataset_200_demo_fixed.xlsx', kind: 'prototype', recordLabel: 'observations'},
  {id: 'earlier-40', title: 'Original 40-row transportation prototype', mode: 'Unspecified', records: 40,
    filename: 'transportation_dataset_40_ph_internet_rows.xlsx', kind: 'prototype', recordLabel: 'observations',
    note: 'Constant predictors and undefined units prevent a valid final station condition.'},
  {id: 'mrt3-ridership', title: 'MRT-3 daily ridership · Jan–Apr 2024', mode: 'Train', records: 121,
    filename: 'mrt3_daily_ridership_jan_apr_2024.csv', kind: 'reference', recordLabel: 'calendar days',
    note: 'Whole-line daily passenger counts, with four source days left blank. This third-party copy of a DOTr-MRT3 report needs agency verification. It has no measured passenger waiting times or six matching predictors, so it cannot be analyzed as a complete dataset.',
    sourceLabel: 'Published MRT-3 report (third-party copy)', sourceUrl: 'https://mediaworldadvertising.b-cdn.net/wp-content/uploads/2024/06/RIDERSHIP-REPORT-2024.pdf'},
  {id: 'sakay-frequency', title: 'Metro Manila historical transit schedules', mode: 'Bus / train / jeepney', records: 1864,
    filename: 'metro_manila_historical_scheduled_frequency.csv', kind: 'reference', recordLabel: 'schedule windows',
    note: 'Historical Sakay/DOTC schedules; calendar ends 30 June 2020. Frequency is derived from scheduled headway, not observed arrivals. Waiting times and matching predictors are missing. Road-transit entries can include jeepneys. This is not current-service data or a complete analysis dataset.',
    sourceLabel: 'Sakay.ph GTFS repository', sourceUrl: 'https://github.com/sakayph/gtfs', licenseFile: 'SAKAY-GTFS-LICENSE.md'},
]
