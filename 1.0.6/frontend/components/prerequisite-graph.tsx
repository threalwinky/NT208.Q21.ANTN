"use client";

type GraphNode = {
  course_id: number;
  code: string;
  name: string;
  credits: number;
  recommended_semester: number;
  category: string;
  status: string;
  plan_slot?: number | null;
};

type GraphEdge = {
  from_course_id: number;
  to_course_id: number;
  prerequisite_type: string;
};

const STATUS_STYLES: Record<string, { fill: string; stroke: string; text: string }> = {
  PASSED: {
    fill: "var(--badge-success-bg)",
    stroke: "var(--badge-success-border)",
    text: "var(--badge-success-text)",
  },
  WAIVED: {
    fill: "var(--badge-success-bg)",
    stroke: "var(--badge-success-border)",
    text: "var(--badge-success-text)",
  },
  IN_PROGRESS: {
    fill: "var(--badge-accent-bg)",
    stroke: "var(--badge-accent-border)",
    text: "var(--badge-accent-text)",
  },
  FAILED: {
    fill: "var(--badge-danger-bg)",
    stroke: "var(--badge-danger-border)",
    text: "var(--badge-danger-text)",
  },
  PLANNED_NEXT: {
    fill: "var(--badge-warn-bg)",
    stroke: "var(--badge-warn-border)",
    text: "var(--badge-warn-text)",
  },
  PENDING: {
    fill: "var(--badge-default-bg)",
    stroke: "var(--badge-default-border)",
    text: "var(--badge-default-text)",
  },
};

function chunkLabel(name: string) {
  const words = name.split(" ");
  if (words.length <= 3) {
    return [name];
  }
  const midpoint = Math.ceil(words.length / 2);
  return [words.slice(0, midpoint).join(" "), words.slice(midpoint).join(" ")];
}

export function PrerequisiteGraph({
  nodes,
  edges,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
}) {
  if (nodes.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-[color:var(--line)] bg-[color:var(--surface-soft)] p-5 text-sm text-[color:var(--text-muted)]">
        Chưa có dữ liệu graph tiên quyết.
      </div>
    );
  }

  const grouped = new Map<number, GraphNode[]>();
  nodes
    .slice()
    .sort((left, right) => left.recommended_semester - right.recommended_semester || left.code.localeCompare(right.code))
    .forEach((node) => {
      const semester = node.recommended_semester || 1;
      grouped.set(semester, [...(grouped.get(semester) ?? []), node]);
    });

  const semesterKeys = [...grouped.keys()].sort((left, right) => left - right);
  const maxRows = Math.max(...semesterKeys.map((key) => grouped.get(key)?.length ?? 0));
  const width = Math.max(1040, semesterKeys.length * 220 + 120);
  const height = Math.max(420, maxRows * 128 + 80);
  const positions = new Map<number, { x: number; y: number }>();
  const graphStroke = "var(--accent)";
  const graphDivider = "var(--line)";
  const graphHeading = "var(--text-soft)";
  const graphPrimaryText = "var(--text-primary)";
  const graphMutedText = "var(--text-muted)";

  semesterKeys.forEach((semester, columnIndex) => {
    const column = grouped.get(semester) ?? [];
    column.forEach((node, rowIndex) => {
      positions.set(node.course_id, {
        x: 50 + columnIndex * 220,
        y: 44 + rowIndex * 120,
      });
    });
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 text-xs">
        {[
          ["Đã đạt", "PASSED"],
          ["Đang học", "IN_PROGRESS"],
          ["Gợi ý kỳ tới", "PLANNED_NEXT"],
          ["Cần học lại", "FAILED"],
          ["Chưa học", "PENDING"],
        ].map(([label, key]) => {
          const tone = STATUS_STYLES[key];
          return (
            <span
              key={key}
              className="inline-flex items-center gap-2 rounded-full border px-3 py-1"
              style={{ background: tone.fill, borderColor: tone.stroke, color: tone.text }}
            >
              <span className="h-2 w-2 rounded-full" style={{ background: tone.stroke }} />
              {label}
            </span>
          );
        })}
      </div>

      <div className="overflow-x-auto rounded-lg border border-[color:var(--line)] bg-[color:var(--surface)] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
        <svg viewBox={`0 0 ${width} ${height}`} className="min-w-[1040px]" role="img" aria-label="Graph tiên quyết học phần">
          <defs>
            <marker id="studify-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
              <path d="M0,0 L8,4 L0,8 z" style={{ fill: graphStroke, opacity: 0.36 }} />
            </marker>
          </defs>

          {semesterKeys.map((semester, index) => (
            <g key={semester}>
              {index > 0 ? (
                <line
                  x1={34 + index * 220}
                  y1={36}
                  x2={34 + index * 220}
                  y2={height - 20}
                  style={{ stroke: graphDivider, strokeWidth: 1.25, strokeDasharray: "6 10" }}
                />
              ) : null}
              <text
                x={84 + index * 220}
                y={24}
                fontSize="12"
                fontWeight="700"
                letterSpacing="0.06em"
                style={{ fill: graphHeading }}
              >
                {`Học kỳ ${semester}`}
              </text>
            </g>
          ))}

          {edges.map((edge) => {
            const from = positions.get(edge.from_course_id);
            const to = positions.get(edge.to_course_id);
            if (!from || !to) {
              return null;
            }
            const startX = from.x + 168;
            const startY = from.y + 42;
            const endX = to.x;
            const endY = to.y + 42;
            const curveOffset = Math.max(40, (endX - startX) / 2);
            return (
              <path
                key={`${edge.from_course_id}-${edge.to_course_id}`}
                d={`M ${startX} ${startY} C ${startX + curveOffset} ${startY}, ${endX - curveOffset} ${endY}, ${endX - 10} ${endY}`}
                strokeWidth="2"
                fill="none"
                markerEnd="url(#studify-arrow)"
                style={{ stroke: graphStroke, opacity: 0.28 }}
              />
            );
          })}

          {nodes.map((node) => {
            const position = positions.get(node.course_id);
            if (!position) {
              return null;
            }
            const tone = STATUS_STYLES[node.status] ?? STATUS_STYLES.PENDING;
            const labelLines = chunkLabel(node.name);
            return (
              <g key={node.course_id} transform={`translate(${position.x}, ${position.y})`}>
                <rect
                  x="0"
                  y="0"
                  rx="18"
                  ry="18"
                  width="168"
                  height="84"
                  strokeWidth="1.5"
                  style={{ fill: tone.fill, stroke: tone.stroke }}
                />
                <text x="14" y="22" fontSize="13" fontWeight="700" style={{ fill: tone.text }}>
                  {node.code}
                </text>
                <text x="14" y="40" fontSize="11.5" fontWeight="600" style={{ fill: graphPrimaryText }}>
                  {labelLines[0]}
                </text>
                {labelLines[1] ? (
                  <text x="14" y="54" fontSize="11.5" fontWeight="600" style={{ fill: graphPrimaryText }}>
                    {labelLines[1]}
                  </text>
                ) : null}
                <text x="14" y="72" fontSize="10.5" style={{ fill: graphMutedText }}>
                  {`${node.credits} TC • ${node.plan_slot ? `Gợi ý kỳ ${node.plan_slot}` : node.category}`}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
