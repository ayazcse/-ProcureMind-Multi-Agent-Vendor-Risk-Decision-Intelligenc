import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import RequestsList from "./pages/RequestsList";
import RequestDetail from "./pages/RequestDetail";
import Vendors from "./pages/Vendors";
import Comparison from "./pages/Comparison";
import HumanReview from "./pages/HumanReview";

function Sidebar() {
  const links = [
    { to: "/", label: "Dashboard", end: true },
    { to: "/requests", label: "Procurement Requests" },
    { to: "/vendors", label: "Vendors" },
    { to: "/review", label: "Human Review" },
  ];
  return (
    <div className="sidebar">
      <h1>ProcureMind</h1>
      <p className="tagline">Vendor Risk &amp; Decision Intelligence</p>
      {links.map((l) => (
        <NavLink key={l.to} to={l.to} end={l.end} className={({ isActive }) => "nav-link" + (isActive ? " active" : "")}>
          {l.label}
        </NavLink>
      ))}
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Sidebar />
      <div className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/requests" element={<RequestsList />} />
          <Route path="/requests/:id" element={<RequestDetail />} />
          <Route path="/requests/:id/comparison" element={<Comparison />} />
          <Route path="/vendors" element={<Vendors />} />
          <Route path="/review" element={<HumanReview />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
