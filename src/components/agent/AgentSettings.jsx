/**
 * AgentSettings.jsx — DS-STAR per-run LLM configuration panel.
 *
 * Renders a compact collapsible settings drawer that lets the user
 * override max_rounds, reasoning model, coder model, and temperature
 * before starting an agent run.
 */

import React, { useState } from 'react'
import { Settings2, ChevronDown, ChevronUp, RotateCcw } from 'lucide-react'

// ── Available model options ──────────────────────────────────────────────────
const REASONING_MODELS = [
  { value: 'meta/llama-3.1-70b-instruct',  label: 'Llama 3.1 70B (default)' },
  { value: 'meta/llama-3.3-70b-instruct',  label: 'Llama 3.3 70B' },
  { value: 'mistralai/mistral-7b-instruct-v0.3', label: 'Mistral 7B' },
  { value: 'nvidia/llama-3.1-nemotron-70b-instruct', label: 'Nemotron 70B' },
]

const CODER_MODELS = [
  { value: 'meta/codellama-70b-instruct',           label: 'CodeLlama 70B (default)' },
  { value: 'qwen/qwen2.5-coder-32b-instruct',       label: 'Qwen 2.5 Coder 32B' },
  { value: 'meta/llama-3.1-70b-instruct',           label: 'Llama 3.1 70B (general)' },
]

export const DEFAULT_SETTINGS = {
  maxRounds:   10,
  model:       'meta/llama-3.1-70b-instruct',
  coderModel:  'meta/llama-3.1-70b-instruct',
  temperature: 0.1,
}

// ── Small labelled slider ────────────────────────────────────────────────────
function Slider({ id, label, min, max, step, value, onChange, format }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <label htmlFor={id} className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
          {label}
        </label>
        <span className="text-[12px] font-mono font-bold text-brand-600 bg-brand-50 px-2 py-0.5 rounded-md">
          {format ? format(value) : value}
        </span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1.5 bg-slate-200 rounded-full appearance-none cursor-pointer
                   accent-brand-500 hover:accent-brand-600"
      />
      <div className="flex justify-between text-[10px] text-slate-400 font-medium">
        <span>{format ? format(min) : min}</span>
        <span>{format ? format(max) : max}</span>
      </div>
    </div>
  )
}

// ── Select dropdown ──────────────────────────────────────────────────────────
function Select({ id, label, value, onChange, options }) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full text-[12px] font-medium text-slate-700 bg-white border border-slate-200
                   rounded-lg px-3 py-2 cursor-pointer focus:outline-none focus:ring-2
                   focus:ring-brand-300 focus:border-brand-400 transition-all"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  )
}

// ── Main component ───────────────────────────────────────────────────────────
export function AgentSettings({ settings, onChange, disabled = false }) {
  const [open, setOpen] = useState(false)

  const updateField = (key, val) => onChange({ ...settings, [key]: val })

  const isModified = (
    settings.maxRounds   !== DEFAULT_SETTINGS.maxRounds   ||
    settings.model       !== DEFAULT_SETTINGS.model       ||
    settings.coderModel  !== DEFAULT_SETTINGS.coderModel  ||
    settings.temperature !== DEFAULT_SETTINGS.temperature
  )

  const handleReset = (e) => {
    e.stopPropagation()
    onChange({ ...DEFAULT_SETTINGS })
  }

  return (
    <div className={`rounded-xl border transition-all duration-200 ${
      open
        ? 'border-brand-200 bg-brand-50/40'
        : 'border-slate-200 bg-white hover:border-brand-200'
    }`}>
      {/* Header */}
      <button
        id="agent-settings-toggle"
        onClick={() => setOpen((o) => !o)}
        disabled={disabled}
        className="w-full flex items-center gap-2.5 px-4 py-2.5 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <Settings2 size={13} className={open ? 'text-brand-500' : 'text-slate-400'} />
        <span className={`text-[12px] font-semibold flex-1 text-left ${
          open ? 'text-brand-700' : 'text-slate-600'
        }`}>
          Agent Settings
        </span>

        {isModified && (
          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full
                           bg-brand-100 text-brand-600 uppercase tracking-wider">
            Modified
          </span>
        )}

        {isModified && !disabled && (
          <button
            onClick={handleReset}
            title="Reset to defaults"
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100
                       transition-colors"
          >
            <RotateCcw size={11} />
          </button>
        )}

        {open
          ? <ChevronUp size={13} className="text-slate-400 shrink-0" />
          : <ChevronDown size={13} className="text-slate-400 shrink-0" />}
      </button>

      {/* Body */}
      {open && (
        <div className="px-4 pb-4 pt-1 border-t border-brand-100 space-y-5 animate-fade-in">
          {/* Max Rounds */}
          <Slider
            id="setting-max-rounds"
            label="Max Rounds"
            min={1}
            max={10}
            step={1}
            value={settings.maxRounds}
            onChange={(v) => updateField('maxRounds', v)}
            format={(v) => `${v} round${v !== 1 ? 's' : ''}`}
          />

          {/* Temperature */}
          <Slider
            id="setting-temperature"
            label="Temperature"
            min={0.0}
            max={1.0}
            step={0.05}
            value={settings.temperature}
            onChange={(v) => updateField('temperature', v)}
            format={(v) => v.toFixed(2)}
          />

          {/* Reasoning Model */}
          <Select
            id="setting-reasoning-model"
            label="Reasoning Model (Planner / Verifier / Router)"
            value={settings.model}
            onChange={(v) => updateField('model', v)}
            options={REASONING_MODELS}
          />

          {/* Coder Model */}
          <Select
            id="setting-coder-model"
            label="Coder Model"
            value={settings.coderModel}
            onChange={(v) => updateField('coderModel', v)}
            options={CODER_MODELS}
          />

          <p className="text-[10px] text-slate-400 leading-relaxed pt-1">
            Settings apply to the next run only. Lower temperature = more deterministic output.
            Higher max rounds gives the agent more time to self-correct.
          </p>
        </div>
      )}
    </div>
  )
}
