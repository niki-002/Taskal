import { useAuth0 } from '@auth0/auth0-react'
import { Navigate } from 'react-router'

import { AuthCard } from '../components/AuthCard'
import { LoginButton } from '../components/LoginButton'
import { REGISTER_PATH, TASKS_PATH } from '../config'

export function LoginPage() {
  const { isAuthenticated } = useAuth0()

  // ログイン済みならタスク一覧へ
  if (isAuthenticated) {
    return <Navigate to={TASKS_PATH} replace />
  }

  return (
    <AuthCard
      description="Taskalを利用するにはログインする必要があります"
      linkTo={REGISTER_PATH}
      linkText="アカウントをお持ちでない方はこちら"
    >
      <title>Taskal-login</title>
      <LoginButton label="ログイン" />
    </AuthCard>
  )
}
