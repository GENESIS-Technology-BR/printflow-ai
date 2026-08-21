const API_BASE_URL = (
  import.meta.env.VITE_API_URL ||
  "https://printflow-api-genesis.onrender.com"
).replace(/\/$/, "");

export type DashboardSummary = {
  total_printers: number;
  active_printers: number;
  inactive_printers: number;
  online: number;
  offline: number;
  unknown: number;
  alerts: number;
  total_pages: number;
  page_count_known: number;
  page_count_unknown: number;
  health_average: number;
  manufacturers: Record<string, number>;
  generated_at: string;
  agent: {
    online: boolean;
    status: string | null;
    name: string | null;
    version: string | null;
    last_seen: string | null;
    last_error: string | null;
  };
};

export type DashboardPrinter = {
  id: number | null;
  uuid: string | null;
  ip: string | null;
  name: string;
  manufacturer: string | null;
  model: string | null;
  status: string;
  source: string | null;
  page_count: number | null;
  page_count_source: string | null;
  page_count_confidence: number | null;
  page_count_confirmed: boolean;
  serial: string | null;
  serial_source: string | null;
  serial_confidence: number | null;
  serial_confirmed: boolean;
  toner_percent: number | null;
  active: boolean;
  last_seen: string | null;
  created_at: string | null;
  health_score: number;
  health_status: string;
  health_reasons: string[];
};

export type OperationalAlert = {
  id: number;
  printer_id: number | null;
  event_key: string;
  category: string;
  severity: "critical" | "warning" | "info";
  title: string;
  description: string;
  status: "open" | "acknowledged" | "resolved";
  opened_at: string;
  last_seen_at: string;
  resolved_at: string | null;
  acknowledged_at: string | null;
  acknowledged_by: number | null;
};

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const token = localStorage.getItem("printflow_token");
  const response = await fetch(
    `${API_BASE_URL}${endpoint}`,
    {
      ...options,
      headers: {
        Accept: "application/json",
        ...options.headers,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    },
  );

  if (!response.ok) {
    throw new Error(
      `A API respondeu com HTTP ${response.status}.`,
    );
  }

  return response.json() as Promise<T>;
}

export async function getDashboardSummary():
Promise<DashboardSummary> {
  return request<DashboardSummary>(
    "/api/v1/dashboard/summary",
  );
}

export async function getDashboardPrinters():
Promise<DashboardPrinter[]> {
  return request<DashboardPrinter[]>(
    "/api/v1/dashboard/printers",
  );
}

export async function getOperationalAlerts(
  status: "open" | "acknowledged" | "resolved" | "all" = "open",
): Promise<OperationalAlert[]> {
  return request<OperationalAlert[]>(
    `/api/v1/alerts?status=${status}&limit=50`,
  );
}

export async function acknowledgeOperationalAlert(
  alertId: number,
): Promise<OperationalAlert> {
  return request<OperationalAlert>(
    `/api/v1/alerts/${alertId}/acknowledge`,
    { method: "POST" },
  );
}

export { API_BASE_URL };
