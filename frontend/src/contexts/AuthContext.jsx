import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'

import { supabase } from '../lib/supabase'

const AuthContext = createContext(null)
const API_URL =
  import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null)
  const [profile, setProfile] = useState(null)
  const [entitlements, setEntitlements] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadAccount = useCallback(async (nextSession) => {
    const user = nextSession?.user

    if (!user) {
      setProfile(null)
      setEntitlements(null)
      return
    }

    const profileResult = await supabase
      .from('profiles')
      .select(
        'id,email,plan,subscription_status,current_period_start,' +
          'current_period_end,created_at',
      )
      .eq('id', user.id)
      .maybeSingle()

    if (profileResult.error) {
      console.error(
        'Profile load failed:',
        profileResult.error,
      )
    }

    setProfile(
      profileResult.data ?? {
        id: user.id,
        email: user.email,
        plan: 'free',
        subscription_status: 'free',
      },
    )

    try {
      const response = await fetch(
        `${API_URL}/entitlements/me`,
        {
          headers: {
            Authorization:
              `Bearer ${nextSession.access_token}`,
          },
        },
      )

      const payload = await response.json().catch(() => null)

      if (!response.ok) {
        throw new Error(
          payload?.detail ||
            `Entitlement load failed (${response.status}).`,
        )
      }

      setEntitlements(payload)
    } catch (error) {
      console.error('Entitlement load failed:', error)
      setEntitlements(null)
    }
  }, [])

  const refreshAccount = useCallback(async () => {
    await loadAccount(session)
  }, [loadAccount, session])

  const applyEntitlements = useCallback(
    (nextEntitlements) => {
      if (nextEntitlements) {
        setEntitlements(nextEntitlements)
      }
    },
    [],
  )

  useEffect(() => {
    let mounted = true

    supabase.auth.getSession().then(
      async ({ data, error }) => {
        if (!mounted) return

        if (error) {
          console.error('Session load failed:', error)
        }

        const nextSession = data.session ?? null
        setSession(nextSession)
        await loadAccount(nextSession)

        if (mounted) {
          setLoading(false)
        }
      },
    )

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(
      async (_event, nextSession) => {
        setSession(nextSession)
        await loadAccount(nextSession)
        setLoading(false)
      },
    )

    return () => {
      mounted = false
      subscription.unsubscribe()
    }
  }, [loadAccount])

  const usageCount =
    entitlements?.forecasts_used ?? 0

  const value = useMemo(
    () => ({
      session,
      user: session?.user ?? null,
      profile,
      entitlements,
      usageCount,
      loading,
      refreshAccount,
      applyEntitlements,
    }),
    [
      session,
      profile,
      entitlements,
      usageCount,
      loading,
      refreshAccount,
      applyEntitlements,
    ],
  )

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const value = useContext(AuthContext)

  if (!value) {
    throw new Error(
      'useAuth must be used inside AuthProvider',
    )
  }

  return value
}
