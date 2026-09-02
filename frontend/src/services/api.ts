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
  hostname: string | null;
  custom_name: string | null;
  unit_name: string | null;
  sector_name: string | null;
  manufacturer: string | null;
  model: string | null;
  status: string;
  source: string | null;
  page_count: number | null;
  page_count_source: string | null;
  page_count_confidence: number | null;
  page_count_confirmed: boolean;
  cost_per_page: number | null;
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

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return request<DashboardSummary>("/api/v1/dashboard/summary");
}

export async function getDashboardPrinters(): Promise<DashboardPrinter[]> {
  return request<DashboardPrinter[]>("/api/v1/dashboard/printers");
}

export async function updatePrinterCustomName(
  printerUuid: string,
  customName: string | null,
): Promise<{ custom_name: string | null }> {
  return request<{ custom_name: string | null }>(
    `/api/v1/printers/${printerUuid}/custom-name`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ custom_name: customName }),
    },
  );
}

export async function updatePrinterCost(
  printerUuid: string,
  costPerPage: number | null,
): Promise<{ cost_per_page: number | null }> {
  return request<{ cost_per_page: number | null }>(
    `/api/v1/printers/${printerUuid}/cost`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cost_per_page: costPerPage }),
    },
  );
}

export async function updatePrinterOrganization(
  printerUuid: string,
  unitName: string | null,
  sectorName: string | null,
): Promise<{ unit_name: string | null; sector_name: string | null }> {
  return request<{ unit_name: string | null; sector_name: string | null }>(
    `/api/v1/printers/${printerUuid}/organization`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ unit_name: unitName, sector_name: sectorName }),
    },
  );
}

export async function getOperationalAlerts(
  status: "open" | "acknowledged" | "resolved" | "all" = "open",
): Promise<OperationalAlert[]> {
  return request<OperationalAlert[]>(`/api/v1/alerts?status=${status}&limit=50`);
}

export async function acknowledgeOperationalAlert(
  alertId: number,
): Promise<OperationalAlert> {
  return request<OperationalAlert>(`/api/v1/alerts/${alertId}/acknowledge`, { method: "POST" });
}

export type OrganizationUnit = {
  id: number;
  uuid: string;
  name: string;
  active: boolean;
  created_at: string;
};

export type OrganizationSector = {
  id: number;
  uuid: string;
  unit_id: number;
  name: string;
  active: boolean;
  created_at: string;
};

export async function getOrganizationUnits(): Promise<OrganizationUnit[]> {
  return request<OrganizationUnit[]>("/api/v1/organization/units");
}

export async function createOrganizationUnit(name: string): Promise<OrganizationUnit> {
  return request<OrganizationUnit>(
    "/api/v1/organization/units",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    },
  );
}

export async function getOrganizationSectors(unitId?: number): Promise<OrganizationSector[]> {
  const query = unitId === undefined ? "" : `?unit_id=${unitId}`;
  return request<OrganizationSector[]>(`/api/v1/organization/sectors${query}`);
}

export async function createOrganizationSector(
  unitId: number,
  name: string,
): Promise<OrganizationSector> {
  return request<OrganizationSector>(
    "/api/v1/organization/sectors",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ unit_id: unitId, name }),
    },
  );
}

export { API_BASE_URL };

export type MeProfile = {
  id: number;
  name: string;
  email: string;
  role: string;
  company_id: number;
  company_name: string;
};

export type ControlCenterCompany = {
  id: number;
  uuid: string;
  name: string;
  plan: string;
  active: boolean;
  agent_online: boolean;
  agent_status: string | null;
  agent_version: string | null;
  agent_last_seen: string | null;
  active_printers: number;
  online_printers: number;
  offline_printers: number;
  alerts: number;
};

export type ControlCenterOverview = {
  generated_at: string;
  companies_total: number;
  companies_active: number;
  agents_online: number;
  active_printers: number;
  open_alerts: number;
  companies: ControlCenterCompany[];
};

export async function getMe(): Promise<MeProfile> {
  return request<MeProfile>("/api/v1/auth/me");
}

export async function getControlCenterOverview(): Promise<ControlCenterOverview> {
  return request<ControlCenterOverview>("/api/v1/control-center/overview");
}

export type ControlCenterClientCreated = {
  company_id: number;
  company_uuid: string;
  company_name: string;
  plan: string;
  user_id: number;
  responsible_name: string;
  email: string;
  temporary_password: string;
  agent_token: string;
};

export async function createControlCenterClient(
  payload: { company_name: string; responsible_name: string; email: string },
): Promise<ControlCenterClientCreated> {
  return request<ControlCenterClientCreated>(
    "/api/v1/control-center/clients",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  );
}

export type UsageReportRow = {
  printer_uuid: string;
  display_name: string;
  ip: string | null;
  hostname: string | null;
  manufacturer: string | null;
  model: string | null;
  serial: string | null;
  unit_name: string | null;
  sector_name: string | null;
  first_usage_date: string | null;
  last_usage_date: string | null;
  opening_page_count: number | null;
  closing_page_count: number | null;
  pages_printed: number;
  anomaly_count: number;
  last_anomaly_type: string | null;
  cost_per_page: number;
  estimated_cost: number;
  cost_source: "company" | "printer";
};

export type UsageReportFilters = {
  startDate: string;
  endDate: string;
  printerUuid?: string;
  unitName?: string;
  sectorName?: string;
};

function usageReportQuery(filters: UsageReportFilters): string {
  const params = new URLSearchParams();
  params.set("start_date", filters.startDate);
  params.set("end_date", filters.endDate);
  if (filters.printerUuid) params.set("printer_uuid", filters.printerUuid);
  if (filters.unitName) params.set("unit_name", filters.unitName);
  if (filters.sectorName) params.set("sector_name", filters.sectorName);
  return params.toString();
}

export async function getUsageReport(
  filters: UsageReportFilters,
): Promise<UsageReportRow[]> {
  return request<UsageReportRow[]>(`/api/v1/usage/report?${usageReportQuery(filters)}`);
}

export async function downloadUsageReport(
  format: "xlsx" | "pdf",
  filters: UsageReportFilters,
): Promise<Blob> {
  const token = localStorage.getItem("printflow_token");
  const response = await fetch(
    `${API_BASE_URL}/api/v1/usage/export.${format}?${usageReportQuery(filters)}`,
    {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    },
  );

  if (!response.ok) {
    throw new Error(`Não foi possível gerar o relatório (${response.status}).`);
  }
  return response.blob();
}
