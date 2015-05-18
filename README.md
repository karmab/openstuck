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

##Typical uses
     
-  TEST YOUR OPENSTACK DEPLOYMENT
    - `openstuck.py`
-  TEST ONLY KEYSTONE
    - `openstuck.py -v -K`

##Additional Environment variables used and their default value

- OS_NOVA_IMAGE 	defaults to cirros 
- OS_NOVA_FLAVOR        defaults to m1.tiny
- OS_NOVA_NETWORK       defaults to private
- OS_CINDER_VOLUME_TYPE defaults to None
- OS_KEYSTONE_TESTS     defaults to Create_Tenant, Create_User, Create_Role, Add_Role, ListRole, Authenticate_User, Delete_User, Delete_Role, Delete_Tenant
- OS_GLANCE_TESTS       defaults to Create_Image, List_Image, Delete_Image
- OS_CINDER_TESTS       defaults to Create_Volume, List_Volume, Delete_Volume
- OS_NEUTRON_TESTS      defaults to Create_Network, List_Network, Delete_Network
- OS_NOVA_TESTS         defaults to Create_Server, List_Server, Delete_Server
- OS_HEAT_TESTS         defaults to Create_Stack, List_Stack, Delete_Stack
- OS_CEILOMETER_TESTS   defaults to Create_Alarm, List_Alarm, Delete_Alarm
- OS_SWIFT_TESTS        defaults to Create_Container, List_Container, Delete_Container
- OS_GLANCE_IMAGE_PATH  defaults to None
- OS_HEAT_TEMPLATE      defaults to None ( and will then create a sample one if OS_NOVA_IMAGE, OS_NOVA_FLAVOR and OS_NOVA_NETWORK are defined )

##TODO LIST 

- wait/check for correct status before reporting volumes test creation/deletion as ok 
- wait/check for correct status before reporting instances test creation/deletion as ok 
- wait/check for correct status before reporting heat test creation/deletion as ok 
- redefine a more advanced heat template for default testing

##Problems?

Send me a mail at [karimboumedhel@gmail.com](mailto:karimboumedhel@gmail.com) !

Mac Fly!!!

karmab
