import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, Clock } from "lucide-react";
import { useEffect, useState } from "react";
import { DashboardLayout } from "../../components/Dashboard";
import { useNotificationPrefs } from "../../components/NotificationBell";
import { Badge, Bar, Button, Card, Field, Spinner, TextArea, Toggle, useToast } from "../../components/ui";
import { api } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import type { User } from "../../lib/types";

type Verification = { label: string; text: string; done: boolean };
type ProfileResponse = { user: User; room_count: number; address: string; trust: { response_hours: number; report_rate: number; first_approval: number }; verification: Verification[] };

export default function LandlordProfile() {
  const { setUser } = useAuth();
  const toast = useToast();
  const { data } = useQuery<ProfileResponse>({ queryKey: ["ll-profile"], queryFn: () => api("/landlord/profile") });
  const [f, setF] = useState({ full_name: "", phone: "", bio: "" });
  const { prefs, set: setPref } = useNotificationPrefs();
  useEffect(() => {
    data && setF({ full_name: data.user.full_name, phone: data.user.phone ?? "", bio: data.user.bio ?? "" });
  }, [data]);
  const save = useMutation({ mutationFn: () => api<User>("/landlord/profile", { method: "PUT", body: f }), onSuccess: (u) => (setUser(u), toast("Đã lưu hồ sơ")) });
  if (!data) return <DashboardLayout role="landlord" title="Hồ sơ chủ trọ"><Spinner /></DashboardLayout>;
  const done = data.verification.filter((v) => v.done).length;

  return (
    <DashboardLayout role="landlord" title="Hồ sơ chủ trọ" sub="Thông tin hiển thị với sinh viên khi xem tin của bạn">
      <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <div className="space-y-6">
          <Card className="space-y-5">
            <div className="flex flex-wrap items-center gap-5">
              <span className="flex h-[72px] w-[72px] items-center justify-center rounded-full bg-accent text-h3 text-white">{data.user.initials}</span>
              <div className="flex-1 space-y-1.5">
                <div className="text-h3">{data.user.full_name}</div>
                <div className="text-sm text-ink-3">Chủ trọ từ {new Date(data.user.created_at).getFullYear()} · {data.room_count} phòng tại Liên Chiểu</div>
                <div className="flex gap-2">{data.user.phone_verified && <Badge tone="Success" dot>Đã xác minh</Badge>}<Badge tone="Info">Phản hồi trong khoảng {data.trust.response_hours} giờ</Badge></div>
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Tên hiển thị" value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} />
              <Field label="Số điện thoại" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} />
              <Field label="Địa chỉ khu trọ" value={data.address} disabled className="sm:col-span-2" />
            </div>
            <TextArea label="Giới thiệu ngắn" value={f.bio} onChange={(e) => setF({ ...f, bio: e.target.value })} maxLength={500} />
            <div className="flex justify-end"><Button loading={save.isPending} onClick={() => save.mutate()}>Lưu thay đổi</Button></div>
          </Card>
          <Card pad="px-6 pt-6 pb-2">
            <h2 className="text-h4">Thông báo cho chủ trọ</h2>
            {([["contact", "Có sinh viên bấm xem bài gốc hoặc liên hệ"], ["approved", "Tin được duyệt hoặc bị ẩn sau kiểm duyệt"], ["price_tip", "Gợi ý giá hằng tuần từ AI"], ["monthly", "Bản tin thị trường hằng tháng"]] as const).map(([k, l]) => (
              <div key={k} className="flex items-center justify-between border-t border-line py-4 first-of-type:mt-3"><span>{l}</span><Toggle checked={!!prefs?.[k]} onChange={(v) => setPref(k, v)} label={l} /></div>
            ))}
          </Card>
        </div>
        <div className="space-y-6">
          <Card className="space-y-4">
            <div className="flex items-center justify-between"><h2 className="text-h4">Xác minh tài khoản</h2><Badge tone="Info">{done}/{data.verification.length}</Badge></div>
            <Bar value={(done / data.verification.length) * 100} tone="success" height={6} />
            {data.verification.map((v) => (
              <div key={v.label} className="flex gap-3">
                {v.done ? <Check className="h-5 w-5 text-success" /> : <Clock className="h-5 w-5 text-warning" />}
                <div><div className="text-sm font-semibold">{v.label}</div><div className="caption">{v.text}</div></div>
              </div>
            ))}
          </Card>
          <Card className="space-y-3">
            <h2 className="text-h4">Độ tin cậy</h2>
            {[["Tỷ lệ tin bị báo cáo", `${data.trust.report_rate}%`, "text-success"], ["Tin được duyệt ngay lần đầu", `${data.trust.first_approval}%`, "text-success"], ["Thời gian phản hồi trung bình", `${data.trust.response_hours} giờ`, ""]].map(([l, v, c]) => (
              <div key={l} className="flex justify-between text-sm"><span className="text-ink-2">{l}</span><span className={`font-semibold ${c}`}>{v}</span></div>
            ))}
            <p className="caption">Chủ trọ đã xác minh được ưu tiên hiển thị và gắn nhãn tin cậy trên tin đăng.</p>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
