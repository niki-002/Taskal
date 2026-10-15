import { AuthCard } from '../components/AuthCard'
import { LoginButton } from '../components/LoginButton'
import { LOGIN_PATH } from '../config'

export function RegisterPage() {
  return (
    <AuthCard
      description="Taskalを利用するにはユーザー登録する必要があります"
      linkTo={LOGIN_PATH}
      linkText="アカウントをお持ちの方はこちら"
    >
      <title>Taskal-regist</title>
      <LoginButton label="登録する" screenHint="signup" />
    </AuthCard>
  )
}
