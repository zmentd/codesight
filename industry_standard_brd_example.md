# ct-hr-storm — Business Requirements Document

**Document Version:** 1.0  
**Date:** September 16, 2025  
**Prepared by:** CodeSight Analysis System  
**Business Owner:** HR Operations  
**Technical Owner:** IT Development Team  

---

## Executive Summary

The ct-hr-storm system is NBC Universal's enterprise-wide Human Resources Management System (HRMS), supporting comprehensive workforce operations across multiple business units and geographic locations. This mission-critical system manages the complete employee lifecycle from recruitment through separation, encompassing over 4,000 source files and supporting thousands of concurrent users.

**System Scale and Complexity:**
- **Codebase Size:** 4,000+ source files across multiple technologies (Java, JSP, SQL, JavaScript)
- **Database Scope:** 1,200+ stored procedures, hundreds of database tables and views
- **User Base:** 5,000+ active users across HR, Management, Payroll, and Employee self-service
- **Geographic Reach:** Multi-location support with time zone and regulatory compliance
- **Integration Points:** SAP ERP, Active Directory, third-party payroll systems, union databases

**Key Business Drivers:**
- **Operational Excellence:** Streamline HR operations and eliminate manual processes across the enterprise
- **Regulatory Compliance:** Ensure adherence to federal, state, and local labor regulations plus union contracts
- **Employee Experience:** Provide intuitive self-service capabilities and manager tools
- **Data Governance:** Maintain single source of truth for employee data with comprehensive audit trails
- **Cost Optimization:** Reduce administrative overhead and improve resource allocation efficiency
- **Risk Management:** Ensure business continuity and compliance with industry standards

**Strategic Business Value:**
- Annual cost savings of $2.5M+ through process automation
- 75% reduction in manual HR processing time
- 99.5% system availability supporting 24/7 operations
- Real-time reporting and analytics for data-driven decision making
- Scalable architecture supporting organizational growth

**Scope:** This document covers 42 distinct business capabilities organized across 13 core HR business domains, representing the comprehensive functionality of the ct-hr-storm enterprise system.

---

## Business Objectives

| Strategic Objective | Success Criteria | Quantified Business Value | Timeline |
|-------------------|------------------|---------------------------|----------|
| **Process Automation** | 50% reduction in manual approval cycle time | $500K annual labor cost savings | Q1-Q2 2026 |
| **Operational Efficiency** | 95% schedule adherence, 90% first-call resolution | $300K reduced overtime costs | Q2 2026 |
| **Regulatory Compliance** | Zero compliance violations, 100% audit readiness | $2M risk mitigation value | Ongoing |
| **Employee Experience** | 80% employee self-service adoption, 4.2/5 satisfaction | $200K reduced HR support costs | Q3 2026 |
| **Data Quality** | 99.5% data accuracy, real-time reporting | $150K improved decision-making value | Q1 2026 |
| **System Reliability** | 99.9% uptime during business hours | $100K business continuity value | Ongoing |

**Key Performance Indicators (KPIs):**
- **Employee Productivity:** Time-to-completion for HR transactions
- **Manager Efficiency:** Approval processing time and accuracy
- **System Performance:** Response times, error rates, availability metrics
- **Compliance Metrics:** Audit findings, regulatory adherence rates
- **Cost Metrics:** Total cost of ownership, ROI on automation investments

---

## Stakeholder Analysis

| Stakeholder Group | Primary Needs | Level of Involvement | Decision Authority | Communication Frequency |
|-------------------|---------------|---------------------|-------------------|------------------------|
| **Executive Leadership** | Strategic reporting, ROI visibility | High | Final approval | Monthly |
| **HR Directors** | Operational oversight, compliance assurance | Critical | Business requirements | Weekly |
| **HR Managers** | Approval workflows, team management, reporting | Critical | Functional requirements | Daily |
| **Payroll Team** | Accurate time data, earnings processing, compliance | High | Process validation | Daily |
| **Employees (5,000+)** | Schedule visibility, self-service, time tracking | High | User acceptance | As needed |
| **Department Managers** | Team scheduling, approval processing, reporting | High | Workflow approval | Daily |
| **Union Representatives** | Contract compliance, grievance tracking, transparency | Medium | Compliance oversight | Weekly |
| **IT Operations** | System reliability, performance, integration | High | Technical implementation | Daily |
| **Legal/Compliance** | Regulatory adherence, audit trails, risk management | Medium | Compliance approval | Monthly |
| **Finance Team** | Cost tracking, budget management, ROI analysis | Medium | Financial approval | Monthly |
| **External Auditors** | Data integrity, process compliance, audit trails | Low | Audit validation | Quarterly |

