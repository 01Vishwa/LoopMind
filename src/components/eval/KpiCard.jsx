/**
 * KpiCard.jsx — stat tile with icon, value, sub-label, and optional trend.
 *
 * Props:
 *   icon     — Lucide React icon component
 *   label    — metric label
 *   value    — formatted string value
 *   sub      — optional sub-label beneath value
 *   color    — Tailwind text-* class for the icon (default: text-violet-500)
 *   bg       — Tailwind bg-* class for the icon background (default: bg-violet-50)
 *   border   — Tailwind border-* for icon ring (default: border-violet-100)
 */

import React from 'react'

export function KpiCard({ icon: Icon, label, value, sub, color = 'text-violet-500', bg = 'bg-violet-50', border = 'border-violet-100' }) {
  return (
    <div className="bg-white p-5 rounded-2xl border border-slate-100 shadow-sm flex items-start gap-4 hover:shadow-md transition-shadow">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center border ${bg} ${border} shrink-0`}>
        <Icon size={18} className={color} />
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-800 tracking-tight">{value}</p>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mt-1">{label}</p>
        {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
      </div>
    </div>
  )
}
