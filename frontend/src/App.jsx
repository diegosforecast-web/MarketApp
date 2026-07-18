import './App.css'
import AuthPage from './components/AuthPage'
import Dashboard from './components/Dashboard'
import { useAuth } from './contexts/AuthContext'

export default function App() {
  const { session, loading } = useAuth()
  if (loading) return <main className="loading"><img src="/logo.png" alt="DiMarket"/><p>Loading DiMarket...</p></main>
  return session ? <Dashboard/> : <AuthPage/>
}
