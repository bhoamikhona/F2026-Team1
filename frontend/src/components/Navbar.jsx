import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { LayoutDashboard, LogOut, UserPlus, Users } from "lucide-react";
import ThemeToggle from "./ThemeToggle.jsx";
import Dropdown from "./Dropdown.jsx";
import "../styles/navbar.css";
import logo from "../assets/images/logo.png";
import useAuth from "../hooks/useAuth.js";

function Navbar() {
  const { user, isLoading, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  async function signout() {
    await logout();
    navigate("/login", { replace: true });
  }

  const userMenuItems = [
    { label: "Dashboard", icon: LayoutDashboard, to: "/dashboard" },
    { label: "My patients", icon: Users, to: "/patients" },
    { label: "New patient", icon: UserPlus, to: "/patients/new" },
    { type: "divider" },
    { label: "Sign out", icon: LogOut, tone: "danger", onClick: signout },
  ];

  return (
    <nav className="nav">
      <div className="nav-container">
        <div className="nav__left">
          <Link className="nav__logo-link" aria-label="DUAL home" to="/">
            <div className="nav__logo-container">
              <div className="nav__logo-img-container">
                <img src={logo} alt="logo" className="nav__logo-img" />
              </div>
              <div className="nav__logo-text-container">
                <p className="nav__logo-text--primary logo-wordmark">DUAL</p>
                <p className="nav__logo-text--secondary logo-descriptor">
                  OCULAR DISEASE SCREENER
                </p>
              </div>
            </div>
          </Link>

          <div className="vertical-line" role="presentation"></div>

          <ul className="nav__list">
            <li className="nav__list-item">
              <NavLink className="nav__link body-md" to="/upload">
                Upload
              </NavLink>
            </li>
            <li className="nav__list-item">
              <NavLink className="nav__link body-md" to="/history">
                History
              </NavLink>
            </li>
            <li className="nav__list-item">
              <NavLink className="nav__link body-md" to="/about">
                About
              </NavLink>
            </li>
          </ul>
        </div>
        <div className="nav__right">
          <ThemeToggle />

          {!isLoading && user && (
            <div className="nav__user">
              <Dropdown
                variant="user"
                label={user.name}
                align="end"
                header={{ title: user.name, subtitle: user.email }}
                items={userMenuItems}
              />
            </div>
          )}

          {!isLoading && !user && (
            <Link
              to="/login"
              state={{ from: location }}
              className="nav__btn--signin body-md"
            >
              Sign In
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
