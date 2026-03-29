import os
import re

replacements = {
    # Typography
    r'className="eyebrow"': 'className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted"',
    r'className="page-title"': 'className="font-heading text-3xl md:text-4xl leading-tight font-bold text-primary tracking-tight"',
    r'className="page-description"': 'className="text-[0.95rem] leading-[1.7] text-secondary max-w-[66ch]"',
    r'className="section-heading"': 'className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted"',
    r'className="body-copy"': 'className="text-[0.95rem] leading-[1.7] text-secondary max-w-[66ch]"',

    # Shell
    r'className="workspace-shell"': 'className="flex h-screen w-full bg-base text-primary antialiased overflow-hidden"',
    r'className="nav-rail(\s+nav-rail--loading)?"': 'className="w-64 flex-shrink-0 flex flex-col gap-6 overflow-y-auto border-r border-border-subtle bg-surface/80 p-4 backdrop-blur-md no-scrollbar\\1"',
    r'className="workspace-stage"': 'className="flex-1 flex flex-col min-w-0 overflow-y-auto relative"',
    r'className="topbar(\s+shimmer)?"': 'className="flex h-14 items-center justify-between border-b border-border-subtle bg-surface/80 px-6 backdrop-blur-md sticky top-0 z-10\\1"',

    # General Layout
    r'className="page-shell"': 'className="flex flex-col gap-6 px-7 py-6 pb-12 w-full max-w-7xl mx-auto animate-fade-in-up"',
    r'className="page-header"': 'className="flex items-end justify-between gap-6"',
    r'className="page-grid"': 'className="grid grid-cols-1 lg:grid-cols-[1fr_19rem] gap-5 items-start"',
    r'className="page-content"': 'className="flex flex-col gap-5 min-w-0"',
    r'className="inspector-panel"': 'className="sticky top-20 flex flex-col gap-3 self-start w-full"',

    # Groupings
    r'className="page-actions"': 'className="flex flex-wrap items-center gap-2"',
    r'className="card-actions"': 'className="flex flex-wrap items-center gap-2"',
    r'className="filter-row"': 'className="flex flex-wrap items-center gap-2"',
    r'className="login-actions"': 'className="flex flex-wrap items-center gap-2"',
    r'className="tag-row"': 'className="flex flex-wrap items-center gap-2"',
    r'className="inline-meta"': 'className="flex flex-wrap items-center gap-2"',

    # Cards
    r'className="surface-card(\s+shimmer)?(\s+surface-card--loading)?"': 'className="flex flex-col gap-5 p-5 md:p-6 rounded-xl bg-card border border-border-card shadow-md transition-colors duration-200 hover:border-border-active backdrop-blur animate-rise-in\\1"',
    r'className="surface-card surface-card--hero"': 'className="flex flex-col gap-5 p-5 md:p-6 rounded-xl bg-card-hero border border-accent-glow shadow-md transition-colors duration-200 hover:border-border-active backdrop-blur animate-rise-in"',
    r'className="surface-panel"': 'className="p-4 rounded-xl bg-card border border-border-card animate-rise-in"',
    r'className="surface-panel--rail"': 'className="p-4 rounded-lg bg-glass border border-border-card"',

    # Context Bar
    r'className="context-bar"': 'className="grid grid-cols-1 lg:grid-cols-[1.2fr_0.8fr] gap-4 mx-7 mb-6 px-5 py-4 rounded-xl bg-glass border border-border-subtle"',
    r'className="context-bar__summary"': 'className="flex flex-col gap-3 text-sm"',
    r'className="context-bar__heading"': 'className="flex items-center gap-3 flex-wrap"',
    r'className="context-bar__meta"': 'className="flex flex-wrap gap-2 text-xs text-secondary"',
    r'className="context-bar__steps"': 'className="flex flex-wrap gap-2"',
    r'className="context-step"': 'className="inline-flex items-center justify-center min-h-[2rem] px-3 py-1.5 rounded-full bg-glass border border-border-subtle text-secondary text-[0.82rem] font-semibold transition-all duration-200 hover:border-border-active hover:text-primary"',
    r'className="context-step context-step--active"': 'className="inline-flex items-center justify-center min-h-[2rem] px-3 py-1.5 rounded-full bg-accent-gradient text-on-accent border-transparent text-[0.82rem] font-semibold transition-all duration-200"',

    # Inputs & Forms
    r'className="field-input"': 'className="w-full px-3.5 py-2.5 rounded-md border border-border-card bg-glass text-primary outline-none transition-all duration-200 focus:border-accent focus:shadow-[0_0_0_3px_var(--accent-glow-sm)]"',
    r'className="search-input"': 'className="min-w-[16rem] px-4 py-2.5 rounded-lg border border-border-subtle bg-glass text-primary outline-none transition-all duration-200 focus:border-accent focus:shadow-[0_0_0_3px_var(--accent-glow-sm)] placeholder:text-muted"',
    r'className="field-label"': 'className="text-[0.6875rem] leading-[1.4] tracking-widest uppercase font-bold text-muted block mb-1"',

    # Buttons
    r'className="button"': 'className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative"',
    r'className="button button--primary"': 'className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent shadow-sm hover:shadow-accent hover:-translate-y-px"',
    r'className="button button--secondary"': 'className="inline-flex items-center justify-center gap-2 min-h-[2.7rem] px-4 py-2 rounded-md font-semibold text-sm transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px"',
    r'className="chip-button"': 'className="inline-flex items-center justify-center gap-2 px-3.5 py-1.5 rounded-full font-semibold text-[0.825rem] capitalize transition-all duration-200 cursor-pointer overflow-hidden relative bg-glass hover:bg-glass-hover text-primary border border-border-subtle hover:border-border-active hover:-translate-y-px"',
    r'className="chip-button chip-button--active"': 'className="inline-flex items-center justify-center gap-2 px-3.5 py-1.5 rounded-full font-semibold text-[0.825rem] capitalize transition-all duration-200 cursor-pointer overflow-hidden relative bg-accent-gradient text-on-accent border-transparent shadow-sm hover:shadow-accent hover:-translate-y-px"',

    # Utilities & Structural
    r'className="alert-stack"': 'className="flex flex-col gap-3"',
    r'className="alert-item"': 'className="flex gap-3 items-start"',
    r'className="stack-gap"': 'className="flex flex-col gap-3"',
    r'className="brand-lockup"': 'className="flex items-center gap-3 pb-2"',
    r'className="rail-project-card"': 'className="flex flex-col gap-2 rounded-md border border-border-card bg-card p-3"',
    
    # Specific elements inside rail / nav
    r'className="timeline-item"': 'className="flex flex-col items-start gap-1 p-3 rounded-lg bg-card border border-border-subtle transition-all duration-200 cursor-pointer text-left hover:border-border-active"',
    r'className="timeline-item timeline-item--active"': 'className="flex flex-col items-start gap-1 p-3 rounded-lg bg-primary border-border-active transition-all duration-200 cursor-pointer text-left"',
    
    r'className="avatar-chip"': 'className="flex items-center gap-2 pl-2"',
    r'className="topbar-chip"': 'className="flex items-center gap-2 rounded-full border border-border-card bg-glass px-3 py-1 text-xs text-secondary"',
    
}

def migrate_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    for pattern, replacement in replacements.items():
        content = re.sub(pattern, replacement, content)

    if original != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Migrated classes in {filepath}")

for root, _, files in os.walk("src"):
    for file in files:
        if file.endswith((".tsx", ".ts")):
            filepath = os.path.join(root, file)
            migrate_file(filepath)
