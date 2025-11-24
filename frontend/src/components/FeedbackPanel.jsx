import { useMemo, useState } from 'react'
import { postFeedback } from '../api/client'

const OPTIONS = [
  {
    key: 'Positive',
    label: 'I have read it, found it useful, thanks.'
  },
  {
    key: 'Inaccurate',
    label: 'I have read it, found some facts or sections to be inaccurate.'
  },
  {
    key: 'Suggestion',
    label: 'I have suggestions for improving the research output or format.'
  }
]

export default function FeedbackPanel({ agentName, sectionLabel = 'Section', sectionValue = '', onSubmitted }) {
  const [feedbackType, setFeedbackType] = useState('')
  const [offDefs, setOffDefs] = useState('')
  const [suggestions, setSuggestions] = useState('')
  const [additional, setAdditional] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [status, setStatus] = useState({ ok: false, msg: '' })

  const employeeId = localStorage.getItem('employee_id') || ''
  const account = localStorage.getItem('account') || ''
  const industry = localStorage.getItem('industry') || ''
  const problem = localStorage.getItem('problem') || ''

  const canSubmit = useMemo(() => {
    if (!feedbackType) return false
    if (feedbackType === 'Inaccurate') return offDefs.trim().length > 0 || additional.trim().length > 0
    if (feedbackType === 'Suggestion') return suggestions.trim().length > 0
    return true
  }, [feedbackType, offDefs, suggestions, additional])

  const onSubmit = async () => {
    setSubmitting(true)
    setStatus({ ok: false, msg: '' })
    try {
      await postFeedback({
        Employee_id: employeeId,
        Feedback: additional,
        FeedbackType: feedbackType,
        OffDefinitions: offDefs,
        Suggestions: suggestions,
        Account: account,
        Industry: industry,
        ProblemStatement: problem,
        Agent: agentName,
        Section: sectionValue,
      })
      setFeedbackType('')
      setOffDefs('')
      setSuggestions('')
      setAdditional('')
      setStatus({ ok: true, msg: 'Thank you! Your feedback has been recorded.' })
      onSubmitted && onSubmitted()
    } catch (e) {
      console.error('Feedback submit failed', e)
      setStatus({ ok: false, msg: `Failed to submit feedback: ${e?.message || e}` })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="card" style={{marginTop: 16}}>
      <div className="section-title-box"><strong>Feedback</strong></div>
      <div style={{display:'flex', gap:12, flexDirection:'column'}}>
        {OPTIONS.map(o => (
          <label key={o.key} style={{display:'flex', alignItems:'center', gap:8}}>
            <input type="radio" name="fbtype" value={o.key} checked={feedbackType===o.key} onChange={() => setFeedbackType(o.key)} />
            <span>{o.label}</span>
          </label>
        ))}
      </div>

      {feedbackType === 'Inaccurate' && (
        <>
          <label style={{marginTop:10}}>Inaccurate excerpts (one per line)</label>
          <textarea className="textarea" rows={4} value={offDefs} onChange={e=>setOffDefs(e.target.value)} />
          <label>Additional comments</label>
          <input className="input" value={additional} onChange={e=>setAdditional(e.target.value)} />
        </>
      )}

      {feedbackType === 'Suggestion' && (
        <>
          <label style={{marginTop:10}}>Your suggestions</label>
          <textarea className="textarea" rows={4} value={suggestions} onChange={e=>setSuggestions(e.target.value)} />
        </>
      )}

      {feedbackType === 'Positive' && (
        <>
          <label style={{marginTop:10}}>Optional comment</label>
          <input className="input" value={additional} onChange={e=>setAdditional(e.target.value)} />
        </>
      )}

      <div style={{marginTop:12}}>
        <button type="button" className="button primary" disabled={!canSubmit || submitting} onClick={onSubmit}>
          {submitting ? 'Submitting…' : 'Submit Feedback'}
        </button>
      </div>
      {status.msg && (
        <div style={{marginTop:8, fontSize:13, color: status.ok ? '#22c55e' : '#b91c1c'}}>{status.msg}</div>
      )}
      <div style={{marginTop:8, fontSize:12, opacity:0.7}}>Employee: {employeeId || 'N/A'} • Agent: {agentName}{sectionValue?` • ${sectionLabel}: ${sectionValue}`:''}</div>
    </div>
  )
}
