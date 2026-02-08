# Yufeed Product Development Rules

**Purpose:** Reusable rules for AI systems to generate consistent, high-quality product artifacts.  
**Version:** 1.0  
**Last Updated:** 2026-01-29

---

## 1. User Story Format Rules

### Standard Template
```
### US-{XXX}: {Short Title}
**As a** {role}  
**I want** {capability}  
**So that** {business value}

**Acceptance Criteria:**
- [ ] {Testable criterion 1}
- [ ] {Testable criterion 2}
- [ ] {Testable criterion N}

**Story Points:** {1|2|3|5|8|13|21}  
**Sprint:** {sprint_number}  
**Dependencies:** {US-XXX, US-YYY | None}  
**Tech Notes ({role}):** {Optional technical implementation hints}
```

### Rules for Writing User Stories

1. **INVEST Principles**
   - **I**ndependent: Stories should be self-contained
   - **N**egotiable: Details can be discussed with team
   - **V**aluable: Must deliver value to user/business
   - **E**stimable: Team can estimate effort
   - **S**mall: Completable in one sprint
   - **T**estable: Has clear acceptance criteria

2. **Role Guidelines**
   - Use real persona names from the product (e.g., "Compliance Officer", "MLRO")
   - Avoid generic roles like "User" unless truly applicable
   - System stories use "As a System" for background processes

3. **Acceptance Criteria Rules**
   - Minimum 3, maximum 8 criteria per story
   - Each criterion must be independently testable
   - Use checkbox format `- [ ]` for tracking
   - Be specific: "Returns 200 OK" not "Works correctly"
   - Include API endpoints with methods and paths

4. **Story Point Scale**
   - Use Fibonacci: 1, 2, 3, 5, 8, 13, 21
   - 1 point = ~2 hours of work
   - 13+ points = Consider splitting
   - Points represent complexity, not just time

---

## 2. Epic Structure Rules

### Epic Template
```
## EPIC-{XXX}: {Epic Name}

**Description:** {1-2 sentence summary}  
**Business Value:** {Why this matters to customers/business}  
**Definition of Done:** {Epic-level completion criteria}  
**Estimated Points:** {Total story points}  
**Target Sprints:** {Sprint X - Sprint Y}
```

### Epic Organization Rules

1. **Naming Convention**
   - EPIC-001 through EPIC-XXX
   - Use domain-based names (e.g., "Policy Management", not "Sprint 4 Work")

2. **Size Guidelines**
   - 5-15 user stories per epic
   - 30-80 story points per epic
   - Completable in 2-4 sprints

3. **Dependencies**
   - Document inter-epic dependencies clearly
   - Avoid circular dependencies
   - Sequence epics in implementation order

---

## 3. Sprint Planning Rules

### Sprint Structure
```yaml
sprint_length: 2 weeks (10 working days)
team_capacity: story_points_per_sprint = team_size * 10
buffer: 20% for unforeseen issues
ceremonies:
  - sprint_planning: 2 hours
  - daily_standup: 15 minutes
  - sprint_review: 1 hour
  - sprint_retro: 1 hour
  - backlog_refinement: 1 hour (mid-sprint)
```

### Velocity Rules

1. **Estimation**
   - First sprint: Estimate 60% of theoretical capacity
   - Subsequent sprints: Use rolling 3-sprint average
   - Account for holidays, PTO, meetings

2. **Allocation**
   - 70% new features
   - 20% tech debt / improvements
   - 10% buffer / bugs

3. **Sprint Goals**
   - One clear goal per sprint
   - Goal should be achievable if 80% of stories complete
   - Communicate goal to stakeholders

---

## 4. Definition of Done (DoD) Checklist

### Story-Level DoD
```markdown
- [ ] Code written and passes linting
- [ ] Unit tests written (>80% coverage for new code)
- [ ] Integration tests for API endpoints
- [ ] Code reviewed and approved by peer
- [ ] Documentation updated (API docs, README)
- [ ] Merged to `develop` branch
- [ ] Deployed to staging environment
- [ ] Product Owner accepts demo
- [ ] No critical/blocker bugs
```

