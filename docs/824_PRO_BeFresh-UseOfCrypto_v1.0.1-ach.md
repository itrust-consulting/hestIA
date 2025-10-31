|    |
|----|
|    |
|    |
|    |

General information

Document history

Approval



| Name      | Role                   | Responsibility            | Signature   |
|-----------|------------------------|---------------------------|-------------|
| C. Harpes | CISO                   | Content,  CISO compliance |             |
| B. Frisch | Managing director (MD) | Ownership                 |             |

Management summary

The importance of security should never be underestimated as the consequences of losing data can be disastrous to an organization. Encryption is one effective method to ensure the confidentiality of information. Encryption software packages can encrypt the entire hard disk or dedicated messages and protect important and confidential data, allowing access only to authorized persons, by the use of a key.

The key ideas of the cryptography procedure are to:



- detail the procedure for choosing a cryptography tool and indicate the responsibility of the different actors during this process;
- explain how to manage secure containers which hold sensitive information;
- describe how encryption keys are deposited, in both physical and electronic forms;
- define the course of action in relation to the different events of the review process.

Table of contents

1	Introduction	6

1.1	Context	6

1.2	Objectives	6

1.3	Scope	6

1.4	Enforcement and reading instructions	6

1.5	Audience	7

1.6	Document structure	7

1.7	References	7

1.8	Acronyms	8

1.9	Glossary	8

2	General information on cryptography	10

2.1	Encryption	10

2.2	Electronic signature	10

2.3	The ‘hash’ function	12

3	Cryptographic controls	14

3.1	General principles	14

4	Request for a new cryptographic tool	15

4.1	Process	15

4.2	Process steps	15

5	Request for a new cryptographic algorithms and key lengths	16

5.1	Process	16

5.2	Process steps	16

5.3	Cryptographic use case review	17

5.4	Reference to standards and guidelines	17

5.5	Development of authorized algorithm list	17

6	Cryptographic tool selection	19

6.1	Process	19

6.2	Process steps	19

6.2.1	Define application context	19

6.2.2	Analyze the proposed cryptographic tool	20

6.2.3	Establish the implementation rules	20

6.2.4	Validate security aspects	20

6.2.5	Final validation	20

6.2.6	Update relative standards	20

7	Key management	21

7.1	Responsibility	21

7.2	Creating the depository	21

7.2.1	Physical depository	21

7.2.2	Electronic depository	21

7.2.3	Depositing a key	21

7.2.4	Exporting a key	22

7.2.5	Declassification of a key	22

8	Controls and updates	23

8.1	Regular checks	23

8.2	Annual review	23

8.3	Events triggering action:	23

List of figures

Figure 1: Lowering the classification of information using encryption	10

Figure 2: Signing a message to protect its integrity	11

Figure 3: Verifying the integrity of a message by its signature	11

Figure 4: Process for creating and verifying a digital fingerprint	13

Figure 5: Request for a new cryptographic tool	15

Figure 5: Request for a new cryptographic tool	16

Figure 6: Process of selecting a cryptographic tool	19

List of tables

Table 1: Development of authorized algorithm list	18

Table 2: Events triggering actions	23

## Introduction

### Context

BeFresh regularly uses cryptography in order to ensure the confidentiality of its information. It is therefore necessary to indicate to all employees, the procedure for using cryptography.

### Objectives

The objective of this document is to outline the process of using cryptographic tools and to define the procedure for depositing encryption keys.

### Scope

The scope of this document is the same as that of the ISMS. The document applies to all ISMS documents of type Policy and Procedure, and optionally to other documents of .

### Enforcement and reading instructions

This document becomes effective once approved by the MD and published on the ISMS repository (\InfoSec-IN) available to all employees of BeFresh. It will remain in effect until revoked or revised by the Owner or the MD. Do not rely on a printed document but rather check on the official documentation site of BeFresh for the currently applicable version.

The MD’s signature is an official recognition of the mandatory character of this document. It is to be respected by all employees of BeFresh and a failure to comply with the Information Security policy may be considered as a violation of the working contract and result in disciplinary action.

The use of the SIMPLE PRESENT tense or the terms ‘MUST’, ‘MANDATORY’, ‘REQUIRED’, or ‘SHALL’ in a statement means that the statement is considered a formal requirement.

The use of words such as ‘SHOULD’ or the adjective ‘RECOMMENDED’ means that there may be legitimate reasons to disregard the statement, but that the implications of such an exception shall be assessed and fully understood.

