import React from 'react'
import {
  CheckCircle2, Circle, Loader2, Wrench, AlertCircle,
} from 'lucide-react'

const STATUS_CONFIG = {
  pending:  { icon: Circle,        cls: 'step-pending', label: 'Pending'  },
  active:   { icon: Loader2,       cls: 'step-active',  label: 'Running'  },
  done:     { icon: CheckCircle2,  cls: 'step-done',    label: 'Done'     },
  fixed:    { icon: Wrench,        cls: 'step-fixed',   label: 'Fixed'    },
  error:    { icon: AlertCircle,   cls: 'step-error',   label: 'Error'    },
}

function TimingTag({ ms, prefix }) {
  if (!ms) return null
  return (
    <span className="text-[9px] font-bold text-slate-400 bg-slate-50 px-1 py-0.2 rounded border">
      {prefix}: {(ms / 1000).toFixed(1)}s
    </span>
  )
}

/**
 * Renders an animated ordered list of DS-STAR plan steps.
 *
 * @param {object} props
 * @param {Array}  props.steps         - Array of plan step objects.
 * @param {number} props.currentRound  - Active round number (used to derive active step).
 */
export function PlanStepList({ steps = [], currentRound = 0 }) {
  if (steps.length === 0) {
    return (
      <p className="text-[12px] text-slate-400 text-center py-4 font-medium">
        Plan steps will appear here once the agent starts.
      </p>
    )
  }

  return (
    <ol className="space-y-2">
      {steps.map((step, i) => {
        const rawStatus = step.status || 'pending'
        const config = STATUS_CONFIG[rawStatus] || STATUS_CONFIG.pending
        const Icon = config.icon

        return (
          <li
            key={`step-${step.index ?? i}`}
            className="step-enter flex items-start gap-3 p-3 rounded-xl bg-white border border-slate-100
                       shadow-sm hover:shadow-md transition-shadow duration-200"
            style={{ animationDelay: `${i * 40}ms` }}
          >
            {/* Status icon */}
            <div
              className={`mt-0.5 w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${config.cls}`}
            >
              <Icon
                size={13}
                className={rawStatus === 'active' ? 'animate-spin' : ''}
              />
            </div>

            {/* Step text */}
            <div className="flex-1 min-w-0">
              <p className="text-[12px] font-semibold text-slate-700 leading-snug">
                Step {step.index + 1}
              </p>
              <p className="text-[12px] text-slate-500 leading-relaxed mt-0.5">
                {step.description}
              </p>
            </div>

            {/* Status badge + Timings */}
            <div className="shrink-0 flex flex-col items-end gap-1 px-1">
              <span
                className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${config.cls}`}
              >
                {config.label}
              </span>
              <div className="flex gap-1 flex-wrap justify-end">
                <TimingTag ms={step.exec_ms} prefix="Exec" />
                <TimingTag ms={step.verifier_ms} prefix="Verify" />
              </div>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