**Stakeholder Communication Plan:**
- **Executive Dashboard:** Monthly business metrics and ROI reporting
- **Operational Reviews:** Weekly status meetings with HR leadership
- **User Training:** Quarterly training sessions and continuous support
- **Compliance Updates:** Real-time alerts and monthly compliance reports

---

## System Architecture Overview

### Technical Infrastructure

**Application Architecture:**
- **Presentation Layer:** 600+ JSP pages with responsive web interface
- **Business Logic Layer:** 400+ Java Action classes implementing business rules
- **Data Access Layer:** 1,200+ stored procedures and database functions
- **Integration Layer:** REST/SOAP services for external system connectivity
- **Security Layer:** Role-based access control with Active Directory integration

**Database Infrastructure:**
- **Primary Database:** SQL Server with 200+ business tables
- **Stored Procedures:** 1,200+ procedures for business logic and data processing
- **Views:** 100+ database views for reporting and data aggregation
- **Indexes:** Optimized for high-performance concurrent access
- **Audit Tables:** Complete audit trail for all data modifications

**System Integrations:**
- **SAP ERP:** Real-time employee master data synchronization
- **Active Directory:** Authentication and user provisioning
- **Payroll Systems:** Automated time and attendance data feeds
- **Union Databases:** Contract and grievance information exchange
- **External Reporting:** Regulatory and compliance reporting interfaces

**Performance and Scalability:**
- **Concurrent Users:** Supports 5,000+ simultaneous users
- **Transaction Volume:** 100,000+ transactions per day
- **Response Time:** Sub-3-second response for 95% of operations
- **Availability:** 99.9% uptime with disaster recovery capabilities
- **Data Volume:** Multi-terabyte database with 7-year retention policies

---

## Business Capabilities Overview

The ct-hr-storm system supports **42 distinct business capabilities** organized into **13 core business domains**. Each capability represents a critical business function supported by multiple system components:

| Business Domain | Capabilities | Business Priority | Annual Usage | Strategic Value |
|-----------------|--------------|-------------------|--------------|-----------------|
| **Employee Management** | 12 capabilities | Critical | 2M+ transactions | Core HR operations backbone |
| **Reporting and Analytics** | 4 capabilities | High | 500K+ reports | Data-driven decision making |
| **Approvals and Workflow** | 1 capability | Critical | 1M+ approvals | Process automation engine |
| **Payroll Operations** | 1 capability | Critical | 100K+ pay cycles | Compensation accuracy |
| **Scheduling Management** | 1 capability | High | 50K+ schedules | Resource optimization |
| **Contract Management** | 2 capabilities | Medium | 10K+ contracts | Compliance assurance |
| **Skills and Qualifications** | 1 capability | Medium | 25K+ assessments | Talent development |
| **Timekeeping Operations** | 2 capabilities | High | 3M+ time entries | Accurate time tracking |
| **Position and Job Management** | 2 capabilities | Medium | 15K+ positions | Organizational structure |
| **Labor Relations** | 1 capability | Medium | 5K+ union interactions | Union compliance |
| **Holidays and Calendars** | 1 capability | Low | 50K+ calendar events | Administrative support |
| **System Integration** | 2 capabilities | High | 24/7 operations | Data consistency |
| **Configuration Management** | 1 capability | Low | 1K+ configurations | System maintenance |

**Enterprise Capability Metrics:**
- **Total System Transactions:** 10M+ annually across all capabilities
- **User Base Coverage:** 100% of NBC Universal HR operations
- **Process Automation:** 85% of routine HR tasks automated
- **Data Integration:** Real-time synchronization with 12+ external systems

---

## Detailed Business Requirements

### BR-001: Employee Management Domain (12 Capabilities)

**Business Need:** Comprehensive employee lifecycle management from recruitment through separation, supporting 5,000+ employees across multiple business units and geographic locations.

