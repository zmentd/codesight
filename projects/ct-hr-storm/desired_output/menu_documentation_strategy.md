# Menu & Page Documentation Strategy

This document defines the forward structure for documenting navigation → page behavior in `ct-hr-storm` without altering the existing evidence file `application_menus.md`.

## 1. Goals
- Provide an at-a-glance master matrix (menus ↔ security ↔ landing pages).
- Group related menu keys into domain "Page Bundles" for deep dive docs.
- Standardize how we list JSP endpoints (Find, Details, Report, Log, etc.).
- Create a scalable path for later automation (JSP inventory + permission diff detection).

## 2. Layers
1. Master Navigation Matrix (single file) – concise, all keys, columns below.
2. Bundle Documents (one per domain bundle) – narrative + full JSP inventory + security impact.
3. (Optional) Generated JSON index – machine-readable listing for tooling.

## 3. Master Navigation Matrix Columns
| Column | Purpose |
|--------|---------|
| Key | Exact `ObjName` registered via `xhtmlHandlers.put` |
| Bundle | Logical domain grouping (see Section 5) |
| Type | Container | List | Mixed | Direct |
| Primary Landing Page | The first JSP a typical user reaches *after clicking the menu* (or `(expands only)` for pure containers) |
| Action Pages (Sample) | Key JSPs (Find*, *Details*, *Report*, *Log*) actually referenced by handler logic – kept short here |
| Secured By | Primary permission getter / constant controlling list visibility |
| Child Conditions | Secondary permission(s) required to show nested virtual nodes |
| Add Enabled When | Permission condition for Add link(s) (e.g. EDIT, or constant EDIT) |
| Anomalies / Notes | Cross-linking, permission mismatches, feature flags |

(Full exhaustive submenu logic & evidence stays in `application_menus.md`; matrix links out to bundle docs.)

### 3.1 Type Classification Rules
- Container: Click only expands (no immediate JSP). Example: `QuartzCP`.
- List: Root directly lists entities or shows Find + list. Example: `Users`.
- Mixed: Root offers multiple conceptual child entry points (Requests family: `Jobs`).
- Direct: Static JSP link in `Menu.jsp` (e.g., `My Personal Info`).

### 3.2 Example (Subset)
| Key | Bundle | Type | Primary Landing Page | Action Pages (Sample) | Secured By | Child Conditions | Add Enabled When | Anomalies / Notes |
|-----|--------|------|----------------------|----------------------|------------|------------------|------------------|------------------|
| Jobs | jobs-requests | Mixed | FindJob.jsp (when choosing "Find request") | FindJob.jsp, JobDetails.jsp, CopyRequest.jsp, JobsReportParams.jsp | composite (findRequestRequestor/newRequest/copyRequest/resources) | fieldCrewRequest, editRequestForm, dubRequest+feature flag | EDIT on respective perms | Multiple virtual links; feature flag gates Dub |
| Request | jobs-requests | List | FindJob.jsp | FindJob.jsp, JobDetails.jsp, CopyRequest.jsp | findRequestRequestor/resources | newRequest, copyRequest | EDIT for creation | Alias handled by JobXHTMLHandler |
| FieldCrewRequest | jobs-requests | List | FindFieldCrew.jsp | FindFieldCrewResources.jsp, Details.jsp, AssignedCrews.jsp | fieldCrewRequest/findFieldCrewResources/resources | fcrAssignedCrews | EDIT on fieldCrewRequest | Distinct job type (FIELDCREW) |
| Assignments | assignments | Mixed | ScheduleLauncher.jsp?Format=1 (Today) | ScheduleLauncher.jsp (Formats 1,2,7,9), Find resource JSP | assignments/lastPostings | lastPostings, changeAssignmentsResource | Based on respective perm == EDIT | Date nodes unconditional |
| Contracts | contracts-domain | Container | (expands only) | ContractDetails.jsp (entity rows) | contracts | rulesGroups (to show Rules groups) | EDIT via contracts | Parent path switches security context on groups |
| PayTransactions | payroll | List | PayTransactionsDetails.jsp (entity row) | (TBD scan) | (ANOMALY) timeZones used | — | timeZones==EDIT (currently) | Should likely use getPayTransactions() |
| QuartzCP | quartz-scheduler | Container | (expands only) | Quartz* JSPs under control panel | quartzControlPanel | — (children use same) | EDIT for Add in children | Root injects Feeds Status link |

(Primary Landing Page / Action Pages for some keys remain TBD until JSP scan is executed – mark as `(TBD)` where unknown.)

## 4. Bundle Documents
One markdown file per bundle under `pages/` (see Section 8 for naming).

