"use client";

import type { ReactNode } from "react";
import {
  BookOpen,
  CalendarDays,
  Gauge,
  Layers,
  LayoutGrid,
  Phone,
  Target,
} from "lucide-react";

// Same shape/classes as LRN's workspaceNav (src/components/lrn-app.tsx) — the
// original items are inert (this clone has no routing), Mock Interview is live.
const workspaceNav = [
  { label: "Dashboard", href: "#", icon: LayoutGrid },
  { label: "Diagnostic", href: "#", icon: Gauge },
  { label: "Practice", href: "#", icon: Target },
  { label: "Flashcards", href: "#", icon: Layers },
  { label: "Glossary", href: "#", icon: BookOpen },
  { label: "Study plan", href: "#", icon: CalendarDays },
];

const interviewNav = { label: "Mock Interview", href: "#", icon: Phone, active: true };

/** Static clone of LRN's authenticated workspace shell — sidebar chrome only, no auth/routing. */
export function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="app-shell">
      <header className="sidebar">
        <div className="sidebar-brand-row">
          <span className="brand" aria-label="LRN">
            <img className="brand-image" src="/brand/lrn-centered-logo.png" alt="LRN" />
            <span className="brand-wordmark">LRN</span>
            <span className="brand-text">
              <span className="brand-sub">Interview readiness</span>
            </span>
          </span>
        </div>
        <nav aria-label="Main" className="sidebar-nav">
          <p className="nav-group">Workspace</p>
          {workspaceNav.map(({ label, href, icon: Icon }) => (
            <a key={label} href={href} className="nav-item">
              <Icon size={17} aria-hidden="true" />
              <span className="nav-item-label">{label}</span>
            </a>
          ))}
          <p className="nav-group">Practice</p>
          <a href={interviewNav.href} className="nav-item" aria-current="page">
            <interviewNav.icon size={17} aria-hidden="true" />
            <span className="nav-item-label">{interviewNav.label}</span>
          </a>
        </nav>
        <div className="sidebar-foot">
          <div className="plan-status">
            <span className="small muted">Mode</span>
            <span className="chip is-accent">Practice</span>
          </div>
        </div>
      </header>
      <div className="app-main">{children}</div>
    </div>
  );
}
