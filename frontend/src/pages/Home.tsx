import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ArrowRight, BarChart3, Brain, Copy, Database, ExternalLink, Flag, GraduationCap, ShieldAlert, ShieldCheck, Sparkles, TrendingDown, Users, type LucideIcon,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { AISearchBar } from "../components/AISearchBar";
import { Aurora } from "../components/Brand";
import { StudentLayout } from "../components/Layout";
import { ListingCard, ListingCardSkeleton, RoomPhoto } from "../components/ListingCard";
import { Badge, Bar, Button, Card, Chip, IconBox, SectionHead, StatCard, fadeUp } from "../components/ui";
import { api } from "../lib/api";
import { num, shortVnd, tr } from "../lib/format";
import type { ListingCard as L } from "../lib/types";

type DistrictStat = { district: string; median: number; change_30d: number };
type HomeResponse = {
  featured: L[];
  districts: DistrictStat[];
  active_listings: number;
  sources: number;
  personalized: boolean;
  school: string;
  new_this_week: number;
  city_median: number;
  hidden_risky: number;
};
type FeatureItem = [LucideIcon, string, string];

const EXAMPLES = ["Gần ĐH Đông Á", "Dưới 2 triệu", "Có gác lửng", "Ở ghép 2 người", "Giờ giấc tự do"];

function HeroVisual({ card, median }: { card?: L; median: number }) {
  return (
    <div className="relative hidden h-[560px] lg:block">
      <motion.div {...fadeUp(2)} className="absolute right-0 top-14 w-[340px] rotate-[-2deg] animate-float">
        {card ? (
          <div className="card overflow-hidden shadow-lg">
            <div className="relative aspect-[16/10]">
              <RoomPhoto src={card.image} alt={card.title} className="h-full w-full" />
              <span className="absolute left-3 top-3 rounded-full bg-white/95 px-2.5 py-1 text-[11px] font-semibold text-slate-900">Gộp từ {Math.max(2, card.source_count)} nguồn</span>
              <span className="absolute bottom-3 left-3 inline-flex items-center gap-1 rounded-full bg-violet px-2.5 py-1 text-[11px] font-semibold text-white">
                <Sparkles className="h-3 w-3" /> Phù hợp {card.match ?? 94}%
              </span>
            </div>
            <div className="space-y-1.5 p-4">
              <div className="flex items-center justify-between">
                <span className="text-xl font-bold text-primary-700">{shortVnd(card.price)}</span>
                <Badge tone="Success">Giá tốt</Badge>
              </div>
              <div className="line-clamp-1 text-sm font-semibold">{card.title}</div>
              <div className="text-xs text-ink-2">{card.meta}</div>
            </div>
          </div>
        ) : (
          <div className="skeleton h-80 rounded-xl" />
        )}
      </motion.div>
      <motion.div {...fadeUp(3)} className="absolute -left-6 top-0 w-[300px] animate-float rounded-xl border border-white/60 bg-surface/80 p-4 shadow-lg backdrop-blur-xl [animation-delay:-2s]">
        <div className="mb-3 flex items-center gap-2 text-[13px] font-semibold text-violet">
          <Sparkles className="h-4 w-4" /> AI đã hiểu yêu cầu của bạn
        </div>
        <div className="flex flex-wrap gap-2">
          {["≤ 2 triệu", "ĐH Đông Á · 2 km", "Chỗ để xe", "2 người"].map((c) => (
            <Chip key={c} state="ai">{c}</Chip>
          ))}
        </div>
      </motion.div>
      <motion.div {...fadeUp(4)} className="absolute bottom-24 left-0 w-[260px] animate-float rounded-xl border border-line bg-surface p-4 shadow-lg [animation-delay:-4s]">
        <div className="caption">Giá trung vị · Liên Chiểu</div>
        <div className="mt-1 flex items-center gap-2">
          <span className="text-xl font-bold">{tr(median)}</span>
          <Badge tone="Success">-2%</Badge>
        </div>
        <div className="mt-3 flex h-14 items-end gap-1.5">
          {[38, 52, 46, 62, 58, 80, 54].map((h, i) => (
            <div key={i} className={i === 5 ? "flex-1 rounded-t bg-primary" : "flex-1 rounded-t bg-primary-100"} style={{ height: `${h}%` }} />
          ))}
        </div>
      </motion.div>
      <motion.div {...fadeUp(5)} className="absolute bottom-4 right-6 flex w-[280px] items-center gap-3 rounded-xl border border-line bg-surface p-3.5 shadow-lg">
        <IconBox icon={ShieldAlert} tone="danger" size={36} />
        <div>
          <div className="text-[13px] font-semibold">Đã ẩn 1 tin nghi lừa đảo</div>
          <div className="caption">Giá thấp bất thường, đòi chuyển cọc trước</div>
        </div>
      </motion.div>
    </div>
  );
}

