# Application Menus in ct-hr-storm

This document provides an evidence-based, exhaustive catalog of all menu and submenu roots discoverable directly from the ct-hr-storm codebase using static analysis of:
- JSP navigation entry point: `Deployment/Storm2/WebContent/ResourceUser/Menu.jsp`
- Dynamic child loader: `Deployment/Storm2/WebContent/ResourceUser/GetChildren.jsp`
- Menu registry classes: `SystemGeneral` and `SystemSetup` which populate `xhtmlHandlers`

NO speculative items are included. Where purpose is not explicitly defined in code we indicate that the description is inferred from the handler class name and MUST be validated.

## Methodology
1. Searched for `xhtmlHandlers.put(` across the project to enumerate dynamic object names exposed via the menu expansion mechanism.
2. Inspected `SystemGeneral.java` (extends `com.nbcuni.dcss.storm.isl.general.GeneralSetup`).
3. Inspected `SystemSetup.java` (extends `com.nbcuni.dcss.storm.isl.setup.SystemSetup`).
4. Collected every key registered: the left-hand string literal in each `this.xhtmlHandlers.put("<Key>", <Handler>.xhtmlHandlerObject())` call.
5. Cross-referenced JSP `Menu.jsp` and `GetChildren.jsp` to confirm these keys are requested via `GetChildren.jsp?ObjName=<Key>` pattern when the user expands nodes.
6. Did NOT include higher-level conceptual groupings (e.g. “System”, “Reports”, “Accounting”) because those container labels are not directly assembled in inspected files; only concrete expandable object keys registered in handlers are listed below. (High-level labels shown in earlier draft remain but are explicitly separated from concrete handler-backed keys.)

## High-Level Static Entries (from Menu.jsp)
These entries are rendered directly in `Menu.jsp` before any AJAX expansion.

### My Schedule
Evidence: `Deployment/Storm2/WebContent/ResourceUser/Menu.jsp` (static <li> element invoking dynamic expansion of `Assignments`).
Description: User-facing schedule root. Expands into dynamic scheduling views via `Assignments` key.
Secured by: None (static render; dynamic children governed by Assignments handler security)

### My Personal Info
Evidence: `Menu.jsp` (static <li>/<a> direct link; no `GetChildren.jsp` call).
Description: Direct navigation to personal information page; no dynamic children.
Secured by: None (no dynamic expansion security inspected here)

### My Skills
Evidence: `Menu.jsp` (static <li>/<a> direct link; no `GetChildren.jsp` call).
Description: Direct navigation to skills information; no dynamic children.
Secured by: None (no dynamic expansion security inspected here)

## Grouped Dynamic Object Keys (Handler-Backed)
All items below are FIRST-LEVEL dynamic menu object keys (registered via `xhtmlHandlers.put`). Grouping headers are organizational only; each key now appears as its own subsection (no numbering). Evidence and handler references unchanged.
NOTE: Each handler `getChildren` signature includes a `Security` parameter; specific permission constants/IDs were not extracted in this pass. Where exact value/flag is not yet identified we mark `Unknown`.

### A. Operational Requests & Scheduling

#### Jobs
Evidence: `SystemGeneral.java` – `this.xhtmlHandlers.put("Jobs", JobXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.dsl.request.xhtml.JobXHTMLHandler`
Description: Handles job-related request entities (inferred from name).
Secured by: Combination of specific request-related permissions. Submenu visibility gates use: findRequestRequestor, newRequest, copyRequest, fieldCrewRequest, findFieldCrewResources, editRequestForm, dubRequest (feature flag dependent), detailedRequest.
Submenus (from JobXHTMLHandler when objName == "Jobs"):
- General Request -> loads key 'Request'; requires ANY of (findRequestRequestor OR newRequest OR copyRequest) (expression: secure(sum of the three, baseline 0)).
- Field Crew Request -> loads key 'FieldCrewRequest'; requires (fieldCrewRequest OR findFieldCrewResources).
- Edit Request -> loads key 'EditRequest'; requires editRequestForm.
- Dub Request -> loads key 'Dubs'; requires dubRequest AND session.showNewFeatures.
- Detailed requests (report link) -> JobsReportParams.jsp; requires detailedRequest.

