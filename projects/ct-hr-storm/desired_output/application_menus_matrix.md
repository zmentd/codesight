# Application Menu Navigation Matrix (Summarized)

Source of detail: `application_menus.md` (full evidence + submenu logic). This file condenses each menu key into a uniform matrix for quick reference. Static high‑level menu entries (from `Menu.jsp`) included first; all remaining entries are dynamic handler-backed keys registered via `xhtmlHandlers.put`.

Legend:
- Type: Container (expands only), List (direct list / find & list), Mixed (virtual links + lists), Direct (static link), List* (list with conditional child link(s)).
- Primary Landing Page: First JSP a user commonly reaches after clicking (TBD = not yet confirmed by JSP scan). `(expands only)` = no immediate JSP.
- Action Pages (Sample): Not exhaustive; fuller enumeration remains in evidence doc. TBD where pending scan.
- Child Conditions: Secondary permission(s) needed for virtual / nested nodes.
- Add Enabled When: Permission level that enables Add (usually EDIT or constant EDIT).
- Anomalies / Notes: Cross-linking, permission mismatches, feature flags, structural quirks.

## Static Top-Level (Menu.jsp)
| Key (Display) | Type | Primary Landing Page | Action Pages (Sample) | Secured By | Child Conditions | Add Enabled When | Anomalies / Notes |
|---------------|------|----------------------|-----------------------|------------|------------------|------------------|------------------|
| My Schedule | Direct→Dynamic | ScheduleLauncher.jsp?Format=1 (via Assignments expansion) | ScheduleLauncher.jsp (Formats 1,2,7,9) | None (static) | Delegated to Assignments perms | As per Assignments | Root static entry expands Assignments |
| My Personal Info | Direct | PersonalInfo.jsp (TBD exact filename) | (TBD) | None | — | — | Static single page |
| My Skills | Direct | Skills.jsp (TBD) | (TBD) | None | — | — | Static single page |

## A. Jobs & Requests (Bundle: jobs-requests)
| Key | Type | Primary Landing Page | Action Pages (Sample) | Secured By | Child Conditions | Add Enabled When | Anomalies / Notes |
|-----|------|----------------------|-----------------------|------------|------------------|------------------|------------------|
| Jobs | Mixed | FindJob.jsp | FindJob.jsp, JobDetails.jsp, CopyRequest.jsp, JobsReportParams.jsp | findRequestRequestor / newRequest / copyRequest / resources (composite) | fieldCrewRequest, editRequestForm, dubRequest (with feature flag), detailedRequest | EDIT on each specific permission | Feature flag `session.showNewFeatures` gates Dub |
| Request | List | FindJob.jsp | FindJob.jsp, JobDetails.jsp, CopyRequest.jsp | findRequestRequestor / resources (+ newRequest / copyRequest for virtual links) | newRequest, copyRequest | EDIT (new/copy) | Alias handled by JobXHTMLHandler |
| FieldCrewRequest | List | FindFieldCrew.jsp | FindFieldCrewResources.jsp, Details.jsp?action=New, AssignedCrews.jsp | fieldCrewRequest / findFieldCrewResources / resources | fcrAssignedCrews | EDIT (fieldCrewRequest) | Distinct job type FIELDCREW |
| EditRequest | List | FindEditRequest.jsp | FindEditRequest.jsp, EditRequestDetails.jsp | editRequestForm / resources | — | EDIT (editRequestForm) | Uses Job.TYPE_EDIT listing |
| Dubs | List | DubDetails.jsp?action=NEW (if creating) | DubDetails.jsp, (list items) | dubRequest (plus feature flag) | — | EDIT (dubRequest) | Hidden entirely if feature flag false |
| Tours | List (TBD) | (TBD) | (TBD) | Unknown | — | Unknown | Handler not yet analyzed fully |
| Assignments | Mixed | ScheduleLauncher.jsp?Format=1 | ScheduleLauncher.jsp (1,2,7,9), labor_mgmt/resource/Find.jsp | assignments / lastPostings / changeAssignmentsResource | lastPostings (Previous Postings), changeAssignmentsResource | EDIT (respective) | Date links unconditional; dynamic expansions (AssignmentsFor / Last3Postings) |

