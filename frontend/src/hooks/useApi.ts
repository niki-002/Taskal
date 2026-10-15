import { useAuth0 } from '@auth0/auth0-react'
import { useMemo } from 'react'
import { useNavigate } from 'react-router'

import { createApiRequest, type ApiRequest } from '../api/client'
import { LOGIN_PATH } from '../config'

// Auth0のアクセストークンをAuthorizationヘッダに付けてAPIを呼び出す関数を返す
export function useApi(): ApiRequest {
  const { getAccessTokenSilently } = useAuth0()
  const navigate = useNavigate()

  return useMemo(
    () =>
      createApiRequest(async () => {
        let token: string | undefined
        try {
          token = await getAccessTokenSilently()
        } catch {
          // 取れなかった場合は下でログイン画面へ遷移させる
        }
        if (!token) {
          // トークンが取れない（未ログイン・期限切れ）ならログイン画面へ
          navigate(LOGIN_PATH)
          throw new Error('ログインしてください')
        }
        return token
      }),
    [getAccessTokenSilently, navigate],
  )
}
