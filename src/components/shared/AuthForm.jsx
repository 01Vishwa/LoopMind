import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  Mail, Lock, LogIn, UserPlus, Eye, EyeOff,
  Loader2, Sparkles, Shield, AlertCircle,
} from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'

export function AuthForm({ onSuccess }) {
  const { signIn, signUp, authError, isAuthenticated } = useAuth()

  const [tab, setTab] = useState('signin') // 'signin' | 'signup'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [localError, setLocalError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  const emailRef = useRef(null)

  useEffect(() => {
    setTimeout(() => emailRef.current?.focus(), 120)
  }, [tab])

  // Call onSuccess when user becomes authenticated
  useEffect(() => {
    if (isAuthenticated && onSuccess) {
      onSuccess()
    }
  }, [isAuthenticated, onSuccess])

  const switchTab = useCallback((t) => {
    setTab(t)
    setLocalError('')
    setSuccessMsg('')
    setEmail('')
    setPassword('')
    setConfirmPassword('')
  }, [])

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault()
    setLocalError('')
    setSuccessMsg('')

    if (!email.trim() || !password.trim()) {
      setLocalError('Email and password are required.')
      return
    }

    if (tab === 'signup' && password !== confirmPassword) {
      setLocalError('Passwords do not match.')
      return
    }

    if (password.length < 6) {
      setLocalError('Password must be at least 6 characters.')
      return
    }

    setLoading(true)
    try {
      if (tab === 'signin') {
        await signIn(email.trim(), password)
      } else {
        const { user } = await signUp(email.trim(), password)
        // Supabase may require email confirmation before session is active
        if (!user?.confirmed_at && !user?.email_confirmed_at) {
          setSuccessMsg('Account created! Check your email to confirm before signing in.')
          setLoading(false)
          return
        }
      }
      // onSuccess is triggered by the isAuthenticated effect above
    } catch (err) {
      setLocalError(err.message || 'Authentication failed.')
    } finally {
      setLoading(false)
    }
  }, [email, password, confirmPassword, tab, signIn, signUp])

  const errorMsg = localError || authError

  return (
    <div className="w-full">
      {/* Logo + heading */}
      <div className="flex flex-col items-center mb-7">
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-brand-500 to-violet-600
                        flex items-center justify-center shadow-lg shadow-brand-500/25 mb-3">
          <Sparkles size={22} className="text-white" />
        </div>
        <h2 className="text-lg font-bold text-slate-800 tracking-tight">
          {tab === 'signin' ? 'Welcome back' : 'Create your account'}
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          {tab === 'signin'
            ? 'Sign in to access your workspaces and runs'
            : 'Start running DS-STAR agents in seconds'}
        </p>
      </div>

      {/* Tab switcher */}
      <div className="flex items-center bg-slate-100 rounded-xl p-1 mb-6">
        <button
          id="auth-tab-signin"
          onClick={() => switchTab('signin')}
          className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-semibold
                      transition-all duration-200
                      ${tab === 'signin'
                        ? 'bg-white text-slate-800 shadow-sm border border-slate-200/60'
                        : 'text-slate-500 hover:text-slate-700'}`}
        >
          <LogIn size={14} />
          Sign In
        </button>
        <button
          id="auth-tab-signup"
          onClick={() => switchTab('signup')}
          className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-semibold
                      transition-all duration-200
                      ${tab === 'signup'
                        ? 'bg-white text-slate-800 shadow-sm border border-slate-200/60'
                        : 'text-slate-500 hover:text-slate-700'}`}
        >
          <UserPlus size={14} />
          Sign Up
        </button>
      </div>

      {/* Form */}
      <form id="auth-form" onSubmit={handleSubmit} noValidate className="space-y-4">
        {/* Email */}
        <div>
          <label htmlFor="auth-email" className="block text-xs font-semibold text-slate-600 mb-1.5">
            Email address
          </label>
          <div className="relative">
            <Mail
              size={15}
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
            />
            <input
              id="auth-email"
              ref={emailRef}
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="input-field pl-10"
              disabled={loading}
            />
          </div>
        </div>

        {/* Password */}
        <div>
          <label htmlFor="auth-password" className="block text-xs font-semibold text-slate-600 mb-1.5">
            Password
          </label>
          <div className="relative">
            <Lock
              size={15}
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
            />
            <input
              id="auth-password"
              type={showPassword ? 'text' : 'password'}
              autoComplete={tab === 'signup' ? 'new-password' : 'current-password'}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="input-field pl-10 pr-11"
              disabled={loading}
            />
            <button
              type="button"
              tabIndex={-1}
              onClick={() => setShowPassword((v) => !v)}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>
        </div>

        {/* Confirm Password (sign-up only) */}
        {tab === 'signup' && (
          <div>
            <label htmlFor="auth-confirm-password" className="block text-xs font-semibold text-slate-600 mb-1.5">
              Confirm Password
            </label>
            <div className="relative">
              <Shield
                size={15}
                className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
              />
              <input
                id="auth-confirm-password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                className="input-field pl-10"
                disabled={loading}
              />
            </div>
          </div>
        )}

        {/* Error message */}
        {errorMsg && (
          <div
            role="alert"
            className="flex items-start gap-2.5 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs"
          >
            <AlertCircle size={14} className="shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Success message */}
        {successMsg && (
          <div
            role="status"
            className="flex items-start gap-2.5 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs"
          >
            <Sparkles size={14} className="shrink-0 mt-0.5" />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Submit */}
        <button
          id="auth-submit-btn"
          type="submit"
          disabled={loading}
          className="btn-primary w-full justify-center mt-2"
        >
          {loading ? (
            <Loader2 size={16} className="animate-spin" />
          ) : tab === 'signin' ? (
            <LogIn size={16} />
          ) : (
            <UserPlus size={16} />
          )}
          {loading
            ? (tab === 'signin' ? 'Signing in…' : 'Creating account…')
            : (tab === 'signin' ? 'Sign In' : 'Create Account')}
        </button>
      </form>

      {/* Footer */}
      <p className="text-center text-xs text-slate-400 mt-5">
        {tab === 'signin' ? "Don't have an account?" : 'Already have an account?'}{' '}
        <button
          type="button"
          onClick={() => switchTab(tab === 'signin' ? 'signup' : 'signin')}
          className="text-brand-600 font-semibold hover:underline"
        >
          {tab === 'signin' ? 'Sign up free' : 'Sign in'}
        </button>
      </p>
    </div>
  )
}
