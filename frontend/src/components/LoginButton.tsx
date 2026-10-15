import { useAuth0 } from '@auth0/auth0-react'
import type { FormEvent } from 'react'
import { useLocation } from 'react-router'

import { TASKS_PATH } from '../config'

interface LoginButtonProps {
  label: string
  // "signup" を渡すとAuth0の新規登録画面を開く
  screenHint?: 'signup'
}

// Auth0のログイン（新規登録）画面へ遷移するボタン
export function LoginButton({ label, screenHint }: LoginButtonProps) {
  const { loginWithRedirect } = useAuth0()
  const location = useLocation()
  // ログイン必須の画面から飛ばされてきた場合は、ログイン後にその画面へ戻す
  const returnTo = (location.state as { from?: string } | null)?.from ?? TASKS_PATH

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    try {
      await loginWithRedirect({
        appState: { returnTo },
        authorizationParams: screenHint ? { screen_hint: screenHint } : {},
      })
    } catch (error) {
      alert(error instanceof Error ? error.message : String(error))
    }
  }

  return (
    <form className="form" onSubmit={handleSubmit}>
      <button id="regist_button" type="submit" name="regist_button">
        {label}
      </button>
    </form>
  )
}
