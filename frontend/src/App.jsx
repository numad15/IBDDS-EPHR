import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import PatientDashboard from './pages/PatientDashboard'
import DoctorDashboard from './pages/DoctorDashboard'
import api from './services/api'

function App() {
  const [user, setUser] = useState(api.getUser())

  const handleLogin = (userData) => {
    setUser(userData)
  }

  const handleLogout = () => {
    api.logout()
    setUser(null)
  }

  if (!user) {
    return (
      <Router>
        <div className="bg-animated"></div>
        <Routes>
          <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />
          <Route path="/register" element={<RegisterPage onLogin={handleLogin} />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </Router>
    )
  }

  return (
    <Router>
      <div className="bg-animated"></div>
      <Routes>
        {user.role === 'patient' ? (
          <Route path="/*" element={<PatientDashboard user={user} onLogout={handleLogout} />} />
        ) : (
          <Route path="/*" element={<DoctorDashboard user={user} onLogout={handleLogout} />} />
        )}
      </Routes>
    </Router>
  )
}

export default App
