import clsx from "clsx";
import { Check, Loader2, Sparkles, X, type LucideIcon } from "lucide-react";
import { createContext, useCallback, useContext, useState, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";

export const ease = [0.22, 1, 0.36, 1] as const;
export const fadeUp = (i = 0) => ({
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4, ease, delay: i * 0.06 },
});

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "m" | "l";
  icon?: ReactNode;
  iconRight?: ReactNode;
  loading?: boolean;
  to?: string;
  href?: string;
  full?: boolean;
};

export function Button({ variant = "primary", size = "m", icon, iconRight, loading, to, href, full, className, children, ...rest }: BtnProps) {
  const cls = clsx(
    "focus-ring inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md font-semibold transition-all duration-150 disabled:pointer-events-none disabled:opacity-50",
    size === "l" ? "h-12 px-6 text-[15px]" : "h-10 px-4 text-sm",
    variant === "primary" && "bg-primary text-on-primary hover:-translate-y-0.5 hover:shadow-glow active:translate-y-0",
    variant === "secondary" && "border border-line bg-surface text-ink hover:border-line-strong hover:bg-muted",
    variant === "ghost" && "text-primary-700 hover:bg-primary-50",
    variant === "danger" && "text-danger hover:bg-danger-50",
    full && "w-full",
    className,
  );
  const inner = (
    <>
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : icon}
      {children}
      {iconRight}
    </>
  );
  if (to) return <Link to={to} className={cls}>{inner}</Link>;
  if (href)
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className={cls} onClick={rest.onClick as any}>
        {inner}
      </a>
    );
  return (
    <button className={cls} disabled={loading || rest.disabled} {...rest}>
      {inner}
    </button>
  );
}

export type Tone = "Success" | "Warning" | "Danger" | "Info" | "Accent" | "Violet" | "Neutral";
const TONES: Record<Tone, string> = {
  Success: "bg-success-50 text-success",
  Warning: "bg-warning-50 text-warning",
  Danger: "bg-danger-50 text-danger",
  Info: "bg-primary-50 text-primary-700",
  Accent: "bg-accent-50 text-accent",
  Violet: "bg-violet-50 text-violet",
  Neutral: "bg-muted text-ink-2",
};

