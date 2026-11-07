import type { MembershipRole, UserRole } from './auth'

export interface Farm {
  id: number
  name: string
  country: string
  region: string
  locality: string
  description: string
  is_active: boolean
  is_demo: boolean
  my_role: MembershipRole | null
  my_role_label: string | null
  members_count: number
  created_at: string
  updated_at: string
}

export interface FarmMember {
  id: number
  user_id: number
  user_email: string
  user_name: string
  user_role: UserRole
  role: MembershipRole
  role_label: string
  is_active: boolean
  created_at: string
}
