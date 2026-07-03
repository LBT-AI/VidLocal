"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Film, Home, Link2, LogOut } from "lucide-react";

export default function Navigation() {
  const pathname = usePathname();
  const links = [
    { href: "/dashboard", label: "Dashboard", icon: Home },
    { href: "/connect", label: "Connect", icon: Link2 },
  ];

  return (
    <nav className="border-b bg-white dark:bg-slate-900 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 font-bold text-xl">
          <Film className="w-6 h-6" />
          VidLocal
        </Link>
        <div className="flex items-center gap-6">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={cn(
                "flex items-center gap-2 text-sm font-medium transition-colors hover:text-primary",
                pathname.startsWith(l.href) ? "text-primary" : "text-muted-foreground"
              )}
            >
              <l.icon className="w-4 h-4" />
              {l.label}
            </Link>
          ))}
          <button
            onClick={() => {
              localStorage.removeItem("vidlocal_token");
              window.location.href = "/";
            }}
            className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-destructive"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
}
