---
title: "Information Security Management System (ISMS)"
subtitle: "ICT infrastructure"
shortTitle: "(ITR-ICTInfra)"
info:
  type: "Standard" 
  reference: "#820A"
  version: "2.3"
  status: "Final" 
  owner: "C. Harpes"
  date: "30/01/2025" 
  classification: "Restricted"
abstract: "This standard describes the network architecture of itrust consulting at Niederanven and Berbourg site."
---



# Introduction


## Context of this document

This document belongs to the IT documentation of the Information Security Management System of itrust consulting and focuses on the description of technical aspects of the Information Security Management System.

## Objectives of the mission

The objective of the document is to:

- describe the network architecture deployed at Niederanven and Berbourg;
- provide a port connection plan of the Niederanven site.

## Document structure

The remainder of this document is structured as follows:

- Chapter 2 describes the network architecture of itrust consulting. It contains a description of the logical network and a description of the port connections of the main site of itrust consulting located at Niederanven.
- Chapter 3 describes what security mechanisms are used to protect the confidentiality, integrity and availability of the elements of the network.
- Chapter 4 presents the technologies used to operate the network and the security mechanisms.

## References

[1] itrust consulting, ISMS, Glossary (ITR-Glossary), #0D.

[2] itrust consulting, ISMS, ICT inventory (ITR-ICTInventory), https://snipeit.itrust.lu/

[3] itrust consulting, ISMS, ITR (ITR-NewPortConf), #514B.

[4] Wikipedia, The Free Encyclopedia, Server Message Block, http://en.wikipedia.org/wiki/Server_Message_Block.

[5] Wikipedia, The Free Encyclopedia, Virtual private network, http://en.wikipedia.org/wiki/Virtual_private_network.

[6] Wikipedia, The Free Encyclopedia, Dynamic Host Configuration Protocol, http://en.wikipedia.org/wiki/Dynamic_Host_Configuration_Protocol.

[7] Wikipedia, The Free Encyclopedia, Web server, http://en.wikipedia.org/wiki/Web_server.

[8] Wikipedia, The Free Encyclopedia, Software versioning, http://en.wikipedia.org/wiki/Software_versioning.

[9] Wikipedia, The Free Encyclopedia, Backup, http://en.wikipedia.org/wiki/Backup.

[10] Wikipedia, The Free Encyclopedia, DMZ (computing), http://en.wikipedia.org/wiki/DMZ_(computing).

[11] Synchronization, storage, and sharing software, Teamdrive, https://www.teamdrive.com/en/.

[12] Inspection générale de la sécurité sociale, IGSS, http://www.mss.public.lu/acteurs/igss/.

[13] The open web application security project (OWASP),https://www.owasp.org/index.php/.

[14] Remote and local file copying tool rsync, https://linux.die.net/man/1/rsync.

[15] Open source software suite samba, https://www.samba.org/.

[16] Setup cryptographic volumes cryptsetup / luks, https://linux.die.net/man/8/cryptsetup.

[17] Packet filtering framework, Netfilter, https://www.netfilter.org/.

[18] Open source java platform, openjdk, http://openjdk.java.net/.

[19] Rocket fast system for log processing, rsyslog, http://www.rsyslog.com/.

[20] Elasticsearch, logstash and kibana, elk, https://www.elastic.co/.

[21] Web caching proxy, squid, http://www.squid-cache.org/.

[22] Open source HTTP server, apache, https://httpd.apache.org/.

[23] Open source distributed version control system, gitlab, https://gitlab.itrust.lu/.

[24] Free operating system, Debian, https://www.debian.org/releases/wheezy/.

[25] Open source software for java implementation, apache tomcat, http://tomcat.apache.org/.

[26] Shell for interactive use, zsh, http://www.zsh.org/.

[27] Virtualization product, virtualbox, https://www.virtualbox.org/.

[28] VPN Tunnel, WireGuard, https://www.wireguard.com/

[29] URL redirector, Squidguard, http://www.squidguard.org/.

[30] Monitorer, Wazuh, https://wazuh.itrust.lu/

[31] Monitor availability of services,https://icinga.com/

[32] Loadbalancer for EpStan, https://www.haproxy.org/

[33] Open source distributed version control system, github, https://github.com/itrust-consulting

[34] Containerization, docker, https://www.docker.com/

