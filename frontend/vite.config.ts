import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // バックエンドと同じリポジトリ直下の .env を読み込む（VITE_ で始まる変数だけがフロントに公開される）
  envDir: '..',
  server: {
    port: 5173,
    // Auth0のCallback URLなどに登録したオリジンと揃えるため、ポートが使用中なら起動を失敗させる
    strictPort: true,
    proxy: {
      // /api へのリクエストはバックエンド（FastAPI）へ転送する
      '/api': 'http://localhost:8000',
    },
  },
})
