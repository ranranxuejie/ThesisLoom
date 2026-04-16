export type LogMode = "key" | "detail";

export interface WorkflowStateSnapshot {
  ok: boolean;
  has_checkpoint?: boolean;
  message?: string;
  server_time?: string;
  project_name?: string;
  project_root?: string;
  topic?: string;
  model?: string;
  language?: string;
  workflow_phase?: string;
  passed?: boolean;
  runtime_status?: string;
  runtime_message?: string;
  runtime_time?: string;
  runtime_interaction_mode?: string;
  current_node?: string;
  current_major_chapter_id?: string;
  current_sub_chapter_id?: string;
  pending_action?: string;
  pending_action_message?: string;
  next_steps_plan?: Array<{
    phase?: string;
    order?: number;
    major_chapter_id?: string;
    major_title?: string;
    sub_chapter_id?: string;
    sub_title?: string;
    status?: string;
    updated_at?: string;
  }>;
  next_steps_updated_at?: string;
  review_round?: number;
  max_review_rounds?: number;
  completed_section_count?: number;
  pending_rewrite_count?: number;
  total_words?: number;
  checkpoint_path?: string;
  checkpoint_mtime?: string;
  output_path?: string;
  last_checkpoint_reason?: string;
  related_works_path?: string;
  research_gap_output_path?: string;
  manual_revision_path?: string;
  inputs_path?: string;
  inputs_topic?: string;
  inputs_model?: string;
  inputs_language?: string;
  search_query_count?: number;
  search_queries?: string[];
  paper_outputs?: Array<{
    sub_chapter_id?: string;
    title?: string;
    major_title?: string;
    actual_order_index?: number;
    content?: string;
  }>;
  architect_outline?: Array<Record<string, unknown>>;
  planner_outputs?: Array<Record<string, unknown>>;
  user_image_descriptions?: Array<Record<string, unknown>>;
  planned_image_descriptions?: Array<Record<string, unknown>>;
  image_planning_done?: boolean;
  image_planning_summary?: string;
  overall_review_summary?: string;
  overall_review_plans?: Array<Record<string, unknown>>;
  major_review_items?: Array<Record<string, unknown>>;
  rewrite_done_sub_ids?: string[];
  version_snapshots?: Array<{
    tag?: string;
    label?: string;
    saved_at?: string;
    markdown_path?: string;
    state_path?: string;
    is_key_node?: boolean;
    key_label?: string;
  }>;
  key_milestones?: Array<{
    tag?: string;
    label?: string;
    time?: string;
    state_path?: string;
  }>;
  token_usage?: {
    total_input_tokens?: number;
    total_output_tokens?: number;
    total_input_cost_usd?: number;
    total_output_cost_usd?: number;
    total_cost_usd?: number;
    pricing_source?: string;
    pricing_currency?: string;
    [key: string]: unknown;
  };
  workflow_metrics?: {
    steps?: Record<
      string,
      {
        count?: number;
        total_seconds?: number;
        avg_seconds?: number;
        last_seconds?: number;
        [key: string]: unknown;
      }
    >;
    totals?: {
      step_calls?: number;
      total_step_seconds?: number;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
  action_preferences?: Record<string, unknown>;
  action_history?: Array<Record<string, unknown>>;
}

export interface InputsPayload {
  ok: boolean;
  path?: string;
  raw?: string;
  data?: Record<string, unknown>;
  message?: string;
}

export interface ActionResult {
  ok: boolean;
  message?: string;
}

export interface FilePayload {
  ok: boolean;
  path?: string;
  content?: string;
  message?: string;
}

export interface LogsPayload {
  ok: boolean;
  mode: LogMode;
  items: Array<{
    time?: string;
    level?: string;
    message?: string;
    detail_line?: string;
    [key: string]: unknown;
  }>;
}

export interface EditableFilesPayload {
  ok: boolean;
  items: string[];
}

export interface BackendStatus {
  running: boolean;
  pid: number | null;
  message: string;
  workspace_root: string;
  python_path: string;
}

export interface ProjectsPayload {
  ok: boolean;
  items: string[];
  current: string;
  message?: string;
}

export interface ProjectOpenResult {
  ok: boolean;
  project_name?: string;
  project_root?: string;
  message?: string;
}

export interface ProjectTrashResult {
  ok: boolean;
  project_name?: string;
  active_project?: string;
  message?: string;
}

export interface ProjectFolderOpenResult {
  ok: boolean;
  project_name?: string;
  project_root?: string;
  message?: string;
}
