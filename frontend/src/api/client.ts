const API_BASE = import.meta.env.VITE_API_URL || "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* no-op */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export interface Vendor {
  id: string;
  name: string;
  contact_email: string | null;
  is_synthetic_demo: boolean;
  created_at: string;
}

export interface Requirement {
  text: string;
  category: string;
  is_mandatory: boolean;
  weight: number;
}

export interface ProcurementRequest {
  id: string;
  title: string;
  description: string | null;
  status: string;
  scoring_weights: Record<string, number>;
  created_at: string;
}

export interface VendorScoreRow {
  vendor_id: string;
  vendor_name: string;
  rank: number;
  weighted_total: number;
  requirement_match_score: number;
  pricing_score: number;
  delivery_score: number;
  compliance_score: number;
  risk_score: number;
  technical_score: number;
  breakdown_json: Record<string, unknown>;
}

export interface AgentExecution {
  id: string;
  agent_name: string;
  vendor_id: string | null;
  status: string;
  llm_enhanced: boolean;
  duration_ms: number;
  error_message: string | null;
  output_json: Record<string, unknown>;
  started_at: string;
  finished_at: string;
}

export interface Recommendation {
  id: string;
  ranked_vendor_ids: string[];
  summary: string;
  evidence_refs: { type: string; requirement: string; source: string }[];
  limitations: string;
  llm_enhanced: boolean;
  approval: { status: string; reviewer_name: string | null; comments: string | null } | null;
}

export interface DashboardSummary {
  total_vendors_evaluated: number;
  active_procurement_requests: number;
  pending_human_reviews: number;
  risk_distribution: Record<string, number>;
  recent_evaluations: { vendor_name: string; request_title: string; weighted_total: number; computed_at: string }[];
  vendor_performance_summary: { vendor_name: string; avg_score: number; evaluations: number }[];
  llm_status: { provider: string; enabled: boolean; mode: string };
}

export const api = {
  health: () => request<{ status: string; llm: unknown }>("/health"),

  listVendors: () => request<Vendor[]>("/vendors"),
  createVendor: (data: { name: string; contact_email?: string; is_synthetic_demo?: boolean }) =>
    request<Vendor>("/vendors", { method: "POST", body: JSON.stringify(data) }),
  getVendorDocuments: (vendorId: string) => request<any[]>(`/vendors/${vendorId}/documents`),

  listRequests: () => request<ProcurementRequest[]>("/requests"),
  getRequest: (id: string) => request<any>(`/requests/${id}`),
  createRequest: (data: { title: string; description?: string; requirements: Requirement[]; scoring_weights?: Record<string, number> }) =>
    request<ProcurementRequest>("/requests", { method: "POST", body: JSON.stringify(data) }),
  evaluateRequest: (id: string) => request<any>(`/requests/${id}/evaluate`, { method: "POST" }),
  getComparison: (id: string) => request<VendorScoreRow[]>(`/requests/${id}/comparison`),
  getAgentExecutions: (id: string) => request<AgentExecution[]>(`/requests/${id}/agent-executions`),
  getRecommendation: (id: string) => request<Recommendation>(`/requests/${id}/recommendation`),

  uploadDocument: (file: File, vendorId: string, requestId: string, docType = "proposal") => {
    const form = new FormData();
    form.append("file", file);
    form.append("vendor_id", vendorId);
    form.append("request_id", requestId);
    form.append("doc_type", docType);
    return fetch(`${API_BASE}/documents/upload`, { method: "POST", body: form }).then((r) => {
      if (!r.ok) throw new Error(`Upload failed: ${r.status}`);
      return r.json();
    });
  },

  listPendingReviews: () => request<any[]>("/review/pending"),
  decideReview: (approvalId: string, data: { status: string; reviewer_name?: string; comments?: string }) =>
    request<any>(`/review/${approvalId}/decide`, { method: "POST", body: JSON.stringify(data) }),
  getAuditLog: (requestId: string) => request<any[]>(`/review/audit-log/${requestId}`),

  getDashboard: () => request<DashboardSummary>("/dashboard/summary"),

  reportJsonUrl: (requestId: string) => `${API_BASE}/reports/${requestId}/json`,
  reportPdfUrl: (requestId: string) => `${API_BASE}/reports/${requestId}/pdf`,
};
