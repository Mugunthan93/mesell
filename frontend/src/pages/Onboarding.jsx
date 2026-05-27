import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuthStore } from "../stores/authStore";

export default function Onboarding() {
  const [step, setStep] = useState("phone");
  const [phone, setPhone] = useState("+91");
  const [otp, setOtp] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();

  async function sendOtp() {
    setError(null);
    setBusy(true);
    try {
      await api.post("/auth/send-otp", { phone });
      setStep("otp");
    } catch (err) {
      setError(err.response?.data?.detail || "Could not send OTP");
    } finally {
      setBusy(false);
    }
  }

  async function verify() {
    setError(null);
    setBusy(true);
    try {
      const { data } = await api.post("/auth/verify-otp", { phone, otp });
      login({ token: data.token, user: data.user });
      navigate("/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Invalid OTP");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md flex-col justify-center px-4">
      <h1 className="text-2xl font-bold">Sign in to MeeSell</h1>
      <p className="mt-1 text-sm text-slate-500">
        AI catalogs · QualityGate · PriceIntel — built for Meesho sellers.
      </p>

      {step === "phone" && (
        <div className="mt-6 space-y-3">
          <label className="block text-sm font-medium">Phone number</label>
          <input
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="+91XXXXXXXXXX"
            className="w-full rounded-md border border-slate-300 px-3 py-2 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          <button
            disabled={busy}
            onClick={sendOtp}
            className="w-full rounded-md bg-brand-500 px-4 py-2 font-medium text-white hover:bg-brand-600 disabled:opacity-60"
          >
            {busy ? "Sending..." : "Send OTP"}
          </button>
        </div>
      )}

      {step === "otp" && (
        <div className="mt-6 space-y-3">
          <p className="text-sm text-slate-600">
            We sent a 4-digit code to <span className="font-mono">{phone}</span>.
          </p>
          <input
            value={otp}
            onChange={(e) => setOtp(e.target.value)}
            placeholder="OTP"
            inputMode="numeric"
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-center text-2xl tracking-[0.5em] focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
          <button
            disabled={busy}
            onClick={verify}
            className="w-full rounded-md bg-brand-500 px-4 py-2 font-medium text-white hover:bg-brand-600 disabled:opacity-60"
          >
            {busy ? "Verifying..." : "Verify & continue"}
          </button>
          <button
            onClick={() => setStep("phone")}
            className="w-full text-sm text-slate-500 hover:text-slate-700"
          >
            Change number
          </button>
        </div>
      )}

      {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}
    </div>
  );
}
