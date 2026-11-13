import { useQuery } from "@tanstack/react-query";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Catalog, Filters } from "../lib/types";
import { Button, Chip, Field, Select, Toggle } from "./ui";

export function useCatalog() {
  return useQuery<Catalog>({ queryKey: ["catalog"], queryFn: () => api("/catalog"), staleTime: Infinity });
}

const toggle = (arr: string[], v: string) => (arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);

/** Bảng bộ lọc chi tiết (desktop: hộp thoại, mobile: khung kéo lên từ dưới). */
export function FilterPanel({ open, value, total, onClose, onApply }: { open: boolean; value: Filters; total?: number; onClose: () => void; onApply: (f: Filters) => void }) {
  const { data: cat } = useCatalog();
  const [f, setF] = useState<Filters>(value);
  useEffect(() => {
    setF(value);
  }, [value, open]);
  const set = (p: Partial<Filters>) => setF((s) => ({ ...s, ...p }));
  const mil = (v?: number | null) => (v ? String(v / 1_000_000).replace(".", ",") : "");
  const toVnd = (s: string) => (s.trim() ? Math.round(parseFloat(s.replace(",", ".")) * 1_000_000) : null);

  return (
    <AnimatePresence>
      {open && (
        <motion.div className="fixed inset-0 z-[60] flex items-end justify-center bg-slate-950/45 backdrop-blur-[2px] sm:items-center" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}>
          <motion.div
            role="dialog"
            aria-label="Bộ lọc"
            onClick={(e) => e.stopPropagation()}
            initial={{ y: 40, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 40, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="max-h-[88vh] w-full overflow-y-auto rounded-t-xl bg-surface p-6 shadow-lg sm:max-w-2xl sm:rounded-2xl"
          >
            <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-line-strong sm:hidden" />
            <div className="flex items-center justify-between">
              <h3 className="text-h3">Bộ lọc</h3>
              <div className="flex items-center gap-2">
                <Button variant="ghost" onClick={() => setF({ ...value, budget_min: null, budget_max: null, districts: [], amenities: [], room_types: [], area_min: null, max_people: null })}>
                  Đặt lại
                </Button>
                <button onClick={onClose} aria-label="Đóng" className="rounded-full bg-muted p-2">
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
            <div className="mt-6 space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <Field label="Giá từ (triệu)" inputMode="decimal" defaultValue={mil(f.budget_min)} key={`min-${open}`} onChange={(e) => set({ budget_min: toVnd(e.target.value) })} placeholder="1,5" />
                <Field label="Giá đến (triệu)" inputMode="decimal" defaultValue={mil(f.budget_max)} key={`max-${open}`} onChange={(e) => set({ budget_max: toVnd(e.target.value) })} placeholder="2,5" />
              </div>
              <div>
                <div className="label-s mb-2 text-ink-2">Khu vực</div>
                <div className="flex flex-wrap gap-2">
                  {cat?.districts.map((d) => (
                    <Chip key={d} state={f.districts.includes(d) ? "selected" : "default"} onClick={() => set({ districts: toggle(f.districts, d) })}>{d}</Chip>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Select label="Gần trường" value={f.school_id ?? ""} onChange={(e) => set({ school_id: e.target.value ? Number(e.target.value) : null, max_distance_km: e.target.value ? f.max_distance_km ?? 3 : null })}>
                  <option value="">Không quan trọng</option>
                  {cat?.schools.map((s) => <option key={s.id} value={s.id}>{s.short_name}</option>)}
                </Select>
                <Select label="Khoảng cách tối đa" value={f.max_distance_km ?? ""} disabled={!f.school_id} onChange={(e) => set({ max_distance_km: e.target.value ? Number(e.target.value) : null })}>
                  {[1, 2, 3, 5, 8].map((k) => <option key={k} value={k}>≤ {k} km</option>)}
                </Select>
              </div>
              <div>
                <div className="label-s mb-2 text-ink-2">Loại phòng</div>
                <div className="flex flex-wrap gap-2">
                  {cat?.room_types.map((r) => (
                    <Chip key={r.key} state={f.room_types.includes(r.key) ? "selected" : "default"} onClick={() => set({ room_types: toggle(f.room_types, r.key) })}>{r.label}</Chip>
                  ))}
                </div>
              </div>
              <div>
                <div className="label-s mb-2 text-ink-2">Tiện ích</div>
                <div className="flex flex-wrap gap-2">
                  {cat?.amenities.map((a) => (
                    <Chip key={a.key} state={f.amenities.includes(a.key) ? "selected" : "default"} onClick={() => set({ amenities: toggle(f.amenities, a.key) })}>{a.label}</Chip>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Diện tích từ (m²)" inputMode="numeric" defaultValue={f.area_min ? Math.round(f.area_min) : ""} key={`area-${open}`} onChange={(e) => set({ area_min: e.target.value ? Number(e.target.value) : null })} />
                <Field label="Số người ở" inputMode="numeric" defaultValue={f.max_people ?? ""} key={`ppl-${open}`} onChange={(e) => set({ max_people: e.target.value ? Number(e.target.value) : null })} />
              </div>
              <div className="flex items-center justify-between rounded-lg bg-muted p-4">
                <div>
                  <div className="text-sm font-semibold">Ẩn tin rủi ro cao</div>
                  <div className="caption">AI tự lọc tin nghi lừa đảo</div>
                </div>
                <Toggle checked={f.hide_high_risk} onChange={(v) => set({ hide_high_risk: v })} label="Ẩn tin rủi ro cao" />
              </div>
            </div>
            <Button full size="l" className="mt-6" onClick={() => onApply(f)}>
              Xem kết quả{total != null ? ` (${total} phòng hiện tại)` : ""}
            </Button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
