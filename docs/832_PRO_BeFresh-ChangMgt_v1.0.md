## Introduction

### Context

This document is the change management procedure of BeFresh. It specifically addresses how the organization controls changes to information processing facilities and systems that affect information security.

### Objectives

The objective of this document is to outline how BeFresh identifies, tests, and approves changes to the information processing facilities of the organization and systems that affect information security.

### Scope

The scope of this document is the same as that of the ISMS.

### Enforcement and reading instructions

This document becomes effective once approved by the MD and published on the ISMS repository (\InfoSec-IN) available to all employees of BeFresh. It will remain in effect until revoked or revised by the Owner or the MD. Do not rely on a printed document but rather check on the official documentation site of BeFresh for the currently applicable version.

The MD’s signature is an official recognition of the mandatory character of this document. It is to be respected by all employees of BeFresh and a failure to comply with the Information Security policy may be considered as a violation of the working contract and result in disciplinary action.

The use of the SIMPLE PRESENT tense or the terms ‘MUST’, ‘MANDATORY’, ‘REQUIRED’, or ‘SHALL’ in a statement means that the statement is considered a formal requirement.

The use of words such as ‘SHOULD’ or the adjective ‘RECOMMENDED’ means that there may be legitimate reasons to disregard the statement, but that the implications of such an exception shall be assessed and fully understood.

The terminology ‘MAY’ or ‘CAN’, or the adjective ‘OPTIONAL’ means that the implementation of the statement is at the discretion of the implementer.

The indication #175W BeFresh-WordTempl refers to the document with the given acronym, here BeFresh-WordTempl. The indication #175W refers to the ISMS document with the given indicator, here 175W, in this case the same document as the reference before.

The indicate #502 refers to a separated document 502 if existent, other wise to the chapter 02 inside document #5.

The text copied by law or other reference is marked in red, and in any case constitutes an obligation.

Control objectives given in ISO are put in bold.

Security measures for reaching these objectives are put in a box.

Specific text for the implementation at BeFresh is highlighted.

### Audience

This document shall be read and applied by all collaborators with responsibility in writing or approving documents within BeFresh.

### Document structure

The remainder of this document is structured as follows:



- Chapter 2 describes change management process.
- Chapter 3 outlines the process of applying changes.

### References

See [2] for all references of type BeFresh-… or with an ISMS document identifier starting with #...

BeFresh, ISMS, Policy, Information Security Policy (BeFresh-InfoSec), #0.

BeFresh, ISMS, Plan, List of documents plan (BeFresh-ListDoc), #0D.

BeFresh, ISMS, Standard, Glossary (BeFresh-Glossary), #0G.

BeFresh, ISMS, Policy, Organizational controls policy (BeFresh-OrgControls), #5.

BeFresh, ISMS, Plan, Roles and responsibilities assignment plan (BeFresh-RoleAssignment), #502.

BeFresh, ISMS, Standard, Asset inventory (BeFresh-AssetInventory), #509A.

BeFresh, ISMS, Standard, Classification standard, (BeFresh-Classification), #512

BeFresh, ISMS, Procedure, Password management (BeFresh-PasswordMgt), #517.

BeFresh, ISMS, Policy, People controls policy (BeFresh-PeopleControls), #6.

BeFresh, ISMS, Policy, Technological controls Policy (BeFresh-TechControls), #8

BeFresh, ISMS, Procedure, Backup management procedure (BeFresh-BackupMgt), #813.

