import { useCallback, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
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
  saveInputFile,
  saveInputs,
  trashProject,
} from "./api";
import type { BackendStatus, LogMode, WorkflowStateSnapshot } from "./types";

const API_BASE_URL = "http://127.0.0.1:8765";

type PageKey = "projects" | "inputs" | "outputs" | "workflow";
type OutputTab = "paper" | "pipeline";

interface InputsFormState {
  topic: string;
  language: "English" | "Chinese";
  model: string;
  max_review_rounds: number;
  paper_search_limit: number;
  openalex_api_key: string;
  ark_api_key: string;
  base_url: string;
  model_api_key: string;
}

const DEFAULT_INPUTS_FORM: InputsFormState = {
  topic: "",
  language: "English",
  model: "gemini-3.1-pro",
  max_review_rounds: 3,
  paper_search_limit: 30,
  openalex_api_key: "",
  ark_api_key: "",
  base_url: "",
  model_api_key: "",
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
    desc: "完成检索、补充 related_works 并生成 research_gaps。",
  },
  {
    key: "architecture",
    title: "架构设计阶段",
    desc: "由 architect 生成并评审章节架构。",
  },
  {
    key: "planning",
    title: "章节规划阶段",
    desc: "由 planner 和章节开场节点完成写作前铺排。",
  },
  {
    key: "drafting",
    title: "正文撰写阶段",
    desc: "按小节顺序生成正文并实时更新完成状态。",
  },
  {
    key: "review_pending",
    title: "审稿准备",
    desc: "确认进入审稿前的人机协作参数。",
  },
  {
    key: "reviewing",
    title: "审稿与重写",
    desc: "轮次化审稿并按需重写。",
  },
  {
    key: "done",
    title: "流程完成",
    desc: "终稿产出完成，可导出或切换项目。",
  },
] as const;

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
  "node_planner",
  "node_chapter_header",
  "node_chapter_opening",
]);

const PHASE_LABELS: Record<string, string> = {
  idle: "准备中",
  pre_research: "前置研究",
  drafting: "撰写中",
  review_pending: "待进入审稿",
  reviewing: "审稿中",
  done: "已完成",
};

const ACTION_LABELS: Record<string, string> = {
  confirm_inputs_ready: "确认输入已准备",
  set_enable_auto_title: "是否自动生成标题",
  set_enable_search: "是否执行文献检索",
  confirm_related_works: "确认 related_works 已补充",
  enter_reviewing: "确认进入审稿",
  set_architecture_force_continue: "架构人工放行",
  retry_after_llm_failure: "LLM 失败后继续",
  confirm_next_review_round: "是否进入下一轮审稿",
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
  const pendingAction = String(snapshot.pending_action || "").trim();
  const queryCount = Number(snapshot.search_query_count || 0);

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
    if (pendingAction === "set_architecture_force_continue" || ARCHITECTURE_NODES.has(node)) {
      return "architecture";
    }
    if (PLANNING_NODES.has(node)) {
      return "planning";
    }
    return "drafting";
  }
  if (phase === "review_pending") {
    return "review_pending";
  }
  if (phase === "reviewing") {
    return "reviewing";
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

function prettyJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value ?? "");
  }
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
    "max_review_rounds",
    "paper_search_limit",
    "openalex_api_key",
    "ark_api_key",
    "base_url",
    "model_api_key",
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

  const form: InputsFormState = {
    topic: String(parsed.topic ?? DEFAULT_INPUTS_FORM.topic),
    language,
    model: String(parsed.model ?? DEFAULT_INPUTS_FORM.model),
    max_review_rounds: toNumber(parsed.max_review_rounds, DEFAULT_INPUTS_FORM.max_review_rounds, 1, 20),
    paper_search_limit: toNumber(parsed.paper_search_limit, DEFAULT_INPUTS_FORM.paper_search_limit, 1, 300),
    openalex_api_key: String(parsed.openalex_api_key ?? DEFAULT_INPUTS_FORM.openalex_api_key),
    ark_api_key: String(parsed.ark_api_key ?? DEFAULT_INPUTS_FORM.ark_api_key),
    base_url: String(parsed.base_url ?? DEFAULT_INPUTS_FORM.base_url),
    model_api_key: String(parsed.model_api_key ?? DEFAULT_INPUTS_FORM.model_api_key),
  };

  return { form, extra };
}