export default function Home() {
  const nav = useNavigate();
  const { data } = useQuery<HomeResponse>({ queryKey: ["home"], queryFn: () => api("/home") });
  const featured: L[] = data?.featured ?? [];
  const districts = data?.districts ?? [];
  const lc = districts.find((d) => d.district === "Liên Chiểu");

  return (
    <StudentLayout>
      {/* Hero */}
      <section className="relative isolate overflow-hidden">
        <Aurora />
        <div className="container-page grid items-center gap-10 pb-16 pt-12 lg:grid-cols-[1.1fr_0.9fr] lg:pb-24 lg:pt-20">
          <div className="space-y-6">
            <motion.div {...fadeUp(0)}>
              <Badge tone="Violet" className="bg-surface/80 shadow-sm">
                <Sparkles className="h-3.5 w-3.5" /> Trợ lý AI tìm trọ dành riêng cho sinh viên Đà Nẵng
              </Badge>
            </motion.div>
            <motion.h1 {...fadeUp(1)} className="text-[40px] font-extrabold leading-[1.1] tracking-tight sm:text-display-l xl:text-[60px]">
              Tìm phòng trọ ưng ý
              <br />
              <span className="bg-gradient-to-r from-[#F97316] to-[#C2410C] bg-clip-text text-transparent">chỉ bằng một câu nói</span>
            </motion.h1>
            <motion.p {...fadeUp(2)} className="max-w-xl text-lg leading-relaxed text-ink-2">
              Phòng Ơi gom tin đăng từ nhiều trang về một nơi, hiểu yêu cầu bằng tiếng Việt tự nhiên, cảnh báo tin có dấu hiệu lừa đảo và gợi ý phòng hợp túi tiền, gần
              trường của bạn.
            </motion.p>
            <motion.div {...fadeUp(3)} className="max-w-[600px]">
              <AISearchBar />
            </motion.div>
            <motion.div {...fadeUp(4)} className="flex flex-wrap items-center gap-2">
              <span className="text-[13px] text-ink-3">Thử ngay:</span>
              {EXAMPLES.map((e) => (
                <Chip key={e} onClick={() => nav(`/tim-kiem?q=${encodeURIComponent(e)}`)}>
                  {e}
                </Chip>
              ))}
            </motion.div>
            <motion.div {...fadeUp(5)} className="flex flex-wrap gap-10 pt-4">
              {[
                [`${num(data?.active_listings ?? 380)}+`, "tin đăng đang hiển thị"],
                [`${data?.sources ?? 3}+`, "nguồn được tổng hợp"],
                ["100%", "tin dẫn về bài gốc"],
              ].map(([v, l]) => (
                <div key={l}>
                  <div className="text-[28px] font-bold">{v}</div>
                  <div className="caption">{l}</div>
                </div>
              ))}
            </motion.div>
          </div>
          <HeroVisual card={featured[0]} median={lc?.median ?? 1_800_000} />
        </div>
      </section>

      {/* Cách hoạt động */}
      <section className="container-page py-16">
        <SectionHead center eyebrow="Cách Phòng Ơi hoạt động" title="Một lần tìm, thay cho hàng chục tab trình duyệt" sub="Hệ thống tự động gom tin, đọc hiểu, kiểm tra và xếp hạng để bạn chỉ còn việc chọn phòng ưng ý." />
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {([
            [Database, "Gom tin từ nhiều nguồn", "Tin đăng công khai được thu thập tự động mỗi ngày, tin trùng được gộp lại."],
            [Brain, "AI đọc hiểu tin đăng", "Giá, diện tích, tiện ích, chi phí điện nước được trích xuất thành dữ liệu rõ ràng."],
            [ShieldCheck, "Chấm điểm và cảnh báo", "Mỗi tin có điểm chất lượng, mức rủi ro và so sánh với giá khu vực."],
            [GraduationCap, "Gợi ý đúng sinh viên", "Xếp hạng theo ngân sách, khoảng cách tới trường và tiện ích bạn cần."],
          ] satisfies FeatureItem[]).map(([Icon, t, d], i) => (
            <motion.div key={t} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.06, duration: 0.4 }}>
              <Card className="h-full">
                <div className="flex items-start justify-between">
                  <IconBox icon={Icon} />
                  <span className="text-3xl font-extrabold text-line-strong/70">0{i + 1}</span>
                </div>
                <h3 className="mt-5 text-h4">{t}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-2">{d}</p>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Gợi ý gần trường */}
      <section className="container-page py-16">
        <SectionHead
          eyebrow={data?.personalized ? "Gợi ý bởi AI · theo hồ sơ nhu cầu của bạn" : "Gợi ý bởi AI · phòng nổi bật gần trường"}
          icon={Sparkles}
          tone="text-violet"
          title={`Phòng hợp với bạn quanh ${data?.school ?? "Bách khoa ĐN"}`}
          sub="Xếp hạng theo ngân sách, khoảng cách tới trường và tiện ích. Tin nào cũng kèm lý do vì sao được gợi ý."
          action={<Button variant="secondary" to="/tim-kiem?q=gần Bách khoa dưới 2,8 triệu" iconRight={<ArrowRight className="h-4 w-4" />}>Xem tất cả {num(data?.active_listings)} phòng</Button>}
        />
        <div className="mt-6 flex flex-wrap gap-2">
          {["Dưới 2 triệu", "Có gác lửng", "Cách trường dưới 2 km", "Giờ giấc tự do", "Cho nuôi thú cưng", "Có chỗ để xe"].map((c) => (
            <Chip key={c} onClick={() => nav(`/tim-kiem?q=${encodeURIComponent(c + " gần Bách khoa")}`)}>{c}</Chip>
          ))}
        </div>
        <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {featured.length ? featured.map((l, i) => <ListingCard key={l.id} l={l} i={i} />) : Array.from({ length: 4 }, (_, i) => <ListingCardSkeleton key={i} />)}
        </div>
      </section>

      {/* An toàn */}
      <section className="container-page py-16">
        <div className="grid items-center gap-12 rounded-2xl border border-line bg-surface p-6 shadow-sm sm:p-12 lg:grid-cols-[1fr_520px]">
          <div className="space-y-6">
            <div className="flex items-center gap-2 text-sm font-semibold text-success">
              <ShieldCheck className="h-[18px] w-[18px]" /> An toàn là ưu tiên số 1
            </div>
            <h2 className="text-[28px] font-bold leading-tight sm:text-h1">AI lọc tin lừa đảo trước khi bạn kịp chuyển cọc</h2>
            <p className="text-lg text-ink-2">Mỗi tin đăng được chấm điểm rủi ro dựa trên giá, hình ảnh, nội dung và lịch sử người đăng. Tin nghi vấn được gắn cảnh báo kèm lý do cụ thể.</p>
            <div className="space-y-5">
              {([
                [TrendingDown, "So sánh với giá trung vị khu vực", "Giá rẻ bất thường so với cùng quận, cùng diện tích sẽ bị đánh dấu."],
                [Copy, "Phát hiện ảnh và nội dung trùng lặp", "Một bộ ảnh xuất hiện ở nhiều địa chỉ khác nhau là dấu hiệu tin giả."],
                [Flag, "Sinh viên cùng báo cáo tin xấu", "Tin bị báo cáo được đưa lên hàng chờ kiểm duyệt ngay lập tức."],
                [ExternalLink, "Luôn dẫn về bài đăng gốc", "Bạn liên hệ thẳng chủ trọ, không qua trung gian, không mất phí."],
              ] satisfies FeatureItem[]).map(([Icon, t, d]) => (
                <div key={t} className="flex gap-4">
                  <IconBox icon={Icon} tone="success" size={44} />
                  <div>
                    <div className="text-h4">{t}</div>
                    <div className="text-sm text-ink-2">{d}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="card space-y-4 p-6 shadow-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-semibold">
                <ShieldAlert className="h-5 w-5 text-danger" /> Phân tích rủi ro tin đăng
              </div>
              <Badge tone="Danger" dot>Rủi ro cao</Badge>
            </div>
            <div className="flex items-center gap-3">
              <RoomPhoto src="/rooms/room-3.jpg" alt="" className="h-[72px] w-[72px] rounded-md" />
              <div>
                <div className="text-sm font-semibold">Phòng 30 m² gần biển Mỹ Khê, chỉ 900 nghìn/tháng</div>
                <div className="caption">Đăng 2 giờ trước · nhóm Facebook “Phòng trọ Đà Nẵng”</div>
              </div>
            </div>
            <div className="h-px bg-line" />
            <div className="label-s text-ink-2">Lý do AI cảnh báo</div>
            {["Giá thấp hơn 65% so với trung vị khu Sơn Trà (2,6 triệu)", "Bộ ảnh trùng với 3 tin ở các địa chỉ khác", "Yêu cầu chuyển cọc trước khi xem phòng", "Tài khoản đăng tin mới tạo 3 ngày"].map((r) => (
              <div key={r} className="flex items-center gap-3 text-sm">
                <span className="h-2 w-2 shrink-0 rounded-full bg-danger" /> {r}
              </div>
            ))}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-ink-2">Điểm rủi ro</span>
                <span className="font-semibold text-danger">86/100</span>
              </div>
              <Bar value={86} tone="danger" />
            </div>
            <div className="flex items-center gap-2 rounded-md bg-danger-50 p-3 text-xs text-danger">
              <ShieldAlert className="h-4 w-4" /> Tin đã được ẩn khỏi kết quả tìm kiếm và chờ kiểm duyệt
            </div>
          </div>
        </div>
      </section>

      {/* Giá thị trường */}
      <section className="container-page py-16">
        <SectionHead eyebrow="Minh bạch giá thuê" icon={BarChart3} title="Biết giá trước khi đi xem phòng" sub="Giá trung vị được tính lại mỗi ngày từ hàng nghìn tin đăng, giúp bạn nhận ra phòng bị hét giá hoặc rẻ bất thường." />
        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_400px]">
          <Card>
            <h3 className="text-h4">Giá thuê trung vị · phòng 15–25 m²</h3>
            <div className="caption mt-1">Cập nhật hôm nay từ {num(data?.active_listings)} tin đăng tại Đà Nẵng</div>
            <div className="mt-6 space-y-4">
              {districts
                .filter((d) => d.district !== "Hòa Vang")
                .map((d, i) => (
                  <div key={d.district} className="grid grid-cols-[110px_1fr_64px_56px] items-center gap-4 sm:grid-cols-[130px_1fr_70px_64px]">
                    <span className="text-[15px] font-medium">{d.district}</span>
                    <Bar value={(d.median / 3_500_000) * 100} tone={i === 0 ? "accent" : "primary"} height={12} />
                    <span className="text-right text-sm font-semibold">{tr(d.median)}</span>
                    <span className={d.change_30d > 0 ? "text-xs font-semibold text-warning" : d.change_30d < 0 ? "text-xs font-semibold text-success" : "text-xs text-ink-3"}>
                      {d.change_30d > 0 ? "+" : ""}
                      {d.change_30d}%
                    </span>
                  </div>
                ))}
            </div>
            <div className="mt-5 flex items-center gap-2 text-xs text-ink-2">
              <span className="h-2 w-2 rounded-full bg-accent" /> Khu vực giá tốt nhất cho sinh viên tháng này
            </div>
          </Card>
          <div className="space-y-4">
            <StatCard label="Tin mới trong tuần" value={num(data?.new_this_week)} delta="Cập nhật liên tục" />
            <StatCard label="Giá trung vị Đà Nẵng" value={shortVnd(data?.city_median)} delta="Phòng đang hiển thị" tone="muted" />
            <StatCard label="Tin bị ẩn vì nghi lừa đảo" value={num(data?.hidden_risky)} delta="Không hiển thị trong kết quả" tone="muted" />
            <Button variant="secondary" full size="l" to="/gia-thi-truong" iconRight={<ArrowRight className="h-4 w-4" />}>
              Xem phân tích giá theo khu vực
            </Button>
          </div>
        </div>
      </section>

      {/* Cảm nhận */}
      <section className="container-page py-16">
        <SectionHead center eyebrow="Sinh viên nói gì" icon={Users} title="Tìm phòng nhẹ đầu hơn hẳn" />
        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {[
            ["“Mình gõ ‘phòng dưới 2 triệu gần Bách khoa, có gác’ là ra đúng mấy phòng cần. Khỏi lướt group Facebook cả tuần.”", "Minh Anh", "Sinh viên năm 2 · ĐH Bách khoa – ĐHĐN", "MA"],
            ["“Tin rẻ bất thường bị cảnh báo ngay, kèm lý do. Năm nhất mình suýt chuyển cọc cho một bài y như vậy.”", "Quốc Huy", "Sinh viên năm 3 · ĐH Duy Tân", "QH"],
            ["“Biểu đồ giá theo quận giúp mình biết phòng đang xem có bị hét giá không, trước khi mất công đi xem.”", "Thu Trang", "Sinh viên năm 1 · ĐH Kinh tế – ĐHĐN", "TT"],
          ].map(([q, n, s, ini]) => (
            <Card key={n} className="flex flex-col gap-6">
              <p className="flex-1 text-[17px] leading-relaxed">{q}</p>
              <div className="flex items-center gap-3">
                <span className="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-[#FB923C] to-[#C2410C] text-sm font-semibold text-white">{ini}</span>
                <div>
                  <div className="text-sm font-semibold">{n}</div>
                  <div className="caption">{s}</div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="container-page py-16">
        <div className="relative isolate overflow-hidden rounded-2xl border border-primary-100 bg-gradient-to-r from-primary-50 to-primary-100 px-6 py-16 text-center shadow-sm">
          <div className="absolute -left-20 -top-28 -z-10 h-80 w-80 rounded-full blur-[100px]" style={{ background: "rgb(var(--aurora-1))", opacity: 0.35 }} />
          <div className="absolute -bottom-24 right-10 -z-10 h-80 w-80 rounded-full blur-[100px]" style={{ background: "rgb(var(--aurora-2))", opacity: 0.25 }} />
          <Badge tone="Accent">Miễn phí cho sinh viên</Badge>
          <h2 className="mx-auto mt-5 max-w-3xl text-[32px] font-extrabold leading-tight sm:text-display-l">Nói cho AI biết bạn cần gì, phần còn lại để Phòng Ơi lo</h2>
          <p className="mx-auto mt-4 max-w-xl text-lg text-ink-2">Một câu mô tả là đủ: ngân sách, trường, kiểu phòng. Không môi giới, không phí ẩn, luôn dẫn về bài gốc.</p>
          <Button size="l" className="mt-8" to="/tim-kiem" iconRight={<ArrowRight className="h-4 w-4" />}>
            Bắt đầu tìm với AI
          </Button>
        </div>
      </section>
    </StudentLayout>
  );
}
