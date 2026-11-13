import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children: ReactNode }) => <div data-testid="map">{children}</div>,
  TileLayer: ({ url, attribution, maxZoom }: { url: string; attribution: string; maxZoom?: number }) => (
    <div data-testid="tile-layer" data-url={url} data-attribution={attribution} data-max-zoom={maxZoom} />
  ),
  Circle: ({ center, radius }: { center: [number, number]; radius: number }) => (
    <div data-testid="circle" data-position={center.join(",")} data-radius={radius} />
  ),
  CircleMarker: ({ center, radius, children }: { center: [number, number]; radius: number; children?: ReactNode }) => (
    <div data-testid="island-feature" data-position={center.join(",")} data-radius={radius}>{children}</div>
  ),
  Rectangle: ({ bounds }: { bounds: [[number, number], [number, number]] }) => (
    <div data-testid="archipelago-region" data-bounds={JSON.stringify(bounds)} />
  ),
  Tooltip: ({ children }: { children: ReactNode }) => <span>{children}</span>,
  Marker: ({ position, icon, alt }: { position: [number, number]; icon: { options?: { html?: string } }; alt?: string }) => (
    <div
      data-testid={alt === "Vị trí của bạn" ? "user-location-marker" : alt?.startsWith("Quần đảo") ? "archipelago-marker" : "map-marker"}
      data-position={position.join(",")}
      data-icon-html={icon?.options?.html}
      data-alt={alt}
    />
  ),
  useMap: () => ({ setView: vi.fn(), fitBounds: vi.fn(), invalidateSize: vi.fn() }),
}));

import { MapView } from "./MapView";

