---
title: "Information Security Management System (ISMS)"
subtitle: "Backup management"
shortTitle: "(ITR-BackupMgt)"
info:
  type: "Procedure (PRO)" 
  reference: "#813"
  version: "1.7"
  status: "Final" 
  owner: "C. Harpes"
  date: "30/11/2024" 
  classification: "Internal"
abstract: |
  This document is part of the ICT management domain of itrust consulting. It specifically addresses the topic of backup management. An irrecoverable loss of data can seriously harm the sustainability of an organization. A rigorous and effective backup management procedure can minimize this risk. The backup management procedure is available to all members of the ICT department on wiki.itrust.lu.
---

# Introduction


## Context

This document is part of the Information Security Management System (ISMS) of itrust consulting. It refers to chapter A.12 of Annex A of the ISO/IEC 27001 standard [10] and the relative security controls listed in the ISO/IEC 27002 standard [11].
An irrecoverable loss of data can seriously harm the sustainability of an organization, but a rigorous and effective backup management procedure can minimize this risk. That is why this backup management procedure has been created by itrust consulting. An additional wiki page [6] has been created for ICT administrators.

## Objectives

This document defines the backup strategies and execution processes for itrust consulting. They ensure that data are available and integer to be restored in case of failure of primary systems.

## Scope

The backup management procedure applies to the physical servers (see the list at [7]), hypervisors, virtual machines, and laptops belonging to itrust consulting.

## Enforcement and reading instructions

This document becomes effective once approved by the Managing Director and published on the ISMS repository [4] available to all employees of itrust consulting (share.itrust.lu). This document will remain in effect until cancellation or revision by the Managing Director. Do not rely on a printed document, but rather check on share.itrust.lu for the currently applicable version.
The signature of the Managing Director is an official recognition of the mandatory character of this document. It is to be respected by all employees of itrust consulting and a failure to comply with this document may be considered as a violation of the working contract and result in disciplinary action as stated in the People Controls policy [2].
The use of the SIMPLE PRESENT tense or the terms ‘MUST’, ‘MANDATORY’, ‘REQUIRED’, or ‘SHALL’ in a statement means that the statement is considered a formal requirement.
The use of words such as ‘SHOULD’ or the adjective ‘RECOMMENDED’ means that there may be legitimate reasons that would dispense to run the statement, but that the implication of such an exemption shall be assessed and fully understood.
The terminology ‘MAY’ or the adjective ‘OPTIONAL’ means that the implementation of the statement is at the discretion of the implementer.

## Audience

This document shall be read and applied by all employees of itrust consulting.



## Document structure

The remainder of the document is structured as follows:
- Chapter 2 details the responsibilities and the assets involved in backup management.
- Chapter 3 describes the different backup processes in detail.
- Chapter 4 addresses capacity management.
- Chapter 5 indicates how backups are tested.
- Chapter 6 details how employees should backup information from their laptops.

## References

[1] itrust consulting, ISMS, Standard, Glossary (ITR-Glossary), #0G.

[2] itrust consulting, ISMS, Standard, People controls (ITR-PeopleControls), #6.

[3] itrust consulting, ISMS, Standard, Asset inventory (ITR-AssetInventory), #509A.

[4] itrust consulting, ISMS, repository of itrust consulting, N:\_INternal\ISMS.

[5] itrust consulting, Redmine website, https://redmine.itrust.lu.

[6] itrust consulting, wiki page, https://wiki.itrust.lu/index.php/Backup_Management.

[7] itrust consulting, wiki page, https://wiki.itrust.lu/index.php/List_of_servers.

[8] Scooter software, Beyond compare website, http://www.scootersoftware.com/.

[9] Open source HIDS security website, OSSEC, http://ossec.github.io/.

[10] ISO/IEC 27001:2022, Information security, cybersecurity and privacy protection — Information security management systems — Requirements..

[11] ISO/IEC 27002:2022, Information security, cybersecurity and privacy protection — Information security controls.


# Backup management


## Responsibilities

The CIO is responsible for the following:

- ensuring that backups are performed on the information systems of the organization based on the requirements indicated in this document;
- testing and maintaining the restoration process in line with business needs.

