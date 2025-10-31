<!-- image -->

## Specification



<!-- image -->



<!-- image -->



<!-- image -->



<!-- image -->

## OpenPeppol AISBL

Peppol Transport Infrastructure ICT - Models

## Peppol Policy for Transport Security

Version: 1.1.0

Status: In use

Author:

Bård Langøy, Pagero, Sweden

## Statement of originality

This deliverable contains original unpublished work except where clearly indicated otherwise. Acknowledgement of previously published material and of the work of others has been made through appropriate citation, quotation or both.

## Statement of copyright



<!-- image -->

This deliverable is released under the terms of the Creative Commons Licence accessed through the following link: http://creativecommons.org/licenses/by-nc-nd/4.0/.

You are free to:

Share -copy and redistribute the material in any medium or format.

The licensor cannot revoke these freedoms as long as you follow the license terms.



<!-- image -->

## Contributors

Bård Langøy, Pagero

Hans Berg, Tickstar

Risto Collanus, Visma

Philip Helger, Bundesrechenzentrum/OpenPeppol Operating Office

Jerry Dimitriou, OpenPeppol Operating Office

Jesper Larsen, OpenPeppol Operating Office

Erlend Klakegg Bergheim, Difi

## Version History



| Version   | Date       | Change log                                                   |
|-----------|------------|--------------------------------------------------------------|
| 1.0.0     | 2019-01-31 | Initial version                                              |
| 1.1.0     | 2020-04-20 | Made rules applicable to SMP and Directory  Updated branding |

## 1 Introduction 1



- Actors within the Peppol eDelivery Network are required to manage two different types of 2 electronic certificates: 3

4

5

6

7



- 1. TLS certificates, used on transport level to provide a standard solution for securing server authentication and message confidentiality.
- 2. OpenPeppol certificates, used on application level, to secure that only authorized and approved actors are operating within the Peppol eDelivery Network.
- The TLS Certificates are not provided by OpenPeppol and MUST be issued by third party Certificate 8 Authorities. 9
- This document covers the policies on the use of TLS certificates and TLS configurations in order to: 10

11

12



- · limit disruptions in traffic between actors
- · provide good security requirements for both current and future demands

## 1.1 Terminology 13



- The keywords "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD 14 NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as 15 described in RFC 2119 [RFC2119]. 16
- The term TLS is used through the entire document instead of SSL to highlight the fact that the TLS 17 protocol is the successor of the SSL protocol. 18



<!-- image -->

## 1.2 Normative references 19



| 20  21     | [RFC2119]   | Key words for use in RFCs to Indicate Requirement Levels,  https://www.ietf.org/rfc/rfc2119.txt                                                              |
|------------|-------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 22         | [NSS]       | Mozilla Network Security Services,                                                                                                                           |
| 23  24  25 | [CACERTS]   | https://developer.mozilla.org/en-US/docs/Mozilla/Projects/NSS  List of pre-loaded CA certificates of NSS,  https://wiki.mozilla.org/CA/Included\_Certificates |
| 26  27     | [SSL-LABS]  | SSL Labs Website performing SSL tests,  https://www.ssllabs.com/ssltest                                                                                      |

## 2 Policy for Transport Security 28

## 2.1 Approved Certificate Authorities 29

TLS Certificates are not issued by OpenPeppol and would lead to security risks and trust issues 30 between actors without any guiding policies. Trust issues have already been a problem within the 31 Peppol eDelivery Network for quite some time and to solve these issues, OpenPeppol restricts the 32



- usage of TLS Certificates as follows: 33

## POLICY 1 Approved Certificate Authorities 34

35

36

37

Each TLS certificate used in the Peppol eDelivery Network MUST be issued (directly or indirectly) only by a root certificate contained in the latest version of the ' List of pre-loaded CA certificates ' [CACERTS] of the 'Mozilla Network Security Services' [NSS].

It's the responsibility of the actor in the Peppol eDelivery Network to use a TLS certificate that 38 adheres to this policy and to verify that only TLS certificates adhering to this policy are allowed to 39 connect. 40

## POLICY 2 Self-signed certificates 41

42

Self-signed TLS certificates are not allowed.



- Self-signed TLS certificates are not allowed, because man-in-the-middle-attacks could be 43 performed unnoticed. 44

## 2.2 TLS Requirements 45



- TLS configurations SHOULD be constantly updated in order to keep the Peppol eDelivery Network 46 secure. TLS configurations cover areas like: 47

48

49

50

51

52



- · Software versions (security patches)
- · Hash algorithms
- · Key exchange algorithms
- · Certificate requirements
- · Cipher suites

## POLICY 3 TLS Configuration Requirements 53

54

The TLS configuration MUST constantly be of at least grade 'A' according to SSL Labs [SSL-LABS].



<!-- image -->



- To address the fact that requirements to keep the TLS configurations up-to-date, without having 55 to re-issue this policy frequently, the third-party analysis tool offered by SSL Labs is used to verify 56
- the TLS configuration. 57
- Every actor graded below "A" in SSL Labs is considered to be ' unavailable  with regards to the ' 58 Transport Infrastructure Agreement. 59
- Note: this applies to all AccessPoints, for all transport protocols supported in the Peppol eDelivery 60 Network (AS2 and AS4 at the time of writing of this document). This also applies to all SML and 61 Peppol Directory instances. This also applies to SMP instances when operated via https. 62
- 2.3 Customizations to TLS configurations 63

## POLICY 4 Customizations to TLS configurations 64



- TLS configurations MUST NOT be modified in order to allow communication with actors violating 65 the policies of this document. 66
- If an actor breaks at one or more of the policies stated in this document it SHOULD be reported to 67 OpenPeppol Operations. 68
- If an actor breaks at one or more of the policies stated in this document it MUST NOT lead to 69 configuration changes for communicating with that specific actor. 70



<!-- image -->