<!-- image -->

Document Title

Version

1.3

Creation Date

12/05/2025

Confidentiality level

Last update

ASP

Date

17-Sep-25

Validation

Date

Date

## Distribution List



| Company Name   | Departement      | Name          | Signature   |
|----------------|------------------|---------------|-------------|
| Deep           | Managed Services | Brice LEONARD | BLE         |
| BeFresh        |                  |               |             |

## BeFresh Backup Plan

8328\_BeFresh\_Avamar\_Backup\_Plan

8328 BeFresh Managed Services Avamar Backup plan

## Summary



| BEFRESH   | BACKUP PLAN ................................................... 1                         |
|-----------|-------------------------------------------------------------------------------------------|
| 1.        | VERSIONS HISTORY  ................................................. 3                     |
| 2.        | PREAMBLE .............................................................. 4                 |
| 3.        | BACKUP PLAN  .......................................................... 4                 |
| 3.1.      | DAILY ONLINE BACKUP FOR SERVERS (OS OR VMDK)  ........................  4                 |
| 3.2.      | DATASETS  ............................................................................  5 |



<!-- image -->

Page 2 sur 6

## 1. VERSIONS HISTORY



|   Version | Description                                                                                                                              | SR/RFC           | Date       | Up   |
|-----------|------------------------------------------------------------------------------------------------------------------------------------------|------------------|------------|------|
|       1   | Initial version &amp; add Sv- 8328lvp01, Sv-8328lvp02, Sv- 8328lvp03, Sv-8328lvp04, Sv- 8328lvp05, Sv-8328lvp06, Sv- 8328lvp07, Sv-8328lvp08 | O.08328.0.000.CX | 09/05/2025 | BLE  |
|       1.1 | Add SV-8328avp01                                                                                                                         | CHG0034978       | 30/07/2025 | BLE  |
|       1.2 | Add sv-8328lvp09.rh.8328.local,  sv-8328lvp10.rh.8328.local                                                                              | RITM0059587      | 25/08/2025 | BLE  |
|       1.3 | Add sv-8328lvp11.rh.8328.local                                                                                                           | RITM0060976      | 17/09/2025 | ASP  |



<!-- image -->

Page 3 sur 6

## 2. PREAMBLE

The present document is a summary of the backup plan for BeFresh servers.

## 3. BACKUP PLAN

## 3.1. Daily Online Backup for Servers (OS or VMDK)



| DOMAIN                         | CLIENT       | GROUP          | SCHEDULE   | DATASET   |   daily  weekly  monthly  yearly |   daily  weekly  monthly  yearly |   daily  weekly  monthly  yearly |   daily  weekly  monthly  yearly |
|--------------------------------|--------------|----------------|------------|-----------|----------------------------------|----------------------------------|----------------------------------|----------------------------------|
| /sv-2000wvp112.ebrc.cloud/8328 | SV-8328AVP01 | G-DIS-14D6W12M | 8314-12AM  | 8328-VM   |                               14 |                                6 |                               12 |                                0 |
| /sv-2000wvp112.ebrc.cloud/8328 | sv-8328lvp01 | G-RCS-14D6W12M | 8314-12AM  | 8328-VM   |                               14 |                                6 |                               12 |                                0 |
| /sv-2000wvp112.ebrc.cloud/8328 | sv-8328lvp02 | G-RCW-14D6W12M | 8314-12AM  | 8328-VM   |                               14 |                                6 |                               12 |                                0 |
| /sv-2000wvp112.ebrc.cloud/8328 | sv-8328lvp03 | G-DIS-14D6W12M | 8314-12AM  | 8328-VM   |                               14 |                                6 |                               12 |                                0 |
| /sv-2000wvp112.ebrc.cloud/8328 | sv-8328lvp04 | G-DIS-14D6W12M | 8314-12AM  | 8328-VM   |                               14 |                                6 |                               12 |                                0 |
| /sv-2000wvp112.ebrc.cloud/8328 | sv-8328lvp05 | G-DIS-14D6W12M | 8314-12AM  | 8328-VM   |                               14 |                                6 |                               12 |                                0 |
| /sv-2000wvp112.ebrc.cloud/8328 | sv-8328lvp06 | G-DIS-14D6W12M | 8314-12AM  | 8328-VM   |                               14 |                                6 |                               12 |                                0 |
| /sv-2000wvp112.ebrc.cloud/8328 | sv-8328lvp07 | G-DIS-14D6W12M | 8314-12AM  | 8328-VM   |                               14 |                                6 |                               12 |                                0 |
| /sv-2000wvp112.ebrc.cloud/8328 | sv-8328lvp08 | G-DIS-14D6W12M | 8314-12AM  | 8328-VM   |                               14 |                                6 |                               12 |                                0 |
| /sv-2000wvp112.ebrc.cloud/8328 | sv-8328lvp09 | G-DIS-14D6W12M | 8314-12AM  | 8328-VM   |                               14 |                                6 |                               12 |                                0 |
| /sv-2000wvp112.ebrc.cloud/8328 | sv-8328lvp10 | G-DIS-14D6W12M | 8314-12AM  | 8328-VM   |                               14 |                                6 |                               12 |                                0 |
| /sv-2000wvp112.ebrc.cloud/8328 | sv-8328lvp11 | G-DIS-14D6W12M | 8314-12AM  | 8328-VM   |                               14 |                                6 |                               12 |                                0 |



<!-- image -->

Page 4 sur 6

## 3.2. Datasets



| Domain                         | Dataset   | Plugin  Included                              | Excluded   |
|--------------------------------|-----------|-----------------------------------------------|------------|
| /sv-2000wvp112.ebrc.cloud/8328 | 8328-VM   | Linux VMware Image, Windows VMware Image  ALL |            |



<!-- image -->

Page 5 sur 6

## 4. ADDITIONAL INFORMATIONS

## Definitions :



| Avamar domains are distinct zones within the Avamar server that are used to organize and segregate clients.                                                                                                                                                                                                               | DOMAINS                   |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------|
| Backup rules set.                                                                                                                                                                                                                                                                                                         | DATASETS                  |
| An Avamar Group provides the mechanism for applying a set of backup rules to a collection of clients.  Groups contain a Dataset, a Schedule, and a Retention Policy which comprise the backup policy for all members (clients) of the group.                                                                              | GROUPS                    |
| An Avamar Retention Policy dictates how long a backup will remain on an Avamar server before being automatically deleted.  D =Daily (Indicates how many daily backups will be retained)  W =Weekly (Indicates how many weekly backups will be retained)  M =Monthly (Indicates how many monthly backups will be retained) | D/W/M/Y  Retention Policy |

## All backups are encrypted and replicated.



- · Weekly backups are scheduled on Sundays.
- · Monthly backups are scheduled the first day of the month.
- · Yearly backups are scheduled the first day of the year.



<!-- image -->

Page 6 sur 6