## Assets

The table below lists the assets involved in the backup management process: 


|Asset| Definition|
|--- | --- |
|Physical servers|The physical servers that contain the hypervisors, the virtual machines, and the physical disks containing the Reference Data (RD)|
|Hypervisors|The hypervisors used to run and maintain virtual machines|
|Virtual machines|Virtual machines running the needed services like the itrust-share|
|Laptops|Laptops used by the employees of itrust consulting|



# Reference data backup


## General methodology

Figure 1: General backup methodology overview

According to the figure above, there are four types of data involved in the backup process:

1. Reference data (RD): this data is online data used by different services of itrust. It is mainly stored in Niederanven site. Other sites/servers which store reference data are vm-gandi-websites (which runs websites), vm-gandi-loadbalancer (which runs load balancer of ÉpStan service), and vm-ovh-monitor (which runs icinga2 instance for monitoring of services);
1. Local backup (LB): these are daily copies of the RD. They are stored at Niederanven and used if there is a problem with the RD.
1. Remote backup (RB): this data is stored on a remote disk in Berbourg. The purpose of this data is to prevent a disaster if there is a loss of LB or RD at the Niederanven site.
1. Offline backup (OB): this data is stored offline and is used to detect illegitimate modifications on other types of data.


The following table summarizes the different characteristics of the different backups: 

|Data| Status| Update frequency |Copies| Mode| Save |In case of disaster|
|--|--|--|--|--|--|--|
|Reference Data (RD)|Constant|Constant|1|Online|-|LB, RB, OB|
|Local Backup (LB)|Backup|Daily|1|Online|RD|RD, RB, OB|
|Remote Backup (RB)|Backup|Daily|1|Online|RD, LB|RD, LB, OB|
|Offline Backup (OB)|Backup|Monthly|4|Offline|RD, LB, OB|RD, LB, RB|

## Reference data (RD)

Reference data is the data used by the different services itrust provides internally or to customers. This data is located on the servers at the Niederanven site and the different virtual machines run by external providers (vm-gandi-websites, vm-gandi-loadbalancer, vm-ovh-monitorer).
The document list of instances per service [3] shows the data currently defined as reference data (which is included in the backups).

## Local backup

The RD backup starts automatically every day at midnight. The backup is written to a hard drive connected locally to the machine ‘sv-lan-addc’. If an error occurs during the backup, e.g. corrupted disk, the CIO and his substitutes are notified by email. This email notification contains the description of the error which comes from the descriptive log files generated by the scripts managing the synchronization. Backups are based on configuration files that the main script will use as input.

The command to launch a local backup is: /root/scripts/startBackups

The backup script will loop on the following folder to find the configuration: /etc/rsync.backups

## Remote backup

Remote backup data is on a hard drive connected to the machine ‘sv-berbourg’ located at the Berbourg site. Given the confidential nature of the data being transferred, it is necessary to use encryption between the two sites during backup. The order and the log management are identical to that of the local backup.

The command to launch a remote backup is: /root/scripts/startBackups

The configuration file for remote backup is: /etc/rsync.backups/999_remote-berb.conf

## Local and remote backup schedule

The task scheduler cron is used to start both the local and remote backups, always at 21h. The script run by cron is: /root/scripts/rsyncOffline
The script starts the local backup and directly afterwards the remote backup.



## Offline backup

An offline backup is performed by itrust consulting during 4-month windows. For this purpose, 4 hard drives have been prepared:

Figure 2: Offline backup strategy

The index of months and disks can be seen in the table below:

|Month| Disk| Month| Disk|
|--|--|--|--|
|January|0|July|2|
|February|1|August|3|
|March|2|September|0|
|April|3|October|1|
|May|0|November|2|
|June|1|December|3|

## Virtual machine backup

These machines do not contain data but are necessary to enable the access to reference data.
Virtual machines are backed up daily at 1h on a disk connected to the ‘hyper-lan server’. In case of a disaster, the virtual machines can be restored from the disk. On modifications to virtual machines (updates, new installation), a snapshot is created, so that in case of errors, the virtual machine can be restored to a working state.

