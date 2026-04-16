import { useCallback, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import packageJson from "../package.json";
import {
  fetchProjects,
  fetchEditableFiles,
  fetchInputFile,
  fetchInputs,
  fetchLogs,
  fetchState,
  openProject,
  openProjectFolder,
  postAction,
  rollbackSnapshot,
  saveInputFile,
  saveInputs,
  trashProject,
} from "./api";
import type { BackendStatus, LogMode, WorkflowStateSnapshot } from "./types";

const API_BASE_URL = "http://127.0.0.1:18765";

type PageKey = "projects" | "inputs" | "outputs" | "workflow" | "about";
type OutputTab = "paper" | "pipeline";
type ModelProvider = "base_url" | "doubao" | "openrouter" | "anthropic";
type TutorialPopoverPosition = "top-left" | "top-right" | "bottom-left" | "bottom-right";

const APP_VERSION = String((packageJson as { version?: string }).version || "0.1.0");
const TUTORIAL_DISMISSED_KEY = "thesisloom:tutorial-dismissed";

interface TutorialStep {
  key: string;
  title: string;
  body: string;
  page: PageKey;
  position: TutorialPopoverPosition;
}

interface ImageDescriptionItem {
  detailed_description: string;
  title: string;
}

interface InputsFormState {
  topic: string;
  language: "English" | "Chinese";
  model: string;
  model_provider: ModelProvider;
  paper_search_limit: number;
  openalex_api_key: string;
  ark_api_key: string;
  base_url: string;
  model_api_key: string;
  image_descriptions: ImageDescriptionItem[];
}

type InputsFieldErrors = Partial<Record<keyof InputsFormState, string>>;

interface InputsValidationResult {
  fieldErrors: InputsFieldErrors;
  blockingIssues: string[];
  warnings: string[];
}

const BASE_URL_TEST_ENDPOINT = "https://acai-proxy-api.onrender.com/v1";
const BASE_URL_TEST_API_KEY = "sk-123";
const ANTHROPIC_DEFAULT_BASE_URL = "https://api.anthropic.com";

const PROVIDER_MODEL_OPTIONS: Record<ModelProvider, readonly string[]> = {
  base_url: ["claude-sonnet-4-5-20250929-thinking", "gemini-3.1-pro"],
  doubao: ["doubao-seed-2-0-pro-260215", "doubao-seed-2-0-mini-260215"],
  openrouter: ["claude-sonnet-4-5-20250929-thinking", "gemini-3.1-pro"],
  anthropic: ["claude-opus-4-6", "claude-opus-4-6-20260205"],
};

const DEFAULT_PROVIDER_MODEL: Record<ModelProvider, string> = {
  base_url: "gemini-3.1-pro",
  doubao: "doubao-seed-2-0-pro-260215",
  openrouter: "gemini-3.1-pro",
  anthropic: "claude-opus-4-6",
};

const DEFAULT_INPUTS_FORM: InputsFormState = {
  topic: "",
  language: "English",
  model: DEFAULT_PROVIDER_MODEL.base_url,
  model_provider: "base_url",
  paper_search_limit: 30,
  openalex_api_key: "",
  ark_api_key: "",
  base_url: BASE_URL_TEST_ENDPOINT,
  model_api_key: BASE_URL_TEST_API_KEY,
  image_descriptions: [],
};

const DOUBAO_DEFAULT_MODEL = DEFAULT_PROVIDER_MODEL.doubao;
const EMPTY_IMAGE_DESCRIPTION_ITEM: ImageDescriptionItem = {
  detailed_description: "",
  title: "",
};

const FLOW_STEPS = [
  {
    key: "preparation",
    title: "准备阶段",
    desc: "确认主题、模型参数与基础输入是否完整。",
  },
  {
    key: "literature_review",
    title: "文献综述阶段",
    desc: "完成检索、补充相关研究整理，并生成研究空白分析。",
  },
  {
    key: "architecture",
    title: "架构设计阶段",
    desc: "由 architect 生成并评审章节架构。",
  },
  {
    key: "drafting",
    title: "正文撰写阶段",
    desc: "逐章完成规划、章节开场与正文撰写，并实时更新进度。",
  },
  {
    key: "review_pending",
    title: "审稿准备",
    desc: "确认进入审稿前的人机协作参数。",
  },
  {
    key: "review_plan",
    title: "总审稿规划",
    desc: "生成本轮审稿结论与大章节改写计划。",
  },
  {
    key: "review_detail",
    title: "审稿细节设计",
    desc: "按章节下钻，产出待改写小节与重写指导。",
  },
  {
    key: "rewrite_execution",
    title: "改稿执行",
    desc: "按审稿意见逐节重写，并决定是否进入下一轮。",
  },
  {
    key: "done",
    title: "流程完成",
    desc: "终稿产出完成，可导出或切换项目。",
  },
] as const;

const TUTORIAL_STEPS: TutorialStep[] = [
  {
    key: "projects",
    title: "步骤 1：先创建或打开项目",
    body: "在“项目”页选择已有项目，或输入新项目名称创建。建议先确认项目目录后再进行后续输入与流程操作。",
    page: "projects",
    position: "top-left",
  },
  {
    key: "inputs",
    title: "步骤 2：填写输入与参数",
    body: "在“输入”页填写论文主题、模型参数，并补充 existing_material、write_requests 等输入文件。保存后再启动流程。",
    page: "inputs",
    position: "top-right",
  },
  {
    key: "workflow",
    title: "步骤 3：在流程页推进任务",
    body: "在“流程”页点击开始工作流，并按提示处理待人工动作。这里也可以使用暂停/继续控制长流程执行。",
    page: "workflow",
    position: "bottom-right",
  },
  {
    key: "outputs",
    title: "步骤 4：查看输出结果",
    body: "流程执行后，到“输出”页查看正文与过程产物。若需要回退，可在流程页使用关键节点与版本回退功能。",
    page: "outputs",
    position: "bottom-left",
  },
];

const LITERATURE_REVIEW_NODES = new Set([
  "node_search_query_builder",
  "node_search_paper",
  "node_research_gaps",
]);

const ARCHITECTURE_NODES = new Set([
  "node_architect",
  "node_architecture_review",
]);

const PLANNING_NODES = new Set([
  "node_image_planner",
  "node_planner",
  "node_chapter_header",
  "node_chapter_opening",
]);

const REVIEW_PLAN_NODES = new Set([
  "node_overall_review",
]);

const REVIEW_DETAIL_NODES = new Set([
  "node_major_review",
]);

const REWRITE_NODES = new Set([
  "node_rewrite",
]);

const PHASE_LABELS: Record<string, string> = {
  idle: "准备中",
  pre_research: "前置研究",
  drafting: "撰写中",
  review_pending: "待进入审稿",
  reviewing: "审稿中",
  done: "已完成",
};

const PAGE_LABELS: Record<PageKey, string> = {
  projects: "项目",
  inputs: "输入",
  workflow: "流程",
  outputs: "输出",
  about: "关于",
};

const ACTION_LABELS: Record<string, string> = {
  confirm_inputs_ready: "确认输入已准备",
  set_enable_auto_title: "是否自动生成标题",
  set_enable_search: "是否执行文献检索",
  confirm_related_works: "确认相关研究整理已补充",
  enter_reviewing: "确认进入审稿",
  set_architecture_force_continue: "架构人工放行",
  retry_after_llm_failure: "LLM 失败后继续",
  confirm_next_review_round: "是否进入下一轮审稿",
  pause_workflow: "暂停流程",
  resume_workflow: "继续流程",
};

const NODE_LABELS: Record<string, string> = {
  pre_start: "前置确认",
  pre_research: "前置准备",
  node_title_builder: "标题生成",
  node_search_query_builder: "检索词生成",
  node_search_paper: "文献检索",
  node_research_gaps: "研究空白生成",
  node_architect: "架构生成",
  node_architecture_review: "架构审查",
  node_image_planner: "图片规划",
  node_planner: "章节规划",
  node_chapter_header: "章节标题",
  node_chapter_opening: "章节总起",
  node_writer: "正文撰写",
  node_overall_review: "总审稿",
  node_major_review: "章节审稿",
  node_rewrite: "章节重写",
};

const EMPTY_BACKEND_STATUS: BackendStatus = {
  running: false,
  pid: null,
  message: "后端未启动",
  workspace_root: "",
  python_path: "python",
};

function resolveFlowKey(snapshot: WorkflowStateSnapshot | null): string {
  if (!snapshot) {
    return "preparation";
  }
  const phase = String(snapshot.workflow_phase || "idle").toLowerCase();
  const node = String(snapshot.current_node || "").trim();
  const nodeLower = node.toLowerCase();
  const pendingAction = String(snapshot.pending_action || "").trim();
  const queryCount = Number(snapshot.search_query_count || 0);
  const checkpointReason = String(snapshot.last_checkpoint_reason || "").toLowerCase();

  const architectureHint =
    pendingAction === "set_architecture_force_continue" ||
    ARCHITECTURE_NODES.has(node) ||
    nodeLower.includes("architect") ||
    checkpointReason.includes("architect") ||
    checkpointReason.includes("architecture");

  const planningHint =
    PLANNING_NODES.has(node) ||
    nodeLower === "major_loop" ||
    nodeLower.includes("planner") ||
    nodeLower.includes("chapter_header") ||
    nodeLower.includes("chapter_opening") ||
    checkpointReason.includes("planner") ||
    checkpointReason.includes("chapter_header") ||
    checkpointReason.includes("chapter_opening") ||
    checkpointReason.includes("enter_major_chapter");

  const reviewPlanHint =
    REVIEW_PLAN_NODES.has(node) ||
    nodeLower.includes("overall_review") ||
    checkpointReason.includes("overall_review");

  const reviewDetailHint =
    REVIEW_DETAIL_NODES.has(node) ||
    nodeLower.includes("major_review") ||
    checkpointReason.includes("major_review");

  const rewriteExecutionHint =
    REWRITE_NODES.has(node) ||
    nodeLower.includes("rewrite") ||
    checkpointReason.includes("rewrite") ||
    pendingAction === "confirm_next_review_round";

  if (architectureHint) {
    return "architecture";
  }
  if (planningHint) {
    return "drafting";
  }

  if (phase === "idle" || phase === "pre_research") {
    if (pendingAction === "confirm_related_works") {
      return "literature_review";
    }
    if (LITERATURE_REVIEW_NODES.has(node)) {
      return "literature_review";
    }
    if (queryCount > 0) {
      return "literature_review";
    }
    return "preparation";
  }

  if (phase === "drafting") {
    return "drafting";
  }
  if (phase === "review_pending") {
    return "review_pending";
  }
  if (phase === "reviewing") {
    if (reviewPlanHint) {
      return "review_plan";
    }
    if (reviewDetailHint) {
      return "review_detail";
    }
    if (rewriteExecutionHint) {
      return "rewrite_execution";
    }
    return "review_detail";
  }
  if (phase === "done") {
    return "done";
  }
  return "preparation";
}

function getFlowStatusLabel(status: "done" | "current" | "todo"): string {
  if (status === "done") {
    return "已完成";
  }
  if (status === "current") {
    return "进行中";
  }
  return "待开始";
}

function getReviewPriorityLabel(priority: string): string {
  const raw = String(priority || "").trim().toLowerCase();
  if (raw === "high") {
    return "高优先级";
  }
  if (raw === "low") {
    return "低优先级";
  }
  return "中优先级";
}

function getReviewRoundTag(reviewRound: number): string {
  const round = Math.max(0, Math.floor(Number(reviewRound) || 0));
  if (round <= 1) {
    return "";
  }

  const labels = ["第一", "第二", "第三", "第四", "第五", "第六", "第七", "第八", "第九", "第十"];
  const prefix = labels[round - 1] || `第${round}`;
  return `【${prefix}轮】`;
}

function isReviewFlowStep(stepKey: string): boolean {
  return stepKey === "review_pending" || stepKey === "review_plan" || stepKey === "review_detail" || stepKey === "rewrite_execution";
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function asRecordArray(value: unknown): Record<string, unknown>[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null);
}

function pickText(record: Record<string, unknown>, keys: string[], fallback = "-"): string {
  for (const key of keys) {
    const text = String(record[key] ?? "").trim();
    if (text) {
      return text;
    }
  }
  return fallback;
}

function issueListFromValue(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => String(item ?? "").trim())
    .filter((item) => Boolean(item));
}

function formatDurationSeconds(rawSeconds: number): string {
  const total = Math.max(0, Math.round(Number(rawSeconds) || 0));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  if (hours > 0) {
    return `${hours}h ${String(minutes).padStart(2, "0")}m`;
  }
  return `${String(minutes).padStart(2, "0")}m ${String(seconds).padStart(2, "0")}s`;
}

