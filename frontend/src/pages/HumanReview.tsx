import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";

interface PendingItem {
  approval_id: string;
  recommendation_id: string;
  request_id: string;
  request_title: string;
  summary: string;
  created_at: string;
}

export default function HumanReview() {
  const [pending, setPending] = useState<PendingItem[]>([]);
  const [reviewer, setReviewer] = useState("");
  const [comments, setComments] = useState<Record<string, string>>({});
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => api.listPendingReviews().then(setPending).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  const decide = async (approvalId: string, status: "APPROVED" | "REJECTED" | "MODIFIED") => {
    setBusyId(approvalId);
    setError(null);
    try {
      await api.decideReview(approvalId, { status, reviewer_name: reviewer || undefined, comments: comments[approvalId] });
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div>
      <h2 className="page-title">Human Review</h2>
      <p className="page-subtitle">Every recommendation requires explicit human approval before a procurement decision is final.</p>

      <div className="card">
        <label>Your name (reviewer)</label>
        <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} placeholder="e.g. Ayaz Alam" style={{ maxWidth: 300 }} />
      </div>

      {error && <div className="card" style={{ color: "var(--danger)" }}>{error}</div>}

      {pending.length === 0 ? (
        <div className="card empty-state">No pending reviews. Run an evaluation on a procurement request to generate one.</div>
      ) : (
        pending.map((p) => (
          <div className="card" key={p.approval_id}>
            <div className="flex-between">
              <div className="section-title">{p.request_title}</div>
              <Link to={`/requests/${p.request_id}`}>View full evaluation →</Link>
            </div>
            <p>{p.summary}</p>
            <label>Comments (optional)</label>
            <textarea
              rows={2}
              value={comments[p.approval_id] || ""}
              onChange={(e) => setComments((c) => ({ ...c, [p.approval_id]: e.target.value }))}
              placeholder="Add any notes for the audit trail"
            />
            <div className="flex mt-16">
              <button className="btn" onClick={() => decide(p.approval_id, "APPROVED")} disabled={busyId === p.approval_id}>
                ✓ Approve
              </button>
              <button className="btn secondary" onClick={() => decide(p.approval_id, "MODIFIED")} disabled={busyId === p.approval_id}>
                Request Modification
              </button>
              <button className="btn danger" onClick={() => decide(p.approval_id, "REJECTED")} disabled={busyId === p.approval_id}>
                ✗ Reject
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
