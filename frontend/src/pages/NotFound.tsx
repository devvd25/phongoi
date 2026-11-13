import { Search } from "lucide-react";
import { StudentLayout } from "../components/Layout";
import { Button } from "../components/ui";

export default function NotFound() {
  return (
    <StudentLayout>
      <div className="container-page flex flex-col items-center py-24 text-center">
        <div className="flex h-28 w-28 items-center justify-center rounded-full bg-gradient-to-br from-primary-100 to-violet-50"><Search className="h-12 w-12 text-primary" /></div>
        <h1 className="mt-6 text-h1">Không tìm thấy trang</h1>
        <p className="mt-2 text-lg text-ink-2">Đường dẫn có thể đã thay đổi hoặc không còn tồn tại.</p>
        <Button className="mt-6" size="l" to="/">Về trang chủ</Button>
      </div>
    </StudentLayout>
  );
}
