// APIのベースパス（/api/v1 への変更時はここだけ直す）
export const API_BASE_PATH = '/api'

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  // 失敗時に投げるエラーのメッセージ（省略時はレスポンスのdetailかステータスコード）
  errorMessage?: string
}

// API呼び出し関数の型。api/ 配下の関数はこれを受け取って使う
export type ApiRequest = <T>(path: string, options?: RequestOptions) => Promise<T>

// アクセストークンを取得する関数を受け取り、Authorizationヘッダ付きでAPIを呼び出す関数を作る
export function createApiRequest(getAccessToken: () => Promise<string>): ApiRequest {
  return async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { method = 'GET', body, errorMessage } = options

    const headers: Record<string, string> = {
      Authorization: `Bearer ${await getAccessToken()}`,
    }
    if (body !== undefined) {
      headers['Content-Type'] = 'application/json'
    }

    const response = await fetch(`${API_BASE_PATH}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })

    if (!response.ok) {
      throw new ApiError(errorMessage ?? (await readErrorDetail(response)), response.status)
    }
    if (response.status === 204) {
      return undefined as T
    }
    return (await response.json()) as T
  }
}

// FastAPIのエラーレスポンス（{"detail": "..."}）からメッセージを取り出す
async function readErrorDetail(response: Response): Promise<string> {
  try {
    const data: unknown = await response.json()
    if (typeof data === 'object' && data !== null && 'detail' in data) {
      const { detail } = data
      if (typeof detail === 'string') return detail
    }
  } catch {
    // JSONでないレスポンスはステータスコードだけ返す
  }
  return `Request failed with status ${response.status}`
}
