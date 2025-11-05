---
title: "Information Security Management System (ISMS)"
subtitle: "Asset classification scheme"
shortTitle: "(ITR-Classification)"
info:
  type: "Standard (STA)"
  reference: "#512"
  version: "1.3"
  status: "Final"
  owner: "C. Harpes"
  date: "13/01/2025"
  classification: "Internal"
abstract: | 
  Assets include anything of value to itrust consulting. The way itrust consulting manages its assets is of significant importance for the efficiency of daily operations. It is therefore important to explain how assets are classified and documented in inventories, detailing specifically the roles of actors, their responsibilities, and the procedures they must follow.
  There are many types of assets, including: a) information; b) systems (ICT) such as software packages, computer programs; c) physical assets, such as computers, offices; d) services; e) people, their qualifications, skills, and experiences; and f) intangible assets, such as reputation and image.
  Asset classification is the process of systematically dividing assets into different degrees based on the nature and risks associated with the assets. It serves to make a series of consistent rules applicable for managing assets at each degree.
  As this process is described in #509, this document specifies the different degrees to be assigned to assets and the criteria for assignment. This assignment, called classification (for informational assets or documents) or qualification for assets containing other assets, such as sites, systems, is done in three dimensions according to the degrees indicated in this cube:
---

# Document history 

|Version | Date | Author | Modifications|
|---|---|---|---|
|0.2|15/03/2023|C. Harpes|Document creation as extract from former POL_08|
|1.0|15/03/2023|A. Chezganova|Updated Final version|
|1.0.1|5/04/2023|A. Chezganova|Conformity check done, no major nonconformities found, changes implemented directly in the document|
|1.0.2|22/05/2023<B. Hodzic|Changed “Degree” to “Level” of availability, 1week and 4week changed to 1w and 4w|
|1.1|04/04/2024|B. Hodzic|Management summary added, new chapter on asset types added, review and update of Confidentiality table and descriptions, new column added to the same table: Access condition, 1min availability changed to 15’ (‘=minute), cube modified, MD approval|
|1.1.1|09/07/2024|R. Pande|CC check performed. Following changes made while performing CC. 1. Added Cube in Mgmt summary 1. Updated AssetTypes aligning with OpenTRICK 1. Minor corrections in content can be chosen to be accepted.|
|1.1.2-3|29/07/2024|A. Chezganova|Quality review, added chapter 2.|
|1.2|21/10/2024|C. Harpes|Revision|
|1.2.1|19/11/2024|R. Pande|Aligned with changes in PGD procedure . Added specific rules for integrity and availability.|
|1.2.3|28/11/2024|B. Hodzic|In table integrity, columns “Management” and “Security rules and tools” merged into “Security measures and tools”, ch. 5.2 Business Continuity and Recovery parameters added, for approval|
|1.3|13/01/2024|C. Harpes|Revision|


# Introduction

## Context
Asset classification is the process of systematically dividing assets into different groups based on the nature of the assets, applying accounting rules to properly account for each group. These groups are subsequently consolidated for reporting.

Assets are anything that has value to the organization. How itrust consulting manages its assets is of significant importance to the efficient day-to-day operations of the business. It is therefore important to outline to the employees of itrust consulting, how assets are classified and stored in inventories; specifically detailing the roles of actors, their responsibilities, and the procedures they shall follow.

There are many types of assets, including: a) information; b) (ICT) systems such as software packages, computer program; c) physical assets, such as computer; offices; d) services; e) people, and their qualifications, skills, and experience; and f) intangibles, such as reputation and image.

In order to maintain the confidentiality, integrity and availability of its assets, itrust consulting has implemented a classification procedure to ensure the proper management of all assets within its ITR-AssetMgt #509 organization.

## Objectives


The objective of this document is to define the degree of classification and the principles to follow when classifying or qualifying assets.


## Scope


This document applies to all activities and all assets in the scope of the ISMS.


## Enforcement and reading instructions	


This document becomes effective once approved by the MD and published on the ISMS repository available to all employees of itrust consulting. It will remain in effect until revoked or revised by the Owner or the MD. Do not rely on a printed document, but rather check on the official documentation site of itrust consulting for the currently applicable version.

