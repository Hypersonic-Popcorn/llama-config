import { NavLink } from "react-router-dom";

const links = [
  { path: "/config", label: "Config" },
  { path: "/models", label: "Models" },
  { path: "/docker", label: "Docker" },
  { path: "/logs", label: "Logs" },
];

export default function Sidebar({ title }) {
  return (
    <nav className="sidebar">
      <div className="sidebar-title">
        {title}
      </div>
      <div className="sidebar-nav">
        {links.map((link) => (
          <NavLink
            key={link.path}
            to={link.path}
            className={({ isActive }) =>
              `sidebar-link${isActive ? " active" : ""}`
            }
          >
            {link.label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