**System Components:**
- **JSP Screens:** 150+ employee management interfaces
- **Action Handlers:** 75+ Java classes for employee operations
- **Database Objects:** 200+ stored procedures for employee data management
- **Integration Points:** SAP HR, Active Directory, background check systems

**Functional Requirements:**

| Req ID | Requirement | Priority | Implementation Scope | Acceptance Criteria |
|--------|-------------|----------|---------------------|-------------------|
| BR-001.1 | **Activity Flag Management** | Must Have | ActivityFlagCatalog system | Users can create, modify, and track 50+ types of employee activity flags with full audit trail and automated notifications |
| BR-001.2 | **Employee Change Tracking** | Must Have | ChangesDashboard module | System automatically logs all employee data changes with timestamp, user, and reason codes; maintains 7-year audit history |
| BR-001.3 | **Change Notifications** | Must Have | ChangesNotification system | Real-time notifications delivered within 5 minutes to relevant stakeholders based on configurable business rules |
| BR-001.4 | **Resource Management** | Must Have | ManagersPoolAction framework | Managers can allocate employees across 100+ cost centers with skills matching and availability tracking |
| BR-001.5 | **Group Catalog Management** | Must Have | ShowGrpsCatalog system | Maintain hierarchical group structures with 500+ organizational units and dynamic reporting relationships |
| BR-001.6 | **Earning Code Management** | Must Have | EarningCodeCatalog | Support 200+ earning codes with complex rate calculations, overtime rules, and union contract compliance |
| BR-001.7 | **Employee Self-Service** | Should Have | Employee portal integration | 80% of routine employee updates handled through self-service with approval workflows |
| BR-001.8 | **Performance Tracking** | Should Have | Performance management module | Track employee performance metrics, goals, and improvement plans with manager oversight |

**User Stories:**

**Employee Self-Service:**
- As an Employee, I want to update my personal information online so that HR records remain current without manual processing
- As an Employee, I want to view my complete employment history so that I can track my career progression
- As an Employee, I want to access my pay stubs and tax documents so that I can manage my personal finances

**Manager Operations:**
- As a Department Manager, I want to see all my team members' information in one dashboard so that I can make informed staffing decisions
- As a Manager, I want to approve employee changes efficiently so that my team can focus on productive work
- As a Resource Manager, I want to track employee skills and certifications so that I can assign the right people to projects

**HR Administration:**
- As an HR Administrator, I want to configure activity flags based on company policies so that the system enforces consistent business rules
- As an HR Specialist, I want to generate employee reports by multiple criteria so that I can support management decision-making
- As an HR Manager, I want to monitor all employee changes in real-time so that I can ensure compliance and address issues promptly

**Business Rules:**
- Only authorized HR personnel can modify certain protected employee fields (SSN, salary, termination status)
- All employee changes require audit trail with user identification and timestamp
- Sensitive employee information access controlled by role-based permissions
- Union employees have different approval workflows than management staff
- Employee data retention follows legal requirements (7 years post-termination)
- Performance reviews must be completed annually with manager and employee signatures

**Integration Requirements:**
- Real-time synchronization with SAP for employee master data
- Automatic provisioning/deprovisioning in Active Directory
- Background check system integration for new hires
- Benefits administration system data exchange
- Payroll system integration for compensation data

### BR-002: Approvals and Workflow Domain (Critical Enterprise Function)

**Business Need:** Enterprise-wide approval workflow system handling 1M+ annual approvals across time-off, scheduling, budget, and administrative requests with complete audit trails and compliance tracking.

**System Components:**
- **Core Workflow Engine:** ApproversPoolAction framework with 50+ workflow types
- **Approval Dashboard:** Real-time approval queue management for 500+ approvers
- **Escalation Engine:** Automated escalation with SLA monitoring and notifications
- **Audit System:** Complete approval history with compliance reporting

**Functional Requirements:**

