import { useAuth0 } from '@auth0/auth0-react'
import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router'

import { LOGIN_PATH } from '../config'

// 未ログインならログイン画面へリダイレクトする（ログイン後に元の画面へ戻れるよう遷移元を渡す）
export function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth0()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to={LOGIN_PATH} replace state={{ from: location.pathname }} />
  }
  return children
}
