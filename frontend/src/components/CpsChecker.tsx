import { cn } from "@/lib/utils";

export default function CpsChecker({ cps, status }: { cps?: number; status: string }) {
  const color =
    status === "ok"
      ? "bg-green-100 text-green-700"
      : status === "cps_warning"
      ? "bg-amber-100 text-amber-700"
      : "bg-red-100 text-red-700";
  return (
    <span className={cn("text-xs px-2 py-0.5 rounded-full font-medium", color)}>
      {cps?.toFixed(1)} cps
    </span>
  );
}
