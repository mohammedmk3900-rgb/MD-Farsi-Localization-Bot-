export type TaskStatus = "available" | "in_progress" | "review" | "done" | "cancelled";
export type MissionStatus = "open" | "active" | "completed" | "cancelled";

export interface TaskSummary {
  total: number;
  by_status: Record<TaskStatus, number>;
  review_queue: number;
}

export interface MissionSummary {
  total: number;
  open: number;
  active: number;
  completed: number;
  cancelled: number;
}

export interface CommandCenterStatus {
  tasks: TaskSummary;
  missions: MissionSummary;
  events: number;
  glossary_terms: number;
  review_pending: number;
  health: { status: string; checks: Record<string, string> };
}

export interface MissionRecord {
  id: number;
  title: string;
  scope: string;
  priority: string;
  reward: number;
  status: MissionStatus;
  task_id: number | null;
  created_at: string;
}

export interface Notification {
  id: number;
  recipient: string;
  event_type: string;
  message: string;
  created_at: string;
  delivered: boolean;
}

export interface EngineHealth {
  status: string;
  queued: number;
  running: number;
  handled: number;
  workers: number;
}

export interface WorkerJob {
  id: string;
  type: string;
  payload: Record<string, unknown>;
  status: "queued" | "running" | "completed" | "failed";
  created_at: string;
  started_at?: string;
  ended_at?: string;
  result?: Record<string, unknown>;
  error?: string;
}
