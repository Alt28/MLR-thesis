// Demo and prototype selections use normal upload validation.
export interface LibraryDataset {
  id: string; title: string; mode: string; records: number; filename: string;
  kind: 'demo' | 'prototype'; recordLabel: string;
  note?: string;
}
export const datasetLibrary: LibraryDataset[] = [
  {id: 'bus-train-500', title: '500-row bus & train dataset', mode: 'Bus & Train', records: 500,
    filename: 'transportation_dataset_500_bus_train.xlsx', kind: 'prototype', recordLabel: 'observations',
    note: '500-row transportation workbook labelled with 250 bus and 250 train transport modes.'},
]
