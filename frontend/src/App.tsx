import { lazy, Suspense, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { Spinner } from "./components/ui";
import { useAuth } from "./lib/auth";
import type { Role } from "./lib/types";

const Home = lazy(() => import("./pages/Home"));
const Search = lazy(() => import("./pages/Search"));
const Listing = lazy(() => import("./pages/Listing"));
const Recommendations = lazy(() => import("./pages/Recommendations"));
const Market = lazy(() => import("./pages/Market"));
const Saved = lazy(() => import("./pages/Saved"));
const Onboarding = lazy(() => import("./pages/Onboarding"));
const Account = lazy(() => import("./pages/Account"));
const Auth = lazy(() => import("./pages/Auth"));
const NotFound = lazy(() => import("./pages/NotFound"));
const LDashboard = lazy(() => import("./pages/landlord/Dashboard"));
const LRooms = lazy(() => import("./pages/landlord/Rooms"));
const LPost = lazy(() => import("./pages/landlord/Post"));
const LStats = lazy(() => import("./pages/landlord/Stats"));
const LProfile = lazy(() => import("./pages/landlord/Profile"));
const AOverview = lazy(() => import("./pages/admin/Overview"));
const ASources = lazy(() => import("./pages/admin/Sources"));
const APipeline = lazy(() => import("./pages/admin/Pipeline"));
const AModeration = lazy(() => import("./pages/admin/Moderation"));
const AReports = lazy(() => import("./pages/admin/Reports"));
const AAICost = lazy(() => import("./pages/admin/AICost"));
const ACatalog = lazy(() => import("./pages/admin/Catalog"));

function Require({ roles, children }: { roles?: Role[]; children: ReactNode }) {
  const { user, ready } = useAuth();
  const loc = useLocation();
  if (!ready) return <Spinner />;
  if (!user) return <Navigate to={`/dang-nhap?next=${encodeURIComponent(loc.pathname + loc.search)}`} replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Suspense fallback={<Spinner />}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/tim-kiem" element={<Search />} />
        <Route path="/phong/:id" element={<Listing />} />
        <Route path="/gia-thi-truong" element={<Market />} />
        <Route path="/dang-nhap" element={<Auth mode="login" />} />
        <Route path="/dang-ky" element={<Auth mode="register" />} />
        <Route path="/quen-mat-khau" element={<Auth mode="forgot" />} />
        <Route path="/dat-lai-mat-khau" element={<Auth mode="reset" />} />
        <Route path="/goi-y" element={<Require roles={["student"]}><Recommendations /></Require>} />
        <Route path="/da-luu" element={<Require roles={["student"]}><Saved /></Require>} />
        <Route path="/ho-so-nhu-cau" element={<Require roles={["student"]}><Onboarding /></Require>} />
        <Route path="/tai-khoan" element={<Require><Account /></Require>} />
        <Route path="/chu-tro" element={<Require roles={["landlord", "admin"]}><LDashboard /></Require>} />
        <Route path="/chu-tro/phong" element={<Require roles={["landlord", "admin"]}><LRooms /></Require>} />
        <Route path="/chu-tro/dang-tin" element={<Require roles={["landlord", "admin"]}><LPost /></Require>} />
        <Route path="/chu-tro/thong-ke" element={<Require roles={["landlord", "admin"]}><LStats /></Require>} />
        <Route path="/chu-tro/ho-so" element={<Require roles={["landlord", "admin"]}><LProfile /></Require>} />
        <Route path="/admin" element={<Require roles={["admin"]}><AOverview /></Require>} />
        <Route path="/admin/nguon" element={<Require roles={["admin"]}><ASources /></Require>} />
        <Route path="/admin/pipeline" element={<Require roles={["admin"]}><APipeline /></Require>} />
        <Route path="/admin/kiem-duyet" element={<Require roles={["admin"]}><AModeration /></Require>} />
        <Route path="/admin/bao-cao" element={<Require roles={["admin"]}><AReports /></Require>} />
        <Route path="/admin/chi-phi-ai" element={<Require roles={["admin"]}><AAICost /></Require>} />
        <Route path="/admin/danh-muc" element={<Require roles={["admin"]}><ACatalog /></Require>} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}
