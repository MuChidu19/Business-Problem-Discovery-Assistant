import { useEffect, useState } from 'react'
import SharedHeader from '../components/SharedHeader'
import UnifiedInputs from '../components/UnifiedInputs'
import SectionTitle from '../components/SectionTitle'
import { useNavigate, useLocation } from 'react-router-dom'

export default function Home() {
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState(() => ({
    account: localStorage.getItem('account') || 'Select Account',
    industry: localStorage.getItem('industry') || 'Select Industry',
    problem: localStorage.getItem('problem') || ''
  }))
  const [running, setRunning] = useState(false)
  const [status, setStatus] = useState('')

  useEffect(() => { localStorage.setItem('account', form.account) }, [form.account])
  useEffect(() => { localStorage.setItem('industry', form.industry) }, [form.industry])
  useEffect(() => { localStorage.setItem('problem', form.problem) }, [form.problem])

  // If adminPanelToggled=true in query, redirect to /admin and clean param
  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const v = (params.get('adminPanelToggled') || '').toLowerCase()
    if (['1','t','true','show','yes'].includes(v)) {
      // clean URL
      try {
        const url = new URL(window.location.href)
        url.searchParams.delete('adminPanelToggled')
        window.history.replaceState(null, '', url.pathname + url.search + url.hash)
      } catch {}
      navigate('/admin', { replace: true })
    }
  }, [location.search, navigate])

  const ready = form.account && form.account !== 'Select Account' && form.industry && form.industry !== 'Select Industry' && form.problem.trim()

  const analyzeAll = async (ctx) => {
    if (!ready) return
    setRunning(true)
    setStatus('Preparing...')
    try {
      const api = await import('../api/client')
      const common = {
        employee_id: localStorage.getItem('employee_id') || '',
        account: ctx.account,
        industry: ctx.industry,
        industry_subcategory: ctx.industry_subcategory || '',
        problem: ctx.problem,
      }
      // Stage 1: run Vocabulary and Current System in parallel
      setStatus('Running Vocabulary and Current System...')
      const [vocabRes, csRes] = await Promise.all([
        api.analyze('vocabulary', { ...common, context: {}, multiround_convo: 3 }),
        api.analyze('current-system', { ...common, context: {}, multiround_convo: 2 }),
      ])
      const vocabHTML = vocabRes?.output_text || ''
      const csHTML = csRes?.output_text || ''
      try {
        localStorage.setItem('vocabulary_html', vocabHTML)
        localStorage.setItem('current_system_html', csHTML)
      } catch {}

      // Stage 2: run VUCA in parallel with context
      setStatus('Running VUCA analyses...')
      const vucaPayload = { ...common, multiround_convo: 2, context: { vocabulary: vocabHTML, current_system: csHTML } }
      const [volRes, ambRes, intRes, uncRes] = await Promise.all([
        api.analyze('volatility', vucaPayload),
        api.analyze('ambiguity', vucaPayload),
        api.analyze('interconnectedness', vucaPayload),
        api.analyze('uncertainty', vucaPayload),
      ])
      try {
        localStorage.setItem('volatility_html', volRes?.output_text || '')
        localStorage.setItem('ambiguity_html', ambRes?.output_text || '')
        localStorage.setItem('interconnectedness_html', intRes?.output_text || '')
        localStorage.setItem('uncertainty_html', uncRes?.output_text || '')
      } catch {}

      // Stage 3: research/stakeholders/discovery/complexity in parallel
      setStatus('Running research and discovery analyses...')
      const researchPayload = { ...common, multiround_convo: 3, context: {} }
      const [indRes, compRes, stdRes, stkRes, qdRes, pcRes] = await Promise.all([
        api.analyze('industry-research', researchPayload),
        api.analyze('company-research', researchPayload),
        api.analyze('standard-practices', researchPayload),
        api.analyze('identify-stakeholders', { ...common, multiround_convo: 5, context: {} }),
        api.analyze('question-discovery', researchPayload),
        api.analyze('problem-complexity', researchPayload),
      ])
      try {
        localStorage.setItem('industry_research_html', indRes?.output_text || '')
        localStorage.setItem('company_research_html', compRes?.output_text || '')
        localStorage.setItem('standard_practices_html', stdRes?.output_text || '')
        localStorage.setItem('identify_stakeholders_html', stkRes?.output_text || '')
        localStorage.setItem('question_discovery_html', qdRes?.output_text || '')
        localStorage.setItem('problem_complexity_html', pcRes?.output_text || '')
      } catch {}

      setStatus('All analyses complete!')
    } catch (e) {
      console.error('Analyze all failed', e)
      setStatus(`Error: ${e?.message || e}`)
    } finally {
      setRunning(false)
    }
  }

  return (
    <>
      <SharedHeader title="Business Problem Discovery Assistant" subtitle="Select account, industry, and describe your problem. Then choose an agent." />
      <div className="container">
        <SectionTitle title="Get Started" />
        <div style={{margin:'8px 0 12px', textAlign:'center', opacity:0.85}}>
          Provide your context once here; all agents reuse it. You can refine inputs anytime.
        </div>
        <UnifiedInputs value={form} onChange={setForm} onSave={analyzeAll} />
        {running && (
          <div className="card" style={{marginTop:12}}>
            <strong>Running analyses:</strong> {status}
          </div>
        )}

        <SectionTitle title="Agents" />
        <div className="row" style={{flexWrap:'wrap'}}>
          <div className="col"><button className="button primary" disabled={!ready} onClick={()=>navigate('/agents/vocabulary')}>Vocabulary</button></div>
          <div className="col"><button className="button primary" disabled={!ready} onClick={()=>navigate('/agents/current-system')}>Current System</button></div>
          <div className="col"><button className="button primary" disabled={!ready} onClick={()=>navigate('/agents/volatility')}>Volatility</button></div>
        </div>
        <div className="row" style={{flexWrap:'wrap', marginTop:12}}>
          <div className="col"><button className="button primary" disabled={!ready} onClick={()=>navigate('/agents/ambiguity')}>Ambiguity</button></div>
          <div className="col"><button className="button primary" disabled={!ready} onClick={()=>navigate('/agents/interconnectedness')}>Interconnectedness</button></div>
          <div className="col"><button className="button primary" disabled={!ready} onClick={()=>navigate('/agents/uncertainty')}>Uncertainty</button></div>
        </div>
        <div className="row" style={{flexWrap:'wrap', marginTop:12}}>
          <div className="col"><button className="button primary" disabled={!ready} onClick={()=>navigate('/agents/industry-research')}>Industry Research</button></div>
          <div className="col"><button className="button primary" disabled={!ready} onClick={()=>navigate('/agents/company-research')}>Company Research</button></div>
          <div className="col"><button className="button primary" disabled={!ready} onClick={()=>navigate('/agents/standard-practices')}>Standard Practices</button></div>
        </div>
        <div className="row" style={{flexWrap:'wrap', marginTop:12}}>
          <div className="col"><button className="button primary" disabled={!ready} onClick={()=>navigate('/agents/identify-stakeholders')}>Identify Stakeholders</button></div>
          <div className="col"><button className="button primary" disabled={!ready} onClick={()=>navigate('/agents/question-discovery')}>Question Discovery</button></div>
          <div className="col"><button className="button primary" disabled={!ready} onClick={()=>navigate('/agents/problem-complexity')}>Problem Complexity</button></div>
        </div>

        <div style={{marginTop:24}}>
          <button className="button primary" onClick={()=>navigate('/admin')}>Open Admin</button>
        </div>
      </div>
    </>
  )
}
