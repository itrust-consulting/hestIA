|    |
|----|
|    |
|    |
|    |

General Information

Document history



| Version   | Date       | Author        | Modifications                                 |
|-----------|------------|---------------|-----------------------------------------------|
| 0.2       | 14/07/2025 | A. Chezganova | Based on Sm andexport from TRICK v0.2         |
| 0.2-1     |            | C. Harpes     | Revisions and formatting, add mgt summarries. |
| 0.3       | 16/7/2025  | C. Harpes     | Addition of risk appetite and risk acceptance |

Working Group

Approval



| Name      | Role                   | Responsability            | Signature   |
|-----------|------------------------|---------------------------|-------------|
| C. Harpes | CISO                   | Content,  CISO compliance |             |
| B. Frisch | Managing director (MD) | Ownership                 |             |

Summury

###### Context

The following document presents the results of the risk assessment performed by the ISMS team and updated by . This project intended to get a detailed risk assessment and risk treatment plan to increase the security level in the following years. The risk analysis follows ISO/IEC 27005 on risk management and was conducted with the support of the risk assessment and treatment tool TRICK Service developed by itrust consulting.

###### Scope

The scope of the risk analysis consists of .

###### Results and limitations

In agreement with , the results of this analysis are sufficient to implement the risk treatment plan up to phase 3 and to accept the residual risks. However, these results will have to be reviewed periodically to be able to describe the real state of the organisation’s risk at any given time.

This risk assessment is NIS2 copmliant, but has not yet been align with the regulators reporting needs as they have not yet been published.

###### Considered assets and relative risk evaluation

The considered assets have a total value of 708 k€ and the total sum of the risks the organization is currently exposed to the relative scope is estimated to 260 k€/year (ALE).



| Acro   | Type d’actif        | Nom ILR             | Valeur par type d’actif (k€)    | Risque par type d’actif (k€/an)   |
|--------|---------------------|---------------------|---------------------------------|-----------------------------------|
| BS     | Processus métier    | Processus métier    |                                 |                                   |
| INFO   | Information         | Information         |                                 |                                   |
| SY     | Système             | Système             |                                 |                                   |
| SW     | Logiciel            | Logiciel            |                                 |                                   |
| HW     | Matériel            | Matériel            |                                 |                                   |
| NET    | Réseau              | Réseau              |                                 |                                   |
| ORG    | Service             | Organisation        |                                 |                                   |
| SI     | Site                | Site                |                                 |                                   |
| OUT    | Service externalisé | Service externalisé |                                 |                                   |
| HR     | Ressource humaine   | Ressource humaine   | 0                               | 0                                 |
| Compl  | Conformité          | Conformité          | 0                               | 0                                 |
| Fin    | Financier           | Financier           | 0                               | 0                                 |
| IV     | Immatérielle        | Immatérielle        | 0                               | 0                                 |
| Total  | Total               | Total               | 708 k€                          | 260 k€/an                         |

Also note that some value (such asHR) have not been estimated as risk are ssigen to other related asset type. This could be improved in a further iteration. In general, these indications refers to annual turnover, but not actual book values, so the total value should only be regarded as a rough estimate.

###### Current security level

The implementation level of security on average is:

98% according to the requirements of ISO/IEC 27001

86% according to the requirements of ISO/IEC 27002.

###### By convention, an implementation level above 49% means that the organisation is compliant with requirements, but if it remains below 100%, that implementation can be increased or generalised to further reduce risks.

###### Financial risk heat map

May be added in a further iteration

Figure 1 : Financial risk matrix by assets and scenarios (sorted by types) (highest risks first)

###### Privacy risk heat map



| Impact      | 10:IP10-huge-max   |             |               |             |               |             |              |             |             |             |               |
|-------------|--------------------|-------------|---------------|-------------|---------------|-------------|--------------|-------------|-------------|-------------|---------------|
| Impact      | 9:IP9-sign-max     |             |               |             |               |             |              |             |             |             |               |
| Impact      | 8:IP8-few-max      |             |               |             |               |             |              |             |             |             |               |
| Impact      | 7:IP7-huge-sign    |             |               |             |               |             |              |             |             |             |               |
| Impact      | 6:IP6-sign-sign    |             |               |             |               |             |              |             |             |             |               |
| Impact      | 5:IP5-few-sign     |             |               |             |               |             |              |             |             |             |               |
| Impact      | 4:IP4-sign-lim     |             |               |             |               |             |              |             |             |             |               |
| Impact      | 3:IP3-few-lim      |             |               | 9           | 12            | 6           |              |             |             |             |               |
| Impact      | 2:IP2-sign-neg     |             |               |             |               |             |              |             |             |             |               |
| Impact      | 1:IP1-few-neg      | 1           | 1             | 9           | 11            | 6           | 3            | 1           |             |             |               |
| Impact      |                    | 1:p1        | 2:p2 (1×/30y) | 3:p3        | 4:p4 (1×/10y) | 5:p5        | 6:p6 (1×/3y) | 7:p7        | 8:p8 (1×/y) | 9:p9        | 10:p10 (3×/y) |
| Probability | Probability        | Probability | Probability   | Probability | Probability   | Probability | Probability  | Probability | Probability | Probability | Probability   |

Figure 2 : Privacy Heat Map

###### Risk treatment plan

In order to address the risks identified during this project and qualified for treatment, we have drawn up a list of recommended actions for implementation. The list is derived from the analysis of standards and security practice guides proposing security measures that have been arranged into a well thought-out implementation plan using the OpenTRICK tool. Implementing this action list for Phase 1 and 2 will reduce the risks to an acceptable level.

The risk treatment plan includes an indication of the level of risk after the effective implementation of the risk treatment plan. The risk treatment plan comprises several phases to improve safety over time and achieve the chosen risk level within a reasonable timeframe and in accordance with the organisation's resources.

The list was drawn up by the person in charge of this study in discussion with various managers. It will be formally validated with the validation of this report.

The risk treatment plan drawn up contains 39 measures that have not yet been fully implemented and are divided into 5 phases :

Phase 1: From 07/2025 to 10/2025, 16 security measures will be implemented.

Phase 2: From 10/2025 to 01/2026, 9 security measures will be implemented.

Phase 3: From 01/2026 to 07/2026, 9 security measures will be implemented.

Phase 4: From 07/2026 to 01/2027, 4 security measures will be implemented.

Phase 5: From 01/2027 to 01/2028, 1 security measures will be implemented.

The average annual return on investment (ROSI) in terms of safety measures is estimated at 12,2 k€ for the entire treatment plan. The treatment plan will make it possible to achieve an estimated relative ROSI of 1 % which means that every euro invested in a security measure will make it possible to limit by an average of 1,01 € the annual loss due to incidents that could occur without this investment.

Annual risks are expected to fall from 260 k€ to 220k€ by the end of 2025, which is below the level of acceptable risk., i.e. risk reduction of 51 k€, for a high security investment of 24+11= 35k€, or, considering life time and maintenance costs, an average yearly cost of 26+14=40€/y. As this is lower, average annual return on investment (ROSI) in terms of security measures is estimated to 51-40= 1k€ or 11/35=30%.

###### Risk acceptance

Given the conservative (i.e. pessimistic) the comparison of the current risk 260k€ and residual risk of 220 by the end of 2026, and given the high risk appetite (cf. ch. 3.3) and the requirement for compliance, top management has approved the proposed risk treatment plan and has accepted the risk situation described in this report.

Table des matières

1	Introduction	10

1.1	Contexte	10

1.2	Document objectives	10

1.3	Scope	10

1.4	Audience	10

1.5	Structure of the document	10

1.6	Referenzes	11

1.7	Acronyms	11

1.8	Terminologie	11

2	Methodology and conduct	13

2.1	Methodology	13

2.2	Conduct of the study	13

2.3	General consideration regarding TRICK Service	14

2.3.1	Parameter setting and validity of the results	14

2.3.2	A methodology based on profitability	14

2.3.3	Parameter tuning	14

2.4	Links between process and documentation	15

3	Risk context	16

3.1	General considerations (cf. BeFresh-RiskMgt)	16

3.2	Base criteria (cf. BeFresh-RiskMgt)	16

3.2.1	Risk evaluation criteria	16

3.2.2	Impact criteria	16

3.3	Risk acceptance criteria	16

3.3.1	For the brainstorming	16

3.3.2	For the sum of the risks (assessed quantitatively)	17

3.4	Description of the target	17

4	Risk identification	20

4.1	Asset identification	20

4.2	Brainstorming	24

4.2.1	Summary	24

4.2.2	Threats exposure mapping	24

4.2.3	Vulnerabilities exposure mapping	26

4.2.4	Risk exposure mapping	27

5	Gap analysis	31

5.1	Summary	31

5.2	Methodology	31

5.3	Compliance level for ISO/IEC 27001	32

5.4	Compliance level for ISO/IEC 27002	33

5.5	Conformity level for 27701	33

6	Risk analysis	34

6.1	Risk scenarios and likelihood &amp; impact scales	34

6.1.1	Probability	35

6.1.2	Financial consequence	36

6.1.3	Total consequence	36

6.2	Typology of estimated risks	36

6.3	Risk analysis approach	39

6.3.1	Parameter preparation	39

6.3.2	Impact analysis	41

6.3.3	Likelihood analysis	42

6.3.4	Quantified risks sorted by value	43

6.4	Risk for PII principals (DPIA)	45

6.4.1	Overview on risk for PII principals	45

6.5	Details of the risk analysis	46

6.6	Évaluation des risques	52

7	Risk treatment plan	53

7.1	Summary of treatment plan	53

7.2	Increase of compliance rate and rentability of the phases	54

7.3	Detailed risk treatment plan	55

8	Other related risk management processes	59

8.1	Risk acceptance	59

8.2	Risk communication	59

8.3	Risk monitoring and review	59

9	Evaluations des risques selon la méthode de l’ILR	60

Annex :	61

27001	62

27002	64

Liste des figures

Figure 1 : Financial risk matrix by assets and scenarios (sorted by types) (highest risks first)	4

Figure 2 : Privacy Heat Map	5

Figure 3 : Information security risk management process	13

Figure 4 : Asset dependency before adding ILR assets (2022)	21

Figure 5 : Asset Dependency based on ILR dependency model	23

Figure 6 : Taux de conformité ISO/IEC 27001 pendant les différentes phases d’implémentation	32

Figure 7 : Taux de conformité ISO/IEC 27002 pendant les différentes phases d’implémentation	33

Figure 8 : Perte annuelle attendue (ALE) par actif	37

Figure 9 : Perte annuelle attendue (ALE) par type d’actif	37

Figure 10 : Perte annuelle attendue (ALE) par scénario de risque	38

Figure 11 : Perte annuelle attendue (ALE) par type de scénario de risque	38

Figure 12: Matrice des risques	45

Figure 13 : Profitability of the treatment plan	55

Liste des tableaux

Table 1 : Critères d’acceptation du risque	17

Table 2 : Considérations générales sur l’envergure de l’analyse de risque	19

Table 3 : List of assets in scope of the risk analysis	23

Table 4 : List of assets considered out-of-scope of the current assessment	23

Table 5 : Risk exposure scale	24

Table 6 : Cartographie des menaces	26

Table 7 : Liste des vulnérabilités	27

Table 8 : Cartographie des risques	30

Table 9 : Considered risk scenarios	35

Table 10 : Probability scale	35

Table 11 : Financiel consequence scale	36

Table 12: Parametre impacting the risk consequences	41

Table 13: Likelihood for different risk scenarios on information or system assets	43

Table 14: Quantified risks sorted by value (all &gt;3,4 k€/y)	44

Table 15: Risk estimation for the asset VM-SaaS-Shared	46

Table 16: Risk estimation for the asset VM-SaaS-SNHBM	46

Table 17: Risk estimation for the asset Support+Consult	47

Table 18: Risk estimation for the asset LaptopsEtc	47

Table 19: Risk estimation for the asset SaaS	48

Table 20: Risk estimation for the asset VM-Webhosting	48

Table 21: Risk estimation for the asset SW-Dev	49

Table 22: Risk estimation for the asset BeInvoice	49

Table 23: Risk estimation for the asset VM-SaaS-Editpress	49

Table 24: Risk estimation for the asset VM-SaaSContainers	50

Table 25: Risk estimation for the asset VM-SMP-Peppol	50

Table 26: Risk estimation for the asset ITadmin	50

Table 27: Risk estimation for the asset Deep	51

Table 28: Risk estimation for the asset SE\_Dev	51

Table 29: Risk estimation for the asset Phones	51

Table 30: Risk estimation for the asset Peppol	52

Table 31 : : Characteristics of implementation phases	54

## Introduction

### Contexte

To protect information with reasoned security measures, risks shall be assessed, and the most appropriate measures chosen to reduce these risks. The practices of an information security management system (ISMS) require that the methods, procedures, and results of this risk assessment and treatment, i.e. the selection of appropriate measures, are formalized. In that aim,  decided to perform a risk analysis following the guidance of ISO/IEC 27005 and using the TRICK Service web application of risk assessment developed by itrust consulting.

This report contains the first risk assessment and risk treatment documented by BeFresh.

### Document objectives

This document is the export of risk assessment and risk treatment. The current and complete version can be consulted via the TRICK Service web application on app.trickservice.com.

This document is used for discussion, validation by managers and communication to interested parties.

### Scope

The scope of this risk analysis is .

### Audience

The report is intended to be distributed to top management, risk owners and all involved personnel.

### Structure of the document

The following chapters are structured as follows:

Chapter 2 describes the used methodology and specific elements of this project.

Chapter 3 describes the context, the scope and the value of assets considered according to the ISO/IEC 27005 approach.

Chapter 4 presents the risk identification, including the asset considered and the risk brainstorming to identify and quickly assess threats, vulnerabilities, and risks.

Chapter 5 is on Gap analysis: it shows the current implementation level of relevant standards and the cost estimation of missing implementation.

Chapter 6 presents an overview and details justification of the assessment of current risks.

Chapter 7 contains the proposal of risk treatment plan to implement additional security measures.

Chapter 8 provides information on other risk management processes, such an outlook related to risk acceptance, risk communication, and risk monitoring and review.

The Annexe includes the implementation details of security measures of retained international standards and best practices considered for the risk treatment; in this assessment ISO 27001, 27002, 27701.

### References

, SMSI, Politique, Information Security policy (BeFresh-InfoSec), #0.

, SMSI, Plan, Risk Management process (BeFresh-RiskMgt), #161.

, SMSI, Standard, Asset dependency graph (BeFresh-AssetDepgraph), #161AD

, SMSI, Standard, Risk Estimation (BeFresh-RiskEstimation), #161TRE

itrust consulting, SMSI, Outil de gestion des risques (ITR-TRICKService), #161T.

itrust consulting, SMSI, TRICK Service user guide (ITR-TSGuide), #161TU.

ISO/IEC 27001:2022(E), Information technology – Security techniques – Information security management system – Requirements.

ISO/IEC 27002:2022(E), Information technology – Security techniques – Code of practice for information security management.

ISO/IEC 27701:2019(E), Information technology – Security techniques – Extension to ISO/IEC 27001 and ISO/IEC 27002 for privacy information management — Requirements and guidelines.

### Acronyms



| ALE     | Annual Loss Expectancy (Perte annuelle attendue)                                                                                                          |
|---------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| MAGERIT | Analyse de Risque et Méthodologie de Management pour les Systèmes d’Information (méthodologie d’analyse des risques publié par le gouvernement espagnole) |
| ROSI    | Return On Security Investment (le retour sur investissement d’un projet de sécurité)                                                                      |
| TRICK   | Tool for RIsk management based on Central Knowledge base                                                                                                  |

### Terminologie



