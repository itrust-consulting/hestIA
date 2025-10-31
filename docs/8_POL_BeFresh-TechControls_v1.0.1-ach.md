|    |
|----|
|    |
|    |
|    |
|    |

General information

Document history



| Version   | Date       | Author        | Modifications         |
|-----------|------------|---------------|-----------------------|
| 1.0       | 31/03/2025 | A. Chezganova | Creation based on ITR |
|           |            |               |                       |

Approval



| Name      | Role                   | Responsibility            | Signature   |
|-----------|------------------------|---------------------------|-------------|
| C. Harpes | CISO                   | Content,  CISO compliance |             |
| B. Frisch | Managing director (MD) | Ownership                 |             |

Management summary

The purpose of this Policy is to define technological controls (security measure), and specific guidance for their implementation.

In this document all technological controls proposed in ISO/IEC 27002:2022 have been retained for implementation. These measures are as follows:

8.1 User endpoint devices: Information stored on, processed by or accessible via user endpoint devices shall be protected.

8.2 Privileged access rights: The allocation and use of privileged access rights shall be restricted and managed.

8.3 Information access restriction: Access to information and other associated assets shall be restricted in accordance with the established topic-specific policy on access control.

8.4 Access to source code: Read and write access to source code, development tools and software libraries shall be appropriately managed.

8.5 Secure authentication: Secure authentication technologies and procedures shall be implemented based on information access restrictions and the topic-specific policy on access control.

8.6 Capacity management: The use of resources shall be monitored and adjusted in line with current and expected capacity requirements.

8.7 Protection against malware: Protection against malware shall be implemented and supported by appropriate user awareness.

8.8 Management of technical vulnerabilities: Information about technical vulnerabilities of information systems in use shall be obtained, the organization’s exposure to such vulnerabilities shall be evaluated and appropriate measures shall be taken.

8.9 Configuration management: Configurations, including security configurations, of hardware, software, services and networks shall be established, documented, implemented, monitored and reviewed.

8.10 Information deletion: Information stored in information systems, devices or in any other storage media shall be deleted when no longer required.

8.11 Data masking: Data masking shall be used in accordance with the organization’s topic-specific policy on access control and other related topic-specific, and business requirements, taking applicable legislation into consideration.

8.12 Data leakage prevention: Data leakage prevention measures shall be applied to systems, networks and any other devices that process, store or transmit sensitive information.

8.13 Information backup: Backup copies of information, software and systems shall be maintained and regularly tested in accordance with the agreed topic-specific policy on backup.

8.14 Redundancy of information processing facilities: Information processing facilities shall be implemented with redundancy sufficient to meet availability requirements.

8.15 Logging: Logs that record activities, exceptions, faults and other relevant events shall be produced, stored, protected and analysed.

8.16 Monitoring activities: Networks, systems and applications shall be monitored for anomalous behaviour and appropriate actions taken to evaluate potential information security incidents.

8.17 Clock synchronization: The clocks of information processing systems used by the organization shall be synchronized to approved time sources.

8.18 Use of privileged utility programs: The use of utility programs that can be capable of overriding system and application controls shall be restricted and tightly controlled.

8.19 Installation of software on operational systems: Procedures and measures shall be implemented to securely manage software installation on operational systems.

8.20 Networks security: Networks and network devices shall be secured, managed and controlled to protect information in systems and applications.

8.21 Security of network services: Security mechanisms, service levels and service requirements of network services shall be identified, implemented and monitored.

8.22 Segregation of networks: Groups of information services, users and information systems shall be segregated in the organization’s networks.

8.23 Web filtering: Access to external websites shall be managed to reduce exposure to malicious content.

8.24 Use of cryptography: Rules for the effective use of cryptography, including cryptographic key management, shall be defined and implemented.

8.25 Secure development life cycle: Rules for the secure development of software and systems shall be established and applied.

8.26 Application security requirements: Information security requirements shall be identified, specified and approved when developing or acquiring applications.

8.27 Secure system architecture and engineering principles: Principles for engineering secure systems shall be established, documented, maintained and applied to any information system development activities.

8.28 Secure coding: Secure coding principles shall be applied to software development.

8.29 Security testing in development and acceptance: Security testing processes shall be defined and implemented in the development life cycle.

8.30 Outsourced development: The organization shall direct, monitor and review the activities related to outsourced system development.

8.31 Separation of development, test and production environments: Development, testing and production environments shall be separated and secured.

8.32 Change management: Changes to information processing facilities and information systems shall be subject to change management procedures.

8.33 Test information: Test information shall be appropriately selected, protected and managed.

8.34 Protection of information systems during audit testing: Audit tests and other assurance activities involving assessment of operational systems shall be planned and agreed between the tester and appropriate management.

Table of contents

1	Introduction	7

1.1	Context	7

1.2	Objectives	7

1.3	Scope	7

1.4	Enforcement and reading instructions	7

1.5	Audience	8

1.6	Document structure	8

1.7	References	8

1.8	Acronyms	9

1.9	Glossary	9

8	Technological controls	13

8.1	User endpoint devices [A8.01]	13

8.2	Privileged access rights [A8.02]	15

8.3	Information access restriction [A8.03]	17

8.4	Access to source code [A8.04]	19

8.5	Secure authentication [A8.05]	20

8.6	Capacity management [A8.06]	22

8.7	Protection against malware [A8.07]	24

8.8	Management of technical vulnerabilities [A8.08]	26

8.9	Configuration management [A8.09]	29

8.10	Information deletion [A8.10]	31

8.11	Data masking [A8.11]	32

8.12	Data leakage prevention [A8.12]	34

8.13	Information backup [A8.13]	35

8.14	Redundancy of information processing facilities [A8.14]	36

8.15	Logging [A8.15]	38

8.16	Monitoring activities [A8.16]	40

8.17	Clock synchronization [A8.17]	42

8.18	Use of privileged utility programs [A8.18]	43

8.19	Installation of software on operational systems [A8.19]	44

8.20	Networks security [A8.20]	46

8.21	Security of network services [A8.21]	48

8.22	Segregation of networks [A8.22]	49

8.23	Web filtering [A8.23]	51

8.24	Use of cryptography [A8.24]	51

8.25	Secure development life cycle [A8.25]	58

8.26	Application security requirements [A8.26]	59

8.27	Secure system architecture and engineering principles [A8.27]	63

8.28	Secure coding [A8.28]	65

8.29	Security testing in development and acceptance [A8.29]	67

8.30	Outsourced development [A8.30]	69

8.31	Separation of development, test and production environments [A8.31]	70

8.32	Change management [A8.32]	72

8.33	Test information [A8.33]	75

8.34	Protection of information systems during audit testing [A8.34]	76

## Introduction

### Context

The underlying policy is part of the Information Security Management System (ISMS) of BeFresh.

### Objectives

The purpose of this document was to create an exhaustive document of all requirements and most relevant recommendations most relevant for BeFresh with respect to current practices related to technological controls. In this document ISO/IEC 27002 was considered. This document establishes and makes applicable inside BeFresh:



- all requirements related to technological control from this norm;
- those recommendations that are important for– there a worded as implemented facts;
- all other recommendations for which the person in scope can decide on a case-by-case basis whether they are followed or not – these statements are worded with “should”.

The purpose of all these technological controls is to reduce information risk to an acceptable level and to ensure compliance with recognized practices, as stated in the overall information security policy.

### Scope

The scope of this document is the same as that of the ISMS.

### Enforcement and reading instructions

This document becomes effective once approved by the MD and published on the ISMS repository (\InfoSec-IN) available to all employees of BeFresh. It will remain in effect until revoked or revised by the Owner or the MD. Do not rely on a printed document but rather check on the official documentation site of BeFresh for the currently applicable version.

The MD’s signature is an official recognition of the mandatory character of this document. It is to be respected by all employees of BeFresh and a failure to comply with the Information Security policy may be considered as a violation of the working contract and result in disciplinary action.

The use of the SIMPLE PRESENT tense or the terms ‘MUST’, ‘MANDATORY’, ‘REQUIRED’, or ‘SHALL’ in a statement means that the statement is considered a formal requirement.

The use of words such as ‘SHOULD’ or the adjective ‘RECOMMENDED’ means that there may be legitimate reasons to disregard the statement, but that the implications of such an exception shall be assessed and fully understood.

The terminology ‘MAY’ or ‘CAN’, or the adjective ‘OPTIONAL’ means that the implementation of the statement is at the discretion of the implementer.

The indication #175W BeFresh-WordTempl refers to the document with the given acronym, here BeFresh-WordTempl. The indication #175W refers to the ISMS document with the given indicator, here 175W, in this case the same document as the reference before.

The indicate #502 refers to a separated document 502 if existent, other wise to the chapter 02 inside document #5.

The text copied by law or other reference is marked in red, and in any case constitutes an obligation.

Control objectives given in ISO are put in bold.

Security measures for reaching these objectives are put in a box.

Specific text for the implementation at BeFresh is highlighted.

### Audience

This document shall be read and applied by all collaborators with responsibility in writing or approving documents within BeFresh.

### Document structure

The structure of the document is the following:



- Chapter 8 deals with Technological security measures; the sections are numbered in the same way as in the corresponding standard.

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



