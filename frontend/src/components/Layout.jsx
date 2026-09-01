import { Outlet } from "react-router-dom";

import Sidebar from "./Sidebar";
import UserMenu from "./UserMenu";

export default function Layout() {
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-area">
        <div className="topbar">
          <UserMenu />
        </div>
        <Outlet />
      </div>
    </div>
  );
}