describe("MapView", () => {
  afterEach(cleanup);

  beforeEach(() => {
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: undefined,
    });
  });

  it("uses the official OpenStreetMap tile service without a provider API key", () => {
    render(<MapView pins={[]} />);

    const tiles = screen.getByTestId("tile-layer");
    expect(tiles).toHaveAttribute("data-url", "https://tile.openstreetmap.org/{z}/{x}/{y}.png");
    expect(tiles).toHaveAttribute("data-max-zoom", "19");
    expect(tiles.getAttribute("data-attribution")).toContain("OpenStreetMap contributors");
    expect(tiles.getAttribute("data-attribution")).not.toContain("CARTO");
  });

  it("shows every rental pin and locates the user only after an explicit click", async () => {
    const getCurrentPosition = vi.fn((success: PositionCallback) =>
      success({
        coords: {
          latitude: 16.0544,
          longitude: 108.2022,
          accuracy: 24,
          altitude: null,
          altitudeAccuracy: null,
          heading: null,
          speed: null,
          toJSON: () => ({}),
        },
        timestamp: Date.now(),
        toJSON: () => ({}),
      } as GeolocationPosition),
    );
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: { getCurrentPosition },
    });

    render(
      <MapView
        pins={[
          { id: 1, lat: 16.0644, lng: 108.2022, price: 2_300_000 },
          { id: 2, lat: 16.0444, lng: 108.2022, price: 2_500_000 },
        ]}
      />,
    );

    expect(screen.getAllByTestId("map-marker")).toHaveLength(2);
    expect(getCurrentPosition).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Dùng vị trí hiện tại" }));

    await waitFor(() => expect(screen.getByTestId("user-location-marker")).toBeInTheDocument());
    expect(getCurrentPosition).toHaveBeenCalledWith(expect.any(Function), expect.any(Function), {
      enableHighAccuracy: true,
      maximumAge: 60_000,
      timeout: 10_000,
    });
    expect(screen.getByTestId("user-location-marker")).toHaveAttribute("data-position", "16.0544,108.2022");
    expect(screen.getByTestId("circle")).toHaveAttribute("data-radius", "24");
    expect(screen.getByRole("status")).toHaveTextContent("Đã xác định vị trí của bạn");
    expect(within(screen.getByTestId("map-controls")).getByRole("status")).toBeInTheDocument();
    expect(screen.getAllByTestId("map-marker")[0].getAttribute("data-icon-html")).toContain("1,1 km");
    expect(screen.getAllByTestId("map-marker")[0]).toHaveAttribute("data-alt", expect.stringContaining("ước tính cách bạn 1,1 km"));
  });

  it("keeps the city map readable by labeling only the five nearest rentals", async () => {
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: {
        getCurrentPosition: (success: PositionCallback) =>
          success({
            coords: { latitude: 16.0544, longitude: 108.2022, accuracy: 20 } as GeolocationCoordinates,
            timestamp: Date.now(),
          } as GeolocationPosition),
      },
    });
    const pins = Array.from({ length: 7 }, (_, index) => ({
      id: index + 1,
      lat: 16.0554 + index * 0.001,
      lng: 108.2022,
      price: 2_000_000 + index * 100_000,
    }));

    render(<MapView pins={pins} />);
    fireEvent.click(screen.getByRole("button", { name: "Dùng vị trí hiện tại" }));
    await screen.findByTestId("user-location-marker");

    const labeledPins = screen
      .getAllByTestId("map-marker")
      .filter((marker) => marker.getAttribute("data-icon-html")?.includes("price-pin-distance"));
    expect(labeledPins).toHaveLength(5);
    expect(screen.getByText(/7 phòng · gần nhất ước tính/)).toBeInTheDocument();
  });

  it("explains how to recover when location permission is denied", async () => {
    const getCurrentPosition = vi.fn((_success: PositionCallback, error: PositionErrorCallback) =>
      error({ code: 1, message: "denied", PERMISSION_DENIED: 1, POSITION_UNAVAILABLE: 2, TIMEOUT: 3 }),
    );
    Object.defineProperty(navigator, "geolocation", {
      configurable: true,
      value: { getCurrentPosition },
    });

    render(<MapView pins={[]} />);
    fireEvent.click(screen.getByRole("button", { name: "Dùng vị trí hiện tại" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("bật quyền Vị trí trong trình duyệt");
    expect(screen.getByRole("button", { name: "Thử định vị lại" })).toBeInTheDocument();
  });

  it("draws the individual Hoang Sa and Truong Sa features instead of rectangular extents", () => {
    render(<MapView pins={[{ id: 1, lat: 16.0544, lng: 108.2022, price: 2_300_000 }]} />);

    const initialMarkers = screen.getAllByTestId("archipelago-marker");
    expect(initialMarkers.map((marker) => marker.getAttribute("data-alt"))).toEqual(["Quần đảo Hoàng Sa", "Quần đảo Trường Sa"]);
    expect(screen.queryByTestId("archipelago-region")).not.toBeInTheDocument();
    expect(screen.getAllByTestId("island-feature")).toHaveLength(58);
    const hoangSaPosition = screen.getByText("Đảo Hoàng Sa").closest('[data-testid="island-feature"]')?.getAttribute("data-position")?.split(",").map(Number);
    const truongSaPosition = screen.getByText("Đảo Trường Sa").closest('[data-testid="island-feature"]')?.getAttribute("data-position")?.split(",").map(Number);
    expect(hoangSaPosition?.[0]).toBeCloseTo(16.533333, 6);
    expect(hoangSaPosition?.[1]).toBeCloseTo(111.601944, 6);
    expect(truongSaPosition?.[0]).toBeCloseTo(8.641667, 6);
    expect(truongSaPosition?.[1]).toBeCloseTo(111.931944, 6);
    fireEvent.click(screen.getByRole("button", { name: "Đi tới Hoàng Sa và Trường Sa" }));

    const archipelagoMarkers = screen.getAllByTestId("archipelago-marker");
    expect(archipelagoMarkers).toHaveLength(2);
    expect(archipelagoMarkers.map((marker) => marker.getAttribute("data-alt"))).toEqual(["Quần đảo Hoàng Sa", "Quần đảo Trường Sa"]);
    expect(screen.getAllByTestId("island-feature")).toHaveLength(58);
    expect(screen.getByText("Đang xem 58 điểm đảo, đá và bãi theo tọa độ địa lý của Hoàng Sa và Trường Sa.")).toHaveAttribute("role", "status");
    expect(screen.getByRole("button", { name: "Quay lại bản đồ phòng trọ Đà Nẵng" })).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(screen.getByRole("button", { name: "Quay lại bản đồ phòng trọ Đà Nẵng" }));
    expect(screen.getAllByTestId("archipelago-marker")).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Đi tới Hoàng Sa và Trường Sa" })).toHaveAttribute("aria-pressed", "false");
  });
});