[35] Containerization, kubernetes, https://kubernetes.io/

# Network architecture

This chapter describes the network architecture of itrust consulting. The chapter contains a description of the logical network and a description of the port connections of the main site of itrust consulting located in Niederanven.

## Description of the general architecture

The general network architecture of itrust consulting is split into two network sites (see Figure 1), both connected on the Internet:

- Niederanven site: it is the main site of itrust consulting where employees work most of the time. It also contains the main network components such as web servers opened on the Internet, and most of the reference data;
- Berbourg site: it is the secondary site of itrust consulting. Only sporadic work is made at this place. This site also stores a backup of online data of itrust consulting, and act as backup site for ÉpStan service;
- Gandi site: it is a webserver machine hosted by Gandi provider and used to provide websites (e.g. itrust.lu, cockpitci.eu) to customers, and to provide load balancer for ÉpStan service;
- OVH site: it is a server hosted by OVH and used to operate an Icinga2 instance to do monitoring of itrust’s services.

The figures in the next chapters depict the different detail levels of network architecture of itrust consulting.
Figure 1: General logical network
InternetNiederanven siteBerbourg siteGandi site (Bissen)OVH site (Strasbourg)
 

## Berbourg network

Figure 2: Berbourg network

## Niederanven network

Niederanven network (see Figure 3) has been separated into five main sub-networks:

- DMZ network (DN): this network hosts services (e.g. ÉpStan TTP service) to be provided on the Internet;
- Wi-Fi network (WFN): the Wi-Fi network can be used by employees and guests to access the Internet;
- Employee network (EN): this network contains the machines of the employees;
- Server and administration network (SAAN): this network hosts the servers which are critical and only to be provided to the employees. It also hosts the ICT administrators;
- VPN network (VN): this network contains employee devices connected through WireGuard.
 
Figure 3: Niederanven logical network

We use two different network numberings for internal and external connections. 192.168.x.0 network numbering denotes the local network of Niederanven, and 10.0.x.0 network numbering denotes the external network, i.e. connection point where devices connecting to it can (VPN) or could (WFN) be outside of the Niederanven network.

### Employees network (EN) – 192.168.1.0/24

The employees’ network must only be accessed by employees. From this network, employees only have access to the Internet and the services provided by the server and administration network. Access to the DMZ services is done through a reverse proxy located in the server and administration network.

### Server and administration network (SAAN) – 192.168.0.0/24

The server and administration network contains the main services provided to employees. It contains for example the share of data (CO, IN) and the Redmine service. ICT administrators are connected to this network and can thus access the different administration ports (e.g. SSH) of the different services and servers located in the entire network (including those in the DMZ).
Services provided to employees by the server and administration network include (the list is not exhaustive):

- Share: this service provides sharing capabilities between different employees;
- Redmine: a ticketing service for managing issues in projects;
- Gitlab server to maintain a central git repository;
- Wiki: a wiki to maintain documentation on IT management;
 

### DMZ network (DN) – 192.168.4.0/24

A DMZ network primary goal is to provide services to the Internet while protecting internal LAN, using sub-network separation. Therefore, it must only contain services that need to be provided on the Internet for commercial or research projects of itrust consulting. Current services that are provided include (the list is not exhaustive):

- TRICK Service demo: version deployed for use by testers;
- ÉpStan server, which provides access to the ÉpStan TTP service.

Components located in the DN can only access the Internet.

### Wi-Fi network (WFN) – 192.168.3.0/24

The Wi-Fi network is dedicated to connecting the mobile devices of employees and guests to the Internet. If employees want to access data and/or services of the server and administration network, they must connect to the VPN.
The DHCP currently assigns the IP addresses in range from 192.168.3.100 to 192.168.3.150 to the connected devices on wifi network.

### VPN network (VPN) – 10.0.2.0/24

The VPN network is the network from which employees can access itrust consulting’s network from outside (generally from their house or when working from a customer’s network). This network can only access the Internet and the services provided by the SAAN.
 

### ALAB network – 192.168.0.15

The vm-lan-bastion-cyfort acts as a Gateway to connect ALAB network to itrust network.

### Summary of different network 