### 4.1 Bundle Doc Structure Template
```
# <Bundle Display Name>
Bundle ID: <kebab-case>

Covered Keys: <comma-separated list>

## 1. Overview
Business / functional scope (validated or TO VALIDATE).

## 2. Menu Entry Paths
- <Key> → (Type: Container/List/Mixed) → Primary Landing Page
- ... (list each)

## 3. Security Matrix
| Permission Getter / Constant | Affects | Effect Summary |
|------------------------------|---------|----------------|
| security.getContracts() | Contracts list | Visibility & row listing |
| security.getRulesGroups() | Nested groups & revisions | Enables child links + Add |
...

## 4. JSP Inventory
| Category | JSP | Trigger (menu action / handler path) | Notes |
|----------|-----|--------------------------------------|-------|
| Find | FindJob.jsp | "Find request" virtual link | Requires findRequestRequestor |
| Details | JobDetails.jsp | Clicking existing request | Row-level permission gating |
| New | JobDetails.jsp?action=New | "New request" link | Shown if newRequest OR findRequestRequestor > NONE |
| Copy | CopyRequest.jsp | "Copy request" link | Requires copyRequest OR findRequestRequestor |
| Report | JobsReportParams.jsp | "Detailed requests" link | Requires detailedRequest |

## 5. Handler Logic Summary
Summarize `getChildren` patterns & conditional nodes with evidence line refs (line numbers optional).

## 6. Data Sources / Stored Procedures (If identified)
List referenced DAO / proc names extracted from handler or JSP scriptlets.

## 7. Conditional UI & Feature Flags
Enumerate session flags (e.g., session.showNewFeatures) and their gating impact.

## 8. Anomalies / Open Questions
List mismatches, TODO verifications.

## 9. Cross Navigation
Other bundles this area links into (e.g., Codes from IndicatorsCodeGroups).

## 10. Revision Log
Date | Change | Author.
```

## 5. Proposed Bundles & Key Mapping
| Bundle ID | Display Name | Keys |
|-----------|--------------|------|
| jobs-requests | Jobs & Requests | Jobs, Request, FieldCrewRequest, EditRequest, Dubs, Tours (later) |
| assignments | Assignments & Schedule Views | Assignments |
| org-structure | Organizational Hierarchy | Companies, Branches, Divisions, Departments, Groups, Services, Packages |
| users-groups | Users & Security Groups | Users, UserGroups, ManagerPools (if confirmed) |
| trainings | Trainings & Employee Types | Trainings, EmployeeTypes, TkUnions |
| resources | Resources & Collections | Resources, ResourceCollections, ServiceCollections, RCollectionsVP, Processes |
| library-categories | Library & Categories | Library, Categories, Location |
| time-config | Time & Calendar Config | DayTypes, DaysRulesGroups, TKHolidays, HolidaysOcurrences, TimeZones, GMTOffsets |
| overtime-penalties | Overtime & Penalties | OvertimeTypes, Penalties, ActivityFlags |
| contracts-domain | Contracts & Agreements | Contracts, ContractGroups, Agreements, TkContracts, ContractsRevisions |
| payroll | Payroll Codes & Transactions | EarningCodes, PayTransactions |
| indicators-codes | Indicators & Taxonomy | Indicators, IndicatorsCodeGroups, Codes, ClientTypes |
| approvals | Approvals | SecondLevelApprovals |
| quartz-scheduler | Scheduler (Quartz) | QuartzCP, QuartzSchedule, QuartzJobGroup, QuartzJob, QuartzJobSchedule |

(If a key appears minimal it may share a bundle until content justifies separation.)

## 6. Extraction / Automation Plan (Phase 2)
Script idea (Python):
1. Locate handler class → parse `getMyDetailsPagePath()` return value.
2. Enumerate JSPs under that directory.
3. Grep handler + JSPs for literal occurrences of those filenames to filter unused.
4. Record permission getters by regex: `security.get[A-Z][A-Za-z0-9_]*\(`.
5. Output JSON: `{ key: { bundle, basePath, jsp: [...], permissions: [...], anomalies: [...] } }`.
6. Regenerate matrix & per-bundle skeleton sections programmatically.

## 7. Handling Anomalies
Maintain a centralized table in master file listing anomalies with: Key | Observed | Expected | Action | Status.
Initial:
- PayTransactions | Uses `security.getTimeZones()` | Should use `security.getPayTransactions()` | Confirm intention / fix | OPEN.

## 8. File & Naming Conventions
- Master matrix file: `application_menus_matrix.md` (to be created after first automation or manual seed).
- Bundle docs directory: `pages/` under `desired_output/`.
  - Example: `pages/jobs-requests.md`.
- JSON index (future): `pages/menu_index.json`.

## 9. Incremental Adoption Plan
Step | Action | Output
---- | ------ | ------
1 | Approve structure (this document) | —
2 | Seed master matrix (manually for top 8 keys) | `application_menus_matrix.md`
3 | Author first bundle (`jobs-requests.md`) using template | Reference model
4 | Run first JSP inventory script (manual or ad-hoc) | Preliminary JSP list
5 | Fill remaining matrix rows progressively | Updated matrix
6 | Add anomaly table & track remediation | Matrix section
7 | Automate regeneration (optional) | JSON + regenerated docs

## 10. Immediate Next Actions (If Approved)
1. Create `application_menus_matrix.md` with 10–12 representative entries.
2. Draft `pages/jobs-requests.md` fully.
3. Collect team feedback (columns, naming, depth) before scaling.

## 11. Rationale Summary
- Separates evidentiary raw detail (existing file) from consumable matrix & narrative pages.
- Encourages consistency & automation.
- Minimizes duplication: deep permission logic maintained once per bundle.

---
Questions to Confirm:
1. Include numeric permission levels (NONE/VIEW/EDIT) now or later? (Recommend later after extraction.)
2. Represent feature flags (e.g., `session.showNewFeatures`) in matrix or only bundle docs? (Recommend bundle only.)
3. Need cross-reference to stored procedures/DAO class names in initial pass? (Optional.)

Provide answers and I can proceed with seeding the matrix & first bundle.
