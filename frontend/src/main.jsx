import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import ReplyStudio from './pages/ReplyStudio.jsx'

// 사장님이 쓰는 화면은 답글 만들기 하나다.
// 기존 리뷰 분석 대시보드는 #dashboard 로 남겨 둔다.
function Root() {
  const [isDashboard, setIsDashboard] = useState(
    () => window.location.hash === '#dashboard',
  )

  useEffect(() => {
    // 모듈 로드 시점에 한 번만 읽으면 해시를 바꿔도 화면이 안 바뀐다.
    const onHashChange = () => setIsDashboard(window.location.hash === '#dashboard')
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  return isDashboard ? <App /> : <ReplyStudio />
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Root />
  </StrictMode>,
)