## B. Organizational Hierarchy (Bundle: org-structure)
| Key | Type | Primary Landing Page | Action Pages (Sample) | Secured By | Child Conditions | Add Enabled When | Anomalies / Notes |
|-----|------|----------------------|-----------------------|------------|------------------|------------------|------------------|
| Companies | List | CompanyDetails.jsp (TBD) | (TBD) | companies | — | EDIT (companies) | Root of hierarchy |
| Branches | List* | BranchDetails.jsp (TBD) | (TBD) | branches | divisions (>NONE) | EDIT (branches) | Child Divisions appear per branch |
| Divisions | List* | DivisionDetails.jsp (TBD) | (TBD) | divisions | departments (>NONE) | EDIT (divisions) | Child Departments conditional |
| Departments | List | DepartmentDetails.jsp (TBD) | (TBD) | departments | — | EDIT (departments) | Terminal in observed chain |
| Groups | List | (TBD) | (TBD) | Unknown | — | Unknown | Needs handler permission extraction |
| Services | List | (TBD) | (TBD) | Unknown | — | Unknown | Permission getter not yet captured |
| Packages | List | (TBD) | (TBD) | Unknown | — | Unknown | Requires handler review |

## C. Users & Skills (Bundle: users-groups / trainings)
| Key | Type | Primary Landing Page | Action Pages (Sample) | Secured By | Child Conditions | Add Enabled When | Anomalies / Notes |
|-----|------|----------------------|-----------------------|------------|------------------|------------------|------------------|
| Users | List | FindUser.jsp (TBD actual filename) | UserDetails.jsp, FindUser.jsp | users | (From UserGroups) users (>NONE) to show group Users link | EDIT (users) | Group expansion passes parentId |
| UserGroups | List* | UserGroupDetails.jsp (TBD) | (TBD) | securityGroups | users (>NONE) (to show Users child) | EDIT (securityGroups) | Counts users per group |
| ManagerPools | List | (TBD) | (TBD) | Unknown | — | Unknown | Handler not inspected |
| Trainings | List | TrainingFind.jsp (TBD) | TrainingDetails.jsp | training | — | EDIT (training) | Simple list |
| EmployeeTypes | List | EmployeeTypeDetails.jsp (TBD) | (TBD) | Constant EDIT | — | Always (constant EDIT) | Hardcoded Security.EDIT usage |
| TkUnions | List | (TBD) | (TBD) | Unknown | — | Unknown | Pending analysis |

## D. Resources & Collections (Bundle: resources / library-categories)
| Key | Type | Primary Landing Page | Action Pages (Sample) | Secured By | Child Conditions | Add Enabled When | Anomalies / Notes |
|-----|------|----------------------|-----------------------|------------|------------------|------------------|------------------|
| Resources | Mixed | FindResource.jsp (TBD) | ResourceDetails.jsp, Reports (virtual) | resources | resourcesReports (>NONE) | EDIT (resources) | Virtual 'Reports' node loads key `Reports` |
| ResourceCollections | List | (TBD) | (TBD) | Unknown | — | Unknown | Pending handler review |
| ServiceCollections | List | (TBD) | (TBD) | Unknown | — | Unknown | Pending handler review |
| RCollectionsVP | List | (TBD) | (TBD) | Unknown | — | Unknown | VP meaning unclear |
| Processes | List | (TBD) | (TBD) | Unknown | — | Unknown | Generic process catalog |
| Library | List* | CategoryFind.jsp (TBD) | CategoryDetails.jsp | library | (Per Category) link to `Categories` | EDIT (library) | Cross-links to Locations via Categories |
| Categories | List* | LocationList.jsp (TBD) | LocationDetails.jsp | library | Child link to `Location` per item | EDIT (library) | Key/handler name mismatch; Location handler used |
| Location | List | MaterialResourceDetails.jsp (TBD) | (TBD) | None (Security.NONE) | — | N/A (no security gating) | Items listed regardless of permission |

