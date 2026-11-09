import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, Vendor, AgentExecution, Recommendation } from "../api/client";

export default function RequestDetail() {
  const { id } = useParams<{ id: string }>();
  const [req, setReq] = useState<any>(null);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [selectedVendor, setSelectedVendor] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [evaluating, setEvaluating] = useState(false);
  const [executions, setExecutions] = useState<AgentExecution[]>([]);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedExec, setExpandedExec] = useState<string | null>(null);

  const load = () => {
    if (!id) return;
    api.getRequest(id).then(setReq).catch((e) => setError(e.message));
    api.listVendors().then(setVendors);
    api.getAgentExecutions(id).then(setExecutions).catch(() => {});
    api.getRecommendation(id).then(setRecommendation).catch(() => setRecommendation(null));
  };

  useEffect(() => { load(); }, [id]);

  const onUpload = async () => {
    if (!file || !selectedVendor || !id) return;
    setUploading(true);
    setError(null);
    try {
      await api.uploadDocument(file, selectedVendor, id);
      setFile(null);
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  const onEvaluate = async () => {
    if (!id) return;
    setEvaluating(true);
    setError(null);
    try {
      await api.evaluateRequest(id);
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setEvaluating(false);
    }
  };

  if (!req) return <div className="empty-state">{error || "Loading…"}</div>;

  return (
    <div>
      <h2 className="page-title">{req.title}</h2>
      <p className="page-subtitle">{req.description || "No description provided."} &nbsp; <span className="pill">{req.status}</span></p>

      <div className="card">
        <div className="section-title">Requirements ({req.requirements.length})</div>
        <table>
          <thead><tr><th>Requirement</th><th>Category</th><th>Mandatory</th></tr></thead>
          <tbody>
            {req.requirements.map((r: any) => (
              <tr key={r.id}>
                <td>{r.text}</td>
                <td><span className="pill">{r.category}</span></td>
                <td>{r.is_mandatory ? "Yes" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <div className="section-title">Upload Vendor Proposal</div>
        <div className="grid grid-2">
          <div>
            <label>Vendor</label>
            <select value={selectedVendor} onChange={(e) => setSelectedVendor(e.target.value)}>
              <option value="">Select a vendor…</option>
              {vendors.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
            </select>
          </div>
          <div>
            <label>Document (PDF, DOCX, TXT, CSV)</label>
            <input type="file" accept=".pdf,.docx,.txt,.csv,.md" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </div>
        </div>
        {vendors.length === 0 && <p className="muted mt-8"><Link to="/vendors">Add a vendor first →</Link></p>}
        {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
        <button className="btn mt-16" onClick={onUpload} disabled={uploading || !file || !selectedVendor}>
          {uploading ? "Uploading…" : "Upload & Extract"}
        </button>
      </div>

      <div className="card">
        <div className="section-title">Documents Uploaded ({req.documents.length})</div>
        {req.documents.length === 0 ? (
          <p className="muted">No documents uploaded yet.</p>
        ) : (
          <ul>
            {req.documents.map((d: any) => <li key={d.id}>{d.filename}</li>)}
          </ul>
        )}
        <div className="flex" style={{ marginTop: 14 }}>
          <button className="btn" onClick={onEvaluate} disabled={evaluating || req.documents.length === 0}>
            {evaluating ? "Running multi-agent evaluation…" : "▶ Run AI Evaluation"}
          </button>
          {executions.length > 0 && <Link to={`/requests/${id}/comparison`} className="btn secondary">View Comparison →</Link>}
        </div>
      </div>

      {executions.length > 0 && (
        <div className="card">
          <div className="section-title">AI Evaluation Workspace — Agent Execution Log</div>
          <table>
            <thead><tr><th>Agent</th><th>Scope</th><th>Status</th><th>LLM</th><th>Duration</th><th></th></tr></thead>
            <tbody>
              {executions.map((e) => (
                <>
                  <tr key={e.id}>
                    <td>{e.agent_name}</td>
                    <td className="muted">{e.vendor_id ? vendors.find((v) => v.id === e.vendor_id)?.name || e.vendor_id.slice(0, 8) : "request-level"}</td>
                    <td><span className={`badge ${e.status === "SUCCESS" ? "success" : "failed"}`}>{e.status}</span></td>
                    <td>{e.llm_enhanced ? <span className="pill">LLM</span> : <span className="pill">rule-based</span>}</td>
                    <td className="muted">{e.duration_ms}ms</td>
                    <td>
                      <button className="btn secondary" onClick={() => setExpandedExec(expandedExec === e.id ? null : e.id)}>
                        {expandedExec === e.id ? "Hide" : "Inspect"}
                      </button>
                    </td>
                  </tr>
                  {expandedExec === e.id && (
                    <tr>
                      <td colSpan={6}>
                        <pre style={{ background: "var(--surface-2)", padding: 12, borderRadius: 8, overflowX: "auto", fontSize: 12 }}>
                          {JSON.stringify(e.output_json, null, 2)}
                        </pre>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {recommendation && (
        <div className="card">
          <div className="section-title">Decision Recommendation</div>
          <p>{recommendation.summary}</p>
          <p className="muted" style={{ fontStyle: "italic" }}>{recommendation.limitations}</p>
          {recommendation.approval && (
            <p>Review status: <span className={`badge ${recommendation.approval.status.toLowerCase()}`}>{recommendation.approval.status}</span></p>
          )}
          <div className="flex mt-16">
            <a className="btn secondary" href={api.reportPdfUrl(id!)} target="_blank">Download PDF Report</a>
            <a className="btn secondary" href={api.reportJsonUrl(id!)} target="_blank">Download JSON Report</a>
            <Link className="btn secondary" to="/review">Go to Human Review →</Link>
          </div>
        </div>
      )}
    </div>
  );
}
