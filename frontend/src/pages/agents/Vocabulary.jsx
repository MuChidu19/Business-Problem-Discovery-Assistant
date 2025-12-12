import { useEffect, useState } from 'react'
import SharedHeader from '../../components/SharedHeader'
import SectionTitle from '../../components/SectionTitle'
 
import ReportActions from '../../components/ReportActions'
 

export default function Vocabulary() {
  const [form, setForm] = useState(() => ({
    account: localStorage.getItem('account') || 'Select Account',
    industry: localStorage.getItem('industry') || 'Select Industry',
    industry_subcategory: localStorage.getItem('industry_subcategory') || '',
    problem: localStorage.getItem('problem') || ''
  }))
  const [html, setHtml] = useState('')

  useEffect(() => { localStorage.setItem('account', form.account) }, [form.account])
  useEffect(() => { localStorage.setItem('industry', form.industry) }, [form.industry])
  useEffect(() => { localStorage.setItem('industry_subcategory', form.industry_subcategory || '') }, [form.industry_subcategory])
  useEffect(() => { localStorage.setItem('problem', form.problem) }, [form.problem])

  useEffect(() => {
    setHtml(localStorage.getItem('vocabulary_html') || '')
  }, [])

  return (
    <>
      <SharedHeader title="Vocabulary Agent" subtitle="Extracts and displays business vocabulary from your problem statement" />
      <div className="container">
        {!html && (
          <div className="card" style={{marginTop:12}}>
            Analysis not ready yet. Please go back to Home and click Save Problem Details.
          </div>
        )}
        {html && <SectionTitle title="Vocabulary Analysis" />}
        {html && (
          <div style={{margin:'8px 0 0', textAlign:'center', opacity:0.8}}>
            AI-generated from <strong>{form.account || 'Unknown Company'}</strong> ({form.industry || 'Unknown Industry'}).<br />
            Something off? Use the feedback section below.
          </div>
        )}
        <div style={{marginTop: 16}} className="card fade-up">
          <div dangerouslySetInnerHTML={{ __html: html }} />
        </div>
        <ReportActions agentDisplayName="Vocabulary Agent" account={form.account} htmlContent={html} />
        <div style={{marginTop:16}}>
          <button className="button" onClick={()=>window.history.back()}>Back to Home</button>
        </div>
      </div>
    </>
  )
}


