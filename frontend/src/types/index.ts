export type TransportMode = 'all' | 'bus' | 'train' | 'unspecified'
export type Cell = string | number | boolean | null
export type Row = Record<string, Cell>
export interface ResearchConfig {
  test_size: number; random_state: number; split_method: 'random' | 'grouped'; split_group_column: string;
  iqr_multiplier: number; iqr_columns: string[];
  pairwise_interactions: string[][]; higher_order_interactions: string[][];
  category_severity: Record<string, Record<string, number>>;
  numerical_directions: Record<string, 'higher' | 'lower' | null>;
  vehicle_frequency_unit: string; route_distance_unit: string;
  research_notes?: Record<string, string>;
  wait_thresholds: number[]; station_thresholds: number[]; negative_wait_rule: string;
}
export interface Experiment {
  id: string; name: string; created: string; revision: number;
  status: 'ready' | 'running' | 'partial' | 'complete' | 'error'; error: string | null;
  approved: boolean; config: ResearchConfig; records: number; training: number; reviewed_training: number;
  test: number; flagged: number; reviewed: number; metadata: string[]; trained: string[];
  metrics: { Model: string; MSE: number; RMSE: number }[];
  mode_metrics: Row[];
  station_aggregation: {
    available: boolean; grouping_column: string; reason: string | null;
    station_count: number; ungrouped_records: number; aggregation?: string;
  };
  comparison: Row[]; conclusion: string | null; warnings: string[];
  provenance?: {status: 'prototype' | 'recorded_declared' | 'undocumented'; message: string; workbook_declares_prototype: boolean; workbook_notes: Record<string, string>[]; researcher_notes: Record<string, string>};
  transport?: {column: string | null; dataset_counts: Record<'bus' | 'train' | 'unspecified', number>; test_counts: Record<'bus' | 'train' | 'unspecified', number>; source: string};
  study_available?: boolean; study_metrics?: Row[]; study_comparisons?: Row[];
  classification_version?: number; classification_stale?: boolean;
  distribution: Record<string, number>; evidence: Row[]; thresholds: Row[]; figures: string[]; export_ready: boolean;
}
export interface ExperimentListItem { id: string; name: string; created: string; revision: number }
export interface TableResult { columns: string[]; rows: Row[]; total: number; offset: number }
export interface PredictionOutput {
  columns: string[]; rows: Row[]; station_summary: Row[];
  station_aggregation: {
    available: boolean; grouping_column: string; reason: string | null;
    station_count: number; ungrouped_records: number; aggregation?: string;
  };
  experiment_id: string; model_revision: number;
}
export const PREDICTORS = ['Traffic Condition', 'Weather Condition', 'Passenger Volume', 'Route Distance', 'Vehicle Frequency', 'Time of Day']
export const CATEGORICAL = ['Traffic Condition', 'Weather Condition', 'Time of Day']
export const NUMERICAL = ['Passenger Volume', 'Route Distance', 'Vehicle Frequency']
export const TARGET = 'Actual Waiting Time'
export const LABELS = ['Normal Operation', 'Minor Delay', 'Moderate Delay', 'Severe Delay']
