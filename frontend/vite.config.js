import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // 카카오 로그인은 <a href="/api/auth/kakao/login"> 로 브라우저를 넘긴다.
      // 프록시가 없으면 dev 서버(5173)가 그 경로를 자기 것으로 받아
      // 로그인이 백엔드에 닿지 않는다. 세션 쿠키도 같은 출처여야 붙는다.
      '/api': 'http://localhost:8000',
    },
  },
})
