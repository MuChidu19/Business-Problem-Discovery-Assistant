import { useEffect, useState } from 'react'
import SharedHeader from '../../components/SharedHeader'
import UnifiedInputs from '../../components/UnifiedInputs'
import SectionTitle from '../../components/SectionTitle'
import { analyze } from '../../api/client'
import ReportActions from '../../components/ReportActions'

export default function Uncertainty() {
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

  const canAnalyze = form.account && form.account !== 'Select Account' && form.industry && form.industry !== 'Select Industry' && form.problem.trim()

  const onAnalyze = async () => {
    setLoading(true)
    try {
      const payload = {
        employee_id: localStorage.getItem('employee_id') || '',
        account: form.account,
        industry: form.industry,
        problem: form.problem,
        context: {
          vocabulary: localStorage.getItem('vocabulary_html') || '',
          current_system: localStorage.getItem('current_system_html') || ''
        },
        multiround_convo: 2
      }
      const res = await analyze('uncertainty', payload)
      setHtml(res.output_text)
    } catch (e) {
      setHtml(`<div class='card'>Error: ${e?.message || e}</div>`) 
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <SharedHeader title="Uncertainty Agent" subtitle="Quantify risks and unknowns" />
      <div className="container">
        <UnifiedInputs value={form} onChange={setForm} />
        <div style={{marginTop: 12}}>
          <button className="button primary" disabled={!canAnalyze || loading} onClick={onAnalyze}>
            {loading ? 'Analyzing…' : 'Analyze Uncertainty'}
          </button>
        </div>
        {html && <SectionTitle title="Uncertainty Analysis" />}
        {html && (
          <div style={{margin:'8px 0 0', textAlign:'center', opacity:0.8}}>
            AI-generated from <strong>{form.account || 'Unknown Company'}</strong> ({form.industry || 'Unknown Industry'}).
          </div>
        )}
        <div style={{marginTop: 16}} className="card fade-up">
          <div dangerouslySetInnerHTML={{ __html: html }} />
        </div>
        <ReportActions agentDisplayName="Uncertainty Agent" account={form.account} htmlContent={html} />
        <div style={{marginTop:16}}>
          <button className="button" onClick={()=>window.history.back()}>Back to Home</button>
        </div>
      </div>
    </>
  )
}
