import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useEffect, type FormEvent, type ReactNode } from "react";
import { Button } from "./ui";

/** Hộp thoại dạng biểu mẫu: trượt từ dưới lên trên điện thoại, nằm giữa màn hình trên máy tính. */
export function Dialog({
  open, title, sub, onClose, onSubmit, submitLabel = "Lưu", busy, children, danger,
}: {
  open: boolean; title: string; sub?: string; onClose: () => void; onSubmit: () => void; submitLabel?: string; busy?: boolean; children: ReactNode; danger?: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    onSubmit();
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div className="fixed inset-0 z-[70] flex items-end justify-center bg-slate-950/50 backdrop-blur-[3px] sm:items-center" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}>
          <motion.form
            role="dialog"
            aria-label={title}
            onSubmit={submit}
            onClick={(e) => e.stopPropagation()}
            initial={{ y: 30, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 20, opacity: 0 }}
            className="max-h-[90vh] w-full space-y-4 overflow-y-auto rounded-t-xl bg-surface p-6 shadow-lg sm:max-w-[600px] sm:rounded-2xl sm:p-7"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="text-h3">{title}</h3>
                {sub && <p className="text-sm text-ink-3">{sub}</p>}
              </div>
              <button type="button" onClick={onClose} aria-label="Đóng" className="rounded-full bg-muted p-2"><X className="h-4 w-4" /></button>
            </div>
            {children}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
              <div>{danger}</div>
              <div className="flex gap-3">
                <Button type="button" variant="secondary" onClick={onClose}>Hủy</Button>
                <Button type="submit" loading={busy}>{submitLabel}</Button>
              </div>
            </div>
          </motion.form>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
