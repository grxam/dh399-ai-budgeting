import { NavLink } from "react-router-dom";
import { Camera, ChartNoAxesColumn, House, Target, WalletCards } from "lucide-react";

const TABS = [
  { to: "/", label: "Home", Icon: House },
  { to: "/budgets", label: "Budgets", Icon: WalletCards },
  { to: "/receipt", label: "Receipt", Icon: Camera },
  { to: "/insights", label: "Insights", Icon: ChartNoAxesColumn },
  { to: "/goals", label: "Goals", Icon: Target },
];

export function BottomNav() {
  return (
    <nav className="bottom-nav" aria-label="Main">
      {TABS.map(({ to, label, Icon }) => (
        <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => `tab ${isActive ? "tab-on" : ""}`}>
          <span className="tab-icon">
            <Icon size={24} strokeWidth={1.6} />
          </span>
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
