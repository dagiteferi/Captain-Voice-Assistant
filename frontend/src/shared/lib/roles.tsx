import React, { createContext, useContext, useState } from 'react'

export type UserRole = 'captain' | 'crew' | 'guest'

interface RoleContextValue {
  role: UserRole
  setRole: (role: UserRole) => void
}

const RoleContext = createContext<RoleContextValue | null>(null)

export function RoleProvider({ children }: { children: React.ReactNode }) {
  const [role, setRole] = useState<UserRole>('captain')
  return (
    <RoleContext.Provider value={{ role, setRole }}>
      {children}
    </RoleContext.Provider>
  )
}

export function useRole(): RoleContextValue {
  const ctx = useContext(RoleContext)
  if (!ctx) throw new Error('useRole must be used within RoleProvider')
  return ctx
}

export const ROLE_META: Record<UserRole, { label: string; description: string; color: string }> = {
  captain: {
    label: 'Captain',
    description: 'Full access — commands, history, knowledge, review queue',
    color: 'text-amber',
  },
  crew: {
    label: 'Crew',
    description: 'Commands + own submissions. Cannot review queue.',
    color: 'text-sky',
  },
  guest: {
    label: 'Guest',
    description: 'Knowledge submission only. No commands.',
    color: 'text-slate',
  },
}
