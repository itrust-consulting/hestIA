---
title: "Information Security Management System (ISMS)"
subtitle: "Backup Plan"
shortTitle: "(ITR-BackupPlan)"
info:
  type: "Procedure (PRO)" 
  reference: "#813A"
  version: "1.3"
  status: "Final" 
  owner: "CISO"
  date: "03.05.23" 
  classification: "Restricted"
abstract: ""
---

|ID |Asset / Service| Description| Backup frequency|Responsible|
|--|--|--|--|--|
|1|EpStan TTP (production data)| A pseudonymisation service which allow the Luxembourg Centre for Educational Testing (LUCET) of the University of Luxembourg to access some private data of students without both the LUCET and the ministry, even collectively, being able to associate it to a precise student. |Every 2 hours |CIO|
|2 |GitLab (source code, malwasm, LASP, ISIS, softwarechecker, etc.) |A web-based Git repository manager with wiki and issue tracking features. |Daily |CIO|
|3 |ICT inventory (Snipe-IT online)| A FOSS project for asset management in IT Operations.| Daily |CIO|
|4 |itrust consulting wiki |MediaWiki is a free and open-source wiki application.| Daily| CIO|
|5 |Laptops or workstations of employees| Personal and company's computers. |Monthly |Employee|
|6 |malware.lu |CERT website Website of malware.lu. |Daily |CIO|
|7 |Mobile devices of employees| Mobile phones (Smartphones) of employees.| As per schedule |Employee|
|8 |Nextcloud |A web-based File reposistory, access is limited to itrust consulting employee URL: https://nextcloud.itrust.lu |Daily |CIO|
|9 |Official itrust.lu website |Website of itrust consulting itrust.lu. |Daily |CIO|
|10|Owncloud| A web-based File reposistory, access is limited to itrust consulting employee and customers URL: https://owncloud.itrust.lu|Daily| CIO|
|11| Redmine| Redmine is a free and open source, web-based project management and issue tracking tool.| Daily| CIO|
|12|Shared drive (client info, confidential info, ISMS, R&D HR, or Sales documents, etc.)|Linux or Unix path smb://dc1.domitr.itrust.lu/; Windows path \\dc1.domitr.itrust.lu\ The share service running Samba software. It is used by itrust consulting employees to store and share documents regarding projects made for client, timesheet, HR information etc.|Daily| CIO|
|13| TRICK Service (production data) Internally developed web application designed to conduct risk assessments. DMZ: https://app.trickservice.com LAN: https://trickservice.itrust.lu|Daily| CIO|
|14 |Virtual Private Network |VPN certificates of itrust consulting. |Daily| CIO|
|15 |Servers, VM's, hypervisors |Servers, virtual machines and hypervisors of itrust consulting |Daily |CIO
|16 |Firewall LAN, DMZ |Firewall LAN, DMZ |Daily| CIO|
|17 |Switch |Switch configuration file |As per schedule |CIO|
|18 |Router |Router configuration file |As per schedule |CIO|