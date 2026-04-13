import { useState, useEffect } from 'react'
import api from '../services/api'

export default function DoctorDashboard({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState('records')
  const [records, setRecords] = useState([])
  const [grants, setGrants] = useState([])
  const [auditLogs, setAuditLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState(null)

  // Record detail
  const [showRecord, setShowRecord] = useState(null)
  const [recordDetail, setRecordDetail] = useState(null)
  const [decrypting, setDecrypting] = useState(false)

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [recs, grs] = await Promise.all([
        api.listRecords(), api.listGrants()
      ])
      setRecords(recs.records || [])
      setGrants(grs.grants || [])
    } catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  const loadAuditLogs = async () => {
    try {
      const data = await api.getAuditLogs()
      setAuditLogs(data.logs || [])
    } catch (e) { setError(e.message) }
  }

  useEffect(() => {
    if (activeTab === 'audit') loadAuditLogs()
  }, [activeTab])

  const viewRecord = async (recordId) => {
    setDecrypting(true)
    setShowRecord(recordId)
    setRecordDetail(null)
    try {
      const data = await api.getRecord(recordId)
      setRecordDetail(data)
    } catch (e) {
      setError(e.message)
      setShowRecord(null)
    } finally {
      setDecrypting(false)
    }
  }

  useEffect(() => {
    if (message) { const t = setTimeout(() => setMessage(null), 4000); return () => clearTimeout(t) }
  }, [message])
  useEffect(() => {
    if (error) { const t = setTimeout(() => setError(''), 4000); return () => clearTimeout(t) }
  }, [error])

  const tabs = [
    { id: 'records', icon: '📋', label: 'Accessible Records' },
    { id: 'grants', icon: '🔑', label: 'My Grants' },
    { id: 'audit', icon: '📜', label: 'Audit Log' },
  ]

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>🛡️ IBDDS</h1>
          <p>Doctor Portal</p>
        </div>
        <div className="sidebar-user">
          <div className="sidebar-avatar" style={{background:'linear-gradient(135deg, #10b981, #06b6d4)'}}>
            {user.email[0].toUpperCase()}
          </div>
          <div className="sidebar-user-info">
            <h3>{user.email.split('@')[0]}</h3>
            <p>Doctor</p>
          </div>
        </div>
        <nav className="sidebar-nav">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`nav-item ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
              id={`nav-${tab.id}`}
            >
              <span className="nav-icon">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button className="nav-item" onClick={onLogout} id="nav-logout">
            <span className="nav-icon">🚪</span>
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="main-content">
        {message && <div className={`alert alert-${message.type}`}>{message.text}</div>}
        {error && <div className="alert alert-error">⚠️ {error}</div>}

        {/* Stats */}
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">📄</div>
            <div className="stat-value">{records.length}</div>
            <div className="stat-label">Accessible Records</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">🔑</div>
            <div className="stat-value">{grants.filter(g => g.is_active).length}</div>
            <div className="stat-label">Active Grants</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">🔒</div>
            <div className="stat-value">IBE</div>
            <div className="stat-label">Encryption Scheme</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">🏥</div>
            <div className="stat-value">3-of-5</div>
            <div className="stat-label">Threshold Decryption</div>
          </div>
        </div>

        {/* Records Tab */}
        {activeTab === 'records' && (
          <div style={{animation: 'fadeIn 0.4s ease'}}>
            <div className="page-header">
              <h1>Accessible Patient Records</h1>
              <p>Records shared with you by patients through access grants</p>
            </div>

            {loading ? (
              <div className="loading-overlay"><div className="spinner"></div><p>Loading records...</p></div>
            ) : records.length === 0 ? (
              <div className="glass-card-static">
                <div className="empty-state">
                  <div className="empty-icon">📋</div>
                  <h3>No Accessible Records</h3>
                  <p>Patients can grant you access to specific fields of their health records</p>
                </div>
              </div>
            ) : (
              <div className="glass-card-static">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Patient</th>
                      <th>Record ID</th>
                      <th>Created</th>
                      <th>Allowed Fields</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.map(rec => (
                      <tr key={rec.record_id + rec.grant_id}>
                        <td style={{fontWeight:600, color:'var(--accent-emerald)'}}>
                          {rec.patient_email || 'Unknown Patient'}
                        </td>
                        <td><code style={{color:'var(--accent-blue)', fontSize:'0.82rem'}}>{rec.record_id.slice(0, 8)}...</code></td>
                        <td>{new Date(rec.created_at).toLocaleDateString()}</td>
                        <td>
                          <div className="field-chips">
                            {rec.allowed_fields?.map(f => (
                              <span key={f} className="field-chip">{f}</span>
                            ))}
                          </div>
                        </td>
                        <td>
                          <button className="btn btn-sm btn-primary" onClick={() => viewRecord(rec.record_id)}>
                            🔓 Decrypt & View
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Grants Tab */}
        {activeTab === 'grants' && (
          <div style={{animation: 'fadeIn 0.4s ease'}}>
            <div className="page-header">
              <h1>My Access Grants</h1>
              <p>Grants that patients have given you to access their records</p>
            </div>

            {grants.length === 0 ? (
              <div className="glass-card-static">
                <div className="empty-state">
                  <div className="empty-icon">🔑</div>
                  <h3>No Grants</h3>
                  <p>You haven't received any access grants yet</p>
                </div>
              </div>
            ) : (
              <div className="glass-card-static">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Patient</th>
                      <th>Fields</th>
                      <th>Granted</th>
                      <th>Expires</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {grants.map(g => (
                      <tr key={g.grant_id}>
                        <td style={{fontWeight:600}}>{g.patient_email || 'Unknown'}</td>
                        <td>
                          <div className="field-chips">
                            {g.resource_fields?.map(f => (
                              <span key={f} className="field-chip">{f}</span>
                            ))}
                          </div>
                        </td>
                        <td>{new Date(g.granted_at).toLocaleDateString()}</td>
                        <td>{g.expires_at ? new Date(g.expires_at).toLocaleDateString() : 'Never'}</td>
                        <td>
                          <span className={`badge ${g.is_active ? 'badge-success' : 'badge-danger'}`}>
                            {g.is_active ? 'Active' : 'Expired'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Audit Tab */}
        {activeTab === 'audit' && (
          <div style={{animation: 'fadeIn 0.4s ease'}}>
            <div className="page-header">
              <h1>Audit Log</h1>
              <p>Your access activity history</p>
            </div>
            <div className="glass-card-static">
              {auditLogs.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">📜</div>
                  <h3>No Audit Entries</h3>
                </div>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Timestamp</th>
                      <th>Action</th>
                      <th>Status</th>
                      <th>Resource</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLogs.map(log => (
                      <tr key={log.entry_id}>
                        <td style={{whiteSpace:'nowrap'}}>{new Date(log.timestamp).toLocaleString()}</td>
                        <td><span className="badge badge-info">{log.action}</span></td>
                        <td>
                          <span className={`badge ${log.status === 'success' ? 'badge-success' : 'badge-danger'}`}>
                            {log.status}
                          </span>
                        </td>
                        <td><code style={{fontSize:'0.78rem',color:'var(--text-muted)'}}>{log.resource_id?.slice(0,8) || '—'}</code></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Record Detail Modal */}
      {showRecord && (
        <div className="modal-overlay" onClick={() => { setShowRecord(null); setRecordDetail(null) }}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{maxWidth:700}}>
            <div className="modal-header">
              <h2>🔓 Decrypted Record</h2>
              <button className="modal-close" onClick={() => { setShowRecord(null); setRecordDetail(null) }}>✕</button>
            </div>
            <div className="modal-body">
              {decrypting ? (
                <div className="loading-overlay">
                  <div className="spinner"></div>
                  <p>Performing threshold decryption...</p>
                  <p className="text-sm text-muted">Gathering partial decryptions from 3 of 5 servers</p>
                </div>
              ) : recordDetail ? (
                <>
                  <div className="flex items-center gap-3 mb-4">
                    <span className="badge badge-success">🔓 Decrypted</span>
                    <span className="badge badge-purple">🔑 Grant Access</span>
                    {recordDetail.allowed_fields && (
                      <span className="badge badge-info">
                        {recordDetail.allowed_fields.length} fields visible
                      </span>
                    )}
                  </div>

                  <div className="alert alert-info" style={{marginBottom:20}}>
                    ℹ️ You can only see fields that the patient has granted you access to.
                    {recordDetail.allowed_fields && ` Visible fields: ${recordDetail.allowed_fields.join(', ')}`}
                  </div>

                  <div className="record-detail">
                    {recordDetail.data && Object.entries(recordDetail.data).map(([key, value]) => (
                      <div className="record-field" key={key}>
                        <div className="field-label">{key.replace(/_/g, ' ')}</div>
                        <div className="field-value">
                          {Array.isArray(value) ? value.join(', ') : String(value)}
                        </div>
                      </div>
                    ))}
                  </div>

                  {recordDetail.metadata && (
                    <div className="mt-4" style={{fontSize:'0.82rem', color:'var(--text-muted)'}}>
                      <p>🔒 Decrypted via threshold scheme: {recordDetail.metadata.threshold}</p>
                      <p>📅 Record created: {new Date(recordDetail.created_at).toLocaleString()}</p>
                    </div>
                  )}
                </>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
