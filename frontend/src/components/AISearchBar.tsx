import clsx from "clsx";
import { ArrowRight, Sparkles } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

export function AISearchBar({ initial = "", onSubmit, busy, className, compact }: { initial?: string; onSubmit?: (q: string) => void; busy?: boolean; className?: string; compact?: boolean }) {
  const [q, setQ] = useState(initial);
  const nav = useNavigate();
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const v = q.trim();
    if (!v) return;
    onSubmit ? onSubmit(v) : nav(`/tim-kiem?q=${encodeURIComponent(v)}`);
  };
  return (
    <form
      onSubmit={submit}
      className={clsx(
        "group relative flex items-center gap-3 rounded-xl border bg-surface/90 p-2 pl-4 shadow-lg backdrop-blur-xl transition-all",
        busy ? "border-violet/50 shadow-[0_0_0_4px_rgb(var(--violet)/0.12)]" : "border-line focus-within:border-primary focus-within:shadow-[0_0_0_4px_rgb(var(--primary)/0.12)]",
        className,
      )}
    >
      <Sparkles className={clsx("h-5 w-5 shrink-0 text-violet", busy && "animate-pulse")} />
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        aria-label="Mô tả phòng bạn cần"
        placeholder="Ví dụ: phòng dưới 2,5 triệu gần Bách khoa, có gác, cho nấu ăn"
        className={clsx("min-w-0 flex-1 bg-transparent text-ink placeholder:text-ink-3 focus:outline-none", compact ? "text-[15px]" : "text-base sm:text-[17px]")}
      />
      <button type="submit" disabled={busy} className="focus-ring inline-flex h-11 shrink-0 items-center gap-2 rounded-md bg-primary px-4 text-sm font-semibold text-on-primary transition hover:shadow-glow disabled:opacity-60 sm:px-5">
        <span className="hidden sm:inline">Tìm với AI</span>
        <ArrowRight className="h-4 w-4" />
      </button>
    </form>
  );
}
