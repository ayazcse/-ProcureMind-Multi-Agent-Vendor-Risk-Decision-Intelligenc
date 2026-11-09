import { useEffect, useState } from "react";
import { api, Vendor } from "../api/client";

export default function Vendors() {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [isDemo, setIsDemo] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => api.listVendors().then(setVendors).catch((e) => setError(e.message));

  useEffect(() => { load(); }, []);

  const onCreate = async () => {
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api.createVendor({ name, contact_email: email || undefined, is_synthetic_demo: isDemo });
      setName("");
      setEmail("");
      load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h2 className="page-title">Vendors</h2>
      <p className="page-subtitle">Add vendors and upload their proposal documents from a procurement request's page.</p>

      <div className="card">
        <div className="section-title">Add Vendor</div>
        <div className="grid grid-2">
          <div>
            <label>Vendor name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Acme Logistics Pvt Ltd" />
          </div>
          <div>
            <label>Contact email (optional)</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="sales@vendor.com" />
          </div>
        </div>
        <label className="flex mt-8" style={{ marginTop: 14 }}>
          <input type="checkbox" style={{ width: "auto" }} checked={isDemo} onChange={(e) => setIsDemo(e.target.checked)} />
          <span style={{ marginLeft: 6 }}>This is synthetic demo data</span>
        </label>
        {error && <p style={{ color: "var(--danger)" }}>{error}</p>}
        <button className="btn mt-16" onClick={onCreate} disabled={busy || !name.trim()}>
          {busy ? "Adding…" : "Add Vendor"}
        </button>
      </div>

      <div className="card">
        <div className="section-title">All Vendors ({vendors.length})</div>
        {vendors.length === 0 ? (
          <p className="muted">No vendors yet.</p>
        ) : (
          <table>
            <thead><tr><th>Name</th><th>Contact</th><th>Demo Data</th><th>Added</th></tr></thead>
            <tbody>
              {vendors.map((v) => (
                <tr key={v.id}>
                  <td>{v.name}</td>
                  <td className="muted">{v.contact_email || "—"}</td>
                  <td>{v.is_synthetic_demo ? <span className="pill">synthetic</span> : "—"}</td>
                  <td className="muted">{new Date(v.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
