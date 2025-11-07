import { useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";

export default function ChangePasswordPage() {
  const [searchParams] = useSearchParams();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const email = searchParams.get("email");
  const token = searchParams.get("token");

  // ✅ Use Node backend URL from .env (Cloud Run)
  const API_BASE = import.meta.env.VITE_NODE_BACKEND_URL;

  useEffect(() => {
    if (!email) {
      setError("Missing email. Please use a valid link.");
    }
  }, [email]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");

    if (!password || !confirmPassword) {
      setError("Please fill all fields.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/update-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, token }),
      });

      // ✅ Handle non-JSON error pages (like 404 HTML)
      const text = await response.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch {
        throw new Error("Invalid server response. Please check backend URL.");
      }

      if (response.ok && data.success) {
        setMessage(data.message);
        setTimeout(() => navigate("/"), 2000);
      } else {
        setError(data.error || "Error updating password.");
      }
    } catch (err) {
      setError(err.message || "Server error. Please try again.");
    }
  };

  return (
    <div className="flex justify-center items-center min-h-screen bg-gradient-to-b from-gray-100 to-white">
      <div className="bg-white shadow-xl rounded-2xl p-8 w-[400px]">
        <h2 className="text-2xl font-bold text-center mb-6 text-gray-800">
          Set Your New Password
        </h2>

        {error && <p className="text-red-600 mb-3 text-sm text-center">{error}</p>}
        {message && (
          <div className="mb-3 text-center bg-green-100 border border-green-300 text-green-800 text-sm font-medium rounded-lg p-2 animate-fade-in">
            ✅ {message || "Password reset successfully!"}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <label className="block mb-2 text-gray-700 text-sm font-medium">
            New Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Enter new password"
          />

          <label className="block mb-2 text-gray-700 text-sm font-medium">
            Confirm Password
          </label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 mb-6 focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Confirm new password"
          />

          <button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-lg transition duration-200"
          >
            Update Password
          </button>
        </form>
      </div>
    </div>
  );
}