### Sprint-Level DoD
```markdown
- [ ] All committed stories meet Story-Level DoD
- [ ] Sprint goal achieved
- [ ] Release notes drafted
- [ ] Stakeholder demo completed
- [ ] Metrics/KPIs updated
- [ ] Retro action items documented
```

### Epic-Level DoD
```markdown
- [ ] All stories in epic complete
- [ ] End-to-end user journey tested
- [ ] Feature flag enabled in production
- [ ] Customer documentation published
- [ ] Success metrics baseline established
- [ ] Handoff to support team complete
```

---

## 5. Backlog Prioritization Rules

### Priority Framework (RICE)

```
RICE Score = (Reach × Impact × Confidence) / Effort

Reach: How many users affected per quarter (1-100)
Impact: Effect on user (0.25=low, 0.5=med, 1=high, 2=massive, 3=critical)
Confidence: How sure are we (0.5=low, 0.8=med, 1=high)
Effort: Person-months of work
```

### Priority Labels

| Priority | Description | Response Time |
|----------|-------------|---------------|
| P0 - Critical | Production blocker | Immediate |
| P1 - High | Revenue/compliance impact | This sprint |
| P2 - Medium | User pain point | Next 2 sprints |
| P3 - Low | Nice to have | Backlog |

### Sprint Commitment Rules

1. Always include at least one P1 story
2. No more than 2 sprints of P3 stories queued
3. If P0 emerges, swap out lowest-priority committed story

---

## 6. Technical Debt Rules

### Classification

```yaml
tech_debt_types:
  - code_quality: "Refactoring, test coverage, documentation"
  - architecture: "Design improvements, scalability"
  - dependency: "Library updates, security patches"
  - infrastructure: "DevOps, monitoring, tooling"
```

### Management Rules

1. Track in separate backlog or label
2. Allocate 20% of sprint capacity
3. Prioritize security-related debt
4. Review quarterly with CTO

---

## 7. Dependency Management Rules

### Dependency Types

```yaml
internal:
  - story_to_story: "US-005 depends on US-004"
  - epic_to_epic: "EPIC-005 depends on EPIC-002"
  - team_to_team: "Frontend blocked by Backend API"

external:
  - vendor: "Anthropic API availability"
  - regulatory: "Compliance approval needed"
  - infrastructure: "Database migration required"
```

### Handling Rules

1. Document all dependencies in story template
2. Schedule dependent stories in later sprints
3. Create placeholder stories for blocked work
4. Escalate external blockers immediately

---

## 8. Acceptance Criteria Guidelines

### Good Criteria Examples
```markdown
✅ "API returns 200 OK with JSON body containing user_id"
✅ "Page loads in <2 seconds on 3G connection"
✅ "Error message displayed when email format invalid"
✅ "Database record created with status='draft'"
✅ "Celery task runs daily at 8:00 AM UTC"
```

### Bad Criteria Examples
```markdown
❌ "Works correctly" (not testable)
❌ "Looks good" (subjective)
❌ "Fast enough" (not measurable)
❌ "User is happy" (not verifiable)
❌ "No bugs" (impossible to prove)
```

### Criteria Categories

1. **Functional**: What the feature does
2. **Validation**: Input/output rules
3. **Error Handling**: Edge cases
4. **Performance**: Speed, scale requirements
5. **Security**: Auth, authorization rules
6. **Integration**: API contracts, database changes

---

## 9. Story Splitting Techniques

When a story is too large (>13 points), split using:

### 1. Workflow Steps
```
Original: "User can complete checkout"
Split:
- US-A: "User can add items to cart"
- US-B: "User can enter shipping address"
- US-C: "User can enter payment details"
- US-D: "User can confirm and submit order"
```

