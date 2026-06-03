import { AppShell } from "@/components/app-shell";
import { AppCard, Badge } from "@/components/ui";

export default function PrivacySettingsPage() {
  return (
    <AppShell pageTitle="Riêng tư và an toàn" pageDescription="Các nguyên tắc bảo vệ dữ liệu cá nhân trong module wellbeing của Studify.">
      <div className="grid gap-4 xl:grid-cols-2">
        <AppCard title="Ghi chú riêng" subtitle="Nội dung nhật ký không được dùng để train model và không tự gửi sang LLM.">
          <div className="space-y-3 text-sm leading-6 text-[color:var(--text-muted)]">
            <p>Ghi chú wellbeing mặc định là private theo tài khoản sinh viên.</p>
            <p>Admin chỉ nên xử lý metadata vận hành, không cần đọc nội dung riêng tư của sinh viên.</p>
            <p>Người dùng có thể xóa mềm ghi chú và export lại dữ liệu của mình.</p>
          </div>
        </AppCard>
        <AppCard title="Guardrail khủng hoảng" subtitle="Khi có tín hiệu tự hại/nguy hiểm, hệ thống ưu tiên hỗ trợ người thật.">
          <div className="flex flex-wrap gap-2">
            <Badge tone="danger">Không chẩn đoán</Badge>
            <Badge tone="warn">Không thay thế trị liệu</Badge>
            <Badge tone="success">Ưu tiên nguồn hỗ trợ UIT</Badge>
          </div>
          <p className="mt-4 text-sm leading-6 text-[color:var(--text-muted)]">
            Studify chỉ đồng hành mức ban đầu. Nếu sinh viên đang gặp nguy cơ trực tiếp, phản hồi phải nghiêm túc, khuyến nghị liên hệ người thân, bạn bè, cố vấn hoặc dịch vụ khẩn cấp phù hợp.
          </p>
        </AppCard>
      </div>
    </AppShell>
  );
}
