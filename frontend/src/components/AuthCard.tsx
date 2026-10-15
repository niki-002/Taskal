import type { ReactNode } from 'react'
import { Link } from 'react-router'

import { useBodyClass } from '../hooks/useBodyClass'

interface AuthCardProps {
  description: string
  linkTo: string
  linkText: string
  children: ReactNode
}

// ログイン・新規登録画面の共通レイアウト
export function AuthCard({ description, linkTo, linkText, children }: AuthCardProps) {
  useBodyClass('auth_body')

  return (
    <main className="mainpage">
      <div className="logo_area">
        <img className="svg" src="/icon.svg" alt="Taskal" />
      </div>

      <p className="description">{description}</p>

      <section>
        {children}
        <Link className="link" to={linkTo}>
          {linkText}
        </Link>
      </section>
    </main>
  )
}
