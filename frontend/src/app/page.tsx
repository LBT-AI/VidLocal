"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [token, setToken] = useState("");

  const login = () => {
    localStorage.setItem("vidlocal_token", token || "demo-token");
    router.push("/dashboard");
  };

  return (
    <div className="flex items-center justify-center min-h-[80vh]">
      <div className="w-full max-w-sm p-8 rounded-xl border bg-white shadow-sm">
        <h1 className="text-2xl font-bold mb-6 text-center">VidLocal</h1>
        <p className="text-sm text-muted-foreground mb-6 text-center">
          Paste a dev JWT or click Login to continue
        </p>
        <input
          type="text"
          placeholder="JWT Token (optional)"
          className="w-full px-3 py-2 border rounded-lg mb-4 text-sm"
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
        <button
          onClick={login}
          className="w-full bg-primary text-primary-foreground py-2 rounded-lg font-medium hover:opacity-90"
        >
          Login
        </button>
      </div>
    </div>
  );
}
