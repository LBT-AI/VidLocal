import { cn } from "@/lib/utils";

const statusMap: Record<string, string> = {
  pending: "bg-slate-100 text-slate-800",
  transcribing: "bg-blue-100 text-blue-800",
  translating: "bg-indigo-100 text-indigo-800",
  tts: "bg-purple-100 text-purple-800",
  rendering: "bg-amber-100 text-amber-800",
  done: "bg-green-100 text-green-800",
  error: "bg-red-100 text-red-800",
};

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span className={cn("px-2.5 py-0.5 rounded-full text-xs font-semibold", statusMap[status] || statusMap.pending)}>
      {status}
    </span>
  );
}
