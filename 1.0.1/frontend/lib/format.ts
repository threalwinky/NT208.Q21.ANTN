export function formatDate(value?: string | null) {
  if (!value) {
    return "Chưa cập nhật";
  }
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(value));
}

export function formatDateTime(value?: string | null) {
  if (!value) {
    return "Chưa xác định";
  }
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
  }).format(new Date(value));
}

export function formatDeadlineDistance(value?: string | null) {
  if (!value) {
    return "Chưa xác định";
  }

  const now = new Date();
  const target = new Date(value);
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startOfTarget = new Date(target.getFullYear(), target.getMonth(), target.getDate()).getTime();
  const diffDays = Math.round((startOfTarget - startOfToday) / 86400000);

  if (diffDays < 0) {
    return "Đã quá hạn";
  }
  if (diffDays === 0) {
    return "Đến hạn hôm nay";
  }
  if (diffDays === 1) {
    return "Đến hạn ngày mai";
  }
  if (diffDays <= 7) {
    return `Còn ${diffDays} ngày`;
  }

  return formatDateTime(value);
}
