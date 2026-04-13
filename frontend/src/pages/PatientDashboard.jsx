import { useState, useEffect } from 'react'
import api from '../services/api'

export default function PatientDashboard({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState('records')
  const [records, setRecords] = useState([])
  const [grants, setGrants] = useState([])
  const [auditLogs, setAuditLogs] = useState([])
  const [doctors, setDoctors] = useState([])
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState(null)
  const [error, setError] = useState('')

  // Modal states
  const [showUpload, setShowUpload] = useState(false)
  const [showGrant, setShowGrant] = useState(false)
  const [showRecord, setShowRecord] = useState(null)
  const [recordDetail, setRecordDetail] = useState(null)

  // Upload form
  const [healthData, setHealthData] = useState({
    name: '', age: '', blood_type: '', medications: '',
    allergies: '', conditions: '', emergency_contact: '', insurance: ''
  })

  // Grant form
  const [grantForm, setGrantForm] = useState({
    accessor_email: '', duration_days: 30,
    fields: { name: false, age: false, blood_type: true, medications: true, allergies: true, conditions: false, emergency_contact: false, insurance: false }
  })

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [recs, grs, docs] = await Promise.all([
        api.listRecords(), api.listGrants(), api.getDoctors()
      ])
      setRecords(recs.records || [])
      setGrants(grs.grants || [])
      setDoctors(docs.doctors || [])
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

  const handleUpload = async (e) => {
    e.preventDefault()
    try {
      const data = { ...healthData }
      if (data.medications) data.medications = data.medications.split(',').map(s => s.trim())
      if (data.allergies) data.allergies = data.allergies.split(',').map(s => s.trim())
      if (data.conditions) data.conditions = data.conditions.split(',').map(s => s.trim())
      if (data.age) data.age = parseInt(data.age)
      
      // Remove empty fields
      Object.keys(data).forEach(k => { if (!data[k] || (Array.isArray(data[k]) && data[k].length === 0)) delete data[k] })

      await api.uploadRecord(data)
      setMessage({ type: 'success', text: 'Record encrypted and stored successfully! 🎉' })
      setShowUpload(false)
      setHealthData({ name: '', age: '', blood_type: '', medications: '', allergies: '', conditions: '', emergency_contact: '', insurance: '' })
      loadData()
    } catch (e) { setError(e.message) }
  }

  const handleGrant = async (e) => {
    e.preventDefault()
    try {
      const fields = Object.entries(grantForm.fields).filter(([, v]) => v).map(([k]) => k)
      if (fields.length === 0) { setError('Select at least one field'); return }
      await api.grantAccess(grantForm.accessor_email, ['read'], fields, grantForm.duration_days)
      setMessage({ type: 'success', text: 'Access granted successfully! 🔑' })
      setShowGrant(false)
      loadData()
    } catch (e) { setError(e.message) }
  }

  const handleRevoke = async (grantId) => {
    try {
      await api.revokeAccess(grantId)
      setMessage({ type: 'success', text: 'Access revoked' })
      loadData()
    } catch (e) { setError(e.message) }
  }

  const viewRecord = async (recordId) => {
    try {
      const data = await api.getRecord(recordId)
      setRecordDetail(data)
      setShowRecord(recordId)
    } catch (e) { setError(e.message) }
  }

  const tabs = [
    { id: 'records', icon: '📋', label: 'My Records' },
    { id: 'grants', icon: '🔑', label: 'Access Grants' },
    { id: 'upload', icon: '📤', label: 'Upload Record' },
    { id: 'audit', icon: '📜', label: 'Audit Log' },
  ]

  useEffect(() => {
    if (message) { const t = setTimeout(() => setMessage(null), 4000); return () => clearTimeout(t) }
  }, [message])
  useEffect(() => {
    if (error) { const t = setTimeout(() => setError(''), 4000); return () => clearTimeout(t) }
  }, [error])

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h1>🛡️ IBDDS</h1>
          <p>Patient Portal</p>
        </div>
        <div className="sidebar-user">
          <div className="sidebar-avatar">{user.email[0].toUpperCase()}</div>
          <div className="sidebar-user-info">
            <h3>{user.email.split('@')[0]}</h3>
            <p>Patient</p>
          </div>
        </div>
        <nav className="sidebar-nav">
          {tabs.map(tab => (
            <button
              key={tab.id}
              className={`nav-item ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => { tab.id === 'upload' ? setShowUpload(true) : setActiveTab(tab.id) }}
              id={`nav-${tab.id}`}
            >
              <span className="nav-icon">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
          <div style={{flex:1}}></div>
          <button className="nav-item" onClick={() => setShowGrant(true)} id="nav-new-grant">
            <span className="nav-icon">➕</span>
            New Grant
          </button>
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
            <div className="stat-label">Total Records</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">🔑</div>
            <div className="stat-value">{grants.filter(g => !g.revoked).length}</div>
            <div className="stat-label">Active Grants</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">🩺</div>
            <div className="stat-value">{doctors.length}</div>
            <div className="stat-label">Registered Doctors</div>
          </div>
          <div className="stat-card">
            <div className="stat-icon">🔒</div>
            <div className="stat-value">3-of-5</div>
            <div className="stat-label">Threshold Encryption</div>
          </div>
        </div>

        {/* Records Tab */}
        {activeTab === 'records' && (
          <div style={{animation: 'fadeIn 0.4s ease'}}>
            <div className="page-header page-header-row">
              <div>
                <h1>My Health Records</h1>
                <p>All records are encrypted with Identity-Based Encryption</p>
              </div>
              <button className="btn btn-primary" onClick={() => setShowUpload(true)}>
                ➕ Upload New Record
              </button>
            </div>

            {loading ? (
              <div className="loading-overlay"><div className="spinner"></div><p>Loading records...</p></div>
            ) : records.length === 0 ? (
              <div className="glass-card-static">
                <div className="empty-state">
                  <div className="empty-icon">📋</div>
                  <h3>No Records Yet</h3>
                  <p>Upload your first health record to get started. All data is encrypted with IBE.</p>
                  <button className="btn btn-primary mt-4" onClick={() => setShowUpload(true)}>Upload Record</button>
                </div>
              </div>
            ) : (
              <div className="glass-card-static">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Record ID</th>
                      <th>Created</th>
                      <th>Encryption</th>
                      <th>Fields</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.map(rec => (
                      <tr key={rec.record_id}>
                        <td><code style={{color:'var(--accent-blue)', fontSize:'0.82rem'}}>{rec.record_id.slice(0, 8)}...</code></td>
                        <td>{new Date(rec.created_at).toLocaleDateString()}</td>
                        <td><span className="badge badge-success">🔐 {rec.encryption_algorithm}</span></td>
                        <td>
                          <div className="field-chips">
                            {rec.metadata?.fields?.slice(0, 3).map(f => (
                              <span key={f} className="field-chip">{f}</span>
                            ))}
                            {rec.metadata?.fields?.length > 3 && (
                              <span className="field-chip">+{rec.metadata.fields.length - 3}</span>
                            )}
                          </div>
                        </td>
                        <td>
                          <button className="btn btn-sm btn-outline" onClick={() => viewRecord(rec.record_id)}>
                            👁️ View
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
            <div className="page-header page-header-row">
              <div>
                <h1>Access Grants</h1>
                <p>Manage who can access your health records</p>
              </div>
              <button className="btn btn-success" onClick={() => setShowGrant(true)}>
                ➕ New Grant
              </button>
            </div>

            {grants.length === 0 ? (
              <div className="glass-card-static">
                <div className="empty-state">
                  <div className="empty-icon">🔑</div>
                  <h3>No Grants Yet</h3>
                  <p>Grant a doctor access to specific fields of your health records</p>
                </div>
              </div>
            ) : (
              <div className="glass-card-static">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Doctor</th>
                      <th>Allowed Fields</th>
                      <th>Granted</th>
                      <th>Expires</th>
                      <th>Status</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {grants.map(g => (
                      <tr key={g.grant_id}>
                        <td style={{fontWeight:600}}>{g.accessor_email || 'Unknown'}</td>
                        <td>
                          <div className="field-chips">
                            {g.resource_fields?.map(f => <span key={f} className="field-chip">{f}</span>)}
                          </div>
                        </td>
                        <td>{new Date(g.granted_at).toLocaleDateString()}</td>
                        <td>{g.expires_at ? new Date(g.expires_at).toLocaleDateString() : 'Never'}</td>
                        <td>
                          {g.revoked ? (
                            <span className="badge badge-danger">Revoked</span>
                          ) : (
                            <span className="badge badge-success">Active</span>
                          )}
                        </td>
                        <td>
                          {!g.revoked && (
                            <button className="btn btn-sm btn-danger" onClick={() => handleRevoke(g.grant_id)}>
                              Revoke
                            </button>
                          )}
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
              <p>Complete history of all actions on your health records (HIPAA compliant)</p>
            </div>
            <div className="glass-card-static">
              {auditLogs.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">📜</div>
                  <h3>No Audit Entries</h3>
                  <p>Actions will appear here as they occur</p>
                </div>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Timestamp</th>
                      <th>Action</th>
                      <th>Status</th>
                      <th>Resource</th>
                      <th>Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLogs.map(log => (
                      <tr key={log.entry_id}>
                        <td style={{whiteSpace:'nowrap'}}>{new Date(log.timestamp).toLocaleString()}</td>
                        <td>
                          <span className="badge badge-info">{log.action}</span>
                        </td>
                        <td>
                          <span className={`badge ${log.status === 'success' ? 'badge-success' : 'badge-danger'}`}>
                            {log.status}
                          </span>
                        </td>
                        <td><code style={{fontSize:'0.78rem',color:'var(--text-muted)'}}>{log.resource_id?.slice(0,8) || '—'}...</code></td>
                        <td style={{fontSize:'0.8rem',color:'var(--text-muted)',maxWidth:200,overflow:'hidden',textOverflow:'ellipsis'}}>
                          {log.details ? JSON.stringify(log.details).slice(0, 60) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Upload Modal */}
      {showUpload && (
        <div className="modal-overlay" onClick={() => setShowUpload(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📤 Upload Health Record</h2>
              <button className="modal-close" onClick={() => setShowUpload(false)}>✕</button>
            </div>
            <form onSubmit={handleUpload}>
              <div className="modal-body">
                <p className="text-sm text-muted mb-4">Your data will be encrypted with Identity-Based Encryption (Boneh-Franklin) and protected by 3-of-5 threshold decryption.</p>
                
                {[
                  { key: 'name', label: 'Full Name', placeholder: 'John Doe', type: 'text' },
                  { key: 'age', label: 'Age', placeholder: '45', type: 'number' },
                  { key: 'blood_type', label: 'Blood Type', placeholder: 'O+, A-, B+, etc.' },
                  { key: 'medications', label: 'Medications', placeholder: 'Lisinopril, Metformin (comma-separated)' },
                  { key: 'allergies', label: 'Allergies', placeholder: 'Penicillin, Sulfa (comma-separated)' },
                  { key: 'conditions', label: 'Conditions', placeholder: 'Hypertension, Diabetes (comma-separated)' },
                  { key: 'emergency_contact', label: 'Emergency Contact', placeholder: 'Jane Doe - (555) 123-4567' },
                  { key: 'insurance', label: 'Insurance', placeholder: 'BlueCross - Policy #BC123456' },
                ].map(field => (
                  <div className="form-group" key={field.key}>
                    <label className="form-label">{field.label}</label>
                    <input
                      className="form-input"
                      type={field.type || 'text'}
                      placeholder={field.placeholder}
                      value={healthData[field.key]}
                      onChange={e => setHealthData({...healthData, [field.key]: e.target.value})}
                    />
                  </div>
                ))}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-ghost" onClick={() => setShowUpload(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary">🔐 Encrypt & Store</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Grant Modal */}
      {showGrant && (
        <div className="modal-overlay" onClick={() => setShowGrant(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>🔑 Grant Access</h2>
              <button className="modal-close" onClick={() => setShowGrant(false)}>✕</button>
            </div>
            <form onSubmit={handleGrant}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Doctor's Email</label>
                  <select
                    className="form-select"
                    value={grantForm.accessor_email}
                    onChange={e => setGrantForm({...grantForm, accessor_email: e.target.value})}
                    required
                  >
                    <option value="">Select a doctor...</option>
                    {doctors.map(d => (
                      <option key={d.id} value={d.email}>{d.email}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Allowed Fields</label>
                  <p className="text-sm text-muted" style={{marginBottom:10}}>Select which fields the doctor can see</p>
                  {Object.keys(grantForm.fields).map(field => (
                    <div className="form-checkbox" key={field}>
                      <input
                        type="checkbox"
                        id={`field-${field}`}
                        checked={grantForm.fields[field]}
                        onChange={e => setGrantForm({
                          ...grantForm,
                          fields: { ...grantForm.fields, [field]: e.target.checked }
                        })}
                      />
                      <label htmlFor={`field-${field}`}>{field.replace(/_/g, ' ')}</label>
                    </div>
                  ))}
                </div>

                <div className="form-group">
                  <label className="form-label">Duration (Days)</label>
                  <input
                    className="form-input"
                    type="number"
                    min="1"
                    max="365"
                    value={grantForm.duration_days}
                    onChange={e => setGrantForm({...grantForm, duration_days: parseInt(e.target.value)})}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-ghost" onClick={() => setShowGrant(false)}>Cancel</button>
                <button type="submit" className="btn btn-success">✅ Grant Access</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Record Detail Modal */}
      {showRecord && recordDetail && (
        <div className="modal-overlay" onClick={() => { setShowRecord(null); setRecordDetail(null) }}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{maxWidth:700}}>
            <div className="modal-header">
              <h2>📋 Record Details</h2>
              <button className="modal-close" onClick={() => { setShowRecord(null); setRecordDetail(null) }}>✕</button>
            </div>
            <div className="modal-body">
              <div className="flex items-center gap-3 mb-4">
                <span className="badge badge-success">🔓 Decrypted</span>
                <span className="badge badge-purple">🔑 {recordDetail.access_type === 'owner' ? 'Owner Access' : 'Grant Access'}</span>
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
                  <p>🔒 Encryption: {recordDetail.metadata.encryption_algorithm} | Threshold: {recordDetail.metadata.threshold}</p>
                  <p>📅 Created: {new Date(recordDetail.created_at).toLocaleString()}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
