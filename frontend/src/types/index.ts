export type TransportMode = 'all' | 'bus' | 'train' | 'unspecified'
export type Cell = string | number | boolean | null
export type Row = Record<string, Cell>
export const SCHEMA_VERSION = "station-calendar-v2"
export interface ResearchConfig {
  schema_version: string; classification_approved: boolean; observed_targets_confirmed: boolean; prediction_inputs_available: boolean;
  test_size: number; random_state: number; split_method: 'random' | 'grouped'; split_group_column: string;
  iqr_multiplier: number; iqr_columns: string[];
  pairwise_interactions: string[][]; higher_order_interactions: string[][];
  center_interactions?: boolean; hierarchical_interactions?: boolean; cv_folds?: number; cv_repeats?: number;
  category_severity: Record<string, Record<string, number>>;
  category_scoring?: 'automatic' | 'manual';
  numerical_directions: Record<string, 'higher' | 'lower' | null>;
  vehicle_frequency_unit: string;
  research_notes?: Record<string, string>;
  wait_thresholds: number[]; station_thresholds: number[]; negative_wait_rule: string;
  severity_basis?: 'adjusted' | 'marginal';
}
export interface Experiment {
  compatible: boolean; transport_mode: string; schema_version: string;
  id: string; name: string; created: string; revision: number;
  status: 'ready' | 'running' | 'partial' | 'complete' | 'error'; error: string | null;
  approved: boolean; config: ResearchConfig; records: number; training: number; reviewed_training: number;
  test: number; flagged: number; reviewed: number; metadata: string[]; trained: string[];
  metrics: { Model: string; MSE: number; RMSE: number; MAE?: number | null; R2?: number | null }[];
  mode_metrics: Row[];
  validation?: {
    available: boolean; heldout: Row[]; cv_summary: Row[]; cv_test: Row[];
    cv_design: {design?: string; folds?: number; repeats?: number; fitted_folds?: number};
    classification: Row[]; notes: string[];
  };
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
export interface ExperimentListItem { id: string; name: string; created: string; revision: number; status: Experiment['status']; compatible: boolean; transport_mode: string }
export interface DatasetInspection {
  purpose: 'training' | 'prediction' | 'source_review'; rows: number; recorded_waits: number; unknown_waits: number;
  missing_predictors: Record<string, number>; source_notes: string[];
  target_column_present: boolean; schema_version: string; preview: Row[]; columns: string[]; transport_mode: string; warnings: string[];
}
export interface TableResult { columns: string[]; rows: Row[]; total: number; offset: number }
export interface PredictionOutput {
  columns: string[]; rows: Row[]; station_summary: Row[];
  station_aggregation: {
    available: boolean; grouping_column: string; reason: string | null;
    station_count: number; ungrouped_records: number; aggregation?: string;
  };
  experiment_id: string; model_revision: number;
}
export const PREDICTORS = ['Passenger Volume', 'Vehicle Frequency', 'Station / Stop', 'Time of Day', 'Day of Week', 'Month of Year']
export const CATEGORICAL = ['Station / Stop', 'Time of Day', 'Day of Week', 'Month of Year']
export const NUMERICAL = ['Passenger Volume', 'Vehicle Frequency']
export const TARGET = 'Actual Waiting Time'
export const LABELS = ['Normal Operation', 'Minor Delay', 'Moderate Delay', 'Severe Delay']
