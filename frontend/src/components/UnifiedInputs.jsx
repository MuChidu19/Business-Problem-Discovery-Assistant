import { useEffect, useMemo, useState } from 'react'
import { getConstants } from '../api/client'

export default function UnifiedInputs({ value, onChange, onSave, saveLabel = 'Save Problem Details' }) {
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

  // Ensure subcategory defaults to first option of selected industry
  const subcats = (constants.subcategories && constants.subcategories[value.industry]) || []
  useEffect(() => {
    if (value.industry && subcats.length) {
      if (!value.industry_subcategory || !subcats.includes(value.industry_subcategory)) {
        onChange({ ...value, industry_subcategory: subcats[0] })
      }
    }
  }, [value.industry, subcats.length])

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
          <div className="input" style={{display:'flex',alignItems:'center',height: 'auto'}}>
            {value.industry || 'Select Industry'}
          </div>
        </div>
        <div className="col">
          <label>Subcategory</label>
          <select className="select" value={value.industry_subcategory || ''} onChange={e => onChange({ ...value, industry_subcategory: e.target.value })}>
            {subcats.length ? subcats.map(sc => <option key={sc} value={sc}>{sc}</option>) : <option value="">Select Subcategory</option>}
          </select>
        </div>
      </div>

      <div className="section-title-box" style={{ marginTop: 16 }}><strong>Business Problem Description</strong></div>
      <textarea className="textarea" rows={6} placeholder="Describe your business problem in detail..." value={value.problem} onChange={e => onChange({ ...value, problem: e.target.value })} />

      <button className="button primary" onClick={() => { setSaved(value); onSave && onSave(value) }}>{saveLabel}</button>
    </div>
  )
}