#### Request
Evidence: `SystemGeneral.java` – `this.xhtmlHandlers.put("Request", JobXHTMLHandler.xhtmlHandlerObject());`
Handler: `JobXHTMLHandler` (same as Jobs)
Description: Alias to job handler (inferred from duplicate handler usage).
Secured by: Request-level operations gated by: findRequestRequestor, newRequest, copyRequest, resources (for listing existing requests). New/Copy items hidden when both triggering perms at NONE.
Submenus (from JobXHTMLHandler when objName == "Request"):
- Find request -> FindJob.jsp; requires findRequestRequestor.
- New request -> New request form (getNewObj); shown if (newRequest OR findRequestRequestor) > NONE.
- Copy request -> CopyRequest.jsp flow; shown if (copyRequest OR findRequestRequestor) > NONE (variant path if preSAP flag true).
- Existing Requests list -> listOfItems(security.getResources(), Job.TYPE_REGULAR) (each row gated by resources permission value).

#### FieldCrewRequest
Evidence: `SystemGeneral.java` – `...put("FieldCrewRequest", JobFieldCrewXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.dsl.request.field.xhtml.JobFieldCrewXHTMLHandler`
Description: Field crew–specific job/request operations (inferred).
Secured by: fieldCrewRequest, findFieldCrewResources, fcrAssignedCrews, resources.
Submenus (from JobFieldCrewXHTMLHandler):
- Find crews -> FindFieldCrewResources.jsp; requires findFieldCrewResources.
- Find field crew request -> FindFieldCrew.jsp; requires fieldCrewRequest.
- New field crew request -> Details.jsp?action=New; requires fieldCrewRequest.
- Assigned Crews (report) -> report/AssignedCrews.jsp; requires fcrAssignedCrews.
- Existing Field Crew Requests list -> listOfItems(security.getResources(), Job.TYPE_FIELDCREW).

#### Tours
Evidence: `SystemGeneral.java` – `...put("Tours", TourXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.dsl.tour.xhtml.TourXHTMLHandler`
Description: Tour request / management entities (inferred).
Secured by: Unknown

#### EditRequest
Evidence: `SystemGeneral.java` – `...put("EditRequest", EditRequestXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.dsl.request.edit.xhtml.EditRequestXHTMLHandler`
Description: Edit service requests (inferred).
Secured by: editRequestForm (for all actions) plus resources (for listing existing edit requests).
Submenus (from EditRequestXHTMLHandler):
- Find edit request -> FindEditRequest.jsp; requires editRequestForm.
- New edit request -> EditRequestDetails.jsp?action=New; requires editRequestForm.
- Existing Edit Requests list -> listOfItems(security.getResources(), Job.TYPE_EDIT).

#### Dubs
Evidence: `SystemGeneral.java` – `...put("Dubs", DubRequestXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.dsl.request.dub.xhtml.DubRequestXHTMLHandler`
Description: Dubbing-related requests (inferred).
Secured by: dubRequest (and session.showNewFeatures flag) controlling both creation and listing.
Submenus (from DubRequestXHTMLHandler):
- New Dub Request -> DubDetails.jsp?action=NEW; requires dubRequest AND session.showNewFeatures.
- Existing Dub Requests list -> listOfItems(security.getDubRequest(), lastUsedDubsCompany) shown only if dubRequest > NONE AND session.showNewFeatures.

#### Assignments
Evidence: `SystemGeneral.java` – `...put("Assignments", AssignmentXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.dsl.schedule.assignment.xhtml.AssignmentXHTMLHandler`
Description: Scheduling / assignment entities (inferred).
Secured by: assignments (My assignments), lastPostings (Previous Postings), changeAssignmentsResource (Change resource). Date range links appear unconditional (no explicit security gate beyond overall handler access). Additional display logic depends on session security for posting history and cost object visibility.
Submenus (from AssignmentXHTMLHandler):
- My assignments -> key 'AssignmentsFor' (calls getChildren with modified key); requires assignments.
- Today (Format=1) -> ScheduleLauncher.jsp?Format=1 for current day; no explicit security check.
- Today 2 days (Format=2) -> ScheduleLauncher.jsp?Format=2; no explicit security check.
- Next 6 daily entries (Format=1) -> one per subsequent day (loop generated); no explicit security check.
- Posted 7 days -> ScheduleLauncher.jsp?Format=7; visibility depends on presence of SavedDate4Schedule7 data (node status) but no explicit permission method.
- Posted 9 days -> ScheduleLauncher.jsp?Format=9; same as above.
- Previous Postings -> triggers getChildren('Last3Postings'); requires lastPostings == VIEW.
- Change resource -> labor_mgmt/resource/Find.jsp path; requires changeAssignmentsResource.

