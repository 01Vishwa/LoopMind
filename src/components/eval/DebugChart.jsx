/**
 * DebugChart.jsx
 * Displays debug loop analysis with charts.
 */

import React from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts'

const COLORS = ['#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#3b82f6', '#6366f1']

export function DebugChart({ debugStats }) {
  if (!debugStats) return null

  const data = debugStats.error_type_distribution || []

  return (
    <div className="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm">
      <h3 className="text-sm font-bold text-slate-800 mb-6 uppercase tracking-wider">Debugger Error Types</h3>
      
      {data.length === 0 ? (
        <div className="h-48 flex items-center justify-center text-slate-400 text-sm">
          No error data available
        </div>
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={2}
                dataKey="count"
                nameKey="error_type"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
              />
              <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="mt-8 pt-6 border-t border-slate-100 grid grid-cols-2 gap-4">
        <div>
           <p className="text-xl font-bold text-slate-800">{debugStats.avg_debug_depth}</p>
           <p className="text-xs font-semibold text-slate-500 uppercase">Avg Debug Depth</p>
        </div>
        <div>
           <p className="text-xl font-bold text-slate-800">{(debugStats.retry_success_ratio * 100).toFixed(1)}%</p>
           <p className="text-xs font-semibold text-slate-500 uppercase">Retry Recovery Rate</p>
        </div>
      </div>
    </div>
  )
}
