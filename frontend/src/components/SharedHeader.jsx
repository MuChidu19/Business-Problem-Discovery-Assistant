import { useEffect, useState } from 'react'

const LOGO_URL = "https://yt3.googleusercontent.com/ytc/AIdro_k-7HkbByPWjKpVPO3LCF8XYlKuQuwROO0vf3zo1cqgoaE=s900-c-k-c0x00ffffff-no-rj"

export default function SharedHeader({ title, subtitle, enableAdmin = true }) {
  const [theme, setTheme] = useState(localStorage.getItem('appTheme') || 'light')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('appTheme', theme)
  }, [theme])

  const adminHref = enableAdmin ? '/home?adminPanelToggled=true' : '#'

  return (
    <div className="fixed-header">
      <a className="header-logo" href={adminHref} title="Open Admin View">
        <img src={LOGO_URL} alt="Logo" width={48} height={48} style={{borderRadius: '50%', border: '2px solid rgba(255,255,255,0.5)'}} />
      </a>
      <div className="header-title">
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="theme-toggle-capsule">
        <button className={`theme-toggle-btn ${theme === 'light' ? 'active' : ''}`} onClick={() => setTheme('light')}>Light</button>
        <button className={`theme-toggle-btn ${theme === 'dark' ? 'active' : ''}`} onClick={() => setTheme('dark')}>Dark</button>
      </div>
    </div>
  )
}