## E. Time & Calendar Configuration (Bundle: time-config)
| Key | Type | Primary Landing Page | Action Pages (Sample) | Secured By | Child Conditions | Add Enabled When | Anomalies / Notes |
|-----|------|----------------------|-----------------------|------------|------------------|------------------|------------------|
| DayTypes | List | DayTypeDetails.jsp (TBD) | DayTypePenalties.jsp (Add) | dayTypes | — | EDIT (dayTypes) | Simple list |
| DaysRulesGroups | List | RulesDetails.jsp (TBD) | (TBD) | daysOffRulesGroups | — | EDIT (daysOffRulesGroups) | Gating for day off rule groups |
| TKHolidays | List* | HolidayDetails.jsp (TBD) | (TBD) | timeZones | gmtOffsets (>NONE) to show occurrences link | EDIT (timeZones) | Permission chain to GMTOffsets |
| HolidaysOcurrences | List | HolidayOccurrenceDetails.jsp (TBD) | (TBD) | gmtOffsets | — | EDIT (gmtOffsets) | Spelling retained as in code |
| TimeZones | List* | TimeZoneDetails.jsp (TBD) | (TBD) | timeZones | gmtOffsets (>NONE) (to show GMTOffsets node) | EDIT (timeZones) | Child link conditional |
| GMTOffsets | List | GMTOffsetDetails.jsp (TBD) | (TBD) | gmtOffsets | — | EDIT (gmtOffsets) | Add GMT offset at EDIT |
| OvertimeTypes | List | OverTimeTypeDetails.jsp (TBD) | (TBD) | overTimeCatalog | — | EDIT (overTimeCatalog) | Standard listOfItems pattern |
| Penalties | List | PenaltyDetails.jsp (TBD) | (TBD) | penalties | — | EDIT (penalties) | Standard list |
| ActivityFlags | List | ActivityFlagDetails.jsp (TBD) | (TBD) | activityFlag | — | EDIT (activityFlag) | Standard list |

## F. Contracts & Agreements (Bundle: contracts-domain)
| Key | Type | Primary Landing Page | Action Pages (Sample) | Secured By | Child Conditions | Add Enabled When | Anomalies / Notes |
|-----|------|----------------------|-----------------------|------------|------------------|------------------|------------------|
| Contracts | List* | ContractDetails.jsp (TBD) | (TBD) | contracts | rulesGroups (>NONE) (Rules groups link) | EDIT (contracts) | Child to ContractGroups only from Contracts context |
| ContractGroups | List | RulesGroupDetails.jsp (TBD) | (TBD) | rulesGroups | — | EDIT (rulesGroups) | Exposed via Contracts or direct key |
| Agreements | List* | AgreementDetails.jsp (TBD) | (TBD) | contracts | rulesGroups (>NONE) (Contracts link → TkContracts) | EDIT (contracts) | Cross navigation to TkContracts |
| TkContracts | List* | TkContractDetails.jsp (TBD) | (TBD) | rulesGroups | rulesGroups (>NONE) (ContractsRevisions link) | EDIT (rulesGroups) | Chain to revisions |
| ContractsRevisions | List | ContractRevisionDetails.jsp (TBD) | (TBD) | rulesGroups | — | EDIT (rulesGroups) | Terminal revision list |

## G. Payroll (Bundle: payroll)
| Key | Type | Primary Landing Page | Action Pages (Sample) | Secured By | Child Conditions | Add Enabled When | Anomalies / Notes |
|-----|------|----------------------|-----------------------|------------|------------------|------------------|------------------|
| EarningCodes | List | EarningCodesDetails.jsp (TBD) | (TBD) | earningCodes | — | EDIT (earningCodes) | Standard list |
| PayTransactions | List | PayTransactionsDetails.jsp (TBD) | (TBD) | (ANOMALY) timeZones | — | timeZones==EDIT (current) | Should likely use getPayTransactions(); verify |