### B. Organizational Structure & Services

#### Companies
Evidence: `SystemSetup.java` – `...put("Companies", CompanyXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.company.xhtml.CompanyXHTMLHandler`
Description: Company master data (inferred).
Secured by: companies (controls listing of companies). Submenus: company list items (each <LI> generated by listOfItems with key prefix 'Company'). No further nested nodes emitted by this handler.

#### Branches
Evidence: `SystemSetup.java` – `...put("Branches", BranchXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.company.branch.xhtml.BranchXHTMLHandler`
Description: Branch organizational units (inferred).
Secured by: branches (controls listing). Submenus (from BranchXHTMLHandler when Id==0): list of Branch entities. Conditional child link: Divisions node appears per branch if divisions > NONE. Visibility rule: if divisions == NONE the branch list items are terminal (LastItem true flag in listOfItems call).

#### Divisions
Evidence: `SystemSetup.java` – `...put("Divisions", DivisionXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.company.division.xhtml.DivisionXHTMLHandler`
Description: Company divisions (inferred).
Secured by: divisions (controls listing). Submenus (from DivisionXHTMLHandler when Id==0): list of Division entities. Conditional child link: Departments node per division if departments > NONE. If departments == NONE, the division list items are terminal.

#### Departments
Evidence: `SystemSetup.java` – `...put("Departments", DepartmentXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.company.dept.xhtml.DepartmentXHTMLHandler`
Description: Department master data (inferred).
Secured by: departments (controls listing). Submenus: department entities only; no further child generation in first-level handler logic (no conditional lower hierarchy shown here).

#### Groups
Evidence: `SystemSetup.java` – `...put("Groups", GroupXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.group.xhtml.GroupXHTMLHandler`
Description: Generic grouping (semantics not shown).
Secured by: Unknown

#### Services
Evidence: `SystemSetup.java` – `...put("Services", ServiceXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.group.service.xhtml.ServiceXHTMLHandler`
Description: Service definitions (inferred).
Secured by: Unknown

#### Packages
Evidence: `SystemSetup.java` – `...put("Packages", PackageXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.group.packages.xhtml.PackageXHTMLHandler`
Description: Service/resource package definitions (inferred).
Secured by: Unknown

### C. Human Resources, Users & Skills

#### Users
Evidence: `SystemSetup.java` – `...put("Users", UserXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.user.xhtml.UserXHTMLHandler`
Description: User account management.
Secured by: users (Security.getUsers()). Submenus (UserXHTMLHandler):
- Find user (Find link) -> requires users (any level; always shown when parentId==0).
- Add User -> shown only when users == EDIT.
- Recently loaded users list -> listOfItems(users permission, lastLoadedUsers(userId, companyId)).
- Users (child under a specific User Group) -> when expanding a Security Group node (from UserGroups) passes parentId group id; list items gated at Security.EDIT constant.

#### UserGroups
Evidence: `SystemSetup.java` – `...put("UserGroups", UserGroupXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.usergroup.xhtml.UserGroupXHTMLHandler`
Description: User grouping / roles (inferred).
Secured by: securityGroups (controls listing of user/security groups). Submenus (UserGroupXHTMLHandler):
- Security Group list -> listOfItems(securityGroups, parentId=0). Each group may expose a Users child link if users > NONE (counts users via CountUsersInUserGroup stored proc).
- Users child link per group -> requires users > NONE; leads to Users handler with parentId=groupId.

#### ManagerPools
Evidence: `SystemSetup.java` – `...put("ManagerPools", ResourceManagersPoolXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.resourcemanagers.xhtml.ResourceManagersPoolXHTMLHandler`
Description: Pools of resource managers (inferred).
Secured by: Unknown

