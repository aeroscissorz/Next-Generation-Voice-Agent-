import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import ChatSession from './pages/ChatSession'
import SplashCursor from './components/SplashCursor'
import { SidebarProvider } from './context/SidebarContext'
import './App.css'
import './styles/scrollbar.css'

function App() {
  return (
    <Router>
      <SidebarProvider>
        {/* <SplashCursor /> */}
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/dashboard/:sessionId" element={<ChatSession />} />
        </Routes>
      </SidebarProvider>
    </Router>
  )
}

export default App
