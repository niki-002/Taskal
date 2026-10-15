// Auth0の設定値（SPA用のApplicationとAPIの値を .env で設定する）
// domain・clientIdは公開されても問題ない値。Client Secretは絶対に設定しないこと
export const AUTH0_CONFIG = {
  domain: import.meta.env.VITE_AUTH0_DOMAIN,
  clientId: import.meta.env.VITE_AUTH0_CLIENT_ID,
  audience: import.meta.env.VITE_AUTH0_AUDIENCE,
}

export const LOGIN_PATH = '/login'
export const REGISTER_PATH = '/register'
export const TASKS_PATH = '/'