#### Trainings
Evidence: `SystemSetup.java` – `...put("Trainings", TrainingXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.training.xhtml.TrainingXHTMLHandler`
Description: Training catalog (inferred).
Secured by: training (controls listing). Submenus: Training entities list (Id==0) only; no deeper nodes.

#### EmployeeTypes
Evidence: `SystemSetup.java` – `...put("EmployeeTypes", EmployeeTypeXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.employeetype.xhtml.EmployeeTypeXHTMLHandler`
Description: Employee classification (inferred).
Secured by: implicit EDIT level inside handler (uses Security.EDIT constant directly for list items). Submenus: Employee type entities list (Id==0), no deeper nodes. Note: Unlike others, does not call a specific security.getEmployeeTypes(); uses global edit capability for maintenance.

#### TkUnions
Evidence: `SystemSetup.java` – `...put("TkUnions", TkUnionXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.tkunion.xhtml.TkUnionXHTMLHandler`
Description: Union tracking (inferred).
Secured by: Unknown

### D. Resource & Collection Management

#### Resources
Evidence: `SystemSetup.java` – `...put("Resources", ResourceXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.dsl.resources.xhtml.ResourceXHTMLHandler`
Description: Core resource entities (inferred).
Secured by: resources (controls listing). Additional report access gated by resourcesReports (adds Reports node when > NONE). Submenus (ResourceXHTMLHandler):
- Find Resource (Find link).
- Recent Resources list -> listOfItems(resources, lastUsedCompany(...)).
- Reports (virtual child) -> appears only if resourcesReports > NONE; loads key 'Reports'.

#### ResourceCollections
Evidence: `SystemSetup.java` – `...put("ResourceCollections", ResourcesCollectionXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.collections.resource.xhtml.ResourcesCollectionXHTMLHandler`
Description: Groupings of resources (inferred).
Secured by: Unknown

#### ServiceCollections
Evidence: `SystemSetup.java` – `...put("ServiceCollections", ServicesCollectionXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.collections.services.xhtml.ServicesCollectionXHTMLHandler`
Description: Groupings of services (inferred).
Secured by: Unknown

#### Location
Evidence: `SystemSetup.java` – `...put("Location", ResourceMaterialXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.dsl.resources.material.xhtml.ResourceMaterialXHTMLHandler`
Description: Location-related resource materials (inferred).
Secured by: none (listOfItems called with Security.NONE constant). Submenus: Material resource items (ResourceMaterialXHTMLHandler) generated from byLocation(parentId); no deeper authorized nodes.

#### Categories
Evidence: `SystemSetup.java` – `...put("Categories", LocationXHMTLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.location.xhtml.LocationXHMTLHandler`
Description: NOTE mismatch (Location handler). Requires validation.
Secured by: library (uses security.getLibrary() for list items). Submenus (LocationXHMTLHandler when Id==0): list of Locations (listOfItems(library,...)). Each Location item (Id!=0) exposes a child link to 'Location' (Material Resources) regardless of additional permission; permission gating already applied at top-level listing via library.

#### Library
Evidence: `SystemSetup.java` – `...put("Library", CategoryXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.category.xhtml.CategoryXHTMLHandler`
Description: Category/Library taxonomy; mismatch with Categories above (requires validation).
Secured by: library (security.getLibrary()). Submenus (CategoryXHTMLHandler):
- Category list -> listOfItems(library,...).
- For each Category (Id!=0) adds child link to 'Categories' which actually points to Location handler (label 'Location'). This creates cross-linking between Library and Categories keys.

#### RCollectionsVP
Evidence: `SystemSetup.java` – `...put("RCollectionsVP", RCollectionVPXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.collections.xhtml.RCollectionVPXHTMLHandler`
Description: Resource collection variant/perspective (VP meaning not defined).
Secured by: Unknown

#### Processes
Evidence: `SystemSetup.java` – `...put("Processes", ProcessXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.process.xhtml.ProcessXHTMLHandler`
Description: Generic process definitions (inferred).
Secured by: Unknown

### E. Time, Calendar & Scheduling Configuration

