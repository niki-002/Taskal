import { Auth0Provider, type AppState } from '@auth0/auth0-react'
import type { ReactNode } from 'react'
import { useNavigate } from 'react-router'

import { AUTH0_CONFIG, TASKS_PATH } from '../config'

// Auth0からのコールバック処理後に、ログイン前にいた画面へReact Routerで遷移させる
export function Auth0ProviderWithNavigate({ children }: { children: ReactNode }) {
  const navigate = useNavigate()

  const onRedirectCallback = (appState?: AppState) => {
    // URLに残ったcode・stateも消える
    navigate(appState?.returnTo ?? TASKS_PATH, { replace: true })
  }

  return (
    <Auth0Provider
      domain={AUTH0_CONFIG.domain}
      clientId={AUTH0_CONFIG.clientId}
      // 画面遷移やリロードでログイン状態が消えないよう、トークンをlocalStorageに保存しリフレッシュトークンで更新する
      cacheLocation="localstorage"
      useRefreshTokens
      authorizationParams={{
        audience: AUTH0_CONFIG.audience,
        redirect_uri: window.location.origin,
      }}
      onRedirectCallback={onRedirectCallback}
    >
      {children}
    </Auth0Provider>
  )
}
