import React from 'react'
import { HomePage } from './pages/HomePage'
import { ToastContainer } from './components/shared/Toast'
import './index.css'

export default function App() {
  return (
    <>
      <HomePage />
      <ToastContainer />
    </>
  )
}
