import type {
  ActionResult,
  EditableFilesPayload,
  FilePayload,
  InputsPayload,
  LogsPayload,
  LogMode,
  ProjectFolderOpenResult,
  ProjectOpenResult,
  ProjectTrashResult,
  ProjectsPayload,
  WorkflowStateSnapshot,
} from "./types";

async function requestJson<T>(url: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {};
  if (init?.body !== undefined && init?.body !== null) {
    headers["Content-Type"] = "application/json";
  }
  if (init?.headers) {
    Object.assign(headers, init.headers as Record<string, string>);
  }

  const response = await fetch(url, {
    ...init,
    headers: Object.keys(headers).length > 0 ? headers : undefined,
  });

  const data = (await response.json()) as T;
  return data;
}

export async function fetchState(baseUrl: string): Promise<WorkflowStateSnapshot> {
  return requestJson<WorkflowStateSnapshot>(`${baseUrl}/api/state?_=${Date.now()}`);
}

export async function fetchInputs(baseUrl: string): Promise<InputsPayload> {
  return requestJson<InputsPayload>(`${baseUrl}/api/inputs?_=${Date.now()}`);
}

export async function saveInputs(baseUrl: string, content: string): Promise<InputsPayload> {
  return requestJson<InputsPayload>(`${baseUrl}/api/inputs`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export async function fetchLogs(baseUrl: string, mode: LogMode): Promise<LogsPayload> {
  return requestJson<LogsPayload>(`${baseUrl}/api/logs?mode=${mode}&limit=120&_=${Date.now()}`);
}

export async function postAction(baseUrl: string, payload: Record<string, unknown>): Promise<ActionResult> {
  return requestJson<ActionResult>(`${baseUrl}/api/action`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchEditableFiles(baseUrl: string): Promise<EditableFilesPayload> {
  return requestJson<EditableFilesPayload>(`${baseUrl}/api/editable-files?_=${Date.now()}`);
}

export async function fetchInputFile(baseUrl: string, path: string): Promise<FilePayload> {
  return requestJson<FilePayload>(`${baseUrl}/api/input-file?path=${encodeURIComponent(path)}&_=${Date.now()}`);
}

export async function saveInputFile(baseUrl: string, path: string, content: string): Promise<FilePayload> {
  return requestJson<FilePayload>(`${baseUrl}/api/input-file`, {
    method: "POST",
    body: JSON.stringify({ path, content }),
  });
}

export async function fetchProjects(baseUrl: string): Promise<ProjectsPayload> {
  return requestJson<ProjectsPayload>(`${baseUrl}/api/projects?_=${Date.now()}`);
}

export async function openProject(baseUrl: string, projectName: string): Promise<ProjectOpenResult> {
  return requestJson<ProjectOpenResult>(`${baseUrl}/api/project/open`, {
    method: "POST",
    body: JSON.stringify({ project_name: projectName }),
  });
}

export async function trashProject(baseUrl: string, projectName: string): Promise<ProjectTrashResult> {
  return requestJson<ProjectTrashResult>(`${baseUrl}/api/project/trash`, {
    method: "POST",
    body: JSON.stringify({ project_name: projectName }),
  });
}

export async function openProjectFolder(baseUrl: string, projectName: string): Promise<ProjectFolderOpenResult> {
  return requestJson<ProjectFolderOpenResult>(`${baseUrl}/api/project/open-folder`, {
    method: "POST",
    body: JSON.stringify({ project_name: projectName }),
  });
}

export async function rollbackSnapshot(baseUrl: string, statePath: string): Promise<ActionResult> {
  return requestJson<ActionResult>(`${baseUrl}/api/snapshot/rollback`, {
    method: "POST",
    body: JSON.stringify({ state_path: statePath }),
  });
}