function isValidHttpUrl(raw: string): boolean {
  const text = String(raw || "").trim();
  if (!text) {
    return false;
  }
  try {
    const parsed = new URL(text);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function normalizeImageDescriptionsForForm(raw: unknown): ImageDescriptionItem[] {
  if (!Array.isArray(raw)) {
    return [];
  }

  const rows: ImageDescriptionItem[] = [];
  for (const item of raw) {
    if (!item || typeof item !== "object" || Array.isArray(item)) {
      continue;
    }

    const record = item as Record<string, unknown>;
    const detailedDescription = String(
      record.detailed_description ?? record.description ?? record["图片的超级详细的描述"] ?? "",
    ).trim();
    const title = String(record.title ?? record["图标题"] ?? "").trim();
    if (!detailedDescription && !title) {
      continue;
    }

    rows.push({
      detailed_description: detailedDescription,
      title,
    });
  }
  return rows;
}

function normalizeImageDescriptionsForPayload(rows: ImageDescriptionItem[]): ImageDescriptionItem[] {
  const result: ImageDescriptionItem[] = [];
  for (const item of rows) {
    const detailedDescription = String(item.detailed_description || "").trim();
    const title = String(item.title || "").trim();
    if (!detailedDescription) {
      continue;
    }
    result.push({
      detailed_description: detailedDescription,
      title,
    });
  }
  return result;
}

function normalizeModelForProvider(provider: ModelProvider, rawModel: unknown): string {
  const model = String(rawModel ?? "").trim();
  const options = PROVIDER_MODEL_OPTIONS[provider] || [];
  if (options.includes(model)) {
    return model;
  }
  return DEFAULT_PROVIDER_MODEL[provider];
}

function formatWorkflowLogRow(item: Record<string, unknown>, mode: LogMode): string {
  const t = String(item.time ?? "-");
  const lvl = String(item.level ?? "detail");
  const msg = String(item.message ?? "");
  const detailLine = String(item.detail_line ?? "").trim();

  if (mode === "detail" && detailLine) {
    return `[${t}] [${lvl}] ${detailLine}`;
  }

  if (mode !== "detail") {
    return `[${t}] [${lvl}] ${msg}`;
  }

  const contextKeys = [
    "phase",
    "node",
    "major_id",
    "sub_id",
    "status",
    "runtime_status",
    "pending_action",
    "llm_attempt",
    "llm_max_retries",
    "model",
    "interaction_mode",
  ];
  const contextParts: string[] = [];
  contextKeys.forEach((key) => {
    const value = item[key];
    if (value === undefined || value === null) {
      return;
    }
    const text = String(value).trim();
    if (!text) {
      return;
    }
    contextParts.push(`${key}=${text}`);
  });

  return contextParts.length > 0
    ? `[${t}] [${lvl}] ${msg} | ${contextParts.join(" | ")}`
    : `[${t}] [${lvl}] ${msg}`;
}

function validateInputsForm(form: InputsFormState): InputsValidationResult {
  const fieldErrors: InputsFieldErrors = {};
  const blockingIssues: string[] = [];
  const warnings: string[] = [];

  const topic = String(form.topic || "").trim();
  if (!topic) {
    warnings.push("论文标题可留空，流程会自动生成标题。");
  } else if (topic.length < 12) {
    warnings.push("论文标题较短，建议补充研究对象、方法和目标。");
  }

  const model = String(form.model || "").trim();
  if (!model) {
    const message = "模型名称不能为空。";
    fieldErrors.model = message;
    blockingIssues.push(message);
  } else {
    const allowedModels = PROVIDER_MODEL_OPTIONS[form.model_provider] || [];
    if (!allowedModels.includes(model)) {
      const message = `当前供应商仅支持以下模型: ${allowedModels.join(" / ")}`;
      fieldErrors.model = message;
      blockingIssues.push(message);
    }
  }

  const searchLimit = Number(form.paper_search_limit || 0);
  if (!Number.isFinite(searchLimit) || searchLimit < 1 || searchLimit > 300) {
    const message = "文献检索数量需在 1 到 300 之间。";
    fieldErrors.paper_search_limit = message;
    blockingIssues.push(message);
  }

  const baseUrl = String(form.base_url || "").trim();
  if (form.model_provider === "base_url") {
    if (!baseUrl) {
      warnings.push(`当前使用 Base URL 供应商，建议填写服务地址（默认可用：${BASE_URL_TEST_ENDPOINT}）。`);
    } else if (!isValidHttpUrl(baseUrl)) {
      const message = "模型服务地址格式无效，请使用 http(s):// 开头的完整 URL。";
      fieldErrors.base_url = message;
      blockingIssues.push(message);
    }
  }

  if (form.model_provider === "openrouter" && baseUrl && !isValidHttpUrl(baseUrl)) {
    warnings.push("检测到 base_url 格式异常，建议改为 OpenRouter 默认地址。");
  }

  if (form.model_provider === "anthropic" && baseUrl && !isValidHttpUrl(baseUrl)) {
    warnings.push("检测到 Anthropic base_url 格式异常，建议改为 https://api.anthropic.com。");
  }

  const imageDescriptions = Array.isArray(form.image_descriptions) ? form.image_descriptions : [];
  const invalidRows: number[] = [];
  imageDescriptions.forEach((item, index) => {
    const detailed = String(item?.detailed_description || "").trim();
    const title = String(item?.title || "").trim();
    if (!detailed && !title) {
      return;
    }
    if (!detailed) {
      invalidRows.push(index + 1);
    }
  });
  if (invalidRows.length > 0) {
    const message = `图片描述第 ${invalidRows.join("、")} 行缺少详细描述。`;
    fieldErrors.image_descriptions = message;
    blockingIssues.push(message);
  }

  return { fieldErrors, blockingIssues, warnings };
}

function toNumber(value: unknown, fallback: number, min: number, max: number): number {
  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    return fallback;
  }
  return Math.min(max, Math.max(min, Math.round(parsed)));
}

function displayInputFileName(path: string): string {
  const raw = String(path || "").trim();
  if (!raw) {
    return "";
  }
  return raw.replace(/^inputs[\\/]/i, "");
}

function describeInputFile(path: string): string {
  const name = displayInputFileName(path).toLowerCase();
  if (!name) {
    return "";
  }

  const map: Record<string, string> = {
    "inputs.json": "参数设置",
    "existing_material.md": "已有材料（原始资料）",
    "existing_sections.md": "已有章节（可复用正文）",
    "related_works.md": "相关研究整理",
    "research_gaps.md": "研究空白与创新点",
    "write_requests.md": "写作偏好与格式要求",
    "revision_requests.md": "审稿改写要求",
  };

  return map[name] || displayInputFileName(path);
}

function parseInputsForm(raw: string): { form: InputsFormState; extra: Record<string, unknown> } {
  let parsed: Record<string, unknown> = {};
  try {
    const value = JSON.parse(raw);
    if (value && typeof value === "object" && !Array.isArray(value)) {
      parsed = value as Record<string, unknown>;
    }
  } catch {
    parsed = {};
  }

  const knownKeys = new Set([
    "topic",
    "language",
    "model",
    "model_provider",
    "max_review_rounds",
    "paper_search_limit",
    "openalex_api_key",
    "ark_api_key",
    "base_url",
    "model_api_key",
    "image_descriptions",
    "auto_resume",
  ]);

  const extra: Record<string, unknown> = {};
  Object.entries(parsed).forEach(([key, value]) => {
    if (!knownKeys.has(key)) {
      extra[key] = value;
    }
  });

  const languageValue = String(parsed.language ?? DEFAULT_INPUTS_FORM.language).trim();
  const language: "English" | "Chinese" = languageValue === "Chinese" ? "Chinese" : "English";
  const providerValue = String(parsed.model_provider ?? DEFAULT_INPUTS_FORM.model_provider).trim().toLowerCase();
  const modelProvider: ModelProvider =
    providerValue === "doubao"
      ? "doubao"
      : providerValue === "openrouter"
        ? "openrouter"
        : providerValue === "anthropic"
          ? "anthropic"
          : "base_url";

  const rawBaseUrl = String(parsed.base_url ?? DEFAULT_INPUTS_FORM.base_url).trim();
  const normalizedBaseUrl =
    modelProvider === "anthropic"
      ? (rawBaseUrl || ANTHROPIC_DEFAULT_BASE_URL)
      : modelProvider === "base_url"
        ? (rawBaseUrl || BASE_URL_TEST_ENDPOINT)
        : rawBaseUrl;

  const rawModelApiKey = String(parsed.model_api_key ?? DEFAULT_INPUTS_FORM.model_api_key);
  const normalizedModelApiKey =
    modelProvider === "base_url"
      ? (String(rawModelApiKey).trim() || BASE_URL_TEST_API_KEY)
      : rawModelApiKey;

  const form: InputsFormState = {
    topic: String(parsed.topic ?? DEFAULT_INPUTS_FORM.topic),
    language,
    model: normalizeModelForProvider(modelProvider, parsed.model),
    model_provider: modelProvider,
    paper_search_limit: toNumber(parsed.paper_search_limit, DEFAULT_INPUTS_FORM.paper_search_limit, 1, 300),
    openalex_api_key: String(parsed.openalex_api_key ?? DEFAULT_INPUTS_FORM.openalex_api_key),
    ark_api_key: String(parsed.ark_api_key ?? DEFAULT_INPUTS_FORM.ark_api_key),
    base_url: normalizedBaseUrl,
    model_api_key: normalizedModelApiKey,
    image_descriptions: normalizeImageDescriptionsForForm(parsed.image_descriptions),
  };

  return { form, extra };
}

function composeInputsPayload(form: InputsFormState, extra: Record<string, unknown>): Record<string, unknown> {
  const imageDescriptions = normalizeImageDescriptionsForPayload(form.image_descriptions);
  const normalizedModel = normalizeModelForProvider(form.model_provider, form.model);
  const rawBaseUrl = String(form.base_url || "").trim();
  const normalizedBaseUrl =
    form.model_provider === "anthropic"
      ? (rawBaseUrl || ANTHROPIC_DEFAULT_BASE_URL)
      : form.model_provider === "base_url"
        ? (rawBaseUrl || BASE_URL_TEST_ENDPOINT)
        : rawBaseUrl;
  const normalizedModelApiKey =
    form.model_provider === "base_url"
      ? (String(form.model_api_key || "").trim() || BASE_URL_TEST_API_KEY)
      : form.model_api_key;

  return {
    ...extra,
    topic: form.topic,
    language: form.language,
    model: normalizedModel,
    model_provider: form.model_provider,
    paper_search_limit: form.paper_search_limit,
    openalex_api_key: form.openalex_api_key,
    ark_api_key: form.ark_api_key,
    base_url: normalizedBaseUrl,
    model_api_key: normalizedModelApiKey,
    image_descriptions: imageDescriptions,
  };
}

function App() {
  const [page, setPage] = useState<PageKey>("workflow");
  const [outputTab, setOutputTab] = useState<OutputTab>("paper");
  const [outputSearchQuery, setOutputSearchQuery] = useState<string>("");
  const [tutorialOpen, setTutorialOpen] = useState<boolean>(() => {
    if (typeof window === "undefined") {
      return true;
    }
    return window.localStorage.getItem(TUTORIAL_DISMISSED_KEY) !== "1";
  });
  const [tutorialStepIndex, setTutorialStepIndex] = useState<number>(0);
  const [paperExpandAll, setPaperExpandAll] = useState(false);
  const [paperExpandToken, setPaperExpandToken] = useState(0);
  const [pipelineExpandAll, setPipelineExpandAll] = useState(false);
  const [pipelineExpandToken, setPipelineExpandToken] = useState(0);

  const [backendStatus, setBackendStatus] = useState<BackendStatus>(EMPTY_BACKEND_STATUS);
  const [stateSnapshot, setStateSnapshot] = useState<WorkflowStateSnapshot | null>(null);

  const [inputsForm, setInputsForm] = useState<InputsFormState>(DEFAULT_INPUTS_FORM);
  const [inputsExtra, setInputsExtra] = useState<Record<string, unknown>>({});
  const [autoSaveHint, setAutoSaveHint] = useState<string>("等待加载参数");
  const suppressAutoSaveRef = useRef<boolean>(true);

  const [editableFiles, setEditableFiles] = useState<string[]>([]);
  const [selectedFilePath, setSelectedFilePath] = useState<string>("");
  const [selectedFileContent, setSelectedFileContent] = useState<string>("");
  const lastSavedInputFileRef = useRef<{ path: string; content: string }>({ path: "", content: "" });

  const [projects, setProjects] = useState<string[]>([]);
  const [selectedProjectName, setSelectedProjectName] = useState<string>("");
  const [newProjectName, setNewProjectName] = useState<string>("");

  const [logMode, setLogMode] = useState<LogMode>("key");
  const [logs, setLogs] = useState<string[]>([]);

  const [notice, setNotice] = useState<{
    kind: "info" | "ok" | "warn" | "error";
    text: string;
    visible: boolean;
    token: number;
  }>({
    kind: "info",
    text: "",
    visible: false,
    token: 0,
  });
  const lastPendingActionRef = useRef<string>("");

  const [skipApprovalEnabled, setSkipApprovalEnabled] = useState(false);
  const skipApprovalBusyRef = useRef(false);
  const lastSkipApprovalKeyRef = useRef("");
  const [runtimeControlBusy, setRuntimeControlBusy] = useState(false);
  const baseUrl = API_BASE_URL;

  const pushNotice = useCallback((kind: "info" | "ok" | "warn" | "error", text: string) => {
    setNotice({ kind, text, visible: true, token: Date.now() });
  }, []);

  const copyTextToClipboard = useCallback(async (content: string, successText: string) => {
    const text = String(content || "");
    if (!text.trim()) {
      pushNotice("warn", "当前内容为空，无法复制");
      return;
    }

    try {
      await navigator.clipboard.writeText(text);
      pushNotice("ok", successText);
    } catch {
      pushNotice("warn", "复制失败，请检查系统剪贴板权限");
    }
  }, [pushNotice]);

  const openExternalLink = useCallback(async (url: string) => {
    const target = String(url || "").trim();
    if (!isValidHttpUrl(target)) {
      pushNotice("warn", "链接地址无效，无法打开");
      return;
    }

    try {
      await invoke("open_external_url", { url: target });
    } catch (err) {
      pushNotice("error", `打开链接失败: ${String(err)}`);
    }
  }, [pushNotice]);

  const openTutorial = useCallback((startIndex = 0) => {
    const normalized = Math.max(0, Math.min(startIndex, TUTORIAL_STEPS.length - 1));
    setTutorialStepIndex(normalized);
    window.localStorage.removeItem(TUTORIAL_DISMISSED_KEY);
    setTutorialOpen(true);
  }, []);

  const closeTutorial = useCallback((skipped: boolean) => {
    window.localStorage.setItem(TUTORIAL_DISMISSED_KEY, "1");
    setTutorialOpen(false);
    if (skipped) {
      pushNotice("info", "已跳过教程，可在“关于”页重新打开。 ");
      return;
    }
    pushNotice("ok", "教程已完成，可开始正式使用。");
  }, [pushNotice]);

  const prevTutorialStep = useCallback(() => {
    setTutorialStepIndex((prev) => Math.max(0, prev - 1));
  }, []);

  const nextTutorialStep = useCallback(() => {
    setTutorialStepIndex((prev) => {
      if (prev >= TUTORIAL_STEPS.length - 1) {
        closeTutorial(false);
        return prev;
      }
      return prev + 1;
    });
  }, [closeTutorial]);

  const togglePaperExpandAll = useCallback(() => {
    setPaperExpandAll((prev) => !prev);
    setPaperExpandToken((prev) => prev + 1);
  }, []);

  const togglePipelineExpandAll = useCallback(() => {
    setPipelineExpandAll((prev) => !prev);
    setPipelineExpandToken((prev) => prev + 1);
  }, []);

  const refreshBackendStatus = useCallback(async () => {
    try {
      const data = await invoke<BackendStatus>("backend_status", {
        workspace_root: "",
      });
      setBackendStatus(data);
    } catch (err) {
      setBackendStatus({ ...EMPTY_BACKEND_STATUS, message: String(err) });
    }
  }, []);

  const refreshState = useCallback(async () => {
    try {
      const data = await fetchState(baseUrl);
      setStateSnapshot(data);
      if (!data.ok) {
        pushNotice("error", data.message || "状态读取失败");
      }
    } catch (err) {
      setStateSnapshot(null);
      pushNotice("warn", `状态接口不可达: ${String(err)}`);
    }
  }, [baseUrl, pushNotice]);

  const refreshInputs = useCallback(async () => {
    try {
      const data = await fetchInputs(baseUrl);
      if (!data.ok) {
        pushNotice("error", data.message || "inputs 读取失败");
        return;
      }

      const parsed = parseInputsForm(data.raw || "{}");
      suppressAutoSaveRef.current = true;
      setInputsForm(parsed.form);
      setInputsExtra(parsed.extra);
      setAutoSaveHint("参数已同步");
      window.setTimeout(() => {
        suppressAutoSaveRef.current = false;
      }, 30);
    } catch (err) {
      pushNotice("warn", `inputs 接口不可达: ${String(err)}`);
    }
  }, [baseUrl, pushNotice]);

  const refreshLogs = useCallback(async () => {
    try {
      const data = await fetchLogs(baseUrl, logMode);
      if (!data.ok) {
        setLogs(["日志读取失败"]);
        return;
      }
      const rows = (data.items || []).map((item) => formatWorkflowLogRow(item as Record<string, unknown>, logMode));
      setLogs(rows.length > 0 ? rows : ["暂无日志"]);
    } catch (err) {
      setLogs([`日志接口不可达: ${String(err)}`]);
    }
  }, [baseUrl, logMode]);

  const refreshProjects = useCallback(async () => {
    try {
      const payload = await fetchProjects(baseUrl);
      if (!payload.ok) {
        pushNotice("warn", payload.message || "项目列表读取失败");
        return;
      }
      const all = payload.items || [];
      setProjects(all);

      const current = String(payload.current || "").trim();
      if (current) {
        setSelectedProjectName(current);
      } else if (all.length > 0) {
        setSelectedProjectName(all[0]);
      }
    } catch (err) {
      pushNotice("warn", `读取项目列表失败: ${String(err)}`);
    }
  }, [baseUrl, pushNotice]);

  const loadEditableFiles = useCallback(async () => {
    try {
      const payload = await fetchEditableFiles(baseUrl);
      if (!payload.ok) {
        pushNotice("warn", "可编辑文件列表读取失败");
        return;
      }
      setEditableFiles(payload.items || []);
      if ((payload.items || []).length > 0) {
        const first = payload.items[0];
        setSelectedFilePath(first);
      }
    } catch (err) {
      pushNotice("warn", `读取可编辑文件失败: ${String(err)}`);
    }
  }, [baseUrl, pushNotice]);

  const openProjectByName = useCallback(
    async (projectNameRaw: string) => {
      const projectName = String(projectNameRaw || "").trim();
      if (!projectName) {
        pushNotice("warn", "请先选择要打开的项目");
        return false;
      }

      const result = await openProject(baseUrl, projectName);
      if (!result.ok) {
        pushNotice("error", result.message || "打开项目失败");
        return false;
      }

      setSelectedProjectName(result.project_name || projectName);
      pushNotice("ok", `已打开项目: ${result.project_name || projectName}`);
      await refreshProjects();
      await refreshInputs();
      await loadEditableFiles();
      await refreshState();
      await refreshLogs();
      return true;
    },
    [baseUrl, loadEditableFiles, pushNotice, refreshInputs, refreshLogs, refreshProjects, refreshState],
  );

  const loadSelectedFile = useCallback(
    async (path: string) => {
      if (!path) {
        return;
      }
      try {
        const payload = await fetchInputFile(baseUrl, path);
        if (!payload.ok) {
          pushNotice("error", payload.message || "读取文件失败");
          return;
        }
        const loadedContent = payload.content || "";
        setSelectedFilePath(path);
        setSelectedFileContent(loadedContent);
        lastSavedInputFileRef.current = { path, content: loadedContent };
      } catch (err) {
        pushNotice("error", `读取文件失败: ${String(err)}`);
      }
    },
    [baseUrl, pushNotice],
  );

  const saveSelectedFile = useCallback(async (silent = false) => {
    if (!selectedFilePath) {
      if (!silent) {
        pushNotice("warn", "未选择输入文件");
      }
      return;
    }

    if (silent) {
      const lastSaved = lastSavedInputFileRef.current;
      if (lastSaved.path === selectedFilePath && lastSaved.content === selectedFileContent) {
        return;
      }
    }

    try {
      const payload = await saveInputFile(baseUrl, selectedFilePath, selectedFileContent);
      if (!payload.ok) {
        pushNotice("error", payload.message || "保存文件失败");
        return;
      }
      lastSavedInputFileRef.current = { path: selectedFilePath, content: selectedFileContent };
      if (!silent) {
        pushNotice("ok", `已保存 ${selectedFilePath}`);
      }
    } catch (err) {
      pushNotice("error", `保存文件失败: ${String(err)}`);
    }
  }, [baseUrl, pushNotice, selectedFileContent, selectedFilePath]);

  const persistInputsForm = useCallback(async (silent: boolean): Promise<boolean> => {
    try {
      const body = JSON.stringify(composeInputsPayload(inputsForm, inputsExtra), null, 2);
      const payload = await saveInputs(baseUrl, body);
      if (!payload.ok) {
        setAutoSaveHint("自动保存失败");
        pushNotice("error", payload.message || "inputs 保存失败");
        return false;
      }

      const stamp = new Date().toLocaleTimeString();
      setAutoSaveHint(`已自动保存 ${stamp}`);
      if (!silent) {
        pushNotice("ok", "inputs 参数已保存");
      }
      await refreshState();
      return true;
    } catch (err) {
      setAutoSaveHint("自动保存失败");
      pushNotice("error", `inputs 保存失败: ${String(err)}`);
      return false;
    }
  }, [baseUrl, inputsExtra, inputsForm, pushNotice, refreshState]);

  const updateForm = useCallback(<K extends keyof InputsFormState>(key: K, value: InputsFormState[K]) => {
    setInputsForm((prev) => ({ ...prev, [key]: value }));
    setAutoSaveHint("待自动保存");
  }, []);

  const addImageDescriptionRow = useCallback(() => {
    setInputsForm((prev) => ({
      ...prev,
      image_descriptions: [...prev.image_descriptions, { ...EMPTY_IMAGE_DESCRIPTION_ITEM }],
    }));
    setAutoSaveHint("待自动保存");
  }, []);

  const updateImageDescriptionRow = useCallback((index: number, key: keyof ImageDescriptionItem, value: string) => {
    setInputsForm((prev) => ({
      ...prev,
      image_descriptions: prev.image_descriptions.map((row, rowIndex) => (
        rowIndex === index ? { ...row, [key]: value } : row
      )),
    }));
    setAutoSaveHint("待自动保存");
  }, []);

  const removeImageDescriptionRow = useCallback((index: number) => {
    setInputsForm((prev) => ({
      ...prev,
      image_descriptions: prev.image_descriptions.filter((_, rowIndex) => rowIndex !== index),
    }));
    setAutoSaveHint("待自动保存");
  }, []);

  const sendAction = useCallback(
    async (payload: Record<string, unknown>) => {
      const finishActionSubmission = async () => {
        // Optimistically hide pending action so the button disappears immediately after click.
        setStateSnapshot((prev) => {
          if (!prev) {
            return prev;
          }
          return {
            ...prev,
            pending_action: "",
            pending_action_message: "",
          };
        });

        pushNotice("ok", `动作已提交: ${String(payload.action || "unknown")}`);
        await refreshState();
        await refreshLogs();
      };

      try {
        const data = await postAction(baseUrl, payload);
        if (!data.ok) {
          pushNotice("error", data.message || "动作提交失败");
          return;
        }
        await finishActionSubmission();
      } catch (err) {
        const firstError = String(err);
        pushNotice("warn", "动作提交失败，正在尝试自动恢复后端后重试...");

        try {
          const status = await invoke<BackendStatus>("backend_status", {
            workspace_root: "",
          });

          if (!status.running) {
            const started = await invoke<BackendStatus>("start_backend", {
              host: "127.0.0.1",
              port: 18765,
              python_path: "",
              workspace_root: "",
            });
            setBackendStatus(started);
          } else {
            setBackendStatus(status);
          }

          const retryResult = await postAction(baseUrl, payload);
          if (!retryResult.ok) {
            pushNotice("error", retryResult.message || "动作重试失败");
            return;
          }

          await finishActionSubmission();
        } catch (retryErr) {
          pushNotice("error", `动作提交失败: ${firstError}；重试后仍失败: ${String(retryErr)}`);
        }
      }
    },
    [baseUrl, pushNotice, refreshLogs, refreshState],
  );

  const handleRuntimeControlClick = useCallback(async (actionName: "pause_workflow" | "resume_workflow") => {
    setRuntimeControlBusy(true);
    try {
      await sendAction({ action: actionName });
    } finally {
      setRuntimeControlBusy(false);
    }
  }, [sendAction]);

  const rollbackToVersion = useCallback(
    async (statePath: string, label: string) => {
      const normalizedPath = String(statePath || "").trim();
      if (!normalizedPath) {
        pushNotice("warn", "该快照缺少状态文件，无法回退");
        return;
      }

      const confirmText = `确认回退到版本「${label || "未命名快照"}」吗？回退会覆盖当前 checkpoint 与正文输出。`;
      if (!window.confirm(confirmText)) {
        return;
      }

      try {
        const result = await rollbackSnapshot(baseUrl, normalizedPath);
        if (!result.ok) {
          pushNotice("error", result.message || "版本回退失败");
          return;
        }

        pushNotice("ok", result.message || "版本回退成功");
        await refreshState();
        await refreshLogs();
      } catch (err) {
        pushNotice("error", `版本回退失败: ${String(err)}`);
      }
    },
    [baseUrl, pushNotice, refreshLogs, refreshState],
  );

  const saveInputsAndStart = useCallback(async () => {
    const startValidation = validateInputsForm(inputsForm);
    if (startValidation.blockingIssues.length > 0) {
      pushNotice("warn", `请先修复输入参数问题：${startValidation.blockingIssues[0]}`);
      setPage("inputs");
      return;
    }

    const ok = await persistInputsForm(false);
    if (!ok) {
      return;
    }
    await sendAction({ action: "confirm_inputs_ready" });
  }, [inputsForm, persistInputsForm, pushNotice, sendAction]);

  const ensureBackendStarted = useCallback(async (silent = false) => {
    try {
      const status = await invoke<BackendStatus>("backend_status", {
        workspace_root: "",
      });
      setBackendStatus(status);

      if (status.running) {
        if (!silent) {
          pushNotice("ok", "后端已自动就绪");
        }
        return status;
      }

      const result = await invoke<BackendStatus>("start_backend", {
        host: "127.0.0.1",
        port: 18765,
        python_path: "",
        workspace_root: "",
      });
      setBackendStatus(result);
      pushNotice("ok", result.message || "后端已自动启动");
      await refreshProjects();
      await refreshInputs();
      await loadEditableFiles();
      await refreshState();
      await refreshLogs();
      return result;
    } catch (err) {
      pushNotice("error", `后端启动失败: ${String(err)}`);
      return null;
    }
  }, [loadEditableFiles, pushNotice, refreshInputs, refreshLogs, refreshProjects, refreshState]);

  const openSelectedProjectFolder = useCallback(async () => {
    const projectName = selectedProjectName.trim();
    if (!projectName) {
      pushNotice("warn", "请先选择要打开目录的项目");
      return;
    }

    try {
      const result = await openProjectFolder(baseUrl, projectName);
      if (!result.ok) {
        pushNotice("error", result.message || "打开项目文件夹失败");
        return;
      }

      pushNotice("ok", result.message || `已打开项目文件夹: ${result.project_name || projectName}`);
    } catch (err) {
      pushNotice("error", `打开项目文件夹失败: ${String(err)}`);
    }
  }, [baseUrl, pushNotice, selectedProjectName]);

  const createAndOpenProject = useCallback(async () => {
    const projectName = newProjectName.trim();
    if (!projectName) {
      pushNotice("warn", "请输入新项目名称");
      return;
    }

    try {
      const opened = await openProjectByName(projectName);
      if (!opened) {
        return;
      }

      setNewProjectName("");
    } catch (err) {
      pushNotice("error", `新建项目失败: ${String(err)}`);
    }
  }, [newProjectName, openProjectByName, pushNotice]);

  const moveProjectToTrash = useCallback(async () => {
    const projectName = selectedProjectName.trim();
    if (!projectName) {
      pushNotice("warn", "请先选择要移至回收站的项目");
      return;
    }
    if (projectName === "default") {
      pushNotice("warn", "默认项目不可移至回收站");
      return;
    }

    const confirmText = `确定将项目 ${projectName} 移至回收站吗？`;
    if (!window.confirm(confirmText)) {
      return;
    }

    try {
      const result = await trashProject(baseUrl, projectName);
      if (!result.ok) {
        pushNotice("error", result.message || "移至回收站失败");
        return;
      }

      pushNotice("ok", `已移至回收站: ${projectName}`);
      await refreshProjects();
      await refreshInputs();
      await loadEditableFiles();
      await refreshState();
      await refreshLogs();
    } catch (err) {
      pushNotice("error", `移至回收站失败: ${String(err)}`);
    }
  }, [
    baseUrl,
    loadEditableFiles,
    pushNotice,
    refreshInputs,
    refreshLogs,
    refreshProjects,
    refreshState,
    selectedProjectName,
  ]);

  useEffect(() => {
    if (!notice.visible) {
      return;
    }

    const timer = window.setTimeout(() => {
      setNotice((prev) => ({ ...prev, visible: false }));
    }, 5000);

    return () => window.clearTimeout(timer);
  }, [notice.token, notice.visible]);

  useEffect(() => {
    if (suppressAutoSaveRef.current) {
      return;
    }

    const timer = window.setTimeout(async () => {
      setAutoSaveHint("自动保存中...");
      await persistInputsForm(true);
    }, 700);

    return () => window.clearTimeout(timer);
  }, [inputsForm, persistInputsForm]);

  useEffect(() => {
    let cancelled = false;

    const bootstrap = async () => {
      await ensureBackendStarted(true);
      if (cancelled) {
        return;
      }
      await refreshBackendStatus();
      await refreshProjects();
      await refreshInputs();
      await loadEditableFiles();
      await refreshState();
      await refreshLogs();
    };

    void bootstrap();

    const id = window.setInterval(() => {
      void refreshBackendStatus();
      void refreshState();
      void refreshLogs();
    }, 1000);

    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [ensureBackendStarted, loadEditableFiles, refreshBackendStatus, refreshInputs, refreshLogs, refreshProjects, refreshState]);

  useEffect(() => {
    if (backendStatus.running) {
      return;
    }
    const timer = window.setTimeout(() => {
      void ensureBackendStarted(true);
    }, 1400);
    return () => window.clearTimeout(timer);
  }, [backendStatus.running, ensureBackendStarted]);

  useEffect(() => {
    refreshLogs();
  }, [logMode, refreshLogs]);

  useEffect(() => {
    if (selectedFilePath) {
      loadSelectedFile(selectedFilePath);
    }
  }, [loadSelectedFile, selectedFilePath]);

  useEffect(() => {
    if (!tutorialOpen) {
      return;
    }
    const step = TUTORIAL_STEPS[tutorialStepIndex];
    if (!step) {
      return;
    }
    if (page !== step.page) {
      setPage(step.page);
    }
  }, [page, tutorialOpen, tutorialStepIndex]);

  useEffect(() => {
    if (!tutorialOpen) {
      return;
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeTutorial(true);
        return;
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        prevTutorialStep();
        return;
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        nextTutorialStep();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [closeTutorial, nextTutorialStep, prevTutorialStep, tutorialOpen]);

  const phase = stateSnapshot?.workflow_phase || "idle";
  const pendingAction = stateSnapshot?.pending_action || "";
  const runtimeStatus = stateSnapshot?.runtime_status || "unknown";
  const runtimeStatusLower = String(runtimeStatus || "").toLowerCase();
  const hasPendingAction = Boolean(String(pendingAction || "").trim());
  const canPauseWorkflow = runtimeStatusLower === "running" && !hasPendingAction;
  const canResumeWorkflow = runtimeStatusLower === "paused";
  const canToggleRuntimeControl = canPauseWorkflow || canResumeWorkflow;
  const runtimeControlAction: "pause_workflow" | "resume_workflow" = canResumeWorkflow ? "resume_workflow" : "pause_workflow";
  const runtimeControlText = canResumeWorkflow ? "继续流程" : "暂停流程";
  const runtimeControlHint = canResumeWorkflow
    ? "当前流程已暂停，点击“继续流程”恢复。"
    : canPauseWorkflow
      ? "运行中，可点击暂停。"
      : hasPendingAction
        ? "当前有待处理审批动作，暂停不可用。"
        : "当前不在可暂停/继续状态。";
  const runtimeIsRunning = runtimeStatusLower === "running";
  const currentNode = stateSnapshot?.current_node || "";
  const currentSubId = stateSnapshot?.current_sub_chapter_id || "";
  const flowKey = resolveFlowKey(stateSnapshot);
  const flowIndex = Math.max(0, FLOW_STEPS.findIndex((x) => x.key === flowKey));
  const reviewRound = Number(stateSnapshot?.review_round ?? 0);
  const reviewRoundTag = getReviewRoundTag(reviewRound);
  const topicLine = stateSnapshot?.topic || stateSnapshot?.inputs_topic || "(empty topic)";
  const paperOutputs = stateSnapshot?.paper_outputs || [];
  const searchQueries = stateSnapshot?.search_queries || [];
  const architectOutline = stateSnapshot?.architect_outline || [];
  const plannerOutputs = stateSnapshot?.planner_outputs || [];
  const overallPlans = stateSnapshot?.overall_review_plans || [];
  const majorReviewItems = stateSnapshot?.major_review_items || [];
  const versionSnapshots = stateSnapshot?.version_snapshots || [];
  const keyMilestones = stateSnapshot?.key_milestones || [];
  const rewriteDoneSubIds = Array.isArray(stateSnapshot?.rewrite_done_sub_ids)
    ? stateSnapshot?.rewrite_done_sub_ids || []
    : [];
  const rewriteDoneSet = new Set(
    rewriteDoneSubIds
      .map((x) => String(x || "").trim())
      .filter((x) => Boolean(x)),
  );
  const nextSteps = stateSnapshot?.next_steps_plan || [];
  const nextStepsUpdatedAt = stateSnapshot?.next_steps_updated_at || "";
  const flowMajorBaseLabel = FLOW_STEPS.find((x) => x.key === flowKey)?.title || "";
  const flowMajorLabel = isReviewFlowStep(flowKey) && reviewRoundTag ? `${flowMajorBaseLabel}${reviewRoundTag}` : flowMajorBaseLabel;
  const phaseMajor = flowMajorLabel || PHASE_LABELS[phase] || phase;
  const isDoubaoProvider = inputsForm.model_provider === "doubao";
  const isOpenRouterProvider = inputsForm.model_provider === "openrouter";
  const isAnthropicProvider = inputsForm.model_provider === "anthropic";
  const providerModelOptions = PROVIDER_MODEL_OPTIONS[inputsForm.model_provider] || [];
  const providerSelectedModel = normalizeModelForProvider(inputsForm.model_provider, inputsForm.model);
  const activeApiKeyValue = isDoubaoProvider ? inputsForm.ark_api_key : inputsForm.model_api_key;
  const activeApiKeyTitle = isDoubaoProvider ? "ark_api_key" : "model_api_key";
  const activeApiKeyLabel = isDoubaoProvider
    ? "豆包 Ark API 密钥（可选）"
    : isAnthropicProvider
      ? "Anthropic API 密钥（可选）"
      : isOpenRouterProvider
        ? "OpenRouter API 密钥（可选）"
        : "模型服务 API 密钥（默认 sk-123，可替换）";
  const activeApiKeyPlaceholder = isDoubaoProvider
    ? "请输入豆包 Ark API Key"
    : isAnthropicProvider
      ? "请输入 Anthropic API Key"
      : isOpenRouterProvider
        ? "请输入 OpenRouter API Key"
        : "默认 sk-123（可替换）";
  const activeApiKeyLink = isDoubaoProvider
    ? "https://console.volcengine.com/ark/region:ark+cn-beijing/openManagement"
    : isAnthropicProvider
      ? "https://console.anthropic.com/settings/keys"
      : isOpenRouterProvider
        ? "https://openrouter.ai/workspaces/default/keys"
        : "";
  const activeApiKeyHelp = isDoubaoProvider
    ? "当前仅需填写豆包 Ark API 密钥；切到其他供应商时再填写对应密钥。"
    : isAnthropicProvider
      ? "当前固定支持 Claude Opus 4.6 两个模型版本；可填写 Anthropic API 密钥后直接运行。"
      : isOpenRouterProvider
        ? "当前仅需填写 OpenRouter API 密钥；豆包 Ark API 密钥可留空。"
        : `默认测试配置：Base URL=${BASE_URL_TEST_ENDPOINT}，API Key=${BASE_URL_TEST_API_KEY}；可按需覆盖。`;

  const draftingProgressItems = nextSteps
    .filter((item) => String(item.sub_chapter_id || "").trim())
    .sort((a, b) => Number(a.order ?? 9999) - Number(b.order ?? 9999))
    .map((item, idx) => {
      const subId = String(item.sub_chapter_id || "").trim();
      const title = String(item.sub_title || item.major_title || "(untitled)").trim();
      const order = Number(item.order ?? idx + 1);
      const done = String(item.status || "").trim() === "done";
      const current = !done && Boolean(currentSubId) && subId === currentSubId;
      return { subId, title, order, done, current };
    });
  const draftingDoneCount = draftingProgressItems.filter((item) => item.done).length;
  const draftingTotalCount = draftingProgressItems.length;
  const draftingProgressPercent =
    draftingTotalCount > 0 ? Math.round((draftingDoneCount / draftingTotalCount) * 100) : 0;
  const workflowMetrics = asRecord(stateSnapshot?.workflow_metrics);
  const workflowMetricSteps = asRecord(workflowMetrics?.steps);
  const draftingStepKeys = ["node_planner", "node_chapter_header", "node_chapter_opening", "node_writer"];
  const draftingElapsedSeconds = draftingStepKeys.reduce((sum, stepKey) => {
    const row = asRecord(workflowMetricSteps?.[stepKey]);
    return sum + Number(row?.total_seconds || 0);
  }, 0);
  const draftingRemainingCount = Math.max(0, draftingTotalCount - draftingDoneCount);
  const draftingAvgSecondsPerSection = draftingDoneCount > 0 ? draftingElapsedSeconds / draftingDoneCount : 0;
  const draftingEtaSeconds =
    draftingRemainingCount > 0 && draftingAvgSecondsPerSection > 0
      ? draftingAvgSecondsPerSection * draftingRemainingCount
      : 0;
  const draftingElapsedLabel = formatDurationSeconds(draftingElapsedSeconds);
  const draftingEtaLabel =
    draftingRemainingCount <= 0
      ? "00m 00s"
      : draftingEtaSeconds > 0
        ? formatDurationSeconds(draftingEtaSeconds)
        : "样本不足";

  const rewriteProgressItems = majorReviewItems
    .map((item, idx) => {
      const record = item as Record<string, unknown>;
      const subId = String(record.sub_chapter_id || "").trim();
      if (!subId) {
        return null;
      }
      const title = String(record.title || record.sub_title || "").trim();
      const itemType = String(record.item_type || "").trim();
      const priority = String(record.priority || "medium").trim();
      const issues = record.issues;
      const issueCount = Array.isArray(issues) ? issues.length : 0;
      const done = rewriteDoneSet.has(subId);
      const current = !done && currentNode === "node_rewrite" && Boolean(currentSubId) && subId === currentSubId;
      return {
        idx,
        subId,
        title,
        itemType,
        priority,
        issueCount,
        done,
        current,
      };
    })
    .filter((item): item is {
      idx: number;
      subId: string;
      title: string;
      itemType: string;
      priority: string;
      issueCount: number;
      done: boolean;
      current: boolean;
    } => item !== null)
    .sort((a, b) => a.subId.localeCompare(b.subId, undefined, { numeric: true, sensitivity: "base" }));
  const rewriteDoneCount = rewriteProgressItems.filter((item) => item.done).length;

  const tokenUsage = stateSnapshot?.token_usage || {};
  const inputTokens = Number(tokenUsage.total_input_tokens || 0);
  const outputTokens = Number(tokenUsage.total_output_tokens || 0);
  const currentYear = new Date().getFullYear();
  const inputValidation = validateInputsForm(inputsForm);
  const hasBlockingInputIssues = inputValidation.blockingIssues.length > 0;
  const firstBlockingInputIssue = inputValidation.blockingIssues[0] || "";
  const outputSearchKeyword = outputSearchQuery.trim().toLowerCase();
  const filteredPaperOutputs = paperOutputs.filter((row) => {
    if (!outputSearchKeyword) {
      return true;
    }
    const haystack = [
      String(row.major_title || ""),
      String(row.title || ""),
      String(row.sub_chapter_id || ""),
      String(row.content || ""),
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(outputSearchKeyword);
  });
  const pipelineArtifactTotal =
    searchQueries.length + architectOutline.length + plannerOutputs.length + overallPlans.length + majorReviewItems.length;
  const pendingActionLabel = ACTION_LABELS[pendingAction] || pendingAction || "无";
  const completedSectionCount = Number(stateSnapshot?.completed_section_count ?? 0);
  const draftingTotalDisplay = draftingTotalCount > 0 ? draftingTotalCount : "-";
  const tutorialStep = TUTORIAL_STEPS[Math.max(0, Math.min(tutorialStepIndex, TUTORIAL_STEPS.length - 1))];
  const isLastTutorialStep = tutorialStepIndex >= TUTORIAL_STEPS.length - 1;
  const tutorialHighlights = String(tutorialStep?.body || "")
    .split(/[。！？]/)
    .map((item) => item.trim())
    .filter((item) => Boolean(item));
  const inputChecklist = [
    {
      key: "topic",
      label: "论文标题",
      ready: true,
      hint: String(inputsForm.topic || "").trim()
        ? "已填写，将优先使用当前标题"
        : "可留空，系统会自动生成并补全标题",
    },
    {
      key: "model",
      label: "模型名称",
      ready: !inputValidation.fieldErrors.model,
      hint: "需与供应商和密钥匹配",
    },
    {
      key: "paper_search_limit",
      label: "检索数量",
      ready: Number(inputsForm.paper_search_limit) >= 1 && Number(inputsForm.paper_search_limit) <= 300,
      hint: "按需填写即可，系统支持较大的检索数量",
    },
    {
      key: "image_descriptions",
      label: "图片描述列表",
      ready: !inputValidation.fieldErrors.image_descriptions,
      hint: inputsForm.image_descriptions.length > 0
        ? `已录入 ${inputsForm.image_descriptions.length} 条图片描述`
        : "可选；如需插图规划，可逐行新增描述",
    },
    ...((inputsForm.model_provider === "base_url" || inputsForm.model_provider === "openrouter" || inputsForm.model_provider === "anthropic")
      ? [
          {
            key: "base_url",
            label: "服务地址格式",
            ready: !String(inputsForm.base_url || "").trim() || isValidHttpUrl(inputsForm.base_url),
            hint:
              inputsForm.model_provider === "anthropic"
                ? "Anthropic 格式支持自定义网关 URL"
                : inputsForm.model_provider === "openrouter"
                  ? "OpenRouter 支持自定义网关 URL"
                  : `默认测试地址：${BASE_URL_TEST_ENDPOINT}`,
          },
        ]
      : []),
  ];
  const readyChecklistCount = inputChecklist.filter((item) => item.ready).length;

  let phaseMinor = "等待流程节点";
  if (pendingAction) {
    phaseMinor = `待处理：${ACTION_LABELS[pendingAction] || pendingAction}`;
  } else if (currentNode) {
    phaseMinor = NODE_LABELS[currentNode] || currentNode;
  }
  if (currentSubId) {
    phaseMinor = `${phaseMinor} / ${currentSubId}`;
  }
  const autoSaveStatusClass = autoSaveHint.includes("失败")
    ? "is-error"
    : autoSaveHint.includes("保存中")
      ? "is-saving"
      : "is-ok";

  const resolveStepStatus = (idx: number): "done" | "current" | "todo" => {
    if (flowKey === "done" || idx < flowIndex) {
      return "done";
    }
    if (idx === flowIndex) {
      return "current";
    }
    return "todo";
  };

  useEffect(() => {
    const action = String(stateSnapshot?.pending_action || "").trim();
    if (!action) {
      lastPendingActionRef.current = "";
      return;
    }

    if (action === lastPendingActionRef.current) {
      return;
    }

    lastPendingActionRef.current = action;
    const label = ACTION_LABELS[action] || action;
    const msg = String(stateSnapshot?.pending_action_message || "").trim();
    const toastText = msg ? `需要人工操作：${label}。${msg}` : `需要人工操作：${label}`;
    pushNotice("warn", toastText);
  }, [pushNotice, stateSnapshot?.pending_action, stateSnapshot?.pending_action_message]);

  useEffect(() => {
    if (!skipApprovalEnabled) {
      skipApprovalBusyRef.current = false;
      lastSkipApprovalKeyRef.current = "";
      return;
    }

    const action = String(pendingAction || "").trim();
    if (!action) {
      skipApprovalBusyRef.current = false;
      return;
    }

    const actionKey = `${action}|${stateSnapshot?.runtime_time || ""}|${stateSnapshot?.checkpoint_mtime || ""}`;
    if (skipApprovalBusyRef.current || lastSkipApprovalKeyRef.current === actionKey) {
      return;
    }

    lastSkipApprovalKeyRef.current = actionKey;

    const runSkipApproval = async () => {
      skipApprovalBusyRef.current = true;
      try {
        if (action === "confirm_inputs_ready") {
          const ok = await persistInputsForm(true);
          if (!ok) {
            pushNotice("error", "跳过审批失败：inputs 保存失败");
            return;
          }
          await sendAction({ action: "confirm_inputs_ready" });
          return;
        }

        if (action === "set_enable_auto_title") {
          await sendAction({ action: "set_enable_auto_title", value: true });
          return;
        }
        if (action === "set_enable_search") {
          await sendAction({ action: "set_enable_search", value: true });
          return;
        }
        if (action === "confirm_related_works") {
          await sendAction({ action: "confirm_related_works" });
          return;
        }
        if (action === "enter_reviewing") {
          await sendAction({
            action: "enter_reviewing",
            load_requirements: true,
            requirements_path: "inputs/write_requests.md",
            manual_revision_path: "inputs/revision_requests.md",
          });
          return;
        }
        if (action === "set_architecture_force_continue") {
          await sendAction({ action: "set_architecture_force_continue", value: true });
          return;
        }
        if (action === "retry_after_llm_failure") {
          await sendAction({ action: "retry_after_llm_failure" });
          return;
        }
        if (action === "confirm_next_review_round") {
          await sendAction({ action: "confirm_next_review_round", continue: true });
        }
      } finally {
        skipApprovalBusyRef.current = false;
      }
    };

    pushNotice("info", `跳过审批：${ACTION_LABELS[action] || action}`);
    void runSkipApproval();
  }, [
    skipApprovalEnabled,
    pendingAction,
    persistInputsForm,
    pushNotice,
    sendAction,
    stateSnapshot?.checkpoint_mtime,
    stateSnapshot?.runtime_time,
  ]);

  const actionControl = (
    <div className="action-zone">
      <div className={pendingAction ? "workflow-alert pending" : "workflow-alert calm"}>
        <strong>{pendingAction ? "需要优先处理人工动作" : "当前流程可继续推进"}</strong>
        <span>
          {pendingAction
            ? `${pendingActionLabel}：${stateSnapshot?.pending_action_message || "请先完成该动作后继续。"}`
            : "当前无阻塞动作，可结合流程视图继续推进。"}
        </span>
      </div>

      <div className="action-block">
        <p>全局运行控制已移至页面顶部，可在任意页面点击“暂停/继续流程”和“跳过审批”。</p>
        <div className="line"><span>当前全局模式:</span> {skipApprovalEnabled ? "跳过审批已开启" : "跳过审批未开启"}</div>
      </div>

      {!pendingAction && flowKey === "preparation" && (
        <div className="action-block">
          <p>当前处于准备阶段，可手动开始工作流。</p>
          <button className="btn major" disabled={hasBlockingInputIssues} onClick={saveInputsAndStart}>开始工作流</button>
          {hasBlockingInputIssues && <small className="field-error">开始前请先修复输入参数：{firstBlockingInputIssue}</small>}
        </div>
      )}

      {!pendingAction && flowKey !== "preparation" && (
        <div className="action-block">
          <p>当前无待处理动作。</p>
        </div>
      )}

      {pendingAction === "confirm_inputs_ready" && (
        <div className="action-block">
          <p>请先保存 inputs.json，再点击保存并开始。</p>
          <button className="btn major" disabled={hasBlockingInputIssues} onClick={saveInputsAndStart}>保存并开始</button>
          {hasBlockingInputIssues && <small className="field-error">请先在“输入”页修复参数问题。</small>}
        </div>
      )}

      {pendingAction === "set_enable_auto_title" && (
        <div className="action-block">
          <p>是否自动生成标题？</p>
          <div className="action-buttons">
            <button className="btn major" onClick={() => sendAction({ action: "set_enable_auto_title", value: true })}>启用</button>
            <button className="btn" onClick={() => sendAction({ action: "set_enable_auto_title", value: false })}>关闭</button>
          </div>
        </div>
      )}

      {pendingAction === "set_enable_search" && (
        <div className="action-block">
          <p>是否执行文献检索？</p>
          <div className="action-buttons">
            <button className="btn major" onClick={() => sendAction({ action: "set_enable_search", value: true })}>执行检索</button>
            <button className="btn" onClick={() => sendAction({ action: "set_enable_search", value: false })}>跳过</button>
          </div>
        </div>
      )}

      {pendingAction === "confirm_related_works" && (
        <div className="action-block">
          <p>检索已完成。请先前往“输入”页面补充“相关研究整理”，再回来继续流程。</p>
          <div className="action-buttons">
            <button
              className="btn"
              onClick={() => {
                setPage("inputs");
                void loadSelectedFile(stateSnapshot?.related_works_path || "inputs/related_works.md");
              }}
            >
              去输入页面填写
            </button>
            <button className="btn major" onClick={() => sendAction({ action: "confirm_related_works" })}>已补充，继续</button>
          </div>
        </div>
      )}

      {pendingAction === "enter_reviewing" && (
        <div className="action-block">
          <p>确认进入审稿阶段。</p>
          <p className="section-help">默认会加载写作要求文件。若需补充审稿改写，请先点击“输入自定义要求”。</p>
          <div className="action-buttons">
            <button
              className="btn"
              onClick={() => {
                setPage("inputs");
                void loadSelectedFile("inputs/revision_requests.md");
              }}
            >
              输入自定义要求
            </button>
            <button
              className="btn major"
              onClick={() =>
                sendAction({
                  action: "enter_reviewing",
                  load_requirements: true,
                  requirements_path: "inputs/write_requests.md",
                  manual_revision_path: "inputs/revision_requests.md",
                })
              }
            >
              确认进入审稿
            </button>
          </div>
        </div>
      )}

      {pendingAction === "set_architecture_force_continue" && (
        <div className="action-block">
          <p>架构审查仅有中低优问题，是否人工放行？</p>
          <div className="action-buttons">
            <button className="btn major" onClick={() => sendAction({ action: "set_architecture_force_continue", value: true })}>放行</button>
            <button className="btn" onClick={() => sendAction({ action: "set_architecture_force_continue", value: false })}>继续修订</button>
          </div>
        </div>
      )}

      {pendingAction === "retry_after_llm_failure" && (
        <div className="action-block">
          <p>检测到 LLM 连续失败，可继续重试。</p>
          <button className="btn major" onClick={() => sendAction({ action: "retry_after_llm_failure" })}>继续重试</button>
        </div>
      )}

      {pendingAction === "confirm_next_review_round" && (
        <div className="action-block">
          <p>本轮审稿结束，是否继续下一轮？</p>
          <div className="action-buttons">
            <button className="btn major" onClick={() => sendAction({ action: "confirm_next_review_round", continue: true })}>继续下一轮</button>
            <button className="btn" onClick={() => sendAction({ action: "confirm_next_review_round", continue: false })}>停止并保留当前结果</button>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <div className="app-shell modern-shell">
      <div className="ambient ambient-a" />
      <div className="ambient ambient-b" />

      {notice.visible && (
        <div className={`toast ${notice.kind}`} role="status" aria-live="polite">
          {notice.text}
        </div>
      )}

      {tutorialOpen && tutorialStep && (
        <div className="tutorial-overlay" role="dialog" aria-modal="true" aria-label="使用教程" onClick={() => closeTutorial(true)}>
          <div className={`tutorial-popover ${tutorialStep.position}`} onClick={(event) => event.stopPropagation()}>
            <div className="tutorial-head">
              <div className="tutorial-step-meta">
                教程 {tutorialStepIndex + 1}/{TUTORIAL_STEPS.length}
              </div>
              <button className="tutorial-close-btn" onClick={() => closeTutorial(true)} aria-label="关闭教程">×</button>
            </div>
            <h3>{tutorialStep.title}</h3>
            <p>{tutorialStep.body}</p>
            <div className="tutorial-progress-track" aria-hidden="true">
              <span className={`tutorial-progress-fill step-${tutorialStepIndex + 1}`} />
            </div>
            {tutorialHighlights.length > 0 && (
              <div className="tutorial-highlights">
                {tutorialHighlights.map((item, idx) => (
                  <div key={`${tutorialStep.key}-tip-${idx}`} className="tutorial-highlight-item">{item}</div>
                ))}
              </div>
            )}
            <div className="line"><span>当前引导页:</span> {PAGE_LABELS[tutorialStep.page]}</div>
            <div className="tutorial-shortcuts">快捷键：← 上一步，→ 下一步，Esc 跳过</div>
            <div className="action-buttons">
              <button className="btn" disabled={tutorialStepIndex === 0} onClick={prevTutorialStep}>上一步</button>
              <button className="btn major" onClick={nextTutorialStep}>{isLastTutorialStep ? "完成" : "下一步"}</button>
              <button className="btn" onClick={() => closeTutorial(true)}>本次不再显示</button>
              <button className="btn" onClick={() => closeTutorial(true)}>跳过教程</button>
            </div>
          </div>
        </div>
      )}

      <aside className="sidebar">
        <div className="brand">
          <img className="brand-logo" src="/thesisloom.png" alt="ThesisLoom" />
          <p>Desktop Console</p>
        </div>

        <nav className="nav-list">
          <button className={page === "projects" ? "nav-btn active" : "nav-btn"} onClick={() => setPage("projects")}>项目</button>
          <button className={page === "inputs" ? "nav-btn active" : "nav-btn"} onClick={() => setPage("inputs")}>输入</button>
          <button className={page === "workflow" ? "nav-btn active" : "nav-btn"} onClick={() => setPage("workflow")}>流程</button>
          <button className={page === "outputs" ? "nav-btn active" : "nav-btn"} onClick={() => setPage("outputs")}>输出</button>
          <button className={page === "about" ? "nav-btn active" : "nav-btn"} onClick={() => setPage("about")}>关于</button>
        </nav>

        <div className="sidebar-meta">
          <div className="line"><span>当前项目:</span> {stateSnapshot?.project_name || "-"}</div>
          <div className="line"><span>当前阶段:</span> {phaseMajor}</div>
          <div className="line"><span>Tokens(in):</span> {inputTokens.toLocaleString()}</div>
          <div className="line"><span>Tokens(out):</span> {outputTokens.toLocaleString()}</div>
        </div>
      </aside>

      <main className="content-area">
        <header className="hero">
          <div>
            <h2>Human-in-the-Loop Workspace</h2>
            <p>面向论文全流程的人机协作工作台，覆盖资料准备、写作生成、审稿决策与改稿落地。</p>
          </div>

          <section className="top-info-grid">
            <div className="top-pill topic-pill"><span>当前论文标题</span>{topicLine}</div>
            <div className="top-pill phase-pill">
              <span>当前流程阶段</span>
              <strong>{phaseMajor}</strong>
              <small>{phaseMinor}</small>
            </div>
            <div className={runtimeIsRunning ? "top-pill runtime-pill is-running" : "top-pill runtime-pill"}>
              <span>运行状态 · 运行控制</span>
              <strong>{runtimeStatus}</strong>
              {runtimeIsRunning
                ? <small className="runtime-running-hint">正在运行中...</small>
                : <small className="runtime-running-hint">{runtimeControlHint}</small>}
            </div>
          </section>

          <section className="global-runtime-strip">
            <div className="global-runtime-actions">
              <button
                className="btn major"
                disabled={!canToggleRuntimeControl || runtimeControlBusy}
                onClick={() => void handleRuntimeControlClick(runtimeControlAction)}
              >
                {runtimeControlBusy ? "提交中..." : runtimeControlText}
              </button>
              <button
                className={skipApprovalEnabled ? "btn skip-approval-btn active" : "btn skip-approval-btn"}
                onClick={() => setSkipApprovalEnabled((prev) => !prev)}
              >
                {skipApprovalEnabled ? "跳过审批：已开启" : "跳过审批：未开启"}
              </button>
            </div>
            <small className="global-runtime-hint">{runtimeControlHint}</small>
          </section>
        </header>

        <div key={page} className="page-transition">

        {page === "projects" && (
          <section className="panel view-panel view-panel-flat">
            <h3>项目管理</h3>
            <div className="project-grid">
              <label className="field project-field">
                <span>打开已有项目</span>
                <select
                  title="existing projects"
                  value={selectedProjectName}
                  onChange={(e) => {
                    const nextProject = e.target.value;
                    setSelectedProjectName(nextProject);
                    void openProjectByName(nextProject);
                  }}
                >
                  {projects.length === 0 && <option value="">(暂无项目)</option>}
                  {projects.map((name) => (
                    <option key={name} value={name}>{name}</option>
                  ))}
                </select>
              </label>
              <div className="project-actions">
                <button className="btn" onClick={openSelectedProjectFolder}>打开项目文件夹</button>
                <button className="btn danger" onClick={moveProjectToTrash}>将当前选中项目移至回收站</button>
              </div>

              <label className="field project-field">
                <span>新建项目名称</span>
                <input
                  title="new project name"
                  placeholder="例如 demo_preflow"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                />
              </label>
              <div className="project-actions">
                <button className="btn major" onClick={createAndOpenProject}>新建并打开</button>
              </div>
            </div>

            <div className="project-chips">
              {projects.map((name) => (
                <button
                  key={name}
                  type="button"
                  className={name === selectedProjectName ? "project-chip active" : "project-chip"}
                  onClick={() => {
                    setSelectedProjectName(name);
                    void openProjectByName(name);
                  }}
                >
                  {name}
                </button>
              ))}
            </div>
          </section>
        )}

        {page === "inputs" && (
          <section className="panel view-panel view-panel-flat">
            <h3>写作参数设置</h3>
            <p className="section-help">带 * 的字段为必填项。论文标题可留空，流程会自动补全。API 密钥按当前供应商只需填写一项，填写后点击“立即保存参数”，系统会自动更新状态。</p>
            <div
              className={
                hasBlockingInputIssues
                  ? "validation-banner danger"
                  : inputValidation.warnings.length > 0
                    ? "validation-banner warn"
                    : "validation-banner ok"
              }
            >
              <span className="validation-pill">参数校验</span>
              <strong>
                {hasBlockingInputIssues
                  ? `发现 ${inputValidation.blockingIssues.length} 项必修问题`
                  : inputValidation.warnings.length > 0
                    ? `发现 ${inputValidation.warnings.length} 条提示`
                    : "参数格式检查通过"}
              </strong>
              <small>
                {hasBlockingInputIssues
                  ? "修复红色错误后再启动流程。"
                  : inputValidation.warnings[0] || "可以继续保存参数并启动流程。"}
              </small>
            </div>

            {inputValidation.warnings.length > 1 && !hasBlockingInputIssues && (
              <div className="validation-list">
                {inputValidation.warnings.slice(1).map((item, idx) => (
                  <div key={`input-warning-${idx}`} className="validation-item">{item}</div>
                ))}
              </div>
            )}

            <div className="input-checklist-head">
              <strong>参数完成度</strong>
              <small>{readyChecklistCount}/{inputChecklist.length} 项通过</small>
            </div>
            <div className="input-checklist-grid">
              {inputChecklist.map((item) => (
                <article key={item.key} className={item.ready ? "input-check-item ready" : "input-check-item pending"}>
                  <span>{item.label}</span>
                  <strong>{item.ready ? "已就绪" : "待完善"}</strong>
                  <small>{item.hint}</small>
                </article>
              ))}
            </div>

            <div className="settings-groups">
              <section className="settings-group">
                <h4>写作设置</h4>
                <div className="form-grid">
                  <label className={inputValidation.fieldErrors.topic ? "field field-wide has-error" : "field field-wide"}>
                    <span>论文标题（可选）</span>
                    <textarea
                      className={inputValidation.fieldErrors.topic ? "topic-textarea input-invalid" : "topic-textarea"}
                      title="topic"
                      placeholder="请输入论文主题"
                      value={inputsForm.topic}
                      onChange={(e) => updateForm("topic", e.target.value)}
                    />
                    {inputValidation.fieldErrors.topic && <small className="field-error">{inputValidation.fieldErrors.topic}</small>}
                    <small className="field-help">可留空自动生成；若手动填写，建议写清研究对象、方法方向与预期目标。</small>
                  </label>

                  <label className="field">
                    <span>写作语言 <b className="required-mark">*</b></span>
                    <select
                      title="language"
                      value={inputsForm.language}
                      onChange={(e) => updateForm("language", e.target.value === "Chinese" ? "Chinese" : "English")}
                    >
                      <option value="English">English</option>
                      <option value="Chinese">Chinese</option>
                    </select>
                    <small className="field-help">选择你希望论文最终输出的语言。</small>
                  </label>
                </div>
              </section>

              <section className="settings-group">
                <h4>语言模型设置</h4>
                <div className="form-grid">
                  <label className="field">
                    <span>模型供应商 <b className="required-mark">*</b></span>
                    <select
                      title="model_provider"
                      value={inputsForm.model_provider}
                      onChange={(e) => {
                        const value: ModelProvider = e.target.value === "doubao"
                          ? "doubao"
                          : e.target.value === "openrouter"
                            ? "openrouter"
                            : e.target.value === "anthropic"
                              ? "anthropic"
                            : "base_url";
                        updateForm("model_provider", value);
                        if (value === "doubao") {
                          updateForm("model", DOUBAO_DEFAULT_MODEL);
                        } else {
                          updateForm("model", DEFAULT_PROVIDER_MODEL[value]);
                        }
                        if (value === "base_url" && !String(inputsForm.base_url || "").trim()) {
                          updateForm("base_url", BASE_URL_TEST_ENDPOINT);
                        }
                        if (value === "base_url" && !String(inputsForm.model_api_key || "").trim()) {
                          updateForm("model_api_key", BASE_URL_TEST_API_KEY);
                        }
                        if (value === "openrouter" && !String(inputsForm.base_url || "").trim()) {
                          updateForm("base_url", "https://openrouter.ai/api/v1");
                        }
                        if (value === "anthropic" && !String(inputsForm.base_url || "").trim()) {
                          updateForm("base_url", ANTHROPIC_DEFAULT_BASE_URL);
                        }
                      }}
                    >
                      <option value="base_url">自定义 Base URL</option>
                      <option value="doubao">豆包 Ark</option>
                      <option value="openrouter">OpenRouter</option>
                      <option value="anthropic">Anthropic 格式</option>
                    </select>
                    <small className="field-help">用于决定请求路由：Base URL、豆包、OpenRouter 或 Anthropic。</small>
                  </label>

                  <label className={inputValidation.fieldErrors.model ? "field has-error" : "field"}>
                    <span>使用模型名称 <b className="required-mark">*</b></span>
                    <select
                      className={inputValidation.fieldErrors.model ? "input-invalid" : ""}
                      title="model"
                      value={providerSelectedModel}
                      onChange={(e) => updateForm("model", e.target.value)}
                    >
                      {providerModelOptions.map((name) => (
                        <option key={name} value={name}>{name}</option>
                      ))}
                    </select>
                    {inputValidation.fieldErrors.model && <small className="field-error">{inputValidation.fieldErrors.model}</small>}
                    <small className="field-help">
                      {isDoubaoProvider
                        ? "豆包固定两项：doubao-seed-2-0-pro-260215 / doubao-seed-2-0-mini-260215"
                        : isAnthropicProvider
                          ? "Anthropic 固定两项：claude-opus-4-6 / claude-opus-4-6-20260205"
                          : isOpenRouterProvider
                            ? "OpenRouter 当前复用 Base URL 固定模型列表。"
                            : "Base URL 固定两项：claude-sonnet-4-5-20250929-thinking / gemini-3.1-pro"}
                    </small>
                  </label>

                  {(inputsForm.model_provider === "base_url" || inputsForm.model_provider === "openrouter" || inputsForm.model_provider === "anthropic") && (
                    <label className={inputValidation.fieldErrors.base_url ? "field has-error" : "field"}>
                      <span>模型服务地址（可选）</span>
                      <input
                        className={inputValidation.fieldErrors.base_url ? "input-invalid" : ""}
                        title="base_url"
                        placeholder={
                          inputsForm.model_provider === "openrouter"
                            ? "例如 https://openrouter.ai/api/v1"
                            : inputsForm.model_provider === "anthropic"
                              ? "例如 https://api.anthropic.com"
                              : `默认 ${BASE_URL_TEST_ENDPOINT}`
                        }
                        value={inputsForm.base_url}
                        onChange={(e) => updateForm("base_url", e.target.value)}
                      />
                      {inputValidation.fieldErrors.base_url && <small className="field-error">{inputValidation.fieldErrors.base_url}</small>}
                      <small className="field-help">
                        {inputsForm.model_provider === "openrouter"
                          ? "可改为自定义 OpenRouter 网关地址。"
                          : inputsForm.model_provider === "anthropic"
                            ? "支持官方 Anthropic 或兼容 Anthropic /v1/messages 的网关地址。"
                            : `默认使用测试地址 ${BASE_URL_TEST_ENDPOINT}。`}
                      </small>
                    </label>
                  )}

                  <label className="field">
                    <span>
                      {activeApiKeyLabel}
                      {activeApiKeyLink && (
                        <button
                          type="button"
                          className="field-link-btn"
                          onClick={() => void openExternalLink(activeApiKeyLink)}
                        >
                          获取链接
                        </button>
                      )}
                    </span>
                    <input
                      title={activeApiKeyTitle}
                      placeholder={activeApiKeyPlaceholder}
                      value={activeApiKeyValue}
                      onChange={(e) => {
                        const value = e.target.value;
                        if (isDoubaoProvider) {
                          updateForm("ark_api_key", value);
                          return;
                        }
                        updateForm("model_api_key", value);
                      }}
                    />
                    <small className="field-help">{activeApiKeyHelp}</small>
                  </label>
                </div>
              </section>

              <section className="settings-group">
                <h4>文献检索设置</h4>
                <div className="form-grid">
                  <label className={inputValidation.fieldErrors.paper_search_limit ? "field has-error" : "field"}>
                    <span>文献检索数量上限 <b className="required-mark">*</b></span>
                    <input
                      className={inputValidation.fieldErrors.paper_search_limit ? "input-invalid" : ""}
                      title="paper_search_limit"
                      type="number"
                      min={1}
                      max={300}
                      value={inputsForm.paper_search_limit}
                      onChange={(e) => updateForm("paper_search_limit", toNumber(e.target.value, inputsForm.paper_search_limit, 1, 300))}
                    />
                    {inputValidation.fieldErrors.paper_search_limit && (
                      <small className="field-error">{inputValidation.fieldErrors.paper_search_limit}</small>
                    )}
                    <small className="field-help">用于限制自动检索的文献条数，数字越大检索时间通常越长。</small>
                  </label>

                  <label className="field">
                    <span>
                      OpenAlex API 密钥（可选）
                      <button
                        type="button"
                        className="field-link-btn"
                        onClick={() => void openExternalLink("https://openalex.org/settings/api-key")}
                      >
                        获取链接
                      </button>
                    </span>
                    <input
                      title="openalex_api_key"
                      placeholder="可选"
                      value={inputsForm.openalex_api_key}
                      onChange={(e) => updateForm("openalex_api_key", e.target.value)}
                    />
                    <small className="field-help">用于文献检索加速或提高访问稳定性，不填也可运行。</small>
                  </label>
                </div>
              </section>
            </div>

            <section className={inputValidation.fieldErrors.image_descriptions ? "settings-group settings-group-wide image-settings-group has-error" : "settings-group settings-group-wide image-settings-group"}>
              <h4>图片描述列表（可选）</h4>
              <div className="image-description-editor">
                {inputsForm.image_descriptions.length === 0 && (
                  <div className="image-empty-hint">当前还没有图片描述。点击下方按钮可按行新增。</div>
                )}

                {inputsForm.image_descriptions.length > 0 && (
                  <div className="image-description-grid">
                    {inputsForm.image_descriptions.map((item, index) => (
                      <article key={`image-description-${index}`} className="image-description-row">
                        <div className="image-row-head">
                          <strong>图片 {index + 1}</strong>
                          <button
                            type="button"
                            className="btn ghost btn-mini"
                            onClick={() => removeImageDescriptionRow(index)}
                          >
                            删除
                          </button>
                        </div>

                        <label className="field">
                          <span>图标题（可选）</span>
                          <input
                            title={`image_title_${index + 1}`}
                            placeholder="例如：性能对比图"
                            value={item.title}
                            onChange={(e) => updateImageDescriptionRow(index, "title", e.target.value)}
                          />
                        </label>

                        <label className="field">
                          <span>图片详细描述</span>
                          <textarea
                            title={`image_detailed_description_${index + 1}`}
                            rows={4}
                            placeholder="请尽量描述图中元素、坐标轴、变量关系、趋势与标注要求..."
                            value={item.detailed_description}
                            onChange={(e) => updateImageDescriptionRow(index, "detailed_description", e.target.value)}
                          />
                        </label>
                      </article>
                    ))}
                  </div>
                )}

                <div className="image-editor-actions">
                  <button
                    type="button"
                    className="btn"
                    onClick={addImageDescriptionRow}
                  >
                    + 新增图片描述
                  </button>
                </div>
              </div>
              {inputValidation.fieldErrors.image_descriptions && (
                <small className="field-error">{inputValidation.fieldErrors.image_descriptions}</small>
              )}
              <small className="field-help">每行显示 3 张图卡；仅填写标题不会生效，至少补充“图片详细描述”后才会参与后续规划与写作。</small>
            </section>

            <div className="action-buttons">
              <button className="btn" onClick={refreshInputs}>重新加载参数</button>
              <button className="btn major" onClick={() => void persistInputsForm(false)}>立即保存参数</button>
            </div>
            <div className={`autosave-indicator ${autoSaveStatusClass}`}>
              <span className="autosave-dot" />
              <span>{autoSaveHint}</span>
            </div>

            <h3>输入资料文件（可直接编辑）</h3>
            <p className="section-help">这里用于填写素材、已有章节、相关研究和改写要求，系统会按文件用途自动读取。</p>
            <div className="file-tabs">
              {editableFiles.map((path) => (
                <button
                  key={path}
                  className={path === selectedFilePath ? "tab active" : "tab"}
                  onClick={() => loadSelectedFile(path)}
                >
                  {describeInputFile(path)}
                </button>
              ))}
            </div>

            <div className="line"><span>当前编辑内容:</span> {describeInputFile(selectedFilePath) || "-"}</div>
            <textarea
              title="selected input file editor"
              className="input-file-textarea"
              placeholder="在这里编辑所选输入文件"
              value={selectedFileContent}
              onChange={(e) => setSelectedFileContent(e.target.value)}
              onBlur={() => {
                void saveSelectedFile(true);
              }}
            />
            <div className="action-buttons">
              <button className="btn" onClick={() => loadSelectedFile(selectedFilePath)}>重新加载文件</button>
              <button className="btn major" onClick={() => void saveSelectedFile(false)}>保存当前文件</button>
            </div>
          </section>
        )}

        {page === "outputs" && (
          <section className="panel view-panel view-panel-flat">
            <div className="section-title-row">
              <h3>结果查看（只读）</h3>
              <div className="status-chip-row">
                <span className="status-chip neutral">正文 {paperOutputs.length} 节</span>
                <span className="status-chip neutral">过程产物 {pipelineArtifactTotal} 条</span>
              </div>
            </div>
            <p className="section-help">左侧查看正文内容，右侧查看系统过程产物（检索、规划与审稿建议）。</p>

            <div className="outputs-overview-grid">
              <article className="output-stat-card">
                <span>正文章节</span>
                <strong>{paperOutputs.length}</strong>
                <small>可展开查看完整正文内容</small>
              </article>
              <article className="output-stat-card">
                <span>检索关键词</span>
                <strong>{searchQueries.length}</strong>
                <small>用于文献检索与研究空白分析</small>
              </article>
              <article className="output-stat-card">
                <span>审稿/改写项</span>
                <strong>{overallPlans.length + majorReviewItems.length}</strong>
                <small>包含总体计划与分章节审稿建议</small>
              </article>
            </div>

            <div className="tab-head">
              <button className={outputTab === "paper" ? "tab active" : "tab"} onClick={() => setOutputTab("paper")}>正文结果</button>
              <button className={outputTab === "pipeline" ? "tab active" : "tab"} onClick={() => setOutputTab("pipeline")}>过程产物</button>
            </div>

            <div className="output-head-tools">
              {outputTab === "paper" && (
                <button className="btn" onClick={togglePaperExpandAll}>
                  {paperExpandAll ? "恢复手动折叠" : "正文全部展开"}
                </button>
              )}
              {outputTab === "pipeline" && (
                <button className="btn" onClick={togglePipelineExpandAll}>
                  {pipelineExpandAll ? "恢复精简视图" : "过程产物全部展开"}
                </button>
              )}
            </div>

            {outputTab === "paper" && (
              <div className="output-pane">
                <div className="output-tools">
                  <label className="field field-wide output-filter-field">
                    <span>正文关键词筛选</span>
                    <input
                      title="paper output keyword filter"
                      placeholder="按章节名、子章节编号或正文内容筛选"
                      value={outputSearchQuery}
                      onChange={(e) => setOutputSearchQuery(e.target.value)}
                    />
                  </label>
                  {outputSearchQuery.trim() && (
                    <button className="btn" onClick={() => setOutputSearchQuery("")}>清空筛选</button>
                  )}
                </div>

                <div className="line"><span>展示结果:</span> {filteredPaperOutputs.length}/{paperOutputs.length} 节</div>

                {paperOutputs.length === 0 && <div className="empty-tip">当前还没有正文输出。</div>}
                {paperOutputs.length > 0 && filteredPaperOutputs.length === 0 && (
                  <div className="empty-tip">未找到匹配“{outputSearchQuery.trim()}”的正文结果，请调整关键词。</div>
                )}

                {filteredPaperOutputs.map((row, idx) => {
                  const label = `第 ${row.actual_order_index ?? idx + 1} 节 | ${row.major_title || "未命名章节"} | ${row.title || row.sub_chapter_id || "未命名小节"}`;
                  const sectionText = String(row.content || "");
                  const sectionSize = sectionText.trim().length;
                  const sectionWordCount = sectionText.trim() ? sectionText.trim().split(/\s+/).length : 0;
                  return (
                    <details
                      key={`${row.sub_chapter_id || "na"}-${idx}-${paperExpandToken}`}
                      className="fold-block"
                      open={paperExpandAll ? true : undefined}
                    >
                      <summary>{label.trim()}</summary>
                      <div className="fold-actions">
                        <span className="fold-meta">字符数 {sectionSize.toLocaleString()} · 词数 {sectionWordCount.toLocaleString()}</span>
                        <button className="btn" onClick={() => void copyTextToClipboard(sectionText, "正文片段已复制")}>复制正文</button>
                      </div>
                      <pre>{sectionText || "(empty)"}</pre>
                    </details>
                  );
                })}
              </div>
            )}

            {outputTab === "pipeline" && (
              <div className="output-pane">
                <details
                  className="fold-block"
                  key={`pipeline-search-${pipelineExpandToken}`}
                  open={pipelineExpandAll ? true : undefined}
                >
                  <summary>系统生成的文献检索关键词（{searchQueries.length} 条）</summary>
                  {searchQueries.length === 0 ? (
                    <div className="empty-tip">暂无检索关键词。</div>
                  ) : (
                    <ol className="schema-list">
                      {searchQueries.map((query, idx) => (
                        <li key={`search-query-${idx}`} className="schema-item">
                          <span className="schema-index">{idx + 1}</span>
                          <span className="schema-main">{String(query || "").trim() || "(empty)"}</span>
                        </li>
                      ))}
                    </ol>
                  )}
                </details>

                <details
                  className="fold-block"
                  key={`pipeline-outline-${pipelineExpandToken}`}
                  open={pipelineExpandAll ? true : undefined}
                >
                  <summary>论文整体章节架构（{architectOutline.length} 项）</summary>
                  {architectOutline.length === 0 ? (
                    <div className="empty-tip">暂无章节架构数据。</div>
                  ) : (
                    <div className="schema-stack">
                      {architectOutline.map((item, idx) => {
                        const record = asRecord(item) || {};
                        const majorId = pickText(record, ["major_chapter_id", "id"], `${idx + 1}`);
                        const majorTitle = pickText(record, ["major_title", "title"], "(untitled)");
                        const majorPurpose = pickText(record, ["major_purpose", "purpose", "architecture_role"], "-");
                        const subSections = asRecordArray(record.sub_sections);
                        return (
                          <article key={`outline-major-${majorId}-${idx}`} className="schema-card">
                            <h4>{majorId}. {majorTitle}</h4>
                            <p className="schema-subtext">{majorPurpose}</p>
                            {subSections.length > 0 && (
                              <ul className="schema-sub-list">
                                {subSections.map((sub, subIdx) => {
                                  const subId = pickText(sub, ["sub_chapter_id", "id"], `${majorId}.${subIdx + 1}`);
                                  const subTitle = pickText(sub, ["sub_title", "title"], "(untitled)");
                                  return (
                                    <li key={`outline-sub-${majorId}-${subId}-${subIdx}`}>
                                      <strong>{subId}</strong>
                                      <span>{subTitle}</span>
                                    </li>
                                  );
                                })}
                              </ul>
                            )}
                          </article>
                        );
                      })}
                    </div>
                  )}
                </details>

                <details
                  className="fold-block"
                  key={`pipeline-planner-${pipelineExpandToken}`}
                  open={pipelineExpandAll ? true : undefined}
                >
                  <summary>各章节的小节写作规划（{plannerOutputs.length} 项）</summary>
                  {plannerOutputs.length === 0 ? (
                    <div className="empty-tip">暂无小节写作规划。</div>
                  ) : (
                    <div className="schema-stack">
                      {plannerOutputs.map((item, idx) => {
                        const record = asRecord(item) || {};
                        const subId = pickText(record, ["sub_chapter_id", "id"], `Item-${idx + 1}`);
                        const subTitle = pickText(record, ["sub_title", "title"], "(untitled)");
                        const majorId = pickText(record, ["major_chapter_id"], "-");
                        const majorTitle = pickText(record, ["major_title"], "-");
                        const objective = pickText(
                          record,
                          ["writing_objective", "sub_purpose", "architecture_role", "selected_guidance_key"],
                          "-",
                        );
                        const blueprints = Array.isArray(record.paragraph_blueprints) ? record.paragraph_blueprints.length : 0;
                        return (
                          <article key={`planner-item-${subId}-${idx}`} className="schema-card">
                            <h4>{subId} {subTitle}</h4>
                            <div className="schema-meta-row">
                              <span>所属章节：{majorId} {majorTitle}</span>
                              <span>段落规划：{blueprints} 段</span>
                            </div>
                            <p className="schema-subtext">{objective}</p>
                          </article>
                        );
                      })}
                    </div>
                  )}
                </details>

                <details
                  className="fold-block"
                  key={`pipeline-overall-${pipelineExpandToken}`}
                  open={pipelineExpandAll ? true : undefined}
                >
                  <summary>全文审稿总结与改进计划（{overallPlans.length} 条计划）</summary>
                  <div className="json-box">
                    <h4>审稿结论摘要</h4>
                    <div className="schema-summary-box">{stateSnapshot?.overall_review_summary || "(no summary)"}</div>
                    <h4>改进计划清单</h4>
                    {overallPlans.length === 0 ? (
                      <div className="empty-tip">暂无改进计划。</div>
                    ) : (
                      <ol className="schema-list">
                        {overallPlans.map((item, idx) => {
                          const record = asRecord(item) || {};
                          const title = pickText(record, ["major_title", "title", "target", "focus"], `计划 ${idx + 1}`);
                          const action = pickText(record, ["action", "revision_goal", "instruction", "rewrite_guidance"], "-");
                          const priority = pickText(record, ["priority"], "medium");
                          return (
                            <li key={`overall-plan-${idx}`} className="schema-item">
                              <span className="schema-index">{idx + 1}</span>
                              <div className="schema-main-block">
                                <div className="schema-main">{title}</div>
                                <div className="schema-subtext">{action}</div>
                                <div className="schema-meta-row"><span className="tag-chip">优先级：{priority}</span></div>
                              </div>
                            </li>
                          );
                        })}
                      </ol>
                    )}
                  </div>
                </details>

                <details
                  className="fold-block"
                  key={`pipeline-major-${pipelineExpandToken}`}
                  open={pipelineExpandAll ? true : undefined}
                >
                  <summary>分章节审稿意见（{majorReviewItems.length} 条）</summary>
                  {majorReviewItems.length === 0 ? (
                    <div className="empty-tip">暂无分章节审稿意见。</div>
                  ) : (
                    <div className="schema-stack">
                      {majorReviewItems.map((item, idx) => {
                        const record = asRecord(item) || {};
                        const subId = pickText(record, ["sub_chapter_id", "id"], `${idx + 1}`);
                        const title = pickText(record, ["title", "sub_title"], "(untitled)");
                        const priority = pickText(record, ["priority"], "medium");
                        const itemType = pickText(record, ["item_type"], "text");
                        const issues = issueListFromValue(record.issues);
                        return (
                          <article key={`major-review-${subId}-${idx}`} className="schema-card">
                            <h4>{subId} {title}</h4>
                            <div className="schema-meta-row">
                              <span className="tag-chip">类型：{itemType}</span>
                              <span className="tag-chip">优先级：{priority}</span>
                              <span className="tag-chip">问题数：{issues.length}</span>
                            </div>
                            {issues.length > 0 && (
                              <ul className="schema-sub-list">
                                {issues.map((issue, issueIdx) => (
                                  <li key={`major-review-issue-${subId}-${issueIdx}`}>
                                    <span>{issue}</span>
                                  </li>
                                ))}
                              </ul>
                            )}
                          </article>
                        );
                      })}
                    </div>
                  )}
                </details>
              </div>
            )}
          </section>
        )}

        {page === "workflow" && (
          <section className="panel view-panel workflow-grid">
            <section className="workflow-overview-grid">
              <article className={pendingAction ? "workflow-kpi-card danger" : "workflow-kpi-card ok"}>
                <span>待处理动作</span>
                <strong>{pendingActionLabel}</strong>
                <small>
                  {stateSnapshot?.pending_action_message || (pendingAction ? "请先完成该动作后继续流程。" : "当前没有阻塞动作。")}
                </small>
              </article>

              <article className="workflow-kpi-card">
                <span>当前阶段</span>
                <strong>{phaseMajor}</strong>
                <small>{phaseMinor}</small>
              </article>

              <article className="workflow-kpi-card">
                <span>进度概览</span>
                <strong>{completedSectionCount}/{draftingTotalDisplay} 小节</strong>
                <small>
                  审稿轮次 {reviewRoundTag || reviewRound} · 已完成改写 {rewriteDoneCount}/{rewriteProgressItems.length}
                </small>
              </article>
            </section>

            {reviewRoundTag && (
              <div className="workflow-round-banner">
                当前处于 {reviewRoundTag}，审稿相关步骤会自动标注轮次。
              </div>
            )}

            <section className="panel-block">
              <div className="section-title-row">
                <h3>动作控制</h3>
                <div className="status-chip-row">
                  <span className={skipApprovalEnabled ? "status-chip ok" : "status-chip neutral"}>
                    跳过审批：{skipApprovalEnabled ? "开启" : "关闭"}
                  </span>
                </div>
              </div>
              <div className="line"><span>待处理动作:</span> {pendingActionLabel}</div>
              <div className="line"><span>动作提示:</span> {stateSnapshot?.pending_action_message || "-"}</div>
              <div className="line"><span>跳过审批:</span> {skipApprovalEnabled ? "已开启" : "未开启"}</div>
              {actionControl}
            </section>

            <section className="panel-block">
              <h3>流程视图</h3>
              <div className="phase-track">
                {FLOW_STEPS.map((step, idx) => {
                  const status = resolveStepStatus(idx);
                  const displayTitle = isReviewFlowStep(step.key) && reviewRoundTag ? `${step.title}${reviewRoundTag}` : step.title;
                  return (
                    <div key={`${step.key}-track`} className={`phase-track-item ${status}`}>
                      <div className="phase-track-dot" />
                      <span>{displayTitle}</span>
                      {idx < FLOW_STEPS.length - 1 && <i className={status === "done" ? "phase-track-line done" : "phase-track-line"} />}
                    </div>
                  );
                })}
              </div>
              <div className="flow-list">
                {FLOW_STEPS.map((step, idx) => {
                  const status = resolveStepStatus(idx);
                  const displayTitle = isReviewFlowStep(step.key) && reviewRoundTag ? `${step.title}${reviewRoundTag}` : step.title;
                  return (
                    <div key={step.key} className={`flow-item ${status}`}>
                      <div className="marker">{status === "done" ? "✓" : status === "current" ? "▶" : "○"}</div>
                      <div>
                        <div className="flow-title-row">
                          <strong>{displayTitle}</strong>
                          <span>{getFlowStatusLabel(status)}</span>
                        </div>
                        <p>{step.desc}</p>

                        {step.key === "drafting" && draftingProgressItems.length > 0 && (
                          <div className="drafting-progress-inline">
                            <div className="drafting-progress-head">
                              <strong>小节写作进度</strong>
                              <div className="mini-progress-wrap">
                                <small>{nextStepsUpdatedAt || "-"}</small>
                                <progress className="mini-progress" value={draftingProgressPercent} max={100} />
                                <small>{draftingDoneCount}/{draftingTotalCount} ({draftingProgressPercent}%)</small>
                                <small>实际写作耗时 {draftingElapsedLabel}</small>
                                <small>预计剩余 {draftingEtaLabel}</small>
                              </div>
                            </div>
                            <div className="drafting-progress-list">
                              {draftingProgressItems.map((item, itemIdx) => (
                                <div
                                  key={`${item.subId}-${item.order}-${itemIdx}`}
                                  className={
                                    item.done
                                      ? "drafting-progress-item done"
                                      : item.current
                                        ? "drafting-progress-item current"
                                        : "drafting-progress-item"
                                  }
                                >
                                  <strong>{item.order}. {item.subId}</strong>
                                  <span>{item.title}</span>
                                  <em>{item.done ? "已完成" : item.current ? "进行中" : "待执行"}</em>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {step.key === "rewrite_execution" && rewriteProgressItems.length > 0 && (
                          <div className="drafting-progress-inline">
                            <div className="drafting-progress-head">
                              <strong>改写小节进度</strong>
                              <small>{rewriteProgressItems.length} 项</small>
                            </div>
                            <div className="drafting-progress-list">
                              {rewriteProgressItems.map((item) => (
                                <div
                                  key={`${item.subId}-${item.idx}`}
                                  className={
                                    item.done
                                      ? "drafting-progress-item done"
                                      : item.current
                                        ? "drafting-progress-item current"
                                        : "drafting-progress-item"
                                  }
                                >
                                  <strong>{item.subId}</strong>
                                  <span>{item.title || (item.itemType === "chapter_header" ? "章节标题与总起句" : "正文小节改写")}</span>
                                  <em>
                                    {item.done ? "已完成" : item.current ? "进行中" : `${getReviewPriorityLabel(item.priority)} · 待执行`}
                                    {item.issueCount > 0 ? ` · 问题 ${item.issueCount} 条` : ""}
                                  </em>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="line"><span>当前节点:</span> {currentNode || "-"}</div>
              <div className="line"><span>当前子步骤:</span> {phaseMinor}</div>
              <div className="line"><span>审稿轮次:</span> {(stateSnapshot?.review_round ?? 0)}</div>
              <div className="line"><span>完成小节:</span> {stateSnapshot?.completed_section_count ?? 0} | 待改写 {stateSnapshot?.pending_rewrite_count ?? 0}</div>
            </section>

            <section className="panel-block">
              <h3>关键节点与版本回退</h3>

              {keyMilestones.length === 0 && (
                <div className="empty-tip">暂无关键节点快照。完成初稿或审稿轮次后会自动出现。</div>
              )}

              {keyMilestones.length > 0 && (
                <div className="drafting-progress-inline">
                  <div className="drafting-progress-head">
                    <strong>关键节点</strong>
                    <small>{keyMilestones.length} 项</small>
                  </div>
                  <div className="drafting-progress-list milestone-grid">
                    {keyMilestones.map((item, idx) => (
                      <div key={`${item.tag || "milestone"}-${idx}`} className="drafting-progress-item done">
                        <strong>{item.label || item.tag || "关键节点"}</strong>
                        <span>{item.time || "-"}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="drafting-progress-inline">
                <div className="drafting-progress-head">
                  <strong>版本快照</strong>
                  <small>{versionSnapshots.length} 项</small>
                </div>
                <div className="drafting-progress-list milestone-grid">
                  {versionSnapshots.length === 0 && (
                    <div className="drafting-progress-item">
                      <span>暂无可回退快照。</span>
                    </div>
                  )}

                  {versionSnapshots.map((snap, idx) => (
                    <div key={`${snap.tag || "snapshot"}-${idx}`} className={snap.is_key_node ? "drafting-progress-item current" : "drafting-progress-item"}>
                      <strong>{snap.label || snap.tag || "snapshot"}</strong>
                      <span>{snap.saved_at || "-"}</span>
                      <em>{snap.key_label || "普通快照"}</em>
                      <div className="action-buttons">
                        <button
                          className="btn"
                          disabled={!snap.state_path}
                          onClick={() => void rollbackToVersion(String(snap.state_path || ""), String(snap.label || snap.tag || "snapshot"))}
                        >
                          回退到此版本
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section className="panel-block logs-panel">
              <div className="logs-header">
                <h3>Workflow 日志</h3>
                <div className="action-buttons">
                  <button className={logMode === "key" ? "btn major" : "btn"} onClick={() => setLogMode("key")}>关键日志</button>
                  <button className={logMode === "detail" ? "btn major" : "btn"} onClick={() => setLogMode("detail")}>详细日志</button>
                </div>
              </div>
              <pre>{logs.join("\n")}</pre>
            </section>
          </section>
        )}

        {page === "about" && (
          <section className="panel view-panel view-panel-flat">
            <h3>关于 ThesisLoom</h3>
            <p className="section-help">论文写作全流程人机协作系统（Desktop + Local Backend）。</p>

            <div className="schema-stack">
              <article className="schema-card">
                <h4>软件信息</h4>
                <div className="line"><span>软件名称:</span> ThesisLoom</div>
                <div className="line"><span>当前版本:</span> v{APP_VERSION}</div>
                <div className="line"><span>运行模式:</span> Desktop UI + Local Backend</div>
                <div className="action-buttons">
                  <button className="btn" onClick={() => openTutorial(0)}>重新打开教程</button>
                </div>
              </article>

              <article className="schema-card">
                <h4>作者与联系方式</h4>
                <div className="line"><span>作者:</span> 李修然</div>
                <div className="line"><span>单位:</span> Tongji University</div>
                <div className="line"><span>邮箱:</span> xiuran@tongji.edu.cn</div>
              </article>

              <article className="schema-card">
                <h4>版权信息</h4>
                <div className="line">Copyright (c) {currentYear} 李修然@Tongji University. All rights reserved.</div>
                <div className="line">ThesisLoom 用于学术研究与论文写作流程辅助，使用时请遵守所在机构与数据合规要求。</div>
              </article>
            </div>
          </section>
        )}
        </div>
      </main>
    </div>
  );
}

export default App;