The terminology ‘MAY’ or ‘CAN’, or the adjective ‘OPTIONAL’ means that the implementation of the statement is at the discretion of the implementer.

The indication #175W BeFresh-WordTempl refers to the document with the given acronym, here BeFresh-WordTempl. The indication #175W refers to the ISMS document with the given indicator, here 175W, in this case the same document as the reference before.

The indicate #502 refers to a separated document 502 if existent, other wise to the chapter 02 inside document #5.

The text copied by law or other reference is marked in red, and in any case constitutes an obligation.

Control objectives given in CISO are put in bold.

Security measures for reaching these objectives are put in a box.

Specific text for the implementation at BeFresh is highlighted.

### Audience

This document shall be read and applied by all employees of BeFresh.

### Document structure

The document is structured as follows:



- Chapter 2 provides general info on cryptography.
- Chapter 3 specifies how cryptographic tools are chosen.
- Chapter 4 describes the process after an employee has requested a new cryptographic tool.
- Chapter 5 indicates the process for selecting a cryptographic tool.
- Chapter 6 deals with key management.
- Chapter 7 describes controls and updates.

### References

See [2] for all references of type BeFresh-… or with an ISMS document identifier starting with #...

BeFresh, ISMS, Policy, Information Security Policy (BeFresh-InfoSec), #0.

BeFresh, ISMS, Plan, List of documents plan (BeFresh-ListDoc), #0D.

BeFresh, ISMS, Standard, Glossary (BeFresh-Glossary), #0G.

BeFresh, ISMS, Standard, Asset inventory (BeFresh-AssetInventory), #509A.

BeFresh, ISMS, Standard, Classification standard, (BeFresh-Classification), #512

