export interface LibraryDataset {
  id: string; title: string; mode: string; records: number; filename: string;
  kind: 'collected' | 'source_review'; recordLabel: string; note?: string;
}
