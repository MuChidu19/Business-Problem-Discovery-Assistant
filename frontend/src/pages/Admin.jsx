import { useEffect, useMemo, useState, useCallback } from 'react'
import SharedHeader from '../components/SharedHeader'
import { getFeedback } from '../api/client'

function toCSV(rows) {
  if (!rows || !rows.length) return ''
  const headers = Object.keys(rows[0])
  const esc = (v) => {
    const s = `${v??''}`.replaceAll('"', '""')
    return /[,"]/.test(s) ? `"${s}"` : s
  }
  const lines = [headers.join(',')].concat(rows.map(r => headers.map(h => esc(r[h])).join(',')))
  return lines.join('\n')
}

export default function Admin() {
  const [rows, setRows] = useState([])
  const [agent, setAgent] = useState('All')
  const [type, setType] = useState('All')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const fetchRows = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getFeedback()
      setRows(Array.isArray(data?.rows) ? data.rows : [])
    } catch (e) {
      console.error('Failed to load feedback', e)
      setError(`Failed to load feedback: ${e?.message || e}`)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchRows() }, [fetchRows])

  const agents = useMemo(() => ['All'].concat(Array.from(new Set(rows.map(r => r.Agent).filter(Boolean)))), [rows])
  const types = useMemo(() => ['All'].concat(Array.from(new Set(rows.map(r => r.FeedbackType).filter(Boolean)))), [rows])

  const filtered = useMemo(() => rows.filter(r => (agent==='All' || r.Agent===agent) && (type==='All' || r.FeedbackType===type)), [rows, agent, type])

  const onDownload = () => {
    const csv = toCSV(filtered)
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const stamp = new Date().toISOString().slice(0,10)
    a.download = `feedback_${agent}_${type}_${stamp}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <SharedHeader title="Admin" subtitle="Feedback report and filters" />
      <div className="container">
        <div className="card">
          <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12}}>
            <div style={{fontWeight:700}}>Feedback Dashboard</div>
            <div style={{display:'flex', gap:8}}>
              <button type="button" className="button" onClick={fetchRows} disabled={loading}>Refresh</button>
            </div>
          </div>
          <div className="row" style={{marginBottom:12}}>
            <div className="col">
              <label>Agent</label>
              <select className="select" value={agent} onChange={e=>setAgent(e.target.value)}>{agents.map(a=> <option key={a} value={a}>{a}</option>)}</select>
            </div>
            <div className="col">
              <label>Feedback Type</label>
              <select className="select" value={type} onChange={e=>setType(e.target.value)}>{types.map(t=> <option key={t} value={t}>{t}</option>)}</select>
            </div>
          </div>
          {error && <div style={{marginBottom:8, color:'#b91c1c'}}>{error}</div>}
          <div style={{marginBottom:8}}>
            {loading ? 'Loading…' : `Showing ${filtered.length} of ${rows.length}`}
          </div>
          {(!loading && !filtered.length) ? (
            <div style={{opacity:0.7}}>No feedback yet. Submit from any agent page, then click Refresh.</div>
          ) : (
            <div style={{overflowX:'auto'}}>
              <table style={{width:'100%', borderCollapse:'collapse'}}>
                <thead>
                  <tr>
                    {['Timestamp','Employee_id','Feedback','FeedbackType','OffDefinitions','Suggestions','Account','Industry','ProblemStatement','Agent','Section'].map(h => (
                      <th key={h} style={{textAlign:'left', borderBottom:'1px solid #e2e8f0', padding:'6px 8px'}}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((r,i)=> (
                    <tr key={i}>
                      {['Timestamp','Employee_id','Feedback','FeedbackType','OffDefinitions','Suggestions','Account','Industry','ProblemStatement','Agent','Section'].map(h => (
                        <td key={h} style={{borderBottom:'1px solid #f1f5f9', padding:'6px 8px', fontSize:13}}>{r[h]}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div style={{marginTop:12}}>
            <button className="button primary" onClick={onDownload} disabled={!filtered.length}>Download CSV</button>
          </div>
        </div>
      </div>
    </>
  )
}
