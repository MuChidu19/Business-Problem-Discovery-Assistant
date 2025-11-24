export default function SectionTitle({ title, color = '#8b1e1e' }) {
  return (
    <div className="section-title-box" style={{ background: `linear-gradient(135deg, ${color} 0%, #ff6b35 100%)` }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <h3 style={{ margin: 0, fontWeight: 800, fontSize: '1.3rem' }}>{title}</h3>
      </div>
    </div>
  )
}

