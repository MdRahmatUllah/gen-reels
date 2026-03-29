import re

with open('src/components/ui.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Loading shell
content = content.replace(
'''      <div className="workspace-shell">
        <aside className="nav-rail nav-rail--loading" />
        <main className="workspace-stage">
          <div className="topbar shimmer" style={{ height: "3.5rem" }} />
          <div className="page-shell">
            <div className="surface-card surface-card--loading shimmer" />
          </div>
        </main>
      </div>''',
'''      <div className="flex h-screen w-full bg-slate-950 text-slate-100 antialiased overflow-hidden">
        <aside className="w-64 flex-shrink-0 border-r border-slate-800/50 bg-slate-900/50 animate-pulse" />
        <main className="flex-1 flex flex-col min-w-0">
          <div className="h-14 w-full bg-slate-900/50 animate-pulse" />
          <div className="p-8">
            <div className="h-64 rounded-xl border border-slate-800 bg-slate-900/40 animate-pulse" />
          </div>
        </main>
      </div>'''
)

# ShellLayout wrapper
content = content.replace(
    '<div className="workspace-shell">',
    '<div className="flex h-screen w-full bg-slate-950 text-slate-100 antialiased overflow-hidden">'
).replace(
    '<aside className="nav-rail">',
    '<aside className="w-64 flex-shrink-0 flex flex-col gap-6 overflow-y-auto border-r border-slate-800/50 bg-slate-900/50 p-4 backdrop-blur-md">'
)

# Brand Lockup
content = content.replace(
'''        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true" />
          <div>
            <p className="eyebrow">Production Atelier</p>
            <h1>Reels Generation Studio</h1>
          </div>
        </div>''',
'''        <div className="flex items-center gap-3 px-2">
          <div className="h-6 w-6 rounded bg-gradient-to-br from-accent-cyan to-accent-violet flex-shrink-0 shadow-[0_0_10px_rgba(34,211,238,0.4)]" aria-hidden="true" />
          <div>
            <p className="text-[9px] font-bold uppercase tracking-widest text-slate-400 mb-0.5">Production Atelier</p>
            <h1 className="text-xs font-semibold tracking-wide text-slate-200">Reels Generation Studio</h1>
          </div>
        </div>'''
)

# Workspace Switcher
content = content.replace(
'''        <div className="workspace-switcher">
          <label className="field-label" htmlFor="workspace-select">
            Workspace
          </label>
          <select
            id="workspace-select"
            className="field-input"''',
'''        <div className="flex flex-col gap-2 rounded-lg border border-slate-800 bg-slate-800/20 p-3">
          <label className="text-[10px] font-medium text-slate-400 mb-0.5" htmlFor="workspace-select">
            Workspace
          </label>
          <select
            id="workspace-select"
            className="w-full bg-slate-900 border border-slate-700/50 rounded flex-1 py-1.5 px-2 text-xs text-slate-200 outline-none focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan transition-all"'''
)

content = content.replace(
'''          <div className="rail-metric-row">
            <div>
              <span>Credits</span>
              <strong>
                {activeWorkspace.creditsRemaining} / {activeWorkspace.creditsTotal}
              </strong>
            </div>
            <div>
              <span>Queue</span>
              <strong>{activeWorkspace.queueCount} active</strong>
            </div>
          </div>''',
'''          <div className="flex items-center justify-between mt-2 pt-2 border-t border-slate-800/50 text-[10px] text-slate-400">
            <div className="flex flex-col">
              <span>Credits</span>
              <strong className="text-slate-200 text-xs">
                {activeWorkspace.creditsRemaining} / {activeWorkspace.creditsTotal}
              </strong>
            </div>
            <div className="flex flex-col text-right">
              <span>Queue</span>
              <strong className="text-slate-200 text-xs">{activeWorkspace.queueCount} active</strong>
            </div>
          </div>'''
)

# Surface Panel Rail
content = content.replace(
    'className="surface-panel--rail"',
    'className="flex flex-col gap-2 rounded-lg border border-slate-800/50 bg-slate-800/10 p-3"'
).replace(
    'className="rail-project-card"',
    'className="flex flex-col gap-1.5 rounded-md border border-slate-700/50 bg-slate-900 p-3"'
)

# Workspace Stage & Topbar
content = content.replace(
    '<main className="workspace-stage">',
    '<main className="flex-1 flex flex-col min-w-0 overflow-y-auto relative">'
).replace(
    '<header className="topbar">',
    '<header className="flex h-14 items-center justify-between border-b border-slate-800/50 bg-slate-950/80 px-6 backdrop-blur-md sticky top-0 z-10">'
)

content = content.replace(
    '<div className="topbar-title">',
    '<div className="flex flex-col">'
).replace(
    '<div className="topbar-actions">',
    '<div className="flex items-center gap-4">'
).replace(
    'className="search-input"',
    'className="w-64 rounded-full bg-slate-900 border border-slate-700/50 px-4 py-1.5 text-xs text-slate-200 placeholder-slate-500 outline-none focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan transition-all"'
).replace(
    '<div className="topbar-chip">',
    '<div className="flex items-center gap-2 rounded-full border border-slate-800 bg-slate-900/50 px-3 py-1 text-xs text-slate-300">'
).replace(
    '<div className="avatar-chip">',
    '<div className="flex items-center gap-2 pl-2 border-l border-slate-800">'
)

content = content.replace(
'''              <span aria-hidden="true">{data.user.avatarInitials}</span>
              <div>
                <strong>{data.user.name}</strong>
                <p>{data.user.role}</p>
              </div>''',
'''              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-accent-violet/20 text-xs font-bold text-accent-violet ring-1 ring-accent-violet/50" aria-hidden="true">{data.user.avatarInitials}</span>
              <div className="flex flex-col">
                <strong className="text-xs text-slate-200">{data.user.name}</strong>
                <p className="text-[10px] text-slate-400">{data.user.role}</p>
              </div>'''
)

# NavGroup
content = content.replace(
'''    <div className="nav-group">
      <p className="section-heading">{label}</p>
      <div className={compact ? "nav-group-list nav-group-list--compact" : "nav-group-list"}>
        {items.map((item) => (
          <NavLink
            key={item.to}
            className={({ isActive }) =>
              isActive ? "nav-link nav-link--active" : "nav-link"
            }
            to={item.to}
            end={item.to === "/app"}
          >
            <span className="nav-link__label">
              {navIconMap[item.label] && (
                <Icon path={navIconMap[item.label]} size={15} />
              )}
              {item.label}
            </span>
          </NavLink>
        ))}
      </div>
    </div>''',
'''    <div className="flex flex-col gap-1">
      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-2 mb-1">{label}</p>
      <div className={compact ? "flex flex-col gap-0.5" : "flex flex-col gap-1"}>
        {items.map((item) => (
          <NavLink
            key={item.to}
            className={({ isActive }) =>
              isActive 
                ? "flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-medium text-accent-cyan bg-accent-cyan/10 transition-colors" 
                : "flex items-center gap-2 rounded-md px-3 py-1.5 text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-colors"
            }
            to={item.to}
            end={item.to === "/app"}
          >
            <span className="flex items-center gap-2">
              {navIconMap[item.label] && (
                <span className="opacity-70"><Icon path={navIconMap[item.label]} size={14} /></span>
              )}
              {item.label}
            </span>
          </NavLink>
        ))}
      </div>
    </div>'''
)

# PageFrame
content = content.replace(
'''    <section className="page-shell">
      <div className="page-header">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h1 className="page-title">{title}</h1>
          <p className="page-description">{description}</p>
        </div>
        {actions ? <div className="page-actions">{actions}</div> : null}
      </div>

      <div className="page-grid">
        <div className="page-content">{children}</div>
        <aside className="inspector-panel">{inspector}</aside>
      </div>
    </section>''',
'''    <section className="p-8 max-w-[1400px] mx-auto w-full animate-fade-in-up">
      <div className="flex items-start justify-between mb-8">
        <div className="flex flex-col gap-1">
          <p className="text-xs font-bold uppercase tracking-widest text-accent-violet">{eyebrow}</p>
          <h1 className="text-2xl font-semibold tracking-tight text-white">{title}</h1>
          <p className="text-sm text-slate-400 max-w-2xl">{description}</p>
        </div>
        {actions ? <div className="flex items-center gap-3">{actions}</div> : null}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-8 items-start">
        <div className="flex flex-col gap-6">{children}</div>
        <aside className="sticky top-20 flex flex-col gap-4">{inspector}</aside>
      </div>
    </section>'''
)

# SectionCard
content = content.replace(
'''    <section className={className ? `surface-card ${className}` : "surface-card"}>
      <div className="section-header">
        <div>
          <h3>{title}</h3>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
      </div>
      {children}
    </section>''',
'''    <section className={className ? `rounded-xl border border-slate-800/60 bg-slate-900/40 shadow-lg backdrop-blur flex flex-col overflow-hidden ${className}` : "rounded-xl border border-slate-800/60 bg-slate-900/40 shadow-lg backdrop-blur flex flex-col overflow-hidden"}>
      <div className="flex flex-col px-5 py-4 border-b border-slate-800/50 bg-slate-800/20">
        <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
        {subtitle ? <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p> : null}
      </div>
      <div className="p-5 flex flex-col gap-4">
        {children}
      </div>
    </section>'''
)

with open('src/components/ui.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