## H. Indicators & Taxonomy (Bundle: indicators-codes)
| Key | Type | Primary Landing Page | Action Pages (Sample) | Secured By | Child Conditions | Add Enabled When | Anomalies / Notes |
|-----|------|----------------------|-----------------------|------------|------------------|------------------|------------------|
| Indicators | List | IndicatorsDetails.jsp (TBD) | (TBD) | indicators | — | EDIT (indicators) | Standard listOfIndicators |
| IndicatorsCodeGroups | List* | CodeGroupDetails.jsp (TBD) | (TBD) | indicators | indicators (>NONE) (Indicators & Codes child links) | EDIT (indicators) | Virtual branching to Indicators & Codes |
| Codes | List | CodeDetails.jsp (TBD) | (TBD) | indicators | — | EDIT (indicators) | Standard listOfCodes |
| ClientTypes | List | ClientTypeDetails.jsp (TBD) | (TBD) | Constant EDIT | — | Always (constant EDIT) | Hardcoded security; no getter |

## I. Approvals (Bundle: approvals)
| Key | Type | Primary Landing Page | Action Pages (Sample) | Secured By | Child Conditions | Add Enabled When | Anomalies / Notes |
|-----|------|----------------------|-----------------------|------------|------------------|------------------|------------------|
| SecondLevelApprovals | List | SecondLevelApprovalDetails.jsp (TBD) | (TBD) | secondLevelApprovals | — | EDIT (secondLevelApprovals) | Approver pools |

## J. Scheduler (Bundle: quartz-scheduler)
| Key | Type | Primary Landing Page | Action Pages (Sample) | Secured By | Child Conditions | Add Enabled When | Anomalies / Notes |
|-----|------|----------------------|-----------------------|------------|------------------|------------------|------------------|
| QuartzCP | Container | (expands only) | Quartz* (JobGroup / Schedule / Job) JSPs | quartzControlPanel | — (children share) | EDIT (children lists) | Injects Feeds Status link |
| QuartzSchedule | List | QuartzScheduleDetails.jsp (TBD) | (TBD) | quartzControlPanel | — | EDIT (quartzControlPanel) | Standard list |
| QuartzJobGroup | List* | QuartzJobGroupDetails.jsp (TBD) | (TBD) | quartzControlPanel | quartzControlPanel (>NONE) (Jobs child) | EDIT (quartzControlPanel) | Child Jobs link per group |
| QuartzJob | List* | QuartzJobDetails.jsp (TBD) | (TBD) | quartzControlPanel | quartzControlPanel (>NONE) (Assigned Schedules) | EDIT (quartzControlPanel) | Assigned Schedules child |
| QuartzJobSchedule | List | QuartzJobScheduleDetails.jsp (TBD) | (TBD) | quartzControlPanel | — | N/A (no Add) | listOfItems invoked with security=0 (no Add) |

## K. Misc (Unassigned or Pending Confirmation)
If any remaining keys appear later (e.g., reports root) they will be appended here after verification.

---
## Next Fill Actions
1. Confirm actual JSP filenames (replace TBD) via directory scan of each handler base path.
2. Extract exact permission method names for Unknown items (Groups, Services, etc.).
3. Add numeric level semantics (NONE/VIEW/EDIT) once standardized mapping gathered.
4. Populate Action Pages with Report / Log pages where referenced.

## Anomaly Table (Initial)
| Key | Observed Permission Getter | Expected | Action | Status |
|-----|----------------------------|----------|--------|--------|
| PayTransactions | security.getTimeZones() | security.getPayTransactions() | Review handler & correct if unintended | OPEN |

---
Generated as a derivative summary; authoritative behavioral detail remains in `application_menus.md`.
