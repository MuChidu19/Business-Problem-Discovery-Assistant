import { useEffect, useState } from 'react'
import SharedHeader from '../../components/SharedHeader'
import UnifiedInputs from '../../components/UnifiedInputs'
import SectionTitle from '../../components/SectionTitle'
import { analyze } from '../../api/client'
import ReportActions from '../../components/ReportActions'

export default function ProblemComplexity() {
  const [form, setForm] = useState(() => ({
    account: localStorage.getItem('account') || 'Select Account',
    industry: localStorage.getItem('industry') || 'Select Industry',
    problem: localStorage.getItem('problem') || ''
  }))
  const [loading, setLoading] = useState(false)
  const [html, setHtml] = useState('')

  useEffect(() => { localStorage.setItem('account', form.account) }, [form.account])
  useEffect(() => { localStorage.setItem('industry', form.industry) }, [form.industry])
  useEffect(() => { localStorage.setItem('problem', form.problem) }, [form.problem])

  const canAnalyze = form.account && form.account !== 'Select Account' && form.problem.trim()

  const onAnalyze = async () => {
    setLoading(true)
    try {
      const payload = {
        employee_id: localStorage.getItem('employee_id') || '',
        account: form.account,
        industry: form.industry,
        problem: form.problem,
        context: {},
        multiround_convo: 3
      }
      const res = await analyze('problem-complexity', payload)
      setHtml(res.output_text)
    } catch (e) {
      setHtml(`<div class='card'>Error: ${e?.message || e}</div>`) 
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <SharedHeader title="Problem Complexity" subtitle="Reveal hidden interdependencies and reframe scope" />
      <div className="container">
        <UnifiedInputs value={form} onChange={setForm} />
        <div style={{marginTop: 12}}>
          <button className="button primary" disabled={!canAnalyze || loading} onClick={onAnalyze}>
            {loading ? 'Analyzing…' : 'Analyze Complexity'}
          </button>
        </div>
        {html && <SectionTitle title="Problem Complexity" />}
        {html && (
          <div style={{margin:'8px 0 0', textAlign:'center', opacity:0.8}}>
            Complexity analysis for <strong>{form.account || 'Unknown Company'}</strong>.
          </div>
        )}
        <div style={{marginTop: 16}} className="card fade-up">
          <div dangerouslySetInnerHTML={{ __html: html }} />
        </div>
        <ReportActions agentDisplayName="Problem Complexity Agent" account={form.account} htmlContent={html} />
        <div style={{marginTop:16}}>
          <button className="button" onClick={()=>window.history.back()}>Back to Home</button>
        </div>
      </div>
    </>
  )
}