#### DayTypes
Evidence: `SystemSetup.java` – `...put("DayTypes", DayTypeXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.daytype.xhtml.DayTypeXHTMLHandler`
Description: Day classification (inferred).
Secured by: dayTypes (uses `security.getDayTypes()` in `getChildren`).
Submenus (DayTypeXHTMLHandler):
- Day type list (Id==0) -> listOfItems(security.getDayTypes(), label "Day type"). No conditional deeper nodes emitted by this handler.
Visibility logic: Node rendered only when user has dayTypes > Security.NONE (listOfItems gating). EDIT level (3) enables Add links inside JSP forms (observed in `DayTypePenalties.jsp`).

#### DaysRulesGroups
Evidence: `SystemSetup.java` – `...put("DaysRulesGroups", DayRequestXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.daysrequest.xhtml.DayRequestXHTMLHandler`
Description: Day off rules grouping entities.
Secured by: daysOffRulesGroups (uses `security.getDaysOffRulesGroups()`).
Submenus: Day off rules group list (Id==0) -> listOfItems(security.getDaysOffRulesGroups(), label "Day off rules group"). No additional child links produced by handler.
Visibility logic: Add links available at EDIT level inside JSP (`RulesDetails.jsp`).

#### TKHolidays
Evidence: `SystemSetup.java` – `...put("TKHolidays", TKHolidaysXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.TKHoliday.xhtml.TKHolidaysXHTMLHandler`
Description: Holiday definitions.
Secured by: timeZones for top-level listing (handler comment notes default). Child expansion conditional on GMT offsets permission (`security.getGMTOffsets()`).
Submenus (TKHolidaysXHTMLHandler):
- Holiday list (Id==0) -> listOfItems(security.getTimeZones(), label "Holiday", LastItem flag depends on GMTOffsets permission).
- Holiday Occurrences link (Id!=0) -> adds `<A ... onclick=getChildren('HolidaysOcurrences')>` only if `security.getGMTOffsets() > Security.NONE`.
Visibility logic: Without GMTOffsets permission, individual Holiday nodes are terminal.

#### HolidaysOcurrences
Evidence: `SystemSetup.java` – `...put("HolidaysOcurrences", HolidaysOcurrencesXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.holidayocurrences.xhtml.HolidaysOcurrencesXHTMLHandler`
Description: Occurrence instances for a specific holiday.
Secured by: gmtOffsets (uses `security.getGMTOffsets()` in listing call).
Submenus: Holiday Occurrence list (Id==0) -> listOfHolidaysOcurrences(security.getGMTOffsets(), label "Holiday Occurrence"). No deeper nodes.
Visibility logic: EDIT level shows Add occurrence link (checks `security == Security.EDIT`).

#### TimeZones
Evidence: `SystemSetup.java` – `...put("TimeZones", TimeZoneXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.timezone.xhtml.TimeZoneXHTMLHandler`
Description: Time zone configuration.
Secured by: timeZones (for listing), plus conditional gmtOffsets for child link.
Submenus (TimeZoneXHTMLHandler):
- Time Zone list (Id==0) -> listOfItems(security.getTimeZones(), label "Time Zone", LastItem flag true when user lacks GMTOffsets permission).
- GMT Offsets child link (Id!=0 and `security.getGMTOffsets() > Security.NONE`) -> adds node loading key 'GMTOffsets'.
Visibility logic: GMTOffsets permission toggles presence of nested link; without it timezone entries are LastItem.

#### GMTOffsets
Evidence: `SystemSetup.java` – `...put("GMTOffsets", GMTOffsetXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.timezone.gmtoffset.xhtml.GMTOffsetXHTMLHandler`
Description: Date/time offset snapshots tied to a specific time zone.
Secured by: gmtOffsets (uses `security.getGMTOffsets()`; Add link only at EDIT level inside listOfGMTOffsets).
Submenus: GMT Offset instances (Id==0) -> listOfGMTOffsets(security.getGMTOffsets(), label "GMT offset"). No further nesting.
Visibility logic: If user has EDIT, an 'Add GMT offset' menu entry (MenuAdd) is rendered.

#### OvertimeTypes
Evidence: `SystemSetup.java` – `...put("OvertimeTypes", OverTimeTypeXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.overTime.xhtml.OverTimeTypeXHTMLHandler`
Description: Overtime classification catalog.
Secured by: overTimeCatalog (uses `security.getOverTimeCatalog()`).
Submenus: Overtime Type list (Id==0) -> listOfItems(security.getOverTimeCatalog(), label "Overtime Type"). No deeper nodes.
Visibility logic: Add link appears when overTimeCatalog == Security.EDIT (observed via standard listOfItems pattern and security options in UserGroup security config).