BeFresh, ISMS, Jira ticketing system, (https://befreshlu.atlassian.net/).

BeFresh, ISMS repository, \InfoSec-IN, (BeFresh-ISMS-REPO)

BeFresh, ISMS, Standard, User profiles (BeFresh-UserProfiles), #518P.

BeFresh, ISMS, Standard, Access review (BeFresh-AccessReview), #518R.

REGULATION (EU) 2016/679 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL of 27 April 2016 on the protection of natural persons with regard to the processing of personal data and on the free movement of such data, and repealing Directive 95/46/EC (General Data Protection Regulation)

CISO/IEC 27001:2022(E), Information security, cybersecurity and privacy protection — Information security management systems — Requirements.

CISO/IEC 27002:2022(E), Information security, cybersecurity and privacy protection — Information security controls.

### Acronyms



| CIO   | Chief Information Officer                 |
|-------|-------------------------------------------|
| CISO  | Chief Information Security Officer        |
| ELK   | Elasticsearch, Logstash &amp; Kibana          |
| HoD   | Head of Department                        |
| ICT   | Information and Communications Technology |
| ISMS  | Information Security Management System    |
| LDAP  | Lightweight Directory Access Protocol     |
| MD    | Managing Director                         |
| UID   | User Identifier                           |

### Glossary

For other descriptions of common terms used in this document, please refer to the general glossary of BeFresh [2].



| Access rights                                 | Means to ensure that access to assets is authorized and restricted based on business and security requirements                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
|-----------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Information Security Management System (ISMS) | Part of the overall management system, based on a business risk approach, to establish, implement, operate, monitor, review, maintain and improve information security                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| Chief Information Security Officer (CISO)     | The CISO is responsible for functional specifications and controls the implementation of provisions on information security                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| Chief Information Officer (CIO)               | Agency official responsible for: (i) Providing advice and other assistance to the head of the executive agency and other senior management personnel of the agency to ensure that information technology is acquired and information resources are managed in a manner that is consistent with laws, executive orders, directives, policies, regulations, and priorities established by the head of the agency; (ii) Developing, maintaining, and facilitating the implementation of a sound and integrated information technology architecture for the agency; (iii) Promoting the effective and efficient design and operation of all major information resource management processes for the agency, including improvements to the work processes of the agency |
| Information                                   | Element of knowledge that may be transmitted                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Information system                            | A discrete set of information resources organized for the collection, processing, maintenance, use, sharing, dissemination, or disposition of information                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |

## General information on cryptography

### Encryption

In the case of encryption, a plain text which requires protection is converted using algorithms into an encrypted text, which can be transmitted like a text that needs no such protection. These algorithms are based on the use of keys, where each key is protected to at least the same extent as the text protected by it.



<!-- image -->

Figure 1: Lowering the classification of information using encryption

The need for information to be encrypted is dependent on its classification. The different classifications used by BeFresh (and more importantly each classification security requirements) are indicated in the asset management standard BeFresh-Classification #512.

Cryptographic controls are used in compliance with all relevant agreements, laws, and regulations cf. BeFresh-ListLegalReq #531.

### Electronic signature

In addition, there are encryption algorithms with which the integrity of a message can be ensured. These algorithms are based on the use of keys, where each key is protected to at least the same extent as the text protected by it. Those messages protected for the preservation of their integrity can be categorized one class lower than unprotected messages.

Thus, for example, a message protected by an electronic signature and classified as 'normal' can be converted into an unsigned message classified as 'vital' by verifying and removing the signature. The message, protected by the security rules for the 'vital' classification, then enters into a 'vital' process, whereas a normal message which has not undergone verification cannot enter into a similar process.



<!-- image -->

Figure 2: Signing a message to protect its integrity

The key used to sign is called a private key, because its disclosure can lead to signature forging. The key used to verify the signature is called public because a large number of people can use it to verify the signature. The public key is usually found in an electronic certificate, which is also a file containing the signature of the signer, the conditions of use and a signature on the previous data. The public key is generated by an authority called a certification authority, such as LuxTrust.



<!-- image -->

Figure 3: Verifying the integrity of a message by its signature

The security rules in the asset inventory indicate which algorithms are permitted for which classes of plain text data and how the keys and encrypted messages are classified.

Note: This could be taken as an exception to the rule that pieces of information maintain their classification independently of their format. It should be noted, however, that encryption alters essential qualities, i.e. format. An encrypted message is unintelligible to anyone who does not have the key; it can thus be classified as an unintelligible file, unlike the information contained within it.

Important note:

Processes to verify the integrity of a message are not to be confused with integrity conservation processes. Verification of integrity based on proof of integrity (i.e. the signature presented here) provides only a binary answer as to the integrity of the message: it is of integrity or not, without giving the means to restore the message in case of corruption of this integrity. A process of preserving integrity is a process that ensures the impossibility of manipulation. For instance, data written on a non-rewritable CD cannot be modified with the available technical means, so writing on CD can be considered as a process of preserving integrity.

### The ‘hash’ function

The result of a cryptographic hash function, in other words, a standardized and unique summary of any message is called a hash code.

Note: This fingerprint is used as input to the electronic signature process.

In order to meet all requirements, cryptographic hash functions are required to have the following security properties:

‘One-way’:



- pre-image resistant: it is infeasible to calculate for a given fingerprint (output data of the hash function) an input message;
- second pre-image resistant: it is infeasible to compute for a given input message (input data of the hash function) a second different input message whose fingerprint corresponds to the calculated fingerprint of the first message.

‘Collision resistant’:



- it is infeasible to calculate two different input messages whose fingerprints by this function will be identical.

The repeated calculation of a fingerprint from the same message made using the same function always provides the same result. However, calculating a fingerprint from the modified message never gives the same fingerprint if the function is a cryptographic hash function.

A fingerprint of integrity, i.e. a fingerprint taken from the message and which has not been modified, allows to verify at any time the integrity of a message with respect to the message used to calculate the message footprint.

Note: The use of encryption processes could be seen as an exception to the rule that information always keeps the same degree, regardless of the modality under which it is stored or transported, since the classification takes into account the intrinsic properties of information and not its form. However, it is clear that cryptography fundamentally changes the properties of information. An encrypted text is an incomprehensible message for anyone who does not have the key and can therefore be treated as incomprehensible information.

However, for some well-known hash algorithms, such as MD5 or SHA-1, collisions between "hash" have been found. Researchers continue to develop new methods of attacks, and attackers have increasingly powerful computers to attack algorithms. This is why it is important to set rules that indicate which algorithms can be used in which context, and that these rules are continually adjusted by personnel familiar with this domain.



<!-- image -->

Figure 4: Process for creating and verifying a digital fingerprint

## Cryptographic controls

BeFresh implements cryptographic controls in order to protect the confidentiality, integrity, and availability of its information.

Cryptographic tools are qualified, and their security features assessed before being implemented throughout the organization. All cryptographic tools (1Password) which are validated are listed in an ISMS standard, the Asset Inventory, BeFresh-AssetInventory #509A.

### General principles

The need for information to be encrypted is dependent on its classification. The different classifications used by BeFresh are listed in the asset management procedure, BeFresh-AssetMgt #509.

## Request for a new cryptographic tool

Employees may make a request to the CIO or the CISO for a new cryptographic tool if they deem that the currently implemented tools in BeFresh-AssetInventory #509A are unable to meet their requirements.

### Process

Figure 5: Request for a new cryptographic tool

### Process steps

The process for determining whether a new cryptographic tool is needed is performed in the following steps:

An employee may make a request either to the Managing Director, CISO, CIO, or their relevant head of department for a new cryptographic tool.

The request will be analysed in order to determine whether a new tool is needed based on the already implemented tools indicated in BeFresh-AssetInventory #509A

The request will be refused if an already implemented tool is deemed suitable to meeting the employee’s requirements.

If the request is granted, the CISO will initiate the cryptographic tool selection process (see chapter 5).

If the Managing Director, CISO, CIO, or head of department rejects the request, they should recommend an already existing tool to the employee from the current list of implemented cryptographic tools in BeFresh-AssetInventory #509A.

## Request for a new cryptographic algorithms and key lengths

Employees may make a request to the CIO or the CISO for a new cryptographic algorithms and key lengths if they deem that the currently implemented tools in BeFresh-AssetInventory #509A are unable to meet their requirements.

### Process

Figure 5: Request for a new cryptographic tool

### Process steps

The process for determining whether a new cryptographic algorithms and key lengths is needed is performed in the following steps:

Employees may submit a formal request to the Managing Director, Chief Information Security Officer (CISO), Chief Information Officer (CIO), or their relevant head of department.

The request should include:

Justification for the need (e.g., incompatibility, performance issues, regulatory requirements)

The intended use case and risk context

A suggested algorithm or key length, if known

The request will be reviewed and assessed against the currently approved cryptographic mechanisms listed in the BeFresh-AssetInventory (#509A).

If an existing approved algorithm and key length is determined to be sufficient for the requirement, the request will be declined, with reasons provided.

If the request is justified, the CISO will initiate the cryptographic algorithm evaluation and selection process (refer to Chapter 6), which includes:

Risk and security analysis

Standards alignment check (e.g., NIST, ISO/IEC)

Performance and compatibility evaluation

Final approval and policy update if adopted

Once approved, the new algorithm or key length will be added to the list of authorised cryptographic standards in the organisational cryptographic policy and reflected in BeFresh-AssetInventory (#509A).

If the Managing Director, CISO, CIO, or head of department rejects the request, they should recommend an already existing tool to the employee from the current list of implemented cryptographic tools in BeFresh-AssetInventory #509A.

### Cryptographic use case review

Should be identified all instances where cryptographic functions are used, including:

Data encryption (storage and transmission)

Digital signatures

Secure communication protocols (e.g., TLS, VPNs)

Password hashing

Document the purpose and cryptographic requirement of each instance.

### Reference to standards and guidelines

Consult industry-accepted standards such as:

NIST SP 800-57, SP 800-131A

ISO/IEC 18033 and ISO/IEC 27001 Annex A.10

ENISA or national regulatory bodies

Ensure that algorithms and key lengths align with current recommendations.

### Development of authorized algorithm list

Establish a list of approved cryptographic algorithms and corresponding minimum key lengths.

Example:



| Algorithm Category    | Algorithm          | Minimum Key Length   | Notes                                    |
|-----------------------|--------------------|----------------------|------------------------------------------|
| Symmetric Encryption  | AES                | 256 bits             | AES-128 may be used where justified      |
| Asymmetric Encryption | RSA                | 2048 bits            | 3072+ preferred for long-term protection |
| Asymmetric Encryption | ECC (P-256, P-384) | 256 bits             | Stronger than RSA at equivalent bit size |

Table 1: Development of authorized algorithm list

## Cryptographic tool selection

Once the Managing Director has given a final validation to the request for a new cryptographic tool, the CISO will start the following cryptographic tool selection process.

### Process

The diagram below shows the different stages of the cryptographic tool selection process.

Figure 6: Process of selecting a cryptographic tool

### Process steps

#### Define application context

Defining the application context considers the following factors:



- what the cryptographic tool is used for;
- what type of data is processed, and the security classification of both the plaintext and ciphertext.

#### Analyze the proposed cryptographic tool

Cryptography tools are assessed with the help of security forums, articles found on the Internet, and magazines. Information is thus obtained about various topics, such as security vulnerabilities, the strength of the cryptographic algorithms used, the author or the release version of a software package.

The software packages should have a security certification or be referenced by a reputable security agency such as BSI, ILNAS, etc. Only the most ‘high-end’ products should be considered for selection. Once a cryptographic tool has been chosen, it is installed and tested by the CIO.

#### Establish the implementation rules

At this stage, the rules for implementation are established and include:



- the configuration of the tool that is to be implemented;
- the choice of options to use, e.g. which algorithms should be used if the software offers multiple options;
- management rules for the use of encryption keys (who should keep the keys, where, and how).

#### Validate security aspects

The CISO validates that the implementation rules comply with ISMS requirements.

#### Final validation

The Managing Director provides a final validation of the tool after a discussion with the CISO and CIO. If the Managing Director chooses not to validate the tool, the CIO and CISO should propose alternative cryptographic tools based on the outcomes of the discussion.

#### Update relative standards

Once the Managing Director has provided final validation of the cryptographic tool, the CISO should update BeFresh-AssetInventory #509A.

## Key management

A policy on the use, protection and lifetime of cryptographic keys should be developed and implemented through their whole lifecycle.

### Responsibility

The CIO is responsible for managing cryptographic keys.

### Creating the depository

The CIO defines a secure location (typically a safe) at which copies of symmetric and asymmetric encryption keys used are retained. This depository shall have another physically separated backup of the encryption keys. In the event of loss or destruction the CIO shall resubmit the keys. The information in the safe is classified as ‘Secret’ by default.

#### Physical depository

Two people are required (two-man principle, separate authentication).

Keys in sealed envelopes.

An inventory of the contents shall indicate:



- The name of the creator of the key and the names of the persons who are authorized to access it.
- The name of the software package used.
- The type of the data that is protected.
- The value of the key to the organization.

#### Electronic depository

The management for an electronic deposit is the same as for a physical deposit except there is no two-man principle. The keys should be kept in electronic form, in a container that is sufficiently protected. The CIO should ensure, however, that his or her deputy (sometimes also called substitute or backup) can also access the files in the event of an emergency.

#### Depositing a key

The author prepares a key form and locks it in a sealed envelope in the presence of the depository manager, who stores the envelope in the depository. They again show the depository manager the key form in order for them to check that the key quality is good and that the form is complete. The depository manager shall then update the depository inventory, and have it signed by the author of the added key.

#### Exporting a key

A key may not be removed from the depository. When necessary, the following people are authorized to view the key:



- the author of the key;
- any person delegated by the Managing Director, if their legitimacy is also validated by the CISO.

The person who has viewed the key, and the person who is responsible for the safe, must both sign a document stating the time, date, and the reason for viewing the key.

#### Declassification of a key

The owner of a key may submit a declassification request using the Redmine project management tool Error! Reference source not found.. This request shall be approved by the Managing Director and the CISO before the key is declassified. In this case, the envelope containing the key is destroyed in a shredder.

## Controls and updates

### Regular checks

The CISO will sporadically check the implemented cryptographic tools in order to assess that they still meet the security requirements needed by the company. In the case of a tool no longer being deemed suitable for use, the CISO should immediately inform all employees and recommend a new cryptographic tool which can be used.

### Annual review

All implemented cryptographic tools shall be reviewed (logged in BeFresh-AssetInventory #509A) on a yearly basis by the CIO, who will assess whether the tools still meet the requirements of the organization.

### Events triggering action:

The following events and corresponding actions and further an update of BeFresh-ListCryptoKeys #824K is specified in table below:



| Events                                                                       | Action                                                                                                                              |
|------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| Request for recognition of a cryptographic tool's conformity.                | Analysis and decision on recognition of conformity according to BeFresh-Crypto.                                                     |
| Request for revision of a tool (e.g. in the event of an update).             | Update the analysis and, if necessary, confirm or withdraw the tool's conformity.                                                   |
| Discovery or publication of a flaw in an authorized cryptographic tool.      | Consequence analysis. Record in list of security incidents. Update analysis and, if necessary, confirm or withdraw tool compliance. |
| Identification of non-compliance with security rules for an authorized tool. | Check other use cases. Adapt associated rules if possible. Remind users of rules.                                                   |

Table 2: Events triggering actions