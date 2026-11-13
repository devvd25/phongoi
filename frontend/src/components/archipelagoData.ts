export type ArchipelagoFeature = {
  name: string;
  position: [number, number];
  kind: "island" | "reef" | "shoal";
};

export type ArchipelagoGroup = {
  name: string;
  labelPosition: [number, number];
  features: ArchipelagoFeature[];
};

const dms = (degrees: number, minutes: number, seconds: number) => degrees + minutes / 60 + seconds / 3_600;
const point = (
  name: string,
  kind: ArchipelagoFeature["kind"],
  latitude: [number, number, number],
  longitude: [number, number, number],
): ArchipelagoFeature => ({
  name,
  kind,
  position: [dms(...latitude), dms(...longitude)],
});

// Tọa độ Hoàng Sa: Cổng thông tin điện tử thành phố Đà Nẵng.
// https://danang.gov.vn/vi/web/dng/w/ubnd-huyen-hoang-sa-i
const HOANG_SA_FEATURES: ArchipelagoFeature[] = [
  point("Đảo Đá Bắc", "island", [17, 6, 0], [111, 30, 8]),
  point("Đảo Hoàng Sa", "island", [16, 32, 0], [111, 36, 7]),
  point("Đảo Hữu Nhật", "island", [16, 30, 3], [111, 35, 3]),
  point("Đảo Duy Mộng", "island", [16, 27, 6], [111, 35, 3]),
  point("Đảo Quang Hòa", "island", [16, 26, 9], [111, 42, 7]),
  point("Đảo Quang Ảnh", "island", [16, 27, 0], [111, 30, 8]),
  point("Đảo Bạch Quy", "island", [16, 3, 5], [111, 46, 9]),
  point("Đảo Tri Tôn", "island", [15, 47, 2], [111, 11, 8]),
  point("Bãi ngầm Ốc Tai Voi", "shoal", [15, 44, 0], [112, 14, 1]),
  point("Đảo Ốc Hoa", "island", [16, 34, 0], [111, 40, 0]),
  point("Đảo Ba Ba", "island", [16, 33, 8], [111, 41, 5]),
  point("Đảo Lưỡi Liềm", "island", [16, 30, 5], [111, 46, 2]),
  point("Đá Hải Sâm", "reef", [16, 28, 0], [111, 35, 5]),
  point("Đá Lồi", "reef", [16, 15, 0], [111, 41, 0]),
  point("Đá Chim Én", "reef", [16, 20, 8], [112, 2, 6]),
  point("Bãi Xà Cừ", "shoal", [16, 34, 9], [111, 42, 9]),
  point("Bãi Ngự Bình", "shoal", [16, 27, 5], [111, 39, 0]),
  point("Đảo Phú Lâm", "island", [16, 50, 2], [112, 20, 0]),
  point("Đảo Linh Côn", "island", [16, 40, 3], [112, 43, 6]),
  point("Đảo Cây", "island", [16, 59, 0], [112, 15, 9]),
  point("Đảo Trung", "island", [16, 57, 6], [112, 19, 1]),
  point("Đảo Bắc", "island", [16, 58, 0], [112, 18, 3]),
  point("Đảo Nam", "island", [16, 57, 0], [112, 19, 7]),
  point("Đảo Đá", "island", [16, 50, 9], [112, 20, 5]),
  point("Đá Trương Nghĩa", "reef", [16, 58, 6], [112, 15, 4]),
  point("Đá Sơn Kỳ", "reef", [16, 34, 6], [111, 44, 0]),
  point("Đá Trà Tây", "reef", [16, 32, 8], [111, 42, 8]),
  point("Đá Bông Bay", "reef", [16, 2, 0], [112, 30, 0]),
  point("Bãi Bình Sơn", "shoal", [16, 46, 6], [112, 13, 2]),
  point("Bãi Đèn Pha", "shoal", [16, 32, 3], [111, 36, 9]),
  point("Bãi Châu Nhai", "shoal", [16, 19, 6], [112, 25, 4]),
  point("Cồn Cát Tây", "island", [16, 58, 9], [112, 12, 3]),
  point("Cồn Cát Nam", "island", [16, 55, 6], [112, 20, 5]),
  point("Hòn Tháp", "island", [16, 34, 8], [112, 38, 6]),
  point("Bãi cạn Gò Nổi", "shoal", [16, 49, 7], [112, 53, 4]),
  point("Bãi Thủy Tề", "shoal", [16, 32, 0], [112, 39, 9]),
  point("Bãi Quang Nghĩa", "shoal", [16, 19, 4], [112, 41, 1]),
];

// Tọa độ Trường Sa: Cổng thông tin điện tử Công an tỉnh Hà Tĩnh.
// https://catphatinh.gov.vn/bai-viet/danh-sach-cac-dao-do-viet-nam-kiem-soat-o-quan-dao-truong-sa.catp
const TRUONG_SA_FEATURES: ArchipelagoFeature[] = [
  point("Đảo An Bang", "island", [7, 52, 10], [112, 54, 10]),
  point("Đảo Nam Yết", "island", [10, 10, 54], [114, 21, 36]),
  point("Đảo Sinh Tồn", "island", [9, 53, 0], [114, 19, 0]),
  point("Đảo Sinh Tồn Đông", "island", [9, 54, 18], [114, 33, 42]),
  point("Đảo Sơn Ca", "island", [10, 22, 36], [114, 28, 42]),
  point("Đảo Trường Sa", "island", [8, 38, 30], [111, 55, 55]),
  point("Đảo Song Tử Tây", "island", [11, 25, 46], [114, 19, 54]),
  point("Đá Cô Lin", "reef", [9, 46, 13], [114, 15, 25]),
  point("Đá Đông", "reef", [8, 49, 42], [112, 35, 48]),
  point("Đá Lát", "reef", [8, 40, 42], [111, 40, 12]),
  point("Đá Len Đao", "reef", [9, 46, 48], [114, 22, 12]),
  point("Đá Lớn", "reef", [10, 3, 42], [113, 51, 6]),
  point("Đá Nam", "reef", [11, 23, 31], [114, 17, 54]),
  point("Đá Núi Thị", "reef", [10, 24, 42], [114, 34, 12]),
  point("Đá Núi Le", "reef", [8, 42, 36], [114, 11, 6]),
  point("Đảo Phan Vinh", "island", [8, 58, 6], [113, 41, 54]),
  point("Đá Tây", "reef", [8, 51, 0], [112, 11, 0]),
  point("Đá/Bãi Thuyền Chài", "shoal", [8, 10, 0], [113, 18, 0]),
  point("Đá Tiên Nữ", "reef", [8, 51, 18], [114, 39, 18]),
  point("Đá Tốc Tan", "reef", [8, 48, 42], [113, 59, 0]),
  point("Đảo Trường Sa Đông", "island", [8, 56, 6], [112, 20, 54]),
];

export const ARCHIPELAGO_GROUPS: ArchipelagoGroup[] = [
  {
    name: "Quần đảo Hoàng Sa",
    labelPosition: [15.86, 112.65],
    features: HOANG_SA_FEATURES,
  },
  {
    name: "Quần đảo Trường Sa",
    labelPosition: [10.2, 115.25],
    features: TRUONG_SA_FEATURES,
  },
];

export const ARCHIPELAGO_FEATURE_COUNT = ARCHIPELAGO_GROUPS.reduce((total, group) => total + group.features.length, 0);
