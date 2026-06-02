"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

function normalizeMarkdown(raw: string): string {
  // Ensure heading markers always start on their own line
  return raw.replace(/([^\n])(#{1,6} )/g, "$1\n\n$2");
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