#### Penalties
Evidence: `SystemSetup.java` – `...put("Penalties", PenaltyXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.penalty.xhtml.PenaltyXHTMLHandler`
Description: Penalty rules catalog.
Secured by: penalties (uses `security.getPenalties()`).
Submenus: Penalty list (Id==0) -> listOfItems(security.getPenalties(), label "Penalty"). No child link emission.
Visibility logic: EDIT level allows Add (observed in related JSP, not in handler directly—listOfItems handles Add when security==EDIT).

#### ActivityFlags
Evidence: `SystemSetup.java` – `...put("ActivityFlags", ActivityFlagXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.activityflag.xhtml.ActivityFlagXHTMLHandler`
Description: Activity flag configuration.
Secured by: activityFlag (uses `security.getActivityFlag()`).
Submenus: Activity Flag list (Id==0) -> listOfItems(security.getActivityFlag(), label "Activity Flag"). No deeper nodes.
Visibility logic: EDIT level enables Add link via listOfItems.

### F. Contracts & Agreements

#### Contracts
Evidence: `SystemSetup.java` – `...put("Contracts", ContractXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.contract.xhtml.ContractXHTMLHandler`
Description: Contract records (inferred).
Secured by: contracts (uses `security.getContracts()` when `objName` != `ContractGroups`).
Submenus (ContractXHTMLHandler – Contracts path, Id==0):
- Contract list -> `listOfItems(security.getContracts(), "Contract", ...)` (LastItem true when `security.getRulesGroups()==Security.NONE`).
Child links (Id != 0):
- Rules groups -> added only if `security.getRulesGroups() > Security.NONE` (loads key `ContractGroups`).

#### ContractGroups
Evidence: `SystemSetup.java` – `...put("ContractGroups", ContractXHTMLHandler.xhtmlHandlerObject());`
Handler: `ContractXHTMLHandler`
Description: Grouping of contracts / rules groups (inferred).
Secured by: rulesGroups (uses `security.getRulesGroups()` when `objName == "ContractGroups"`).
Submenus (Id==0):
- Rules group list -> `listOfItems(security.getRulesGroups(), "Rules group", ...)` (LastItem always true for each group; deeper child link appears only from Contracts context, not here).

#### ContractsRevisions
Evidence: `SystemSetup.java` – `...put("ContractsRevisions", ContractsRevisionXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.contractrevision.xhtml.ContractsRevisionXHTMLHandler`
Description: Contract revision records.
Secured by: rulesGroups (listing gated by `security.getRulesGroups()`).
Submenus (Id==0):
- Contract Revision list -> `listOfContractRevisions(security.getRulesGroups(),...)`; Add link when permission == EDIT.

#### Agreements
Evidence: `SystemSetup.java` – `...put("Agreements", AgreementsXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.agreement.xhtml.AgreementsXHTMLHandler`
Description: Agreement / contract adjuncts.
Secured by: contracts (top-level list uses `security.getContracts()`), with conditional dependency on rulesGroups for child link.
Submenus:
- Agreement list (Id==0) -> `listOfItems(security.getContracts(),"Agreement",...)` (LastItem when `security.getRulesGroups()==Security.NONE`).
- Contracts (child link, Id!=0) -> appears only if `security.getRulesGroups() > Security.NONE` (loads key `TkContracts`).

#### TkContracts
Evidence: `SystemSetup.java` – `...put("TkContracts", TkContractsXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.tkcontract.xhtml.TkContractsXHTMLHandler`
Description: Timekeeper contracts hierarchy.
Secured by: rulesGroups (uses `security.getRulesGroups()` for listing and child link gating).
Submenus:
- Contract list (Id==0) -> `listOfItems(security.getRulesGroups(), "Contract", ...)` (LastItem true when user lacks rulesGroups EDIT; Add shown only at EDIT level via listOfItems standard behavior).
- Contracts Revisions (child link, Id!=0) -> appears only if `security.getRulesGroups() > Security.NONE` (loads key `ContractsRevisions`).

