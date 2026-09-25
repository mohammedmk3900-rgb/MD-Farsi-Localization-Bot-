export type OperationStatus = "ok" | "failed" | "skipped";

export interface OperationResult {
  schema_version: number;
  operation: string;
  status: OperationStatus;
  generated_at: string;
}

export function isOperationResult(value: unknown): value is OperationResult {
  if (!value || typeof value !== "object") return false;
  const item = value as Record<string, unknown>;
  return typeof item.schema_version === "number"
    && typeof item.operation === "string"
    && (item.status === "ok" || item.status === "failed" || item.status === "skipped")
    && typeof item.generated_at === "string";
}
