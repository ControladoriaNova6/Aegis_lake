import { useState } from "react";
import { Outlet } from "react-router-dom";

import Sidebar from "./Sidebar";
import UserMenu from "./UserMenu";

export default function Layout() {
  const [sidebarMinimizada, setSidebarMinimizada] = useState(false);

  return (
    <div className={`app-shell${sidebarMinimizada ? " sidebar-minimizada" : ""}`}>
      <Sidebar minimizada={sidebarMinimizada} onToggleMinimizar={() => setSidebarMinimizada((v) => !v)} />
      <div className="main-area">
        <div className="topbar">
          <UserMenu />
        </div>
        <Outlet />
      </div>
    </div>
  );
}