Permission Dependency Chain (Contracts domain):
contracts controls visibility of Contracts & Agreements lists; rulesGroups unlocks nested: Rules groups (from Contracts), Contracts (from Agreements), Contracts Revisions (from TkContracts), and contract revision listing.

### G. Payroll & Financial Codes

#### EarningCodes
Evidence: `SystemSetup.java` – `...put("EarningCodes", EarningCodesXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.earningcodes.xhtml.EarningCodesXHTMLHandler`
Description: Earning/payroll codes.
Secured by: earningCodes (uses `security.getEarningCodes()`).
Submenus (Id==0):
- Earning Codes list -> `listOfItems(security.getEarningCodes(), "EarningCodes", ...)` (Add at EDIT).

#### PayTransactions
Evidence: `SystemSetup.java` – `...put("PayTransactions", PayTransactionsXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.paytransaction.xhtml.PayTransactionsXHTMLHandler`
Description: Payroll transaction records.
Secured by: (anomaly) timeZones (handler code calls `listOfItems(security.getTimeZones(), "PayTransactions", ...)` instead of `security.getPayTransactions()`).
Anomaly Note: Security.java defines `getPayTransactions()`; UserGroup security UI sets PayTransactions level, but handler does NOT reference it. Potential defect or intentional reuse of timeZones permission. Recommend verification and possible remediation.
Submenus (Id==0):
- Pay Transactions list -> gated indirectly by timeZones permission.

### H. Codes, Indicators & Taxonomy

#### Indicators
Evidence: `SystemSetup.java` – `...put("Indicators", IndicatorsXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.codegroup.indicators.xhtml.IndicatorsXHTMLHandler`
Description: Indicator definitions.
Secured by: indicators (uses `security.getIndicators()` in `listOfIndicators`).
Submenus (Id==0):
- Indicator list -> `listOfIndicators(security.getIndicators(), ...)` (Add at EDIT).

#### IndicatorsCodeGroups
Evidence: `SystemSetup.java` – `...put("IndicatorsCodeGroups", CodeGroupXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.codegroup.xhtml.CodeGroupXHTMLHandler`
Description: Indicator-associated code groups.
Secured by: indicators (uses `security.getIndicators()` for both group listing and child link condition).
Submenus:
- Code Group list (Id==0) -> `listOfItems(security.getIndicators(), "IndicatorsCodeGroup", ...)`.
- Child links (Id!=0 and indicators > NONE):
  - Indicators (loads key `Indicators`).
  - Codes (loads key `Codes`).

#### Codes
Evidence: `SystemSetup.java` – `...put("Codes", CodeXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.codegroup.code.xhtml.CodeXHTMLHandler`
Description: Individual codes within a group.
Secured by: indicators (handler uses `security.getIndicators()` for listing & Add gating).
Submenus (Id==0):
- Code list -> `listOfCodes(security.getIndicators(), ...)` (Add at EDIT).

#### ClientTypes
Evidence: `SystemSetup.java` – `...put("ClientTypes", ClientTypeXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.clienttype.xhtml.ClientTypeXHTMLHandler`
Description: Client category taxonomy.
Secured by: (hardcoded) EDIT – handler calls `listOfItems(Security.EDIT, ...)` and fetches list with `byCompany(Security.YES, Security.EDIT,0)`; no direct `security.getClientTypes()`.
Submenus (Id==0):
- Client type list -> always shows Add option (since constant EDIT passed) for any user who can load menu; upstream menu visibility likely governed elsewhere.

(Reaffirm) EmployeeTypes & ActivityFlags covered in earlier sections with explicit security (EmployeeTypes uses constant EDIT; ActivityFlags uses `security.getActivityFlag()`).

### I. Workflow & Approvals

#### SecondLevelApprovals
Evidence: `SystemSetup.java` – `...put("SecondLevelApprovals", SecondLevelApprovalXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.secondLevelApproval.xhtml.SecondLevelApprovalXHTMLHandler`
Description: Second-level approver pools.
Secured by: secondLevelApprovals (uses `security.getSecondLevelApprovals()`).
Submenus (Id==0):
- Approvers Pool list -> `listOfItems(security.getSecondLevelApprovals(), "Approvers Pool", ...)` (Add at EDIT).

