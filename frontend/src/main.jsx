import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@xyflow/react/dist/style.css'
import './index.css'
import App from './App.jsx'
import ReplyStudio from './pages/ReplyStudio.jsx'
import { LangProvider } from './contexts/LangContext.jsx'

// 사장님이 쓰는 화면은 답글 만들기 하나다.
// 기존 리뷰 분석 대시보드는 #dashboard 로 남겨 둔다.
const isDashboard = window.location.hash === '#dashboard'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <LangProvider>
      {isDashboard ? <App /> : <ReplyStudio />}
    </LangProvider>
  </StrictMode>,
)
