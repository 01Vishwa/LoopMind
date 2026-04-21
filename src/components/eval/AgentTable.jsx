/**
 * AgentTable.jsx
 * Displays a table of per-agent performance metrics.
 */

import React from 'react'

export function AgentTable({ agents = [] }) {
  if (agents.length === 0) {
    return <div className="text-sm text-slate-500 p-4">No agent metrics available.</div>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b border-slate-100 text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <th className="py-3 px-4 font-medium">Agent</th>
            <th className="py-3 px-4 font-medium text-right">Avg Latency</th>
            <th className="py-3 px-4 font-medium text-right">Failure Rate</th>
            <th className="py-3 px-4 font-medium text-right">Total Calls</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {agents.map((agent) => (
            <tr key={agent.agent_name} className="hover:bg-slate-50 transition-colors">
              <td className="py-3 px-4 text-sm font-medium text-slate-800">
                {agent.agent_name}
              </td>
              <td className="py-3 px-4 text-sm text-slate-600 text-right font-mono">
                {agent.avg_latency_ms} ms
              </td>
              <td className="py-3 px-4 text-sm text-right">
                <span className={`px-2 py-0.5 rounded-full font-medium ${
                  agent.failure_rate > 0.05 ? 'bg-rose-50 text-rose-700' : 'bg-emerald-50 text-emerald-700'
                }`}>
                  {(agent.failure_rate * 100).toFixed(1)}%
                </span>
              </td>
              <td className="py-3 px-4 text-sm text-slate-600 text-right">
                {agent.total_calls}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
