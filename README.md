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

##Problems?

Send me a mail at [karimboumedhel@gmail.com](mailto:karimboumedhel@gmail.com) !

Mac Fly!!!

karmab