### 2. Business Rules
```
Original: "Validate user input"
Split:
- US-A: "Validate email format"
- US-B: "Validate password strength"
- US-C: "Validate phone number by country"
```

### 3. Data Variations
```
Original: "Import data from multiple sources"
Split:
- US-A: "Import from CSV"
- US-B: "Import from Excel"
- US-C: "Import from API"
```

### 4. Operations (CRUD)
```
Original: "Manage policies"
Split:
- US-A: "Create new policy"
- US-B: "View policy list"
- US-C: "Edit existing policy"
- US-D: "Delete/archive policy"
```

---

## 10. Panel Collaboration Rules

### Role Responsibilities

```yaml
product_owner:
  - writes user stories
  - defines acceptance criteria
  - prioritizes backlog
  - accepts completed work

scrum_master:
  - facilitates ceremonies
  - removes impediments
  - ensures DoD compliance
  - tracks velocity

cto:
  - technical architecture decisions
  - identifies tech debt
  - evaluates feasibility
  - flags technical risks

engineering_lead:
  - estimates story points
  - assigns team members
  - code review oversight
  - deployment approval
```

### Decision Matrix

| Decision Type | Final Authority | Consulted |
|---------------|-----------------|-----------|
| Feature scope | Product Owner | CTO, Engineering |
| Technical approach | CTO | Engineering Lead |
| Sprint commitment | Scrum Master | Team |
| Resource allocation | Engineering Lead | Scrum Master |
| Release timing | Product Owner | All |

---

## 11. API Story Conventions

### Endpoint Specification Format
```markdown
**Endpoint:** `{METHOD} /api/{resource}/{action}`
**Auth:** {Required | Optional | None}
**Request Body:** {JSON schema or "None"}
**Response:** {HTTP status} with {JSON schema}
**Errors:** {List of error codes and meanings}
```

### Example
```markdown
**Endpoint:** `POST /api/policies/{id}/link-obligation/{obligation_id}`
**Auth:** Required (MLRO or Compliance Officer role)
**Request Body:** None
**Response:** 200 OK with `{policy_id, obligation_id, linked_at}`
**Errors:**
- 404: Policy or obligation not found
- 403: Insufficient permissions
- 409: Already linked
```

---

## 12. Testing Requirements Rules

### Unit Test Coverage
```yaml
minimum_coverage: 80%
critical_paths: 100%
exceptions:
  - third_party_integrations
  - ui_components (covered by e2e)
```

### Test Types by Story

| Story Type | Required Tests |
|------------|----------------|
| API endpoint | Unit + Integration |
| Background job | Unit + Integration |
| UI component | Unit + E2E |
| Data migration | Unit + Rollback test |
| Third-party integration | Mock + Integration |

---

## 13. Documentation Requirements

### Per-Story Documentation
```markdown
- [ ] API endpoint added to OpenAPI/Swagger spec
- [ ] README updated if new feature area
- [ ] Code comments for complex logic
- [ ] Error messages user-friendly
```

### Per-Epic Documentation
```markdown
- [ ] Feature guide in docs/features/
- [ ] Architecture decision record (ADR) if needed
- [ ] Changelog entry prepared
- [ ] Support team briefing scheduled
```

---

## Usage Instructions for AI Systems

When generating product artifacts, follow these rules:

1. **Always use the User Story template** in Section 1
2. **Include all required fields**: Story points, Sprint, Dependencies
3. **Acceptance criteria must be testable** per Section 8
4. **Apply INVEST principles** for every story
5. **Split stories over 13 points** using techniques in Section 9
6. **Document API endpoints** using format in Section 11
7. **Include DoD checklist** for sprint planning
8. **Specify roles from the product context**, not generic roles

**Input Required for Story Generation:**
- Epic name and description
- User personas/roles
- Technical context (existing APIs, models, services)
- Sprint number and capacity
- Prior story dependencies
