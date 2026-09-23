export interface AuthUser {
  id: string
  email: string
  username: string
  is_active: boolean
  is_admin: boolean
  created_at: string
}

export interface AccessSession {
  access_token: string
  token_type: string
  expires_in: number
}

export interface LoginInput {
  email: string
  password: string
}

export interface RegisterInput extends LoginInput {
  username: string
}
