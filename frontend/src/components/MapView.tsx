import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { ArrowLeft, Loader2, LocateFixed, MapPin, Waves } from "lucide-react";
import { Fragment, useCallback, useEffect, useMemo, useState } from "react";
import { Circle, CircleMarker, MapContainer, Marker, TileLayer, Tooltip, useMap } from "react-leaflet";
import { tr } from "../lib/format";
import { ARCHIPELAGO_FEATURE_COUNT, ARCHIPELAGO_GROUPS, type ArchipelagoFeature } from "./archipelagoData";

type Pin = { id: number; lat: number; lng: number; price: number };
type UserLocation = { lat: number; lng: number; accuracy: number };
type LocationState = "idle" | "locating" | "success" | "error";

const ARCHIPELAGO_VIEW_BOUNDS: [[number, number], [number, number]] = [[6.65, 108], [17.3, 117.55]];
const ARCHIPELAGO_FEATURE_STYLES: Record<ArchipelagoFeature["kind"], L.PathOptions> = {
  island: { color: "#FFFFFF", weight: 1.5, fillColor: "#EA580C", fillOpacity: 1, className: "archipelago-feature" },
  reef: { color: "#EA580C", weight: 2, fillColor: "#FDBA74", fillOpacity: 0.95, className: "archipelago-feature" },
  shoal: { color: "#C2410C", weight: 2, fillColor: "#FFF7ED", fillOpacity: 1, className: "archipelago-feature" },
};
const ARCHIPELAGO_FEATURE_LABELS: Record<ArchipelagoFeature["kind"], string> = {
  island: "Điểm đảo",
  reef: "Điểm đá/rạn san hô",
  shoal: "Điểm bãi/cồn",
};

const pinIcon = (price: number, active: boolean, distance?: string) =>
  L.divIcon({
    className: "",
    html: `<div class="price-pin ${active ? "is-active" : ""}"><span>${tr(price)}</span>${distance ? `<span class="price-pin-distance">${distance}</span>` : ""}</div>`,
    iconSize: [0, 0],
  });
const schoolIcon = (name: string) =>
  L.divIcon({
    className: "",
    html: `<div class="school-pin"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 10 12 5 2 10l10 5 10-5Z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>${name}</div>`,
    iconSize: [0, 0],
  });
const userLocationIcon = L.divIcon({
  className: "",
  html: '<div class="user-location-pin"><span></span></div>',
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});
const archipelagoIcon = (name: string, featureCount: number) =>
  L.divIcon({
    className: "",
    html: `<div class="archipelago-pin"><span></span><div><strong>${name}</strong><small>${featureCount} điểm đảo, đá và bãi</small></div></div>`,
    iconSize: [0, 0],
  });

function distanceMetres(from: UserLocation, pin: Pin) {
  return L.latLng(from.lat, from.lng).distanceTo([pin.lat, pin.lng]);
}

function formatDistance(metres: number) {
  if (metres < 1_000) return `${Math.max(10, Math.round(metres / 10) * 10).toLocaleString("vi-VN")} m`;
  return `${(metres / 1_000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} km`;
}

function Fit({ pins, center, userLocation, showArchipelagos }: { pins: Pin[]; center?: [number, number]; userLocation?: UserLocation | null; showArchipelagos: boolean }) {
  const map = useMap();
  useEffect(() => {
    map.invalidateSize({ animate: false, pan: false });
    if (showArchipelagos) {
      map.fitBounds(ARCHIPELAGO_VIEW_BOUNDS, { padding: [24, 24], maxZoom: 6 });
    } else if (userLocation) {
      const points: [number, number][] = [[userLocation.lat, userLocation.lng], ...pins.map((p) => [p.lat, p.lng] as [number, number])];
      if (points.length === 1) map.setView(points[0], 15);
      else map.fitBounds(L.latLngBounds(points).pad(0.12), { padding: [32, 32], maxZoom: 15 });
    } else if (center) map.setView(center, 14);
    else if (pins.length) map.fitBounds(L.latLngBounds(pins.map((p) => [p.lat, p.lng] as [number, number])).pad(0.15));
  }, [map, pins, center?.[0], center?.[1], userLocation?.lat, userLocation?.lng, showArchipelagos]);
  return null;
}

