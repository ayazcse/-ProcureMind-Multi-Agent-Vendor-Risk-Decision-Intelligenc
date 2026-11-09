import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, DashboardSummary } from "../api/client";

export default function Dashboard() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getDashboard().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="card">Could not load dashboard: {error}</div>;
  if (!data) return <div className="empty-state">Loading…</div>;

  return (
    <div>
      <h2 className="page-title">Dashboard</h2>
      <p className="page-subtitle">
        Live metrics from the database — nothing on this page is hardcoded.{" "}
        <span className="pill">LLM mode: {data.llm_status.mode}</span>
      </p>

      <div className="grid grid-4">
        <div className="card">
          <div className="stat-value">{data.total_vendors_evaluated}</div>
          <div className="stat-label">Total Vendors Evaluated</div>
        </div>
        <div className="card">
          <div className="stat-value">{data.active_procurement_requests}</div>
          <div className="stat-label">Active Procurement Requests</div>
        </div>
        <div className="card">
          <div className="stat-value">{data.pending_human_reviews}</div>
          <div className="stat-label">Pending Human Reviews</div>
        </div>
        <div className="card">
          <div className="stat-value">
            {Object.values(data.risk_distribution).reduce((a, b) => a + b, 0)}
          </div>
          <div className="stat-label">Risk Assessments Logged</div>
        </div>
      </div>

      <div className="grid grid-2 mt-16">
        <div className="card">
          <div className="section-title">Risk Distribution</div>
          {Object.keys(data.risk_distribution).length === 0 ? (
            <p className="muted">No risk assessments yet.</p>
          ) : (
            Object.entries(data.risk_distribution).map(([level, count]) => (
              <div key={level} className="flex-between mt-8">
                <span className={`badge ${level.toLowerCase()}`}>{level}</span>
                <span>{count}</span>
              </div>
            ))
          )}
        </div>

        <div className="card">
          <div className="section-title">Vendor Performance Summary</div>
          {data.vendor_performance_summary.length === 0 ? (
            <p className="muted">No evaluations yet.</p>
          ) : (
            <table>
              <thead>
                <tr><th>Vendor</th><th>Avg Score</th><th>Evaluations</th></tr>
              </thead>
              <tbody>
                {data.vendor_performance_summary.map((v) => (
                  <tr key={v.vendor_name}>
                    <td>{v.vendor_name}</td>
                    <td>{v.avg_score}</td>
                    <td>{v.evaluations}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card mt-16">
        <div className="section-title">Recent Evaluations</div>
        {data.recent_evaluations.length === 0 ? (
          <div className="empty-state">
            No evaluations yet. <Link to="/requests">Create a procurement request</Link> to get started.
          </div>
        ) : (
          <table>
            <thead>
              <tr><th>Vendor</th><th>Request</th><th>Score</th><th>Computed</th></tr>
            </thead>
            <tbody>
              {data.recent_evaluations.map((e, i) => (
                <tr key={i}>
                  <td>{e.vendor_name}</td>
                  <td>{e.request_title}</td>
                  <td>{e.weighted_total}</td>
                  <td className="muted">{new Date(e.computed_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
