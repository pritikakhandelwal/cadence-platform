import type { IssueType } from "@cadence/schema";

export interface IssueTypeInfo {
  label: string;
  color: string;
  caption: string;
  icon: React.ReactNode;
}

// One entry per real IssueType the backend can produce (plus "path",
// which the schema reserves but nothing generates yet -- see
// apps/worker/README.md's Scoring section). Colors match the design
// canvas's lavender/blue palette; each type gets its own hue so the
// timeline and legend stay readable at a glance.
export const ISSUE_TYPES: Record<IssueType, IssueTypeInfo> = {
  angle: {
    label: "Angle",
    color: "#7B64D9",
    caption: "A joint differs from the reference",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#7B64D9" strokeWidth="1.8">
        <path d="M12 3v7M12 10l6 9M12 10l-6 9" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  timing: {
    label: "Timing",
    color: "#5B48A6",
    caption: "Running ahead of or behind",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#5B48A6" strokeWidth="1.8">
        <circle cx="12" cy="12" r="8" />
        <path d="M12 8v4l3 2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  occlusion: {
    label: "Occlusion",
    color: "#7FB8E0",
    caption: "Too unclear to score",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#7FB8E0" strokeWidth="1.8">
        <path d="M3 12c2.5-4 6-6 9-6s6.5 2 9 6c-2.5 4-6 6-9 6s-6.5-2-9-6z" />
        <path d="M4 4l16 16" strokeLinecap="round" />
      </svg>
    ),
  },
  tempo: {
    label: "Tempo",
    color: "#6E5FC4",
    caption: "A move sped up or slowed down",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6E5FC4" strokeWidth="1.8">
        <path d="M13 3L4 14h6l-1 7 9-11h-6l1-7z" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  energy: {
    label: "Energy",
    color: "#A6A2B8",
    caption: "Less movement than expected",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#A6A2B8" strokeWidth="1.8">
        <path d="M12 21c4-3 7-6.5 7-10.5A7 7 0 005 10.5C5 14.5 8 18 12 21z" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  balance: {
    label: "Balance",
    color: "#4F6FA8",
    caption: "Off from your base of support",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4F6FA8" strokeWidth="1.8">
        <path d="M12 4v16M6 8l-3 4 3 4M18 8l3 4-3 4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  path: {
    label: "Path",
    color: "#9B8FD9",
    caption: "Spatial trajectory deviation",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#9B8FD9" strokeWidth="1.8">
        <path d="M4 18c4 0 4-12 8-12s4 12 8 12" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
};