The MD’s signature is an official recognition of the mandatory character of this document. It is to be respected by all employees of itrust consulting and a failure to comply with the Information Security policy may be considered as a violation of the working contract and result in disciplinary action.

The use of the SIMPLE PRESENT tense or the terms ‘MUST’, ‘MANDATORY’, ‘REQUIRED’, or ‘SHALL’ in a statement means that the statement is considered a formal requirement.

The use of words such as ‘SHOULD’ or the adjective ‘RECOMMENDED’ means that there may be legitimate reasons to disregard the statement, but that the implications of such an exception shall be assessed and fully understood.
The terminology ‘MAY’ or the adjective ‘OPTIONAL’ means that the implementation of the statement is at the discretion of the implementer.



## Audience

The scheme shall be read and applied by all employees involved in asset management, including all user that should understand and remember the meaning of the different classification levels.

Asset owners are responsible for adequate classification of information assets and adequate qualification of container assets in line with the following principles and degrees, and to indicate this in the asset inventory. If no indication is provided in that inventory, the default classification provided below applies.

## Structure of the document

This document is structured as follows:
- Chapter 2 summarizes the main characteristics of the assets;
- Chapter 3 indicates the asset types;
- Chapter 4 indicates the principles of assets classification and qualification;
- Chapter 5 describes the classification scheme of assets.
	

## References

See [2] for all references of type ITR-… or with an ISMS document identifier starting with #...
[1] itrust consulting, ISMS, Information security policy (ITR-InfoSec), #0.
[2] itrust consulting, ISMS, Standard, List of documents (ITR-DocList), #0D.
[3] itrust consulting, ISMS, Standard, Glossary (ITR-Glossary), #0G.
[4] itrust consulting, ISMS, Policy, Organisational controls (ITR-OrgControls), #5.
[5] itrust consulting, ISMS, Procedure, Asset-management (ITR-AssetMgt), #509.
[6] itrust consulting, ISMS, Standard, Asset inventory (ITR-AssetInventory), 509A.
[7] ISO/IEC 27001:2022, Information technology – Security techniques – Information security management systems – Requirements.
[8] ISO/IEC 27002:2022, Information technology – Security techniques – Code of practice for information security controls.

## Acronyms CISO

Chief Information Security Officer ISMS
Information Security Management System RPO
Recovery Point Objective RT
Recovery Time RTO
Recovery Time Objective SLA
Service Level Agreement

## Glossary

For other descriptions of common terms used in this document, please refer to the general glossary of itrust consulting [3].


Asset
Anything that has value to the organization.
Note: There are many types of assets, including a) information; b) software, such as a computer program; c) physical, such as computers; d) services; e) people, and their qualifications, skills, and experience; and f) intangibles, such as the reputation and image. Availability
One of the three core elements of information security, along with confidentiality and integrity. Availability concerns the requirement for information, IT systems, people and processes to be operational and accessible when needed by the organization. Chief Information Security Officer (CISO)
The CISO is responsible for functional specifications and controls the implementation of provisions on information security. Classification
Convenient grouping of similar or related information assets that are likely to share similar information security risks and control requirements. Classification reduces the need individually to risk assessing and identify security controls needed to protect every single asset in each class. Classification typically relies on confidentiality criteria but more complex schemes may also take account of integrity and availability requirements. Qualification
Grouping according to the level of classification of similar or related containers that are likely to store information.
Process by which an asset that can be considered a container is assessed to be appropriate to store or process information classified to a given classification level. Confidentiality
One of the three core elements of information security, along with availability and integrity. Confidentiality essentially concerns secrecy or privacy. Container
Any logical or physical device used to store or transport goods or assets. Example: computer systems, hard disk, CD, cabinets, office building.ai
Note: Container is considered as a type of asset which needs qualification instead of classification. Information Security Management System (ISMS)
Part of the overall management system, based on a business risk approach, to establish, implement, operate, monitor, review, maintain and improve information security.



# Key elements of asset management

