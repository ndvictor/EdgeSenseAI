import type { JsonRecord, JsonValue } from "@/lib/edgesense/types";

export function asObject(value: JsonValue | undefined | null): JsonRecord | null {
  if (value && typeof value === "object" && !Array.isArray(value)) return value as JsonRecord;
  return null;
}

export function asArray(value: JsonValue | JsonValue[] | undefined | null): JsonValue[] {
  return Array.isArray(value) ? value : [];
}

export function getValue(source: JsonRecord | null | undefined, keys: string[]): JsonValue | undefined {
  if (!source) return undefined;
  for (const key of keys) {
    const value = source[key];
    if (value !== undefined && value !== null && value !== "") return value;
  }
  return undefined;
}

export function display(value: JsonValue | undefined | null): string {
  if (value === undefined || value === null || value === "") return "Unavailable";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : "Unavailable";
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

export function count(value: JsonValue[] | undefined | null): string {
  return Array.isArray(value) ? String(value.length) : "Unavailable";
}

export function formatDateTime(value: string | undefined | null): string {
  if (!value) return "Unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}
