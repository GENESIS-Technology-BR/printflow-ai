const API_BASE_URL = (
  import.meta.env.VITE_API_URL ||
  "https://printflow-api-genesis.onrender.com"
).replace(/\/$/, "");

export type DashboardSummary = {
  total_printers: number;
  active_printers: number;
  online: number;
  offline: number;
  unknown: number;
  alerts: number;
  total_pages: number;
  health_average: number;
  manufacturers: Record<string, number>;
  generated_at: string;
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
  page_count: number;
  active: boolean;
  last_seen: string | null;
  created_at: string | null;
  health_score: number;
  health_status: string;
  health_reasons: string[];
};

async function request<T>(
  endpoint: string,
): Promise<T> {
  const response = await fetch(
    `${API_BASE_URL}${endpoint}`,
    {
      headers: {
        Accept: "application/json",
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

export { API_BASE_URL };
