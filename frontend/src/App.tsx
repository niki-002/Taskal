import { useAuth0 } from '@auth0/auth0-react'
import { Navigate, Route, Routes } from 'react-router'

import { RequireAuth } from './components/RequireAuth'
import { LOGIN_PATH, REGISTER_PATH, TASKS_PATH } from './config'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { TasksPage } from './pages/TasksPage'

export default function App() {
  const { isLoading, error } = useAuth0()

  // Auth0からのコールバック（code・state付きのリダイレクト）の処理が終わるまで画面を出さない
  if (isLoading) {
    return <p>読み込み中...</p>
  }
  if (error) {
    // URLに ?error= が残っているとリロードしても同じエラーになるため、
    // <Link> ではなく通常のリンクでページを読み込み直してログイン画面へ戻す
    return (
      <>
        <p>ログインに失敗しました：{error.message}</p>
        <a href={LOGIN_PATH}>ログイン画面へ戻る</a>
      </>
    )
  }

  return (
    <Routes>
      <Route path={LOGIN_PATH} element={<LoginPage />} />
      <Route path={REGISTER_PATH} element={<RegisterPage />} />
      <Route
        path={TASKS_PATH}
        element={
          <RequireAuth>
            <TasksPage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to={TASKS_PATH} replace />} />
    </Routes>
  )
}