| Annual Loss Expectancy                        | Metric to compare risks (in €).                                                                                                                                                                         |
|-----------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Information Security Management System (ISMS) | That part of the overall management system, based on a business risk approach, to establish, implement, operate, monitor, review, maintain and improve information security.                            |
| Process                                       | Set of interrelated or interacting activities which transform inputs into outputs.                                                                                                                      |
| Residual risk                                 | Risk remaining after risk treatment.                                                                                                                                                                    |
| Risk                                          | Combination of the likelihood of an event and its consequence.                                                                                                                                          |
| Risk analysis                                 | Systematic use of information to identify sources and to estimate the risk.                                                                                                                             |
| Risk assessment                               | Overall process of risk analysis and risk evaluation.                                                                                                                                                   |
| Risk avoidance                                | Decision not to become involved in, or action to withdraw from, a risk situation.                                                                                                                       |
| Risk criteria                                 | Terms of reference by which the significance of risk is assessed.                                                                                                                                       |
| Risk estimation                               | Process used to assign values to the probability and consequences of a risk.                                                                                                                            |
| Risk evaluation                               | Process of comparing the estimated risk against given risk criteria to determine the significance of the risk.                                                                                          |
| Risk identification                           | Process to find, list and characterize elements of risk.                                                                                                                                                |
| Risk management                               | Coordinated activities to direct and control an organization with regard to risk.                                                                                                                       |
| Risk optimization                             | Process related to a risk to minimize the negative and to maximize the positive consequences and their respective probabilities.                                                                        |
| Risk reduction                                | Actions taken to lessen the probability negative consequences or both, associated with a risk.                                                                                                          |
| Risk retention                                | Acceptance of the burden of loss or benefit of gain from a particular risk.                                                                                                                             |
| Risk transfer                                 | Sharing with another party the burden of loss or benefit of gain, for a risk.                                                                                                                           |
| ROSI                                          | Return on investment of a security project obtained as the difference between the change in risk before and after the introduction of security measure (Delta ALE) and the annual cost of this measure. |
| Threat                                        | A potential source of an incident that may result in adverse changes to an asset, a group of assets or an organization.                                                                                 |
| Turnover                                      | Amount of money made in a particular period (typically one year                                                                                                                                         |
| Vulnerability                                 | Weakness in an information system, system security procedures, internal controls, or implementation that could be exploited or triggered by a threat.                                                   |

## Methodology and conduct

### Methodology

The proposed risk management process follows the process described in the ISO/IEC 27005 standard and represented in the figure below (See #161 for more details).



<!-- image -->

Figure 3 : Information security risk management process

The current report does not follow the different phases of the methodology in chronological order but introduces the results according to the processes of the risk management as specified by ISO/IEC 27005.

### Conduct of the study

Risk assessment follows the process supported by TRICK Service and described in the user guide:



- Definition of the risk assessment scope
- Identification of the most important assets to consider
- Classification and estimation of the value of the selected assets
- Qualitative assessment of threats, vulnerabilities, and risks in brainstorming sessions
- Analysis of the current implementation level of security requirements and controls of the following frameworks:
    - ISO/IEC 27001,
    - ISO/IEC 27002,
- Quantitative assessment of likelihood and impact of selected risk scenarios on selected assets
- Assessment of privacy risks
- Estimation on the added value (ROSI) of security controls to be implemented with the help of TRICK Service
- Analysis of risk treatment options, feasibility, and deadlines for missing security controls
- Presentation of the risk treatment conclusions to risk owners
- Discussion, improvement, and validation of the results
- Validation of the risk treatment plan, statement of applicability, and residual risk
- Summary and presentation of the conclusions to top management for risk acceptance.

### General consideration regarding TRICK Service

#### Parameter setting and validity of the results

The risk estimation tool TRICK allows, via expert parameter setting, to adjust the effects of the measures implemented to adapt them to the risk scenarios. These parameters were discussed and consolidated at an expert meeting. Moreover, they have been refined during numerous evaluations carried out by itrust consulting.

The results obtained were studied in collaboration with business managers and considered plausible during the validation phase.

#### A methodology based on profitability

Using the TRICK Service methodology of itrust consulting, we estimated the risk reductions for the various measures that are to be implemented. We derived a first-risk treatment plan in which all missing controls are implemented in the same period. We then decided to consider several implementation phases. Then, based on resource availability, interdependencies, and preference for quick wins, and ROSI, we put each security action in one of the implementation phases. This was done in several iterative steps until the risk treatment plan was plausible and achievable. In the following, we present this proposed risk treatment plan in a top-down approach.

#### Parameter tuning

The risk assessment tool contains multiple parameters for estimating the effect of all measures on different risk scenarios. These parameters have been discussed and approved by a number of experts and have been used as the basis for estimating risk reduction for several previous itrust consulting clients.

The model built into TRICK is based on the mathematical concept that each security measure, when implemented, can reduce risk by a given factor. The underlying assumption is that the various security measures act independently, which is an appropriate model for estimating risk, but is certainly not always correct. For example, if we estimate that measure 1 reduces the risk by 10% and measure 2 by 20%, when they are implemented together, the risk is reduced by 1-(1-0.1)*(1-0.2) = 28% in our calculation. In practice, it may happen that measure 1 renders measure 2 ineffective, or that measure 1 even reinforces the other measures, but these aspects are not taken into account in our estimates.

In configuring all the risk reduction factors, TRICK used the simplified assumption that no measure can have an effect greater than the maximum risk reduction factor (maxRRF). By halving this parameter, all measures will have only half their effect on risk, so the maxRRF can be used to adjust the calculated residual risk to a plausible value relative to the current risk.

In this assessment, the FRR max has been set at 10%.

The result based on this value was deemed plausible during the validation phase.

### Links between process and documentation

The results of the different steps can be found in the following sections:

Identification of assets (see section 4.1);

Identification of threats (see section  4.2.2);

Identification of existing security measures (see chapter 5 anddeatils in the Annexe;

Identification of vulnerabilities through identification of missing security in the previous item (see section 4.2.3 and chapter 5;

Identification of consequences (impact estimated by considering the impact criteria (see section 6.1);

The assessment of the risk consequences (see section 6.3);

The assessment of the risk occurrence likelihood (see section 6.5);

The determination of the level of risk (see section 6).

The gab assessment update has been performed by considering the status of ISMS documents and the current progress on implementation, done by MD and CISO in two meetings (16+24 Jun). The risk assessment started wit ha brainstorming on 26 Juni) and continued with two assessmentmeetings (20 june and 14 july).

The Privacy risk were prepare by th CISO and reviewd by the MD during proof-reading.

The overall situation has been presented at the Management review meeting of 16 July 2025, them reviewed and approved.

## Risk context

### General considerations (cf. BeFresh-RiskMgt)

### Base criteria (cf. BeFresh-RiskMgt)

#### Risk evaluation criteria

Risks are assessed by considering :

the importance of the information for ensuring the operation of the activity relating to the target of the risk analysis ;

the direct financial consequences for income and expenditure;

the three aspects of security (confidentiality, integrity, availability).

#### Impact criteria

The impact of a security incident is estimated in terms of cost, i.e. potential financial loss. If this estimate is too uncertain, the impact is estimated by attributing a formal qualitative level of impact, such as: vital, extremely serious, very serious, serious, minor, insignificant. However, although qualitative in appearance, this scale is a logarithmic scale, for which each threshold is associated with a financial estimate of losses as they could be felt by the organization when such impacts occur. These thresholds will generally be linked to a percentage of turnover and to the conditions of sustainability of the activity.

### Risk acceptance criteria

#### For the brainstorming



- Risks for which the target's exposure is assessed as low or very low according to the first risk assessment approach (MAGERIT and item identified by ILR in Serima) are accepted and not explicitly considered in the treatment of risks.



| Risk level                             | Risk acceptance criteria                                                                                                                                                                    |
|----------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Normal Importance threshold: 14        | Informal risk management sufficient, where the asset owner defines and monitors the security measures.                                                                                      |
| DPIA Importance threshold: 29          | A DPIA approved by the risk owner is required for confirming the likelihood and risk levels, and for identifying an adequate risk treatment.                                                |
| Detailed DPIA Importance threshold: 44 | A detailed description of the processes risks is required and has to be formally validated by top management (e.g. detailed attack defence tree, technical vulnerability assessment, BIA).  |
| Unacceptable Importance threshold: 100 | The risk is unacceptable, except for a defined period during which it is weekly monitored by top management and monthly reported to the shareholders, the board, or the interested parties. |

Table 1 : Critères d’acceptation du risque

#### For the sum of the risks (assessed quantitatively)

In addition, there is a criterion based on the total estimated risks.

Risks are considered accepted as soon as the person responsible for is informed of the estimated risk and :

either the implementation of all the security measures provided for in the standards and regulations and estimated as cost-effective enough using the TRICK Service method has been planned,

or that sufficient measures have been planned to ensure that annual losses are less than 100% of turnover and lower then the estimated benefit of 4 years (400k€ TO in 2023, 85k€ benin in the last 2 years, 150k€ estimated in the next years.

Note : This veryhigh risk appetite is justified by the fact that

beFresh is a start up with limited capital accepting risk of failure,

has an insurance to lower the evaluated impact of this report,

and mainly bescaseu the impact are likelood are estimated in a very pessimistic way, ie. Are generally overrated.

### Description of the scope

The table below summarises the main characteristics and constraints for assessing and dealing with the risks of the target and its environment.



| Description                                                                                   | Value                                                                                                                                              |
|-----------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| Organization type                                                                             | Sàrl                                                                                                                                               |
| Profit type                                                                                   | Profit based                                                                                                                                       |
| Name of organism                                                                              | BeFresh s.àr.l.                                                                                                                                    |
| Organism presentation                                                                         | SW development                                                                                                                                     |
| Sector                                                                                        | ICT                                                                                                                                                |
| Responsible                                                                                   | Benoit Frisch                                                                                                                                      |
| Manpower                                                                                      | 2                                                                                                                                                  |
| Activities                                                                                    | SW development                                                                                                                                     |
| Business processes                                                                            | B-invoice (peppol compiant application) SW development for cusotmers Hosting of SW                                                                 |
| Legal, regulatory and contractual requirements applicable to the organization                 | Lu law                                                                                                                                             |
| The organization’s information security policy                                                | 0\_POL\_BeFresh-InfoSecPol\_v1.0 date 2025-03                                                                                                         |
| The organization’s overall approach to risk management                                        | 1\_POL\_BeFresh-ISMS\_v1.0 dated 2025-03                                                                                                              |
| Locations of the organization and their geographical characteristics                          | Kockelscheuer                                                                                                                                      |
| Various obligations                                                                           | OpenPeppol asbl (requiring 27001 certification for SW developper), NIS2, CR...                                                                     |
| Identification and analysis of the stakeholders                                               | OpenPeppol asbl, ILR, CNPD, ...                                                                                                                    |
| Establishment of the required relationships between the organization and stakeholders         | Newletters, email....                                                                                                                              |
| Expectation of stakeholders                                                                   | Cf. #1                                                                                                                                             |
| Socio-cultural environment                                                                    | Start-up                                                                                                                                           |
| Interfaces (i.e. information exchange with the environment)                                   | Email, Confcall, Meetings                                                                                                                          |
| Definition of roles and responsibilities                                                      | 2 people, i.e. very each responsibilities definition                                                                                               |
| Definition of escalation paths in case of change of risks                                     | All agents have direct path to MD                                                                                                                  |
| Development of the information security risk management process suitable for the organization | cf. #161                                                                                                                                           |
| Specification of records to be kept                                                           | Report #16R and export of OpenTRICK                                                                                                                |
| Excluded assets                                                                               | Nothing                                                                                                                                            |
| The organization’s functions and structure                                                    | cf. #502O (to be defined)                                                                                                                          |
| Strategic objectives, strategy and politics                                                   | "We provide software solutions and services for organisations that want to accelerate their digital transformation initiatives" source: befresh.lu |
| Financial parameters to define risk criteria                                                  | cf.                                                                                                                                                |
| Risk evaluation criteria                                                                      | cf. #16R                                                                                                                                           |
| Impact criteria                                                                               | cf. #16R and Impact table                                                                                                                          |
| Risk acceptance criteria                                                                      | cf. #16R                                                                                                                                           |

Table 2 : Considérations générales sur l’envergure de l’analyse de risque

## Risk identification

The objective of risk identification is to determine what might cause loss, and to understand how, where, and why these losses could happen. This phase prepares the risk assessment itself. It took place in the following order:



- Identification of assets;
- Identification of threats, vulnerabilities, and risk specificities (brainstorming);
- Identification of existing security measures (see Annex);
- Identification of consequences that loss of confidentiality, integrity or availability may have for the considered risk assessment target (details of the risk analysis can be found in Annex).

### Asset identification



<!-- image -->

Figure 5 : Asset Dependency based on ILR dependency model

This graphs shows how risk can propagate from one assets to other assets.

The following table lists the assets considered as sufficiently critical to be included in the risk analysis process. For each asset, a value has been estimated. The value represents the purchase price for Hardware, the efforts to invest to (re-)create the asset for Software), the annual turnover (for business services) and the yearly cost (for supporting service). Thus, the sum of these values is not a real economic value for the company, but only an indication of value to protect.

The expected annual losses (ALE) are shown in this table, but the justification is given in Chapter 5, as it results from the analysis of these risks.



|   Nr | Name              | Type               |   Value (k€) | ALE (k€)   | Comment                                                                                                         |
|------|-------------------|--------------------|--------------|------------|-----------------------------------------------------------------------------------------------------------------|
|    1 | SW-Dev            | Business process   |          250 | 15,7       | Largest customer: S&amp;A (which is shareholder)                                                                    |
|    2 | BeInvoice         | Software           |          200 | 11,8       | Internal development used for SaaS                                                                              |
|    3 | SaaS              | Business process   |          120 | 18,7       |                                                                                                                 |
|    4 | Deep              | Outsourced service |           60 | 5,3        |                                                                                                                 |
|    5 | Support+Consult   | Business process   |           25 | 28         |                                                                                                                 |
|    6 | VM-Webhosting     | System             |           10 | 16,7       | SV-8328LVP08                                                                                                    |
|    7 | VM-SaaS-Shared    | System             |            5 | 49,2       | SV-8328LVP03                                                                                                    |
|    8 | VM-SaaS-SNHBM     | System             |            5 | 49,2       | SV-8328LVP05                                                                                                    |
|    9 | LaptopsEtc        | Hardware           |            5 | 24,6       |                                                                                                                 |
|   10 | VM-SaaS-Editpress | System             |            5 | 10,8       | SV-8328LVP04                                                                                                    |
|   11 | VM-SaaSContainers | System             |            5 | 8,1        | SV-8328LVP07                                                                                                    |
|   12 | VM-SMP-Peppol     | System             |            5 | 8,1        | SV-8328LVP06 - Service Metadata Publishing for Peppol. ensures communication with business partner of customers |
|   13 | ITadmin           | Service            |            5 | 6,7        |                                                                                                                 |
|   14 | Peppol            | Outsourced service |            4 | 1,7        |                                                                                                                 |
|   15 | Phones            | Hardware           |            3 | 2          |                                                                                                                 |
|   16 | SE\_Dev            | Service            |            1 | 3,2        |                                                                                                                 |

Table 3 : List of assets in scope of the risk analysis



|   Nr | Name      | Type             |   Value (k€) |   ALE (k€) | Comment   |
|------|-----------|------------------|--------------|------------|-----------|
|    1 | Hosting   | Business process |           20 |          0 |           |
|    2 | Employees | Personnel        |            0 |          0 |           |
|    3 | Mgt       | Personnel        |            0 |          0 |           |
|    4 | Sales     | Service          |            0 |          0 |           |

Table 4 : List of assets considered out-of-scope of the current assessment

### Brainstorming

#### Summary

During expert meetings, threats, vulnerabilities, and risks logically ordered according to different criteria (MAGERIT method) are considered and assessed according to the level ++ and + in case organization is very exposed, n for a normal exposition, and - or -- whether the organization is less exposed than the normal level.



| Exposition   | Exposition   | Exposition      |
|--------------|--------------|-----------------|
| Zone         | Symbol       | Description     |
| 1            | - -          | Très faible     |
| 1            | -            | Faible          |
| 2            | N            | Normale         |
| 3            | +            | Importante      |
| 3            | + +          | Très importante |

Table 5 : Risk exposure scale

#### Threats exposure mapping

During this step, different threats have been considered. To ensure that the list of considered threats is sufficiently complete, the threats have been classified following the MAGERIT method. For each threat, the exposure of  towards this threat, compared to other companies has been estimated. The exposure level is estimated qualitatively with the help of the scale presented in the previous table.



|   Id | Threat                      | Acro   | Expo.   | Owner   | Comment                                                                                                                             |
|------|-----------------------------|--------|---------|---------|-------------------------------------------------------------------------------------------------------------------------------------|
| 1    | Sources                     |        |         |         |                                                                                                                                     |
| 1.1  | Natural                     | N      | N       | CEO     | Threats not initiated by human beings: snow, thunderstorms, are significant threats to the electricity grid.                        |
| 1.2  | Industrial origin           | I      | N       | CEO     |                                                                                                                                     |
| 1.3  | Technical failure           | T      | N       | CEO     | High internal control                                                                                                               |
| 1.4  | Internal human error        | Err    | -       | CEO     | All staff highly trained                                                                                                            |
| 1.5  | External wilful attack      | EW     | +       | CEO     | Possible due to the organization’s business practices covered by quantitative risk scenarios                                        |
| 1.6  | Internal wilful attack      | IW     | N       | CEO     | Unlikely that any internal employee would attack the organization.                                                                  |
| 2    | Asset classes               |        |         |         |                                                                                                                                     |
| 2.1  | 1 - Personnel               | P      | N       | CEO     | Trained Health and Safety Officer in charge.                                                                                        |
| 2.2  | 1 - Locations               | L      | N       | CEO     | Small secure offices in safe area. Doors and windows locked; access authorized to employees only; alarm protected                   |
| 2.3  | 1 - Auxiliary equipment     | AUX    | N       | CEO     | Managed by the Facility Manager (on behalf of CIP)                                                                                  |
| 2.4  | 1 - Other physical assets   | O      | N       | CEO     | None                                                                                                                                |
| 2.5  | 2 - Software                | SW     | N       | CEO     | Software developed in-house.                                                                                                        |
| 2.6  | 2 - Hardware                | HW     | N       | CEO     | server infrastructure managed by DEEP, Trusted Cloud, laptops are personally managed by respective employees                        |
| 2.7  | 2 - Communication networks  | COM    | N       | CEO     | managed Connected Office in place                                                                                                   |
| 2.8  | 2 - Media                   | Media  | N       | CEO     | Established policy in place for managing external media devices.                                                                    |
| 2.9  | 3 - Data / Information      | D      | +       | CEO     | Folders, documents, databases, encryption keys, etc., covered by quantitative risk scenario                                         |
| 2.1  | 4 - Services                | S      | N       | CEO     | Web, email, B2B, B2C, etc.                                                                                                          |
| 2.11 | 4 - Produced assets         | Pro    | N       | CEO     | Developed software: BeInvoice Software,                                                                                             |
| 2.12 | 4 - Objectives and missions | Obj    | N       | CEO     | Consulting and audit, research and development, training and awareness                                                              |
| 2.13 | 5 - Virtual assets          | null   | N       | CEO     | Customer or partner information                                                                                                     |
| 3    | Security aspects            |        |         |         |                                                                                                                                     |
| 3.1  | Confidentiality             | C      | +       | CEO     | BeFresh stores a lot of sensitive customer information                                                                              |
| 3.2  | Integrity                   | I      | +       | CEO     | Integrity required for documents and reporting, covered by quantitative risk scenarios                                              |
| 3.3  | Availability                | A      | N       | CEO     | managed Trusted cloud in 2 geograhic distrinct Tier IV datacenters                                                                  |
| 3.4  | Reliability                 | R      | N       | CEO     |                                                                                                                                     |
| 3.5  | Operability                 | O      | N       | CEO     |                                                                                                                                     |
| 3.6  | Privacy                     | P      | +       | DPO     | BeFresh stores a lot of sensitive customer information.                                                                             |
| 4    | Complexity                  |        |         |         |                                                                                                                                     |
| 4.1  | Extreme                     | E      | N       | CEO     | Organized crime                                                                                                                     |
| 4.2  | High                        | H      | +       | CEO     | Criminals, frustrated experts of the company, industrial spying, covered by quantitative risk scenarios.                            |
| 4.3  | Medium                      | M      | +       | CEO     | Hackers, crackers, previous employees, covered by quantitative risk scenarios                                                       |
| 4.4  | Low                         | L      | N       | CEO     | Normal internet attacks, script kiddies                                                                                             |
| 5    | Motive/Cause                |        |         |         |                                                                                                                                     |
| 5.1  | Chance/Accident             |        | -       | CEO     | Unlikely                                                                                                                            |
| 5.2  | Terrorism                   |        | -       | CEO     | Organized crime with political motivation                                                                                           |
| 5.3  | Economic spying             |        | N       | CEO     | Theft of information with an economic reason                                                                                        |
| 5.4  | Enrichment                  |        | N       | CEO     | Financial rewards                                                                                                                   |
| 5.5  | Economic advantage          |        | +       | CEO     | From competitors, and organization having advantage if large organization had not planned to locate their activities in Luxembourg. |
| 5.6  | Revenge                     |        | N       | CEO     | Competitors, previous employees, covered by quantitative risk scenarios                                                             |
| 5.7  | Political benefit           |        | N       | CEO     |                                                                                                                                     |
| 5.8  | Media presence              |        | -       | CEO     |                                                                                                                                     |
| 5.9  | Personal satisfaction       |        | +       | CEO     | Ego, challenge, rebellion, social position, curiosity, covered by quantitative risk scenarios                                       |
| 5.1  | Errors and omissions        |        | +       | CEO     | Programming mistake, data capture error, covered by quantitative risk scenario                                                      |

Table 6 : Cartographie des menaces

#### Vulnerabilities exposure mapping

A threat can only become a risk if there are vulnerabilities that can be exploited by the threat. For this, it is very important to know the vulnerabilities of the target to analyse to be able to plan corrective and preventive measures to avoid such an exploitation of a vulnerability by a threat.



| Id   | Vulnerability                                                                                                                                | Expo.   | Owner   | Comment                                                                |
|------|----------------------------------------------------------------------------------------------------------------------------------------------|---------|---------|------------------------------------------------------------------------|
| S    | All specific vulnerabilities defined by ILR in Serima                                                                                        |         | CTO     | All Serima vulnerabilities have been assessed by CHA+BFR on 202506120. |
| S.01 | Unstable power grid                                                                                                                          | -       | CTO     |                                                                        |
| S.02 | Poor password management                                                                                                                     | -       | CTO     |                                                                        |
| S.03 | No substitution equipment / single point of failure                                                                                          | N       | CTO     |                                                                        |
| S.04 | Lack of security awareness                                                                                                                   | N       | CTO     |                                                                        |
| S.05 | Insufficient maintenance/faulty installation of storage media                                                                                | -       | CTO     | Maintenance to be monitored                                            |
| S.06 | Wrong allocation of access rights                                                                                                            | -       | CTO     | cf physical access                                                     |
| S.07 | Incorrect parameter set up                                                                                                                   | N       | CTO     |                                                                        |
| S.08 | Insufficient security training                                                                                                               | N       | CTO     |                                                                        |
| S.09 | Permanent loss: Loss of an asset, which can be partial considering incomplete recovery or full in case of non-existing recovery possibility. | +       | CTO     | Covered by Risk scenario                                               |
| S.10 | Temporary unavailability: The asset is temporarily nonoperational.                                                                           | N       | CTO     | Covered by Risk scenario                                               |
| S.11 | Partial theft coming from external: An essential part of an asset was stolen without complicity of an internal person.                       | +       | CTO     | Covered by Risk scenario                                               |
| S.12 | Deliberate disclosure: An internal staff copies the entire asset to disclose it.                                                             | -       | CTO     | only 2 staff, C2 scenario not needed in this assessment                |
| S.13 | Accidental disclosure: Following a false handling, an important part becomes accessible to people that are not authorized.                   | +       | CTO     | Covered by Risk scenario                                               |
| S.14 | External fraudulent manipulation: An external person succeeds penetrating and handling an asset.                                             | N       | CTO     | Covered by Risk scenario                                               |
| S.15 | Internal fraudulent manipulation: An internal person handles an asset to create an illicit advantage.                                        | -       | CTO     | only 2 staff, C2 scenario not needed in this assessment                |
| S.16 | Accidental manipulation: A technical or organizational error causes a corruption of an asset.                                                | +       | CTO     | Covered by Risk scenario                                               |
| S.17 | Uncontrolled copying                                                                                                                         | N       | CTO     |                                                                        |
| S.18 | Lack of identification and authentication of sender and receiver                                                                             | N       | CTO     |                                                                        |
| S.19 | Unprotected public network connections                                                                                                       | N       | CEO     |                                                                        |
| S.20 | Lack of monitoring mechanisms                                                                                                                | N       | CTO     |                                                                        |
| S.21 | Lack of care at disposal                                                                                                                     | -       | CTO     | Onsite schredder                                                       |
| S.22 | Lack of formal procedure for user registration and de-registration                                                                           | +       | CTO     |                                                                        |
| S.23 | Lack of formal process for access right review (supervision)                                                                                 | +       | CTO     |                                                                        |
| S.24 | Inadequate network management (resilience of routing)                                                                                        | N       | CTO     |                                                                        |
| S.25 | Lack of identification and authentication mechanisms like user authentication                                                                | -       | CTO     |                                                                        |
| S.26 | Incorrect use of software and hardware                                                                                                       | N       | CTO     |                                                                        |
| S.27 | Supplier with extended privileges and without controls                                                                                       | +       | CTO     |                                                                        |
| S.28 | Lack of procedure for the control of the external personnel’s interventions on the organization’s equipments                                 | +       | CTO     |                                                                        |
| S.29 | Lack of periodic replacement schemes                                                                                                         | N       | CTO     |                                                                        |
| S.30 | Complicated user interface                                                                                                                   | N       | CTO     |                                                                        |
| S.31 | No Iogout when leaving the workstation                                                                                                       | N       | CTO     |                                                                        |
| S.32 | No control of access to the site or premises or possibility of intrusion via indirect access routes.                                         | N       | CTO     |                                                                        |
| S.33 | The network makes it easy for unauthorized persons to use the resources.                                                                     | N       | CTO     |                                                                        |
| S.34 | Problems in change management or software maintenance                                                                                        | N       | CTO     | ch #832                                                                |
| S.35 | No contractual clauses covering the security measures to be observed by subcontractors and suppliers.                                        | N       | CTO     |                                                                        |

Table 7 : Liste des vulnérabilités

#### Risk exposure mapping

After considering general aspects in the mapping of threats, we have considered the threats grouped by sources, to roughly estimate the exposure of the company against these threats. This evaluation considers not only the strength and frequency of the threat, but also the level of vulnerability of targeted assets and the impact on the company.



|   Id | Risk                                                         | Expo.   | Owner   | Comment                                                                                                                                                                                                                                                         |
|------|--------------------------------------------------------------|---------|---------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1    | Natural                                                      |         |         |                                                                                                                                                                                                                                                                 |
| 1.1  | Fire                                                         | N       | CEO     | No specific natural source for fire in the neighbourhood.                                                                                                                                                                                                       |
| 1.2  | Water                                                        | -       | CEO     | Geographical location makes it unlikely.                                                                                                                                                                                                                        |
| 1.3  | Lightning                                                    | N       | CEO     |                                                                                                                                                                                                                                                                 |
| 1.4  | Storm                                                        | N       | CEO     |                                                                                                                                                                                                                                                                 |
| 1.5  | Mudslide                                                     | --      | CEO     | Geographical location makes it highly unlikely.                                                                                                                                                                                                                 |
| 1.6  | Earthquake                                                   | --      | CEO     | Geographical location makes it highly unlikely.                                                                                                                                                                                                                 |
| 1.7  | Avalanche                                                    | --      | CEO     | Geographical location makes it highly unlikely.                                                                                                                                                                                                                 |
| 1.8  | Unsuitable temperature                                       | -       | CEO     | Central heating, separate air-conditioning units - office is well ventilated.                                                                                                                                                                                   |
| 1.9  | Epidemic                                                     | N       | CEO     | Close proximity of staff.                                                                                                                                                                                                                                       |
| 2    | Industrial environment                                       |         | CEO     |                                                                                                                                                                                                                                                                 |
| 2.1  | Fire                                                         | -       | CEO     | Fire alarm is in place as well as fire safety rules and evacuation instructions - possible but well managed in case of any event.                                                                                                                               |
| 2.2  | Dust                                                         | -       | CEO     | Building is cleaned on a regular basis.                                                                                                                                                                                                                         |
| 2.3  | Electromagnetic radiation                                    | -       | CEO     |                                                                                                                                                                                                                                                                 |
| 2.4  | Electrostatic pulse                                          | -       | CEO     |                                                                                                                                                                                                                                                                 |
| 2.5  | Other                                                        | N       | CEO     |                                                                                                                                                                                                                                                                 |
| 2.6  | Failure of water supply                                      | N       | CEO     | Unlikely.                                                                                                                                                                                                                                                       |
| 2.7  | Failure of electricity supply                                | -       | CEO     | Tier4 datacentre, and 2 sites.                                                                                                                                                                                                                                  |
| 2.8  | Power interruption                                           | N       | CEO     | No previous incident.                                                                                                                                                                                                                                           |
| 2.9  | Other failures or external accident                          | N       | CEO     |                                                                                                                                                                                                                                                                 |
| 2.1  | Electrical fluctuation                                       | N       | CEO     |                                                                                                                                                                                                                                                                 |
| 2.11 | Loss of phone communication                                  | N       | CEO     | As well as internal company phone, all staff have personal phone for work use.                                                                                                                                                                                  |
| 2.12 | Loss of internet communication                               | -       | CEO     | Connected office, Wifi with 2 internet connextions can be used as backup (to LAN); 4G is other backup.                                                                                                                                                          |
| 2.13 | Loss of other communication channels                         | -       | CEO     | Only the internet and phones.                                                                                                                                                                                                                                   |
| 2.14 | Pollution                                                    | -       | CEO     | Very unlikely.                                                                                                                                                                                                                                                  |
| 2.15 | Loss of building access                                      | -       | CEO     | There are multiple entrances to the building - This includes entrance via the access of CIP.                                                                                                                                                                    |
| 3    | Internal technical failure                                   |         | CEO     |                                                                                                                                                                                                                                                                 |
| 3.1  | Fire                                                         | -       | CEO     |                                                                                                                                                                                                                                                                 |
| 3.2  | Equipment failure                                            | N       | CEO     |                                                                                                                                                                                                                                                                 |
| 3.3  | Software failure                                             | N       | CEO     | Software failures do exist but are followed by the Redmine ticketing system.                                                                                                                                                                                    |
| 3.4  | Other                                                        | N       | CEO     |                                                                                                                                                                                                                                                                 |
| 3.5  | Electrical failure                                           | N       | CEO     |                                                                                                                                                                                                                                                                 |
| 3.6  | Air-conditioning failure                                     | -       | CEO     | Several mobile air-conditioning units which are new.                                                                                                                                                                                                            |
| 3.7  | Cabling failure                                              | -       | CEO     |                                                                                                                                                                                                                                                                 |
| 3.8  | Transmission errors                                          | -       | CEO     |                                                                                                                                                                                                                                                                 |
| 4    | Human errors                                                 |         | CEO     |                                                                                                                                                                                                                                                                 |
| 4.1  | Maintenance error                                            | -       | CEO     | It is ensured that staff members who are responsible for maintenance are competent at their job.                                                                                                                                                                |
| 4.2  | Operational error                                            | N       | CEO     |                                                                                                                                                                                                                                                                 |
| 4.3  | Planning error                                               | N       | CEO     |                                                                                                                                                                                                                                                                 |
| 4.4  | Staff shortage                                               | N       | CEO     | Company continues to grow.                                                                                                                                                                                                                                      |
| 5    | External malicious individual                                |         | CEO     |                                                                                                                                                                                                                                                                 |
| 5.1  | Malicious code                                               | N       | CEO     | No security incident reported or discovered. Staff security awareness and best practices are provided to staff on an ad hoc basis, and for new recruits upon the assumption of duties.                                                                          |
| 5.2  | Sniffing                                                     | N       | CEO     | idem                                                                                                                                                                                                                                                            |
| 5.3  | Eavesdropping                                                | N       | CEO     | idem                                                                                                                                                                                                                                                            |
| 5.4  | Traffic analysis                                             | N       | CEO     | idem                                                                                                                                                                                                                                                            |
| 5.5  | Hacker                                                       | N       | CEO     |                                                                                                                                                                                                                                                                 |
| 5.6  | Social engineering                                           | N       | CEO     | No security incident reported/discovered. Staff security awareness/best practices are provided to staff on an ad hoc basis, and for new recruits upon the assumption of duties.                                                                                 |
| 5.7  | Crime                                                        | -       | CEO     | No documented threat or visibility of threat; appropriate protection in place.                                                                                                                                                                                  |
| 5.8  | Theft                                                        | -       | CEO     | No documented threat or visibility of threat; appropriate protection in place.                                                                                                                                                                                  |
| 5.9  | Theft of information                                         | N       | CEO     | No documented threat or visibility of threat; appropriate protection in place.                                                                                                                                                                                  |
| 5.1  | Masquerading of user identity                                | N       | CEO     | No documented threat or visibility of threat; appropriate protection in place.                                                                                                                                                                                  |
| 5.11 | Theft of informatics resource                                | N       | CEO     | No documented threat or visibility of threat; appropriate protection in place.                                                                                                                                                                                  |
| 5.12 | Economic spying                                              | N       | CEO     | No documented threat or visibility of threat; appropriate protection in place.                                                                                                                                                                                  |
| 5.13 | Industrial spying                                            | N       | CEO     | No documented threat or visibility of threat; appropriate protection in place.                                                                                                                                                                                  |
| 5.14 | Terrorist                                                    | N       | CEO     | No documented threat or visibility of threat; appropriate protection in place.                                                                                                                                                                                  |
| 5.15 | Blackmailing                                                 | N       | CEO     | No documented threat or visibility of threat; appropriate protection in place.                                                                                                                                                                                  |
| 5.16 | Information warfare                                          | N       | CEO     | No documented threat or visibility of threat; appropriate protection in place.                                                                                                                                                                                  |
| 5.17 | Aggressor                                                    | N       | CEO     | No documented threat or visibility of threat; appropriate protection in place.                                                                                                                                                                                  |
| 6    | Internal malicious individual                                |         | CEO     |                                                                                                                                                                                                                                                                 |
| 6.1  | Authorized individual                                        | -       | CEO     |                                                                                                                                                                                                                                                                 |
| 6.2  | Unauthorized individual                                      | -       | CEO     |                                                                                                                                                                                                                                                                 |
| 6.3  | Illegal use of software                                      | -       | CEO     |                                                                                                                                                                                                                                                                 |
| 6.4  | Malicious code                                               | -       | CEO     |                                                                                                                                                                                                                                                                 |
| 6.5  | Illegal import/export of software                            | -       | CEO     |                                                                                                                                                                                                                                                                 |
| 6.6  | Hacker                                                       | N       | CEO     | No security incident reported/discovered. Staff security awareness/best practices are provided to staff on an ad hoc basis, and for new recruits upon the assumption of duties. Collaboration with CIO on alerts as per Kibana dashboard and/or firewall alert. |
| 6.7  | Social engineering                                           | N       | CEO     | idem                                                                                                                                                                                                                                                            |
| 6.8  | Mobbing                                                      | -       | CEO     |                                                                                                                                                                                                                                                                 |
| 6.9  | Theft                                                        | -       | CEO     |                                                                                                                                                                                                                                                                 |
| 6.1  | Theft of information                                         | -       | CEO     | No documented threat or visibility of threat; appropriate protection in place.                                                                                                                                                                                  |
| 6.11 | Data manipulation                                            | -       | CEO     |                                                                                                                                                                                                                                                                 |
| 6.12 | Aggressor                                                    | -       | CEO     | No documented threat or visibility of threat; appropriate protection in place.                                                                                                                                                                                  |
| 6.13 | Saboteur                                                     | -       | CEO     | No documented threat or visibility of threat; appropriate protection in place.                                                                                                                                                                                  |
| 7    | Risks specific for personally identifiable information (PII) | N       | CEO     |                                                                                                                                                                                                                                                                 |
| 7.1  | Processing considered illegitimate                           | -       | CEO     | cf #2R                                                                                                                                                                                                                                                          |
| 7.2  | Insufficiently documented purpose                            | +       | CEO     |                                                                                                                                                                                                                                                                 |
| 7.3  | Lack of necessity and proportionality                        | -       | CEO     | cf #2R in progress                                                                                                                                                                                                                                              |
| 7.4  | Data inaccuracy                                              | -       | CEO     | Cf. STA\_02-0-A\_ITR-ProcesRec\_v1.5                                                                                                                                                                                                                               |
| 7.5  | Breach of loyalty                                            | -       | CEO     |                                                                                                                                                                                                                                                                 |
| 7.6  | Security and confidentiality risk                            | N       | CEO     | cf  this report                                                                                                                                                                                                                                                 |
| 7.7  | Unlawful access to PII                                       | -       | CEO     | cf. Access policy                                                                                                                                                                                                                                               |
| 7.8  | Disappearance of PII                                         | -       | CEO     | cf BCP/DRP                                                                                                                                                                                                                                                      |
| 7.9  | Undesirable manipulation of PII                              | N       | CEO     | Old disks are stored in safes and cannot be manipulated.                                                                                                                                                                                                        |
| 7.1  | Lack of transparency for affected persons                    | N       | CEO     | cf #2R, in progress                                                                                                                                                                                                                                             |
| 7.11 | Risks on protections of sensitive PII                        | -       | CEO     | cf #2R, in progress                                                                                                                                                                                                                                             |
| 7.12 | Non-compliance of right to be informed or right to object    | -       | CEO     | cf #2R, in progress                                                                                                                                                                                                                                             |
| 7.13 | Unnecessarily long storage of data                           | N       | CEO     | cf #2R, in progress                                                                                                                                                                                                                                             |
| 7.14 | Correlation of PII                                           | N       | CEO     |                                                                                                                                                                                                                                                                 |
| 7.15 | Unawareness of personnel handling PII                        | N       | CEO     |                                                                                                                                                                                                                                                                 |

Table 8 : Cartographie des risques

## Gap analysis

### Summary

The level of compliance with information security practices (27002) is quite good, but still leaves room for some improvement in terms of risk management.

The level of compliance with management requirements (27001) is vers high, but the ISMS need matured so that the estimated will be more reliable.

### Methodology

To identify the security measures and assess both the level of current implementation and the resources required for their full implementation, the consultant entered the following information in the TRICK Service tool for an exhaustive list of security measures selected from standards, regulations or good security practice:Ref: the reference of security control;

Domain: the area (and title);

ST: the status i.e. AP if applicable, NA if not applicable, or M if mandatory;

IR: the current implementation rate (indicating the estimated current implementation level of the indicated measure). This rate is expressed as a percentage. If a measure is partially implemented, the risk rate should be estimated: The 80% indication means that the potential of this measure to reduce the total risk is reached at 80%. In this estimate, the implementation guidance related to the measure should also be considered: if a measure is mandatory and implemented for 2 assets, and optional and not implemented for a third, and if these assets have the same value and risk exposure, then the rate should be estimated at 67%. On the other hand, if a required part of a measure is not implemented, a value lower than the threshold parameter ‘Declaration of Applicability’ is chosen, in order to indicate that the implementation of the measure will be considered insufficient in case of audit and that further action is necessary before achieving compliance. 	
If it is difficult to reach consensus on estimates of these rates, the number of permitted values can be restricted, and simplified criteria can be used.

IW: the internal set up workload, showing how many days of internally work are necessary to implement the security measure;

EW: the external set up showing how many days of work of a service provider is needed to implement the security measure;

Inv: the investment budget in k€ indicating what is expected in addition to internal and external resources to implement the measure;

LT : the lifetime in years of the measure;

IM: the yearly internal workload to maintain the security control;

EM: the yearly external workload to maintain the security control;

RI: the recurrent investments for maintaining the security control;

CS: the annual cost in k€, calculated from the previous settings (considering the average cost of one internal person day and of one external person day;

Comment: a justification of the provided estimates;

To do: a description of the actions to be taken to achieve full compliance.

The details evaluation of the implementation level and justification are given in the Annex.

### Compliance level for ISO/IEC 27001

This section presents the results of the estimates of the rate of compliance with the requirements of ISO/IEC 27001. The numbers represent the different chapters of the standard. The following graph shows the average compliance rate for each chapter.

Figure 6 : Taux de conformité ISO/IEC 27001 pendant les différentes phases d’implémentation

### Compliance level for ISO/IEC 27002

Similar to the previous section, we have estimated the rate of compliance with the ISO/IEC 27002 standard. The following figure shows the current level of compliance according to the main areas of information systems security:

Figure 7 : Taux de conformité ISO/IEC 27002 pendant les différentes phases d’implémentation

## Risk analysis

The risk analysis includes several phases:



- Choice of methodology (cf. #161 and TRICK udser guide)

Determining the estimated consequences of the risks in relation to a predefined scale.

Determination of the estimated probability of occurrence of the risks in relation to a predefined scale.

Determination of the level of risk (see Annex).

In what follows, we provide

a summary of the assessment ;

the risk scenarios considered ;

the parameters of the methodology required to understand the assessment;

an overview of the specific privacy risks;

an overview of the risk assessed quantitatively:

the estimated details, sorted by active most at risk.

To summarise :

The risks were assessed using the methodology proposed by itrust consulting, and documented for the TRICK Service tool.

The most significant risks concern integrity, followed by confidentiality. Less important is availabilités and SW devel and even SaaS is not related to penalty and availabiltés, and in general, invoicing activities, support by BeFresh is considered no critical (1w) for his customer.

### Risk scenarios and likelihood &amp; impact scales

In this stage, the risks have been quantified with the help of TRICK Service. The annual losses for the generic risk scenarios described below and regrouping the most essential threats and vulnerabilities in relation to the four information security aspects: Confidentiality, Integrity, Availability and Privacy have been quantified.



|   Nr | Name             | Description                                                                                                                                                                                                                                                            |
|------|------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|    1 | Ap-PermLoss      | Ap : Complete loss, incl. backup: Loss of the entire assets, including backup.                                                                                                                                                                                         |
|    2 | At-TmpUnavail    | At : Tempoary or partial loss: A part of the asset is lost or the asset is temporarily non-operational.                                                                                                                                                                |
|    3 | C1-PartExtTheft  | C1: Partial external theft: An essential part of an asset was stolen without complicity of an internal person.                                                                                                                                                         |
|    4 | C3-AccidDiscl    | C3: Accidental disclosure: Following a false handling, an important part becomes accessible to people that are not authorized.                                                                                                                                         |
|    5 | P1-LawfFairTrans | P1: Lack of lawfulness, fairness and transparency: Personal data is not processed lawfully or fairly, or in a non-transparent manner in relation to the data subject.                                                                                                  |
|    6 | P2-PurpLimit     | P2: Lack of purpose limitation: Personal data is not collected for specified, explicit or legitimate purposes, or further processed in a manner that is incompatible with those purposes.                                                                              |
|    7 | P3-DataMin       | P3 : Lack of data minimization: The collection of personal data is not adequate, relevant or limited to what is necessary in relation to the purposes for which they are processed.                                                                                    |
|    8 | P4-Accuracy      | P4 : Lack of accuracy: Personal data is not accurate or, where necessary, kept up to date.                                                                                                                                                                             |
|    9 | P5-StorageLim    | P5: Lack of storage limitation: Personal data is kept in a form which permits identification of data subjects for longer than is necessary for the purposes for which the personal data are processed.                                                                 |
|   10 | P6-Identif       | P6: Identification: The link between an identity and a piece of information is not sufficiently hidden, so that identities can be inferred when some effort is invested.                                                                                               |
|   11 | P7-Non-repud     | P7: Non-repudiation: Data can be used to prove that a particular person has committed a particular action.                                                                                                                                                             |
|   12 | P8-DetectExist   | P8: Detection of existence: Uninvolved parties can determine if a particular item of interest (such as a data record, an action, an event...) exists or not. The knowledge of the existence of such an item can often be used to find more information about a person. |
|   13 | P9-Unaware       | P9: Unawareness: An internal person owns or discloses PII of customers, without being aware of the nature of the information, or of the legal implications.                                                                                                            |
|   14 | I1-ExtManip      | I1: External fraudulent manipulation: An external person succeeds penetrating and handling an asset.                                                                                                                                                                   |
|   15 | I3-AccidManip    | I3: Accidental manipulation: A technical or organizational error causes a corruption of an asset.                                                                                                                                                                      |

Table 9 : Considered risk scenarios

Il revient normalement au consultant en relation avec les responsables métiers d’estimer les risques en considérant les pertes financières probables en cas de survenance du risque. Cependant au cours de l’estimation des risques, il arrive qu’une estimation quantitative soit trop incertaine et qu’elle ne puisse être envisagée que de manière qualitative. Et afin, malgré tout, de pouvoir établir un bilan financier des pertes attendues et de mesures de la rentabilité des mesures, nous traduisons les estimations qualitatives en estimation quantitative en nous servant des échelles de valeurs suivantes.

#### Probability



|   Level | Acronym   | Qualification                                      | Value (/y)   | From   | To   |
|---------|-----------|----------------------------------------------------|--------------|--------|------|
|       0 | p0        | Never occuring (or less than every 100 years)      | 0,01         | 0      | 0,01 |
|       1 | p1        | A priorio not occuring, very improbable (50 years) | 0,02         | 0,01   | 0,02 |
|       2 | p2        | Isolated / rare event (30 years)                   | 0,03         | 0,02   | 0,04 |
|       3 | p3        |                                                    | 0,06         | 0,04   | 0,08 |
|       4 | p4        | Repetitive / possible event (10 years)             | 0,1          | 0,08   | 0,13 |
|       5 | p5        |                                                    | 0,18         | 0,13   | 0,24 |
|       6 | p6        | Recurring / probable event (3 years)               | 0,33         | 0,24   | 0,44 |
|       7 | p7        |                                                    | 0,57         | 0,44   | 0,76 |
|       8 | p8        | Common / very probable event (yearly)              | 1            | 0,76   | 1,3  |
|       9 | p9        |                                                    | 1,7          | 1,3    | 2,3  |
|      10 | p10       | Constant / certain event (quarterly)               | 3            | 2,3    | +∞   |

Table 10 : Probability scale

#### Financial consequence

#### Total consequence



|   Level | Acronym   | Qualification                                         | Value (k€/y)   | From    | To      |
|---------|-----------|-------------------------------------------------------|----------------|---------|---------|
|       0 | i0        | insignificant                                         | 2              | 0       | 3       |
|       1 | i1        |                                                       | 4,5            | 3       | 6,7     |
|       2 | i2        | minor                                                 | 10             | 6,7     | 12,2    |
|       3 | i3        |                                                       | 15             | 12,2    | 19,4    |
|       4 | i4        | serious                                               | 25             | 19,4    | 35,4    |
|       5 | i5        |                                                       | 50             | 35,4    | 70,7    |
|       6 | i6        | very serious                                          | 100            | 70,7    | 141,4   |
|       7 | i7        |                                                       | 200            | 141,4   | 282,8   |
|       8 | i8        | extremely serious                                     | 400            | 282,8   | 565,7   |
|       9 | i9        |                                                       | 800            | 565,7   | 1 095,4 |
|      10 | i10       | vital (400k€ TO; 12.5k€Capital, current assets: 189k€ | 1 500          | 1 095,4 | +∞      |

Table 11 : Financiel consequence scale

### Typology of estimated risks

This section includes figures that illustrate which assets and asset types are most exposed to risks (Figure 8 et Figure 9) et and from which risk scenarios and risk scenario types most risks are resulting from (Figure 10 et Figure 11) ). It provided a high-level overview of the detailed assessment in which we sum up over all assets or over all scenarios depending on the figures.

The Annual Loss expectancy, for all risk scenarios together, but split over the different assets are shown in the following graph.

Figure 8 : Perte annuelle attendue (ALE) par actif

Figure 9 : Perte annuelle attendue (ALE) par type d’actif

Figure 10 : Perte annuelle attendue (ALE) par scénario de risque

Figure 11 : Perte annuelle attendue (ALE) par type de scénario de risque

### Risk analysis approach

#### Parameter preparation

A impact calculation meth may by applied in further iterations of the risk assesment.

### Risk for PII principals (DPIA)

#### Overview on risk for PII principals

The risks for PII principals are illustrated in the following risk heat map. This map depicts how many assets-risk scenarios of those studied before, have which impact and which likelihood.



| Impact      | 10:IP10-huge-max   |             |               |             |               |             |              |             |             |             |               |
|-------------|--------------------|-------------|---------------|-------------|---------------|-------------|--------------|-------------|-------------|-------------|---------------|
| Impact      | 9:IP9-sign-max     |             |               |             |               |             |              |             |             |             |               |
| Impact      | 8:IP8-few-max      |             |               |             |               |             |              |             |             |             |               |
| Impact      | 7:IP7-huge-sign    |             |               |             |               |             |              |             |             |             |               |
| Impact      | 6:IP6-sign-sign    |             |               |             |               |             |              |             |             |             |               |
| Impact      | 5:IP5-few-sign     |             |               |             |               |             |              |             |             |             |               |
| Impact      | 4:IP4-sign-lim     |             |               |             |               |             |              |             |             |             |               |
| Impact      | 3:IP3-few-lim      |             |               | 9           | 12            | 6           |              |             |             |             |               |
| Impact      | 2:IP2-sign-neg     |             |               |             |               |             |              |             |             |             |               |
| Impact      | 1:IP1-few-neg      | 1           | 1             | 9           | 11            | 6           | 3            | 1           |             |             |               |
| Impact      |                    | 1:p1        | 2:p2 (1×/30y) | 3:p3        | 4:p4 (1×/10y) | 5:p5        | 6:p6 (1×/3y) | 7:p7        | 8:p8 (1×/y) | 9:p9        | 10:p10 (3×/y) |
| Probability | Probability        | Probability | Probability   | Probability | Probability   | Probability | Probability  | Probability | Probability | Probability | Probability   |

Figure 12: Matrice des risques

### Details of the risk analysis

The following table shows for each pair of assets and threats:

the impact when the threat occurs on the asset (in kilo euros or using the value of the impact scale);

the probability of the occurrence of the threat within one year.

These estimations allowed to compute the Annual Loss Expectancy (ALE) which represents the current financial risk of the organization regarding the information security. The ALE is computed by multiplying the impact with the probability of occurrence per year, and the ALE for each asset is obtained by adding the ALE for all risk scenarios.

Total ALE of assets	259,9 k€

VM-SaaS-Shared

Total ALE due to the risk for the asset	49,2 k€



| Scenarios       | Fin. (k€)   | P.   | ALE (k€)   | Owner   | Comment                                           |
|-----------------|-------------|------|------------|---------|---------------------------------------------------|
| Ap-PermLoss     | 5           | p4   | 0,5        | MD      |                                                   |
| At-TmpUnavail   | 4,5         | p6   | 1,5        | MD      |                                                   |
| C1-PartExtTheft | 100         | p4   | 10,0       | MD      |                                                   |
| C3-AccidDiscl   | 100         | p5   | 18,2       | MD      | Impact as fir C1, but a bit more likely           |
| I1-ExtManip     | 100         | p4   | 10,0       | MD      |                                                   |
| I3-AccidManip   | 50          | p5   | 9,1        | MD      | Slighly likelier than I1 attack with lower impact |

Table 15: Risk estimation for the asset VM-SaaS-Shared

VM-SaaS-SNHBM

Total ALE due to the risk for the asset	49,2 k€



| Scenarios       | Fin. (k€)   | P.   | ALE (k€)   | Owner   | Comment                                                                                                                  |
|-----------------|-------------|------|------------|---------|--------------------------------------------------------------------------------------------------------------------------|
| Ap-PermLoss     | 5           | p4   | 0,5        | MD      |                                                                                                                          |
| At-TmpUnavail   | 4,5         | p6   | 1,5        | MD      |                                                                                                                          |
| C1-PartExtTheft | 100         | p4   | 10,0       | MD      | Impact included loss of business                                                                                         |
| C3-AccidDiscl   | 100         | p5   | 18,2       | MD      | Impact as fir C1, but a bit more likely                                                                                  |
| I1-ExtManip     | 100         | p4   | 10,0       | MD      | A liabilty of i7 could not get undetected by internal customer processes, so that a max impact of i6 is considered here. |
| I3-AccidManip   | 50          | p5   | 9,1        | MD      | Slighly likelier than I1 attack with lower impact                                                                        |

Table 16: Risk estimation for the asset VM-SaaS-SNHBM

Support+Consult

Total ALE due to the risk for the asset	28 k€



| Scenarios        | Fin. (k€)   | P.   | ALE (k€)   | Owner   | Comment                                                                                            |
|------------------|-------------|------|------------|---------|----------------------------------------------------------------------------------------------------|
| Ap-PermLoss      | 25          | p4   | 2,5        | MD      |                                                                                                    |
| At-TmpUnavail    | 10          | p7   | 5,7        | MD      |                                                                                                    |
| C1-PartExtTheft  | 15          | p3   | 0,9        | MD      | Risk sc. Seningd info to impersonated customer; quite unlikely as customers are personnelly known. |
| C3-AccidDiscl    | 15          | p4   | 1,5        | MD      | Impact as fir C1, but a bit more likely                                                            |
| I1-ExtManip      | 70          | p4   | 7,0        | MD      | Social eng against beFresh to make errounous config change                                         |
| I3-AccidManip    | 50          | p5   | 9,1        | MD      | Slighly likelier than I1 attack with lower impact                                                  |
| P1-LawfFairTrans | 4,5         | p3   | 0,3        | MD      |                                                                                                    |
| P2-PurpLimit     | 4,5         | p3   | 0,3        | MD      |                                                                                                    |
| P3-DataMin       | 4,5         | p3   | 0,3        | MD      |                                                                                                    |
| P4-Accuracy      | 4,5         | p3   | 0,3        | MD      |                                                                                                    |
| P6-Identif       | 4,5         | 0    | 0          | MD      | No hiding of PII                                                                                   |
| P7-Non-repud     | 4,5         | p3   | 0,3        | MD      |                                                                                                    |

Table 17: Risk estimation for the asset Support+Consult

LaptopsEtc

Total ALE due to the risk for the asset	24,6 k€



| Scenarios     | Fin. (k€)   | P.   | ALE (k€)   | Owner   | Comment                                           |
|---------------|-------------|------|------------|---------|---------------------------------------------------|
| Ap-PermLoss   | 5           | p5   | 0,9        | MD      |                                                   |
| At-TmpUnavail | 4,5         | p6   | 1,5        | MD      |                                                   |
| I1-ExtManip   | 50          | p6   | 16,5       | MD      |                                                   |
| I3-AccidManip | 10          | p7   | 5,7        | MD      | Slighly likelier than I1 attack with lower impact |

Table 18: Risk estimation for the asset LaptopsEtc

SaaS

Total ALE due to the risk for the asset	18,7 k€



| Scenarios        | Fin. (k€)   | P.   | ALE (k€)   | Owner   | Comment                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
|------------------|-------------|------|------------|---------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Ap-PermLoss      | 120         | p2   | 4,0        | MD      | No penality by customer, impact is loss in revenue. Saas Server could be decommissioned easily (5k €*5month transition + 25 cost of closing the activity.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| At-TmpUnavail    | 25          | p4   | 2,5        | MD      | No penalities but loss of ; some cumsomt want to leave after 72 h or unavailability                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| C1-PartExtTheft  | 15          | p4   | 1,5        | MD      | DB Contains 127k invoices since 2022. Ex of critical invoiced: buisness trop in public sector, commercial secret (such a prices of houses…) Risk covers on Systen, here impact due to a signed loss of an info.                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| C3-AccidDiscl    | 10          | p5   | 1,8        | MD      | cf. C3 but less impact                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| I1-ExtManip      | 50          | p4   | 5,0        | MD      | SW tried to avoid invoice such as account number manipulation; as such change are performed by BeFesh on written request.Wring establied invioceare not ncessariyl executed, SC. Creating af a fraudulent account that send invoices to customer: 2Risk Sc, No KYC: a new id could be used without check that the company behind the id exists (but this is an Peppol desin feature, not an implementation feature, as such, BeFresh cannot be hold repsonsible (even if such fraudulent id are generated via his SaaS. Impact is similar as in cas of error, may included higher coat which are coverde by professionnal responsibility insurance, i.e. resudual impact as for I3. |
| I3-AccidManip    | 5           | p6   | 1,7        | MD      | Cost of correct and new release: 2kx; Volume 500 invoiced by day; error will be detected after typically 5 days, and manuel correction is rouhgl 100€, i.e. correction effort: 5*5*100.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| P1-LawfFairTrans | 4,5         | p4   | 0,4        | MD      |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| P2-PurpLimit     | 4,5         | p4   | 0,4        | MD      |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| P3-DataMin       | 4,5         | p4   | 0,4        | MD      |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| P4-Accuracy      | 4,5         | p4   | 0,4        | MD      |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| P6-Identif       | 4,5         | 0    | 0          | MD      | No hiding of PII                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| P7-Non-repud     | 4,5         | p4   | 0,4        | MD      |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |

Table 19: Risk estimation for the asset SaaS

VM-Webhosting

Total ALE due to the risk for the asset	16,7 k€



| Scenarios       | Fin. (k€)   | P.   | ALE (k€)   | Owner   | Comment                                                                                                                                                    |
|-----------------|-------------|------|------------|---------|------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Ap-PermLoss     | 20          | p4   | 2,0        | MD      |                                                                                                                                                            |
| At-TmpUnavail   | 4,5         | p6   | 1,5        | MD      |                                                                                                                                                            |
| C1-PartExtTheft | 50          | p3   | 2,9        | MD      | Highest likelyhood of all VM ( no doman testing for access but secured by Deep, attack could by based on erronous config but still needs additional acces. |
| C3-AccidDiscl   | 50          | p4   | 5,0        | MD      | Impact as fir C1, but a bit more likely                                                                                                                    |
| I1-ExtManip     | 50          | p3   | 2,9        | MD      | Higher damage that C1, but less likely as more difficult to achieve                                                                                        |
| I3-AccidManip   | 25          | p4   | 2,5        | MD      | Slighly likelier than I1 attack with lower impact                                                                                                          |

Table 20: Risk estimation for the asset VM-Webhosting

SW-Dev

Total ALE due to the risk for the asset	15,7 k€



| Scenarios        | Fin. (k€)   | P.   | ALE (k€)   | Owner   | Comment                                                                                                                  |
|------------------|-------------|------|------------|---------|--------------------------------------------------------------------------------------------------------------------------|
| Ap-PermLoss      | 250         | p1   | 4,5        | MD      |                                                                                                                          |
| At-TmpUnavail    | 10          | p2   | 0,3        | MD      |                                                                                                                          |
| C1-PartExtTheft  | 15          | p2   | 0,5        | MD      | Could be used to create a fishing attack, but ib generally SW can be publically known. Inpact. Urgent need to bug fixes. |
| C3-AccidDiscl    | 15          | 0    | 0          | MD      |                                                                                                                          |
| I1-ExtManip      | 70          | p3   | 4,0        | MD      | Big impact if SW is manupulated.                                                                                         |
| I3-AccidManip    | 50          | p4   | 5,0        | MD      | Slighly likelier than I1 attack with lower impact                                                                        |
| P1-LawfFairTrans | 4,5         | p3   | 0,3        | MD      |                                                                                                                          |
| P2-PurpLimit     | 4,5         | p3   | 0,3        | MD      |                                                                                                                          |
| P3-DataMin       | 4,5         | p3   | 0,3        | MD      |                                                                                                                          |
| P4-Accuracy      | 4,5         | p3   | 0,3        | MD      |                                                                                                                          |
| P6-Identif       | 4,5         | 0    | 0          | MD      | No hiding of PII                                                                                                         |
| P7-Non-repud     | 4,5         | p3   | 0,3        | MD      |                                                                                                                          |

Table 21: Risk estimation for the asset SW-Dev

BeInvoice

Total ALE due to the risk for the asset	11,8 k€



| Scenarios     |   Fin. (k€) | P.   | ALE (k€)   | Owner   | Comment                                                                                                                                                              |
|---------------|-------------|------|------------|---------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Ap-PermLoss   |         200 | 0    | 4,0        | MD      |                                                                                                                                                                      |
| At-TmpUnavail |          10 | p5   | 1,8        | MD      | Available on several environment and GitHub, effect will only be a delay in operations.                                                                              |
| I1-ExtManip   |          50 | 0    | 1,0        | MD      | Limited packags are in use over which supply chain attack could be perfoermed, test avoid this t o take effect, so that the impact is reduced to investagation time. |
| I3-AccidManip |          50 | p4   | 5,0        | MD      | Can generally be fixed, creatings outage time.                                                                                                                       |
| P6-Identif    |           0 | 0    | 0          | MD      | No hiding of PII                                                                                                                                                     |
| P7-Non-repud  |           0 | 0    | 0          | MD      | No such scenario, only integrity risk covered by I*.                                                                                                                 |

Table 22: Risk estimation for the asset BeInvoice

VM-SaaS-Editpress

Total ALE due to the risk for the asset	10,8 k€



| Scenarios       | Fin. (k€)   | P.   | ALE (k€)   | Owner   | Comment                                           |
|-----------------|-------------|------|------------|---------|---------------------------------------------------|
| Ap-PermLoss     | 5           | p4   | 0,5        | MD      |                                                   |
| At-TmpUnavail   | 4,5         | p6   | 1,5        | MD      |                                                   |
| C1-PartExtTheft | 25          | p4   | 2,5        | MD      |                                                   |
| C3-AccidDiscl   | 25          | p5   | 4,5        | MD      | Impact as fir C1, but a bit more likely           |
| I1-ExtManip     | 10          | p4   | 1,0        | MD      | Financial data could be changed                   |
| I3-AccidManip   | 4,5         | p5   | 0,8        | MD      | Slighly likelier than I1 attack with lower impact |

Table 23: Risk estimation for the asset VM-SaaS-Editpress

VM-SaaSContainers

Total ALE due to the risk for the asset	8,1 k€



| Scenarios       | Fin. (k€)   | P.   | ALE (k€)   | Owner   | Comment                                           |
|-----------------|-------------|------|------------|---------|---------------------------------------------------|
| Ap-PermLoss     | 5           | p4   | 0,5        | MD      |                                                   |
| At-TmpUnavail   | 4,5         | p6   | 1,5        | MD      |                                                   |
| C1-PartExtTheft | 10          | p4   | 1,0        | MD      | Technical info, no customer data                  |
| C3-AccidDiscl   | 10          | p5   | 1,8        | MD      | Impact as fir C1, but a bit more likely           |
| I1-ExtManip     | 15          | p4   | 1,5        | MD      |                                                   |
| I3-AccidManip   | 10          | p5   | 1,8        | MD      | Slighly likelier than I1 attack with lower impact |

Table 24: Risk estimation for the asset VM-SaaSContainers

VM-SMP-Peppol

Total ALE due to the risk for the asset	8,1 k€



| Scenarios       | Fin. (k€)   | P.   | ALE (k€)   | Owner   | Comment                                                                                         |
|-----------------|-------------|------|------------|---------|-------------------------------------------------------------------------------------------------|
| Ap-PermLoss     | 5           | p4   | 0,5        | MD      |                                                                                                 |
| At-TmpUnavail   | 4,5         | p6   | 1,5        | MD      |                                                                                                 |
| C1-PartExtTheft | 10          | p4   | 1,0        | MD      | Only reputationdamage as all available data are rather public.                                  |
| C3-AccidDiscl   | 10          | p5   | 1,8        | MD      | Impact as fir C1, but a bit more likely                                                         |
| I1-ExtManip     | 10          | p5   | 1,8        | MD      | In case of manipulation, invoices will be sent to the attacker, but no financial fraud possible |
| I3-AccidManip   | 4,5         | p6   | 1,5        | MD      | Slighly likelier than I1 attack with lower impact                                               |

Table 25: Risk estimation for the asset VM-SMP-Peppol

ITadmin

Total ALE due to the risk for the asset	6,7 k€



| Scenarios        | Fin. (k€)   | P.   | ALE (k€)   | Owner   | Comment                                                                                                                               |
|------------------|-------------|------|------------|---------|---------------------------------------------------------------------------------------------------------------------------------------|
| Ap-PermLoss      | 5           | p5   | 0,9        | MD      |                                                                                                                                       |
| At-TmpUnavail    | 4,5         | p6   | 1,5        | MD      |                                                                                                                                       |
| I1-ExtManip      | 25          | p2   | 0,8        | MD      |                                                                                                                                       |
| I3-AccidManip    | 10          | p3   | 0,6        | MD      | Slighly likelier than I1 attack with lower impact                                                                                     |
| P1-LawfFairTrans | 10          | p3   | 0,6        | MD      | Missing transparence for (1) staff member, i.e. limited likelyhood and impact (bad reputation of staff if their errors are published) |
| P2-PurpLimit     | 10          | p3   | 0,6        | MD      | Incomplete doc of processing.                                                                                                         |
| P3-DataMin       | 4,5         | p4   | 0,4        | MD      | Too much logging for staff and client's staff activities.                                                                             |
| P4-Accuracy      | 4,5         | p4   | 0,4        | MD      |                                                                                                                                       |
| P6-Identif       | 4,5         | 0    | 0          | MD      | No hiding of PII                                                                                                                      |
| P7-Non-repud     | 4,5         | p4   | 0,4        | MD      |                                                                                                                                       |
| P9-Unaware       | 4,5         | p4   | 0,4        | MD      |                                                                                                                                       |

Table 26: Risk estimation for the asset ITadmin

Deep

Total ALE due to the risk for the asset	5,3 k€



| Scenarios        |   Fin. (k€) | P.   | ALE (k€)   | Owner   | Comment                     |
|------------------|-------------|------|------------|---------|-----------------------------|
| Ap-PermLoss      |          60 | p3   | 3,4        | MD      |                             |
| At-TmpUnavail    |          10 | p5   | 1,8        | MD      |                             |
| C1-PartExtTheft  |           0 | 0    | 0          | MD      | Covered by technical assets |
| C3-AccidDiscl    |           0 | 0    | 0          | MD      | Covered by technical assets |
| I1-ExtManip      |           0 | 0    | 0          | MD      | Covered by technical assets |
| I3-AccidManip    |           0 | 0    | 0          | MD      | Covered by technical assets |
| P1-LawfFairTrans |           0 | 0    | 0          | MD      | Accoutability at Deep       |
| P2-PurpLimit     |           0 | 0    | 0          | MD      | Accoutability at Deep       |
| P3-DataMin       |           0 | 0    | 0          | MD      | Accoutability at Deep       |
| P4-Accuracy      |           0 | 0    | 0          | MD      | Accoutability at Deep       |
| P5-StorageLim    |           0 | 0    | 0          | MD      | Accoutability at Deep       |
| P6-Identif       |           0 | 0    | 0          | MD      | Accoutability at Deep       |
| P7-Non-repud     |           0 | 0    | 0          | MD      | Accoutability at Deep       |
| P9-Unaware       |           0 | 0    | 0          | MD      | Accoutability at Deep       |

Table 27: Risk estimation for the asset Deep

SE\_Dev

Total ALE due to the risk for the asset	3,2 k€



| Scenarios        | Fin. (k€)   | P.   | ALE (k€)   | Owner   | Comment              |
|------------------|-------------|------|------------|---------|----------------------|
| Ap-PermLoss      | 1           | p5   | 0,2        | MD      |                      |
| At-TmpUnavail    | 4,5         | p6   | 1,5        | MD      |                      |
| I1-ExtManip      | 0           | 0    | 0          | MD      | cf. technical assets |
| I3-AccidManip    | 0           | 0    | 0          | MD      | cf. technical assets |
| P1-LawfFairTrans | 4,5         | p3   | 0,3        | MD      |                      |
| P2-PurpLimit     | 4,5         | p3   | 0,3        | MD      |                      |
| P3-DataMin       | 4,5         | p3   | 0,3        | MD      |                      |
| P4-Accuracy      | 4,5         | p3   | 0,3        | MD      |                      |
| P6-Identif       | 4,5         | 0    | 0          | MD      | No hiding of PII     |
| P7-Non-repud     | 4,5         | p3   | 0,3        | MD      |                      |
| P9-Unaware       | 4,5         | p3   | 0,3        | MD      |                      |

Table 28: Risk estimation for the asset SE\_Dev

Phones

Total ALE due to the risk for the asset	2 k€



| Scenarios     | Fin. (k€)   | P.   | ALE (k€)   | Owner   | Comment   |
|---------------|-------------|------|------------|---------|-----------|
| Ap-PermLoss   | 3           | p5   | 0,5        | MD      |           |
| At-TmpUnavail | 4,5         | p6   | 1,5        | MD      |           |
| I1-ExtManip   | 0           | 0    | 0          | MD      | n.a.      |
| I3-AccidManip | 0           | 0    | 0          | MD      | n.a.      |

Table 29: Risk estimation for the asset Phones

Peppol

Total ALE due to the risk for the asset	1,7 k€



| Scenarios        | Fin. (k€)   | P.   | ALE (k€)   | Owner   | Comment                                                       |
|------------------|-------------|------|------------|---------|---------------------------------------------------------------|
| Ap-PermLoss      | 4           | p2   | 0,1        | MD      |                                                               |
| At-TmpUnavail    | 0           | 0    | 0          | MD      |                                                               |
| C1-PartExtTheft  | 0           | 0    | 0          | MD      | N                                                             |
| C3-AccidDiscl    | 0           | 0    | 0          | MD      |                                                               |
| I1-ExtManip      | 10          | p3   | 0,6        | MD      | Fraudulent info send to Peppol to withdraw compliance status. |
| I3-AccidManip    | 4,5         | p4   | 0,4        | MD      | Slighly likelier than I1 attack with lower impact             |
| P1-LawfFairTrans | 4,5         | p1   | 0,1        | MD      |                                                               |
| P2-PurpLimit     | 4,5         | p1   | 0,1        | MD      |                                                               |
| P3-DataMin       | 4,5         | p1   | 0,1        | MD      |                                                               |
| P4-Accuracy      | 4,5         | p1   | 0,1        | MD      |                                                               |
| P5-StorageLim    | 4,5         | p1   | 0,1        | MD      |                                                               |
| P6-Identif       | 4,5         | 0    | 0          | MD      | No hiding of PII                                              |
| P7-Non-repud     | 4,5         | p1   | 0,1        | MD      |                                                               |
| P9-Unaware       | 4,5         | p1   | 0,1        | MD      |                                                               |

Table 30: Risk estimation for the asset Peppol

### Évaluation des risques

By comparing this result with the risk acceptance criteria (cf. 3.3), we conclude that the risks are acceptable, but that the treatment of the risks makes it possible to reduce them further in an economically justifiable way.

There are no risks to be dealt with from the point of view of the PII principles.

## Risk treatment plan

### Summary of treatment plan

The table below gives the summary of the main characteristics of the treatment plan for each phase. The table described for each phase the following information:

The phase characteristic:

The start and end date of the phase;

The compliance level with the applied standard;

The number of to be implemented during the phase;

The number of whose implementation reached 100% regarding the applied standard at the end of the phase.

The profitability of the planned security measures:

The Annual Loss Expectancy in k€ at the end of the phase (P0 giving the current ALE);

The Risk Reduction in kilo euros (i.e. ALE before – ALE after the implementation);

The average annual cost of the phase (considering set-up cost, lifetime and yearly maintenance);

The Return on security investment (ROSI) in k€ i.e. ROSI = Risk reduction (∆ALE) - average annual cost.

The relative ROSI in %, which is the ROSI divided by the total cost of implementation.

The resources planning:

The implementation costs of the security measures (set-up cost) including:

Internal workload in person days;

External workload in person days;

Investment in kilo-euros

The total of implementation cost in kilo-euros.

The recurrent costs to be planned to maintain the security measures:

Internal maintenance workload in person days;

External maintenance workload in person days;

Recurrent investments to maintain implementation rated in kilo-euro;

The total of recurrent costs in kilo-euros;

The total cost of the phase including internal and external workload and the projected investment and maintenance costs.

Note : the average rate for a man-day for an intern is 400 € and for an extern 800 €..

l Average annual costs are different from the sum of set-up costs and recurring costs, as different lifetimes are considered for set-up costs.

The range and the efficiency of each phase are described in the following table:



| Phase characteristics                         | Start                               | Phase 1                             | Phase 2                             | Phase 3                             | Phase 4                             | Phase 5                             |
|-----------------------------------------------|-------------------------------------|-------------------------------------|-------------------------------------|-------------------------------------|-------------------------------------|-------------------------------------|
| 1 Phase duration                              | 1 Phase duration                    | 1 Phase duration                    | 1 Phase duration                    | 1 Phase duration                    | 1 Phase duration                    | 1 Phase duration                    |
| 1.1 Beginning date                            |                                     | 01/07/25                            | 01/10/25                            | 01/01/26                            | 01/07/26                            | 01/01/27                            |
| 1.2 End date                                  |                                     | 01/10/25                            | 01/01/26                            | 01/07/26                            | 01/01/27                            | 01/01/28                            |
| 2 Conformity                                  | 2 Conformity                        | 2 Conformity                        | 2 Conformity                        | 2 Conformity                        | 2 Conformity                        | 2 Conformity                        |
| 2.1 Level 27001 (%)                           | 98                                  | 98                                  | 98                                  | 100                                 | 100                                 | 100                                 |
| 2.2 Level 27002 (%)                           | 86                                  | 94                                  | 97                                  | 99                                  | 100                                 | 100                                 |
| 2.3 Non-compliant to 27001 (#)                | 1                                   | 1                                   | 1                                   | 0                                   | 0                                   | 0                                   |
| 2.4 Non-compliant to 27002 (#)                | 6                                   | 1                                   | 0                                   | 0                                   | 0                                   | 0                                   |
| 3 Evolution of implemented measures           | 3 Evolution of implemented measures | 3 Evolution of implemented measures | 3 Evolution of implemented measures | 3 Evolution of implemented measures | 3 Evolution of implemented measures | 3 Evolution of implemented measures |
| 3.1 Measures in phase (#)                     | 0                                   | 16                                  | 9                                   | 9                                   | 4                                   | 1                                   |
| 3.2 implemented after (#)                     | 79                                  | 95                                  | 104                                 | 113                                 | 117                                 | 118                                 |
| 4 Profitability                               | 4 Profitability                     | 4 Profitability                     | 4 Profitability                     | 4 Profitability                     | 4 Profitability                     | 4 Profitability                     |
| 4.1 ALE (k€/y)... at end                      | 260                                 | 234                                 | 220                                 | 209                                 | 208                                 | 208                                 |
| 4.2 Risk reduction (k€/y)                     | 0                                   | 26                                  | 14                                  | 11                                  | 1                                   | 0                                   |
| 4.3 Average yearly cost (k€/y)                | 0                                   | 6                                   | 5                                   | 2                                   | 8                                   | 1                                   |
| 4.3 ROSI (k€/y)                               | 0                                   | 21                                  | 8                                   | 9                                   | -7                                  | -1                                  |
| 4.4 Relative ROSI                             | 0                                   | 3,69                                | 1,57                                | 4,28                                | -0,87                               | -0,81                               |
| 5 Resource planning: total cost of phase (k€) | 0                                   | 24                                  | 11,6                                | 12,3                                | 10,5                                | 13,4                                |
| 5.1 Implementation costs                      | 0                                   | 24                                  | 11,4                                | 10,4                                | 8,6                                 | 3,6                                 |
| 5.1.1 Internal workload (md)                  | 0                                   | 33                                  | 18                                  | 16                                  | 17                                  | 3                                   |
| 5.1.2 External workload (md)                  | 0                                   | 13,5                                | 4                                   | 5                                   | 1                                   | 3                                   |
| 5.1.3 Investment (k€)                         | 0                                   | 0                                   | 1                                   | 0                                   | 1                                   | 0                                   |
| 5.2 Recurrent costs                           | 0                                   | 0                                   | 0,2                                 | 1,9                                 | 1,9                                 | 9,8                                 |
| 5.2.1 Internal maintenance (md)               | 0                                   | 0                                   | 0,5                                 | 1                                   | 1                                   | 2                                   |
| 5.2.2 External maintenance (md)               | 0                                   | 0                                   | 0                                   | 0                                   | 0                                   | 0                                   |
| 5.2.3 Recurrent maintenance (k€)              | 0                                   | 0                                   | 0                                   | 1,5                                 | 1,5                                 | 9                                   |

Table 31 : : Characteristics of implementation phases

### Increase of compliance rate and rentability of the phases

The following figure shows the evolution of both rentability for applied measures and compliance rate according to the implementation of security measures during the defined phases.

Figure 13 : Profitability of the treatment plan

### Detailed risk treatment plan

The following table gives a complete list of the guideline safety measures belonging to the selected standards and regulations that have not yet been implemented. This list is grouped by implementation phase and then sorted by profitability. According to ISO/IEC 27001, this list is called the risk treatment plan. It contains the following information:

Nr: a sequential number,

Norme et Réf, a reference to the standard from which the safety measure originates,

Description, a description of what remains to be done, preceded by the title of the relevant safety measure,

ALE, the residual risk after implementation of the measure (including all previous measures),

CS, the average annual cost,

ROI, the profitability of the measure,

CTI and CTE, the number of days of internal work and external consultancy, respectively, to initiate the measure,

INV, additional investment budget for the measure.

P: the number of the implementation phase.

Resp : the acronym of the name or title of the person responsible for implementing the measure.



|   Nr | Ref.       | Description                                                                                                                                               |   ALE (k€) |   ΔALE (k€) |   CS (k€) |   ROI (k€) |   IW (md) | EW (md)   |   INV (k€) |   P | I.   | Resp.   |
|------|------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|------------|-------------|-----------|------------|-----------|-----------|------------|-----|------|---------|
|    1 | 27002-6.3  | Information security awareness, education and training: Create #603B, #173, #173A.                                                                        |        251 |           9 |         0 |          8 |         1 | 1         |          0 |   1 | M    | MD      |
|    2 | 27002-5.34 | Privacy and protection of PII: Create #2R and privacy notices.                                                                                            |        248 |           3 |         0 |          3 |         1 | 2         |          0 |   1 | M    | MD      |
|    3 | 27002-6.6  | Confidentiality or non-disclosure agreements﻿﻿: Create #606E.                                                                                             |        246 |           2 |         0 |          2 |         0 | 0,5       |          0 |   1 | M    | MD      |
|    4 | 27002-5.18 | Access rights: Create access right process #518.                                                                                                          |        244 |           2 |         0 |          2 |         2 | 1         |          0 |   1 | M    | MD      |
|    5 | 27002-5.20 | Addressing information security within supplier agreements: Create list of processing agreements (#520) and assess the status of security implementation. |        242 |           1 |         0 |          1 |         1 | 1         |          0 |   1 | M    | MD      |
|    6 | 27002-5.24 | Information security incident management planning and preparation: Make Security event team meeting and analyse previous events.                          |        241 |           1 |         0 |          1 |         1 | 1         |          0 |   1 | M    | MD      |
|    7 | 27002-8.8  | Management of technical vulnerabilities: Create #819.                                                                                                     |        240 |           1 |         0 |          1 |         1 | 1         |          0 |   1 | M    | MD      |
|    8 | 27002-7.8  | Equipment siting and protection: Add sites to inventory.                                                                                                  |        239 |           1 |         0 |          1 |         1 | 0         |          0 |   1 | M    | MD      |
|    9 | 27002-5.2  | Information security roles and responsibilities: Create an OrgChart #502O.                                                                                |        238 |           1 |         0 |          1 |         1 | 0         |          0 |   1 | M    | MD      |
|   10 | 27002-6.8  | Information security event reporting: Inform staff on what is a security event and how to report it.                                                      |        238 |           1 |         0 |          0 |         1 | 0         |          0 |   1 | M    | MD      |
|   11 | 27002-5.35 | Independent review of information security: Perform pentest on BeInvoice.                                                                                 |        236 |           2 |         1 |          0 |         2 | 3         |          0 |   1 | M    | MD      |
|   12 | 27002-5.3  | Segregation of duties: Inform POST about their role as CIO (inside their role as trusted managed service) by sending #5…                                  |        235 |           0 |         0 |          0 |         1 | 0         |          0 |   1 | M    | MD      |
|   13 | 27002-5.9  | Inventory of information and other associated assets: Finalize inventory and add lifecycle field to #509.                                                 |        235 |           0 |         0 |          0 |         3 | 0         |          0 |   1 | M    | MD      |
|   14 | 27002-8.27 | Secure system architecture and engineering principles: Review BeInvoice with criteria of OWASP-CODEREVIEW.                                                |        235 |           1 |         0 |          0 |         5 | 0         |          0 |   1 | M    | MD      |
|   15 | 27002-5.31 | Legal, statutory, regulatory and contractual requirements: Consider requirements of EU regulations, such as CRA…                                          |        234 |           0 |         0 |          0 |         2 | 0         |          0 |   1 | M    | MD      |
|   16 | 27002-8.28 | Secure coding: Implement a SSDLC 828\_PRO.                                                                                                                 |        234 |           1 |         1 |         -1 |        10 | 3         |          0 |   1 | M    | MD      |
|   17 | 27002-5.8  | Information security in project management: Get coaching by ITR; then create implementation guide including CRA preparation.                              |        227 |           6 |         1 |          6 |         5 | 2         |          0 |   2 | M    | MD      |
|   18 | 27002-5.19 | Information security in supplier relationships: Create a list of suppliers and list of partners (#517P) documenting the security implementation.          |        226 |           1 |         0 |          1 |         1 | 0         |          0 |   2 | M    | MD      |
|   19 | 27002-8.13 | Information backup: Create backup process #813 for internal manual backup.                                                                                |        224 |           2 |         0 |          1 |         3 | 1         |          0 |   2 | M    | MD      |
|   20 | 27002-7.11 | Supporting utilities: Install a remote safe (home of MD) and store their backup tapes).                                                                   |        223 |           1 |         0 |          1 |         1 | 0         |          1 |   2 | M    | MD      |
|   21 | 27002-8.10 | Information deletion: Proceed to review data and delete what is no longer needed.                                                                         |        223 |           1 |         0 |          0 |         2 | 0         |          0 |   2 | M    | MD      |
|   22 | 27002-5.6  | Contact with special interest groups: Add GitHub monitoring to #505 and similar follow-up groups.                                                         |        222 |           0 |         0 |          0 |         1 | 0         |          0 |   2 | M    | MD      |
|   23 | 27002-5.23 | Information security for use of cloud services: Perform asset qualification of cloud service users.                                                       |        222 |           0 |         0 |          0 |         2 | 0         |          0 |   2 | M    | MD      |
|   24 | 27002-8.24 | Use of cryptography: Document SSL certificates in #824K.                                                                                                  |        222 |           0 |         0 |         -0 |         2 | 0         |          0 |   2 | M    | MD      |
|   25 | 27002-8.31 | Separation of development, test and production environments: Crete identical acceptation environment in the Cloud.                                        |        220 |           2 |         3 |         -1 |         1 | 1         |          0 |   2 | M    | MD      |
|   26 | 27002-7.2  | Physical entry: Create key inventory #702K.                                                                                                               |        218 |           2 |         0 |          2 |         1 | 0         |          0 |   3 | M    | MD      |
|   27 | 27002-7.1  | Physical security perimeters: Create procedure for handling removable storage #710.                                                                       |        216 |           2 |         0 |          2 |         3 | 0         |          0 |   3 | M    | MD      |
|   28 | 27002-5.30 | ICT readiness for business continuity: Implement ISO 27031 once the 2025 version is available.                                                            |        215 |           2 |         0 |          1 |         2 | 1         |          0 |   3 | M    | MD      |
|   29 | 27002-5.14 | Information transfer: Create #514 exchange procedure.                                                                                                     |        213 |           2 |         0 |          1 |         1 | 1         |          0 |   3 | L    | MD      |
|   30 | 27001-8.3  | Information security risk treatment: Migrate opne risk treatement tickets to JIRA.                                                                        |        212 |           1 |         0 |          1 |         1 | 1         |          0 |   3 | M    | MD      |
|   31 | 27002-7.14 | Secure disposal or re-use of equipment: Dispose old hard disk after the migration.                                                                        |        211 |           1 |         0 |          1 |         1 | 0         |          0 |   3 | M    | MD      |
|   32 | 27002-5.13 | Labelling of information: Extend labelling to most project documented.                                                                                    |        210 |           1 |         0 |          0 |         2 | 0         |          0 |   3 | M    | MD      |
|   33 | 27002-7.10 | Storage media: Dispose local equipment once the migration to Deep was performed.                                                                          |        210 |           0 |         0 |          0 |         2 | 0         |          0 |   3 | M    | MD      |
|   34 | 27002-8.15 | Logging: Transfer logs to a dedicated tool such as WAZUH, Elasic search…                                                                                  |        209 |           1 |         1 |          0 |         3 | 2         |          0 |   3 | M    | MD      |
|   35 | 27002-5.17 | Authentication information: Create a password management procedure/instruction.                                                                           |        209 |           0 |         0 |         -0 |         1 | 1         |          0 |   4 | M    | MD      |
|   36 | 27002-8.4  | Access to source code: Install GitLab for internal source code.                                                                                           |        209 |           0 |         0 |         -0 |         5 | 0         |          0 |   4 | M    | MD      |
|   37 | 27002-8.12 | Data leakage prevention: Install DLP tool.                                                                                                                |        209 |           0 |         1 |         -1 |        10 | 0         |          0 |   4 | M    | MD      |
|   38 | 27002-5.15 | Access control: Create a second line of firewall.                                                                                                         |        208 |           1 |         6 |         -6 |         1 | 0         |          1 |   4 | M    | MD      |
|   39 | 27002-5.21 | Managing information security in the ICT supply chain: Review need for applied in ISO 20000 (ITIL), 27017, 27018 (Cloud security)                         |        208 |           0 |         1 |         -1 |         3 | 3         |          0 |   5 | M    | MD      |

## Other related risk management processes

### Risk acceptance

This phase consists of accepting the residual risks and ensuring the responsibility that the current risk is reduced to the residual risk in an accepted way. This decision thus includes the acceptance of the risk treatment plan, which means the agreement on needed resources and the commission of the work to ensure that the plan can be implemented as planned.

The decision shall be formally documented.

The decision is to be formally documented by the signature of this report^, based on this observation:

According to the risk acceptance criteria, the turnover is 31 Mio (in 2021), and the profit 2.9 Mio, the ALE has been estimated at 868. In addition, measures have been planned to reduce the annual loss to €585. This level is well below 2% of turnover (32 Mio in 2021), so the risk acceptance criteria have been met.

### Risk communication

The underlying report or parts of it are used to exchange risk-related information. The risk communication strategy is not part of the present report.

### Risk monitoring and review

This process is not part of the underlying report. Risk monitoring and review consists of updating this report annually or in case of significant changes and identification of important risks.

## Evaluations des risques selon la méthode de l’ILR



| Risk ID   | Asset   | id   |    | C   | I   | A   | Label   | Pr   | Threat   | Vuln. lab   | Qualif   | Cc   | Ic   | Ac   | Max   | Treat   | Act   | Res-V   | Res -R   |
|-----------|---------|------|----|-----|-----|-----|---------|------|----------|-------------|----------|------|------|------|-------|---------|-------|---------|----------|
|           |         |      |    |     |     |     |         |      |          |             |          |      |      |      |       |         |       |         |          |

See #161TRE or Serima export.

## Annex :

The following tables include, for each security measure, its current implementation rate and the workload to invest to fully implement the security measures. The implementation rate and the costs of the security measures which are not yet fully implemented were estimated.

For each security measure, we indicate:

Ref, the reference of security control;

Domains, the area (and title);

ST, the status (AP = applicable, NA not applicable, M: mandatory);

IR, the rate of implementation (indicating what percentage of the measure is already operational);

IW, the internal set up workload, showing how many days of internally work are necessary to implement the security measure;

EW, the external set-up showing how many days of work of a service provider is needed to implement the security measure;

INV, the investment budget in k€ indicating what is expected in addition to internal and external resources to implement the measure;

LT, the lifetime in years of the measure (if the value is zero, the tool defaults to 5 years);

IM, the yearly internal workload to maintain the security control;

EM, the yearly external workload to maintain the security control;

RINV, the recurrent investments for maintaining the security control;

CS, the annual cost in k€, calculated from the previous settings (considering the average cost of one internal person day (400 €) and of one external person day (800 €,, this rate includes coordination with internal resources);

Comment, a justification of the provided estimates;

To do, a description of the actions to be done to achieve full compliance;

Resp, acroym of name or title of the person(s) responsible for the implementation of the security measure.

27001



| Ref.   | Security measure                                               | ST                                         | IR %                                       | IW md                                      | EW md                                      | INV k€                                     | LT y                                       | IM md                                      | EM md                                      | RM k€                                      | CS k€                                      | P                                          | I.                                         | Resp.                                      | To Do                                          | Comment                                                                             |
|--------|----------------------------------------------------------------|--------------------------------------------|--------------------------------------------|--------------------------------------------|--------------------------------------------|--------------------------------------------|--------------------------------------------|--------------------------------------------|--------------------------------------------|--------------------------------------------|--------------------------------------------|--------------------------------------------|--------------------------------------------|--------------------------------------------|------------------------------------------------|-------------------------------------------------------------------------------------|
| 4      | Context of the organization                                    | Context of the organization                | Context of the organization                | Context of the organization                | Context of the organization                | Context of the organization                | Context of the organization                | Context of the organization                | Context of the organization                | Context of the organization                | Context of the organization                | Context of the organization                | Context of the organization                | Context of the organization                |                                                |                                                                                     |
| 4.1    | Understanding the organization and its context                 | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #1                                                                              |
| 4.2    | Understanding the needs and expectations of interested parties | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #1                                                                              |
| 4.3    | Determining the scope of the ISMS                              | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #1                                                                              |
| 4.4    | Establish, implement, maintain and continually improve ISMS    | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #1                                                                              |
| 5      | Leadership                                                     | Leadership                                 | Leadership                                 | Leadership                                 | Leadership                                 | Leadership                                 | Leadership                                 | Leadership                                 | Leadership                                 | Leadership                                 | Leadership                                 | Leadership                                 | Leadership                                 | Leadership                                 |                                                | See #1                                                                              |
| 5.1    | Leadership and commitment                                      | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #1                                                                              |
| 5.2    | Policy                                                         | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #1                                                                              |
| 5.3    | Organizational roles, responsibilities and authorities         | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #1                                                                              |
| 6      | Planning                                                       | Planning                                   | Planning                                   | Planning                                   | Planning                                   | Planning                                   | Planning                                   | Planning                                   | Planning                                   | Planning                                   | Planning                                   | Planning                                   | Planning                                   | Planning                                   |                                                |                                                                                     |
| 6.1    | Actions to address risks and opportunities                     | Actions to address risks and opportunities | Actions to address risks and opportunities | Actions to address risks and opportunities | Actions to address risks and opportunities | Actions to address risks and opportunities | Actions to address risks and opportunities | Actions to address risks and opportunities | Actions to address risks and opportunities | Actions to address risks and opportunities | Actions to address risks and opportunities | Actions to address risks and opportunities | Actions to address risks and opportunities | Actions to address risks and opportunities |                                                | See #161                                                                            |
| 6.1.1  | General                                                        | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #161                                                                            |
| 6.1.2  | Information security risk assessment                           | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #161                                                                            |
| 6.1.3  | Information security risk treatment                            | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #161                                                                            |
| 6.2    | Information security objectives and plans to achieve them      | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #161                                                                            |
| 7      | Support                                                        | Support                                    | Support                                    | Support                                    | Support                                    | Support                                    | Support                                    | Support                                    | Support                                    | Support                                    | Support                                    | Support                                    | Support                                    | Support                                    |                                                |                                                                                     |
| 7.1    | Resources                                                      | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #1                                                                              |
| 7.2    | Competence                                                     | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #1                                                                              |
| 7.3    | Awareness                                                      | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #1                                                                              |
| 7.4    | Communication                                                  | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #1                                                                              |
| 7.5    | Documented information                                         | Documented information                     | Documented information                     | Documented information                     | Documented information                     | Documented information                     | Documented information                     | Documented information                     | Documented information                     | Documented information                     | Documented information                     | Documented information                     | Documented information                     | Documented information                     |                                                | See #175                                                                            |
| 7.5.1  | General                                                        | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #1                                                                              |
| 7.5.2  | Creating and updating                                          | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #1                                                                              |
| 7.5.3  | Control of documented information                              | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #1                                                                              |
| 8      | Operation                                                      | Operation                                  | Operation                                  | Operation                                  | Operation                                  | Operation                                  | Operation                                  | Operation                                  | Operation                                  | Operation                                  | Operation                                  | Operation                                  | Operation                                  | Operation                                  |                                                |                                                                                     |
| 8.1    | Operational planning and control                               | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | cf. #16R                                                                            |
| 8.2    | Information security risk assessment                           | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | cf. #16R                                                                            |
| 8.3    | Information security risk treatment                            | AP                                         | 40                                         | 1                                          | 1                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 3                                          | M                                          | MD                                         | Migrate opne risk treatement tickets to JIRA.  | in 2025, followup will be made in xls; migration to JIRA planned for the next year. |
| 9      | Performance evaluation                                         | Performance evaluation                     | Performance evaluation                     | Performance evaluation                     | Performance evaluation                     | Performance evaluation                     | Performance evaluation                     | Performance evaluation                     | Performance evaluation                     | Performance evaluation                     | Performance evaluation                     | Performance evaluation                     | Performance evaluation                     | Performance evaluation                     |                                                |                                                                                     |
| 9.1    | Monitoring, measurement, analysis and evaluation               | AP                                         | 100                                        | 1                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         | Analyse KPI, in particulear reporting by POST. |                                                                                     |
| 9.2    | Internal audit                                                 | AP                                         | 100                                        | 1                                          | 2                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         | Perform independent review of InfoSec.         |                                                                                     |
| 9.3    | Management review                                              | AP                                         | 100                                        | 1                                          | 1                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         | Organize mgt review at latest on 27 juin.      |                                                                                     |
| 10     | Improvement                                                    | Improvement                                | Improvement                                | Improvement                                | Improvement                                | Improvement                                | Improvement                                | Improvement                                | Improvement                                | Improvement                                | Improvement                                | Improvement                                | Improvement                                | Improvement                                |                                                |                                                                                     |
| 10.1   | Nonconformity and corrective action                            | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #1                                                                              |
| 10.2   | Continual improvement                                          | AP                                         | 100                                        | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 0                                          | 1                                          | M                                          | MD                                         |                                                | See #1 Currentl suggestion are introduced by email to the MD (or by a ticket).      |

27002



|   Ref. | Security measure                                                       | ST                      | IR %                    | IW md                   | EW md                   | INV k€                  | LT y                    | IM md                   | EM md                   | RM k€                   | CS k€                   | P                       | I.                      | Resp.                   | To Do                                                                                             | Comment                                                                                                                                                                                                                                                                                            |
|--------|------------------------------------------------------------------------|-------------------------|-------------------------|-------------------------|-------------------------|-------------------------|-------------------------|-------------------------|-------------------------|-------------------------|-------------------------|-------------------------|-------------------------|-------------------------|---------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|   5    | Organizational controls                                                | Organizational controls | Organizational controls | Organizational controls | Organizational controls | Organizational controls | Organizational controls | Organizational controls | Organizational controls | Organizational controls | Organizational controls | Organizational controls | Organizational controls | Organizational controls |                                                                                                   |                                                                                                                                                                                                                                                                                                    |
|   5.1  | Policies for information security                                      | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | #0 signed and distributed, responsibilities defined in #0D                                                                                                                                                                                                                                         |
|   5.2  | Information security roles and responsibilities                        | AP                      | 90                      | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      | Create an OrgChart #502O.                                                                         | No DPO is needed at this stage.                                                                                                                                                                                                                                                                    |
|   5.3  | Segregation of duties                                                  | AP                      | 90                      | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      | Inform POST about their role as CIO (inside their role as trusted managed service) by sending #5… | POST acts as CIO. CISO and Audit role segregated to ITR.                                                                                                                                                                                                                                           |
|   5.4  | Management responsibilities                                            | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | ISMS share with employees via share point. Writen confirmation via email on 24/6/2025.                                                                                                                                                                                                             |
|   5.5  | Contact with authorities                                               | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | #505 defined and distributed, check made by CISO on 29/4.                                                                                                                                                                                                                                          |
|   5.6  | Contact with special interest groups                                   | AP                      | 90                      | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 2                       | M                       | MD                      | Add GitHub monitoring to #505 and similar follow-up groups.                                       | idem                                                                                                                                                                                                                                                                                               |
|   5.7  | Threat intelligence                                                    | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | Main issue related to MS by POST operation under IOS 27001 certification, no other relevant threats to monitor; principles are addressed in #5.                                                                                                                                                    |
|   5.8  | Information security in project management                             | AP                      | 50                      | 5                       | 2                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | 2                       | M                       | MD                      | Get coaching by ITR; then create implementation guide including CRA preparation.                  | Applied currently to main pro; high percentage of time used for testing; test by OpenPeppol succeeded.                                                                                                                                                                                             |
|   5.9  | Inventory of information and other associated assets                   | AP                      | 20                      | 3                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      | Finalize inventory and add lifecycle field to #509.                                               |                                                                                                                                                                                                                                                                                                    |
|   5.1  | Acceptable use of information and other associated assets              | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | Cf. #5, #512, and in #509A.                                                                                                                                                                                                                                                                        |
|   5.11 | Return of assets                                                       | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | Never needed; is defined in #5.                                                                                                                                                                                                                                                                    |
|   5.12 | Classification of information                                          | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | cf.512                                                                                                                                                                                                                                                                                             |
|   5.13 | Labelling of information                                               | AP                      | 60                      | 2                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 3                       | M                       | MD                      | Extend labelling to most project documented.                                                      |                                                                                                                                                                                                                                                                                                    |
|   5.14 | Information transfer                                                   | AP                      | 70                      | 1                       | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 3                       | L                       | MD                      | Create #514 exchange procedure.                                                                   | No CO infor is exchanged over channels; Data is generally give to customers via customer's infrastructure under their responsibility. Exceptional doc are encrypted via zip and the password send in a different channel, so that #514 is not really needed.                                       |
|   5.15 | Access control                                                         | AP                      | 90                      | 1                       | 0                       | 1                       | 0                       | 0                       | 0                       | 6                       | 6                       | 4                       | M                       | MD                      | Create a second line of firewall.                                                                 | cf. #5 Stict acces control for servuer (dedicated VLAN, managed acces via Bastion, Front FW and Web load balances and WAF.                                                                                                                                                                         |
|   5.16 | Identity management                                                    | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | LDAP in use; Github and JIRA manage SSO identity via MS Azure Entra.                                                                                                                                                                                                                               |
|   5.17 | Authentication information                                             | AP                      | 90                      | 1                       | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 4                       | M                       | MD                      | Create a password management procedure/instruction.                                               | cf. above; OTP, password manager in place: 1Password.                                                                                                                                                                                                                                              |
|   5.18 | Access rights                                                          | AP                      | 40                      | 2                       | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      | Create access right process #518.                                                                 |                                                                                                                                                                                                                                                                                                    |
|   5.19 | Information security in supplier relationships                         | AP                      | 2                       | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 2                       | M                       | MD                      | Create a list of suppliers and list of partners (#517P) documenting the security implementation.  |                                                                                                                                                                                                                                                                                                    |
|   5.2  | Addressing information security within supplier agreements             | AP                      | 0                       | 1                       | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      | Create list of processing agreements (#520) and assess the status of security implementation.     |                                                                                                                                                                                                                                                                                                    |
|   5.21 | Managing information security in the ICT supply chain                  | AP                      | 80                      | 3                       | 3                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | 5                       | M                       | MD                      | Review need for applied in ISO 20000 (ITIL), 27017, 27018 (Cloud security)                        | Use of github security to get information on patching of embeded code. ITIL, 270017 and 27018 not yet applied.                                                                                                                                                                                     |
|   5.22 | Monitoring, review and change management of supplier services          | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | POST reports quarterly; these reports including KPIs are seriously reviewed by the MD. Audits are currently not needed.                                                                                                                                                                            |
|   5.23 | Information security for use of cloud services                         | AP                      | 80                      | 2                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 2                       | M                       | MD                      | Perform asset qualification of cloud service users.                                               |                                                                                                                                                                                                                                                                                                    |
|   5.24 | Information security incident management planning and preparation      | AP                      | 60                      | 1                       | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      | Make Security event team meeting and analyse previous events.                                     | #524 distributed. SET is planned for end of 2025. No incident took place until now.                                                                                                                                                                                                                |
|   5.25 | Assessment and decision on information security events                 | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | See above                                                                                                                                                                                                                                                                                          |
|   5.26 | Response to information security incidents                             | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | See above                                                                                                                                                                                                                                                                                          |
|   5.27 | Learning from information security incidents                           | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | See above                                                                                                                                                                                                                                                                                          |
|   5.28 | Collection of evidence                                                 | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | See above                                                                                                                                                                                                                                                                                          |
|   5.29 | Information security during disruption                                 | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | .                                                                                                                                                                                                                                                                                                  |
|   5.3  | ICT readiness for business continuity                                  | AP                      | 60                      | 2                       | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 3                       | M                       | MD                      | Implement ISO 27031 once the 2025 version is available.                                           |                                                                                                                                                                                                                                                                                                    |
|   5.31 | Legal, statutory, regulatory and contractual requirements              | AP                      | 80                      | 2                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      | Consider requirements of EU regulations, such as CRA…                                             | Multiples LU layx have been collect in O:\BeFresh\ISMS\5\_BeFresh-OrgControls\531\_BeFresh-LegalReq\531A\_LU-Lois and were considered when setting up policies.                                                                                                                                       |
|   5.32 | Intellectual property rights                                           | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | Jetbrain (IDE de Devel); github, Microsoft... All SW are listed in the Jira-Wiki.                                                                                                                                                                                                                  |
|   5.33 | Protection of records                                                  | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | There is a 10y email archive. ISMS record are on O: and additionally backuped. by ITR.                                                                                                                                                                                                             |
|   5.34 | Privacy and protection of PII                                          | AP                      | 20                      | 1                       | 2                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      | Create #2R and privacy notices.                                                                   | Create #2R and privacy notices.                                                                                                                                                                                                                                                                    |
|   5.35 | Independent review of information security                             | AP                      | 60                      | 2                       | 3                       | 0                       | 0                       | 2                       | 0                       | 0                       | 1                       | 1                       | M                       | MD                      | Perform pentest on BeInvoice.                                                                     | POST makes reviews incl. vulnerabilty scan (yearly) by themselves.                                                                                                                                                                                                                                 |
|   5.36 | Compliance with policies, rules and standards for information security | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | CC of Pol #5... done withing the risk assessment.                                                                                                                                                                                                                                                  |
|   5.37 | Documented operating procedures                                        | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | cf 382: Change mgt procedure exist; other are planned in preceding task. ackup mgt to be create (cf. 813).                                                                                                                                                                                         |
|   6    | People controls                                                        | People controls         | People controls         | People controls         | People controls         | People controls         | People controls         | People controls         | People controls         | People controls         | People controls         | People controls         | People controls         | People controls         |                                                                                                   |                                                                                                                                                                                                                                                                                                    |
|   6.1  | Screening                                                              | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | cf. #6                                                                                                                                                                                                                                                                                             |
|   6.2  | Terms and conditions of employment                                     | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | NDA including in work contract.                                                                                                                                                                                                                                                                    |
|   6.3  | Information security awareness, education and training                 | AP                      | 0                       | 1                       | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      | Create #603B, #173, #173A.                                                                        | Create an awareness program and make a 2h training for MWE.                                                                                                                                                                                                                                        |
|   6.4  | Disciplinary process                                                   | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | cf. #6                                                                                                                                                                                                                                                                                             |
|   6.5  | Responsibilities after termination or change of employment             | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | cf. #6                                                                                                                                                                                                                                                                                             |
|   6.6  | Confidentiality or non-disclosure agreements﻿﻿                         | AP                      | 80                      | 0                       | 0,5                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      | Create #606E.                                                                                     | The confidentiality is generally included in our general terms and conditions as well as contracts. Freelancers also have it included in their contracts.                                                                                                                                          |
|   6.7  | Remote working                                                         | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | VPN to office in place, with forced login on every connection.                                                                                                                                                                                                                                     |
|   6.8  | Information security event reporting                                   | AP                      | 90                      | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      | Inform staff on what is a security event and how to report it.                                    | JIRA Project in place.                                                                                                                                                                                                                                                                             |
|   7    | Physical controls                                                      | Physical controls       | Physical controls       | Physical controls       | Physical controls       | Physical controls       | Physical controls       | Physical controls       | Physical controls       | Physical controls       | Physical controls       | Physical controls       | Physical controls       | Physical controls       |                                                                                                   |                                                                                                                                                                                                                                                                                                    |
|   7.1  | Physical security perimeters                                           | AP                      | 70                      | 3                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 3                       | M                       | MD                      | Create procedure for handling removable storage #710.                                             | office building protected with card access, cctv, all critical information at DEEP                                                                                                                                                                                                                 |
|   7.2  | Physical entry                                                         | AP                      | 80                      | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 3                       | M                       | MD                      | Create key inventory #702K.                                                                       | Alarm in place, receptionist in place in entrance without badge, forced to give a name. No key management inventory needed as acces handled by batch (and handlles by subcontractor Schroeder&amp;Ass.)                                                                                                |
|   7.3  | Securing offices, rooms and facilities                                 | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | Rooms are secured according to the policy of the main customer who is the owner of the building.                                                                                                                                                                                                   |
|   7.4  | Physical security monitoring                                           | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | CCTV around the whole building, tracking of where a badge is used by building owner, alarm systems in place.                                                                                                                                                                                       |
|   7.5  | Protecting against physical and environmental threats                  | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | not in flooding area, fire detection in place                                                                                                                                                                                                                                                      |
|   7.6  | Working in secure areas                                                | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | outsourced to DEEP                                                                                                                                                                                                                                                                                 |
|   7.7  | Clear desk and clear screen                                            | AP                      | 100                     | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      | Create key handing procedure #702.                                                                | Lock screen in place, locked cupboard for confidential material: the key I hold by the company owner, so tha no handling procedure is currently needed.                                                                                                                                            |
|   7.8  | Equipment siting and protection                                        | AP                      | 80                      | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      | Add sites to inventory.                                                                           | Material not next to windows                                                                                                                                                                                                                                                                       |
|   7.9  | Security of assets off-premises                                        | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | Encrypted hard drives, not left unattended. See 7.2. for further actions.                                                                                                                                                                                                                          |
|   7.1  | Storage media                                                          | AP                      | 90                      | 2                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 3                       | M                       | MD                      | Dispose local equipment once the migration to Deep was performed.                                 | Migration to DEEP ongoing.                                                                                                                                                                                                                                                                         |
|   7.11 | Supporting utilities                                                   | AP                      | 90                      | 1                       | 0                       | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 2                       | M                       | MD                      | Install a remote safe (home of MD) and store their backup tapes).                                 | UPS in place, or outsourced to 2 Tier IV datacenters                                                                                                                                                                                                                                               |
|   7.12 | Cabling security                                                       | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | power lines underground                                                                                                                                                                                                                                                                            |
|   7.13 | Equipment maintenance                                                  | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | all updates are installed, servers are managed by DEEP (for data centre) or Schroeder (for facilities)                                                                                                                                                                                             |
|   7.14 | Secure disposal or re-use of equipment                                 | AP                      | 90                      | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 3                       | M                       | MD                      | Dispose old hard disk after the migration.                                                        | not needed until now                                                                                                                                                                                                                                                                               |
|   8    | Technological controls                                                 | Technological controls  | Technological controls  | Technological controls  | Technological controls  | Technological controls  | Technological controls  | Technological controls  | Technological controls  | Technological controls  | Technological controls  | Technological controls  | Technological controls  | Technological controls  |                                                                                                   |                                                                                                                                                                                                                                                                                                    |
|   8.1  | User endpoint devices                                                  | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | User aware on computer security, unattended equipment is locked during lunch break.                                                                                                                                                                                                                |
|   8.2  | Privileged access rights                                               | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | Servers in Trusted Managed Cloud by DEEP, BF does not have privileged access). Staff is admin on their laptop, both being trained ICT admin.                                                                                                                                                       |
|   8.3  | Information access restriction                                         | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | This is very relevant for SaaS: Access profiles by system in central LDAP or Microsoft Entra. Acces requests logged in the ticketing system.                                                                                                                                                       |
|   8.4  | Access to source code                                                  | AP                      | 90                      | 5                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 4                       | M                       | MD                      | Install GitLab for internal source code.                                                          | Github Enterprise logs all actions, access via SSO and Microsoft entra.                                                                                                                                                                                                                            |
|   8.5  | Secure authentication                                                  | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | MFA is activated on relevant systems.                                                                                                                                                                                                                                                              |
|   8.6  | Capacity management                                                    | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | Capacity is monitored by DEEP. MD assesses quarterly reporting, and get alert if defined quota is reached.                                                                                                                                                                                         |
|   8.7  | Protection against malware                                             | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | Proofpoint in place as Mail relay, firewalls in office, and trusted managed cloud, no direct web access in cloud infrastructure. Mac environment has integrated AV. Weproxy for Datacentre acces.                                                                                                  |
|   8.8  | Management of technical vulnerabilities                                | AP                      | 50                      | 1                       | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      | Create #819.                                                                                      | Github Security notifications on source code, newsletters on used software, DEEP installs security patches on server OS.                                                                                                                                                                           |
|   8.9  | Configuration management                                               | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | Server Infrastructure managed and documented by DEEP, developer setup defined in BeFresh WIKI.                                                                                                                                                                                                     |
|   8.1  | Information deletion                                                   | AP                      | 70                      | 2                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 2                       | M                       | MD                      | Proceed to review data and delete what is no longer needed.                                       | first ticket to do                                                                                                                                                                                                                                                                                 |
|   8.11 | Data masking                                                           | NA                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | No such requirements applicable for invoice management.                                                                                                                                                                                                                                            |
|   8.12 | Data leakage prevention                                                | AP                      | 80                      | 10                      | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | 4                       | M                       | MD                      | Install DLP tool.                                                                                 | Logging on server infrastructure via Wallix Bastion, tracking of admin actions. In SaaS, audit login on views is activated, and is used in case of investigation by customers.                                                                                                                     |
|   8.13 | Information backup                                                     | AP                      | 90                      | 3                       | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 2                       | M                       | MD                      | Create backup process #813 for internal manual backup.                                            | Cloud is backed up by DEEP, source code in GitHub + offline backup on MD laptop. An additional procedure of a manual local backup is useful.                                                                                                                                                       |
|   8.14 | Redundancy of information processing facilities                        | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | completely redundant infrastructure, in 2 Tier IV data centres with automated failover                                                                                                                                                                                                             |
|   8.15 | Logging                                                                | AP                      | 90                      | 3                       | 2                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | 3                       | M                       | MD                      | Transfer logs to a dedicated tool such as WAZUH, Elasic search…                                   | Logging in infrastructure by DEEP, internet access by POST, GitHub, jira. Audit log in SaaS DB, may by tranferred to a dedicated tool such as WAZUH, Elasic search…                                                                                                                                |
|   8.16 | Monitoring activities                                                  | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | Monitoring of infrastructure by DEEP. Additional pingdom tool in place and SMS send in case of issues detected.                                                                                                                                                                                    |
|   8.17 | Clock synchronization                                                  | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | Done in infrastructure by DEEP, laptops are connected to timeserver.                                                                                                                                                                                                                               |
|   8.18 | Use of privileged utility programs                                     | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      | local users on laptop                                                                             | Done in infrastructure by DEEP, no utility installed on server. On laptop, all users a admin and responsible to manage with all possible utility tools. No intunes or technical user that may take controls on computers.                                                                          |
|   8.19 | Installation of software on operational systems                        | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      | Create #819, cf. 8.8                                                                              | done in infrastructure by DEEP, and by MD on laptops                                                                                                                                                                                                                                               |
|   8.2  | Networks security                                                      | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      | Get network diagram (by Deep) (#820A) and review security.                                        | Cloud infrastructure segmented; LAN (connected office by POST, managed) in place; several VLAN in place.                                                                                                                                                                                           |
|   8.21 | Security of network services                                           | AP                      | 100                     | 1                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | Security is a design criteria for Deep.                                                                                                                                                                                                                                                            |
|   8.22 | Segregation of networks                                                | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | cf. 8.21                                                                                                                                                                                                                                                                                           |
|   8.23 | Web filtering                                                          | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | cf. 8.21                                                                                                                                                                                                                                                                                           |
|   8.24 | Use of cryptography                                                    | AP                      | 60                      | 2                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 2                       | M                       | MD                      | Document SSL certificates in #824K.                                                               | Luxtrust signature implemented in SaaS; Cyrp follow Peppol documentation: https://peppol.helger.com/public/menuitem-docs-peppol-pki; https in use.                                                                                                                                                 |
|   8.25 | Secure development life cycle                                          | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 3                       | M                       | MD                      | Implement a SSDLC 828\_PRO.                                                                        | Source code monitoring by gitlab in place; See 8..28 for further info                                                                                                                                                                                                                              |
|   8.26 | Application security requirements                                      | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | SaaS has been designed according to the following security policy: https://docs.peppol.eu/edelivery/policies/PEPPOL-EDN-Policy-for-Transport-Security-1.1.0-2020-04-20.pdf and this has been certified by OpenPeppol. Add to ISMS as #826P. Password policy is in place (also enforcement of MFA). |
|   8.27 | Secure system architecture and engineering principles                  | AP                      | 60                      | 5                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      | Review BeInvoice with criteria of OWASP-CODEREVIEW.                                               | Principles as described in #8.                                                                                                                                                                                                                                                                     |
|   8.28 | Secure coding                                                          | AP                      | 50                      | 10                      | 3                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | 1                       | M                       | MD                      | Implement a SSDLC 828\_PRO.                                                                        |                                                                                                                                                                                                                                                                                                    |
|   8.29 | Security testing in development and acceptance                         | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | 252 tests documented in GitHub, executed after bug corrections.                                                                                                                                                                                                                                    |
|   8.3  | Outsourced development                                                 | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | Not used until now                                                                                                                                                                                                                                                                                 |
|   8.31 | Separation of development, test and production environments            | AP                      | 80                      | 1                       | 1                       | 0                       | 0                       | 0                       | 0                       | 3                       | 3                       | 2                       | M                       | MD                      | Crete identical acceptation environment in the Cloud.                                             | Test environment on a laptop.                                                                                                                                                                                                                                                                      |
|   8.32 | Change management                                                      | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | 832\_PRO\_BeFresh-ChangMgt\_v1.0 in place since Arip, ticket numbers are referred to in the source code.                                                                                                                                                                                              |
|   8.33 | Test information                                                       | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | In case of bug reports on a prod data, test with production data are made. Example files have been generated to perform the usual acceptance tests.                                                                                                                                                |
|   8.34 | Protection of information systems during audit testing                 | AP                      | 100                     | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 0                       | 1                       | M                       | MD                      |                                                                                                   | Not yet needed, all is planned and supervised by MD.                                                                                                                                                                                                                                               |