import clsx from "clsx";
import { motion } from "framer-motion";
import { Heart, ImageIcon, MapPin, Sparkles, Star } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, imageUrl } from "../lib/api";
import { useAuth } from "../lib/auth";
import { riskLabel, riskTone, shortVnd, timeAgo } from "../lib/format";
import type { ListingCard as L } from "../lib/types";
import { Badge, useToast } from "./ui";

export function RoomPhoto({
  src,
  fallbacks,
  alt,
  className,
}: {
  src?: string | null;
  fallbacks?: (string | null | undefined)[];
  alt: string;
  className?: string;
}) {
  const candidates = Array.from(
    new Set([src, ...(fallbacks || [])].filter((u): u is string => Boolean(u && u.trim()))),
  );
  const [idx, setIdx] = useState(0);
  const [failedAll, setFailedAll] = useState(false);

  useEffect(() => {
    setIdx(0);
    setFailedAll(false);
  }, [src, fallbacks?.length]);

  const activeSrc = candidates[idx];
  if (!activeSrc || failedAll)
    return (
      <div className={clsx("flex items-center justify-center bg-gradient-to-br from-primary-100 to-violet-50 text-primary-700", className)}>
        <ImageIcon className="h-8 w-8 opacity-60" />
      </div>
    );
  return (
    <img
      src={imageUrl(activeSrc)}
      alt={alt}
      loading="lazy"
      onError={() => {
        if (idx + 1 < candidates.length) setIdx((i) => i + 1);
        else setFailedAll(true);
      }}
      className={clsx("object-cover", className)}
    />
  );
}

export function SaveButton({ id, initial = false, className }: { id: number; initial?: boolean; className?: string }) {
  const [saved, setSaved] = useState(initial);
  const { user } = useAuth();
  const nav = useNavigate();
  const toast = useToast();
  const toggle = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!user) return nav("/dang-nhap");
    setSaved((s) => !s);
    try {
      await api(`/me/saved/${id}`, { method: saved ? "DELETE" : "POST" });
      toast(saved ? "Đã bỏ lưu tin" : "Đã lưu vào Tin đã lưu");
    } catch {
      setSaved(saved);
    }
  };
  return (
    <motion.button
      whileTap={{ scale: 1.2 }}
      onClick={toggle}
      aria-label={saved ? "Bỏ lưu tin" : "Lưu tin"}
      className={clsx("focus-ring flex h-9 w-9 items-center justify-center rounded-full bg-white/95 shadow-sm", className)}
    >
      <Heart className={clsx("h-[18px] w-[18px]", saved ? "fill-danger text-danger" : "text-slate-900")} />
    </motion.button>
  );
}

export function ListingCard({ l, i = 0, onHover, active }: { l: L; i?: number; onHover?: (id: number | null) => void; active?: boolean }) {
  const nav = useNavigate();
  return (
    <motion.article
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1], delay: Math.min(i, 8) * 0.05 }}
      whileHover={{ y: -4 }}
      onMouseEnter={() => onHover?.(l.id)}
      onMouseLeave={() => onHover?.(null)}
      onClick={() => nav(`/phong/${l.id}`)}
      className={clsx("card group cursor-pointer overflow-hidden transition-shadow hover:shadow-lg", active && "ring-2 ring-primary")}
    >
      <div className="relative aspect-[16/10] overflow-hidden">
        <RoomPhoto src={l.image} fallbacks={l.images} alt={l.title} className="h-full w-full transition-transform duration-500 group-hover:scale-[1.04]" />
        <div className="absolute inset-0 bg-gradient-to-b from-black/10 via-transparent to-black/25" />
        {l.source_count > 1 && <span className="absolute left-3 top-3 rounded-full bg-white/95 px-2.5 py-1 text-[11px] font-semibold text-slate-900">Gộp từ {l.source_count} nguồn</span>}
        <SaveButton id={l.id} className="absolute right-3 top-3" />
        {l.match != null && (
          <span className="absolute bottom-3 left-3 inline-flex items-center gap-1 rounded-full bg-violet px-2.5 py-1 text-[11px] font-semibold text-white">
            <Sparkles className="h-3 w-3" /> Phù hợp {l.match}%
          </span>
        )}
      </div>
      <div className="space-y-2 p-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-baseline gap-1">
            <span className="text-[22px] font-bold text-primary-700">{shortVnd(l.price)}</span>
            <span className="text-xs text-ink-3">/tháng</span>
          </div>
          {l.price_tag && <Badge tone={l.price_tag === "Giá tốt" ? "Success" : "Warning"}>{l.price_tag}</Badge>}
        </div>
        <h3 className="line-clamp-2 min-h-[40px] text-[15px] font-semibold leading-snug">{l.title}</h3>
        <div className="flex items-center gap-1.5 text-[13px] text-ink-2">
          <MapPin className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">{l.short_address}</span>
        </div>
        <div className="truncate text-[13px] text-ink-2">{l.meta}</div>
        <div className="flex items-center justify-between gap-2 border-t border-line pt-3">
          <Badge tone={riskTone[l.risk_level]} dot>
            {riskLabel[l.risk_level]}
          </Badge>
          <span className="inline-flex items-center gap-1 text-xs text-ink-2">
            <Star className="h-3.5 w-3.5 text-accent" /> {l.quality_score.toString().replace(".", ",")}/10
          </span>
          <span className="text-xs text-ink-3">{timeAgo(l.posted_at)}</span>
        </div>
      </div>
    </motion.article>
  );
}

export function ListingCardSkeleton() {
  return (
    <div className="card overflow-hidden">
      <div className="skeleton aspect-[16/10]" />
      <div className="space-y-3 p-4">
        <div className="skeleton h-6 w-32 rounded" />
        <div className="skeleton h-4 w-full rounded" />
        <div className="skeleton h-4 w-2/3 rounded" />
        <div className="skeleton h-4 w-1/2 rounded" />
      </div>
    </div>
  );
}