export function MapView({
  pins,
  activeId,
  onPinClick,
  school,
  radiusKm,
  className,
  enableGeolocation = true,
}: {
  pins: Pin[];
  activeId?: number | null;
  onPinClick?: (id: number) => void;
  school?: { name: string; lat: number; lng: number } | null;
  radiusKm?: number | null;
  className?: string;
  enableGeolocation?: boolean;
}) {
  const [userLocation, setUserLocation] = useState<UserLocation | null>(null);
  const [locationState, setLocationState] = useState<LocationState>("idle");
  const [locationMessage, setLocationMessage] = useState("");
  const [showArchipelagos, setShowArchipelagos] = useState(false);
  const center: [number, number] | undefined = school ? [school.lat, school.lng] : undefined;

  const distanceData = useMemo(() => {
    if (!userLocation) return { pins: pins.map((pin) => ({ ...pin, distance: undefined, distanceMetres: undefined })), nearestIds: new Set<number>(), nearestDistance: undefined };
    const measured = pins.map((pin) => {
      const metres = distanceMetres(userLocation, pin);
      return { ...pin, distance: formatDistance(metres), distanceMetres: metres };
    });
    const nearest = [...measured].sort((a, b) => a.distanceMetres - b.distanceMetres).slice(0, 5);
    return {
      pins: measured,
      nearestIds: new Set(nearest.map((pin) => pin.id)),
      nearestDistance: nearest[0]?.distance,
    };
  }, [pins, userLocation]);

  const locate = useCallback(() => {
    if (!navigator.geolocation) {
      setLocationState("error");
      setLocationMessage("Trình duyệt này không hỗ trợ định vị. Bạn có thể chọn khu vực bằng bộ lọc.");
      return;
    }

    setLocationState("locating");
    setLocationMessage("Đang xác định vị trí của bạn…");
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setUserLocation({ lat: coords.latitude, lng: coords.longitude, accuracy: coords.accuracy });
        setLocationState("success");
        setLocationMessage(`Đã xác định vị trí của bạn · sai số khoảng ${Math.round(coords.accuracy).toLocaleString("vi-VN")} m`);
      },
      (error) => {
        setLocationState("error");
        if (error.code === error.PERMISSION_DENIED) {
          setLocationMessage("Bạn đã từ chối định vị. Hãy bật quyền Vị trí trong trình duyệt rồi thử lại.");
        } else if (error.code === error.TIMEOUT) {
          setLocationMessage("Định vị mất quá nhiều thời gian. Hãy bật GPS hoặc Wi-Fi rồi thử lại.");
        } else {
          setLocationMessage("Chưa xác định được vị trí. Hãy bật GPS hoặc Wi-Fi rồi thử lại.");
        }
      },
      { enableHighAccuracy: true, maximumAge: 60_000, timeout: 10_000 },
    );
  }, []);

  const locateLabel = locationState === "error" ? "Thử định vị lại" : userLocation ? "Cập nhật vị trí hiện tại" : locationState === "locating" ? "Đang xác định vị trí" : "Dùng vị trí hiện tại";

  return (
    <div className={`relative isolate ${className ?? ""}`}>
      <MapContainer center={center ?? [16.0544, 108.2022]} zoom={13} scrollWheelZoom className="h-full w-full" attributionControl>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />
        <Fit pins={pins} center={center} userLocation={userLocation} showArchipelagos={showArchipelagos} />
        {!showArchipelagos && school && radiusKm && (
          <Circle center={[school.lat, school.lng]} radius={radiusKm * 1000} pathOptions={{ color: "#EA580C", weight: 2, dashArray: "8 8", fillColor: "#EA580C", fillOpacity: 0.06 }} />
        )}
        {!showArchipelagos && userLocation && (
          <>
            <Circle
              center={[userLocation.lat, userLocation.lng]}
              radius={Math.max(userLocation.accuracy, 12)}
              pathOptions={{ color: "#2563EB", weight: 1.5, fillColor: "#3B82F6", fillOpacity: 0.12 }}
            />
            <Marker position={[userLocation.lat, userLocation.lng]} icon={userLocationIcon} alt="Vị trí của bạn" zIndexOffset={2_000} />
          </>
        )}
        {!showArchipelagos && school && <Marker position={[school.lat, school.lng]} icon={schoolIcon(school.name)} alt={school.name} />}
        {!showArchipelagos && distanceData.pins.map((p) => (
          <Marker
            key={p.id}
            position={[p.lat, p.lng]}
            icon={pinIcon(p.price, p.id === activeId, distanceData.nearestIds.has(p.id) && p.distance ? `~${p.distance}` : undefined)}
            alt={`Phòng ${tr(p.price)}${p.distance ? `, ước tính cách bạn ${p.distance}` : ""}`}
            zIndexOffset={p.id === activeId ? 1000 : 0}
            eventHandlers={{ click: () => onPinClick?.(p.id) }}
          />
        ))}
        {ARCHIPELAGO_GROUPS.map((archipelago) => (
          <Fragment key={archipelago.name}>
            {archipelago.features.map((feature) => (
              <CircleMarker
                key={`${archipelago.name}-${feature.name}`}
                center={feature.position}
                radius={feature.kind === "island" ? 5 : 4}
                pathOptions={ARCHIPELAGO_FEATURE_STYLES[feature.kind]}
              >
                <Tooltip direction="top" offset={[0, -4]} opacity={1} className="archipelago-feature-tooltip">
                  <span className="archipelago-feature-tooltip-content">
                    <strong>{feature.name}</strong>
                    <small>{ARCHIPELAGO_FEATURE_LABELS[feature.kind]} · {feature.position[0].toFixed(4)}°B, {feature.position[1].toFixed(4)}°Đ</small>
                  </span>
                </Tooltip>
              </CircleMarker>
            ))}
            <Marker
              position={archipelago.labelPosition}
              icon={archipelagoIcon(archipelago.name, archipelago.features.length)}
              alt={archipelago.name}
              zIndexOffset={1_500}
            />
          </Fragment>
        ))}
      </MapContainer>

      <div data-testid="map-controls" className="pointer-events-none absolute right-3 top-3 z-[1000] flex max-w-[calc(100%-72px)] flex-col items-end gap-2">
        {!showArchipelagos && (
          <div title="Vị trí phòng được ước tính từ khu vực và địa chỉ" className="pointer-events-auto flex items-center gap-1.5 rounded-full border border-line bg-surface/95 px-3 py-1.5 text-xs font-semibold text-ink shadow-md backdrop-blur">
            <MapPin aria-hidden="true" className="h-3.5 w-3.5 text-primary" />
            {pins.length} phòng {distanceData.nearestDistance ? `· gần nhất ước tính ${distanceData.nearestDistance}` : "trên bản đồ"}
          </div>
        )}
        {!showArchipelagos && enableGeolocation && (
          <button
            type="button"
            onClick={locate}
            disabled={locationState === "locating"}
            aria-label={locateLabel}
            aria-pressed={userLocation ? true : undefined}
            className="focus-ring pointer-events-auto inline-flex min-h-11 items-center gap-2 rounded-full border border-line bg-surface/95 px-4 text-sm font-semibold text-ink shadow-md backdrop-blur transition-colors hover:border-primary hover:text-primary-700 disabled:cursor-wait disabled:opacity-70"
          >
            {locationState === "locating" ? <Loader2 aria-hidden="true" className="h-4 w-4 animate-spin" /> : <LocateFixed aria-hidden="true" className="h-4 w-4" />}
            <span>{locationState === "locating" ? "Đang định vị…" : userLocation ? "Định vị lại" : locationState === "error" ? "Thử lại" : "Vị trí của tôi"}</span>
          </button>
        )}
        <button
          type="button"
          onClick={() => setShowArchipelagos((visible) => !visible)}
          aria-label={showArchipelagos ? "Quay lại bản đồ phòng trọ Đà Nẵng" : "Đi tới Hoàng Sa và Trường Sa"}
          aria-pressed={showArchipelagos}
          title={showArchipelagos ? undefined : "58 điểm đảo, đá và bãi luôn hiển thị; bấm để chuyển góc nhìn"}
          className="focus-ring pointer-events-auto inline-flex min-h-11 items-center gap-2 rounded-full border border-line bg-surface/95 px-4 text-sm font-semibold text-ink shadow-md backdrop-blur transition-colors hover:border-primary hover:text-primary-700"
        >
          {showArchipelagos ? <ArrowLeft aria-hidden="true" className="h-4 w-4" /> : <Waves aria-hidden="true" className="h-4 w-4" />}
          <span>{showArchipelagos ? "Về bản đồ phòng trọ" : "Hoàng Sa · Trường Sa"}</span>
        </button>
        {showArchipelagos ? (
          <div role="status" className="max-w-xs rounded-md border border-line bg-surface/95 px-3 py-2 text-right text-xs font-medium text-ink-2 shadow-md backdrop-blur">
            Đang xem {ARCHIPELAGO_FEATURE_COUNT} điểm đảo, đá và bãi theo tọa độ địa lý của Hoàng Sa và Trường Sa.
          </div>
        ) : enableGeolocation && locationMessage && (
          <div
            role={locationState === "error" ? "alert" : "status"}
            className={`max-w-xs rounded-md border bg-surface/95 px-3 py-2 text-right text-xs font-medium shadow-md backdrop-blur ${locationState === "error" ? "border-danger/30 text-danger" : "border-line text-ink-2"}`}
          >
            {locationMessage}
          </div>
        )}
      </div>
    </div>
  );
}
