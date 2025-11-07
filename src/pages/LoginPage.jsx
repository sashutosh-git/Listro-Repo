import { useState } from "react";
import { useNavigate } from "react-router-dom";

const LoginPage = () => {
  const navigate = useNavigate();

  // 🔐 Login states
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  // 🔁 Forgot Password states
  const [showForgot, setShowForgot] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [resetEmail, setResetEmail] = useState("");
  const [resetStatus, setResetStatus] = useState("");
  const [loading, setLoading] = useState(false);

  // 🌍 Backend base URL (use Node backend for login/reset)
  // Use only the Vite env var (no fallback)
  const BACKEND_URL = import.meta.env.VITE_PYTHON_BACKEND_URL;




  // ✅ Handle login form
  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setShowForgot(false);

    try {
      const res = await fetch(`${BACKEND_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (data.success) {
        localStorage.setItem("user", JSON.stringify({ email }));

       if (data.first_time) {
        navigate(`/change-password?email=${encodeURIComponent(email)}`);
      } else {
        navigate("/seller-list");
      }

      } else {
        setError(data.error || "Invalid email or password");
        setShowForgot(true);
      }
    } catch (err) {
      console.error(err);
      setError("Server error. Try again later.");
      setShowForgot(true);
    }
  };

  // 📧 Forgot Password handler
const handleResetPassword = async () => {
  setResetStatus("");

  if (!resetEmail.trim()) {
    setResetStatus("Please enter your email.");
    return;
  }

  setLoading(true);
  try {
    const res = await fetch(`${BACKEND_URL}/reset-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: resetEmail }),
    });

    const data = await res.json();

    if (res.ok && data.pending_approval) {
      setResetStatus("⚠️ Please contact your admin for approval.");
    } else if (res.ok && data.success) {
      setResetStatus("✅ Reset link sent to your email!");
    } else {
      setResetStatus(data.error || "Failed to send reset link.");
    }
  } catch (err) {
    console.error("Reset error:", err);
    setResetStatus("⚠️ Server error. Try again later.");
  } finally {
    setLoading(false);
  }
};


  return (
    <div className="w-full h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-orange-50 relative">
      <div className="bg-white rounded-2xl shadow-lg p-10 w-96">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="text-orange-600 text-3xl font-bold">Listro</div>
          <h2 className="text-2xl font-bold text-gray-900 mt-2">
            Welcome to Listro
          </h2>
          <p className="text-gray-600 mt-2">Please sign in to continue.</p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleLogin} className="space-y-4">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full p-3 border border-gray-300 rounded-xl focus:outline-none"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full p-3 border border-gray-300 rounded-xl focus:outline-none"
          />
          <button
            type="submit"
            className="w-full bg-orange-600 text-white py-3 rounded-xl font-semibold hover:bg-orange-700 transition"
          >
            Login
          </button>

          {/* Forgot Password link */}
          {showForgot && (
            <p
              onClick={() => setShowModal(true)}
              className="text-center text-sm text-blue-600 mt-4 cursor-pointer hover:underline"
            >
              Forgot Password?
            </p>
          )}
        </form>

        {error && (
          <p className="text-center text-red-500 text-sm mt-3">{error}</p>
        )}
      </div>

      {/* Forgot Password Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-lg p-6 w-80 text-center">
            <h3 className="text-xl font-semibold text-gray-800 mb-3">
              Forgot Password?
            </h3>
            <p className="text-gray-600 mb-3">
              Enter your email and we'll send you a reset link.
            </p>

            <input
              type="email"
              placeholder="Enter your email"
              value={resetEmail}
              onChange={(e) => setResetEmail(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-xl mb-3 focus:outline-none"
            />

            <button
              onClick={handleResetPassword}
              disabled={loading}
              className={`w-full ${
                loading ? "bg-gray-400" : "bg-orange-600 hover:bg-orange-700"
              } text-white py-2 rounded-xl font-semibold transition`}
            >
              {loading ? "Sending..." : "Send Reset Link"}
            </button>

            {resetStatus && (
              <p
                className={`text-sm mt-3 ${
                  resetStatus.startsWith("✅")
                    ? "text-green-600"
                    : "text-red-500"
                }`}
              >
                {resetStatus}
              </p>
            )}

            <button
              onClick={() => {
                setShowModal(false);
                setResetStatus("");
                setResetEmail("");
              }}
              className="mt-4 text-gray-600 text-sm hover:underline"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default LoginPage;