Assets include various elements that are essential for their effective management (more details in ITR-AssetMgt, #509):

- acronym (without spaces if made up of several words) and a full name ;
- asset type and a group (a sub-type) ;
- decision-maker, usually a person with the rank of director ;
- technical manager (usually the administrator), with a designated deputy if necessary;
- security indicators such as classification or qualification, priorities, continuity and recovery parameters;
- security rules and other important information:
	+ SLA if applicable ;
	+ location (the URL);
	+ brief description to provide an overview;
	+ specific rules, if any, that complement the general management rules that come from assigning classification levels.
	+ SLA, if recovery conditions have been imposed by a beneficiary;
	+ means of authentication, where applicable (generally concerns application assets);
- where applicable, a status indicating whether the asset is due to be decommissioned in the near future;
- management information (who has updated information).
	



# Asset types

The following asset types are based on asset types defined in the OpenTRICK tool used for performing Risk Assessment. The table below has been extracted from AssetType Tab in #509A ITR-AssetInventory. 

|Id |Short name| Type name| Acron. identifier| Example| Assigning a degree of|
|---|---|---|---|---|---|
|0|n.a.|n.a.|NN|For assets currently being identified|n.a.|
|1|Busi|Business process|BS|A service provided to customers, defined in ITR's missions | qualification|
|2|Compl|Conformity|CO| |n.a.| 
|3|Fin|Financial|FN| |n.a.|
|4|Info|Information|IN|Files, data exports, system data (configuration, business data)|classification |
|5|IV|Immaterial Value|IV| |n.a.|
|6|Out|Outsourced service|OR|Supplier contract...|qualification |
|7|Site|Site|ST|Building, rooms|qualification|
|8|SW|Software|SW|Software (either purchased, developed in-house, or delivered custom-made by a service provider) includes its documentation, but without the data processed by this software.|qualification|
|9|HW|Hardware|HW|Physical assets, such as computers, furniture, weapons and equipment|au choix
|10|Net|Network|NT|Computer networks (Wifi, LAN, Fiber...)|qualification|
|11|Serv|Service|SR|Internal services, such as application support for Microsoft AD, legal department support, often a set of people, a working structure, and documented (or undocumented) knowledge.|qualification|
|12|Staff|Personnel|PN|Individuals or groups of people in a business line or department; interns.|qualification|
|13|Sys|System|SY|A set of hardware, software and managed information|qualification|

Table 1: List of asset types



# Principles of classification and qualification


## 3D-classification

The proposed scheme requires that assets are classified with respect to three different factors:
1. Confidentiality.
1. Integrity.
1. Availability.
Figure 1: Three-dimensional classification scheme

## Classification according to impact

The scheme also proposes that assets are classified according to the impact of a security breach:

- the greater the impact of disclosure, the greater the classification of confidentiality;
- the greater the impact of a loss, the greater the classification of integrity;
- the greater the impact of allowing illegitimate access, the greater the classification of availability.
	
The classification can be determined by the level of impact that their compromise would have for the organization. Each level defined in the scheme is given a name that makes sense in the context of the classification scheme’s application.

To conclude, the greater the impact of a security-related incident on an asset, the higher the classification. By giving a high classification to an asset, we reduce the risk as we add management rules.

According to this principle, the classification may depend on the amount of data, e.g. a file containing the information of the power consumption of a single house in Luxembourg and a file containing the data of the power consumption of every household in Luxembourg has the same need for protection under the personal data protection law. The second file, however, will be placed in a greater class as the impact of disclosure is obviously much greater. Similarly, disclosure of personal information about a publicly known person can create much more damage than disclosing the same information about an unknown person.

The scheme is consistent across the whole organization and included in its procedures so that everyone classifies information and applicable other associated assets in the same way, so that everyone has a common understanding of protection requirements and so that everyone applies the appropriate protection.

The classification scheme used within the organization can be different from the schemes used by other organizations, even if the names for levels are similar. In addition, information moving between organizations can vary in classification depending on its context in each organization, even if their classification schemes are identical. Therefore, agreements with other organizations that include information sharing should include procedures to identify the classification of that information and to interpret the classification levels from other organizations. Correspondence between different schemes can be determined by looking for equivalence in the associated handling and protection methods. Classification provides people who deal with information with a concise indication of how to handle and protect it. Creating groups of information with similar protection needs and specifying information security procedures that apply to all the information in each group facilitates this. This approach reduces the need for case-by-case risk assessment and custom design of controls.

Information can cease to be sensitive or critical after a certain period of time. For example, when the information has been made public, it no longer has confidentiality requirements but can still require protection for its integrity and availability properties. These aspects should be taken into account, as over-classification can lead to the implementation of unnecessary controls resulting in additional expense or, on the contrary, under-classification can lead to insufficient controls to protect the information from compromise.

An example of an information confidentiality classification scheme can be based on four levels as follows:
1. disclosure causes no harm;
1. disclosure causes minor reputational damage or minor operational impact;
1. disclosure has a significant short-term impact on operations or business objectives;
1. disclosure has a serious impact on long-term business objectives or puts the survival of the organization at risk.

## Principles of inheritance

To simplify and optimize the classification, we use the principles of inheritance that avoid having to classify each asset separately:
- information always has the same classification regardless of the form it is in;
- an asset containing other assets will assume the classification of the asset with the highest classification.
	
Example: Information may exist in electronic form on the internet, in a file on a disk, in paper form stored in a cabinet or in an oral communication by telephone. If one of these forms of information is classified as confidential, then all the other forms will inherit the same classification. Exceptions: This is a default rule that is subject to exceptions in some cases as it is possible that information in the physical form, e.g. a signed letter, presents more of a risk than the same information told orally.



## Qualification of containers

The same classification scheme is applied to the containers; the physical locations where the assets are stored. Containers are assigned a particular classification which makes them qualified to store information relevant to that classification. The term ‘container’ is considered here in a broad sense and includes offices, cabinets, computer systems, hard drives, directories, databases, communication channels, internet, internal networks, USB sticks, etc. The aim of the qualification is to simplify container management rules and reduce them to the following rule: It is forbidden to place an asset in a container that has a lower classification than the asset.

Example: If a container is classified as internal, we cannot deposit a restricted file into it (or any file which has a higher classification than internal).

Clarification: There is a difference between the essential principle of inheritance and the classification and qualification of containers, e.g. a computer does not inherit the classification of its information. If a computer is classified confidential, it is not because the most critical information it contains is confidential, it is because the CISO believes that it has the necessary requirements to store confidential information.

In practice, it may well be that it does not contain confidential information, or that it contains secret information by mistake. In this case, it does not become a secret computer ‘by inheritance’. However, we consider the hard disk archive file as data and not as a container, so it inherits automatically the classification of the most critical element it contains.

## Default classification

It is sometimes difficult to ensure that the classification is complete and consistent because of the different interpretations of the various asset managers. For this reason, a default classification is used depending on where the asset is stored.

The default classification rules are as follows:

- all files containing customer information are classified as ‘Restricted’;
- all files that contain information from customers who have asked itrust consulting to sign a specific nondisclosure agreement are classified as ‘Confidential’.
	
The information stored in a container always have an equal or lower confidentiality degree than the degree of the container. On certain occasions, it may be necessary to create sub-folders in order to isolate confidential information from lower classified information. In this case, the sub-folder name should clearly indicate the classification, e.g. CO, SE.



# Security and continuity indicators


## Classification scheme

Figure 1 showed the three-dimensional classification scheme used by itrust consulting. This scheme considers the confidentiality, integrity, and availability of information. The different levels of each dimension are explained below.

### Confidentiality

Confidentiality defines the security required to protect information from unauthorized access and misuse.
The following table shows the official abbreviation, the name, and the description of the degrees of confidentiality. The chosen classification scheme is analogous to the information sharing traffic light protocol (ISTLP), defined by the British administration NISCC. These classifications define the rules for distribution of the information and critical infrastructure protection. This protocol has a wide acceptance in the CERT community. 

|Degree| Impact| Management| Access condition| Example of default classif.|
|---|---|---|---|---|
|SE, Secret| Disclosure would cause serious damage.|Managed according to established procedures. Stored only in an encrypted location under exclusive control of the holder.|Explicit agreement of line manager AND asset owner. Prior notification of all persons involved.|Information classified by law, e.g. EU, NATO, national, passwords. |
|CO, Confidential|Disclosure would cause significant damage (to itrust consulting or a person concerned).|Managed according to established procedures. Limited to authorized persons.|Agreement of the beneficiary's line manager AND the asset owner.|Banking secrecy, sensitive personal data (health), security incidents, contract management, etc. |
|RE, Restricted|Disclosure would cause damage or inconvenience.|Management on the basis of an employment contract, etc., distributed internally to "need-to-know" persons. nformation can be distributed outside the organization only with a signed confidentiality agreement.|Agreement of asset manager (defined in user profile) or asset owner.|Documentation or internal network diagram, program source. |
|IN, Internal|Disclosure could be detrimental.|Can be passed on to other entities within itrust consulting. Circulation, cannot be published or posted on the internet, nor distributed outside itrust consulting.|Available on request.|Prior information to manager.|User guide, operating procedures.|
|PU,Public|Disclosure would have no consequences.|Can circulate freely, as it is accessible to external parties Unlimited, subject to standard copyright rules, information can be distributed freely, without restriction.|Available to the public.|Various publications, information content of a website.|

Table 2: Degrees of confidentiality


#### Default confidentiality classification

It is sometimes difficult to ensure that the classification is complete and consistent because of the different interpretations of the various asset managers. For this reason, a default classification is used depending on where the asset is stored.

The default confidentiality classification rules are as follows:

- all files containing customer information are classified as RESTRICTED;
- all files that contain information from customers who have asked itrust consulting to sign a specific nondisclosure agreement are classified as CONFIDENTIAL;
- all files containing sensitive personal data (Health) are classified as SECRET;
- all files containing information of security incidents are classified as SECRET;
- all files that are quotes for customers, request for proposals from (potential) customers are classified as RESTRICTED;
- all files that document a layout, configuration or setup are classified as CONFIDENTIAL, extracts of such a file may be classified as RESTRICTED;
	

### Integrity

Integrity defines the level required to protect information from unauthorized alteration. These measures provide assurance in the accuracy and completeness of data. 

|Degree| Impact |Security measures and Tools |Example of default classif.|
|---|---|---|---|
|VIT, Vital|An amendment could result in significant losses to itrust consulting or the author of the amendment could benefit considerably.|Use of electronic signatures, physical safe. Integrity checks (hashing) or consistency checks (alerts for unusual data) where possible. Formal periodic inspection procedures (conducted weekly, maximum monthly). Exclusive access by explicit agreement of the asset owner AND the manager in charge of the person. Verification procedure (4-eye principle mandatory for all changes). For asset systems: a technical integrity control tool is mandatory. For service and business assets: documented verification of the segregation of roles in management procedures by the CISO or the MD. |Mail ‘DHL’, configuration of servers or storage elements, telephone lines.|
|IMP, Important|An amendment could result in a loss of efficiency or notable cost adjustments.|Limitations on write and delete access rights. Exclusive access with the explicit agreement of the asset manager AND the manager in charge of the person. Hashing and electronic signature. Dedicated process documented in a ticket for verifying integrity in the event of a change. Technical integrity control tool recommended. Formal procedures for periodic inspections are often implemented (about every three months).|Mail, encrypted email, client configuration (PC, laptop, etc.).|
|NOR, Normal|There are no additional security restraints in addition to the protection of privacy. |Access according to confidentiality rules. The rules imposed by the degree of confidentiality, supplemented by the rules of the security policies and procedures, are sufficient. Procedures for periodic monitoring are implemented regularly (about every 6 months to 1 year).|Internal mail, email, internet consulting, etc.

Table 3: Degrees of integrity. Each line inherits the rules of the lower level

### Availability

In order for an information system to be useful, it must be available to authorized users. Availability measures protect timely and uninterrupted access to the system. Depending on the type of asset, the rate of unavailability is interpreted slightly differently:

- Business: This is the downtime of the service to citizens;
- System: This is the downtime required to restart the system after a failure;
- Hardware and Software: This is the downtime accepted by the internal asset manager to analyse, diagnose or escalate a problem to the supplier. In general, the supplier's reaction/correction time is much higher (see corresponding outsourced service asset);
- Outsourced service: This is the time needed for suppliers to respond to requests and propose at least a workaround, while beginning a more in-depth correction of the problem;
- Personnel: This is the time needed for the department to analyze and propose a simple solution, if any, to the problem;
- Network: This is the time required to diagnose, analyze and resolve a simple problem by, for example, restarting and/or replacing faulty network components.
Please note that the time indication in the degree name (e.g. 1h, 4h) is an estimate used to define operating rules. The estimated real time for a restart is encoded as the “RT” parameter, and the maximum time desired by the business activity decision-maker is encoded as the “RTO”. These indications may deviate from those provided in the degree classification. In such cases, asset-specific recovery measures should be used, and documented in the “Specific rules” field of the inventory.


|Acro.| Description| Availability (%)| Unavailability per year| Max restoration time| Max # of unavailability per year| Rules of good practice *|
|--|--|--|--|--|--|--|
|15’|High availability|99,999|15 minutes|15 minutes|1,6|High redundancy, pentest-based vulnerability analysis |
|1h|Error unacceptable|99,99|15 minutes|1 hour|4|BCP testing |
|4h|Urgently managed|99,9|8.3 hours|4 hours|2|24/7 manager availability mandatory |
|8h|High maintenance|99,5|1.8 days|8 hours	|5|BCP |
|1d|Normal maintenance|99|3.5 days|1 day	|4|Documented recovery procedures. |
|1w|Low maintenance|90|1 weeks	|1 week|4|Rigorous enforcement of policy requirements by managers|
|4w|Not managed|80|2.5 months|4 weeks	|2|No specific rules|

Table 4: Levels of availability. Each line inherits the rules of the lower level

## Business Continuity and Recovery Parameters


### Asset Recovery Priorities

In case of overload preventing the parallel execution of recovery processes, it is essential to prioritize IT assets based on their criticality to the organization. Each asset is assigned a unique priority number, ranging from 1 to 5, where 1 represents the most urgent asset to recover and 5 the least urgent. This classification ensures that the most crucial assets for business continuity are restored first, minimizing the impact on essential operations. By clearly defining these priorities, the organization can optimize its recovery efforts and ensure a rapid and effective restoration of critical services.

### RT (Recovery Time)

Recovery Time (RT) represents the maximum acceptable duration for an IT service to begin responding after a failure or request. It is the time measured or estimated between identifying a problem and restoring essential functions, though not necessarily the complete recovery (period from the incident report to the restoration of critical functions).
RT < RTO
This parameter is crucial to ensure a smooth user experience even in the event of disruptions. An optimized response time helps maintain performance and user satisfaction, thus minimizing the negative impact on daily operations.



### RTO (Recovery Time Objective)

The Recovery Time Objective (RTO) determines the maximum time an equipment or service can be unavailable. For example, a printer server that needs to perform important prints every hour must be available within one hour. Thus, the recovery should not take more than one hour. The RTO for various systems and equipment should be defined so that the maximum tolerable duration of disruption to sustained business operations can be met.
Note: For products, services, and activities, the recovery time objective is less than the time it would take for the adverse impacts resulting from the failure to deliver a product/service or the inability to carry out an activity to become unacceptable. This is referred to as the Maximum Tolerable Period of Disruption (MTPD).
RTO < MTPD

### RPO (Recovery Point Objective)

The Recovery Point Objective (RPO) determines the maximum amount of data an organization is willing to lose in the event of a disaster, measured in time. The RPO dictates the frequency of backups required to maintain operations and protect the organization’s critical data. By establishing a stringent RPO, the organization can ensure that data loss is minimized, thus ensuring a rapid and efficient recovery after an incident.
In practice, this is the point from which the information used by an activity must be restored in order to enable its operation upon recovery.