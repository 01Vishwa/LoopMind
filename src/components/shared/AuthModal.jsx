/**
 * AuthModal.jsx — Login / Sign-Up modal.
 *
 * A full-featured glassmorphism modal with animated tab switching between
 * "Sign In" and "Create Account" views. Surfaces Supabase errors inline.
 * Closes automatically on successful authentication.
 *
 * Usage:
 *   <AuthModal isOpen={showAuth} onClose={() => setShowAuth(false)} />
 */

import React, { useEffect } from 'react'
import { X } from 'lucide-react'
import { AuthForm } from './AuthForm'

/**
 * @param {{ isOpen: boolean, onClose: () => void }} props
 */
export function AuthModal({ isOpen, onClose }) {
  // Close on Escape key
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    if (isOpen) window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4"
        onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
        aria-modal="true"
        role="dialog"
        aria-label="Authentication"
      >
        {/* Panel */}
        <div
          className="relative w-full max-w-[420px] bg-white/95 backdrop-blur-xl
                     border border-slate-200/80 rounded-2xl shadow-2xl shadow-slate-900/20
                     animate-slide-up overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Decorative gradient top bar */}
          <div className="h-1 w-full bg-gradient-to-r from-brand-500 via-violet-500 to-brand-400" />

          {/* Close button */}
          <button
            id="auth-modal-close-btn"
            onClick={onClose}
            aria-label="Close"
            className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-slate-600
                       hover:bg-slate-100 transition-all duration-150 z-10"
          >
            <X size={16} />
          </button>

          <div className="px-8 pt-7 pb-8">
            <AuthForm onSuccess={onClose} />
          </div>
        </div>
      </div>
    </>
  )
}
