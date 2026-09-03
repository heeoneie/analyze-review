import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import ReplyStudio from './pages/ReplyStudio.jsx'

// 사장님이 쓰는 화면은 답글 만들기 하나다.
// 수집한 리뷰를 보는 대시보드는 별도 작업으로 다시 붙인다.
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ReplyStudio />
  </StrictMode>,
)
