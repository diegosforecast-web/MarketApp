import './App.css'
import AuthPage from './components/AuthPage'
import Dashboard from './components/Dashboard'
import UpdatePasswordPage from './components/UpdatePasswordPage'
import { useAuth } from './contexts/AuthContext'

export default function App() {
  const { session, loading } = useAuth()
  const isUpdatePasswordPage =
    window.location.pathname === '/update-password'

  if (loading) {
    return (
      <main className="loading">
        <img src="/logo.png" alt="DiMarket" />
        <p>Loading DiMarket...</p>
      </main>
    )
  }

  if (isUpdatePasswordPage) {
    return <UpdatePasswordPage />
  }

  return session ? <Dashboard /> : <AuthPage />
}
