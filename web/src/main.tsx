import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import "@fontsource-variable/inter";
import "./styles.css";
import { MonthContext, currentMonth } from "./hooks";
import { BottomNav } from "./components/BottomNav";
import Overview from "./pages/Overview";
import Budgets from "./pages/Budgets";
import Receipt from "./pages/Receipt";
import Insights from "./pages/Insights";
import Goals from "./pages/Goals";
import Activity from "./pages/Activity";
import Ask from "./pages/Ask";

function App() {
  const [month, setMonth] = useState(currentMonth);
  return (
    <MonthContext.Provider value={{ month, setMonth }}>
      <div className="app">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/budgets" element={<Budgets />} />
          <Route path="/receipt" element={<Receipt />} />
          <Route path="/insights" element={<Insights />} />
          <Route path="/goals" element={<Goals />} />
          <Route path="/activity" element={<Activity />} />
          <Route path="/ask" element={<Ask />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <BottomNav />
      </div>
    </MonthContext.Provider>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