|Network| Addressing| User|
|--|--|--|
|Wi-Fi network|Range: 192.168.3.100 to 192.168.3.150|Employee and guests|
|Server and administration network|192.168.0.0/24|Employee through service ports; Administrators through administration ports|
|VPN network|10.0.2.0/24|Employee| 
|Employees network|192.168.1.0/24|Employee |
|Between fwlan and fwdmz|192.168.2.0/24|/ |
|Between fwdmz and Router|192.168.3.0/24|/ |
|DMZ network|192.168.4.0/24|Outside world| 
|CyFORT VLAN|192.168.5.0/24|CyFORT network|

Table 1: Summary of different network sub-nets

### Port connections

Please refer to document 514B_ITR-PortConf [3].
 

# Security mechanisms

Different security mechanisms are implemented in the network architecture in order to comply with confidentiality, integrity and availability requirements.

## Network segregation

The segregation between the different networks is made with two firewalls (fw-lan and fw-dmz). These firewalls each apply white rules policies, which mean that by default all traffic is dropped. Traffic initiated by the firewalls themselves is authorised in order to let them communicate with the Internet.
These primary firewall rules are also applied by all servers operating in the network: if a service is provided by a server (e.g. web service, SMB), an additional firewall rule is applied to authorise external connection on the port(s) of the service.

### From the EN

From the EN, components can access the Internet and the services provided by the SAAN. Access to the Internet is possible because fw-lan and fw-dmz forward traffic coming from internal networks.
In order to access the services provided by the DN, components of the EN must use the reverse proxy located in the SAAN.
Figure 4: EN white rules
 

### From the SAAN

From the SAAN, components can access the DN network, fw-lan and fw-dmz firewalls, fritz.box, and the Internet.
Figure 5: SAAN white rules
 

### From the VN

Components connected through the VPN can access the services provided by the SAAN and the Internet. As for components located within the EN, access to the services provided by the DN is made through the reverse proxy of the SAAN.
Figure 6: VN white rules
 

### From the WFN

From the WFN, components can only access the Internet. Employees connected to the WFN must use the VPN connection in order to access the services provided by the SAAN and the DN.
Figure 7: WFN white rules
 

### From the DN

From the DN, most of components can only access the Internet, only few have access to the specific SAAN services:

- Wazuh agants to vm-lan-monitorer;
- App TRICK Service to Redmine;
- Burp client to vm-lan-backuper;
- Gitlab from DN.

Figure 8: DN white rules

### From the Internet

As some services are provided to the Internet by the DN, the following complementary white rules are applied on the firewalls.
fw-dmz is connected directly to the Router (fritz.box) and accepts and forwards VPN connections from the Internet to the second firewall. It also authorises and forwards connections coming from the Internet on port 443 and 80 to the Front-End server located in the DN.
fw-lan: this firewall is connected behind the fw-dmz firewall. It accepts VPN connections and SSH connections coming from the fw-dmz. SSH server only accepts connections using public key authentication.
 

### From ALab to itrust

Employees of ALab (Abstraction labs) connect to CyFORT VLAN network though tailscale. The gateway ITR-Alab (192.168.0.15 - vm-lan-bastion-cyfort.itrust.lu) is used to connect and filter traffic between two network segments.
Figure 9: Network flow from ALab to itrust

## From itrust to ALab

itrust employees connect to ALab (Abstraction labs) services via the gateway ITR-Alab (192.168.0.15 - vm-lan-bastion-cyfort.itrust.lu)

10.0.2.1Tailscale213.135.240.50192.168.0.1192.168.1.1192.168.2.0/24192.168.3.2192.168.4.1DN VLAN192.168.4.0/24fw-lan192.168.2.2fw-dmz192.168.2.1EN VLAN (192.168.1.0/24)InternetWFN VLAN192.168.3.0/24ALABALabVPN10.0.2.0/24SAAN VLAN192.168.0.0/24CyFort VLAN192.168.5.0/24Gateway ITR-ALab192.168.0.15friz.box192.168.3.1
 
Figure 10: Network flow itrust to ALab

## Opened ports

The following table summarises what ports are open/listening to the Internet. 

|Service| Ports|
|--|--|
|VPN|UDP/5443|
|EpStan VPN|UDP/43490|
|Web|TCP/443, TCP/80|
|SSH|TCP/8609| 
|ÉpStan service|TCP/2000, TCP 2001|

Table 2: Open/listening ports on the Internet