## Virtual machine backup schedule

The task scheduler cron is used to start the virtual machine backup. A check is done to verify if it is the first day of the month. On the first day of each month, a local and remote backup of the virtual machines is performed.
The script called by cron is: /root/backup or /root/scripts/backup



## Recording

Records of successful or unsuccessful backups are available on the ‘sv-lan-addc’ machine under: /var/log/cscripts/backups



# Capacity management


## Checking capacity

Checking for available memory and disk space is performed using the following tools:

- OSSEC [9] is an open-source host-based intrusion detection system, as well as common IDS functions, makes real-time analysis of the log to detect any problems on the host. In case a machine has insufficient memory, an email alert is sent to ict@itrust.lu. Figure 3 shows an example of such email;
- a custom bash script is used in order to check if the capacity of any disk mount point of any machine is nearly full (90% of the disk mount point capacity is reached).

Figure 3: OSSEC email notification

## Resolving capacity issues

The following requirements are followed in order to sufficiently manage capacity issues.
For memory, two scenarios are possible:

- in the event that a virtual machine runs out of memory, the memory configuration of the machine is required to be reconfigured to increase memory capacity; this is dependent on whether the hypervisor can provide more memory (if not, see the next point);
- in the event that hypervisors or physical servers run out of memory, an assessment is made of how much additional memory is needed before a replacement is bought.

For disks, two scenarios are possible:

- when disk space is nearly full for a virtual machine, its container is required to be extended; this depends on whether the hypervisor can provide more disk space (if not, see the next point);
- when a disk is nearly full on a hypervisor or physical server, an assessment is made of how much additional disk space is needed before a replacement is bought.



# Testing

The CIO tests the following on a yearly basis:

- backup media used in the backup management process;
- the adequacy of the backup management process.

The CIO may also choose to perform ad hoc tests in the event of any changes that affect backup management, e.g. acquisition new hardware. Test results are validated by the asset owners and logged in the Redmine [5] ticketing tool.



# Laptop backup

Regular backups are performed for working documents shared between itrust consulting employees or with customers via Nextcloud or ownCloud. Beyond Compare [8] tool for backup can also be used by itrust employees to backup working documents to the itrust consulting server. Furthermore, it is recommended that employees of itrust consulting do backups as follows:

- backup work emails on a monthly basis, the backup frequency is such that emails received and sent in between two backups are kept on the exchange server;
- a snapshot of the configuration after the first complete installation or important change to wherever they prefer (itrust consulting share or locally).

Employees of itrust consulting are allowed to make a temporary backup on their own hard disk at their private home under the following conditions:

- they keep the disk under their sole control, e.g. in a locked environment in their home;
- they use the appropriate, itrust consulting authorized encryption [3] if they transport it to another location or to work;
- they wipe all data on first request by itrust consulting, and once their working contract with itrust consulting has been cancelled. 6.1 Nextcloud - ownCloud

All working documents related to itrust consulting and its clients are stored in their own infrastructure and shared between all collaborators through the technologies: Nextcloud and ownCloud.
Nextcloud is used by itrust consulting employees to store, produce and share all itrust consulting related documents. ownCloud is used by itrust consulting employees to collaborate with customers and to share and store their data. Therefore, itrust consulting employees are requested to save all itrust consulting related data (personal documents, timesheets, contracts, reports, etc.) on the nextcloud.itrust.lu server and customer-related data on the owncloud.itrust.lu server.
Regular backups are performed on these two servers and allow users to retrieve their documents in case of an incident on their own machine. 6.2 Windows system restore point
Although data is stored in the cloud, it is possible for users to set a restore point. This feature allows to restore Windows at any time in case of lost files or unstable system. The process to do a restore point is as follows:

1. Click on the search bar, type ‘Restore point’ and click on ‘Create restore point’.
1. Click on ‘Configure’
1. In the window that opens, click on ‘Turn on system protection’. Then move the slider to set the maximum disk space for restore points. Then click on OK.
1. Click on create button
1. Name the restore point
1. Finally, click on create.

Once the backup file created, it is possible to restore it at any time using the same restore utility. Going back to an older backup point may erase current files.