BeFresh, ISMS, Jira ticketing system, (https://befreshlu.atlassian.net/).

BeFresh, ISMS repository, \InfoSec-IN, (BeFresh-ISMS-REPO)

REGULATION (EU) 2016/679 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL of 27 April 2016 on the protection of natural persons regarding the processing of personal data and on the free movement of such data, and repealing Directive 95/46/EC (General Data Protection Regulation)

ISO/IEC 27001:2022(E), Information security, cybersecurity and privacy protection — Information security management systems — Requirements.

ISO/IEC 27002:2022(E), Information security, cybersecurity and privacy protection — Information security controls.

### Acronyms



| #CEO   | Placeholder referring to the Managing director of BeFresh.   |
|--------|--------------------------------------------------------------|
| ICT    | Information and Communication Technology.                    |
| ISMS   | Information Security Management System.                      |
| SMB    | Server Message Block, Microsoft protocol for file exchange.  |

### Glossary

For other descriptions of common terms used in this document, please refer to the general glossary of BeFresh [2].



| Change management                             | Process of controlling and documenting any change in a system to maintain the proper operation of the equipment under control.                                          |
|-----------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Information Security Management System (ISMS) | Part of the overall management system, based on a business risk approach, to establish, implement, operate, monitor, review, maintain and improve information security. |

## Change management

### Change Types

Based on ITILv4, there are three types of change, Standard Change, Normal Change and Emergency Change. Each type is managed differently based on its risk, impact, and urgency.

#### Standard Changes

These are preapproved changes that are low-impact, well known, and documented. Standard changes require a risk assessment and authorization when implemented for the first time, but subsequent implementations can be done without these precautions as long as the change has not been modified.

The following changes examples are considered as Standard Change and are therefore not subject to this procedure:



- antivirus updates;
- vulnerability patching, hot fixes;
- minor software upgrades;
- minor service configuration modifications, e.g. changing port of SSH server.

In case risks are identified later on, the necessary documentation has to be provided.

#### Normal Change

A normal change follows the complete change process, including being scheduled, undergoing a risk assessment, and receiving proper authorization. This category encompasses both minor (low to moderate impact) and major changes (high impact and/or high urgency). Any change that is not categorized as standard or emergency should be treated as a normal change and adhere to the established change management process.

#### Emergency Change

These are changes that are implemented as soon as possible; for example, to resolve an incident or implement a security patch. Emergency changes are not typically included in a change schedule, and the process for assessment and authorization is expedited to ensure they can be implemented quickly. As far as possible, emergency changes should be subject to the same testing, assessment, and authorization as normal changes, but it may be acceptable to defer some documentation until after the change has been implemented, and sometimes it will be necessary to implement the change with less testing due to time constraints. There may also be a separate change authority for emergency changes, typically including a small number of senior managers who understand the business risks involved.

### Change Classification: Major v/s Minor

Changes can also be classified as Major or Minor, depending on their risk, impact, and complexity. This classification applies to both Normal and Emergency changes.

#### Major Change

A major change is characterized by its high risk and significant impact on business processes. This affects:



- the normal performance of an overall system or an application;
- how the product behaves, interfaces with other products;
- user skills and training;
- cost or warranty.

Major changes typically require detailed planning, risk mitigation strategies, and a thorough evaluation of their potential consequences.

#### Minor Change

A minor change involves low risk and limited impact on business processes. These changes:



- may have minor or moderate effects, either direct or indirect;
- typically involve straightforward implementation with a quick rollback strategy, minimizing risks and mitigating any potential disruptions;
- require less oversight compared to major changes, though they still follow the structured change management process;
- does not impact user requirements;
- affects configuration documentation or system process not considered as major change.

### Responsibilities

The CIO or his backup is responsible for:



- approving or rejecting change requests, and taking into account the potential benefits, costs involved, related risks, etc.;
- ensuring that all change requests are managed in line with this procedure;
- installing and testing operational software updates and new implementations;
- maintaining and documenting the configuration details of test environments;
- establishing a roll back strategy in line with the business continuity strategy of the organization;
- communicating on change details to all relevant persons.

The Chief Information Security Officer (CISO) or his backup is responsible for:



- deciding if a change is minor or major;
- in case of a major change, carrying out a risk assessment (MD validation) to identify potential risks and their impacts related to any changes. The CISO (considering the input of the CIO) then identifies the security controls needed in line with the risk management framework Error! Reference source not found. of the organization.

The Managing Director (MD) or his backup is responsible for:



- authorizing any major change to go ahead (following risk assessment) and ensuring final approval.

Note: any change that risks disrupting the customers of BeFresh, and therefore indirectly the business activities of its employees is considered as a major change. Changes not blocking the usability of services are considered as minor changes.

Note: A substitute (sometimes also called backup or deputy) can be any BeFresh employee, e.g. a HoD, but no single employee can assume more than one of the following roles: CISO, CIO or MD. An exception to this rule applies to the Managing Director, who himself can assume two of the aforementioned roles, if necessary.

### Change request

Change requests are made by BeFresh employees (asset manager) using the Jira ticketing system [12]. In addition, necessary changes to the user (Laptop) operating systems may be performed by the CIO or his dedicated substitutes whenever they deem it necessary. Changes to server operating systems and applications follow standard BeFresh change management procedure and have to be documented through a ticket. Formal validation by the CISO or his assistants (especially when the document relates to a chapter for which the assistant is responsible) is required.

The use of the ticketing system ensures that all change requests are logged (regardless of whether the change is accepted or rejected).

Standard change: For standard changes, such as updating the client workstation operating system, it is sufficient for the Managing Director to authorize the procedure, rather than individual changes.

Normal change (minor or major) requests are made by the business owner or asset manager, using the Jira ticketing system. A Major Normal change request with high risk and high impact on the business has to be approved by the Managing Director.

Emergency changes: In a declared incident or crisis situation, decisions are made by available delegated staff, and documentation can be deferred until the emergency is resolved. Decisions are confirmed or corrected by personnel authorized to make such decisions in normal situations. A major Emergency change with high risk and high impact has to be approved by the Managing Director.

### Approval

The CIO, CISO or MD analyses the change request in terms of cost, potential benefits, implementation risks, and the required security controls. The approval process also ensure that information security requirements are met.

The CISO proposes to accept or reject the change based on a risk assessment. All changes are approved by the MD prior to their implementation.

In a declared incident or crisis situation, decisions are made by available delegated staff, and documentation can be deferred until the emergency is resolved. Decisions are confirmed or corrected by personnel authorized to make such decisions in normal situations.

### Change identification

Every change needs to be uniquely identified before being approved and implemented.

Change in question is identified as being a:



- Standard change being implemented first time;
- Normal change: Major or Minor change;
- Emergency change: Major or Minor change.

The system administrator in charge of implementing the change:



- sends detailed information on the changes made to all those concerned;
- provides for fallback procedures, following the failure of a change or an unforeseen event;
- keeps an audit log containing all relevant information relating to changes made;
- sets up an emergency change process for rapid, controlled execution of modifications during an incident.

When new versions of software, utilities or systems are released, the IT department takes particular care to carry out acceptance tests and write or adapt installation procedures. The same applies to any major change to the information system or one of its components.

### Change management attributes

#### Priority

All change requests are prioritized in terms of benefits, urgency, effort required and potential impact on everyday operations. The following change priorities are available in Jira [12]:



- low;
- normal;
- high;
- urgent;
- immediate.

Changes of urgent and immediate priority are unscheduled changes that generally have a major impact on system functionality or services but are required to be addressed quickly to prevent an outage, fix a critical problem (deploying security patches) or restart the network, etc. These types of changes may be accelerated through the change management process outlined in this document.

### Risk assessment

When a major change is requested, the risk analysis, rollback strategy, and test results after execution should be filled in Jira [12] by the person who requested the change, and has to be revised by the CIO and the CISO. The risk assessment is validated by the MD.

### Rollback strategy

The CIO establishes and documents a rollback strategy before any changes are made to the system or application, in order to be able to return to the state before the implementation in case of unsuccessful changes or unforeseen events.

### OpenTRICK update

Before a major change, documentation containing service configuration and rollback strategy are updated in a dedicated page on the wiki of BeFresh or on Jira ‘Change request’ ticket. The following figure shows an example of such ‘Change request’ ticket.

### Testing

When a change is requested in Jira (incl. description of possible tests after implementation), an asset owner should specify if the testing is needed after the changes are made to the system or application (e.g. minor changes might not require testing). Whenever a major change in a system or software is made, it is possible that other functionalities are affected. In order to assure that the changes have not had unintended consequences on the behaviour of the system, the CIO is testing major changes to operational systems in a dedicated testing environment and documents the configurations used. A testing environment is a setup of software and hardware running on a physical machine in an isolated network, or a virtual machine, and these replicate running systems. This allows smooth transfer of data and configurations used from an old system to a new system. More information about system change testing and configurations used can be found at the BeFresh wiki page.

### Validation of the test results

Test results are validated by the owner of the asset. All users significantly affected by the change should be notified prior to change implementation.

### Implementation

A major change will be implemented only after appropriate testing and approval from the asset owners.

### Documentation update

Once a major change has been implemented and the proper functionality has been validated by the asset owner, all operating documentation and user procedures and standards related to the major change are updated accordingly, so that the new documentation is available to users. The final step is to close the change request ticket. This documentation follows the ISMS document management process defined in #175 BeFresh-DocMgt.

### Monitoring

All changes are further monitored by the asset owners once they have been rolled out. Deviations from test results should be documented on a dedicated wiki page and treated accordingly.

### Logs

All change requests are logged in the Jira ticketing tool [12] Also, all modifications on service and system configurations (e.g. firewall, SSH server) are logged using Git software and centralized using GitHub.

### Technical review

After a major change is implemented, a technical review and vulnerability scan should be performed in order to ensure that the change did not affect any security aspects related to the system or application.

When operating platforms including operating systems, databases and middleware platforms are changed, business-critical applications should be reviewed and tested to ensure there is no adverse impact on organizational operations or security.

During the operation of information systems and applications, the following types of changes can occur:



- security updates to a server or service;
- changes in server technology.

If such changes occur, the following actions are taken:



- review of application control and integrity procedures to ensure they have not been compromised by change to the operating platform;
- notification of change with enough lead time to allow appropriate tests and reviews prior to implementation;
- appropriate modifications are made to business continuity plans.

Modifications to software packages from external suppliers are avoided, as knowledge of the software package may not be sufficient to prevent the software package from malfunctioning after the change. Where software modifications are necessary, the following points are taken into account:



- the risk of compromising integrated commands and the integrity verification process;
- whether the publisher’s consent is required;
- the possibility of obtaining the desired changes from the publisher, in the form of standard program updates;
- the consequences if the organization becomes responsible for maintaining the software as a result of the changes;
- compatibility with other software already in use.

## Applying changes

### Process

Figure 1: Change management procedure

### Process steps

The process for change management is performed in the following steps:



- An employee of BeFresh requests a change (new web application, update of existing, etc.). They use Jira to create a ticket. This is required to contain information regarding the change, e.g. link to technology, and why they need it;

The CIO analyses the request and if it is a minor change, he proceeds to the implementation step (d);

In case of a major change, the CISO performs a risk assessment to identify potential risks and their related impacts. Considering the input of the CIO, he identifies the risk treatment actions to be added in the Jira ticket. The CISO also assesses if the change respects the required level of security. If not, he proposes to the MD to reject or accept the risks associated with the change. The MD has the final word when the decision is needed about all major changes. The CIO assesses technology, systems, and network requirements. He reports this information on a dedicated wiki page;

The CIO implements the change in a test environment. He also defines a rollback strategy depending on the technology, documents the configuration, and creates a manual for employees. These different documentation activities are required to be made on the BeFresh wiki page;

The CIO tests the implementation to assess if it can be released to production, or if not, he goes back to step d;

The asset owner validates the implementation of the change;

The CIO:

continues with step d if a minor issue (not blocking the usability of services) was noticed;

applies the step ‘rollback the change’ and continues with step d if a major issue was detected;

rolls out the change into production by following risk treatment actions defined in the ticket if no issue was identified, communicates to employees (e.g. giving instructions if customer configuration change is needed), and monitors the implementation for two (2) weeks (e.g. system logs, feedback from employees). In case no issue is detected, the change is considered successful and the Jira ticket can be closed by the employee who initiated it.