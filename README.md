###openstuck.py repository

This script allows testing/stressing/benchmarking of your openstack deployments in a multi-clients way

##Requisites

- python-keystoneclient  python-glanceclient  python-novaclient python-neutronclient  python-cinderclient  python-swiftclient python-paramiko  RPMS
- python-prettyparse rpm

##Contents

-    `README.md` this file
-    `openstuck.py`  tests/stresses your openstack
-     keystonedefaulttests   = ['CreateTenant', 'Create_User', 'Create_Role', 'Add_Role', 'Authenticate_User', 'Delete_User', 'Delete_Role', 'Delete_Tenant']


##Disabled Checks
- GrowVolume
- Create_Backup
- Create_Snapshot
- Create_Volum_From_Snapshot
- List_Backup
- List_Snapshot
- Delete_Backup
- Delete_Snapshot

##Typical uses
     
-  TEST YOUR OPENSTACK DEPLOYMENT
    - `openstuck.py`
-  TEST ONLY KEYSTONE
    - `openstuck.py -v -K`

##Additional Environment variables used and their default value

- OS_NOVA_IMAGE 	 defaults to cirros 
- OS_NOVA_FLAVOR         defaults to m1.tiny
- OS_NOVA_NETWORK        defaults to private
- OS_CINDER_VOLUME_TYPE  defaults to None
- OS_KEYSTONE_TESTS      defaults to Create_Tenant, Create_User, Create_Role, Add_Role, ListRole, Authenticate_User, Delete_User, Delete_Role, Delete_Tenant
- OS_GLANCE_TESTS        defaults to Create_Image, List_Image, Delete_Image
- OS_CINDER_TESTS        defaults to Create_Volume, List_Volume, Delete_Volume
- OS_NEUTRON_TESTS       defaults to Create_Network, List_Network, Delete_Network
- OS_NOVA_TESTS          defaults to Create_Server, List_Server, Delete_Server
- OS_HEAT_TESTS          defaults to Create_Stack, List_Stack, Delete_Stack
- OS_CEILOMETER_TESTS    defaults to Create_Alarm, List_Alarm, Delete_Alarm
- OS_SWIFT_TESTS         defaults to Create_Container, List_Container, Delete_Container
- OS_GLANCE_IMAGE_PATH   defaults to None
- OS_GLANCE_IMAGE_SIZE   defaults to 10. Used when creating a volume from the image as part of the NOVA tests
- OS_HEAT_TEMPLATE       defaults to None ( and will then create a sample one if OS_NOVA_IMAGE, OS_NOVA_FLAVOR and OS_NOVA_NETWORK are defined or custom ones if embedded mode
- OS_CINDERBACKUP_VOLUME defaults to volume. If specified, it should be an existing volume with a unique name accross all tenants
- OS_CINDERBACKUP_ID     defaults to None. This is an alternative around the existing limitations of OS_CINDERBACKUP_VOLUME
- OS_SWIFT_OBJECT_PATH	 defaults to the string  This is openstuck test data
- OS_TIMEOUT		 generic timeout value when waiting for status of created resources
- OS_KEYSTONE_TIMEOUT	
- OS_CINDER_TIMEOUT
- OS_GLANCE_TIMEOUT
- OS_NEUTRON_TIMEOUT		
- OS_NOVA_TIMEOUT		
- OS_CEILOMETER_TIMEOUT		
- OS_SWIFT_TIMEOUT		
- OS_HEAT_TIMEOUT		
- OS_NEUTRON_EXTERNALNET
- OS_HA_AMQP


##TODO LIST 


- IMPORTANT: handle better errors in novabefore and make sure to delete elements like tenant and other resources created there
- improve values for testing alarms creation (threshold and metrics with some sense)
- handle specifically known exceptions instead of beeing generic
- Create a dedicated metadata check with a script that does a echo in /dev/ttyS0
- Add specific ping security rules (usefull in provisioning mode)


##Known bugs
- Create_Backup race condition giving a "Invalid volume: Volume to be backed up must be available" message
- Race condition when creating a lot of network giving the error No available network found in maximum allowed attempts .see https://bugzilla.redhat.com/show_bug.cgi?id=1194432. Note its related to concurrency as it doesnt occur when running sequential tests
- Add_FlavorAccess and Remove_FlavorAccess tests might not work as expected 
- When testing on juno, it is not possible for an user to create public images, ( can be worked aroune editing /etc/glance/policy.json), so we switch to private images 

##Problems?

Send me a mail at [karimboumedhel@gmail.com](mailto:karimboumedhel@gmail.com) !

Mac Fly!!!

karmab
