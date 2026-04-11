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

/**
 * Renders a timing tag from milliseconds.
 * Gap fix: timing data is emitted at the round level, not step level.
 * This component reads from step.round_ms if available, otherwise hides.
 */
function TimingTag({ ms, prefix }) {
  if (!ms || ms <= 0) return null
  return (
    <span className="text-[9px] font-bold text-slate-400 bg-slate-50 px-1 py-0.5 rounded border border-slate-200">
      {prefix}: {(ms / 1000).toFixed(1)}s
    </span>
  )
}

/**
 * Renders an animated ordered list of DS-STAR plan steps.
 *
 * Gap fix: Step timing is now sourced from round-level timing metadata
 * (step.round_coder_ms, step.round_executor_ms) rather than the non-existent
 * per-step exec_ms / verifier_ms fields that were never populated.
 *
 * @param {object} props
 * @param {Array}  props.steps        - Array of plan step objects.
 * @param {number} props.currentRound - Active round number.
 * @param {object} props.roundTimings - Map of round_num → {coder_ms, executor_ms, verifier_ms}
 */
export function PlanStepList({ steps = [], currentRound = 0, roundTimings = {} }) {
  if (steps.length === 0) {
    return (
      <p className="text-[12px] text-slate-400 text-center py-4 font-medium">
        Plan steps will appear here once the agent starts.
      </p>
    )
  }

  // Determine the "active" step: the last non-done step in the current round
  const activeIndex = steps.findIndex(s => s.status === 'active')

  // Round timing for displaying next to the currently executing step
  const currentRoundTiming = roundTimings[currentRound] || {}

  return (
    <ol className="space-y-2">
      {steps.map((step, i) => {
        const rawStatus = step.status || 'pending'
        const config = STATUS_CONFIG[rawStatus] || STATUS_CONFIG.pending
        const Icon = config.icon
        const isCurrentlyActive = rawStatus === 'active' || (i === activeIndex)

        // Attach round timing to the active step only
        const coderMs = isCurrentlyActive ? currentRoundTiming.coder_ms : null
        const executorMs = isCurrentlyActive ? currentRoundTiming.executor_ms : null
        const verifierMs = isCurrentlyActive ? currentRoundTiming.verifier_ms : null

        return (
          <li
            key={`step-${step.index ?? i}`}
            id={`plan-step-${step.index ?? i}`}
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

            {/* Status badge + Round timings (sourced correctly from round-level data) */}
            <div className="shrink-0 flex flex-col items-end gap-1 px-1">
              <span
                className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${config.cls}`}
              >
                {config.label}
              </span>
              {isCurrentlyActive && (
                <div className="flex gap-1 flex-wrap justify-end">
                  <TimingTag ms={coderMs}    prefix="Code"   />
                  <TimingTag ms={executorMs} prefix="Exec"   />
                  <TimingTag ms={verifierMs} prefix="Verify" />
                </div>
              )}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