export function Badge({ tone = "Neutral", dot, children, className }: { tone?: Tone; dot?: boolean; children: ReactNode; className?: string }) {
  return (
    <span className={clsx("inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold", TONES[tone], className)}>
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

export function Chip({ state = "default", onClick, onRemove, children, className }: { state?: "default" | "selected" | "ai"; onClick?: () => void; onRemove?: () => void; children: ReactNode; className?: string }) {
  return (
    <span
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={(e) => onClick && (e.key === "Enter" || e.key === " ") && onClick()}
      className={clsx(
        "focus-ring inline-flex h-9 select-none items-center gap-1.5 whitespace-nowrap rounded-full border px-3.5 text-[13px] font-medium transition-colors",
        onClick && "cursor-pointer",
        state === "default" && "border-line bg-surface text-ink hover:border-line-strong",
        state === "selected" && "border-primary bg-primary-50 text-primary-700",
        state === "ai" && "border-violet/30 bg-violet-50 text-violet",
        className,
      )}
    >
      {state === "selected" && <Check className="h-3.5 w-3.5" />}
      {state === "ai" && <Sparkles className="h-3.5 w-3.5" />}
      {children}
      {onRemove && (
        <button aria-label="Bỏ tiêu chí" onClick={(e) => (e.stopPropagation(), onRemove())} className="-mr-1 rounded-full p-0.5 hover:bg-violet/10">
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </span>
  );
}

const BOX_TONES = {
  primary: "bg-primary-50 text-primary",
  success: "bg-success-50 text-success",
  warning: "bg-warning-50 text-warning",
  danger: "bg-danger-50 text-danger",
  violet: "bg-violet-50 text-violet",
  accent: "bg-accent-50 text-accent",
  muted: "bg-muted text-ink-2",
};
export function IconBox({ icon: Icon, tone = "primary", size = 40, className }: { icon: LucideIcon; tone?: keyof typeof BOX_TONES; size?: number; className?: string }) {
  return (
    <span className={clsx("inline-flex shrink-0 items-center justify-center rounded-md", BOX_TONES[tone], className)} style={{ width: size, height: size }}>
      <Icon style={{ width: size / 2, height: size / 2 }} strokeWidth={2} />
    </span>
  );
}

const inputCls =
  "mt-1.5 w-full rounded-md border border-line bg-surface px-3.5 text-[15px] text-ink placeholder:text-ink-3 transition focus:border-primary focus:outline-none focus:ring-4 focus:ring-primary/15";

export function Field({ label, helper, error, className, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string; helper?: string; error?: string }) {
  return (
    <label className={clsx("block", className)}>
      <span className="label-s text-ink-2">{label}</span>
      <input className={clsx(inputCls, "h-11", error && "border-danger")} {...props} />
      {(error || helper) && <span className={clsx("mt-1 block text-xs", error ? "text-danger" : "text-ink-3")}>{error || helper}</span>}
    </label>
  );
}

export function TextArea({ label, className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string }) {
  return (
    <label className={clsx("block", className)}>
      <span className="label-s text-ink-2">{label}</span>
      <textarea className={clsx(inputCls, "min-h-[96px] py-3 leading-relaxed")} {...props} />
    </label>
  );
}

export function Select({ label, children, className, ...props }: SelectHTMLAttributes<HTMLSelectElement> & { label: string }) {
  return (
    <label className={clsx("block", className)}>
      <span className="label-s text-ink-2">{label}</span>
      <select className={clsx(inputCls, "h-11 appearance-none")} {...props}>
        {children}
      </select>
    </label>
  );
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label?: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={clsx("focus-ring relative h-6 w-10 shrink-0 rounded-full transition-colors", checked ? "bg-primary" : "bg-line-strong")}
    >
      <span className={clsx("absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all", checked ? "left-[18px]" : "left-0.5")} />
    </button>
  );
}

export function Checkbox({ checked, onChange, children }: { checked: boolean; onChange: (v: boolean) => void; children?: ReactNode }) {
  return (
    <label className="inline-flex cursor-pointer items-start gap-2.5 text-sm">
      <span
        className={clsx("mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-[6px] border-[1.5px] transition", checked ? "border-primary bg-primary text-white" : "border-line-strong bg-surface")}
      >
        {checked && <Check className="h-3.5 w-3.5" strokeWidth={3} />}
      </span>
      <input type="checkbox" className="sr-only" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      {children && <span>{children}</span>}
    </label>
  );
}

export function Bar({ value, tone = "primary", height = 8, className }: { value: number; tone?: "primary" | "violet" | "danger" | "success" | "accent" | "warning"; height?: number; className?: string }) {
  const c = { primary: "bg-primary", violet: "bg-violet", danger: "bg-danger", success: "bg-success", accent: "bg-accent", warning: "bg-warning" }[tone];
  return (
    <div className={clsx("w-full overflow-hidden rounded-full bg-muted", className)} style={{ height }}>
      <motion.div className={clsx("h-full rounded-full", c)} initial={{ width: 0 }} animate={{ width: `${Math.max(2, Math.min(100, value))}%` }} transition={{ duration: 0.6, ease }} />
    </div>
  );
}

export function Card({ children, className, pad = "p-6", id }: { children: ReactNode; className?: string; pad?: string; id?: string }) {
  return (
    <div id={id} className={clsx("card scroll-mt-24", pad, className)}>
      {children}
    </div>
  );
}

export function SectionHead({ eyebrow, icon: Icon, tone = "text-primary", title, sub, action, center }: { eyebrow?: string; icon?: LucideIcon; tone?: string; title: string; sub?: string; action?: ReactNode; center?: boolean }) {
  return (
    <div className={clsx("flex flex-wrap items-end gap-4", center ? "justify-center text-center" : "justify-between")}>
      <div className={clsx("space-y-3", center && "flex flex-col items-center")}>
        {eyebrow && (
          <div className={clsx("flex items-center gap-2 text-sm font-semibold", tone)}>
            {Icon && <Icon className="h-[18px] w-[18px]" />}
            {eyebrow}
          </div>
        )}
        <h2 className="text-[28px] font-bold leading-tight sm:text-h1">{title}</h2>
        {sub && <p className={clsx("max-w-2xl text-lg text-ink-2", center && "mx-auto")}>{sub}</p>}
      </div>
      {action}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("skeleton rounded-md", className)} />;
}

export function Spinner({ label = "Đang tải…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-16 text-ink-3">
      <Loader2 className="h-5 w-5 animate-spin" />
      {label}
    </div>
  );
}

export function StatCard({ label, value, delta, tone = "success" }: { label: string; value: ReactNode; delta?: ReactNode; tone?: "success" | "warning" | "danger" | "muted" }) {
  return (
    <div className="card p-5">
      <div className="text-[13px] text-ink-3">{label}</div>
      <div className="mt-1 text-[28px] font-bold leading-tight tracking-tight">{value}</div>
      {delta && <div className={clsx("mt-1 text-xs font-medium", { success: "text-success", warning: "text-warning", danger: "text-danger", muted: "text-ink-3" }[tone])}>{delta}</div>}
    </div>
  );
}

// ---------- Toast ----------
type ToastT = { id: number; text: string; tone: "success" | "info" | "danger" };
const ToastCtx = createContext<(text: string, tone?: ToastT["tone"]) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastT[]>([]);
  const push = useCallback((text: string, tone: ToastT["tone"] = "success") => {
    const id = Date.now() + Math.random();
    setItems((s) => [...s, { id, text, tone }]);
    setTimeout(() => setItems((s) => s.filter((t) => t.id !== id)), 4000);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="pointer-events-none fixed bottom-24 left-1/2 z-[1000] flex -translate-x-1/2 flex-col items-center gap-2 lg:bottom-8">
        <AnimatePresence>
          {items.map((t) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 16, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8 }}
              className={clsx(
                "pointer-events-auto flex items-center gap-3 rounded-lg border border-line bg-surface px-4 py-3 text-sm shadow-lg",
              )}
            >
              <span className={clsx("h-2 w-2 rounded-full", { success: "bg-success", info: "bg-primary", danger: "bg-danger" }[t.tone])} />
              {t.text}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastCtx.Provider>
  );
}
