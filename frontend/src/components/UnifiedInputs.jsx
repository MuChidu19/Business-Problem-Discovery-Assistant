import { useEffect, useMemo, useState } from 'react'
import { getConstants } from '../api/client'

export default function UnifiedInputs({ value, onChange, saveLabel = 'Save Problem Details' }) {
  const [constants, setConstants] = useState({ accounts: [], industries: [], map: {} })
  const [saved, setSaved] = useState(value)

  const isAutoMapped = useMemo(() => {
    return value.account && value.account !== 'Select Account' && constants.map[value.account]
  }, [value.account, constants.map])

  useEffect(() => {
    (async () => {
      const data = await getConstants()
      setConstants(data)
    })()
  }, [])

  // Auto-map industry when account changes
  useEffect(() => {
    if (constants.map[value.account]) {
      onChange({ ...value, industry: constants.map[value.account] })
    }
  }, [value.account])

  const hasUnsaved = (
    value.account !== saved.account ||
    value.industry !== saved.industry ||
    (value.problem || '').trim() !== (saved.problem || '').trim()
  )

  return (
    <div className="card">
      <div className="section-title-box"><strong>Account &amp; Industry</strong></div>
      <div className="row">
        <div className="col">
          <label>Account</label>
          <select className="select" value={value.account} onChange={e => onChange({ ...value, account: e.target.value })}>
            {constants.accounts.map(acc => <option key={acc} value={acc}>{acc}</option>)}
          </select>
        </div>
        <div className="col">
          <label>Industry</label>
          <select className="select" value={value.industry} onChange={e => onChange({ ...value, industry: e.target.value })} disabled={!!isAutoMapped}>
            {constants.industries.map(ind => <option key={ind} value={ind}>{ind}</option>)}
          </select>
        </div>
      </div>

      <div className="section-title-box" style={{ marginTop: 16 }}><strong>Business Problem Description</strong></div>
      <textarea className="textarea" rows={6} placeholder="Describe your business problem in detail..." value={value.problem} onChange={e => onChange({ ...value, problem: e.target.value })} />

      {hasUnsaved && (
        <button className="button primary" onClick={() => setSaved(value)}>{saveLabel}</button>
      )}
    </div>
  )
}

