import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, ProcurementRequest, Requirement } from "../api/client";

const CATEGORIES = ["technical", "compliance", "pricing", "delivery", "general"];

export default function RequestsList() {
  const [requests, setRequests] = useState<ProcurementRequest[]>([]);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [requirements, setRequirements] = useState<Requirement[]>([
    { text: "", category: "technical", is_mandatory: true, weight: 1.0 },
  ]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const load = () => api.listRequests().then(setRequests).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  const updateReq = (i: number, patch: Partial<Requirement>) => {
    setRequirements((rs) => rs.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  };
  const addReq = () => setRequirements((rs) => [...rs, { text: "", category: "technical", is_mandatory: true, weight: 1.0 }]);
  const removeReq = (i: number) => setRequirements((rs) => rs.filter((_, idx) => idx !== i));

  const onCreate = async () => {
    const cleanReqs = requirements.filter((r) => r.text.trim());
    if (!title.trim() || cleanReqs.length === 0) {
      setError("Title and at least one requirement are needed.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.createRequest({ title, description: description || undefined, requirements: cleanReqs });
      setTitle(""); setDescription("");
      setRequirements([{ text: "", category: "technical", is_mandatory: true, weight: 1.0 }]);
      setShowForm(false);
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h2 className="page-title">Procurement Requests</h2>
      <p className="page-subtitle">Define requirements, upload vendor proposals, then run the multi-agent evaluation.</p>

      <div className="card">
        <div className="flex-between">
          <div className="section-title">All Requests ({requests.length})</div>
          <button className="btn secondary" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Cancel" : "+ New Request"}
          </button>
        </div>

        {showForm && (
          <div className="mt-16">
            <label>Title</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Office IT Equipment Procurement" />
            <label>Description</label>
            <textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Short context for this procurement" />

            <label style={{ marginTop: 18 }}>Requirements</label>
            {requirements.map((r, i) => (
              <div key={i} className="flex" style={{ marginBottom: 8, alignItems: "flex-start" }}>
                <input
                  style={{ flex: 3 }}
                  value={r.text}
                  onChange={(e) => updateReq(i, { text: e.target.value })}
                  placeholder="e.g. Vendor must be ISO 9001 certified"
                />
                <select style={{ flex: 1 }} value={r.category} onChange={(e) => updateReq(i, { category: e.target.value })}>
                  {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
                <button className="btn secondary" onClick={() => removeReq(i)} disabled={requirements.length === 1}>×</button>
              </div>
            ))}
            <button className="btn secondary" onClick={addReq}>+ Add requirement</button>

            {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
            <div className="mt-16">
              <button className="btn" onClick={onCreate} disabled={busy}>{busy ? "Creating…" : "Create Procurement Request"}</button>
            </div>
          </div>
        )}
      </div>

      {requests.length === 0 ? (
        <div className="card empty-state">No procurement requests yet. Create one above.</div>
      ) : (
        <div className="card">
          <table>
            <thead><tr><th>Title</th><th>Status</th><th>Created</th><th></th></tr></thead>
            <tbody>
              {requests.map((r) => (
                <tr key={r.id}>
                  <td>{r.title}</td>
                  <td><span className={`badge ${r.status === "CLOSED" ? "approved" : r.status === "DECIDED" ? "partial" : "pending"}`}>{r.status}</span></td>
                  <td className="muted">{new Date(r.created_at).toLocaleDateString()}</td>
                  <td><Link to={`/requests/${r.id}`}>Open →</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
