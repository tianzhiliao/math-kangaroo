export interface Manifest {
  schema_version: number;
  generated_at: string;
  exams: ManifestExamEntry[];
}

export interface ManifestExamEntry {
  exam_id: string;
  path: string;
  family: string;
  year: number;
  level: string;
  language: string;
  question_count: number;
  asset_count: number;
}

export interface PracticeBankEntry {
  exam_id: string;
  question_number: number;
  correct_label: string;
}

export interface PracticeBankResponse {
  total: number;
  entries: PracticeBankEntry[];
}

export interface AITextToSpeechRequest {
  exam_id: string;
  question_number: number;
  voice?: string;
  speed?: number;
  format?: string;
}

export interface AIExplanationRequest {
  exam_id: string;
  question_number: number;
  selected_label: string;
  force_refresh?: boolean;
}

export interface AIExplanationResponse {
  exam_id: string;
  question_number: number;
  selected_label: string;
  correct_label: string;
  explanation: string;
  model: string;
  cache_hit: boolean;
  generated_at: string;
}

export interface ScoringRule {
  from: number;
  to: number;
  points: number;
}

export interface AssetRecord {
  id: string;
  path: string;
  format: string;
  media_type: string;
  kind: string;
  role: string;
  width: number;
  height: number;
}

export interface Choice {
  label: string;
  text: string;
  asset_refs: string[];
}

export interface Question {
  id: string;
  number: number;
  part?: string;
  points?: number;
  stem_text: string;
  shared_asset_refs: string[];
  choices: Choice[];
}

export interface Exam {
  exam_id: string;
  year: number;
  family: string;
  level: string;
  language: string;
  duration_minutes: number | null;
  question_count: number;
  scoring_rules: ScoringRule[];
  instructions: string[];
  answer_key: Record<string, string>;
  assets: AssetRecord[];
  questions: Question[];
}