| access control                           | means to ensure that physical and logical access to assets is authorized and restricted based on business and information security requirements                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
|------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| asset                                    | anything that has value to the organization Note 1: In the context of information security, two kinds of assets can be distinguished: the primary assets: information, business processes and activities; the supporting assets (on which the primary assets rely) of all types, for example: hardware, software, network, personnel, site, organization’s structure.                                                                                                                                                                                                                                   |
| attack                                   | successful or unsuccessful unauthorized attempt to destroy, alter, disable, gain access to an asset or any attempt to expose, steal, or make unauthorized use of an asset                                                                                                                                                                                                                                                                                                                                                                                                                               |
| authentication                           | provision of assurance that a claimed characteristic of an entity is correct                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| authenticity                             | property that an entity is what it claims to be                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| chain of custody                         | demonstrable possession, movement, handling and location of material from one point in time until another Note 1: Material includes information and other associated assets in the context of ISO/IEC 27002.[SOURCE: ISO/IEC 27050-1:2019, 3.1, modified — 'Note 1' added]                                                                                                                                                                                                                                                                                                                              |
| confidential information                 | information that is not intended to be made available or disclosed to unauthorized individuals, entities or processes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| control                                  | measure that maintains and/or modifies risk Note 1: Controls include, but are not limited to, any process, policy, device, practice or other conditions and/or actions which maintain and/or modify risk. Note 2: Controls may not always exert the intended or assumed modifying effect.[SOURCE: ISO 31000:2018, 3.8]                                                                                                                                                                                                                                                                                  |
| disruption                               | incident, whether anticipated or unanticipated, that causes an unplanned, negative deviation from the expected delivery of products and services according to an organization’s objectives"                                                                                                                                                                                                                                                                                                                                                                                                             |
| endpoint device                          | network connected information and communication technology (ICT) hardware device Note 1: Endpoint device can refer to desktop computers, laptops, smart phones, tablets, thin clients, printers or other specialized hardware including smart meters and Internet of things (IoT) devices.                                                                                                                                                                                                                                                                                                              |
| entity                                   | item relevant for the purpose of operation of a domain that has recognizably distinct existence Note 1: An entity can have a physical or a logical embodiment. EXAMPLE A person, an organization, a device, a group of such items, a human subscriber to a telecom service, a SIM card, a passport, a network interface card, a software application, a service or a website.[SOURCE: ISO/IEC 24760-1:2019, 3.1.1]                                                                                                                                                                                      |
| information processing facility          | any information processing system, service or infrastructure, or the physical location housing it [SOURCE: ISO/IEC 27000:2018, 3.27, modified — 'facilities' has been replaced with facility.]                                                                                                                                                                                                                                                                                                                                                                                                          |
| information security breach              | compromise of information security that leads to the undesired destruction, loss, alteration, disclosure of, or access to, protected information transmitted, stored or otherwise processed                                                                                                                                                                                                                                                                                                                                                                                                             |
| information security event               | occurrence indicating a possible information security breach or failure of controls [SOURCE: ISO/IEC 27035-1:2016, 3.3, modified — 'breach of information security' has been replaced with 'information security breach'                                                                                                                                                                                                                                                                                                                                                                                |
| information security incident            | one or multiple related and identified information security events that can harm an organization’s assets or compromise its operations [SOURCE: ISO/IEC 27035-1:2016, 3.4]                                                                                                                                                                                                                                                                                                                                                                                                                              |
| information security incident management | exercise of a consistent and effective approach to the handling of information security incidents [SOURCE: ISO/IEC 27035-1:2016, 3.5]                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| information system                       | set of applications, services, information technology assets, or other information-handling components [SOURCE: ISO/IEC 27000:2018, 3.35]                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| interested party                         | stakeholder person or organization that can affect, be affected by, or perceive itself to be affected by a decision or activity [SOURCE: ISO/IEC 27000:2018, 3.37]                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| non-repudiation                          | ability to prove the occurrence of a claimed event or action and its originating entities                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| personnel                                | persons doing work under the organization’s direction Note 1: The concept of personnel includes the organization’s members, such as the governing body, top management, employees, temporary staff, contractors and volunteers.                                                                                                                                                                                                                                                                                                                                                                         |
| personally identifiable information PII  | any information that (a) can be used to establish a link between the information and the natural person to whom such information relates, or (b) is or can be directly or indirectly linked to a natural person. Note 1: The “natural person” in the definition is the PII principal. To determine whether a PII principal is identifiable, account should be taken of all the means which can reasonably be used by the privacy stakeholder holding the data, or by any other party, to establish the link between the set of PII and the natural person. [SOURCE: ISO/IEC 29100:2011/Amd.1:2018, 2.9] |
| PII principal                            | natural person to whom the personally identifiable information (PII) relates Note 1: Depending on the jurisdiction and the particular data protection and privacy legislation, the synonym “data subject” can also be used instead of the term 'PII principal'. [SOURCE: ISO/IEC 29100:2011, 2.11]                                                                                                                                                                                                                                                                                                      |
| PII processor                            | privacy stakeholder that processes personally identifiable information (PII) on behalf of and in accordance with the instructions of a PII controller [SOURCE: ISO/IEC 29100:2011, 2.12]                                                                                                                                                                                                                                                                                                                                                                                                                |
| policy                                   | intentions and direction of an organization, as formally expressed by its top management [SOURCE: ISO/IEC 27000:2018, 3.53]                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| privacy impact assessment                | PIA overall process of identifying, analysing, evaluating, consulting, communicating and planning the treatment of potential privacy impacts with regard to the processing of personally identifiable information (PII), framed within an organization’s broader risk management framework [SOURCE: ISO/IEC 29134:2017, 3.7, modified — Note 1 to entry removed.]                                                                                                                                                                                                                                       |
| procedure                                | specified way to carry out an activity or a process [SOURCE: ISO 30000:2009, 3.12]                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| process                                  | set of interrelated or interacting activities that uses or transforms inputs to deliver a result [SOURCE: ISO 9000:2015, 3.4.1, modified— Notes to entry removed.]                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| record                                   | information created, received and maintained as evidence and as an asset by an organization or person, in pursuit of legal obligations or in the transaction of business Note 1: Legal obligations in this context include all legal, statutory, regulatory and contractual requirements. [SOURCE: ISO 15489-1:2016, 3.14, modified— 'Note 1 to entry' added.]                                                                                                                                                                                                                                          |
| recovery point objective                 | RPO point in time to which data are to be recovered after a disruption has occurred [SOURCE: ISO/IEC 27031:2011, 3.12, modified — 'must' replaced by 'are to be'.]                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| recovery time objective                  | RTO period of time within which minimum levels of services and/or products and the supporting systems, applications, or functions are to be recovered after a disruption has occurred [SOURCE: ISO/IEC 27031:2011, 3.13, modified — 'must' replaced by 'are to be'.]                                                                                                                                                                                                                                                                                                                                    |
| reliability                              | property of consistent intended behaviour and results                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| rule                                     | accepted principle or instruction that states the organization’s expectations on what is required to be done, what is allowed or not allowed Note 1: Rules can be formally expressed in topic-specific policies and in other types of documents.                                                                                                                                                                                                                                                                                                                                                        |
| sensitive information                    | information that needs to be protected from unavailability, unauthorized access, modification or public disclosure because of potential adverse effects on an individual, organization, national security or public safety                                                                                                                                                                                                                                                                                                                                                                              |
| threat                                   | potential cause of an unwanted incident, which can result in harm to a system or organization [SOURCE: ISO/IEC 27000:2018, 3.74]                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| topic-specific policy                    | intentions and direction on a specific subject or topic, as formally expressed by the appropriate level of management Note 1: Topic-specific policies can formally express rules or organization standards. Note 2: Some organizations use other terms for these topic-specific policies. Note 3: The topic-specific policies referred to in this document are related to information security. EXAMPLE Topic-specific policy on access control, topic-specific policy on clear desk and clear screen.                                                                                                  |
| user                                     | interested party with access to the organization’s information systems EXAMPLE Personnel, customers, suppliers.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| user endpoint device                     | endpoint device used by users to access information processing services Note 1: User endpoint device can refer to desktop computers, laptops, smart phones, tablets, thin clients, etc.                                                                                                                                                                                                                                                                                                                                                                                                                 |
| vulnerability                            | weakness of an asset or control that can be exploited by one or more threats [SOURCE: ISO/IEC 27000:2018, 3.77]                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |

## Technological controls

### User endpoint devices [A8.01]

#Attributes : #Preventive #Confidentiality #Integrity #Availability #Protect #Asset\_management #Information\_protection #Protection

Information stored on, processed by or accessible via user endpoint devices shall be protected.

To protect information against the risks introduced by using user endpoint devices.

###### General

BeFresh establishes a topic-specific policy on secure configuration and handling of user endpoint devices. The topic-specific policy is communicated to all relevant personnel and consider the following:



- the type of information and the classification level that the user endpoint devices can handle, process, store or support;

registration of user endpoint devices;

requirements for physical protection;

restriction of software installation (e.g. remotely controlled by system administrators);

requirements for user endpoint device software (including software versions) and for applying updates (e.g. active automatic updating);

rules for connection to information services, public networks or any other network off premises (e.g. requiring the use of personal firewall);

access controls;

storage device encryption;

protection against malware;

remote disabling, deletion or lockout;

backups;

usage of web services and web applications;

end user behaviour analytics (See section 8.16 #8);

the use of removable devices, including removable memory devices, and the possibility of disabling physical ports (e.g. USB ports);

the use of partitioning capabilities, if supported by the user endpoint device, which can securely separate BeFresh's information and other associated assets (e.g. software) from other information and other associated assets on the device.

Consideration is given as to whether certain information is so sensitive that it can only be accessed via user endpoint devices but not stored on such devices. In such cases, additional technical safeguards can be required on the device. For example, ensuring that downloading files for offline working is disabled and that local storage such as SD card is disabled.

As far as possible, the recommendations on this control are enforced through configuration management (See section 8.9) or automated tools.

###### User responsibility

All users are made aware of the security requirements and procedures for protecting user endpoint devices, as well as of their responsibilities for implementing such security measures. Users are advised to:



- log-off active sessions and terminate services when no longer needed;

protect user endpoint devices from unauthorized use with a physical control (e.g. key lock or special locks) and logical control (e.g. password access) when not in use; not leave devices carrying important, sensitive or critical business information unattended;

use devices with special care in public places, open offices, meeting places and other unprotected areas (e.g. avoid reading confidential information if people can read from the back, use privacy screen filters);

physically protect user endpoint devices against theft (e.g. in cars and other forms of transport, hotel rooms, conference centres and meeting places).

A specific procedure taking into account legal, statutory, regulatory, contractual (including insurance) and other security requirements of BeFresh is established for cases of theft or loss of user endpoint devices.

###### Use of personal devices

Where BeFresh allows the use of personal devices (sometimes known as BYOD), in addition to the guidance given in this control, the following should be considered:



- separation of personal and business use of the devices, including using software to support such separation and protect business data on a private device;

providing access to business information only after users have acknowledged their duties (physical protection, software updating, etc.), waiving ownership of business data, allowing remote wiping of data by BeFresh in case of theft or loss of the device or when no longer authorized to use the service. In such cases, PII protection legislation should be considered;

topic-specific policies and procedures to prevent disputes concerning rights to intellectual property developed on privately owned equipment;

access to privately owned equipment (to verify the security of the machine or during an investigation), which can be prevented by legislation;

software licensing agreements that are such that organizations can become liable for licensing for client software on user endpoint devices owned privately by personnel or external party users.

###### Wireless connections

BeFresh establishes procedures for:



- the configuration of wireless connections on devices (e.g. disabling vulnerable protocols);

using wireless or wired connections with appropriate bandwidth in accordance with relevant topic-specific policies (e.g. because backups or software updates are needed).

Controls to protect information on user endpoint devices depend on whether the user endpoint device is used only inside of BeFresh's secured premises and network connections, or whether it is exposed to increased physical and network related threats outside of BeFresh.

The wireless connections for user endpoint devices are similar to other types of network connections but have important differences that should be considered when identifying controls. In particular, back-up of information stored on user endpoint devices can sometimes fail because of limited network bandwidth or because user endpoint devices are not connected at the times when backups are scheduled.

For some USB ports, such as USB-C, disabling the USB port is not possible because it is used for other purposes (e.g. power delivery and display output).

Users ensure that unattended equipment has appropriate protection.

Unattended equipment has appropriate protection in order to prevent unauthorized access or use. Each employee is personally responsible for the equipment which is situated in their designated workstation. Employees:

terminate active sessions when the session is finished;

log-off mainframe computers, servers, laptops, and desktop PCs when the session is finished;

secure desktop PCs or laptops from unauthorized use by means of a password which follows the guidelines included in the password management procedure of BeFresh, BeFresh-PasswordMgt #517.

Specific users rules are copied from policies to a code of conduct BeFresh-CodeConduct #3 and to related user guides. These documents are also explained during induction training and awareness training and the same message is repeated in coaching activities.

### Privileged access rights [A8.02]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #Protect #Identity\_and\_access\_management #Protection

The allocation and use of privileged access rights shall be restricted and managed.

To ensure only authorized users, software components and services are provided with privileged access rights.

The allocation of privileged access rights is controlled through an authorization process in accordance with the relevant topic-specific policy on access control (See 5.15 in #5). The following is considered:



- identifying users who need privileged access rights for each system or process (e.g. operating systems, database management systems and applications);

allocating privileged access rights to users as needed and on an event-by-event basis in line with the topic-specific policy on access control (See 5.15 in #5) (i.e. only to individuals with the necessary competence to carry out activities that require privileged access and based on the minimum requirement for their functional roles);

maintaining an authorization process (i.e. determining who can approve privileged access rights, or not granting privileged access rights until the authorization process is complete) and a record of all privileges allocated;

defining and implementing requirements for expiry of privileged access rights;

taking measures to ensure that users are aware of their privileged access rights and when they are in privileged access mode. Possible measures include using specific user identities, user interface settings or even specific equipment;

authentication requirements for privileged access rights can be higher than the requirements for normal access rights. Re-authentication or authentication step-up can be necessary before doing work with privileged access rights;

regularly, and after any organizational change, reviewing users working with privileged access rights in order to verify if their duties, roles, responsibilities and competences still qualify them for working with privileged access rights (See section 5.18 in #5);

establishing specific rules in order to avoid the use of generic administration user IDs (such as root), depending on systems’ configuration capabilities; managing and protecting authentication information of such identities (See 5.17 in #5);

granting temporary privileged access just for the time window necessary to implement approved changes or activities (e.g. for maintenance activities or some critical changes), rather than permanently granting privileged access rights. This is often referred as break glass procedure, and often automated by privilege access management technologies;

logging all privileged access to system for audit purposes;

not sharing or linking identities with privileged access rights to multiple persons, assigning each person a separate identity which allows assigning specific privileged access rights. Identities can be grouped (e.g. by defining an administrator group) in order to simplify the management of privileged access rights;

only using identities with privileged access rights for undertaking administrative tasks and not for day-to-day general tasks [i.e. checking email, accessing the web (users have a separate normal network identity for these activities)].

Privileged access rights are access rights provided to an identity, a role or a process that allows the performance of activities that typical users or processes cannot perform. System administrator roles typically require privileged access rights.

Inappropriate use of system administrator privileges (any feature or facility of an information system that enables the user to override system or application controls) is a major contributory factor to failures or breaches of systems.

More information related to access management and the secure management of access to information and information and communications technologies resources can be found in ISO/IEC 29146.

BeFresh refined guidance  in the following way:



- The asset inventory contains an inventory of high privileged access rights (it may refer to a 1Password database for identification of each single login).

Activity is documented in (https://befreshlu.atlassian.net/), except for access of the asset manager named in the asset inventory and configured during set up.

cf. BeFresh-AccessControl #515.

requirements for expiry of privileged access rights are defined in the requested tickets.

Awareness of privileged access rights is defined by dedicated admin users on some systems (e.g. OwnCloud). Specific rules can be added in the asset inventory.

Administration is only allowed from the internal LAN or over VPN connection to the LAN (unless dedicates admin user with two factor authentication are used.

Sporadic checks and regular check after changes are made by the system manager.

Credential of such users are held in 1Password; of which configuration files are either personnel, or share within a team (on ownCloud).

The manager uses all proposed audit functions proposed by the system and a duration in line with agreed rules (See. BeFresh-ProcesRec #2R) and capacity.

Exceptions are allowed if documented in shared 1Password config files.

Head of Department (HoD) or people with technical knowledge can request a LOCAL ADMIN account (additional account with Admin privileges) from ICT.

Because of allowing users to activate and deactivate OpenVPN, each employee has been added on local group "Network configuration Operators" on their laptops. "Network Configuration Operators" group allow users to modify network settings without granting them full admin permissions.

Privileged access rights are allocated to users on a need-to-use basis and on an event-by-event basis to perform their functional roles.

The CIO and CISO reviews the allocation and use of access privileges to assets classified as confidential, vital or higher.

### Information access restriction [A8.03]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #Protect #Identity\_and\_access\_management #Protection

Access to information and other associated assets shall be restricted in accordance with the established topic-specific policy on access control.

To ensure only authorized access and to prevent unauthorized access to information and other associated assets.

Access to information and other associated assets is restricted in accordance with the established topic-specific policies. The following is considered in order to support access restriction requirements:



- not allowing access to sensitive information by unknown user identities or anonymously. Public or anonymous access is only granted to storage locations that do not contain any sensitive information;

providing configuration mechanisms to control access to information in systems, applications and services;

controlling which data can be accessed by a particular user;

controlling which identities or group of identities have which access, such as read, write, delete and execute;

providing physical or logical access controls for the isolation of sensitive applications, application data, or systems.

Further, dynamic access management techniques and processes to protect sensitive information that has high value to BeFresh is considered when BeFresh:



- needs granular control over who can access such information during what period and in what way;

wants to share such information with people outside BeFresh and maintain control over who can access it;

wants to dynamically manage, in real time, the use and distribution of such information;

wants to protect such information against unauthorized changes, copying and distribution (including printing);

wants to monitor the use of the information;

wants to record any changes to such information that take place in case a future investigation is required.

Dynamic access management techniques protect information throughout its life cycle (i.e. creation, processing, storage, transmission and disposal), including:



- establishing rules on the management of dynamic access based on specific use cases considering:

granting access permissions based on identity, device, location or application;

leveraging the classification scheme in order to determine what information needs to be protected with dynamic access management techniques;

establishing operational, monitoring and reporting processes and supporting technical infrastructure.

Dynamic access management systems should protect information by:



- requiring authentication, appropriate credentials or a certificate to access information;

restricting access, for example to a specified time frame (e.g. after a given date or until a particular date);

using encryption to protect information;

defining the printing permissions for the information;

recording who accesses the information and how the information is used;

raising alerts if attempts to misuse the information are detected.

Dynamic access management techniques and other dynamic information protection technologies can support the protection of information even when data is shared beyond the originating organization, where traditional access controls cannot be enforced. It can be applied to documents, emails or other files containing information to limit who can access the content and in what way. It can be at a granular level and be adapted over the life cycle of the information.

Dynamic access management techniques do not replace classical access management [e.g. using access control lists (ACLs)], but can add more factors for conditionality, real-time evaluation, just-in-time data reduction and other enhancements that can be useful for the most sensitive information. It offers a way to control access outside BeFresh’s environment. Incident response can be supported by dynamic access management techniques as permissions can be modified or revoked at any time.

Additional information on a framework for access management is provided in ISO/IEC 29146.

Access to information and application system functions is restricted in accordance with the following access :



- following the need-to-know principles: Employees will only be granted access to the information that they need to fulfil their business duties;
- using grouping of access right by profiles defined by the system.
- If possible for the system using the SMB is managed by LDAP and ACL. If not, the CIO is required to pay attention to correctly (regarding profiles) configure the native authentication and authorization features of services not implementing LDAP, and he indicates this in the asset inventory or on his Wiki.
- Access to the building: Access to the building is ensured through an RFID key. The administrative assistant is responsible for distributing the keys to employees and maintaining a list of unique key attributions in the key inventory standard BeFresh-KeyInventory #702K.
- User identification and authentication: Each BeFresh employee has a unique user ID and password that is used to log on to the OS which they use. The user ID consists of the employees’ first initial followed by their surname. BeFresh may occasionally share credentials and passwords in exceptional circumstances, such as for group projects. If this is the case, the asset owner or the #CEO is required to have approved and validated this decision.
- Central authentication and authorization service: Centralization of the authentication information and of the authorization is made using LDAP. This protocol provides a distributed directory information service in order to store and access directory information, such as list of machines, or list of users and groups, which enables centralized authentication and authorization.
- Utilization of central authentication and authorization service: The utilization of the central authentication and authorization service is recommended for different services provided by BeFresh to its employees. However, this could not be possible for all services, as a technology used to operate a service could not implement an LDAP authentication connector

### Access to source code [A8.04]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #Protect #Identity\_and\_access\_management #Application\_security #Secure\_configuration #Protection

Read and write access to source code, development tools and software libraries shall be appropriately managed.

To prevent the introduction of unauthorized functionality, avoid unintentional or malicious changes and maintain the confidentiality of valuable intellectual property.

Access to source code and associated items (such as designs, specifications, verification plans and validation plans) and development tools (e.g. compilers, builders, integration tools, test platforms and environments) is strictly controlled.

For source code, this can be achieved by controlling central storage of such code, preferably in source code management system.

Read access and write access to source code can differ based on the personnel’s role. For example, read access to source code can be broadly provided inside BeFresh, but write access to source code is only made available to privileged personnel or designated owners. Where code components are used by several developers within an organization, read access to a centralized code repository is implemented. Furthermore, if open-source code or third-party code components are used inside an organization, read access to such external code repositories can be broadly provided. However, write access is still restricted.

The following guidelines are considered to control access to program source libraries in order to reduce the potential for corruption of computer programs:



- managing the access to program source code and the program source libraries according to established procedures;

granting read and write access to source code based on business needs and managed to address risks of alteration or misuse and according to established procedures;

updating of source code and associated items and granting of access to source code in accordance with change control procedures (See 8.32) and only performing it after appropriate authorization has been received;

not granting developers direct access to the source code repository, but through developer tools that control activities and authorizations on the source code;

holding program listings in a secure environment, where read and write access is appropriately managed and assigned;

maintaining an audit log of all accesses and of all changes to source code.

If the program source code is intended to be published, additional controls to provide assurance on its integrity (e.g. digital signature) should be considered.

If access to source code is not properly controlled, source code can be modified or some data in the development environment (e.g. copies of production data, configuration details) can be retrieved by unauthorized persons.

Access to program source code is restricted and strictly controlled to prevent the introduction of unauthorized functionality and to avoid unintentional changes as well as to maintain the confidentiality of valuable intellectual property.

Access to BeFresh program source code is restricted by at least applying the rules applicable to assets classified as restricted or important or higher.

Additionally, BeFresh:



- applies the same access security measures to the source code of the main programs and associated elements (such as design, requirements, specifications, verifications, and program validation) in order to prevent the introduction of unauthorized functionality and avoid unintentional changes, as well as to protect intellectual property.

manages the source code and develops software using #825 BeFresh-LIfeCycleICT

Manager all source code in BeFresh-https://github.com/befreshlu

Developers are responsible to reflect all changes and released in a documented manner in this tool.

The tool admin has established maintenance and copying processes for source program libraries including change control.

Note: Some applications have been published as open source in GitHub. The applications that are open source do not have the above section applicable anymore.

### Secure authentication [A8.05]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #Protect #Identity\_and\_access\_management #Protection

Secure authentication technologies and procedures shall be implemented based on information access restrictions and the topic-specific policy on access control.

To ensure a user or an entity is securely authenticated, when access to systems, applications and services is granted.

A suitable authentication technique is chosen to substantiate the claimed identity of a user, software, messages and other entities.

The strength of authentication is appropriate for the classification of the information to be accessed. Where strong authentication and identity verification is required, authentication methods alternative to passwords, such as digital certificates, smart cards, tokens or biometric means, should be used.

Authentication information is accompanied by additional authentication factors for accessing critical information systems (also known as multi-factor authentication). Using a combination of multiple authentication factors, such as what you know, what you have and what you are, reduces the possibilities for unauthorized accesses. Multi-factor authentication can be combined with other techniques to require additional factors under specific circumstances, based on predefined rules and patterns, such as access from an unusual location, from an unusual device or at an unusual time.

Biometric authentication information is invalidated if it is ever compromised. Biometric authentication can be unavailable depending on the conditions of use (e.g. moisture or aging). To prepare for these issues, biometric authentication is accompanied with at least one alternative authentication technique.

The procedure for logging into a system or application is designed to minimize the risk of unauthorized access. Log-on procedures and technologies are implemented considering the following:



- not displaying sensitive system or application information until the log-on process has been successfully completed in order to avoid providing an unauthorized user with any unnecessary assistance;

displaying a general notice warning that the system or the application or the service should only be accessed by authorized users;

not providing help messages during the log-on procedure that would aid an unauthorized user (e.g. if an error condition arises, the system should not indicate which part of the data is correct or incorrect);

validating the log-on information only on completion of all input data;

protecting against brute force log-on attempts on usernames and passwords (e.g. using CAPTCHA, requiring password reset after a predefined number of failed attempts or blocking the user after a maximum number of errors);

logging unsuccessful and successful attempts;

raising a security event if a potential attempted or successful breach of log-on controls is detected (e.g. sending an alert to the user and BeFresh’s system administrators when a certain number of wrong password attempts have been reached);

displaying or sending the following information on a separate channel on completion of a successful log-on:

date and time of the previous successful log-on;

details of any unsuccessful log-on attempts since the last successful log-on;

not displaying a password in clear text when it is being entered; in some cases, it can be required to de-activate this functionality in order to facilitate user log-on (e.g. for accessibility reasons or to avoid blocking users because of repeated errors);

not transmitting passwords in clear text over a network to avoid being captured by a network 'sniffer' program.

terminating inactive sessions after a defined period of inactivity, especially in high-risk locations such as public or external areas outside BeFresh’s security management or on user endpoint devices;

restricting connection duration times to provide additional security for high-risk applications and reduce the window of opportunity for unauthorized access.

Additional information on entity authentication assurance can be found is ISO/IEC 29115.

On all systems qualified as confidential, access to systems and applications is controlled by a secure log-on procedures: They generally need a login to the system (using strong password); some applications need additional authentication (2FA). The passwords are allowed to be stored in the browser provided that a strong password and appropriate password encryption has been activated.

Critical applications, in particular all those that do not require domain access, but which can be accessed from internet, such SharePoint, ownCloud, need additional strong authentication (where a One-time password is encouraged to be managed on the personal mobile phone with Yubikey, Microsoft authentication, Google authentication, Luxtrust, passkey.

All computers of BeFresh have their entire system drive encrypted, where the OS is installed and from which it boots. BeFresh uses full disk encryption software to perform this function (see BeFresh-AssetInventory #509A).

Session time-out

Operating Systems lock the session of an employee after a few minutes defined period of inactivity in order to avoid unauthorized access by other people.

Limited number of connection attempts

Operating Systems ensure that after three failed connection attempts the access to the login screen is blocked for 5 minutes.

### Capacity management [A8.06]

#Attributes: #Preventive #Detective #Integrity #Availability #Identify #Protect #Detect #Continuity #Governance\_and\_Ecosystem #Protection

The use of resources shall be monitored and adjusted in line with current and expected capacity requirements.

To ensure the required capacity of information processing facilities, human resources, offices and other facilities.

Capacity requirements for information processing facilities, human resources, offices, and other facilities are identified, taking into account the business criticality of the concerned systems and processes.

System tuning and monitoring is applied to ensure and, where necessary, improve the availability and efficiency of systems.

BeFresh performs stress-tests of systems and services to confirm that sufficient system capacity is available to meet peak performance requirements.

Detective controls should be put in place to indicate problems in due time.

Projections of future capacity requirements take account of new business and system requirements and current and projected trends in BeFresh’s information processing capabilities.

Particular attention is paid to any resources with long procurement lead times or high costs. Therefore, managers, service or product owners monitor the utilization of key system resources.

Managers use capacity information to identify and avoid potential resource limitations and dependency on key personnel which can present a threat to system security or services and plan appropriate action.

Providing sufficient capacity can be achieved by increasing capacity or by reducing demand. The following is considered to increase capacity:



- hiring new personnel;

obtaining new facilities or space;

acquiring more powerful processing systems, memory and storage;

making use of cloud computing, which has inherent characteristics that directly address issues of capacity. Cloud computing has elasticity and scalability which enable on-demand rapid expansion and reduction in resources available to particular applications and services.

The following should be considered to reduce demand on BeFresh’s resources:



- deletion of obsolete data (disk space);

disposal of hardcopy records that have met their retention period (free up shelving space);

decommissioning of applications, systems, databases or environments;

optimizing batch processes and schedules;

optimizing application code or database queries;

denying or restricting bandwidth for resource-consuming services if these are not critical (e.g. video streaming).

A documented capacity management plan is considered for mission critical systems.

For more detail on the elasticity and scalability of cloud computing, see ISO/IEC TS 23167.

System managers, under supervision of the CIO, monitors, tunes, and makes projections of future capacity requirements for their resource usage to ensure the required system performance.

Each asset owner ensures that capacity requirements are identified for the critical systems for which they are responsible. They can be defined in system documentation, in the Asset inventory, or in the BeFresh-ICTInventory.

Each system manager ensures capacity management, including the fulfilment of capacity requirements.

In order to ensure the required system performance, the CIO runs scripts on the system that continually monitor the current capacity state. Based on the results, the CIO is able to take necessary action to ensure the required system performance.

Planned monitoring should be implemented to indicate problems in due time. Monitoring and system tuning are part of the measures to ensure and improve the availability and efficiency of systems.

Further projections of future capacity requirements should take account of new business and system requirements.

Managing capacity includes:

deletion of obsolete and of temporary data (disk space);

decommissioning of applications, systems, databases, or environments;

optimizing batch processes and schedules;

optimizing application logic or database queries;

denying or restricting bandwidth for resource-hungry services if these are not critical business (e.g. video streaming).

Note that capacity management also addresses the capacity of the human resources as well as the offices and facilities. Thus, the responsibility stated above for system manager also applies to facility manager and department managers.

### Protection against malware [A8.07]

#Attributes: #Preventive #Detective #Corrective #Confidentiality #Integrity #Availability #Protect #Detect #System\_and\_network\_security #Information\_protection #Protection #Defence

Protection against malware shall be implemented and supported by appropriate user awareness.

To ensure information and other associated assets are protected against malware.

Protection against malware is based on malware detection and repair software, information security awareness, appropriate system access and change management controls. Use of malware detection and repair software alone is not usually adequate. The following guidance should be considered:



- implementing rules and controls that prevent or detect the use of unauthorized software [e.g. application allowlisting, (i.e. using a list providing allowed applications)] (See sections 8.19 and 8.32 );

implementing controls that prevent or detect the use of known or suspected malicious websites (e.g. blocklisting);

reducing vulnerabilities that can be exploited by malware [e.g. through technical vulnerability management (See 8.8 and 8.19)];

conducting regular automated validation of the software and data content of systems, especially for systems supporting critical business processes; investigating the presence of any unapproved files or unauthorized amendments;

establishing protective measures against risks associated with obtaining files and software either from or via external networks or on any other medium;

installing and regularly updating malware detection and repair software to scan computers and electronic storage media. Carrying out regular scans that include:

scanning any data received over networks or via any form of electronic storage media, for malware before use;

scanning email and instant messaging attachments and downloads for malware before use. Carrying out this scan at different places (e.g. at email servers, desktop computers) and when entering the network of BeFresh;

scanning webpages for malware when accessed;

determining the placement and configuration of malware detection and repair tools based on risk assessment outcomes and considering:

defence in depth principles where they would be most effective. For example, this can lead to malware detection in a network gateway (in various application protocols such as email, file transfer and web) as well as user endpoint devices and servers;

the evasive techniques of attackers (e.g. the use of encrypted files) to deliver malware or the use of encryption protocols to transmit malware;

taking care to protect against the introduction of malware during maintenance and emergency procedures, which can bypass normal controls against malware;

implementing a process to authorize temporarily or permanently disable some or all measures against malware, including exception approval authorities, documented justification and review date. This can be necessary when the protection against malware causes disruption to normal operations;

preparing appropriate business continuity plans for recovering from malware attacks, including all necessary data and software backup (including both online and offline backup) and recovery measures (See 8.13);

isolating environments where catastrophic consequences can occur;

defining procedures and responsibilities to deal with protection against malware on systems, including training in their use, reporting and recovering from malware attacks;

providing awareness or training (See #6.3 in #6) to all users on how to identify and potentially mitigate the receipt, sending or installing of malware infected emails, files or programs [the information collected in n) and o) can be used to ensure awareness and training are kept up to date];

implementing procedures to regularly collect information about new malware, such as subscribing to mailing lists or reviewing relevant websites;

verifying that information relating to malware, such as warning bulletins, comes from qualified and reputable sources (e.g. reliable internet sites or suppliers of malware detection software) and is accurate and informative.

It is not always possible to install software that protects against malware on some systems (e.g. some industrial control systems). Some forms of malware infect computer operating systems and computer firmware such that common malware controls cannot clean the system and a full reimaging of the operating system software and sometimes the computer firmware is necessary to return to a secure state.

In order to protect the integrity of software and information, BeFresh implements controls against malicious software.

All Windows computers (laptops and desktops) belong to BeFresh (see in BeFresh-ICTInventory) are installed with antivirus software. The antivirus is configured to check and automatically install updates on a daily basis. Apart from the solutions shipped with the Operating System (OS), namely Microsoft security essentials, only antivirus software that is documented in the ICT asset inventory (https://befreshlu.atlassian.net/), BeFresh-AssetInventory #509A is authorized for use.

If a malware infection is detected, the OS will need to be reinstalled.

Furthermore, BeFresh uses firewalls to control all incoming and outgoing connections to the company’s network. Connecting to the information systems of the company via a computer that does not belong to the company (unless it is an authorized POD) is strictly forbidden.

Information security awareness training is organized to inform users about the different malware types and on applicable rules on how to behave to avoid the infection of critical systems with malware.

### Management of technical vulnerabilities [A8.08]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #identify #Protect #Threat\_and\_vulnerability\_management #Governance\_and\_Ecosystem #Protection #Defence

Information about technical vulnerabilities of information systems in use shall be obtained, BeFresh’s exposure to such vulnerabilities shall be evaluated and appropriate measures shall be taken.

To prevent exploitation of technical vulnerabilities.

Identifying technical vulnerabilities

BeFresh should have an accurate inventory of assets (See sections 5.9 and 5.14 in #5) as a prerequisite for effective technical vulnerability management; the inventory includes the software vendor, software name, version numbers, current state of deployment (e.g. what software is installed on what systems) and the person(s) within BeFresh responsible for the software.

To identify technical vulnerabilities, BeFresh should consider:



- defining and establishing the roles and responsibilities associated with technical vulnerability management, including vulnerability monitoring, vulnerability risk assessment, updating, asset tracking and any coordination responsibilities required;

for software and other technologies (based on the asset inventory list, see 5.9 in #5), identifying information resources that will be used for identifying relevant technical vulnerabilities and maintaining awareness about them. Updating the list of information resources based on changes in the inventory or when other new or useful resources are found;

requiring suppliers of information system (including their components) to ensure vulnerability reporting, handling and disclosure, including the requirements in applicable contracts (See 5.20 in #5);

using vulnerability scanning tools suitable for the technologies in use to identify vulnerabilities and to verify whether the patching of vulnerabilities was successful;

conducting planned, documented and repeatable penetration tests or vulnerability assessments by competent and authorized persons to support the identification of vulnerabilities. Exercising caution as such activities can lead to a compromise of the security of the system;

tracking the usage of third-party libraries and source code for vulnerabilities. This should be included in secure coding (See section 8.28).

BeFresh develops procedures and capabilities to:



- detect the existence of vulnerabilities in its products and services including any external component used in these;

receive vulnerability reports from internal or external sources.

BeFresh provides a public point of contact as part of a topic-specific policy on vulnerability disclosure so that researchers and others are able to report issues. BeFresh establishes vulnerability reporting procedures, online reporting forms and making use of appropriate threat intelligence or information sharing forums. BeFresh should also consider bug bounty programs where rewards are offered as an incentive to assist organizations in identifying vulnerabilities in order to appropriately remediate them. BeFresh also shares information with competent industry bodies or other interested parties.

Evaluating technical vulnerabilities

To evaluate identified technical vulnerabilities, the following guidance should be considered:



- analyse and verify reports to determine what response and remediation activity is needed;

once a potential technical vulnerability has been identified, identifying the associated risks and the actions to be taken. Such actions can involve updating vulnerable systems or applying other controls.

Taking appropriate measures to address technical vulnerabilities

A software update management process is implemented to ensure the most up-to-date approved patches and application updates are installed for all authorized software. If changes are necessary, the original software is retained and the changes applied to a designated copy. All changes are fully tested and documented, so that they can be reapplied, if necessary, to future software upgrades. If required, the modifications are tested and validated by an independent evaluation body.

The following guidance should be considered to address technical vulnerabilities:



- taking appropriate and timely action in response to the identification of potential technical vulnerabilities; defining a timeline to react to notifications of potentially relevant technical vulnerabilities;

depending on how urgently a technical vulnerability needs to be addressed, carrying out the action according to the controls related to change management (See 8.32) or by following information security incident response procedures (See section 5.26 in #5);

only using updates from legitimate sources (which can be internal or external to BeFresh);

testing and evaluating updates before they are installed to ensure they are effective and do not result in side effects that cannot be tolerated; [i.e. if an update is available, assessing the risks associated with installing the update (the risks posed by the vulnerability should be compared with the risk of installing the update)];

addressing systems at high risk first;

develop remediation (typically software updates or patches);

test to confirm if the remediation or mitigation is effective;

provide mechanisms to verify the authenticity of remediation;

if no update is available or the update cannot be installed, considering other controls, such as:

applying any workaround suggested by the software vendor or other relevant sources;

turning off services or capabilities related to the vulnerability;

adapting or adding access controls (e.g. firewalls) at network borders (See sections 8.20, 8.22)

shielding vulnerable systems, devices or applications from attack through deployment of suitable traffic filters (sometimes called virtual patching);

increasing monitoring to detect actual attacks;

raising awareness of the vulnerability.

For acquired software, if the vendors regularly release information about security updates for their software and provide a facility to install such updates automatically, BeFresh should decide whether to use the automatic update or not.

Other considerations

An audit log is kept for all steps undertaken in technical vulnerability management.

The technical vulnerability management process is regularly monitored and evaluated in order to ensure its effectiveness and efficiency.

An effective technical vulnerability management process is aligned with incident management activities, to communicate data on vulnerabilities to the incident response function and provide technical procedures to be carried out in case an incident occurs.

Where BeFresh uses a cloud service supplied by a third-party cloud service provider, technical vulnerability management of cloud service provider resources are ensured by the cloud service provider. The cloud service provider’s responsibilities for technical vulnerability management should be part of the cloud service agreement and this should include processes for reporting the cloud service provider's actions relating to technical vulnerabilities (See section 5.23 in #5). For some cloud services, there are respective responsibilities for the cloud service provider and the cloud service customer. For example, the cloud service customer is responsible for vulnerability management of its own assets used for the cloud services.

Technical vulnerability management can be viewed as a sub-function of change management and as such can take advantage of the change management processes and procedures (See 8.32).

There is a possibility that an update does not address the problem adequately and has negative side effects. Also, in some cases, uninstalling an update cannot be easily achieved once the update has been applied.

If adequate testing of the updates is not possible (e.g. because of costs or lack of resources) a delay in updating can be considered to evaluate the associated risks, based on the experience reported by other users. The use of ISO/IEC 27031 can be beneficial.

Where software patches or updates are produced, BeFresh can consider providing an automated update process where these updates are installed on affected systems or products without the need for intervention by the customer or the user. If an automated update process is offered, it can allow the customer or user to choose an option to turn off the automatic update or control the timing of the installation of the update.

Where the vendor provides an automated update process and the updates can be installed on affected systems or products without the need for intervention, BeFresh determines if it applies the automated process or not. One reason for not electing for automated update is to retain control over when the update is performed. For example, a software used for a business operation cannot be updated until the operation has completed.

A weakness with vulnerability scanning is that it is possible it does not fully account for defence in depth: two countermeasures that are always invoked in sequence can have vulnerabilities that are masked by strengths in the other. The composite countermeasure is not vulnerable, whereas a vulnerability scanner can report that both components are vulnerable. BeFresh should therefore take care in reviewing and acting on vulnerability reports.

Many organizations supply software, systems, products and services not only within BeFresh but also to interested parties such as customers, partners or other users. These software, systems, products and services can have information security vulnerabilities that affect the security of users.

Organizations can release remediation and disclose information about vulnerabilities to users (typically through a public advisory) and provide appropriate information for software vulnerability database services.

For more information relating to the management of technical vulnerabilities when using cloud computing, see the ISO/IEC 19086 series and ISO/IEC 27017.

ISO/IEC 29147 provides detailed information on receiving vulnerability reports and publishing vulnerability advisories. ISO/IEC 30111 provides detailed information about handling and resolving reported vulnerabilities.

Vulnerabilities that have been detected on systems coming from a supplier are reported to the supplier (if the vulnerability is not reported by them). A timeline is to be agreed with the supplier for the resolution of potential vulnerabilities.

If vulnerability is detected and no patch is available, possible workarounds are to be discussed and evaluated (e.g. possible risks linked to the implementation of a workaround). This is documented in the ticketing system https://befreshlu.atlassian.net/.

In general, the installation of patches follows the change management process and rules (see section 8.23).

The installation of patches follows the rules concerning the installation of software on operational systems #819.

A patch is not installed if the risk linked to the installation of the patch is evaluated as higher than the vulnerability itself (e.g. compatibility issues with installed software).

Information about system vulnerabilities of BeFresh systems is to be handled as restricted and as such not discussed in public environments nor communicated to persons that have no need to know.

System vulnerability are also monitored by BeFresh.

### Configuration management [A8.09]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #Protect #Secure\_configuration #Protection

Configurations, including security configurations, of hardware, software, services and networks shall be established, documented, implemented, monitored and reviewed.

To ensure hardware, software, services and networks function correctly with required security settings, and configuration is not altered by unauthorized or incorrect changes.

###### General

BeFresh defines and implements processes and tools to enforce the defined configurations (including security configurations) for hardware, software, services (e.g. cloud services) and networks, for newly installed systems as well as for operational systems over their lifetime.

Roles, responsibilities and procedures should be in place to ensure satisfactory control of all configuration changes.

###### Standard templates

Standard templates for the secure configuration of hardware, software, services and networks should be defined:



- using publicly available guidance (e.g. predefined templates from vendors and from independent security organizations);

considering the level of protection needed in order to determine a sufficient level of security;

supporting BeFresh’s information security policy, topic-specific policies, standards and other security requirements;

considering the feasibility and applicability of security configurations in BeFresh’s context.

The templates are reviewed periodically and updated when new threats or vulnerabilities need to be addressed, or when new software or hardware versions are introduced.

The following should be considered for establishing standard templates for the secure configuration of hardware, software, services and networks:



- minimizing the number of identities with privileged or administrator-level access rights;

disabling unnecessary, unused or insecure identities;

disabling or restricting unnecessary functions and services;

restricting access to powerful utility programs and host parameter settings;

synchronizing clocks;

changing vendor default authentication information such as default passwords immediately after installation and reviewing other important default security-related parameters;

invoking time-out facilities that automatically log off computing devices after a predetermined period of inactivity;

verifying that licence requirements have been met (See 5.32 in #5).

###### Managing configurations

Established configurations of hardware, software, services and networks are recorded and a log is maintained of all configuration changes. These records are securely stored. This can be achieved in various ways, such as configuration databases or configuration templates.

Changes to configurations should follow the change management process (See 8.32).

Configuration records can contain as relevant:



- up-to-date owner or point of contact information for the asset;

date of the last change of configuration;

version of configuration template;

relation to configurations of other assets.

###### Monitoring configurations

Configurations are monitored with a comprehensive set of system management tools (e.g. maintenance utilities, remote support, enterprise management tools, backup and restore software) and are reviewed on a regular basis to verify configuration settings, evaluate password strengths and assess activities performed. Actual configurations can be compared with the defined target templates. Any deviations should be addressed, either by automatic enforcement of the defined target configuration or by manual analysis of the deviation followed by corrective actions.

Documentation for systems often records details about the configuration of both hardware and software.

System hardening is a typical part of configuration management.

Configuration management can be integrated with asset management processes and associated tooling.

Automation is usually more effective to manage security configuration (e.g. using infrastructure as code).

Configuration templates and targets can be confidential information and should be protected from unauthorized access accordingly.

The configurations of the critical softwares and hardware used at BeFresh are maintained in ICT repository or BeFresh wiki in Confluence. The software configurations for other softwares are managed in a central location in Confluence for all staff to be accessed at any point of time^.

### Information deletion [A8.10]

#Attributes: #Preventive #Confidentiality #Protect #Information\_protection #Legal\_and\_compliance #Protection

Information stored in information systems, devices or in any other storage media shall be deleted when no longer required.

To prevent unnecessary exposure of sensitive information and to comply with legal, statutory, regulatory and contractual requirements for information deletion.

###### General

Sensitive information should not be kept for longer than it is required to reduce the risk of undesirable disclosure.

When deleting information on systems, applications and services, the following should be considered:



- selecting a deletion method (e.g. electronic overwriting or cryptographic erasure) in accordance with business requirements and taking into consideration relevant laws and regulations;

recording the results of deletion as evidence;

when using service suppliers of information deletion, obtaining evidence of information deletion from them.

Where third parties store BeFresh’s information on its behalf, BeFresh considers the inclusion of requirements on information deletion into the third-party agreements to enforce it during and upon termination of such services.

###### Deletion methods

In accordance with BeFresh’s topic-specific policy on data retention and taking into consideration relevant legislation and regulations, sensitive information is deleted when no longer required, by:



- configuring systems to securely destroy information when no longer required (e.g. after a defined period subject to the topic-specific policy on data retention or by subject access request);

deleting obsolete versions, copies and temporary files wherever they are located;

using approved, secure deletion software to permanently delete information to help ensure information cannot be recovered by using specialist recovery or forensic tools;

using approved, certified providers of secure disposal services;

using disposal mechanisms appropriate for the type of storage media being disposed of (e.g. degaussing hard disk drives and other magnetic storage media).

Where cloud services are used, BeFresh verifies if the deletion method provided by the cloud service provider is acceptable, and if it is the case, BeFresh should use it, or request that the cloud service provider delete the information. These deletion processes are automated in accordance with topic-specific policies, when available and applicable. Depending on the sensitivity of information deleted, logs can track or verify that these deletion processes have happened.

To avoid the unintentional exposure of sensitive information when equipment is being sent back to vendors, sensitive information is protected by removing auxiliary storage (e.g. hard disk drives) and memory before equipment leaves BeFresh’s premises.

Considering that the secure deletion of some devices (e.g. smartphones) can only be achieved through destruction or using the functions embedded in these devices (e.g. restore factory settings), BeFresh chooses the appropriate method according to the classification of information handled by such devices.

Control measures described in ISO/IEC 27002/2022 7.14 should be applied to physically destroy the storage device and simultaneously delete the information it contains.

An official record of information deletion is useful when analysing the cause of a possible information leakage event.

Information on user data deletion in cloud services can be found in ISO/IEC 27017.

Information on the deletion of PII can be found in ISO/IEC 27555.

A yearly archive deletion ticket is generated in Jira as part of the Risk Treatment Plan. This ticket includes a checklist of actions assigned to all Heads of Departments (HoDs). To resolve the ticket, each HoD must ensure the permanent deletion of any customer or sensitive information stored on their physical devices.

Old and unused IT devices are equipped with encrypted disks and are securely stored as inventory in the ICT office. When devices previously used by former employees are reassigned, they are always formatted before being allocated to new users.

### Data masking [A8.11]

#Attributes: #Preventive #Confidentiality #Protect #Information\_protection #Protection

Data masking shall be used in accordance with BeFresh’s topic-specific policy on access control and other related topic-specific, and business requirements, taking applicable legislation into consideration.

To limit the exposure of sensitive data including PII, and to comply with legal, statutory, regulatory and contractual requirements.

Where the protection of sensitive data (e.g. PII) is a concern, BeFresh considers hiding such data by using techniques such as data masking, pseudonymization or anonymization.

Pseudonymization or anonymization techniques can hide PII, disguise the true identity of PII principals or other sensitive information, and disconnect the link between PII and the identity of the PII principal or the link between other sensitive information.

When using pseudonymization or anonymization techniques, it is verified that data has been adequately pseudonymized or anonymized. Data anonymization considers all the elements of the sensitive information to be effective. As an example, if not considered properly, a person can be identified even if the data that can directly identify that person is anonymised, by the presence of further data which allows the person to be identified indirectly.

Additional techniques for data masking include:



- encryption (requiring authorized users to have a key);

nulling or deleting characters (preventing unauthorized users from seeing full messages);

varying numbers and dates;

substitution (changing one value for another to hide sensitive data);

replacing values with their hash.

The following should be considered when implementing data masking techniques:



- not granting all users access to all data, therefore designing queries and masks in order to show only the minimum required data to the user;

there are cases where some data should not be visible to the user for some records out of a set of data; in this case, designing and implementing a mechanism for obfuscation of data (e.g. if a patient does not want hospital staff to be able to see all of their records, even in case of emergency, then the hospital staff are presented with partially obfuscated data and data can only be accessed by staff with specific roles if it contains useful information for appropriate treatment);

when data are obfuscated, giving the PII principal the possibility to require that users cannot see if the data are obfuscated (obfuscation of the obfuscation; this is used in health facilities, for example if the patient does not want personnel to see that sensitive information such as pregnancies or results of blood exams has been obfuscated);

any legal or regulatory requirements (e.g. requiring the masking of payment cards' information during processing or storage).

The following should be considered when using data masking, pseudonymization or anonymization:



- level of strength of data masking, pseudonymization or anonymization according to the usage of the processed data;

access controls to the processed data;

agreements or restrictions on usage of the processed data;

prohibiting collating the processed data with other information in order to identify the PII principal;

keeping track of providing and receiving the processed data.

Anonymization irreversibly alters PII in such a way that the PII principal can no longer be identified directly or indirectly.

Pseudonymization replaces the identifying information with an alias. Knowledge of the algorithm (sometimes referred to as the additional information) used to perform the pseudonymization allows for at least some form of identification of the PII principal. Such additional information should therefore be kept separate and protected.

While pseudonymization is therefore weaker than anonymization, pseudonymized datasets can be more useful in statistical research.

Data masking is a set of techniques to conceal, substitute or obfuscate sensitive data items. Data masking can be static (when data items are masked in the original database), dynamic (using automation and rules to secure data in real time) or on-the-fly (with data masked in an application’s memory).

Hash functions can be used in order to anonymize PII. In order to prevent enumeration attacks, they should always be combined with a salt function.

PII in resource identifiers and their attributes [e.g. file names, uniform resource locators (URLs)] should be either avoided or appropriately anonymized.

Additional controls concerning the protection of PII in public clouds are given in ISO/IEC 27018.

Additional information on de-identification techniques is available in ISO/IEC 20889.

### Data leakage prevention [A8.12]

#Attributes: #Preventive #Detective #Confidentiality #Protect #Detect #Information\_protection #Protection #Defence

Data leakage prevention measures shall be applied to systems, networks and any other devices that process, store or transmit sensitive information.

To detect and prevent the unauthorized disclosure and extraction of information by individuals or systems.

BeFresh considers the following to reduce the risk of data leakage:



- identifying and classifying information to protect against leakage (e.g. personal information, pricing models and product designs);

monitoring channels of data leakage (e.g. email, file transfers, mobile devices and portable storage devices);

acting to prevent information from leaking (e.g. quarantine emails containing sensitive information).

Data leakage prevention tools should be used to:



- identify and monitor sensitive information at risk of unauthorized disclosure (e.g. in unstructured data on a user’s system);

detect the disclosure of sensitive information (e.g. when information is uploaded to untrusted third-party cloud services or sent via email);

block user actions or network transmissions that expose sensitive information (e.g. preventing the copying of database entries into a spreadsheet).

BeFresh determines if it is necessary to restrict a user’s ability to copy and paste or upload data to services, devices and storage media outside of BeFresh. If that is the case, BeFresh implements technology such as data leakage prevention tools or the configuration of existing tools that allow users to view and manipulate data held remotely but prevent copy and paste outside of BeFresh’s control.

If data export is required, the data owner is allowed to approve the export and hold users accountable for their actions.

Taking screenshots or photographs of the screen should be addressed through terms and conditions of use, training and auditing.

Where data is backed up, care is taken to ensure sensitive information is protected using measures such as encryption, access control and physical protection of the storage media holding the backup.

Data leakage prevention is also considered to protect against the intelligence actions of an adversary from obtaining confidential or secret information (geopolitical, human, financial, commercial, scientific or any other) which can be of interest for espionage or can be critical for the community. The data leakage prevention actions is oriented to confuse the adversary’s decisions for example by replacing authentic information with false information, either as an independent action or as response to the adversary’s intelligence actions. Examples of these kinds of actions are reverse social engineering or the use of honeypots to attract attackers.

Data leakage prevention tools are designed to identify data, monitor data usage and movement, and take actions to prevent data from leaking (e.g. alerting users to their risky behaviour and blocking the transfer of data to portable storage devices).

Data leakage prevention inherently involves monitoring personnel’s communications and online activities, and by extension external party messages, which raises legal concerns that is considered prior to deploying data leakage prevention tools. There is a variety of legislation relating to privacy, data protection, employment, interception of data and telecommunications that is applicable to monitoring and data processing in the context of data leakage prevention.

Data leakage prevention can be supported by standard security controls, such as topic-specific policies on access control and secure document management (See section 5.12 and section 5.15 in #5).

The employees are encouraged to only use Confluence, ownCloud or SharePoint to share data and the public links are secured having password and expiration date.

### Information backup [A8.13]

#Attributes: #Corrective #Integrity #Availability #Recover #Continuity #Protection

Backup copies of information, software and systems shall be maintained and regularly tested in accordance with the agreed topic-specific policy on backup.

To enable recovery from loss of data or systems.

A topic-specific policy on backup is established to address BeFresh’s data retention and information security requirements.

Adequate backup facilities are provided to ensure that all essential information and software can be recovered following an incident or failure or loss of storage media.

Plans are developed and implemented for how BeFresh will back up information, software and systems, to address the topic-specific policy on backup.

When designing a backup plan, the following items should be taken into consideration:



- producing accurate and complete records of the backup copies and documented restoration procedures;

reflecting the business requirements of BeFresh (e.g. the recovery point objective, see 5.30), the security requirements of the information involved and the criticality of the information to the continued operation of BeFresh in the extent (e.g. full or differential backup) and frequency of backups;

storing the backups in a safe and secure remote location, at a sufficient distance to escape any damage from a disaster at the main site;

giving backup information an appropriate level of physical and environmental protection (see Clause 7 and 8.1) consistent with the standards applied at the main site;

regularly testing backup media to ensure that they can be relied on for emergency use when necessary. Testing the ability to restore backed-up data onto a test system, not by overwriting the original storage media in case the backup or restoration process fails and causes irreparable data damage or loss;

protecting backups by means of encryption according to the identified risks (e.g. in situations where confidentiality is of importance);

taking care to ensure that inadvertent data loss is detected before backup is taken.

Operational procedures monitor the execution of backups and address failures of scheduled backups to ensure completeness of backups according to the topic-specific policy on backups.

Backup measures for individual systems and services are regularly tested to ensure that they meet the objectives of incident response and business continuity plans (See section 5.30 in #5). This should be combined with a test of the restoration procedures and checked against the restoration time required by the business continuity plan. In the case of critical systems and services, backup measures cover all systems information, applications and data necessary to recover the complete system in the event of a disaster.

When BeFresh uses a cloud service, backup copies of BeFresh’s information, applications and systems in the cloud service environment should be taken. BeFresh determines if and how requirements for backup are fulfilled when using the information backup service provided as part of the cloud service.

The retention period for essential business information is determined, taking into account any requirement for retention of archive copies. BeFresh considers the deletion of information (See section 8.10) in storage media used for backup once the information’s retention period expires and takes into consideration legislation and regulations.

For further information on storage security including retention consideration, see ISO/IEC 27040.

Refer #813 BeFresh-BackupMgmt.

### Redundancy of information processing facilities [A8.14]

#Attributes: #Preventive #Availability #Protect #Continuity #Asset\_management #Protection #Resilience

Information processing facilities shall be implemented with redundancy sufficient to meet availability requirements.

To ensure the continuous operation of information processing facilities.

BeFresh identifies requirements for the availability of business services and information systems. BeFresh designs and implements systems architecture with appropriate redundancy to meet these requirements.

Redundancy can be introduced by duplicating information processing facilities in part or in their entirety (i.e. spare components or having two of everything). BeFresh plans and implements procedures for the activation of the redundant components and processing facilities. The procedures establish if the redundant components and processing activities are always activated, or in case of emergency, automatically or manually activated. The redundant components and information processing facilities ensure the same security level as the primary ones.

Mechanisms are in place to alert BeFresh to any failure in the information processing facilities, enable executing the planned procedure and allow continued availability while the information processing facilities are repaired or replaced.

BeFresh should consider the following when implementing redundant systems:



- contracting with two or more suppliers of network and critical information processing facilities such as internet service providers;

using redundant networks;

using two geographically separate data centres with mirrored systems;

using physically redundant power supplies or sources;

using multiple parallel instances of software components, with automatic load balancing between them (between instances in the same data centre or in different data centres);

having duplicated components in systems (e.g. CPU, hard disks, memories) or in networks (e.g. firewalls, routers, switches).

Where applicable, preferably in production mode, redundant information systems are tested to ensure the failover from one component to another component works as intended.

There is a strong relationship between redundancy and ICT readiness for business continuity (See section 5.30 in #5) especially if short recovery times are required. Many of the redundancy measures can be part of the ICT continuity strategies and solutions.

The implementation of redundancies can introduce risks to the integrity (e.g. processes of copying data to duplicated components can introduce errors) or confidentiality (e.g. weak security control of duplicated components can lead to compromise) of information and information systems, which need to be considered when designing information systems.

Redundancy in information processing facilities does not usually address application unavailability due to faults within an application.

With the use of public cloud computing, it is possible to have multiple live versions of information processing facilities, existing in multiple separate physical locations with automatic failover and load balancing between them.

Some of the technologies and techniques for providing redundancy and automatic fail-over in the context of cloud services are discussed in ISO/IEC TS 23167.

### Logging [A8.15]

#Attributes: #Detective #Confidentiality #Integrity #Availability #Detect #Information\_security\_event\_management #Protection #Defence

Logs that record activities, exceptions, faults and other relevant events shall be produced, stored, protected and analysed.

To record events, generate evidence, ensure the integrity of log information, prevent against unauthorized access, identify information security events that can lead to an information security incident and to support investigations.

###### General

BeFresh determines the purpose for which logs are created, what data is collected and logged, and any log-specific requirements for protecting and handling the log data. This should be documented in a topic-specific policy on logging.

Event logs include for each event, as applicable:



- user IDs;

system activities;

dates, times and details of relevant events (e.g. log-on and log-off);

device identity, system identifier and location;

network addresses and protocols.

The following events should be considered for logging:



- successful and rejected system access attempts;

successful and rejected data and other resource access attempts;

changes to system configuration;

use of privileges;

use of utility programs and applications;

files accessed and the type of access, including deletion of important data files;

alarms raised by the access control system;

activation and de-activation of security systems, such as anti-virus systems and intrusion detection systems;

creation, modification or deletion of identities;

transactions executed by users in applications. In some cases, the applications are a service or product provided or run by a third party.

It is important for all systems to have synchronized time sources (See section 8.17) as this allows for correlation of logs between systems for analysis, alerting and investigation of an incident.

###### Protection of logs

Users, including those with privileged access rights, should not have permission to delete or de-activate logs of their own activities. They can potentially manipulate the logs on information processing facilities under their direct control. Therefore, it is necessary to protect and review the logs to maintain accountability for the privileged users.

Controls aim to protect against unauthorized changes to log information and operational problems with the logging facility including:



- alterations to the message types that are recorded;

log files being edited or deleted;

failure to record events or over-writing of past recorded events if the storage media holding a log file is exceeded.

For protection of logs, the use of the following techniques are considered: cryptographic hashing, recording in an append-only and read-only file, recording in a public transparency file.

Some audit logs can be required to be archived because of requirements on data retention or requirements to collect and retain evidence (See section 5.28 in #5).

Where BeFresh needs to send system or application logs to a vendor to assist with debugging or troubleshooting errors, logs are de-identified where possible using data masking techniques (See section 8.11 #8) for information such as usernames, internet protocol (IP) addresses, hostnames or organization name, before sending to the vendor.

Event logs can contain sensitive data and personally identifiable information. Appropriate privacy protection measures should be taken (See section 5.34 in #5 and #2).

###### Log analysis

Log analysis covers the analysis and interpretation of information security events, to help identify unusual activity or anomalous behaviour, which can represent indicators of compromise.

Analysis of events should be performed by taking into account:



- the necessary skills for the experts performing the analysis;

determining the procedure of log analysis;

the required attributes of each security-related event;

exceptions identified through the use of predetermined rules [e.g. security information and event management (SIEM) or firewall rules, and intrusion detection systems (IDSs) or malware signatures];

known behaviour patterns and standard network traffic compared to anomalous activity and behaviour [user and entity behaviour analytics (UEBA)];

results of trend or pattern analysis (e.g. as a result of using data analytics, big data techniques and specialized analysis tools);

available threat intelligence.

Log analysis is supported by specific monitoring activities to help identify and analyse anomalous behaviour, which includes:



- reviewing successful and unsuccessful attempts to access protected resources [e.g. domain name system (DNS) servers, web portals and file shares];

checking DNS logs to identify outbound network connections to malicious servers, such as those associated with botnet command and control servers;

examining usage reports from service providers (e.g. invoices or service reports) for unusual activity within systems and networks (e.g. by reviewing patterns of activity);

including event logs of physical monitoring such as entrance and exit to ensure more accurate detection and incident analysis;

correlating logs to enable efficient and highly accurate analysis.

Suspected and actual information security incidents are identified (e.g. malware infection or probing of firewalls) and be subject to further investigation (e.g. as part of an information security incident management process, see 5.25 in #5).

System logs often contain a large volume of information, much of which is extraneous to information security monitoring. To help identify significant events for information security monitoring purposes, the use of suitable utility programs or audit tools to perform file interrogation can be considered.

Event logging sets the foundation for automated monitoring systems (See section 8.16) which are capable of generating consolidated reports and alerts on system security.

A SIEM tool or equivalent service can be used to store, correlate, normalize and analyse log information, and to generate alerts. SIEMs tend to require careful configuration to optimize their benefits. Configurations to consider include identification and selection of appropriate log sources, tuning and testing of rules and development of use cases.

Public transparency files for the recording of logs are used, for example, in certificate transparency systems. Such files can provide an additional detection mechanism useful for guarding against log tampering.

In cloud environments, log management responsibilities can be shared between the cloud service customer and the cloud service provider. Responsibilities vary depending on the type of cloud service being used. Further guidance can be found in ISO/IEC 27017.

Information system logs (including administrator logs) are stored on the company server and are only accessible by the CIO, the ICT team, and the MD.

Periodic system checks are carried out on the information system logs to detect any unauthorized processing of information or unusual behaviour. The BeFresh SIEM is in place for handling this.

Administrator and operator logs

The CIO and the ICT team regularly review system logs and report any uncommon activity from administrators and operators to the Security Event Team (SET).

Any suspicious activity is reported to the ICT team via an automated email.

### Monitoring activities [A8.16]

#Attributes: #Detective #Corrective #Confidentiality #Integrity #Availability #Detect #Respond #Information\_security\_event\_management #Defence

Networks, systems and applications shall be monitored for anomalous behaviour and appropriate actions taken to evaluate potential information security incidents.

To detect anomalous behaviour and potential information security incidents.

The monitoring scope and level is determined in accordance with business and information security requirements and taking into consideration relevant laws and regulations. Monitoring records are maintained for defined retention periods.

The following should be considered for inclusion within the monitoring system:



- outbound and inbound network, system and application traffic;

access to systems, servers, networking equipment, monitoring system, critical applications, etc.

critical or admin level system and network configuration files;

logs from security tools [e.g. antivirus, IDS, intrusion prevention system (IPS), web filters, firewalls, data leakage prevention];

event logs relating to system and network activity;

checking that the code being executed is authorized to run in the system and that it has not been tampered with (e.g. by recompilation to add additional unwanted code);

use of the resources (e.g. CPU, hard disks, memory, bandwidth) and their performance.

BeFresh establishes a baseline of normal behaviour and monitor against this baseline for anomalies. When establishing a baseline, the following should be considered:



- reviewing utilization of systems at normal and peak periods;

usual time of access, location of access, frequency of access for each user or group of users.

The monitoring systems are configured against the established baseline to identify anomalous behaviour, such as:



- unplanned termination of processes or applications;

activity typically associated with malware or traffic originating from known malicious IP addresses or network domains (e.g. those associated with botnet command and control servers);

known attack characteristics (e.g. denial of service and buffer overflows);

unusual system behaviour (e.g. keystroke logging, process injection and deviations in use of standard protocols);

bottlenecks and overloads (e.g. network queuing, latency levels and network jitter);

unauthorized access (actual or attempted) to systems or information;

unauthorized scanning of business applications, systems and networks;

successful and unsuccessful attempts to access protected resources (e.g. DNS servers, web portals and file systems);

unusual user and system behaviour in relation to expected behaviour.

Continuous monitoring via a monitoring tool is used. Monitoring is done in real time or in periodic intervals, subject to organizational need and capabilities. Monitoring tools include the ability to handle large amounts of data, adapt to a constantly changing threat landscape, and allow for real-time notification. The tools are also able to recognize specific signatures and data or network or application behaviour patterns.

Automated monitoring software is configured to generate alerts (e.g. via management consoles, email messages or instant messaging systems) based on predefined thresholds. The alerting system is tuned and trained on BeFresh’s baseline to minimize false positives. Personnel are dedicated to respond to alerts and should be properly trained to accurately interpret potential incidents. There should be redundant systems and processes in place to receive and respond to alert notifications.

Abnormal events are communicated to relevant parties in order to improve the following activities: auditing, security evaluation, vulnerability scanning and monitoring (See section 5.25 in #5). Procedures should be in place to respond to positive indicators from the monitoring system in a timely manner, in order to minimize the effect of adverse events (See section 5.26 in #5) on information security. Procedures are also established to identify and address false positives including tuning the monitoring software to reduce the number of future false positives.

Security monitoring can be enhanced by:

leveraging threat intelligence systems (See section 5.7 in #5);

leveraging machine learning and artificial intelligence capabilities;

using blocklists or allowlists;

undertaking a range of technical security assessments (e.g. vulnerability assessments, penetration testing, cyber-attack simulations and cyber response exercises), and using the results of these assessments to help determine baselines or acceptable behaviour;

using performance monitoring systems to help establish and detect anomalous behaviour;

leveraging logs in combination with monitoring systems.

Monitoring activities are often conducted using specialist software, such as intrusion detection systems. These can be configured to a baseline of normal, acceptable and expected system and network activities.

Monitoring for anomalous communications helps in the identification of botnets (i.e. set of devices under the malicious control of the botnet owner, usually used for mounting distributed denial of service attacks on other computers of other organizations). If the computer is being controlled by an external device, there is a communication between the infected device and the controller. BeFresh should therefore employ technologies to monitor for anomalous communications and take such action as necessary.

Any suspicious activity is reported to the ICT team via an automated email. This is managed by BeFresh SIEM.

### Clock synchronization [A8.17]

#Attributes: #Detective #Integrity #Protect #Detect #Information\_security\_event\_management #Protection #Defence

The clocks of information processing systems used by BeFresh shall be synchronized to approved time sources.

To enable the correlation and analysis of security-related events and other recorded data, and to support investigations into information security incidents.

External and internal requirements for time representation, reliable synchronization and accuracy is documented and implemented. Such requirements can be from legal, statutory, regulatory, contractual, standards and internal monitoring needs. A standard reference time for use within BeFresh is defined and considered for all systems, including building management systems, entry and exit systems and others that can be used to aid investigations.

A clock linked to a radio time broadcast from a national atomic clock or global positioning system (GPS) should be used as the reference clock for logging systems; a consistent, trusted date and time source to ensure accurate time-stamps. Protocols such as network time protocol (NTP) or precision time protocol (PTP) should be used to keep all networked systems in synchronization with a reference clock.

BeFresh can use two external time sources at the same time in order to improve the reliability of external clocks, and appropriately manage any variance.

Clock synchronization can be difficult when using multiple cloud services or when using both cloud and on-premise services. In this case, the clock of each service is monitored and the difference recorded in order to mitigate risks arising from discrepancies.

The correct setting of computer clocks is important to ensure the accuracy of event logs, which can be required for investigations or as evidence in legal and disciplinary cases. Inaccurate audit logs can hinder such investigations and damage the credibility of such evidence.

The server clock needs to be synchronized to effectively trace users’ actions on the server. The frequency of the synchronizations may depend on the clock drift but is required to occur at least once per day. The CIO keeps a record of the exact time of synchronization as it may be useful when it comes to analyzing logs.

For the LAN servers the clock will synchronize with LAN firewall.

### Use of privileged utility programs [A8.18]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #Protect #System\_and\_network\_security #Secure\_configuration #Application\_security #Protection

The use of utility programs that can be capable of overriding system and application controls shall be restricted and tightly controlled.

To ensure the use of utility programs does not harm system and application controls for information security.

The following guidelines for the use of utility programs that can be capable of overriding system and application controls are considered:



- limitation of the use of utility programs to the minimum practical number of trusted, authorized users (See section 8.2);

use of identification, authentication and authorization procedures for utility programs, including unique identification of the person who uses the utility program;

defining and documenting of authorization levels for utility programs;

authorization for ad hoc use of utility programs;

not making utility programs available to users who have access to applications on systems where segregation of duties is required;

removing or disabling all unnecessary utility programs;

at a minimum, logical segregation of utility programs from application software. Where practical, segregating network communications for such programs from application traffic;

limitation of the availability of utility programs (e.g. for the duration of an authorized change);

logging of all use of utility programs.

Most information systems have one or more utility programs that can be capable of overriding system and application controls, for example diagnostics, patching, antivirus, disk defragmenters, debuggers, backup and network tools.

The use of standard utility programs that might be capable of overriding system and application controls are restricted and tightly controlled.

By default, a session type of an employee is set to ‘standard user’. With this type of session, employees can use software and change system settings that do not affect the security of their computer.

For each system classified as confidential, and for each type of system classified as restricted, asset owners:



- identify and record these programs, for example: hexadecimal editors, database administration programs bypassing business applications, network sniffers, hacking tools, etc.

justify the use of such a program in case of precaution, it could be necessary to:

separate utility programs from application software;

limit the use of utility programs to a minimum number of privileged users (such as internal hacking team);

limit the availability of utility programs, for example limit the duration of change authorization.

log all utility program uses.

document the licensing levels for utility programs.

uninstall or disable all unnecessary utility programs.

not make these utility programs available to users.

monitor and tries to detect unauthorized use of such a program.

Additional information



- Most operating systems, applications or databases have one or more utility programs that can bypass the security measures of a system or application.

### Installation of software on operational systems [A8.19]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #Protect #Secure\_configuration #Application\_security #Protection

Procedures and measures shall be implemented to securely manage software installation on operational systems.

To ensure the integrity of operational systems and prevent exploitation of technical vulnerabilities.

The following guidelines are considered to securely manage changes and installation of software on operational systems:



- performing updates of operational software only by trained administrators upon appropriate management authorization (See section 8.5);

ensuring that only approved executable code and not development code or compilers is installed on operational systems;

only installing and updating software after extensive and successful testing (See sections 8.29 and 8.31);

updating all corresponding program source libraries;

using a configuration control system to keep control of all operational software as well as the system documentation;

defining a rollback strategy before changes are implemented;

maintaining an audit log of all updates to operational software;

archiving old versions of software, together with all required information and parameters, procedures, configuration details and supporting software as a contingency measure, and for as long as the software is required to read or process archived data.

Any decision to upgrade to a new release takes into account the business requirements for the change and the security of the release (e.g. the introduction of new information security functionality or the number and severity of information security vulnerabilities affecting the current version). Software patches are applied when they can help to remove or reduce information security vulnerabilities (See sections 8.8 and 8.19).

Computer software can rely on externally supplied software and packages (e.g. software programs using modules which are hosted on external sites), are monitored and controlled to avoid unauthorized changes, because they can introduce information security vulnerabilities.

Vendor supplied software used in operational systems is maintained at a level supported by the supplier. Over time, software vendors will cease to support older versions of software. BeFresh considers the risks of relying on unsupported software. Open-source software used in operational systems is maintained to the latest appropriate release of the software. Over time, open source code can cease to be maintained but is still available in an open-source software repository. BeFresh considers the risks of relying on unmaintained open source software when used in operational systems.

When suppliers are involved in installing or updating software, physical or logical access should only be given when necessary and with appropriate authorization. The supplier’s activities are monitored (See section 5.22 in #5).

BeFresh defines and enforces strict rules on which types of software users can install.

The privilege principle is applied to software installation on operational systems. BeFresh should identify what types of software installations are permitted (e.g. updates and security patches to existing software) and what types of installations are prohibited (e.g. software that is only for personal use and software whose pedigree with regard to being potentially malicious is unknown or suspect). These privileges are granted based on the roles of the users concerned.

The updating of the operational software, applications, and program libraries is performed only by authorized administrators (internal or from software supplier) having the necessary skills and knowledge. Applications and operating system software are only implemented after extensive and successful testing; which covers usability, security, effects on other systems and if possible, should be carried out on separate systems. In emergency, the tests may be reduced to a minimum, but this decision is authorized by the CIO or his backup.

Operational systems hold only approved executable code, and not development code or compilers.

A rollback strategy is in place before changes are implemented. An audit log should be maintained of all updates to operational program libraries.

Previous versions of application software are to be retained as a contingency measure. Old versions of software are archived, together with all required information and parameters, procedures, configuration details and supporting software for as long as the data are retained in the archive.

Old software versions that are no longer supported by a software vendor should be either updated to a supported version or no longer used.

Any decision to upgrade to a new release should take into account the security of the release, e.g. the introduction of new information security functionality or the number and severity of information security problems affecting this version. Software patches should be applied when they can help to remove or reduce information security weaknesses.

Restrictions on software installation

The rules concerning the installation of software as defined in the Code of conduct for data and IT users BeFresh-CodeConduct #3 shall be respected by all BeFresh staff members.

In general, only authorized software is installed by authorized system operators having sufficient knowledge and skills.

NOTE: The description above is mainly applicable for Operating systems. For other applications which are not installed by default the employees have to request the ICT admin using ticketing system.

### Networks security [A8.20]

#Attributes: #Preventive #Detective #Confidentiality #Integrity #Availability #Protect #Detect #System\_and\_network\_security #Protection

Networks and network devices shall be secured, managed and controlled to protect information in systems and applications.

To protect information in networks and its supporting information processing facilities from compromise via the network.

Controls are implemented to ensure the security of information in networks and to protect connected services from unauthorized access. In particular, the following items are considered:



- the type and classification level of information that the network can support;

establishing responsibilities and procedures for the management of networking equipment and devices;

maintaining up to date documentation including network diagrams and configuration files of devices (e.g. routers, switches);

separating operational responsibility for networks from ICT system operations where appropriate (See section 5.3 in #5);

establishing controls to safeguard the confidentiality and integrity of data passing over public networks, third-party networks or over wireless networks and to protect the connected systems and applications (See sections 5.22 and 5.14 in #5, section 8.24 in #8 and 6.6 in #6). Additional controls can also be required to maintain the availability of the network services and computers connected to the network;

appropriately logging and monitoring to enable recording and detection of actions that can affect, or are relevant to, information security (See sections 8.15 and 8.16);

closely coordinating network management activities both to optimize the service to BeFresh and to ensure that controls are consistently applied across the information processing infrastructure;

authenticating systems on the network;

restricting and filtering systems connection to the network (e.g. using firewalls);

detecting, restricting and authenticating the connection of equipment and devices to the network;

hardening of network devices;

segregating network administration channels from other network traffic;

temporarily isolating critical subnetworks (e.g. with drawbridges) if the network is under attack;

disabling vulnerable network protocols.

BeFresh ensures that appropriate security controls are applied to the use of virtualized networks. Virtualized networks also cover software-defined networking (SDN, SD-WAN). Virtualized networks can be desirable from a security viewpoint, since they can permit logical separation of communication taking place over physical networks, particularly for systems and applications that are implemented using distributed computing.

Additional information on network security can be found in the ISO/IEC 27033 series.

More information concerning virtualized networks can be found in ISO/IEC TS 23167.

Network Controls

The network architecture of BeFresh reflects the company’s risk assessment and is designed to maximize security whilst maintaining a high level of business efficiency. Furthermore, it takes into account BeFresh’s specific requirements and it is continually kept under review.

The network is managed by the Chief Information Officer (CIO) and his or her dedicated substitute (sometimes also called deputy or backup). The CIO may choose to designate administrative tasks concerning the network to the members of the ICT department.

Network assets are inventoried and assigned a confidentiality degree by the network manager according to the security requirements BeFresh-AssetMgt #509, #710. This degree sets the maximum degree of information that can pass over this network.

The Network architecture is documented in ICT infrastructure BeFresh-ICTInfra #820A

In BeFresh network, the following requirements apply:



- only inventoried equipment, either supplied or authorized by BeFresh, are connected to the network, except for the guest Wi-Fi;

free outlets are disconnected from any default network. The activity of their connection or disconnection remains reserved to the ICT Department.

Free access computers e.g. in meeting rooms only provide access to the restricted internal public network (GUEST type network), but not to restrict LAN, such as the office LAN.

Should BeFresh outsource the operation of the computer network, in whole or in part, to a service provider which does not provide information security guarantees equivalent to those recommended in the security policy, the follows actions are either implemented or planned:



- define procedures and responsibilities for managing the networks;

define the operational responsibilities of the networks;

ensure, as far as possible, the separation of network management from the management of connected information systems;

implement special measures to ensure the confidentiality and integrity of information transmitted over public networks or wireless networks. Special measures may also be necessary to maintain the availability of network services;

monitor and log network traffic to detect and record actions that may affect the security of information;

closely coordinate management activities, both to optimize the service provided to BeFresh and to ensure that the measures are applied consistently across the entire information processing infrastructure;

authenticate the systems on the (internal) BeFresh network;

regularly review the configuration of the network equipment to detect and record any action that may affect the security of the information;

limit the connection of systems to the network.

Additional recommendations for network management and security are detailed in ISO/IEC 27033 - Information technology - Security techniques - Network security.

### Security of network services [A8.21]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #Protect #System\_and\_network\_security #Protection

Security mechanisms, service levels and service requirements of network services shall be identified, implemented and monitored.

To ensure security in the use of network services.

The security measures necessary for particular services, such as security features, service levels and service requirements, should be identified and implemented (by internal or external network service providers). BeFresh ensures that network service providers implement these measures.

The ability of the network service provider to manage agreed services in a secure way is determined and regularly monitored. The right to audit is agreed between BeFresh and the provider. BeFresh also considers third-party attestations provided by service providers to demonstrate they maintain appropriate security measures.

Rules on the use of networks and network services are formulated and implemented to cover:



- the networks and network services which are allowed to be accessed;

authentication requirements for accessing various network services;

authorization procedures for determining who is allowed to access which networks and networked services;

network management and technological controls and procedures to protect access to network connections and network services;

the means used to access networks and network services [e.g. use of virtual private network (VPN) or wireless network];

time, location and other attributes of the user at the time of the access;

monitoring of the use of network services.

The following security features of network services should be considered:



- technology applied for security of network services, such as authentication, encryption and network connection controls;

technical parameters required for secured connection with the network services in accordance with the security and network connection rules;

caching (e.g. in a content delivery network) and its parameters that allow users to choose the use of caching in accordance with performance, availability and confidentiality requirements;

procedures for the network service usage to restrict access to network services or applications, where necessary.

Network services include the provision of connections, private network services and managed network security solutions such as firewalls and intrusion detection systems. These services can range from simple unmanaged bandwidth to complex value-added offerings.

More guidance on a framework for access management is given in ISO/IEC 29146.

The ICT infrastructure standard BeFresh-ICTInfra #820 contains a detailed description and diagram of the BeFresh network architecture. It summarizes the different services provided by the network, security features implemented, and it also describes how networks segregation is performed.

Employees of BeFresh only have access to the network and network services for which they have been specifically authorized (cf. BeFresh-OrgChart #502O). Employees are provided by default with limited access rights to the shared services of BeFresh (See BeFresh-AccessControl #515 and section 8.2, 8.18).

### Segregation of networks [A8.22]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #Protect #System\_and\_network\_security #Protection

Groups of information services, users and information systems shall be segregated in BeFresh’s networks.

To split the network in security boundaries and to control traffic between them based on business needs.

BeFresh considers managing the security of large networks by dividing them into separate network domains and separating them from the public network (i.e. internet). The domains can be chosen based on levels of trust, criticality and sensitivity (e.g. public access domain, desktop domain, server domain, low- and high-risk systems), along organizational units (e.g. human resources, finance, marketing) or some combination (e.g. server domain connecting to multiple organizational units). The segregation can be done using either physically different networks or by using different logical networks.

The perimeter of each domain is well defined. If access between network domains is allowed, it is controlled at the perimeter using a gateway (e.g. firewall, filtering router). The criteria for segregation of networks into domains, and the access allowed through the gateways, is based on an assessment of the security requirements of each domain. The assessment should be in accordance with the topic-specific policy on access control (See section 5.15 in #5), access requirements, value and classification of information processed and take account of the relative cost and performance impact of incorporating suitable gateway technology.

Wireless networks require special treatment due to the poorly defined network perimeter. Radio coverage adjustment is considered for segregation of wireless networks. For sensitive environments, consideration is made to treat all wireless access as external connections and to segregate this access from internal networks until the access has passed through a gateway in accordance with network controls (See 8.20) before granting access to internal systems. Wireless access network for guests should be segregated from those for personnel if personnel only use controlled user endpoint devices compliant to BeFresh’s topic-specific policies. Wi-Fi for guests should have at least the same restrictions as Wi-Fi for personnel, in order to discourage the use of guest Wi-Fi by personnel.

Networks often extend beyond organizational boundaries, as business partnerships are formed that require the interconnection or sharing of information processing and networking facilities. Such extensions can increase the risk of unauthorized access to BeFresh’s information systems that use the network, some of which require protection from other network users because of their sensitivity or criticality.

Groups of information services, users and information systems are segregated on the networks of organizations, either in separate physical networks or in separate logical networks.

Networks qualified to the confidentiality degree restricted or higher are segregated with firewalls or routers. Their preliminary security analysis (by a penetration test or network audit) establishes that the segregation cannot be bypassed.

Any temporary or permanent connection of a device or system to a network qualified to the confidentiality degree confidential shall be analysed from a security point of view and then authorized by the CISO before connection by a network administrator.

To ensure internal network security and isolate unused access by network users to one or more of the information assets, the follows actions are either implemented or planned:

set up a segregation of the networks;

define the type of segregation and the perimeter of each domain in a standard often called ‘ICT infrastructure’ BeFresh-ICTInfra #820A;

allow access between different network domains, but control at perimeter level using a gateway (e.g. firewall or router);

verify that access authorization complies with established access rights;

treat all wireless access as external connections and separate them from access to internal networks.

### Web filtering [A8.23]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #Protect #System\_and\_network\_security #Protection

Access to external websites shall be managed to reduce exposure to malicious content.

To protect systems from being compromised by malware and to prevent access to unauthorized web resources.

BeFresh reduces the risks of its personnel accessing websites that contain illegal information or are known to contain viruses or phishing material. A technique for achieving this works by blocking the IP address or domain of the website(s) concerned. Some browsers and anti-malware technologies do this automatically or can be configured to do so.

BeFresh identifies the types of websites to which personnel should or should not have access. BeFresh considers blocking access to the following types of websites:



- websites that have an information upload function unless permitted for valid business reasons;

known or suspected malicious websites (e.g. those distributing malware or phishing contents);

command and control servers;

malicious website acquired from threat intelligence (See section 5.7 in #5);

websites sharing illegal content.

Prior to deploying this control, BeFresh establishes rules for safe and appropriate use of online resources, including any restriction to undesirable or inappropriate websites and web-based applications. The rules are kept up to date.

Training is given to personnel on the secure and appropriate use of online resources including access to the web. The training includes BeFresh’s rules, contact point for raising security concerns, and exception process when restricted web resources need to be accessed for legitimate business reasons. Training is also given to personnel to ensure that they do not overrule any browser advisory that reports that a website is not secure but allows the user to proceed.

Web filtering can include a range of techniques including signatures, heuristics, list of acceptable websites or domains, list of prohibited websites or domains and bespoke configuration to help prevent malicious software and other malicious activity from attacking BeFresh’s network and systems.

The browsers commonly in use Google Chrome and Safari all have built-in content filtering. The employees are advised not to visit any site which is blocked and use caution while visiting an unknown site. Alternately they are suggested to use Safe browsing in case of any suspicion.

### Use of cryptography [A8.24]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #Protect #Secure\_configuration #Protection

Rules for the effective use of cryptography, including cryptographic key management, shall be defined and implemented.

To ensure proper and effective use of cryptography to protect the confidentiality, authenticity or integrity of information according to business and information security requirements, and taking into consideration legal, statutory, regulatory and contractual requirements related to cryptography.

###### General

When using cryptography, the following should be considered:



- the topic-specific policy on cryptography defined by BeFresh, including the general principles for the protection of information. A topic-specific policy on the use of cryptography is necessary to maximize the benefits and minimize the risks of using cryptographic techniques and to avoid inappropriate or incorrect use;

identifying the required level of protection and the classification of the information and consequently establishing the type, strength and quality of the cryptographic algorithms required;

the use of cryptography for protection of information held on mobile user endpoint devices or storage media and transmitted over networks to such devices or storage media;

the approach to key management, including methods to deal with the generation and protection of cryptographic keys and the recovery of encrypted information in the case of lost, compromised or damaged keys;

roles and responsibilities for:

the implementation of the rules for the effective use of cryptography;

the key management, including key generation (See 8.24);

the standards to be adopted, as well as cryptographic algorithms, cipher strength, cryptographic solutions and usage practices that are approved or required for use in BeFresh;

the impact of using encrypted information on controls that rely on content inspection (e.g. malware detection or content filtering).

When implementing BeFresh’s rules for effective use of cryptography, the regulations and national restrictions that can apply to the use of cryptographic techniques in different parts of the world are taken into consideration as well as the issues of trans-border flow of encrypted information (See section 5.31 in #5).

The contents of service level agreements or contracts with external suppliers of cryptographic services (e.g. with a certification authority) cover issues of liability, reliability of services and response times for the provision of services (See section 5.22 in #5).

###### Key management

Appropriate key management requires secure processes for generating, storing, archiving, retrieving, distributing, retiring and destroying cryptographic keys.

A key management system is based on an agreed set of standards, procedures and secure methods for:



- generating keys for different cryptographic systems and different applications;

issuing and obtaining public key certificates;

distributing keys to intended entities, including how to activate keys when received;

storing keys, including how authorized users obtain access to keys;

changing or updating keys including rules on when to change keys and how this will be done;

dealing with compromised keys;

revoking keys including how to withdraw or deactivate keys [e.g. when keys have been compromised or when a user leaves an organization (in which case keys are also archived)];

recovering keys that are lost or corrupted;

backing up or archiving keys;

destroying keys;

logging and auditing of key management related activities;

setting activation and deactivation dates for keys so that the keys can only be used for the period of time according to BeFresh's rules on key management;

handling legal requests for access to cryptographic keys (e.g. encrypted information can be required to be made available in an unencrypted form as evidence in a court case).

All cryptographic keys are protected against modification and loss. In addition, secret and private keys need protection against unauthorized use as well as disclosure. Equipment used to generate, store and archive keys is physically protected.

In addition to integrity, for many use cases, the authenticity of public keys should also be considered.

The authenticity of public keys is usually addressed by public key management processes using certificate authorities and public key certificates, but it is also possible to address it by using technologies such as applying manual processes for small number keys.

Cryptography can be used to achieve different information security objectives, for example:

confidentiality: using encryption of information to protect sensitive or critical information, either stored or transmitted;

integrity or authenticity: using digital signatures or message authentication codes to verify the authenticity or integrity of stored or transmitted sensitive or critical information. Using algorithms for the purpose of file integrity checking;

non-repudiation: using cryptographic techniques to provide evidence of the occurrence or non-occurrence of an event or action;

authentication: using cryptographic techniques to authenticate users and other system entities requesting access to or transacting with system users, entities and resources.

The ISO/IEC 11770 series provides further information on key management.

Requirements

BeFresh implements this policy to protect its information, take advantage of the benefits of encryption, minimize associated risks, and avoid incorrect use of cryptographic measures.

BeFresh uses cryptography to achieve the following information security objectives:



- Confidentiality: using encryption of information to protect sensitive or critical information, either stored or transmitted.

Integrity/authenticity: using digital signatures or message authentication codes to verify the authenticity or integrity of stored or transmitted sensitive or critical information.

Non-repudiation: using cryptographic techniques to provide evidence of the occurrence or non-occurrence of an event or action.

Authentication: using cryptographic techniques to authenticate users and other system entities requesting access to or transacting with system users, entities and resources.

Cryptographic tools are selected, and their security features assessed before being used within the company. All cryptographic tools that have been validated and that are authorized for use are indicated in the cryptography tab of the asset inventory BeFresh-AssetInventory #509A.

Responsibilities

The Chief Information Officer (CIO) is responsible for:

selecting cryptographic tools and assessing their adequacy based on the requirements defined by the #CEO;

maintaining and ensuring compliance with the procedure related to cryptography BeFresh-UseOfCrypto #824.

The #CEO is responsible for:

validating the use of the cryptographic tools which are proposed by the CIO.

ensuring that the cryptographic tools that are used comply with BeFresh information security policy BeFresh-InfoSec #0, ISMS policies, as well as any relevant laws BeFresh-ListLegalReq #531;

maintaining the asset inventory BeFresh-AssetInventory #509A, BeFresh-ICTInventory (https://befreshlu.atlassian.net/) by updating the list of cryptographic tools whenever a tool is validated or revoked. The CISO also reviews the list on a yearly basis to ensure that it is up to date and correct.

All employees are responsible for:

compliance with the requirements of BeFresh ISMS and ensuring the proper and effective use of cryptography as and when it is required by the company.

Security rules for the use of cryptography

The following rules do not apply to cryptographic tools or algorithms applied to information that does not need to be protected with cryptographic algorithms.

For example, if a data transmission uses a certain cryptographic algorithm while the degree of information and the context do not require additional protection from the environment in which the data resides, then there is no rule concerning the cryptographic tools used for this transmission. On the other hand, if an interested party requests cryptographic protection or a high degree of protection, the choice of this protection corresponds to the rules mutually determined by BeFresh and the customer.

Analysis and compliance of cryptographic tools

To meet the need for cryptographic protection, BeFresh uses exclusively cryptographic tools analysed and recognized as compliant to this cryptography policy.

To implement a cryptographic algorithm, BeFresh uses exclusively tools (software packages or hardware) which are analysed and recognized compliant to this cryptography policy (see next section).

Such analysis involves an assessment by a cryptographic expert or a publication by a recognized cryptographic expert or an association for the certification or certification of cryptographic tools.

The analysis follows the following guidelines:

on the basis of a risk assessment, an adequate level of protection is identified taking into account the type, power and quality of the required encryption algorithm;

the analysis makes it possible to define rules for the use of the tool which are prerequisites for a proper use of the tool. These rules include instructions on key lengths to be used or specific management instructions.

It is recommended to refer to national or international certifications or approval for compliance recognition of a tool.

The list of cryptographic tools included in BeFresh-AssetInventory #509A does not intend to compare the different tools, but it highlights the result of the evaluation of the cryptographic properties and specifies which tools are compliant for the encryption of plaintext of a given degree, and what is the degree of classification of encrypted keys of messages.

The use of the cryptography procedure BeFresh-UseOfCrypto #824 clearly indicates the following processes related to cryptography:

request for a new cryptographic tool: BeFresh employees may request the use of a new cryptographic tool if they deem the currently authorized tools BeFresh-AssetInventory #509A, #710 are unable to meet their requirements;

cryptographic tool selection: the process of selecting a new cryptographic tool for use whilst ensuring it meets all the necessary security requirements of BeFresh;

cryptographic key management: the process for managing cryptographic keys throughout their entire lifecycle.

Proper use and responsibilities

When using compliant cryptographic tools, the user ensures to meet the rules related to these tools as defined or referred to in the list of authorized cryptographic tools BeFresh-AssetInventory #509A, #710.

Asset owners are responsible for assigning an important or vital degree of integrity to the cryptographic tools that are used to protect data of either a restricted or confidential level of confidentiality.

Technology watch

Regular monitoring checks the durability of the rules of use and cryptographic analyses:



- The CISO controls the proper use of cryptographic tools within BeFresh.

BeFresh, in collaboration with malware.lu CERT or the cryptographic experts of the R&amp;D department ensure technological monitoring of authorized tools.

Key inventory

BeFresh has established and maintains an inventory of the cryptographic keys under the responsibility of the CIO BeFresh-ListCryptoKeys #824K. The list of cryptographic keys BeFresh-ListCryptoKeys #824K includes the specifications of all public cryptographic keys used by BeFresh (especially the key length). The private keys are kept by the CIO in an encrypted solution, e.g. 1Password.

Cryptographic tools inventory and use

All cryptographic tools that are validated for use are listed in the ISMS standard BeFresh-AssetInventory #509A. It also contains or refers to management requirements. These are supplemented where necessary by specific documents (procedures or standards).

The use of cryptography procedures of BeFresh BeFresh-UseOfCrypto #824 defines the general requirements for the key management.

Key holder responsibilities

Sinc keys are considered to be assets, the owner of the assets protected by the key should be appointed as the key owner. If a key protects the data of several managers, the CIO or the CISO acts as the key owner, who is   together with the key manager, responsible to:

define appropriate management rules for keys, including key lifetime;

verify that these rules meet the requirements for the cryptographic tools for which they will be used;

monitor compliance with these rules;

establish and update key inventory.

Note: If a number of employees use individual keys, such as a LuxTrust signature card, the inventory does not contain all the cards, but only the type of cards and any additional rules to follow:

generate and obtain public key certificates;

assign keys to intended users and indicate the mode of activation or use upon receipt of keys;

store keys, including defining how authorized users can access keys;

updating or replacing keys, including rules on when to change keys and how to proceed;

revoke the keys, in particular define the modes of withdrawal or deactivation of the keys;

retrieve lost or altered keys;

save or archive keys;

destroy keys;

journaling and auditing key management activities.

Note: The manager does not know the value of this key in all cases. There are schemes in which a key could be broken down into several parts held by separate key managers and managed according to specific rules that ensure that the key is known only within certified equipment. In this case, nobody knows the value of the key, unless simultaneous fraud of several managers or vulnerabilities that are not detected during the certification.

Requirements for the key lifecycle management

For cryptographic keys protecting confidential or restricted data, BeFresh has implemented a procedure for the key lifecycle in terms of:

key generation;

storage;

archiving;

extraction;

attribution;

withdrawal;

destruction.

Cryptographic keys with the exception of public keys, are classified to the degree of confidentiality yellow or red according to the impacts in case of disclosure. These keys are protected against unauthorized use and unauthorized disclosure. The cryptographic material of BeFresh is also physically protected. In our key management policy, we have considered the ISO/IEC 11770 standard.

Recourse to the eIDAS certificate

In addition to the secure management of secret and private keys, BeFresh takes into account the authentication requirements of public keys that can be implemented using public key certificates issued by a certified certification authority that complies with European regulations #ISO/IEC11770-6:2016.

Cryptographic service providers

Service agreements or contracts with external providers of cryptographic services cover the following aspects:

legal responsibilities;

reliability of services;

responsiveness in the provision of these services.

Database with confidential data

BeFresh ensures that access to database containing confidential data require strong authentication, such as LuxTrust tools.

Specific recommendations and controls

BeFresh recommend that cryptographic controls are applied as far as possible to:

the data in transit over untrusted, unsecured, public, shared or distributed networks;

mobile hard disks (e.g. laptop);

removable storage media (portable hard drives, USB drives);

emails as soon as the data sent has the confidential privacy level;

databases hosted by an external provider;

data in cloud systems hosted and managed by an external service provider;

backup and archive media stored in an environment not controlled by the manager;

smartphones used in a professional context.

All BeFresh project partnership agreements and customer contracts should contain a clause indicating that BeFresh is not liable to make sure that the tools BeFresh uses (involving cryptography) can be used outside of the EU.

When signing agreements with companies outside of the EU, BeFresh follows export regulations regarding restrictions on cryptography BeFresh-ListLegalReq #531.

Cryptographic certificates are contained in the ICT Inventory BeFresh-ListCryptoKeys #824K in the "cryptographic certificate" tab. The role of the #CEO is to check the validity of these certificates on a periodic basis. After each verification a ticket (https://befreshlu.atlassian.net/) will have to be opened planning the next verification of the certificate.

### Secure development life cycle [A8.25]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #Protect #Application\_security #System\_and\_network\_security #Protection

Rules for the secure development of software and systems shall be established and applied.

To ensure information security is designed and implemented within the secure development life cycle of software and systems.

Secure development is a requirement to build up a secure service, architecture, software and system. To achieve this, the following aspects should be considered:



- separation of development, test and production environments (See section 8.31);

guidance on the security in the software development life cycle:

security in the software development methodology (See sections 8.27 and 8.28 );

secure coding guidelines for each programming language used (See section 8.28);

security requirements in the specification and design phase (See section 5.8 in #5);

security checkpoints in projects (See section 5.8 in #5);

system and security testing, such as regression testing, code scan and penetration tests (See section 8.29);

secure repositories for source code and configuration (See sections 8.4and 8.9);

security in the version control (See 8.32);

required application security knowledge and training (See 8.28);

developers’ capability for preventing, finding and fixing vulnerabilities (See 8.28);

licensing requirements and alternatives to ensure cost-effective solutions while avoiding future licensing issues (See 5.32 in #5).

If development is outsourced, BeFresh obtains assurance that the supplier complies with BeFresh’s rules for secure development (See 8.30).

Development can also take place inside applications, such as office applications, scripting, browsers and databases.

The following rules for the development of software and systems are applied to developments within BeFresh.



- The development environment is secured similarly as the production environment;

The software development lifecycle ensures:

security in the software development methodology;

secure coding guidelines for each programming language used;

security requirements are documented in the design phase;

security is assessed at the following project milestones;

before a system is analysed;

before a system is purchased; and

before the system is put into production.

secure repositories for storing project documentation and source code;

secure version control;

training of project managers on application security;

training on developers’ capability of avoiding, finding and fixing vulnerabilities;

If development is outsourced, BeFresh asks assurance that the external party complies with these rules on secure development (see [8.30]).

Note that this also covers office applications, scripting, browsers, and databases.

To ensure secure development, the following standards or methodologies are followed during development:

the use of OWASP methodologies and best security practices #OWASP-CODEREVIEW-URL, whenever the application is qualified as confidential;

Furthermore, the following aspects should be considered:

security requirements in the design phase;

security checkpoints within the project milestones;

required application security knowledge;

capability of avoiding, finding and fixing vulnerabilities. Note that projects can also be carried out using a methodology other than Scrum. In such a case, the project shall contain a sufficient description of the methodology used and this methodology shall ensure the implementation of information security within the development project.

Note that projects can also be carried out using a methodology other than Scrum. In such a case, the project shall contain a sufficient description of the methodology used and this methodology shall ensure the implementation of information security within the development project.

### Application security requirements [A8.26]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #Protect #Application\_security #System\_and\_network\_security #Protection #Defence

Information security requirements shall be identified, specified and approved when developing or acquiring applications.

To ensure all information security requirements are identified and addressed when developing or acquiring applications.

###### General

Application security requirements are identified and specified. These requirements are usually determined through a risk assessment. The requirements are developed with the support of information security specialists.

Application security requirements can cover a wide range of topics, depending on the purpose of the application.

Application security requirements should include, as applicable:



- level of trust in identity of entities [e.g. through authentication (See section 5.17 in #5, sections 8.2 and 8.5)];

identifying the type of information and classification level to be processed by the application;

need for segregation of access and level of access to data and functions in the application;

resilience against malicious attacks or unintentional disruptions [e.g. protection against buffer overflow or structured query language (SQL) injections];

legal, statutory and regulatory requirements in the jurisdiction where the transaction is generated, processed, completed or stored;

need for privacy associated with all parties involved;

the protection requirements of any confidential information;

protection of data while being processed, in transit and at rest;

need to securely encrypt communications between all involved parties;

input controls, including integrity checks and input validation;

automated controls (e.g. approval limits or dual approvals);

output controls, also considering who can access outputs and its authorization;

restrictions around content of 'free-text' fields, as these can lead to uncontrolled storage of confidential data (e.g. personal data);

requirements derived from the business process, such as transaction logging and monitoring, nonrepudiation requirements;

requirements mandated by other security controls (e.g. interfaces to logging and monitoring or data leakage detection systems);

error message handling.

###### Transactional services

Additionally, for applications offering transactional services between BeFresh and a partner, the following should be considered when identifying information security requirements:



- the level of trust each party requires in each other’s claimed identity;

the level of trust required in the integrity of information exchanged or processed and the mechanisms for identification of lack of integrity (e.g. cyclic redundancy check, hashing, digital signatures);

authorization processes associated with who can approve contents of, issue or sign key transactional documents;

confidentiality, integrity, proof of dispatch and receipt of key documents and the non-repudiation (e.g. contracts associated with tendering and contract processes);

the confidentiality and integrity of any transactions (e.g. orders, delivery address details and confirmation of receipts);

requirements on how long to maintain a transaction confidential;

insurance and other contractual requirements.

###### Electronic ordering and payment applications

Additionally, for applications involving electronic ordering and payment, the following should be considered:



- requirements for maintaining the confidentiality and integrity of order information;

the degree of verification appropriate to verify payment information supplied by a customer;

avoidance of loss or duplication of transaction information;

storing transaction details outside of any publicly accessible environment (e.g. on a storage platform existing on BeFresh intranet, and not retained and exposed on electronic storage media directly accessible from the internet);

where a trusted authority is used (e.g. for the purposes of issuing and maintaining digital signatures or digital certificates) security is integrated and embedded throughout the entire end-to-end certificate or signature management process.

Several of the above considerations can be addressed by the application of cryptography (See 8.24), taking into consideration legal requirements (See sections 5.31 to 5.36 in #5 for cryptography legislation).

Applications accessible via networks are subject to a range of network related threats, such as fraudulent activities, contract disputes or disclosure of information to the public; incomplete transmission, misrouting, unauthorized message alteration, duplication or replay. Therefore, detailed risk assessments and careful determination of controls are indispensable. Controls required often include cryptographic methods for authentication and securing data transfer.

Further information on application security can be found in the ISO/IEC 27034 series.

The needs for application security and transactional security can be satisfied in one of two ways: either by creating a new application from scratch or by using an existing framework that satisfies security requirements.

At BeFresh, frameworks that already satisfy security requirements are analysed and compared. Once the analysis is found to be satisfactory, they are then used in development or database applications. To cite an example, Spring frameworks (Spring MVC, Spring Security) and Hibernate (ORM), Symfony, Wordpress and Drupal are used for development and database management framework for BeFresh’s software products. We also use tools to analyse the code for security issues and follow the best practice for each programming language.

Information involved in application services passing over public networks is protected from fraudulent activity, contract dispute and unauthorized disclosure and modification.

Information security considerations for application services passing over public networks should include the following:

the level of confidence each party requires in each other’s claimed identity, e.g. through authentication;

authorization processes associated with who may approve contents of, issue or sign key transactional documents;

ensuring that communicating partners are fully informed of their authorizations for provision or use of the service;

determining and meeting requirements for confidentiality, integrity, proof of dispatch and receipt of key documents and the non-repudiation of contracts, e.g. associated with tendering and contract processes;

the level of trust required in the integrity of key documents;

the protection requirements of any confidential information;

the confidentiality and integrity of any order transactions, payment information, delivery address details and confirmation of receipts;

the degree of verification appropriate to verify payment information supplied by a customer;

selecting the most appropriate settlement form of payment to guard against fraud;

the level of protection required to maintain the confidentiality and integrity of order information;

avoidance of loss or duplication of transaction information;

liability associated with any fraudulent transactions;

insurance requirements.

Many of the above considerations can be addressed by the application of cryptographic controls, taking into account compliance with legal requirements.

Application service arrangements between partners are referred to in a documented agreement which commits both parties to the agreed terms of services, including details of authorization.

Resilience requirements against attacks should be considered, which can include requirements for protecting the involved application servers or ensuring the availability of network interconnections required to deliver the service.

Protecting application services transactions

Information involved in application service transactions is protected to prevent incomplete transmission, mis-routing, unauthorized message alteration, unauthorized disclosure, unauthorized message duplication or replay.

Concerning application services transactions, the following additional security requirements are studied:

the use of electronic signatures by each of the parties involved in the transaction;

all aspects of the transaction, i.e. ensuring that the:

secret authentication information of all parties is valid and verified;

transaction remains confidential;

privacy associated with all parties involved is retained;

communication paths between all involved parties are encrypted;

protocols used to communicate between all involved parties are secured;

ensuring that the storage of the transaction details is located outside of any publicly accessible environment, e.g. on a storage platform existing on the intranet of BeFresh, and not retained and exposed on a storage medium directly accessible from the Internet;

where a trusted authority is used (e.g. for the purposes of issuing and maintaining digital signatures or digital certificates) security is integrated and embedded throughout the entire end-to-end certificate/signature management process.

### Secure system architecture and engineering principles [A8.27]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #Protect #Application\_security #System\_and\_network\_security #Protection

Principles for engineering secure systems shall be established, documented, maintained and applied to any information system development activities.

To ensure information systems are securely designed, implemented and operated within the development life cycle.

Security engineering principles are established, documented and applied to information system engineering activities. Security is designed into all architecture layers (business, data, applications and technology). New technology is analysed for security risks and the design is reviewed against known attack patterns.

Secure engineering principles provide guidance on user authentication techniques, secure session control and data validation and sanitization.

Secure system engineering principles should include analysis of:



- the full range of security controls required to protect information and systems against identified threats;

the capabilities of security controls to prevent, detect or respond to security events;

specific security controls required by particular business processes (e.g. encryption of sensitive information, integrity checking and digitally signing information);

where and how security controls are to be applied (e.g. by integrating with a security architecture and the technical infrastructure);

how individual security controls (manual and automated) work together to produce an integrated set of controls.

Security engineering principles should take account of:



- the need to integrate with a security architecture;

technical security infrastructure [e.g. public key infrastructure (PKI), identity and access management (IAM), data leakage prevention and dynamic access management];

capability of BeFresh to develop and support the chosen technology;

cost, time and complexity of meeting security requirements;

current good practices.

Secure system engineering should involve:



- the use of security architecture principles, such as 'security by design', 'defence in depth', 'security by default', 'default deny', 'fail securely', 'distrust input from external applications', 'security in deployment', 'assume breach', 'least privilege', 'usability and manageability' and 'least functionality';

a security-oriented design review to help identify information security vulnerabilities, ensure security controls are specified and meet security requirements;

documentation and formal acknowledgement of security controls that do not fully meet requirements (e.g. due to overriding safety requirements);

hardening of systems.

BeFresh considers 'zero trust' principles such as:



- assuming BeFresh’s information systems are already breached and thus not be reliant on network perimeter security alone;

employing a 'never trust and always verify' approach for access to information systems;

ensuring that requests to information systems are encrypted end-to-end;

verifying each request to an information system as if it originated from an open, external network, even if these requests originated internal to BeFresh (i.e. not automatically trusting anything inside or outside its perimeters);

using 'least privilege' and dynamic access control techniques (See sections 5.15 and 5.18 in #5 and section 8.2). This includes authenticating and authorizing requests for information or to systems based on contextual information such as authentication information (See section 5.17 in #5), user identities (See section 5.16 in #5), data about the user endpoint device, and data classification (See #512);

always authenticating requesters and always validating authorization requests to information systems based on information including authentication information (See 5.17 in #5) and user identities (5.16), data about the user endpoint device, and data classification (See section 5.12 in #5), for example enforcing strong authentication (e.g. multi-factor, see 8.5).

The established security engineering principles are applied, where applicable, to outsourced development of information systems through the contracts and other binding agreements between BeFresh and the supplier to whom BeFresh outsources. BeFresh ensures that suppliers’ security engineering practices align with BeFresh’s needs.

The security engineering principles and the established engineering procedures are regularly reviewed to ensure that they are effectively contributing to enhanced standards of security within the engineering process. They are also regularly reviewed to ensure that they remain up to date in terms of combatting any new potential threats and in remaining applicable to advances in the technologies and solutions being applied.

Secure engineering principles can be applied to the design or configuration of a range of techniques, such as:

fault tolerance and other resilience techniques;

segregation (e.g. through virtualization or containerization);

tamper resistance.

Secure virtualization techniques can be used to prevent interference between applications running on the same physical device. If a virtual instance of an application is compromised by an attacker, only that instance is affected. The attack has no effect on any other application or data.

Tamper resistance techniques can be used to detect tampering of information containers, whether physical (e.g. a burglar alarm) or logical (e.g. a data file). A characteristic of such techniques is that there is a record of the attempt to tamper with the container. In addition, the control can prevent the successful extraction of data through its destruction (e.g. device memory can be deleted).

Principles for engineering secure systems are established, documented, maintained and applied to any information system implementation efforts.

Secure system engineering principles are applied during the development phase of information systems and applications.

The following standards are used:

as stated in chapter 8.25, use of OWASP Code review guide, #OWASP-CODEREVIEW-URL is recommended when developing applications that have input/output interfaces;

common criteria should be used when designing and developing applications or information systems involving hardware components.

Vulnerabilities in application services on public networks classified as Confidential or Important are analysed using the OWASP methodology (owasp.org).

### Secure coding [A8.28]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #Protect #Application\_security #System\_and\_network\_security #Protection

Secure coding principles shall be applied to software development.

To ensure software is written securely thereby reducing the number of potential information security vulnerabilities in the software.

###### General

BeFresh establishes organization-wide processes to provide good governance for secure coding. A minimum secure baseline is established and applied. Additionally, such processes and governance are extended to cover software components from third parties and open source software.

BeFresh monitors real world threats and up-to-date advice and information on software vulnerabilities to guide BeFresh’s secure coding principles through continual improvement and learning. This can help with ensuring effective secure coding practices are implemented to combat the fast-changing threat landscape.

###### Planning and before coding

Secure coding principles are used both for new developments and in reuse scenarios. These principles are applied to development activities both within BeFresh and for products and services supplied by BeFresh to others. Planning and prerequisites before coding include:



- organization-specific expectations and approved principles for secure coding to be used for both in-house and outsourced code developments;

common and historical coding practices and defects that lead to information security vulnerabilities;

configuring development tools, such as integrated development environments (IDE), to help enforce the creation of secure code;

following guidance issued by the providers of development tools and execution environments as applicable;

maintenance and use of updated development tools (e.g. compilers);

qualification of developers in writing secure code;

secure design and architecture, including threat modelling;

secure coding standards and where relevant mandating their use;

use of controlled environments for development.

###### During coding

Considerations during coding should include:



- secure coding practices specific to the programming languages and techniques being used;

using secure programming techniques, such as pair programming, refactoring, peer review, security iterations and test-driven development;

using structured programming techniques;

documenting code and removing programming defects, which can allow information security vulnerabilities to be exploited;

prohibiting the use of insecure design techniques (e.g. the use of hard-coded passwords, unapproved code samples and unauthenticated web services).

Testing is conducted during and after development (See section 8.29). Static application security testing (SAST) processes can identify security vulnerabilities in software.

Before software is made operational, the following should be evaluated:



- attack surface and the principle of least privilege;

conducting an analysis of the most common programming errors and documenting that these have been mitigated.

Review and maintenance

After code has been made operational:



- updates are securely packaged and deployed;

reported information security vulnerabilities are handled (See section 8.8);

errors and suspected attacks are logged and logs regularly reviewed to make adjustments to the code as necessary;

source code is protected against unauthorized access and tampering (e.g. by using configuration management tools, which typically provide features such as access control and version control).

If using external tools and libraries, organizations should consider:



- ensuring that external libraries are managed (e.g. by maintaining an inventory of libraries used and their versions) and regularly updated with release cycles;

selection, authorization and reuse of well-vetted components, particularly authentication and cryptographic components;

the licence, security and history of external components;

ensuring that software is maintainable, tracked and originates from proven, reputable sources;

sufficiently long-term availability of development resources and artefacts.

Where a software package needs to be modified the following points should be considered:



- the risk of built-in controls and integrity processes being compromised;

whether to obtain the consent of the vendor;

the possibility of obtaining the required changes from the vendor as standard program updates;

the impact if BeFresh becomes responsible for the future maintenance of the software as a result of changes;

compatibility with other software in use.

A guiding principle is to ensure security-relevant code is invoked when necessary and is tamper-resistant. Programs installed from compiled binary code also have these properties but only for data held within the application. For interpreted languages, the concept only works when the code is executed on a server that is otherwise inaccessible by the users and processes that use it, and that its data is held in a similarly protected database. For example, the interpreted code can be run on a cloud service where access to the code itself requires administrator privileges. Such administrator access should be protected by security mechanisms such as just-in-time administration principles and strong authentication. If the application owner can access scripts by direct remote access to the server, so in principle can an attacker. Webservers should be configured to prevent directory browsing in such cases.

Application code is best designed on the assumption that it is always subject to attack, through error or malicious action. In addition, critical applications can be designed to be tolerant of internal faults. For example, the output from a complex algorithm can be checked to ensure that it lies within safe bounds before the data is used in an application such as a safety or financial critical application. The code that performs the boundary checks is simple and therefore much easier to prove correctness.

Some web applications are susceptible to a variety of vulnerabilities that are introduced by poor design and coding, such as database injection and cross-site scripting attacks. In these attacks, requests can be manipulated to abuse the webserver functionality.

More information on ICT security evaluation can be found in the ISO/IEC 15408 series.

BeFresh follows a development procedure aligned with ISO 12207: #ORG-SSDLC, #828.

### Security testing in development and acceptance [A8.29]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #Identify #Application\_security #Information\_security\_assurance #System\_and\_network\_security #Protection

Security testing processes shall be defined and implemented in the development life cycle.

To validate if information security requirements are met when applications or code are deployed to the production environment.

New information systems, upgrades and new versions are thoroughly tested and verified during the development processes. Security testing should be an integral part of the testing for system or components.

Security testing is conducted against a set of requirements, which can be expressed as functional or non-functional. Security testing includes testing of:



- security functions [e.g. user authentication (See section 8.5), access restriction (See 8.3) and use of cryptography (See 8.24)];

secure coding (See section 8.28);

secure configurations (See sections 8.9, 8.20, 8.22) including that of operating systems, firewalls and other security components.

Test plans are determined using a set of criteria. The extent of testing should be in proportion to the importance, nature of the system and the potential impact of the change being introduced. The test plan includes:



- detailed schedule of activities and test;

inputs and expected outputs under a range of conditions;

criteria to evaluate the results;

decision for further actions as necessary.

BeFresh can leverage automated tools, such as code analysis tools or vulnerability scanners, and verifies the remediation of security-related defects.

For in-house developments, such tests are initially performed by the development team. Independent acceptance testing is then undertaken to ensure that the system works as expected and only as expected (See section 5.8 in #5). The following should be considered:



- performing code review activities as a relevant element for testing for security flaws, including unanticipated inputs and conditions;

performing vulnerability scanning to identify insecure configurations and system vulnerabilities;

performing penetration testing to identify insecure code and design.

For outsourced development and purchasing components, an acquisition process is followed. Contracts with the supplier address the identified security requirements (See 5.20). Products and services are evaluated against these criteria before acquisition.

Testing is performed in a test environment that matches the target production environment as closely as possible to ensure that the system does not introduce vulnerabilities to BeFresh’s environment and that the tests are reliable (See 8.31).

Multiple test environments can be established, which can be used for different kinds of testing (e.g. functional and performance testing). These different environments can be virtual, with individual configurations to simulate a variety of operating environments.

Testing and monitoring of test environments, tools and technologies also needs to be considered to ensure effective testing. The same considerations apply to monitoring of the monitoring systems deployed in development, test and production settings. Judgement is needed, guided by the sensitivity of the systems and data, to determine how many layers of meta-testing are useful.

Testing of security functionality is carried out during development.

Security functionality testing phase is an important step to reduce the risk of regression in the security features of information systems. Based on the list of security requirements defined in chapter 14, tests are done during development by developers, by product owners during validation, and by hacking teams before being released. Testing methods include source code review #OWASP-CODEREVIEW-URL, vulnerability penetration tests, and test automation (unit testing and functional testing).

Before moving from one environment to another, e.g. from development to testing or from testing to production environments, information systems pass all testing activities defined during the development process. This includes activities previously mentioned (source code review, vulnerability pentests, test automation).

In order to verify that a system meets the security requirements penetration tests can be performed.

Acceptance testing programs and related criteria are established for new information systems, upgrades and new versions.

System acceptance testing includes testing of information security requirements (see 8.26) and adherence to secure system development practices (see 8.25). The testing is also conducted on received components and integrated systems. BeFresh uses automated tools, such as ‘Nessus’ which is a network vulnerability scanner and ‘Software checker’ which checks software vulnerabilities BeFresh-SoftwareMgt #819, and verifies the remediation of security-related defects by using ticketing system https://befreshlu.atlassian.net/.

Testing is performed in a realistic test environment to ensure that the system will not introduce vulnerabilities to the environment of BeFresh and that the tests are reliable BeFresh-ChangeMgt #832, BeFresh-SoftwareMgt #819.

### Outsourced development [A8.30]

#Attributes: #Preventive #Detective #Confidentiality #Integrity #Availability #Identify #Protect #Detect #System\_and\_network\_security #Application\_security #Supplier\_relationships\_security #Governance\_and\_Ecosystem #Protection

BeFresh shall direct, monitor and review the activities related to outsourced system development.

To ensure information security measures required by BeFresh are implemented in outsourced system development.

Where system development is outsourced, BeFresh communicates and agrees requirements and expectations, and continually monitor and review whether the delivery of outsourced work meets these expectations. The following points are considered across BeFresh’s entire external supply chain:



- licensing agreements, code ownership and intellectual property rights related to the outsourced content (See section 5.32 in #5);

contractual requirements for secure design, coding and testing practices (See sections 8.25 and 8.29);

provision of the threat model to consider by external developers;

acceptance testing for the quality and accuracy of the deliverables (See section 8.29 in #8);

provision of evidence that minimum acceptable levels of security and privacy capabilities are established (e.g. assurance reports);

provision of evidence that sufficient testing has been applied to guard against the presence of malicious content (both intentional and unintentional) upon delivery;

provision of evidence that sufficient testing has been applied to guard against the presence of known vulnerabilities;

escrow agreements for the software source code (e.g. if the supplier goes out of business);

contractual right to audit development processes and controls;

security requirements for the development environment (See section 8.31);

taking consideration of applicable legislation (e.g. on protection of personal data).

Further information on supplier relationships can be found in the ISO/IEC 27036 series.

Outsourced development

The project manager using outsourced development in his project supervises and monitors the activity of outsourced system development and included in the project documentation the following aspects:



- licensing arrangements, code ownership and intellectual property rights related to the outsourced content;

contractual requirements for secure design, coding and testing practices (see 8.25);

provision of the approved threat model to the external developer;

acceptance testing for the quality and accuracy of the deliverables;

provision of evidence that security thresholds were used to establish minimum acceptable levels of security and privacy;

provision of evidence that sufficient testing has been applied to guard against the absence of both intentional and unintentional malicious content upon delivery;

provision of evidence that sufficient testing has been applied to guard against the presence of known vulnerabilities;

escrow arrangements, e.g. if source code is no longer available;

contractual rights to audit development processes and controls;

effective documentation of the build environment used to create deliverables;

BeFresh remains responsible for compliance with applicable laws and control efficiency verification.

Note: BeFresh uses many softwares that are open source but currently we do not have dedicated outsourced software.

### Separation of development, test and production environments [A8.31]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #Protect #Application\_security #System\_and\_network\_security #Protection

Development, testing and production environments shall be separated and secured.

To protect the production environment and data from compromise by development and test activities.

The level of separation between production, testing and development environments that is necessary to prevent production problems are identified and implemented.

The following items should be considered:



- adequately separating development and production systems and operating them in different domains (e.g. in separate virtual or physical environments);

defining, documenting and implementing rules and authorization for the deployment of software from development to production status;

testing changes to production systems and applications in a testing or staging environment prior to being applied to production systems (See section 8.29);

not testing in production environments except in circumstances that have been defined and approved;

compilers, editors and other development tools or utility programs not being accessible from production systems when not required;

displaying appropriate environment identification labels in menus to reduce the risk of error;

not copying sensitive information into the development and testing system environments unless equivalent controls are provided for the development and testing systems.

In all cases, development and testing environments should be protected considering:



- patching and updating of all the development, integration and testing tools (including builders, integrators, compilers, configuration systems and libraries);

secure configuration of systems and software;

control of access to the environments;

monitoring of change to the environment and code stored therein;

secure monitoring of the environments;

taking backups of the environments.

A single person should not have the ability to make changes to both development and production without prior review and approval. This can be achieved for example through segregation of access rights or through rules that are monitored. In exceptional situations, additional measures such as detailed logging and real time monitoring should be implemented in order to detect and act on unauthorized changes.

Without adequate measures and procedures, developers and testers having access to production systems can introduce significant risks (e.g. unwanted modification of files or system environment, system failure, running unauthorized and untested code in production systems, disclosure of confidential data, data integrity and availability issues). There is a need to maintain a known and stable environment in which to perform meaningful testing and to prevent inappropriate developer access to the production environment.

Measures and procedures include carefully designed roles in conjunction with implementing segregation of duty requirements and having adequate monitoring processes in place.

Development and testing personnel also pose a threat to the confidentiality of production information. Development and testing activities can cause unintended changes to software or information if they share the same computing environment. Separating development, testing and production environments is therefore desirable to reduce the risk of accidental change or unauthorized access to production software and business data (See section  8.33 in #8 for the protection of test information).

In some cases, the distinction between development, test and production environments can be deliberately blurred and testing can be carried out in a development environment or through controlled rollouts to live users or servers (e.g. small population of pilot users). In some cases, product testing can occur through live use of the product inside BeFresh. Furthermore, to reduce downtime of live deployments, two identical production environments can be supported where only one is live at any one time.

Supporting processes for the use of production data in development and testing environments (8.33) are necessary.

Organizations can also consider the guidance provided in this section for training environments when conducting end user training.

Development and testing environments of BeFresh are separated from operational (production) environment in order to reduce the risk of unauthorized access or changes to the operational environment. Development and operational environments are segregated by one (or a combination) of the following:

running on separate computer systems;

running on different domains;

secure disposal of data information used in testing environment;

use of temporary testing credentials.

It is recommended that the environments be separated in accordance with the following principles:



- The transition of software from the development or external delivery stage to the operational stage follows documented rules and is justified by tests.

Production and development software are operated on logically distinct environments.

The test and acceptance environment operates as closely as possible to the production environment.

No sensitive data is shared between the test environment and the production environment. The test environment includes its own data set.

User profiles allowing access to production systems are different from those for test systems.

No compilers are installed in the production environment.

The menus display different colours for the windows depending on the environment in order to reduce the risk of error, e.g. performing a test operation when the user is on a window in a production environment.

Secure development environment (cf 27002 :2017 14.2.6)

Additionally, separation of access control is maintained to ensure that no individual can gain administrator level of access to the BeFresh systems. An example of the BeFresh development process and release management for TRICK Service is available at BeFresh-ReleaseMgt #825.

### Change management [A8.32]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #Protect #Application\_security #System\_and\_network\_security #Protection

Changes to information processing facilities and information systems shall be subject to change management procedures.

To preserve information security when executing changes.

Introduction of new systems and major changes to existing systems follows agreed rules and a formal process of documentation, specification, testing, quality control and managed implementation. Management responsibilities and procedures is in place to ensure satisfactory control of all changes.

Change control procedures are documented and enforced to ensure the confidentiality, integrity and availability of information in information processing facilities and information systems, for the entire system development life cycle from the early design stages through all subsequent maintenance efforts.

Wherever practicable, change control procedures for ICT infrastructure and software is integrated.

The change control procedures includes:



- planning and assessing the potential impact of changes considering all dependencies;

authorization of changes;

communicating changes to relevant interested parties;

tests and acceptance of tests for the changes (See section 8.29);

implementation of changes including deployment plans;

emergency and contingency considerations including fallback procedures;

maintaining records of changes that include all of the above;

ensuring that operating documentation (See section 5.37 in #5) and user procedures are changed as necessary to remain appropriate;

ensuring that ICT continuity plans and response and recovery procedures (See 5.30 in #5) are changed as necessary to remain appropriate.

Inadequate control of changes to information processing facilities and information systems is a common cause of system or security failures. Changes to the production environment, especially when transferring software from development to operational environment, can impact on the integrity and availability of applications.

Changing software can impact the production environment and vice versa.

Good practice includes the testing of ICT components in an environment segregated from both the production and development environments (See 8.31). This provides a means of having control over new software and allowing additional protection of operational information that is used for testing purposes. This should include patches, service packs and other updates.

Production environment includes operating systems, databases and middleware platforms. The control should be applied for changes of applications and infrastructures.

Change management control

The following items are considered when planning changes:

Every significant change is recorded in ticketing system https://befreshlu.atlassian.net/. Insignificant changes are recorded on the system by adding comments and storing the previous version at the same place (e.g. in the old folder).

After the approval of a change request, there is a person or team designated who is responsible to:

Plan the change and communicate change details with all affected parties.

Assess the potential impacts including the information security impacts of such changes. Potential information security impacts are reported to the ISMS.

Test changes before being executed.

Establish fallback procedures, including procedures and responsibilities for aborting and recovering from unsuccessful changes and unforeseen events.

Emergency changes

To enable a quick and controlled implementation of changes to resolve an incident, the heads of impacted BeFresh departments may decide to either skip or postpone to a later date some elements of the normal change management process.

Other references

In addition to the change management procedure BeFresh-ChangeMgt #832, the following ISMS standard contains detailed information regarding changes to BeFresh information processing facilities and systems:

Asset inventory BeFresh-AssetInventory #509A and the ICT inventory;

different user guides;

the manufacturer’s documentation.

The asset inventory is owned and maintained by the CISO. The ICT inventory is owned by the CIO and maintained by the ICT department (see the ICT team members in BeFresh-RoleAssignment #502).

System change control procedures

Changes to systems within the development lifecycle is controlled using formal change control procedures BeFresh-ChangeMgt #832.

A formal process of documentation, specification, testing, quality control and managed implementation is made prior to adding any new information system, or modification of an existing information system.

This process includes:

a risk assessment;

an analysis of the impacts of changes;

the specification of needed security controls.

The following aspects should also be considered:

maintaining a record of agreed authorization levels;

ensuring changes are submitted by authorized users;

reviewing controls and integrity procedures to ensure that they will not be compromised by the changes;

identifying all software, information, database entities and hardware that require amendment;

identifying and checking critical security code to minimize the likelihood of known security weaknesses;

obtaining formal approval for detailed proposals before work commences;

ensuring authorized users accept changes prior to implementation;

ensuring that the system documentation set is updated at the completion of each change and that old documentation is archived or disposed of;

maintaining version control for all software updates;

maintaining an audit trail of all change requests;

ensuring that operating documentation (see 5.37 in #5) and user procedures are changed as necessary to remain appropriate;

ensuring that the implementation of changes takes place at the right time and does not disturb the business processes involved.

Relevant actions are recorded in ticketing system https://befreshlu.atlassian.net/.

Technical review of applications after operating platform changes

When operating platforms are changed, business-critical applications are reviewed and tested to ensure there is no adverse impact on organizational operations or security.

During operations of information systems and applications, the following types of changes can occur:

security update of a server or service;

change of server technology.

If such changes occur, the following actions are performed:

review application control and integrity procedures to ensure that they have not been compromised by the operating platform changes;

notify operating platform changes in time to allow appropriate tests and reviews to take place before the implementation;

update business continuity plans accordingly.

Restrictions on changes to software packages

Modifications to software packages are discouraged, limited to necessary changes and all changes are strictly controlled.

Modification of software packages coming from external providers are avoided as knowledge of the software package may not be sufficient to prevent malfunctioning of the package after change. If the modification cannot be avoided, the following principles are considered:

the risk of built-in controls and integral processes being compromised;

whether the consent of the vendor is obtained;

the possibility of obtaining the required changes from the vendor as standard program updates;

the impact if BeFresh becomes responsible for the future maintenance of the software because of any changes;

compatibility issues.

### Test information [A8.33]

#Attributes: #Preventive #Confidentiality #Integrity #Protect #Information\_protection #Protection

Test information shall be appropriately selected, protected and managed.

To ensure relevance of testing and protection of operational information used for testing.

Test information is selected to ensure the reliability of tests results and the confidentiality of the relevant operational information. Sensitive information (including personally identifiable information) should not be copied into the development and testing environments (See section 8.31).

The following guidelines are applied to protect the copies of operational information, when used for testing purposes, whether the test environment is built in-house or on a cloud service:



- applying the same access control procedures to test environments as those applied to operational environments;

having a separate authorization each time operational information is copied to a test environment;

logging the copying and use of operational information to provide an audit trail;

protecting sensitive information by removal or masking (See section 8.11) if used for testing;

properly deleting (See section 8.10) operational information from a test environment immediately after the testing is complete to prevent unauthorized use of test information.

Test information is securely stored (to prevent tampering, which can otherwise lead to invalid results) and only used for testing purposes.

System and acceptance testing can require substantial volumes of test information that are as close as possible to operational information.

Test data are selected carefully, protected and controlled.

Test data are needed when testing information systems prior to release. This test data should not contain any sensitive information, i.e. be created from scratch as much as possible. In the case where the use of test data with sensitive information cannot be avoided, e.g. when a realistic set of test data is needed, the following additional information security requirements are applied:

the access control procedures, which apply to operational application systems, should also apply to test application systems;

there should be separate authorization each time operational information is copied to a test environment;

operational information should be erased from a test environment immediately after the testing is complete;

the copying and use of operational information should be logged to provide an audit trail.

### Protection of information systems during audit testing [A8.34]

#Attributes: #Preventive #Confidentiality #Integrity #Availability #Protect #System\_and\_network\_security #Information\_protection #Governance\_and\_Ecosystem #Protection

Audit tests and other assurance activities involving assessment of operational systems shall be planned and agreed between the tester and appropriate management.

To minimize the impact of audit and other assurance activities on operational systems and business processes.

The following guidelines are observed:



- agreeing audit requests for access to systems and data with appropriate management;

agreeing and controlling the scope of technical audit tests;

limiting audit tests to read-only access to software and data. If read-only access is not available to obtain the necessary information, executing the test by an experienced administrator who has the necessary access rights on behalf of the auditor;

if access is granted, establishing and verifying the security requirements (e.g. antivirus and patching) of the devices used for accessing the systems (e.g. laptops or tablets) before allowing the access;

only allowing access other than read-only for isolated copies of system files, deleting them when the audit is completed, or giving them appropriate protection if there is an obligation to keep such files under audit documentation requirements;

identifying and agreeing on requests for special or additional processing, such as running audit tools;

running audit tests that can affect system availability outside business hours;

monitoring and logging all access for audit and test purposes.

Audit tests and other assurance activities can also happen on development and test systems, where such tests can impact for example the integrity of code or lead to disclosure of any sensitive information held in such environments.

If information system audits are required, the following guidelines are observed to minimize disruptions to business processes:

audit requirements for access to systems and data are agreed with the CIO;

the scope of technical audit tests is agreed and controlled;

audit tests are limited to read-only access to software and data;

access other than read-only is only allowed for isolated copies of system files, which are erased when the audit is completed, or given appropriate protection if there is an obligation to keep such files under audit documentation requirements;

requirements for specific or additional treatments (such as an external intrusion tests) are identified and agreed;

audit tests do not impact on the availability of critical business processes;

all access is monitored and logged to produce a reference trail.