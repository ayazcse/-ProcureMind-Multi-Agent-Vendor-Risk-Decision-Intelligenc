import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { api, VendorScoreRow } from "../api/client";

const DIMENSIONS: { key: keyof VendorScoreRow; label: string }[] = [
  { key: "requirement_match_score", label: "Requirement Match" },
  { key: "pricing_score", label: "Pricing" },
  { key: "delivery_score", label: "Delivery" },
  { key: "compliance_score", label: "Compliance" },
  { key: "risk_score", label: "Risk (inverted)" },
  { key: "technical_score", label: "Technical" },
];

export default function Comparison() {
  const { id } = useParams<{ id: string }>();
  const [rows, setRows] = useState<VendorScoreRow[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    api.getComparison(id).then(setRows).catch((e) => setError(e.message));
  }, [id]);

  if (error) return <div className="card">{error}</div>;
  if (rows.length === 0) return <div className="empty-state">No comparison data yet — run an evaluation first.</div>;

  return (
    <div>
      <h2 className="page-title">Vendor Comparison</h2>
      <p className="page-subtitle">
        <Link to={`/requests/${id}`}>← Back to request</Link>
      </p>

      <div className="card">
        <div className="section-title">Weighted Total Score by Vendor</div>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={rows}>
            <CartesianGrid strokeDasharray="3 3" stroke="#253046" />
            <XAxis dataKey="vendor_name" stroke="#8d9ab3" fontSize={12} />
            <YAxis stroke="#8d9ab3" fontSize={12} domain={[0, 100]} />
            <Tooltip contentStyle={{ background: "#1a2232", border: "1px solid #253046" }} />
            <Bar dataKey="weighted_total" fill="#5b8cff" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <div className="section-title">Side-by-Side Scoring Breakdown</div>
        <table>
          <thead>
            <tr>
              <th>Vendor</th>
              <th>Rank</th>
              {DIMENSIONS.map((d) => <th key={d.key as string}>{d.label}</th>)}
              <th>Weighted Total</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.vendor_id}>
                <td>{r.vendor_name}</td>
                <td>#{r.rank}</td>
                {DIMENSIONS.map((d) => <td key={d.key as string}>{r[d.key] as number}</td>)}
                <td><strong>{r.weighted_total}</strong></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <div className="section-title">Transparent Scoring Formula</div>
        {rows.map((r) => (
          <details key={r.vendor_id} style={{ marginBottom: 10 }}>
            <summary style={{ cursor: "pointer" }}>{r.vendor_name} — weights &amp; notes</summary>
            <pre style={{ background: "var(--surface-2)", padding: 12, borderRadius: 8, fontSize: 12, overflowX: "auto" }}>
              {JSON.stringify(r.breakdown_json, null, 2)}
            </pre>
          </details>
        ))}
      </div>
    </div>
  );
}
