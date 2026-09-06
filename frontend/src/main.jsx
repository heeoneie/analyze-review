import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import ReplyStudio from './pages/ReplyStudio.jsx'
import Dashboard from './pages/Dashboard.jsx'

// 화면은 둘이다. 답글 만들기(기본)와 모아 둔 리뷰(#dashboard).
// 라우터 라이브러리를 넣을 만큼 복잡하지 않아 해시로 가른다.
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

  return isDashboard ? <Dashboard /> : <ReplyStudio />
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Root />
  </StrictMode>,
)
