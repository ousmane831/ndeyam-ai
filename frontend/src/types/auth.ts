export type UserRole = 'ADMIN' | 'ELEVEUR' | 'EXPERT'
export type MembershipRole = 'OWNER' | 'MANAGER' | 'EXPERT' | 'VETERINARIAN' | 'TECHNICIAN'

export interface MembershipSummary {
  farm_id: number
  farm_name: string
  role: MembershipRole
  role_label: string
}

export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  phone: string
  role: UserRole
  role_label: string
  is_platform_admin: boolean
  memberships: MembershipSummary[]
  date_joined: string
}

export interface AuthTokens {
  access: string
  refresh: string
}

export interface RegisterPayload {
  email: string
  password: string
  password_confirm: string
  first_name: string
  last_name: string
  phone?: string
  farm_name: string
  farm_region?: string
  farm_locality?: string
}

export interface AdminUser {
  id: number
  email: string
  first_name: string
  last_name: string
  phone: string
  role: UserRole
  role_label: string
  is_active: boolean
  farms_count: number
  date_joined: string
  last_login: string | null
}
