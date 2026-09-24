export default function PageHeader({ icon, eyebrow, title, subtitle, action }) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <p className="page-eyebrow">{eyebrow}</p>}
        <h1 className="page-title">
          <span className="page-title-icon">{icon}</span>
          {title}
        </h1>
        <p className="muted">{subtitle}</p>
      </div>
      {action || <div />}
    </header>
  );
}
