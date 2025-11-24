export default function DownloadReport({ filename = 'report.html', content = '' }) {
  const wrapHtml = (body) => `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Report</title>
    <style>
      body { font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; color: #1e293b; }
      .agent-display { line-height: 1.36; font-size: 16px; }
      h1,h2,h3,h4,h5 { margin: 0.5rem 0; }
      .section-title { background: linear-gradient(135deg, #8b1e1e 0%, #ff6b35 100%); color: #fff; padding: 10px 14px; border-radius: 10px; margin: 0 0 12px 0; font-weight: 800; }
    </style>
  </head>
  <body>
    ${body}
  </body>
</html>`

  const ensureHtml = (s) => {
    const looksHtml = /<\w+[^>]*>/.test(s)
    return looksHtml ? s : `<pre>${(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;')}</pre>`
  }

  const onDownload = () => {
    const htmlDoc = wrapHtml(ensureHtml(content || ''))
    const blob = new Blob([htmlDoc], { type: 'text/html;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }
  return (
    <div style={{marginTop:12}}>
      <button type="button" className="button primary" onClick={onDownload}>Download Report</button>
    </div>
  )
}