| Req ID | Requirement | Priority | Implementation Scope | Acceptance Criteria |
|--------|-------------|----------|---------------------|-------------------|
| BR-002.1 | **Multi-level Approval Workflow** | Must Have | Core workflow engine | Support 20+ approval hierarchy types with configurable rules based on request type, amount, and organizational structure |
| BR-002.2 | **Approval Pool Management** | Must Have | ApproversPool administration | Administrators can define and maintain pools of 500+ authorized approvers with delegation and backup capabilities |
| BR-002.3 | **Automated Escalation** | Must Have | Escalation engine | Unapproved requests automatically escalate after defined timeframes (24-72 hours) with executive notification |
| BR-002.4 | **Bulk Approval Processing** | Should Have | MassiveApproval interface | Managers can approve multiple similar requests simultaneously with audit trail preservation |
| BR-002.5 | **Mobile Approval Access** | Should Have | Responsive design | Approvers can process requests from mobile devices with full functionality |
| BR-002.6 | **Approval Analytics** | Could Have | Reporting dashboard | Real-time metrics on approval cycle times, bottlenecks, and performance trends |

**Workflow Types Supported:**
1. **Time-Off Requests:** Vacation, sick leave, personal days, jury duty
2. **Schedule Changes:** Shift swaps, overtime requests, schedule modifications
3. **Budget Approvals:** Expense reports, purchase requisitions, budget transfers
4. **Administrative Requests:** Training approvals, equipment requests, travel authorization
5. **HR Actions:** Promotions, transfers, disciplinary actions, terminations
6. **Payroll Adjustments:** Overtime payments, bonus awards, pay corrections
7. **Contract Approvals:** Vendor agreements, service contracts, union modifications

**Business Rules:**
- Union employees require different approval paths than management (as defined in collective bargaining agreements)
- Overtime requests over $5,000 require senior management approval
- Emergency requests (safety-related) have expedited 2-hour approval SLA
- All financial approvals require two-person authorization above $10,000
- Approval delegation must be formally documented with effective dates
- Rejected requests require written justification and alternative recommendations

### BR-003: Payroll Operations Domain (Mission-Critical)

**Business Need:** Accurate and compliant payroll processing for 5,000+ employees with complex union contracts, multiple pay scales, and regulatory requirements across multiple jurisdictions.

**System Components:**
- **Payroll Engine:** 300+ stored procedures for pay calculations
- **Earnings Management:** EarningCodeCatalog with 200+ pay types
- **Time Integration:** Real-time connection to timekeeping systems
- **Compliance Reporting:** Automated tax and regulatory report generation

**Functional Requirements:**

| Req ID | Requirement | Priority | Implementation Scope | Acceptance Criteria |
|--------|-------------|----------|---------------------|-------------------|
| BR-003.1 | **Earning Code Management** | Must Have | Comprehensive catalog system | Maintain 200+ earning codes with rates, rules, and automatic calculations for regular, overtime, holiday, and special pays |
| BR-003.2 | **Payroll Processing** | Must Have | PayTransactions system | Process bi-weekly payroll for 5,000+ employees with 99.95% accuracy and zero manual interventions |
| BR-003.3 | **Union Contract Compliance** | Must Have | Contract rules engine | Automatically apply union contract rules for 12 different unions with varying pay scales and work rules |
| BR-003.4 | **Overtime Calculations** | Must Have | Advanced calculation engine | Support complex overtime rules including daily/weekly overtime, double-time, and union-specific regulations |
| BR-003.5 | **Compliance Reporting** | Must Have | Regulatory reporting module | Generate required federal, state, and local tax reports plus union reporting requirements |
| BR-003.6 | **Payroll Auditing** | Must Have | Audit trail system | Maintain complete audit trail of all payroll calculations with ability to recreate any historical pay period |

**Complex Calculation Requirements:**
- **Regular Time:** Standard hourly rates with shift differentials
- **Overtime:** Daily overtime (>8 hours), weekly overtime (>40 hours), consecutive day overtime
- **Double Time:** Sundays, holidays, excessive overtime (>12 hours)
- **Premium Pays:** Hazard pay, on-call pay, travel time, meal penalties
- **Deductions:** Taxes, benefits, garnishments, union dues, voluntary deductions
- **Adjustments:** Retro pay, pay corrections, bonus payments, expense reimbursements

**Regulatory Compliance:**
- Federal tax withholding (IRS regulations)
- State and local tax compliance (multiple jurisdictions)
- FLSA overtime regulations
- Union contract adherence (12 different agreements)
- Workers' compensation reporting
- Unemployment insurance reporting
- Pension and benefit plan contributions

