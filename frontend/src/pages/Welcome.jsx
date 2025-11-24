import { useEffect, useState } from 'react'
import SharedHeader from '../components/SharedHeader'
import { useNavigate } from 'react-router-dom'

export default function Welcome() {
  const navigate = useNavigate()
  const [employeeId, setEmployeeId] = useState(localStorage.getItem('employee_id') || '')

  useEffect(() => { localStorage.setItem('employee_id', employeeId) }, [employeeId])
  const canProceed = (employeeId || '').trim().length > 0

  return (
    <>
      <SharedHeader title="Welcome" subtitle="Business Problem Discovery Assistant" />
      <div className="container">
        <div className="card" style={{marginBottom: 16, padding:'2rem'}}>
          <h2 style={{marginTop:0}}>Welcome</h2>
          <p style={{opacity:0.85}}>Please enter your Employee ID to continue.</p>
          <label>Employee ID</label>
          <input className="input" value={employeeId} onChange={e => setEmployeeId(e.target.value)} placeholder="Enter your Employee ID" />
          <div style={{marginTop:16}}>
            <button className="button primary" disabled={!canProceed} onClick={()=>navigate('/home')}>Continue</button>
          </div>
        </div>
      </div>
    </>
  )
}
