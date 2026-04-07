# User Notifications

Users should receive real-time notifications when actions relevant to them occur in the application.

## Goals & Success Metrics

### Business Goals
- Increase user engagement by surfacing relevant activity
- Reduce time-to-awareness for collaborative actions
- Drive return visits through email notifications

### Success Metrics
| Metric | Definition | Target |
|--------|-----------|--------|
| Notification open rate | % of in-app notifications clicked | > 40% |
| Email click-through rate | % of email notifications that drive a return visit | > 15% |
| Time to awareness | Median time between event and user seeing notification | < 30 seconds (in-app) |

### Traffic & Load Expectations
| Dimension | Estimate | Basis |
|-----------|----------|-------|
| Expected RPS at launch | 50 | Current active user base of 5K, ~10 events/user/day |
| Expected RPS at steady state (30d) | 200 | Growth projection + increased feature usage |
| Expected peak RPS | 600 | 3x steady state during business hours |
| Polling frequency | Event-driven (WebSocket) | Real-time requirement < 30s |
| Payload size (typical) | 2KB | Notification object + metadata |
| Traffic pattern | Time-of-day, business hours heavy | B2B usage pattern |

## Out of Scope
- Push notifications (mobile) — planned for v2
- Notification preferences/settings UI — v2, using defaults for v1
- Digest/summary emails — v2
- Notification grouping/threading — v2

## User Personas

### Persona A: Active Collaborator
- As a team member, I want to see when someone comments on my work so that I can respond quickly.
- As a team member, I want to know when I'm assigned a task so that I can start working on it.

### Persona B: Project Owner
- As a project owner, I want to see when deliverables are completed so that I can review them.
- As a project owner, I want to know when team members need my input so that I'm not a bottleneck.

## Screen-by-Screen Specifications

### Screen 1: Notification Bell (Header)

FULLY DESIGNED

Bell icon in the top-right header. Shows unread count badge.

| Field | Detail |
|-------|--------|
| Bell Icon | Standard bell icon, header right section, next to user avatar |
| Unread Badge | Red circle with count (max display: 99+), hidden when 0 |
| Click Action | Opens notification dropdown panel |
| Real-time Update | Badge count updates via WebSocket without page refresh |

### Screen 2: Notification Dropdown

FULLY DESIGNED

Dropdown panel showing recent notifications.

| Field | Detail |
|-------|--------|
| Panel | 400px wide, max-height 500px, scrollable, anchored to bell icon |
| Notification Item | Avatar + actor name + action text + timestamp + unread indicator |
| Unread Indicator | Blue dot on left side of unread notifications |
| Click Action | Navigate to the relevant resource (comment, task, deliverable) |
| Mark All Read | Text link at top-right of panel, marks all as read |
| Empty State | "No notifications yet" with illustration |
| Timestamp | Relative time (2m ago, 1h ago, Yesterday) |

### Screen 3: Notification Email

IN DESIGN

Transactional email sent for high-priority notifications.

| Field | Detail |
|-------|--------|
| Subject Line | "[App Name] {Actor} {action} on {resource}" |
| Body | Actor avatar + action description + resource preview + CTA button |
| CTA | "View in App" button, deep links to the relevant resource |
| Unsubscribe | Footer link (required by CAN-SPAM) |

## Dependencies & Risks

### Dependencies
- WebSocket infrastructure (does not exist today — needs building)
- Email service (exists: SendGrid integration at `src/lib/email.ts`)
- User preferences model (does not exist — simplified version for v1)

### Risks
- WebSocket at scale: if connections exceed server capacity, fall back to polling
- Email deliverability: SendGrid reputation must be maintained
- Notification fatigue: without preferences UI, users may get too many notifications
