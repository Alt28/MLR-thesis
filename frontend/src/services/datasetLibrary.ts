// Demo and prototype selections use normal upload validation.
export interface LibraryDataset {
  id: string; title: string; mode: string; records: number; filename: string;
  kind: 'demo' | 'prototype'; recordLabel: string;
  note?: string;
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
]
