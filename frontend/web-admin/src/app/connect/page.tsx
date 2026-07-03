"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";

export default function ConnectPage() {
  const [connections, setConnections] = useState<any[]>([]);

  useEffect(() => {
    api.get("/api/connect").then((r) => setConnections(r.data.data || []));
  }, []);

  const connectYouTube = async () => {
    const res = await api.get("/api/connect/youtube/auth");
    window.location.href = res.data.data.auth_url;
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-xl font-bold mb-6">Platform Connections</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-5 border rounded-xl bg-white">
          <h3 className="font-semibold mb-2">YouTube</h3>
          <p className="text-xs text-muted-foreground mb-4">
            {connections.find((c) => c.platform === "youtube")?.connected ? "Connected" : "Not connected"}
          </p>
          <button onClick={connectYouTube} className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium">
            Connect
          </button>
        </div>
        <div className="p-5 border rounded-xl bg-white">
          <h3 className="font-semibold mb-2">TikTok</h3>
          <p className="text-xs text-muted-foreground mb-4">Coming soon</p>
          <button disabled className="px-4 py-2 bg-slate-200 text-slate-500 rounded-lg text-sm font-medium">
            Connect
          </button>
        </div>
        <div className="p-5 border rounded-xl bg-white">
          <h3 className="font-semibold mb-2">Facebook</h3>
          <p className="text-xs text-muted-foreground mb-4">Coming soon</p>
          <button disabled className="px-4 py-2 bg-slate-200 text-slate-500 rounded-lg text-sm font-medium">
            Connect
          </button>
        </div>
      </div>
    </div>
  );
}
