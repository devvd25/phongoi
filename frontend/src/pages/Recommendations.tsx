import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";
import { useState } from "react";
import { Aurora } from "../components/Brand";
import { StudentLayout } from "../components/Layout";
import { ListingCard, ListingCardSkeleton, RoomPhoto, SaveButton } from "../components/ListingCard";
import { Badge, Bar, Button, Chip, Spinner, useToast } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { fullVnd, timeAgo } from "../lib/format";
import type { ListingCard as Listing } from "../lib/types";

type RecommendationResponse = { total: number; profile: { chips: string[] } | null; top_pick: Listing | null; items: Listing[] };

const TABS = [
  ["match", "Phù hợp nhất"],
  ["new", "Mới đăng hôm nay"],
  ["cheap", "Giá tốt"],
  ["near", "Gần trường nhất"],
] as const;
const FEEDBACK = [
  ["too_far", "Quá xa trường"],
  ["too_expensive", "Quá đắt"],
  ["room_type", "Không thích kiểu phòng"],
  ["unsafe_area", "Khu vực không an toàn"],
] as const;
const CRIT: Record<string, string> = { budget: "Ngân sách", distance: "Khoảng cách tới trường", amenities: "Tiện ích bạn cần", safety: "Độ an toàn" };

export default function Recommendations() {
  const { user } = useAuth();
  const [tab, setTab] = useState<(typeof TABS)[number][0]>("match");
  const qc = useQueryClient();
  const toast = useToast();
  const { data, isLoading } = useQuery<RecommendationResponse>({ queryKey: ["reco", tab], queryFn: () => api(`/recommendations?tab=${tab}`) });
  const fb = useMutation({
    mutationFn: (reason: string) => api("/recommendations/feedback", { body: { reason, listing_id: data?.top_pick?.id } }),
    onSuccess: () => (toast("Cảm ơn bạn! Lần gợi ý sau sẽ sát hơn."), qc.invalidateQueries({ queryKey: ["reco"] })),
  });
  const top = data?.top_pick;

  return (
    <StudentLayout>
      <div className="relative isolate">
        <Aurora intensity={0.7} className="h-[480px]" />
        <div className="container-page space-y-8 pb-16 pt-10">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm font-semibold text-violet"><Sparkles className="h-[18px] w-[18px]" /> Cập nhật lúc 8:00 sáng nay</div>
            <h1 className="text-[30px] font-bold leading-tight sm:text-h1">Chào {user?.full_name.split(" ").slice(-2).join(" ")}, có {data?.total ?? "…"} phòng hợp với bạn</h1>
            <p className="text-lg text-ink-2">Gợi ý dựa trên hồ sơ nhu cầu, các tin bạn đã lưu và những phòng bạn bỏ qua.</p>
          </div>

          <div className="flex flex-wrap items-center gap-4 rounded-xl border border-white/60 bg-surface/75 p-5 shadow-sm backdrop-blur-xl">
            <div className="flex-1 space-y-2.5">
              <div className="text-sm font-semibold text-ink-2">Hồ sơ nhu cầu của bạn</div>
              <div className="flex flex-wrap gap-2">
                {data?.profile ? data.profile.chips.map((c: string) => <Chip key={c} state="ai">{c}</Chip>) : <span className="text-sm text-ink-3">Bạn chưa có hồ sơ nhu cầu, gợi ý đang dùng tiêu chí mặc định.</span>}
              </div>
            </div>
            <Button variant="secondary" to="/ho-so-nhu-cau">{data?.profile ? "Chỉnh hồ sơ" : "Tạo hồ sơ nhu cầu"}</Button>
          </div>

          <div className="flex gap-8 overflow-x-auto border-b border-line">
            {TABS.map(([k, l]) => (
              <button key={k} onClick={() => setTab(k)} className={clsx("whitespace-nowrap border-b-2 pb-3 text-sm font-semibold transition", tab === k ? "border-primary text-primary-700" : "border-transparent text-ink-2 hover:text-ink")}>
                {l}
              </button>
            ))}
          </div>

          {isLoading ? (
            <Spinner label="AI đang chọn phòng cho bạn…" />
          ) : top ? (
            <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} className="card grid gap-8 p-4 shadow-lg md:grid-cols-[minmax(0,560px)_1fr]">
              <div className="relative overflow-hidden rounded-lg">
                <RoomPhoto src={top.image} alt={top.title} className="h-full max-h-[380px] w-full" />
                <SaveButton id={top.id} className="absolute right-3 top-3" />
              </div>
              <div className="space-y-4 py-2 pr-2">
                <div className="flex flex-wrap gap-2"><Badge tone="Accent" dot>Phù hợp nhất hôm nay</Badge><Badge tone="Violet">Phù hợp {top.match}%</Badge></div>
                <h2 className="text-h2">{top.title}</h2>
                <div className="flex flex-wrap items-baseline gap-1.5"><span className="text-h3 text-primary-700">{fullVnd(top.price)}</span><span className="text-ink-3">/tháng · {top.short_address}</span></div>
                <div className="space-y-3">
                  {Object.entries(top.match_breakdown ?? {}).map(([k, v]) => (
                    <div key={k} className="grid grid-cols-[170px_1fr_44px] items-center gap-4 text-sm">
                      <span className="text-ink-2">{CRIT[k]}</span>
                      <Bar value={v as number} tone="violet" />
                      <span className="text-right font-semibold">{v as number}%</span>
                    </div>
                  ))}
                </div>
                <div className="flex gap-3 rounded-lg bg-violet-50 p-4 text-sm">
                  <Sparkles className="h-[18px] w-[18px] shrink-0 text-violet" />
                  <span>{top.reasons.join(". ")}.</span>
                </div>
                <div className="flex gap-3">
                  <Button size="l" to={`/phong/${top.id}`} iconRight={<ArrowRight className="h-4 w-4" />}>Xem chi tiết</Button>
                  <span className="self-center text-xs text-ink-3">Đăng {timeAgo(top.posted_at)}</span>
                </div>
              </div>
            </motion.div>
          ) : (
            <div className="card p-10 text-center text-ink-2">Chưa có phòng phù hợp. Hãy nới ngân sách hoặc khoảng cách trong hồ sơ nhu cầu.</div>
          )}

          <div className="flex items-center justify-between"><h2 className="text-h3">Các phòng khác dành cho bạn</h2><span className="text-[13px] text-ink-3">Sắp xếp theo mức phù hợp</span></div>
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {isLoading ? Array.from({ length: 4 }, (_, i) => <ListingCardSkeleton key={i} />) : data?.items.map((l, i) => <ListingCard key={l.id} l={l} i={i} />)}
          </div>

          <div className="card flex flex-wrap items-center gap-4 p-5">
            <div className="flex-1">
              <div className="text-h4">Gợi ý chưa đúng ý?</div>
              <div className="text-sm text-ink-2">Cho AI biết lý do, lần sau gợi ý sẽ sát hơn.</div>
            </div>
            {FEEDBACK.map(([k, l]) => <Chip key={k} onClick={() => fb.mutate(k)}>{l}</Chip>)}
          </div>
        </div>
      </div>
    </StudentLayout>
  );
}