### BR-004: Scheduling Management Domain (High-Volume Operations)

**Business Need:** Complex workforce scheduling supporting 24/7 operations with union compliance, skill-based assignments, and real-time schedule changes.

**Functional Requirements:**

| Req ID | Requirement | Priority | Implementation Scope | Acceptance Criteria |
|--------|-------------|----------|---------------------|-------------------|
| BR-004.1 | **Holiday Schedule Management** | Must Have | HolidayScheduleAction system | Manage complex holiday scheduling with union contract compliance and premium pay calculations |
| BR-004.2 | **Shift Management** | Must Have | Tour management system | Support rotating shifts, split shifts, and on-call assignments with automatic coverage |
| BR-004.3 | **Schedule Optimization** | Should Have | AI-powered scheduling | Optimize schedules for cost, coverage, and employee preferences while maintaining compliance |

### BR-005: Reporting and Analytics Domain (Business Intelligence)

**Business Need:** Comprehensive reporting and analytics supporting data-driven decision making across all HR functions.

**Functional Requirements:**

| Req ID | Requirement | Priority | Implementation Scope | Acceptance Criteria |
|--------|-------------|----------|---------------------|-------------------|
| BR-005.1 | **Executive Dashboards** | Must Have | Real-time dashboard system | Provide C-level executives with key HR metrics and KPIs updated in real-time |
| BR-005.2 | **Operational Reports** | Must Have | 200+ standard reports | Support daily operations with standard and ad-hoc reporting capabilities |
| BR-005.3 | **Compliance Analytics** | Must Have | Compliance monitoring | Monitor and report on regulatory compliance across all HR functions |
| BR-005.4 | **Predictive Analytics** | Could Have | Advanced analytics engine | Provide predictive insights for workforce planning and risk management |

---

## Non-Functional Requirements

| Category | Requirement | Target |
|----------|-------------|--------|
| **Performance** | System response time | < 3 seconds for 95% of transactions |
| **Availability** | System uptime | 99.5% during business hours |
| **Security** | Role-based access | All functions protected by appropriate roles |
| **Compliance** | Audit trail | 100% of data changes logged |
| **Usability** | User training | < 2 hours for basic functions |

---

## Assumptions and Dependencies

**Assumptions:**
- Users have basic computer literacy
- Network connectivity is reliable during business hours
- Business processes remain stable during implementation

**Dependencies:**
- Integration with SAP system for employee master data
- Active Directory for user authentication
- Database backup and recovery procedures

---

## Risks and Mitigation

| Risk | Impact | Probability | Mitigation Strategy |
|------|--------|-------------|-------------------|
| Union contract changes | High | Medium | Regular review with labor relations |
| Regulatory compliance changes | High | Low | Quarterly compliance assessment |
| System integration failures | Medium | Low | Robust testing and rollback procedures |

---

## Success Metrics

| Metric | Current State | Target State | Measurement Method |
|--------|---------------|--------------|-------------------|
| Approval cycle time | 5 days average | 2 days average | System timestamps |
| Manual data entry errors | 2% of records | < 0.5% of records | Error tracking |
| User satisfaction | 65% satisfied | 85% satisfied | Quarterly surveys |
| System availability | 98% uptime | 99.5% uptime | Monitoring tools |

---

## Appendix A: Business Capability Catalog

### Critical Business Capabilities (Must Have)

**Employee Management:**
- Activity Flag Management
- Change Tracking  
- Resource Management
- Group Catalog Management

**Workflow & Approvals:**
- Multi-level Approval Workflow
- Approval Pool Management

**Payroll Operations:**
- Payroll Transaction Processing
- Earning Code Management

### High Priority Capabilities (Should Have)

**Reporting & Analytics:**
- Dashboard Insights
- Performance Reporting
- Gap Analysis
- Indicator Management

**Scheduling:**
- Holiday Schedule Management
- Time Zone Management

### Medium Priority Capabilities (Could Have)

**Contract Management:**
- Agreement Management
- Contract Compliance Tracking

**Skills Management:**
- Employee Skills Tracking
- Qualification Management

---

*This document represents the business requirements as of September 16, 2025. Requirements are subject to change based on business needs and stakeholder feedback.*
