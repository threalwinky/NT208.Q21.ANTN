"use client";

import {
  AlertTriangle,
  BookMarked,
  CalendarClock,
  CheckCircle2,
  ChevronRight,
  GraduationCap,
  Info,
  ListChecks,
  Phone,
  Sparkles,
  Wallet,
} from "lucide-react";
import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

function normalizeMarkdown(raw: string): string {
  // Ensure heading markers always start on their own line
  return raw.replace(/([^\n])(#{1,6} )/g, "$1\n\n$2");
}

// Lấy text thuần từ children của heading (có thể lồng <strong>, mảng...)
function nodeText(children: ReactNode): string {
  if (children == null || typeof children === "boolean") return "";
  if (typeof children === "string" || typeof children === "number") return String(children);
  if (Array.isArray(children)) return children.map(nodeText).join("");
  if (typeof children === "object" && "props" in children) {
    return nodeText((children as { props?: { children?: ReactNode } }).props?.children);
  }
  return "";
}

// Chọn icon theo nội dung tiêu đề mục -> giúp câu trả lời dễ quét, bắt mắt hơn.
function headingIcon(text: string): ReactNode {
  const t = text.toLowerCase();
  const cls = "h-[1.05em] w-[1.05em] shrink-0 text-[color:var(--accent)]";
  if (/(nguồn|tham khảo|trích|tài liệu)/.test(t)) return <BookMarked className={cls} />;
  if (/(nên làm|tiếp theo|bước|hành động|gợi ý|cần làm|checklist|to-?do)/.test(t)) return <ListChecks className={cls} />;
  if (/(lưu ý|cảnh báo|chú ý|cẩn thận|tránh|quan trọng)/.test(t)) return <AlertTriangle className={cls} />;
  if (/(thời gian|thời hạn|hạn|mốc|lịch|deadline|khi nào|ngày)/.test(t)) return <CalendarClock className={cls} />;
  if (/(liên hệ|liên lạc|hỗ trợ|phòng ban|email)/.test(t)) return <Phone className={cls} />;
  if (/(điều kiện|yêu cầu|tiêu chí|đối tượng)/.test(t)) return <CheckCircle2 className={cls} />;
  if (/(học phí|chi phí|tiền|thanh toán|đóng)/.test(t)) return <Wallet className={cls} />;
  if (/(học bổng|tốt nghiệp|chương trình|tín chỉ|môn|ngành|đào tạo)/.test(t)) return <GraduationCap className={cls} />;
  if (/(tóm tắt|tổng quan|tổng kết|kết luận)/.test(t)) return <Sparkles className={cls} />;
  if (/(chi tiết|thông tin|giới thiệu|nội dung)/.test(t)) return <Info className={cls} />;
  return <ChevronRight className={cls} />;
}

function IconHeading({ level, children }: { level: 1 | 2 | 3 | 4; children: ReactNode }) {
  const Tag = `h${level}` as "h1" | "h2" | "h3" | "h4";
  return (
    <Tag className="flex items-center gap-2">
      {headingIcon(nodeText(children))}
      <span>{children}</span>
    </Tag>
  );
}

export function MarkdownContent({
  content,
  className = "",
}: {
  content: string;
  className?: string;
}) {
  return (
    <div className={`prose-studify ${className}`.trim()}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        skipHtml={false}
        components={{
          a: ({ ...props }) => <a {...props} target="_blank" rel="noreferrer" />,
          h1: ({ children }) => <IconHeading level={1}>{children}</IconHeading>,
          h2: ({ children }) => <IconHeading level={2}>{children}</IconHeading>,
          h3: ({ children }) => <IconHeading level={3}>{children}</IconHeading>,
          h4: ({ children }) => <IconHeading level={4}>{children}</IconHeading>,
          table: ({ children, ...props }) => (
            <div className="markdown-table-wrap">
              <table className="markdown-table" {...props}>
                {children}
              </table>
            </div>
          ),
          thead: ({ children, ...props }) => <thead className="markdown-table-head" {...props}>{children}</thead>,
          tbody: ({ children, ...props }) => <tbody className="markdown-table-body" {...props}>{children}</tbody>,
          tr: ({ children, ...props }) => <tr className="markdown-table-row" {...props}>{children}</tr>,
          th: ({ children, ...props }) => <th className="markdown-table-cell markdown-table-heading" {...props}>{children}</th>,
          td: ({ children, ...props }) => <td className="markdown-table-cell" {...props}>{children}</td>,
          code: ({ className: codeClassName, children, ...props }) => {
            const isBlock = Boolean(codeClassName);
            if (!isBlock) {
              return (
                <code className="rounded bg-[color:var(--surface-soft)] px-1.5 py-0.5 text-[0.95em]" {...props}>
                  {children}
                </code>
              );
            }
            return (
              <code className={codeClassName} {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {normalizeMarkdown(content)}
      </ReactMarkdown>
    </div>
  );
}
