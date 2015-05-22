###openstuck.py repository

This script allows testing/stressing/benchmarking of your openstack deployments in a multi-clients way

##Requisites

- python-keystoneclient  python-glanceclient  python-novaclient python-neutronclient  python-cinderclient  python-swiftclient rpms
- python-prettyparse rpm
- openstuck.ini file in your home directory or in same directory as program (look at sample for syntax)

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
- OS_NEUTRON_EXTERNALID


##TODO LIST 

- wait/check for correct status before reporting instances creation/deletion as ok 
- wait/check for correct status before reporting heat creation/deletion as ok 
- redefine a more advanced heat template for default testing
- improve values for testing alarms creation (threshold and metrics with some sense)
- add listmeters to test ( and stressing of instance to check it s reported by ceilometer)
- handle specifically known exceptions instead of beeing generic
- improve Create_Subnet function to be able to create more than 254 networks as we use the current step to establish cidr (optionally dont do steps, and create as many subnets as nets, one subnet per net...)
- add tenantid in network creation tests
- create a specific flavor during nova testing instead of hardcoded relying on m1.tiny


##Known bugs
- Create_Backup race condition giving a "Invalid volume: Volume to be backed up must be available" message
- Race condition when creating a lot of network giving the error No available network found in maximum allowed attempts .see https://bugzilla.redhat.com/show_bug.cgi?id=1194432. Note its related to concurrency as it doesnt occur when running sequential tests
- Add_FlavorAccess and Remove_FlavorAccess tests

##Problems?

Send me a mail at [karimboumedhel@gmail.com](mailto:karimboumedhel@gmail.com) !

Mac Fly!!!

karmab
