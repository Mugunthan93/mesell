import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";

export default function Navbar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link to={user ? "/dashboard" : "/"} className="flex items-center gap-2">
          <span className="text-xl font-bold text-brand-600">MeeSell</span>
          <span className="text-xs text-slate-400">AI catalogs for Meesho</span>
        </Link>
        <nav className="flex items-center gap-3 text-sm">
          {user ? (
            <>
              <span className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-700">
                {user.plan?.toUpperCase() || "FREE"}
              </span>
              <Link to="/dashboard" className="text-slate-600 hover:text-slate-900">
                Dashboard
              </Link>
              <Link to="/pricing" className="text-slate-600 hover:text-slate-900">
                Pricing
              </Link>
              <button
                onClick={() => {
                  logout();
                  navigate("/");
                }}
                className="text-slate-600 hover:text-slate-900"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link to="/pricing" className="text-slate-600 hover:text-slate-900">
                Pricing calculator
              </Link>
              <Link
                to="/"
                className="rounded-md bg-brand-500 px-3 py-1.5 font-medium text-white hover:bg-brand-600"
              >
                Start free
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