### J. Scheduler (Quartz) Management

#### QuartzCP
Evidence: `SystemSetup.java` – `...put("QuartzCP", QuartzCPXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.quartzcp.xhtml.QuartzCPXHTMLHandler`
Description: Quartz scheduler control panel root.
Secured by: quartzControlPanel (visibility + child insertion when `security.getQuartzControlPanel() > Security.NONE`).
Submenus (Id==0):
- Job Groups (loads `QuartzJobGroup`).
- Schedules (loads `QuartzSchedule`).
- Feeds Status (direct link with time range params) – terminal node.

#### QuartzSchedule
Evidence: `SystemSetup.java` – `...put("QuartzSchedule", QuartzScheduleXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.quartzcp.schedule.xhtml.QuartzScheduleXHTMLHandler`
Description: Schedule definitions.
Secured by: quartzControlPanel (uses `security.getQuartzControlPanel()`).
Submenus (Id==0):
- Schedule list -> `listOfItems(security.getQuartzControlPanel(), "Schedule", ...)` (Add at EDIT).

#### QuartzJobGroup
Evidence: `SystemSetup.java` – `...put("QuartzJobGroup", QuartzJobGroupXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.quartzcp.jobgroup.xhtml.QuartzJobGroupXHTMLHandler`
Description: Job grouping container.
Secured by: quartzControlPanel.
Submenus:
- Job Group list (Id==0) -> `listOfItems(security.getQuartzControlPanel(), "Job Group", ...)`.
- Jobs (child link, Id!=0) -> appears only if quartzControlPanel > NONE (loads key `QuartzJob`).

#### QuartzJob
Evidence: `SystemSetup.java` – `...put("QuartzJob", QuartzJobXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.quartzcp.jobgroup.job.xhtml.QuartzJobXHTMLHandler`
Description: Individual jobs.
Secured by: quartzControlPanel.
Submenus:
- Job list (Id==0) -> `listOfItems(security.getQuartzControlPanel(), "Job", ...)`.
- Assigned Schedules (child link, Id!=0) -> appears when quartzControlPanel > NONE (loads key `QuartzJobSchedule`).

#### QuartzJobSchedule
Evidence: `SystemSetup.java` – `...put("QuartzJobSchedule", QuartzJobSchedulesXHTMLHandler.xhtmlHandlerObject());`
Handler: `com.nbcuni.dcss.storm.gsl.quartzcp.jobgroup.job.xhtml.QuartzJobSchedulesXHTMLHandler`
Description: Schedules assigned to a specific job.
Secured by: quartzControlPanel (parent gating; list call uses security value 0 to suppress Add).
Submenus (Id==0):
- Assigned Schedule list -> `listOfItems(0, "", ...)` (no Add regardless of permission).

Quartz Permission Hierarchy Summary:
Single permission `quartzControlPanel` gates entire scheduler tree. Child nodes do not introduce additional permission checks; they rely exclusively on root permission.

---
## Items Previously Listed But Not Backed by Direct `xhtmlHandlers.put` in Inspected Files
Earlier drafts mentioned higher-level conceptual labels (e.g. Reports, Accounting, System, Resources as a top-level category). Only the concrete keys above are confirmed by direct handler registration. To enumerate report variants (Client Costing, Days Off, etc.) one would need to inspect additional JSPs under `Deployment/Storm2/WebContent/Reports/*` – this document avoids claiming dynamic handler-backed keys absent explicit registration lines.

## Gaps / Next Validation Steps
- Extract per-handler internal permission constants / numeric levels (next pass: inspect each handler body for `security.` method calls or numeric comparisons, e.g. `if(security.get...` or `if(securityLevel >= ...)`).
- Identify shared security constants (e.g., GetDayTypeSecurity) and map to handlers.
- Distinguish between node visibility vs row filtering inside handlers.
- Confirm any static JSP-level guards (scriptlet security checks) for static menu items (currently marked None).

## Summary
Total distinct dynamic object keys discovered (first-level): 57 (grouped; each presented as its own subsection). Security review pass 1: all dynamic handlers accept a `Security` parameter but specific permission values remain Unknown pending deeper code inspection.