function composeInputsPayload(form: InputsFormState, extra: Record<string, unknown>): Record<string, unknown> {
  return {
    ...extra,
    topic: form.topic,
    language: form.language,
    model: form.model,
    max_review_rounds: form.max_review_rounds,
    paper_search_limit: form.paper_search_limit,
    openalex_api_key: form.openalex_api_key,
    ark_api_key: form.ark_api_key,
    base_url: form.base_url,
    model_api_key: form.model_api_key,
  };
}

function App() {
  const [page, setPage] = useState<PageKey>("workflow");
  const [outputTab, setOutputTab] = useState<OutputTab>("paper");

  const [backendStatus, setBackendStatus] = useState<BackendStatus>(EMPTY_BACKEND_STATUS);
  const [stateSnapshot, setStateSnapshot] = useState<WorkflowStateSnapshot | null>(null);

  const [inputsForm, setInputsForm] = useState<InputsFormState>(DEFAULT_INPUTS_FORM);
  const [inputsExtra, setInputsExtra] = useState<Record<string, unknown>>({});
  const [autoSaveHint, setAutoSaveHint] = useState<string>("等待加载参数");
  const suppressAutoSaveRef = useRef<boolean>(true);

  const [editableFiles, setEditableFiles] = useState<string[]>([]);
  const [selectedFilePath, setSelectedFilePath] = useState<string>("");
  const [selectedFileContent, setSelectedFileContent] = useState<string>("");

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

  const [loadRequirements, setLoadRequirements] = useState(true);
  const baseUrl = API_BASE_URL;

  const pushNotice = useCallback((kind: "info" | "ok" | "warn" | "error", text: string) => {
    setNotice({ kind, text, visible: true, token: Date.now() });
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
      const rows = (data.items || []).map((item) => {
        const t = item.time || "-";
        const lvl = item.level || "detail";
        const msg = item.message || "";
        return `[${t}] [${lvl}] ${msg}`;
      });
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
        setSelectedFilePath(path);
        setSelectedFileContent(payload.content || "");
      } catch (err) {
        pushNotice("error", `读取文件失败: ${String(err)}`);
      }
    },
    [baseUrl, pushNotice],
  );

  const saveSelectedFile = useCallback(async () => {
    if (!selectedFilePath) {
      pushNotice("warn", "未选择输入文件");
      return;
    }
    try {
      const payload = await saveInputFile(baseUrl, selectedFilePath, selectedFileContent);
      if (!payload.ok) {
        pushNotice("error", payload.message || "保存文件失败");
        return;
      }
      pushNotice("ok", `已保存 ${selectedFilePath}`);
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

  const sendAction = useCallback(
    async (payload: Record<string, unknown>) => {
      try {
        const data = await postAction(baseUrl, payload);
        if (!data.ok) {
          pushNotice("error", data.message || "动作提交失败");
          return;
        }

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
      } catch (err) {
        pushNotice("error", `动作提交失败: ${String(err)}`);
      }
    },
    [baseUrl, pushNotice, refreshLogs, refreshState],
  );

  const saveInputsAndStart = useCallback(async () => {
    const ok = await persistInputsForm(false);
    if (!ok) {
      return;
    }
    await sendAction({ action: "confirm_inputs_ready" });
  }, [persistInputsForm, sendAction]);

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
        port: 8765,
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

  const openExistingProject = useCallback(async () => {
    const projectName = selectedProjectName.trim();
    if (!projectName) {
      pushNotice("warn", "请先选择要打开的项目");
      return;
    }

    try {
      const result = await openProject(baseUrl, projectName);
      if (!result.ok) {
        pushNotice("error", result.message || "打开项目失败");
        return;
      }

      pushNotice("ok", `已打开项目: ${result.project_name || projectName}`);
      await refreshProjects();
      await refreshInputs();
      await loadEditableFiles();
      await refreshState();
      await refreshLogs();
    } catch (err) {
      pushNotice("error", `打开项目失败: ${String(err)}`);
    }
  }, [baseUrl, loadEditableFiles, pushNotice, refreshInputs, refreshLogs, refreshProjects, refreshState, selectedProjectName]);

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
      const result = await openProject(baseUrl, projectName);
      if (!result.ok) {
        pushNotice("error", result.message || "新建项目失败");
        return;
      }

      setNewProjectName("");
      setSelectedProjectName(result.project_name || projectName);
      pushNotice("ok", `已创建并打开项目: ${result.project_name || projectName}`);
      await refreshProjects();
      await refreshInputs();
      await loadEditableFiles();
      await refreshState();
      await refreshLogs();
    } catch (err) {
      pushNotice("error", `新建项目失败: ${String(err)}`);
    }
  }, [baseUrl, loadEditableFiles, newProjectName, pushNotice, refreshInputs, refreshLogs, refreshProjects, refreshState]);

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

  const phase = stateSnapshot?.workflow_phase || "idle";
  const pendingAction = stateSnapshot?.pending_action || "";
  const runtimeStatus = stateSnapshot?.runtime_status || "unknown";
  const currentNode = stateSnapshot?.current_node || "";
  const currentSubId = stateSnapshot?.current_sub_chapter_id || "";
  const flowKey = resolveFlowKey(stateSnapshot);
  const flowIndex = Math.max(0, FLOW_STEPS.findIndex((x) => x.key === flowKey));
  const flowProgress = (flowIndex + 1) / FLOW_STEPS.length;
  const topicLine = stateSnapshot?.topic || stateSnapshot?.inputs_topic || "(empty topic)";
  const paperOutputs = stateSnapshot?.paper_outputs || [];
  const searchQueries = stateSnapshot?.search_queries || [];
  const architectOutline = stateSnapshot?.architect_outline || [];
  const plannerOutputs = stateSnapshot?.planner_outputs || [];
  const overallPlans = stateSnapshot?.overall_review_plans || [];
  const majorReviewItems = stateSnapshot?.major_review_items || [];
  const nextSteps = stateSnapshot?.next_steps_plan || [];
  const nextStepsUpdatedAt = stateSnapshot?.next_steps_updated_at || "";
  const flowMajorLabel = FLOW_STEPS.find((x) => x.key === flowKey)?.title || "";
  const phaseMajor = flowMajorLabel || PHASE_LABELS[phase] || phase;

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

  const tokenUsage = stateSnapshot?.token_usage || {};
  const totalInputTokens = Number(tokenUsage.total_input_tokens || 0);
  const totalOutputTokens = Number(tokenUsage.total_output_tokens || 0);
  const totalTokens = totalInputTokens + totalOutputTokens;

  let phaseMinor = "等待流程节点";
  if (pendingAction) {
    phaseMinor = `待处理：${ACTION_LABELS[pendingAction] || pendingAction}`;
  } else if (currentNode) {
    phaseMinor = NODE_LABELS[currentNode] || currentNode;
  }
  if (currentSubId) {
    phaseMinor = `${phaseMinor} / ${currentSubId}`;
  }

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

  const actionControl = (
    <div className="action-zone">
      {!pendingAction && flowKey === "preparation" && (
        <div className="action-block">
          <p>当前处于准备阶段，可手动开始工作流。</p>
          <button className="btn major" onClick={saveInputsAndStart}>开始工作流</button>
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
          <button className="btn major" onClick={saveInputsAndStart}>保存并开始</button>
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
          <p>请补充 related_works 后继续。</p>
          <div className="action-buttons">
            <button
              className="btn"
              onClick={() => loadSelectedFile(stateSnapshot?.related_works_path || "inputs/related_works.md")}
            >
              打开预览
            </button>
            <button className="btn major" onClick={() => sendAction({ action: "confirm_related_works" })}>已补充，继续</button>
          </div>
        </div>
      )}

      {pendingAction === "enter_reviewing" && (
        <div className="action-block">
          <p>确认进入审稿阶段。</p>
          <label className="check-row">
            <input
              type="checkbox"
              checked={loadRequirements}
              onChange={(e) => setLoadRequirements(e.target.checked)}
            />
            加载自定义要求文件
          </label>
          <button
            className="btn major"
            onClick={() =>
              sendAction({
                action: "enter_reviewing",
                load_requirements: loadRequirements,
                  requirements_path: "inputs/write_requests.md",
                  manual_revision_path: "inputs/revision_requests.md",
              })
            }
          >
            确认进入审稿
          </button>
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

      <aside className="sidebar panel">
        <div className="brand">
          <h1>ThesisLoom</h1>
          <p>Desktop Console</p>
        </div>

        <nav className="nav-list">
          <button className={page === "projects" ? "nav-btn active" : "nav-btn"} onClick={() => setPage("projects")}>项目</button>
          <button className={page === "inputs" ? "nav-btn active" : "nav-btn"} onClick={() => setPage("inputs")}>输入</button>
          <button className={page === "outputs" ? "nav-btn active" : "nav-btn"} onClick={() => setPage("outputs")}>输出</button>
          <button className={page === "workflow" ? "nav-btn active" : "nav-btn"} onClick={() => setPage("workflow")}>流程</button>
        </nav>

        <div className="sidebar-meta">
          <div className="line"><span>当前项目:</span> {stateSnapshot?.project_name || "-"}</div>
          <div className="line"><span>当前阶段:</span> {phaseMajor}</div>
          <div className="line"><span>Tokens 使用量:</span> {totalTokens.toLocaleString()}</div>
        </div>
      </aside>

      <main className="content-area">
        <header className="hero">
          <div>
            <h2>Human-in-the-Loop Workspace</h2>
            <p>页面已拆分为项目、输入、输出、流程四个视图，按功能独立管理。</p>
          </div>

          <section className="top-info-grid">
            <div className="top-pill topic-pill"><span>Topic</span>{topicLine}</div>
            <div className="top-pill phase-pill">
              <span>Phase</span>
              <strong>{phaseMajor}</strong>
              <small>{phaseMinor}</small>
            </div>
            <div className="top-pill"><span>Runtime</span>{runtimeStatus}</div>
          </section>
        </header>

        {page === "projects" && (
          <section className="panel view-panel">
            <h3>项目管理</h3>
            <div className="project-grid">
              <label className="field field-wide">
                <span>打开已有项目</span>
                <select
                  title="existing projects"
                  value={selectedProjectName}
                  onChange={(e) => setSelectedProjectName(e.target.value)}
                >
                  {projects.length === 0 && <option value="">(暂无项目)</option>}
                  {projects.map((name) => (
                    <option key={name} value={name}>{name}</option>
                  ))}
                </select>
              </label>
              <button className="btn" onClick={openExistingProject}>打开项目</button>
              <button className="btn" onClick={openSelectedProjectFolder}>打开项目文件夹</button>

              <label className="field field-wide">
                <span>新建项目名称</span>
                <input
                  title="new project name"
                  placeholder="例如 demo_preflow"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                />
              </label>
              <button className="btn major" onClick={createAndOpenProject}>新建并打开</button>
              <button className="btn danger" onClick={moveProjectToTrash}>移至回收站</button>
            </div>

            <div className="project-chips">
              {projects.map((name) => (
                <button
                  key={name}
                  className={name === selectedProjectName ? "project-chip active" : "project-chip"}
                  onClick={() => setSelectedProjectName(name)}
                >
                  {name}
                </button>
              ))}
            </div>
          </section>
        )}

        {page === "inputs" && (
          <section className="panel view-panel">
            <h3>输入参数（固定表单 + 实时更新）</h3>
            <div className="form-grid">
              <label className="field field-wide">
                <span>topic *</span>
                <textarea
                  className="topic-textarea"
                  title="topic"
                  placeholder="请输入论文主题"
                  value={inputsForm.topic}
                  onChange={(e) => updateForm("topic", e.target.value)}
                />
              </label>

              <label className="field">
                <span>language *</span>
                <select
                  title="language"
                  value={inputsForm.language}
                  onChange={(e) => updateForm("language", e.target.value === "Chinese" ? "Chinese" : "English")}
                >
                  <option value="English">English</option>
                  <option value="Chinese">Chinese</option>
                </select>
              </label>

              <label className="field">
                <span>model *</span>
                <input
                  title="model"
                  placeholder="模型名称"
                  value={inputsForm.model}
                  onChange={(e) => updateForm("model", e.target.value)}
                />
              </label>

              <label className="field">
                <span>max_review_rounds *</span>
                <input
                  title="max_review_rounds"
                  type="number"
                  min={1}
                  max={20}
                  value={inputsForm.max_review_rounds}
                  onChange={(e) => updateForm("max_review_rounds", toNumber(e.target.value, inputsForm.max_review_rounds, 1, 20))}
                />
              </label>

              <label className="field">
                <span>paper_search_limit *</span>
                <input
                  title="paper_search_limit"
                  type="number"
                  min={1}
                  max={300}
                  value={inputsForm.paper_search_limit}
                  onChange={(e) => updateForm("paper_search_limit", toNumber(e.target.value, inputsForm.paper_search_limit, 1, 300))}
                />
              </label>

              <label className="field">
                <span>openalex_api_key</span>
                <input
                  title="openalex_api_key"
                  placeholder="可为空"
                  value={inputsForm.openalex_api_key}
                  onChange={(e) => updateForm("openalex_api_key", e.target.value)}
                />
              </label>

              <label className="field">
                <span>ark_api_key</span>
                <input
                  title="ark_api_key"
                  placeholder="可为空"
                  value={inputsForm.ark_api_key}
                  onChange={(e) => updateForm("ark_api_key", e.target.value)}
                />
              </label>

              <label className="field">
                <span>base_url</span>
                <input
                  title="base_url"
                  placeholder="例如 http://localhost:8000/v1"
                  value={inputsForm.base_url}
                  onChange={(e) => updateForm("base_url", e.target.value)}
                />
              </label>

              <label className="field">
                <span>model_api_key</span>
                <input
                  title="model_api_key"
                  placeholder="可为空"
                  value={inputsForm.model_api_key}
                  onChange={(e) => updateForm("model_api_key", e.target.value)}
                />
              </label>
            </div>

            <div className="action-buttons">
              <button className="btn" onClick={refreshInputs}>重新加载参数</button>
              <button className="btn" onClick={() => void persistInputsForm(false)}>立即保存参数</button>
            </div>

            <h3>输入资料文件</h3>
            <div className="file-tabs">
              {editableFiles.map((path) => (
                <button
                  key={path}
                  className={path === selectedFilePath ? "tab active" : "tab"}
                  onClick={() => loadSelectedFile(path)}
                >
                  {displayInputFileName(path)}
                </button>
              ))}
            </div>

            <div className="line"><span>当前文件:</span> {displayInputFileName(selectedFilePath) || "-"}</div>
            <textarea
              title="selected input file editor"
              placeholder="在这里编辑所选输入文件"
              value={selectedFileContent}
              onChange={(e) => setSelectedFileContent(e.target.value)}
            />
            <div className="action-buttons">
              <button className="btn" onClick={() => loadSelectedFile(selectedFilePath)}>重新加载文件</button>
              <button className="btn major" onClick={saveSelectedFile}>保存当前文件</button>
            </div>
          </section>
        )}

        {page === "outputs" && (
          <section className="panel view-panel">
            <h3>输出查看</h3>
            <div className="tab-head">
              <button className={outputTab === "paper" ? "tab active" : "tab"} onClick={() => setOutputTab("paper")}>论文输出</button>
              <button className={outputTab === "pipeline" ? "tab active" : "tab"} onClick={() => setOutputTab("pipeline")}>架构与审稿输出</button>
            </div>

            {outputTab === "paper" && (
              <div className="output-pane">
                {paperOutputs.length === 0 && <div className="empty-tip">当前还没有正文输出。</div>}
                {paperOutputs.map((row, idx) => {
                  const label = `[${row.actual_order_index ?? idx}] ${row.major_title || ""} ${row.sub_chapter_id || ""} ${row.title || ""}`;
                  return (
                    <details key={`${row.sub_chapter_id || "na"}-${idx}`} className="fold-block">
                      <summary>{label.trim()}</summary>
                      <pre>{row.content || "(empty)"}</pre>
                    </details>
                  );
                })}
              </div>
            )}

            {outputTab === "pipeline" && (
              <div className="output-pane">
                <details className="fold-block">
                  <summary>检索词输出（Search Query Builder）</summary>
                  <pre>{prettyJson(searchQueries)}</pre>
                </details>

                <details className="fold-block">
                  <summary>架构输出（Architect）</summary>
                  <pre>{prettyJson(architectOutline)}</pre>
                </details>

                <details className="fold-block">
                  <summary>规划输出（Planner）</summary>
                  <pre>{prettyJson(plannerOutputs)}</pre>
                </details>

                <details className="fold-block">
                  <summary>总审稿输出（Overall Review）</summary>
                  <div className="json-box">
                    <h4>summary</h4>
                    <pre>{stateSnapshot?.overall_review_summary || "(no summary)"}</pre>
                    <h4>plans</h4>
                    <pre>{prettyJson(overallPlans)}</pre>
                  </div>
                </details>

                <details className="fold-block">
                  <summary>章节审稿输出（Major Review）</summary>
                  <pre>{prettyJson(majorReviewItems)}</pre>
                </details>
              </div>
            )}
          </section>
        )}

        {page === "workflow" && (
          <section className="panel view-panel workflow-grid">
            <section className="panel-block">
              <h3>动作控制</h3>
              <div className="line"><span>待处理动作:</span> {ACTION_LABELS[pendingAction] || pendingAction || "无"}</div>
              <div className="line"><span>动作提示:</span> {stateSnapshot?.pending_action_message || "-"}</div>
              {actionControl}
            </section>

            <section className="panel-block">
              <h3>流程视图</h3>
              <div className="progress-wrap">
                <progress className="progress-native" value={Math.round(flowProgress * 100)} max={100} />
                <small>{Math.round(flowProgress * 100)}%</small>
              </div>
              <div className="flow-list">
                {FLOW_STEPS.map((step, idx) => {
                  let status: "done" | "current" | "todo" = "todo";
                  if (flowKey === "done" || idx < flowIndex) {
                    status = "done";
                  } else if (idx === flowIndex) {
                    status = "current";
                  }
                  return (
                    <div key={step.key} className={`flow-item ${status}`}>
                      <div className="marker">{status === "done" ? "✓" : status === "current" ? "▶" : "○"}</div>
                      <div>
                        <div className="flow-title-row">
                          <strong>{step.title}</strong>
                          <span>{getFlowStatusLabel(status)}</span>
                        </div>
                        <p>{step.desc}</p>

                        {step.key === "drafting" && draftingProgressItems.length > 0 && (
                          <div className="drafting-progress-inline">
                            <div className="drafting-progress-head">
                              <strong>小节写作进度</strong>
                              <small>{nextStepsUpdatedAt || "-"}</small>
                            </div>
                            <div className="drafting-progress-list">
                              {draftingProgressItems.slice(0, 18).map((item, itemIdx) => (
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
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="line"><span>当前节点:</span> {currentNode || "-"}</div>
              <div className="line"><span>当前子步骤:</span> {phaseMinor}</div>
              <div className="line"><span>审稿轮次:</span> {(stateSnapshot?.review_round ?? 0)} / {(stateSnapshot?.max_review_rounds ?? 0)}</div>
              <div className="line"><span>完成小节:</span> {stateSnapshot?.completed_section_count ?? 0} | 待改写 {stateSnapshot?.pending_rewrite_count ?? 0}</div>

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
      </main>
    </div>
  );
}

export default App;
