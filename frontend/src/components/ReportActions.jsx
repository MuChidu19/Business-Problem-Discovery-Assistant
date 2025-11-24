import FeedbackPanel from './FeedbackPanel'
import DownloadReport from './DownloadReport'

export default function ReportActions({ agentDisplayName, account, htmlContent }) {
  if (!htmlContent) return null
  const safeAccount = (account || 'Unknown').replaceAll(' ', '_')
  const filename = `${agentDisplayName.toLowerCase().replaceAll(' ','_')}_${safeAccount}.html`

  return (
    <div style={{marginTop:16}}>
      <div className="section-title-box" style={{padding:'0.5rem 1rem'}}>
        <div style={{display:'flex', alignItems:'center', justifyContent:'center'}}>
          <h3 style={{margin:0, color:'white', fontWeight:700, fontSize:'1.1rem'}}>Download {agentDisplayName} Report</h3>
        </div>
      </div>
      <DownloadReport filename={filename} content={htmlContent} />

      <div className="section-title-box" style={{padding:'0.5rem 1rem', marginTop:12}}>
        <div style={{display:'flex', alignItems:'center', justifyContent:'center'}}>
          <h3 style={{margin:0, color:'white', fontWeight:700, fontSize:'1.1rem'}}>Feedback</h3>
        </div>
      </div>
      <FeedbackPanel agentName={`${agentDisplayName}`} onSubmitted={() => {}} />
    </div>
  )
}
