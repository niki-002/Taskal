import { useAuth0 } from '@auth0/auth0-react'

import { LOGIN_PATH } from '../config'

export function LogoutButton() {
  const { logout } = useAuth0()

  const handleClick = () => {
    void logout({ logoutParams: { returnTo: `${window.location.origin}${LOGIN_PATH}` } })
  }

  return (
    <button id="logout_button" className="button" type="button" onClick={handleClick}>
      ログアウト
    </button>
  )
}
