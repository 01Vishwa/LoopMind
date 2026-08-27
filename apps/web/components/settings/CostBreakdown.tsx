function fmtTokens(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return String(n);
}

interface BreakdownRow {
  name: string;
  tokens: number;
  cost: number;
  pct?: number;
}

interface BreakdownSection {
  title: string;
  rows: BreakdownRow[];
  showPct?: boolean;
}

interface CostBreakdownProps {
  sections: BreakdownSection[];
}

export function CostBreakdown({ sections }: CostBreakdownProps) {
  return (
    <div className="space-y-6">
      {sections.map((section) => (
        <div key={section.title}>
          <h4 className="text-[11px] font-semibold uppercase tracking-widest text-vera-muted mb-2">
            {section.title}
          </h4>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-vera-border">
                <th className="table-header pb-2 text-left w-full">Name</th>
                <th className="table-header pb-2 text-right whitespace-nowrap pr-4">Tokens</th>
                <th className="table-header pb-2 text-right whitespace-nowrap pr-4">Cost</th>
                {section.showPct && (
                  <th className="table-header pb-2 text-right whitespace-nowrap">%</th>
                )}
              </tr>
            </thead>
            <tbody>
              {section.rows.map((row) => (
                <tr key={row.name} className="border-b border-vera-border-subtle last:border-0">
                  <td className="py-2 text-vera-ink">{row.name}</td>
                  <td className="py-2 text-right text-vera-muted tabular-nums pr-4">
                    {fmtTokens(row.tokens)}
                  </td>
                  <td className="py-2 text-right text-vera-ink tabular-nums font-medium pr-4">
                    ${row.cost.toFixed(2)}
                  </td>
                  {section.showPct && (
                    <td className="py-2 text-right text-vera-muted tabular-nums">
                      {row.pct ?? 0}%
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