## Proxy

A proxy is installed on the fw-lan, which is responsible for logging what web content is accessed by employees and administrators from the EN, SAAN, and VN. It blocks web content which seems to be vectors of spreading malware, based on an updated malware blacklist.

## VPN access

A VPN access has been implemented on the fw-lan firewall in order to provide access to services of the SAAN to the employees when they are outside of the itrust consulting network. The VPN server requires a strong authentication (each employee has a certificate) before authorizing clients to be connected. When connected to the VPN, all flow between the client and the VPN server is encrypted.

## HTTPS

All services requiring authentication process or transmitting confidential information provided by itrust consulting network (from DMZ or from SAAN) are protected using HTTPS.

## Reverse proxies

Reverse proxies are used to provide internal services of itrust consulting (DMZ and SAAN) to customers and employees:

- one reverse proxy is installed on the fw-lan. This reverse proxy manages web connections from the EN or from the SAAN to the DN or to the SAAN;
- another reverse proxy is installed on the fw-dmz. This reverse proxy manages web connections from the Internet to the DN.

## Monitoring of the network

Wazuh used to centralise and monitor network and host activities. Concretely, servers will collect logs during their operation, and send them to a dedicated server running Wazuh. It enables to make research and present log data with graphics. There are some open ports in Wazuh to collect data from itrust cloud services and these ports are restricted the itrust cloud IPs.

## Deployment server scheme

In the context of software development, three types of servers will operate within the itrust consulting network:

- development server: this type of server is run by developers on their own machine and enables them to test immediately if new or modified features work as planned;
- testing server: this type of server is run by a server on the hypervisor of the SAAN. It enables Product Owners to validate modifications made by developers. It is run on SAAN, as non-validated services should not be accessible on the DN. Access from outside can be made through VPN connection;
- production server: this type of server runs the validated version of services developed by itrust consulting. Two production servers will be available, one on the SAAN and one on the DN. Each production server can operate several services but services that do not require to be provided to the Internet should stay on the SAAN.
 

# Technologies

The following table summarises what technology will be used for different needs in components. 

|Need |Technology |Description |
|--|--|--|
|Differential backup|Rsync / Borg backup [14]/ Burp Backup|Backup of data from SAAN and DN NAS to the Berbourg NAS. 
|Domain controller|Samba [15] / LDAP|Access control of data provided by the share server|
|Encryption|Cryptsetup/LUKS [16] / Bitlocker|Protect data stored by the different NAS. Full-disk encryption feature to protect data by encrypting the entire drive where Windows and user data are stored. 
|Firewall|Netfilter / iptables [17]|Protect network access to the servers. 
|Monitoring|Icinga [31]|Monitor the availability of services from outside or inside. 
|Java virtual machine|OpenJDK [18]|Running software developed under Java EE. 
|Log centralisation|Rsyslog [19]|Sending log activities of one host to the centralised logging server. 
|Loadbalancer|HAproxy [32]|Loadbalancer for EpStan 
Log real-time and historical search|Wazuh [30]|Monitoring and analysis of the network and host activities. Wazuh is used for monitoring websites and network logs. 
|Proxy|Squid [21]|Analysing web user traffic and preventing users access to malware. Squid is currently disabled #6758 created for reinstalling. 
|Reverse proxy|Apache HTTP server [22]|Providing different web services to the Internet and to the EN. 
|Revision control softwares|Gitlab [23] / Github [33]|Versioning of source code between different developers. 
|Server OS|Debian / Ubuntu [24]|Operating system. 
|Linux shell|ZSH [26] / Bash|Controlling command line. 
|Microsoft shell|MS Powershell|Microsoft scripting language and command-line interface. Used in ITR systems for task automation, system management, and configuration such as GPOs, some management scripts, etc. 
|Virtualisation|VirtualBox [27] / KVM|Hosting several virtual machines on unique physical machine. 
|VPN|WireGuard [28]|Enabling outside employees’ access to the SAAN services. 
|Web server|Apache HTTP server [22]|Operating web applications. 
|Website content control|Squidguard [29]|Analysing web user traffic and preventing users’ access to malware. 
|Database|Maria DB / MySQL /Postgres SQL|Database management system |
|Containerization|Docker [34] / Kubernetes [35]|Launching applications in software containers
 

Table 3: Technologies used