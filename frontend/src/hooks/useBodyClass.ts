import { useEffect } from 'react'

// 表示中の画面だけ <body> にクラスを付ける（画面ごとの背景色などを切り替えるため）
export function useBodyClass(className: string): void {
  useEffect(() => {
    document.body.classList.add(className)
    return () => document.body.classList.remove(className)
  }, [className])
}
