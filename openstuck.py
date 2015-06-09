#!/usr/bin/python
"""
script to quickly test an openstack installation
based on api info found at http://www.ibm.com/developerworks/cloud/library/cl-openstack-pythonapis/
"""

import json
import multiprocessing
import optparse
import os
from prettytable import PrettyTable
import random
import sys
import StringIO
import time
import yaml
import paramiko
import cinderclient.exceptions as cinderexceptions
import novaclient.exceptions   as novaexceptions
from keystoneclient.openstack.common.apiclient.exceptions   import NotFound               as keystone_notfound
from glanceclient.exc                                       import HTTPNotFound           as glance_notfound
from cinderclient.exceptions                                import NotFound               as cinder_notfound
from neutronclient.common.exceptions                        import NeutronClientException as neutron_notfound
from novaclient.exceptions                                  import NotFound               as nova_notfound
from heatclient.exc                                         import HTTPNotFound           as heat_notfound
from ceilometerclient.openstack.common.apiclient.exceptions import NotFound               as ceilometer_notfound
from swiftclient.exceptions                                 import ClientException        as swift_notfound
import keystoneclient.v2_0.client as keystoneclient
import glanceclient.v2.client as glanceclient
import cinderclient.v2.client as cinderclient
from neutronclient.neutron import client as neutronclient
from novaclient import client as novaclient
from heatclient import client as heatclient
import ceilometerclient.client as ceilometerclient
import swiftclient.client as swiftclient

__author__     = 'Karim Boumedhel'
__credits__    = ['Karim Boumedhel']
__license__    = 'GPL'
__version__    = '0.1'
__maintainer__ = 'Karim Boumedhel'
__email__      = 'karim.boumedhel@gmail.com'
__status__     = 'Testing'


keystonedefaulttests     = ['Create_Tenant', 'Create_User', 'Create_Role', 'Add_Role', 'ListRole', 'Authenticate_User', 'Delete_User', 'Delete_Role', 'Delete_Tenant']
glancedefaulttests       = ['Create_Image', 'List_Image', 'Delete_Image']
cinderdefaulttests       = ['Create_Volume', 'List_Volume', 'Create_Backup', 'List_Backup', 'Restore_Backup', 'Delete_Backup', 'Create_Snapshot', 'List_Snapshot', 'Delete_Snapshot', 'Delete_Volume', 'Reach_VolumeQuota', 'Reach_StorageQuota']
neutrondefaulttests      = ['Create_SecurityGroup', 'Create_Network', 'Create_Subnet', 'Create_Router', 'List_Network', 'List_Subnet', 'List_Router', 'Delete_Router','Delete_Subnet', 'Delete_Network', 'Delete_SecurityGroup']
novadefaulttests         = ['Create_Flavor','List_Flavor', 'Delete_Flavor', 'Create_KeyPair', 'List_KeyPair', 'Delete_KeyPair', 'Create_Server', 'List_Server', 'Check_Console', 'Check_Novnc', 'Check_Connectivity', 'Add_FloatingIP', 'Check_SSH', 'Grow_Server', 'Shrink_Server', 'Migrate_Server', 'Attach_Volume', 'Detach_Volume', 'Create_VolumeServer', 'Create_SnapshotServer', 'Delete_Server']
heatdefaulttests         = ['Create_Stack', 'List_Stack', 'Update_Stack', 'Delete_Stack']
ceilometerdefaulttests   = ['Create_Alarm', 'List_Alarm', 'List_Meter', 'Delete_Alarm']
swiftdefaulttests        = ['Create_Container', 'List_Container', 'Delete_Container']
hadefaulttests		 = ['Fence_Node', 'Stop_Mysql', 'Stop_Amqp', 'Stop_Mongodb', 'Stop_Keystone', 'Stop_Glance', 'Stop_Cinder', 'Stop_Neutron', 'Stop_Nova', 'Stop_Heat', 'Stop_Ceilometer', 'Stop_Swift']

def _keystonecreds():
	keystoneinfo                = {}
	keystoneinfo['username']    = os.environ['OS_USERNAME']
	keystoneinfo['password']    = os.environ['OS_PASSWORD']
	keystoneinfo['auth_url']    = os.environ['OS_AUTH_URL']
	keystoneinfo['tenant_name'] = os.environ['OS_TENANT_NAME']
	return keystoneinfo

def _novacreds():
	novainfo               = {}
	novainfo['username']   = os.environ['OS_USERNAME']
	novainfo['api_key']    = os.environ['OS_PASSWORD']
	novainfo['auth_url']   = os.environ['OS_AUTH_URL']
	novainfo['project_id'] = os.environ['OS_TENANT_NAME']
	return novainfo

def metrics(key):
	if not os.environ.has_key(key) or not ':' in os.environ[key] or not len(os.environ[key].split(':')) == 2  or not os.environ[key].replace(':','').isdigit():
		return 1,1
	else:
		concurrency = int(os.environ[key].split(':')[0])
		repeat = int(os.environ[key].split(':')[1])
 		return concurrency, repeat


class Openstuck():
	def __init__(self, keystonecredentials, novacredentials, project='', endpoint='publicURL', keystonetests=None, glancetests=None, cindertests=None, neutrontests=None, novatests=None, heattests=None, ceilometertests=None, swifttests=None, hatests=None, imagepath=None, imagesize=10, volumetype=None, debug=False,verbose=0, timeout=80, embedded=True, externalnet=None, clouduser='root', ram='512', cpus='1', disk='20',haamqp='rabbitmq-server',haserver=None, hauser='root', hapassword=None, haprivatekey=None, hafenceservers=None, hafencenames=None, hafenceusers=None, hafencepasswords=None, hafencemodes=None, hafencewait=0):
		self.auth_username    = keystonecredentials['username']
		self.auth_password    = keystonecredentials['password']
		self.auth_tenant_name = keystonecredentials['tenant_name']
		self.auth_url         = keystonecredentials['auth_url']
		self.debug            = debug
		self.novacredentials  = novacredentials
		self.embedded	      = embedded
		self.embeddedobjects  = {}
		self.externalnet      = externalnet
		try:
			self.keystone = keystoneclient.Client(**keystonecredentials)
			try:
				user       = self.keystone.users.find(id=self.keystone.user_id)
				roles      = user.list_roles(self.keystone.tenant_id)
				adminroles = [ role for role in roles if role.name == 'admin' ]
				adminrole  = adminroles[0]
				self.admin = True
			except:
				self.admin = False
			if embedded and self.admin:
				embeddedtenant = self.keystone.tenants.create(tenant_name=project, enabled=True)
				if verbose >0:
					print "Created tenant %s for nova/heat testing" % project
				self.keystone.roles.add_user_role(user, adminrole, embeddedtenant)
				self.auth_tenant_name = project
				self.auth_tenant_id   = embeddedtenant.id
			else:
				self.auth_tenant_name = keystonecredentials['tenant_name']
				self.auth_tenant_id = self.keystone.tenant_id
			
		except Exception as e:
			print "Got the following issue: %s" % str(e) 
			os._exit(1)
		self.keystonetests     = keystonetests 
		self.glancetests       = glancetests 
		self.cindertests       = cindertests
		self.neutrontests      = neutrontests 
		self.novatests         = novatests 
		self.heattests         = heattests 
		self.ceilometertests   = ceilometertests 
		self.swifttests        = swifttests
		self.hatests           = hatests
		self.output            = PrettyTable(['Category', 'Description', 'Concurrency', 'Repeat', 'Time(Seconds)', 'Result'])
		self.output.align      = "l"
		self.endpoint          = endpoint
        	self.project           = project
        	self.tenant            = "%stenant" % project
        	self.user              = "%suser" % project
        	self.password          = "%spassword" % project
        	self.role              = "%srole" % project
        	self.tenant            = "%stenant" % project
        	self.email             = "%suser@xxx.com" % project
        	self.description       = "Members of the %s corp" % project
        	self.image             = "%simage" % project
		self.imagepath         = imagepath
		self.imagesize         = imagesize
        	self.volume            = "%svolume" % project
        	self.volumetype        = volumetype
        	self.securitygroup     = "%ssecuritygroup" % project
        	self.network           = "%snetwork" % project
        	self.subnet            = "%ssubnet" % project
        	self.router            = "%srouter" % project
        	self.server            = "%sserver" % project
        	self.volumeserver      = "%svolumeserver" % project
        	self.snapshotserver    = "%ssnapshotserver" % project
        	self.flavor            = "%sflavor" % project
        	self.keypair           = "%skeypair" % project
        	self.stack             = "%sstack" % project
        	self.alarm             = "%salarm" % project
        	self.container         = "%scontainer" % project
		self.debug            = debug
		self.verbose          = verbose
		self.timeout          = timeout
		self.clouduser        = clouduser
		self.ram              = ram
		self.cpus             = cpus
		self.disk             = disk
		self.haamqp           = haamqp
		self.haserver	      = haserver
		self.hauser	      = hauser
		self.hapassword	      = hapassword
		self.haprivatekey     = haprivatekey
		self.hafenceservers   = hafenceservers
		self.hafencenames     = hafencenames
		self.hafenceusers     = hafenceusers
		self.hafencepasswords = hafencepasswords
		self.hafencemodes     = hafencemodes
		self.hafencewait      = hafencewait
	def _getfloatingip(self, server):
		for net in server.addresses:
        		for info in server.addresses[net]:
                		if info["OS-EXT-IPS:type"] == 'floating':
                        		return info['addr']
		return None

	def _novabefore(self, externalnet=None, image=True, volume=False, snapshot=False):
		tenantid          = self.auth_tenant_id	
		novaflavor1	  = "%s-flavor1" % self.project
		novaflavor2	  = "%s-flavor2" % self.project
		novaimage	  = "%s-image" % self.project
		novavolume	  = "%s-volume" % self.project
		novasnapshot	  = "%s-snapshot" % self.project
		novakey	          = "%s-key" % self.project
		novanet		  = "%s-net" % self.project
		novasubnet	  = "%s-subnet" % self.project
		novarouter	  = "%s-router" % self.project
		imagepath         = self.imagepath
		imagesize         = self.imagesize
		keystone          = self.keystone
		nova              = novaclient.Client('2', **self.novacredentials)
                glanceendpoint    = keystone.service_catalog.url_for(service_type='image',endpoint_type=self.endpoint)
                glance            = glanceclient.Client(glanceendpoint, token=keystone.auth_token)
		cindercredentials = self.novacredentials
		cindercredentials['project_id'] = self.auth_tenant_name
		cinder            = cinderclient.Client(**cindercredentials)
                neutronendpoint   = keystone.service_catalog.url_for(service_type='network',endpoint_type=self.endpoint)
                neutron           = neutronclient.Client('2.0',endpoint_url=neutronendpoint, token=keystone.auth_token)
		if not self.embedded:
				if not os.environ.has_key('OS_NOVA_FLAVOR')  and image:
					raise Exception('Missing OS_NOVA_FLAVOR environment variable pointing to an available flavor for running Create_Server/Create_Stack')
				if not os.environ.has_key('OS_NOVA_IMAGE')  and image:
					raise Exception('Missing OS_NOVA_IMAGE environment variable pointing to an available image for running Create_Server/Create_Stack')
				if not os.environ.has_key('OS_NOVA_NETWORK'):
					raise Exception('Missing OS_NOVA_NETWORK environment variable pointing to an available network for running Create_Server/Create_Stack')
				if not os.environ.has_key('OS_NOVA_VOLUME') and volume:
					raise Exception('Missing OS_NOVA_VOLUME environment variable pointing to an existing volume for running Create_VolumeServer/Create_Stack')
				if not os.environ.has_key('OS_NOVA_SNAPSHOT'):
					raise Exception('Missing OS_NOVA_SNAPSHOT environment variable pointing to an available snapshot for running Create_Server/Create_Stack')
				return
		if not self.embeddedobjects.has_key('flavor'):
			flavor1 = nova.flavors.create(name=novaflavor1,ram=self.ram,vcpus=self.cpus,disk=self.disk)
			flavor2 = nova.flavors.create(name=novaflavor2,ram=self.ram*2,vcpus=self.cpus*2,disk=self.disk)
			if self.verbose >0:
				print "Created flavors %s and %s for nova/heat testing" % (novaflavor1, novaflavor2)
			self.embeddedobjects['flavor']=[flavor1.id, flavor2.id]
		if not self.embeddedobjects.has_key('keypair'):
			keypair = nova.keypairs.create(novakey)
			if self.verbose >0:
				print "Created keypair %s for nova/heat testing" % novakey
			self.private_key = keypair.private_key
			self.embeddedobjects['keypair'] = keypair
		if not self.embeddedobjects.has_key('image') and image:
			image           = glance.images.create(name=novaimage, visibility='private', disk_format='qcow2',container_format='bare')
			if self.verbose >0:
				print "Created image %s for nova/heat testing" % novaimage
			self.embeddedobjects['image'] = image.id
			with open(imagepath,'rb') as data:
				if self.verbose >0:
					print 'Uploading image prior to testing'
				glance.images.upload(image.id, data)
			o._available(glance.images, image.id, timeout,status='active')
			if not self.embeddedobjects.has_key('volume') and volume:
				volume = cinder.volumes.create(name=novavolume,size=self.imagesize, imageRef=image.id)
				if self.verbose >0:
					print "Created volume %s for nova/heat testing" % novavolume
				self.embeddedobjects['volume'] = volume.id
				o._available(cinder.volumes, volume.id, timeout,status='available')
				if not self.embeddedobjects.has_key('snapshot') and snapshot:
					snapshot = cinder.volume_snapshots.create(volume_id=volume.id, name=novasnapshot)
					if self.verbose >0:
						print "Created snapshot %s for nova/heat testing" % novasnapshot
					self.embeddedobjects['snapshot'] = snapshot.id
					o._available(cinder.volume_snapshots, snapshot.id, timeout,status='available')
					
		if not self.embeddedobjects.has_key('network'):
			network         = {'name': novanet, 'admin_state_up': True, 'tenant_id': tenantid}
			network         = neutron.create_network({'network':network})
			if self.verbose >0:
				print "Created network %s for nova/heat testing" % novanet
			networkid       = network['network']['id']
			self.embeddedobjects['network'] = networkid
		else:
			networkid  = self.embeddedobjects['network']
		if not self.embeddedobjects.has_key('subnet'):
			subnet          = {'name':novasubnet, 'network_id':networkid,'ip_version':4,"cidr":'10.0.0.0/24', 'tenant_id': tenantid}
			subnet          = neutron.create_subnet({'subnet':subnet})
			if self.verbose >0:
				print "Created subnet %s for nova/heat testing" % novasubnet
			subnetid        = subnet['subnet']['id']
			self.embeddedobjects['subnet'] = subnetid
		if not self.embeddedobjects.has_key('router'):
			router          = {'name':novarouter, 'tenant_id': tenantid}
			if externalnet is not None:
				externalnets        = [ n for n in neutron.list_networks()['networks'] if n['name'] == externalnet ]
				if externalnets:
					externalid  = externalnets[0]['id']
			        	router['external_gateway_info']= {"network_id": externalid, "enable_snat": True}
			router    = neutron.create_router({'router':router})
			routerid  = router['router']['id']
			self.embeddedobjects['router'] = router['router']
			neutron.add_interface_router(routerid,{'subnet_id':subnetid } )
			if self.verbose >0:
				print "Created router %s for nova/heat testing" % novarouter
		if self.embedded:
			securitygroups = [ s for s in neutron.list_security_groups()['security_groups'] if s['name'] == 'default' and s['tenant_id'] == tenantid]
			if securitygroups:
        			securitygroup=securitygroups[0]
        			securitygroupid=securitygroup['id']
				self.embeddedobjects['securitygroup'] = securitygroupid
        			sshrule = {'security_group_rule': {'direction': 'ingress','security_group_id': securitygroupid, 'port_range_min': '22' ,'port_range_max': '22','protocol': 'tcp','remote_group_id': None,'remote_ip_prefix': '0.0.0.0/0'}}
        			neutron.create_security_group_rule(sshrule)
				if self.verbose >0:
					print "Created security group rule for nova/heat testing"
		return 
	def _novaafter(self):
		tenantid          = self.auth_tenant_id
                keystone        = self.keystone
                glanceendpoint  = keystone.service_catalog.url_for(service_type='image',endpoint_type=self.endpoint)
                glance          = glanceclient.Client(glanceendpoint, token=keystone.auth_token)
		cindercredentials = self.novacredentials
		cindercredentials['project_id'] = self.auth_tenant_name
		cinder            = cinderclient.Client(**cindercredentials)
                neutronendpoint = keystone.service_catalog.url_for(service_type='network',endpoint_type=self.endpoint)
                neutron         = neutronclient.Client('2.0',endpoint_url=neutronendpoint, token=keystone.auth_token)
		nova            = novaclient.Client('2', **self.novacredentials)
		if self.embeddedobjects.has_key('flavor'):
			flavors = self.embeddedobjects['flavor']
			for flavorid in flavors:
				nova.flavors.delete(flavorid)
		if self.embeddedobjects.has_key('keypair'):
			keypair = self.embeddedobjects['keypair']
			keypair.delete()
		if self.embeddedobjects.has_key('image'):
			imageid = self.embeddedobjects['image']
			glance.images.delete(imageid)
		if self.embeddedobjects.has_key('router'):
			router = self.embeddedobjects['router']
			routerid  = router['id']
                       	if router['external_gateway_info']:
				neutron.remove_gateway_router(routerid)
                       	ports = [ p for p in neutron.list_ports()['ports'] if p['device_id'] == routerid ]
                       	for port in ports:
				portid = port['id']
                       	        neutron.remove_interface_router(routerid, {'port_id':portid})
			neutron.delete_router(routerid)
		if self.embeddedobjects.has_key('subnet') and self.embeddedobjects.has_key('network'):
			networkid = self.embeddedobjects['network']
			subnetid = self.embeddedobjects['subnet']
			ports = [ port for port in neutron.list_ports()['ports'] if port['network_id'] == networkid ]
			for port in ports:
        			portid = port['id']
        			neutron.delete_port(portid)			
			neutron.delete_subnet(subnetid)
		if self.embeddedobjects.has_key('network'):
			networkid = self.embeddedobjects['network']
			neutron.delete_network(networkid)
		if self.embeddedobjects.has_key('securitygroup'):
				securitygroupid = self.embeddedobjects['securitygroup']
				neutron.delete_security_group(securitygroupid)
		if self.embeddedobjects.has_key('snapshot'):
				snapshotid = self.embeddedobjects['snapshot']
				o._available(cinder.volume_snapshots, snapshotid, timeout)
				cinder.volume_snapshots.delete(snapshotid)
				o._deleted(cinder.volume_snapshots, snapshotid, timeout)
		if self.embeddedobjects.has_key('volume'):
				volumeid= self.embeddedobjects['volume']
				o._available(cinder.volumes, volumeid, timeout)
				cinder.volumes.delete(volumeid)

	def _clean(self):
		if self.embedded and self.admin:
			tenant = self.keystone.tenants.find(name=self.auth_tenant_name)
			tenant.delete()
	def _first(self, elements):
		for element in elements:
			if element is not None:
				return element
		return None
	def _process(self, jobs):
		for j in jobs:
                	j.start()
		for j in jobs:
			j.join()
	def _addrows(self, verbose, rows):
		if verbose ==0 or not rows:
			return
		for row in rows:
			self.output.add_row(row)
	def _report(self, category, test, concurrency, repeat, time, errors):
		if test in errors:
			self.output.add_row([category, test, concurrency, repeat,'', "Failures: %d" % errors.count(test)])
		else:
			self.output.add_row([category, test, concurrency, repeat,time, 'OK'])
	def _available(self, manager, objectid, timeout, status='available'):
		timein = 0
		newstatus = manager.get(objectid).status
		while newstatus != status:
			timein += 0.2
			if timein > timeout:
				raise Exception('Time out waiting for correct status')
			if newstatus.lower() == 'error':
				if 'fault' in dir(manager.get(objectid)):
					message = manager.get(objectid).fault['message']
					raise Exception(message)
				elif 'fail_reason' in dir(manager.get(objectid)):
                                        message = manager.get(objectid).fail_reason
                                        raise Exception(message)
				else:
					raise Exception('Error')
			time.sleep(0.2)
			if self.verbose > 1:
				if stack_name in dir(manager.get(objectid)):
					name = manager.get(objectid).stack_name
				else:
					name = manager.get(objectid).name
				print "Waiting for status %s on %s and object %s" % (status, manager.__class__.__name__, name)
			newstatus = manager.get(objectid).status
		return {'success':True}
	def _searchlog(self, server,search, timeout):
		timein = 0
		while True:
			log = server.get_console_output()
			if search in log:
        			break
			timein += 1
			if timein > timeout:
				return False
			time.sleep(0.5)
		return True
	def _deleted(self, manager, objectid, timeout):
		timein = 0
		while True:
			try:
				manager.get(objectid)
				timein += 0.2
				if timein > timeout:
					return False
				time.sleep(0.2)
				continue
			except (keystone_notfound, glance_notfound, cinder_notfound, nova_notfound, neutron_notfound, heat_notfound, ceilometer_notfound, swift_notfound):
				return True
	def _stackdeleted(self, manager, objectid, timeout):
		status = 'DELETE_COMPLETE'
		timein = 0
		while manager.get(objectid).stack_status != status:
			timein += 0.2
			if timein > timeout:
				return False
			time.sleep(0.2)
		return True

	def _nextcidr(self, neutron):
		cidrs = [ subnet['cidr'] for subnet in  neutron.list_subnets()['subnets'] ]
		while True:
        		i, j, k = random.randint(1,254), random.randint(1,254), random.randint(1,254)
        		cidr    = "%s.%s.%s.0/24" % (i, j, k)
        		if cidr not in cidrs:
                		break
		return cidr
	def _testservice(self, server, service, username='root', password=None, privatekey=None, timeout=60, stopcmd=None, statuscmd=None, startcmd=None):
		if password is None and privatekey is None:
			print "Missing hapassword and/or privatekeyfile. Set them as OS_HA_PASSWORD and OS_HA_PRIVATEKEY or on command line"
			return False
		if server is None:
			print "Missing haserver. Set them as OS_HA_SERVER or on command line"
			return False
		success   = False
		stopcmd   = stopcmd   if stopcmd   is not None else "sudo service %s stop"   % service 
		startcmd  = startcmd  if startcmd  is not None else "sudo service %s start"  % service 
		statuscmd = statuscmd if statuscmd is not None else "sudo service %s status" % service 
		pkey=None
		if privatekey is not None:
			password = None
			#privatekeyfile = StringIO.StringIO(privatekey)
			#pkey = paramiko.RSAKey.from_private_key(privatekey)
			pkey = paramiko.RSAKey.from_private_key_file(privatekey)
		ssh = paramiko.SSHClient()
		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		ssh.connect(server, username=username,password=password, pkey=pkey)
		stdin, stdout, stderr   = ssh.exec_command(stopcmd)
		timein = 0
		running = False
		while not running:
			timein += 0.2
			if timein > timeout :
				success = False
				break
			time.sleep(0.2)
			stdin, stdout, stderr   = ssh.exec_command(statuscmd)
			returncode = stdout.channel.recv_exit_status()
			if returncode == 0:
				success = True
				break
		stdin, stdout, stderr   = ssh.exec_command(startcmd)
		return success

	def Add_FlavorAccess(self, nova, flavor, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		try:
			tenant_id = nova.tenant_id
			nova.flavor_access.add_tenant_access(flavor, tenant_id)
			results = 'OK'
		except Exception as error:
			errors.append('Add_FlavorAccess')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Add_FlavorAccess: %s %s seconds %s" % (flavor, runningtime, results )
			output.append(['nova', 'Add_FlavorAccess', flavor, flavor, runningtime, results,])

	def Add_FloatingIP(self, nova, server, floatings, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if server is None:
			errors.append('Add_FloatingIP')
			results = 'NotRun'
			if verbose >0:
				print "Add_FloatingIP: %s 0 seconds" % 'N/A'
				output.append(['nova', 'Add_FloatingIP', 'N/A', 'N/A', '0', results,])
			return
		servername = server.name
		try:
			if self.externalnet is not None:
                		neutronendpoint = self.keystone.service_catalog.url_for(service_type='network',endpoint_type=self.endpoint)
                		neutron         = neutronclient.Client('2.0',endpoint_url=neutronendpoint, token=self.keystone.auth_token)
				externalnets        = [ n for n in neutron.list_networks()['networks'] if n['name'] == self.externalnet ]
				if externalnets:
					externalid  = externalnets[0]['id']
					floating_ip = nova.floating_ips.create(externalid)
					floatings.append(floating_ip.id)
					if self.verbose > 1:
						print "Add_FloatingIP: added %s" % floating_ip.ip
				else:
					raise Exception("External net %s not found" % self.externalnet)
			else:
				raise Exception('Missing External net.set OS_NEUTRON_EXTERNALNET env variable?')
			server.add_floating_ip(floating_ip)
			results = 'OK'
		except Exception as error:
			errors.append('Add_FloatingIP')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Add_FloatingIP: %s %s seconds %s" % (servername, runningtime, results)
			output.append(['nova', 'Add_FloatingIP', servername, servername, runningtime, results,])

	def Add_Role(self, keystone, user, role, tenant, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if tenant is None or user is None:
			errors.append('Add_Role')
			results = 'NotRun'
			if verbose >0:
				print "Add_Role: %s to %s 0 seconds" % ('N/A', 'N/A')
				output.append(['keystone', 'Add_Role', 'N/A', 'N/A', '0', results,])
			return
		try:
			keystone.roles.add_user_role(user, role, tenant)
			results = 'OK'
		except Exception as error:
			errors.append('Add_Role')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Add_Role: %s to %s %s seconds %s" % (role.name, user.name, runningtime, results)
			output.append(['keystone', 'Add_Role', role.name, role.name, runningtime, results,])

	def Attach_Volume(self, nova, server, attachedvolumes, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		cinder = cinderclient.Client(**self.novacredentials)
		if server is None:
			errors.append('Attach_Volume')
			results = 'NotRun'
			if verbose >0:
				print "Attach_Volume: %s 0 seconds" % 'N/A'
				output.append(['nova', 'Attach_Volume', 'N/A', 'N/A', '0', results,])
			return
		try:
			attachedvolume = cinder.volumes.create(size=1, name="attachedvolume-%s" % server.name)
			attachedvolumes.append(attachedvolume.id)
			o._available(cinder.volumes, attachedvolume.id, timeout)
			attachedvolume.attach(server.id,'vdb')
			o._available(nova.servers, server.id, timeout, status='ACTIVE')
			results = 'OK'
		except Exception as error:
			errors.append('Attach_Volume')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			output.append(['nova', 'Attach_Volume', server.name, server.name, runningtime, results,])

	def Authenticate_User(self, user, password, auth_url, tenant=None, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if user is None or tenant is None:
			errors.append('Authenticate_User')
			results = 'NotRun'
			if verbose >0:
				print "Authenticate_User: %s in %s 0 seconds" % ('N/A', 'N/A')
				output.append(['keystone', 'Authenticate_User', 'N/A', 'N/A', '0', results,])
			return
		try:
			usercredentials = { 'username' : user.name, 'password' : password, 'auth_url' : auth_url , 'tenant_name' : tenant.name }
			userkeystone = keystoneclient.Client(**usercredentials)
			results = 'OK'
		except Exception as error:
			errors.append('Authenticate_User')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Authenticate_User: %s in %s %s seconds %s" % (user.name, tenant.name, runningtime, results)
			output.append(['keystone', 'Authenticate_User', user.name, user.name, runningtime, results,])

	def Check_Console(self, nova, server, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if server is None:
			errors.append('Check_Console')
			results = 'NotRun'
			if verbose >0:
				print "Check_Console: %s 0 seconds" % 'N/A'
				output.append(['nova', 'Check_Console', 'N/A', 'N/A', '0', results,])
			return
		servername = server.name
		try:
			console = server.get_console_output()
			results = 'OK'
		except Exception as error:
			errors.append('Check_Console')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Check_Console: %s %s seconds %s" % (servername, runningtime, results)
			output.append(['nova', 'Check_Console', servername, servername, runningtime, results,])

	def Check_Novnc(self, nova, server, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if server is None:
			errors.append('Check_Novnc')
			results = 'NotRun'
			if verbose >0:
				print "Check_Novnc: %s 0 seconds" % 'N/A'
				output.append(['nova', 'Check_Novnc', 'N/A', 'N/A', '0', results,])
			return
		servername = server.name
		try:
			console = server.get_console_output()
			results = 'OK'
		except Exception as error:
			errors.append('Check_Novnc')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Check_Novnc: %s %s seconds %s" % (servername, runningtime, results)
			output.append(['nova', 'Check_Novnc', servername, servername, runningtime, results,])

	def Check_Connectivity(self, nova, server, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if server is None:
			errors.append('Check_Connectivity')
			results = 'NotRun'
			if verbose >0:
				print "Check_Connectivity: %s 0 seconds" % 'N/A'
				output.append(['nova', 'Check_Connectivity', 'N/A', 'N/A', '0', results,])
			return
		servername = server.name
		try:
                        #found = o._searchlog(server,'METADATA',timeout)
                        found = o._searchlog(server,servername,timeout)
                        if not found:
                                raise Exception("Timeout waiting for metadata")
			results = 'OK'
		except Exception as error:
			errors.append('Check_Connectivity')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Check_Connectivity: %s %s seconds %s" % (servername, runningtime, results)
			output.append(['nova', 'Check_Connectivity', servername, servername, runningtime, results,])

	def Check_SSH(self, nova, server, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if server is None:
			errors.append('Check_SSH')
			results = 'NotRun'
			if verbose >0:
				print "Check_SSH: %s 0 seconds" % 'N/A'
				output.append(['nova', 'Check_SSH', 'N/A', 'N/A', '0', results,])
			return
		servername = server.name
		try:
			floatingip = o._getfloatingip(nova.servers.get(server.id))
			if floatingip is None:
				raise Exception('Missing floating ip')
			privatekeyfile = StringIO.StringIO(self.private_key)
			pkey = paramiko.RSAKey.from_private_key(privatekeyfile)
			cmd='ls'
			ssh = paramiko.SSHClient()
			ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			ssh.connect(floatingip, username=self.clouduser, pkey=pkey)
			stdin, stdout, stder   = ssh.exec_command(cmd)
			results = 'OK'
		except Exception as error:
			errors.append('Check_SSH')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Check_SSH: %s %s seconds %s" % (servername, runningtime, results)
			output.append(['nova', 'Check_SSH', servername, servername, runningtime, results,])

	def Create_Alarm(self, ceilometer, alarm, alarms=None, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		try:
			newalarm = ceilometer.alarms.create(name=alarm, threshold=100, meter_name=alarm)
			alarms.append(newalarm.alarm_id)
			results = 'OK'
		except Exception as error:
			errors.append('Create_Alarm')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			alarms.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Alarm: %s %s seconds %s" % (alarm, runningtime, results )
			output.append(['ceilometer', 'Create_Alarm', alarm, alarm, runningtime, results,])
	def Create_Backup(self, cinder, volume, backups, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if volume is None:
			errors.append('Create_Backup')
			backups.append(None)
			results = 'NotRun'
			if verbose >0:
				print "Create_Backup: %s 0 seconds" % 'N/A'
				output.append(['cinder', 'Create_Backup', 'N/A', 'N/A', '0', results,])
			return
		backup = "backup-%s" % volume.name
		try:
			volume_id = volume.id
			o._available(cinder.volumes, volume_id, timeout)
			newbackup = cinder.backups.create(volume_id=volume_id, name=backup)
			backups.append(newbackup.id)
			results = 'OK'
                        o._available(cinder.backups, newbackup.id, timeout)
		except cinderexceptions.NoUniqueMatch:
			errors.append('Create_Backup')
			results = 'NoUniqueMatch'
			backups.append(None)
		except Exception as error:
			errors.append('Create_Backup')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			backups.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Backup: %s %s seconds %s" % (backup, runningtime, results )
			output.append(['cinder', 'Create_Backup', backup, backup, runningtime, results,])	
	def Create_Container(self, swift, container, containers=None, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		try:
			objdata = os.environ['OS_SWIFT_OBJECT_PATH']   if os.environ.has_key('OS_SWIFT_OBJECT_PATH')   else None
			if objdata is not None:
				objdata = open(objdata)  	
			else:
				objdata = 'This is openstuck test data' 
			
			objname = "%s-object" % (container)
			swift.put_container(container)			
			swift.put_object(container, objname, objdata)
			results = 'OK'
			containers.append(container)
		except Exception as error:
			errors.append('Create_Container')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			containers.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Container: %s %s seconds %s" % (container, runningtime, results )
			output.append(['swiftcontainer', 'Create_Container', container, container, runningtime, results,])	
			
	def Create_Flavor(self, nova, flavor, flavors=None, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		try:
			newflavor = nova.flavors.create(name=flavor,ram=512,vcpus=1,disk=1)
			results = 'OK'
			flavors.append(newflavor.id)
		except Exception as error:
			errors.append('Create_Flavor')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			flavors.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Flavor: %s %s seconds %s" % (flavor, runningtime, results )
			output.append(['nova', 'Create_Flavor', flavor, flavor, runningtime, results,])

	def Create_Image(self, glance, image, imagepath, images=None, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		try:
			if imagepath is None:
				raise Exception('Missing OS_GLANCE_IMAGE_PATH environment variable')
			newimage = glance.images.create(name=image, visibility='private', disk_format='qcow2',container_format='bare')
			with open(imagepath,'rb') as data:
				if self.verbose >0:
					print 'Uploading image'
				glance.images.upload(newimage.id, data)
			o._available(glance.images, newimage.id, timeout,status='active')
			results = 'OK'
			images.append(newimage.id)
		except Exception as error:
			errors.append('Create_Image')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			images.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Image: %s %s seconds %s" % (image, runningtime, results )
			output.append(['glance', 'Create_Image', image, image, runningtime, results,])
	def Create_KeyPair(self, nova, keypair, keypairs=None, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		try:
			newkeypair = nova.keypairs.create(keypair)
			results = 'OK'
			keypairs.append(newkeypair.id)
		except Exception as error:
			errors.append('Create_KeyPair')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			keypairs.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_KeyPair: %s %s seconds %s" % (keypair, runningtime, results )
			output.append(['nova', 'Create_KeyPair', keypair, keypair, runningtime, results,])

	def Create_Network(self, neutron, network, networks=None, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		try:
			newnetwork = {'name': network, 'admin_state_up': True}
			newnetwork = neutron.create_network({'network':newnetwork})
			results = 'OK'
			networks.append(newnetwork['network']['id'])
		except Exception as error:
			errors.append('Create_Network')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			networks.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Network: %s %s seconds %s" % (network, runningtime, results )
			output.append(['neutron', 'Create_Network', network, network, runningtime, results,])
	def Create_Role(self, keystone, name, roles=None, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		try:
			role = keystone.roles.create(name=name)
			results = 'OK'
			roles.append(role.id)
		except Exception as error:
			errors.append('Create_Role')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			roles.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Create_Role: %s %s seconds %s" % (name, runningtime, results)
			output.append(['keystone', 'Create_Role', name, name, runningtime, results,])
	def Create_Router(self, neutron, router, subnet, externalnet, routers=None, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if subnet is None:
			errors.append('Create_Router')
			results = 'NotRun'
			if verbose >0:
				output.append(['neutron', 'Create_Router', 'N/A', 'N/A', '0', results,])
			return
		subnetid  = subnet['id']
		try:
			newrouter = {'name':router}
			if externalnet:
				externalnets        = [ n for n in neutron.list_networks()['networks'] if n['name'] == externalnet ]
				if externalnets:
					externalid  = externalnets[0]['id']
					newrouter['external_gateway_info']= {"network_id": externalid, "enable_snat": True}
                        newrouter = neutron.create_router({'router':newrouter})
			routerid  = newrouter['router']['id']
			neutron.add_interface_router(routerid,{'subnet_id':subnetid } )
			results = 'OK'
			routers.append(routerid)
		except Exception as error:
			errors.append('Create_Router')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			routers.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Router: %s %s seconds %s" % (router, runningtime, results )
	def Create_SecurityGroup(self, neutron, securitygroup, securitygroups=None, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		try:
			newsecuritygroup = {'name': securitygroup}
			newsecuritygroup = neutron.create_security_group({'security_group':newsecuritygroup})
			results = 'OK'
			securitygroups.append(newsecuritygroup['security_group']['id'])
		except Exception as error:
			errors.append('Create_SecurityGroup')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			securitygroups.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_SecurityGroup: %s %s seconds %s" % (securitygroup, runningtime, results )
			output.append(['neutron', 'Create_SecurityGroup', securitygroup, securitygroup, runningtime, results,])

	def Create_Server(self, nova, server, servers=None, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		try:
			if not embedded:
				keypairname = None
				image       = os.environ['OS_NOVA_IMAGE']
				image       = nova.images.find(name=image)
				network     = os.environ['OS_NOVA_NETWORK']
				networkid   = nova.networks.find(label=network).id
				flavor      = os.environ['OS_NOVA_FLAVOR']
				flavor      = nova.flavors.find(name=flavor)
			else:
				flavorname  = "%s-flavor1" % self.project
				flavor      = nova.flavors.find(name=flavorname)
				keypairname = "%s-key" % self.project
				imagename   = "%s-image" % self.project
				image       = nova.images.find(name=imagename)
				networkname = "%s-net" % self.project
				networkid   = nova.networks.find(label=networkname).id
			nics = [{'net-id': networkid}]
			userdata = "#!/bin/bash\necho METADATA >/dev/ttyS0"
			newserver = nova.servers.create(name=server, image=image, flavor=flavor, nics=nics, key_name=keypairname, userdata=userdata)
			servers.append(newserver.id)
                        o._available(nova.servers, newserver.id, timeout, status='ACTIVE')
			results = 'OK'
		except Exception as error:
			errors.append('Create_Server')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			servers.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Server: %s %s seconds %s" % (server, runningtime, results )
			output.append(['nova', 'Create_Server', server, server, runningtime, results,])

	def Create_SnapshotServer(self, nova, server, servers=None, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		cinder = cinderclient.Client(**self.novacredentials)
		try:
			if not embedded:
				keypairname = None
				snapshot    = os.environ['OS_NOVA_SNAPSHOT']
				snapshot    = cinder.volume_snapshots.find(name=snapshot)
				network     = os.environ['OS_NOVA_NETWORK']
				networkid   = nova.networks.find(label=network).id
			else:
				flavorname    = "%s-flavor1" % self.project
				flavor        = nova.flavors.find(name=flavorname)
				keypairname   = "%s-key" % self.project
				snapshotname  = "%s-snapshot" % self.project
				snapshot      = cinder.volume_snapshots.find(name=snapshotname)
				networkname   = "%s-net" % self.project
				networkid     = nova.networks.find(label=networkname).id
			nics = [{'net-id': networkid}]
			userdata = "#!/bin/bash\necho METADATA >/dev/ttyS0"
			mapping = {'vda':"%s:snap::0" % snapshot.id}
			newserver = nova.servers.create(name=server, image='', block_device_mapping=mapping, flavor=flavor, nics=nics, key_name=keypairname, userdata=userdata)
			servers.append(newserver.id)
                        o._available(nova.servers, newserver.id, timeout, status='ACTIVE')
			results = 'OK'
		except Exception as error:
			errors.append('Create_SnapshotServer')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			servers.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_SnapshotServer: %s %s seconds %s" % (server, runningtime, results )
			output.append(['nova', 'Create_SnapshotServer', server, server, runningtime, results,])

	def Create_VolumeServer(self, nova, server, servers=None, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		cinder = cinderclient.Client(**self.novacredentials)
		try:
			if not embedded:
				keypairname = None
				volume      = os.environ['OS_NOVA_VOLUME']
				volume      = cinder.volumes.find(name=volume)
				network     = os.environ['OS_NOVA_NETWORK']
				networkid   = nova.networks.find(label=network).id
			else:
				flavorname  = "%s-flavor1" % self.project
				flavor      = nova.flavors.find(name=flavorname)
				keypairname = "%s-key" % self.project
				volumename  = "%s-volume" % self.project
				volume      = cinder.volumes.find(name=volumename)
				networkname = "%s-net" % self.project
				networkid   = nova.networks.find(label=networkname).id
			nics = [{'net-id': networkid}]
			userdata = "#!/bin/bash\necho METADATA >/dev/ttyS0"
			mapping = {'vda':volume.id}
			newserver = nova.servers.create(name=server, image='', block_device_mapping=mapping, flavor=flavor, nics=nics, key_name=keypairname, userdata=userdata)
			servers.append(newserver.id)
                        o._available(nova.servers, newserver.id, timeout, status='ACTIVE')
			results = 'OK'
		except Exception as error:
			errors.append('Create_VolumeServer')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			servers.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_VolumeServer: %s %s seconds %s" % (server, runningtime, results )
			output.append(['nova', 'Create_VolumeServer', server, server, runningtime, results,])


	def Create_Snapshot(self, cinder, volume, snapshots, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if volume is None:
			errors.append('Create_Snapshot')
			snapshots.append(None)
			results = 'NotRun'
			if verbose >0:
				output.append(['cinder', 'Create_Snapshot', 'N/A', 'N/A', '0', results,])
			return
		snapshot = "snapshot-%s" % volume.name
		try:
			volume_id = volume.id				
                        o._available(cinder.volumes, volume_id, timeout)
			newsnapshot = cinder.volume_snapshots.create(volume_id=volume_id, name=snapshot)
			snapshots.append(newsnapshot.id)
			results = 'OK'
                        o._available(cinder.volume_snapshots, newsnapshot.id, timeout)
		except cinderexceptions.NoUniqueMatch:
			errors.append('Create_Snapshot')
			results = 'NoUniqueMatch'
			snapshots.append(None)
		except Exception as error:
			errors.append('Create_Snapshot')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			snapshots.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Snapshot: %s %s seconds %s" % (snapshot, runningtime, results )
			output.append(['cinder', 'Create_Snapshot', snapshot, snapshot, runningtime, results,])	

	def Create_Stack(self, heat, stack, stacks=None, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		try:
			template  = os.environ['OS_HEAT_TEMPLATE']   if os.environ.has_key('OS_HEAT_TEMPLATE')   else None
			if template is None:
				if not embedded:
					image     = os.environ['OS_NOVA_IMAGE']
					network   = os.environ['OS_NOVA_NETWORK']
					flavor1   = os.environ['OS_NOVA']
				else:
					image     = "%s-image" % self.project
					network   = "%s-net" % self.project
					flavor1   = "%s-flavor1" % self.project
				stackinstance = "%sinstance" % stack
				template={'heat_template_version': '2013-05-23', 'description': 'Testing Template', 'resources': 
				 	{stackinstance: {'type': 'OS::Nova::Server', 'properties': {'image': image,
				 	'flavor': flavor1, 'networks': [{'network': network }]}}}}
				template = json.dumps(template)
			else:
				template = yaml.load(open(template))
				#for oldkey in template['resources'].keys():
				#	newkey = "%s%s" % (stack, oldkey)
				#	template['resources'][newkey]= template['resources'].pop(oldkey)
				#	del template['resources'][oldkey]
			newstack = heat.stacks.create(stack_name=stack, template=template)
			stacks.append(newstack['stack']['id'])
			o._available(heat.stacks, newstack['stack']['id'], timeout, status='COMPLETE')
			results = 'OK'
		except Exception as error:
			errors.append('Create_Stack')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			stacks.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Stack: %s %s seconds %s" % (stack, runningtime, results )
			output.append(['heat', 'Create_Stack', stack, stack, runningtime, results,])
	def Create_Subnet(self, neutron, subnet, network, cidr='10.0.0.0/24', subnets=None, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if network is None:
			errors.append('Create_Subnet')
			results = 'NotRun'
			if verbose >0:
				output.append(['neutron', 'Create_Subnet', 'N/A', 'N/A', '0', results,])
			return
		networkid  = network['id']
		try:
			newsubnet = {'name':subnet, 'network_id':networkid,'ip_version':4,"cidr":cidr}
                        newsubnet = neutron.create_subnet({'subnet':newsubnet})
			results = 'OK'
			subnets.append(newsubnet['subnet']['id'])
		except Exception as error:
			errors.append('Create_Subnet')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			subnets.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Subnet: %s %s seconds %s" % (subnet, runningtime, results )
			output.append(['neutron', 'Create_Subnet', subnet, subnet, runningtime, results,])
	def Create_Tenant(self, keystone, name, description, tenants=None, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		try:
			tenant = keystone.tenants.create(tenant_name=name, description=description,enabled=True)
			results = 'OK'
			tenants.append(tenant.id)
		except Exception as error:
			errors.append('Create_Tenant')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			tenants.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Tenant:%s %s seconds %s" % (name, runningtime, results)
			output.append(['keystone', 'Create_Tenant', name, name, runningtime, results,])
	def Create_TypedVolume(self, cinder, volume, volumetype, volumes=None, errors=None, output=None, verbose=0, timeout=20):
		if volumetype is None:
			results = 'Missing OS_CINDER_VOLUME_TYPE environment variable'
			volumes.append(None)
			if verbose >0:
				print "Create_TypedVolume: %s 0 seconds" % 'N/A'
				output.append(['cinder', 'Create_TypedVolume', 'N/A', 'N/A', '0', results,])
			return
		starttime = time.time()
		try:
			newvolume = cinder.volumes.create(size=1, name=volume, volume_type=volumetype)
			volumes.append(newvolume.id)
			results = 'OK'
                        o._available(cinder.volumes, newvolume.id, timeout)
		except Exception as error:
			errors.append('Create_TypedVolume')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			volumes.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_TypedVolume: %s %s seconds %s" % (volume, runningtime, results )
			output.append(['cinder', 'Create_TypedVolume', volume, volume, runningtime, results,])
	def Create_User(self, keystone, name, password, email,tenant, users=None, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if tenant is None:
			errors.append('Create_User')
			results = 'NotRun'
			users.append(None)
			if verbose >0:
				print "Create_User: %s 0 seconds" % 'N/A'
				output.append(['keystone', 'Create_User', 'N/A', 'N/A', '0', results,])
			return
		try:
			user = keystone.users.create(name=name, password=password, email=email, tenant_id=tenant.id)
			results = 'OK'
			users.append(user.id)
		except Exception as error:
			errors.append('Create_User')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			users.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_User: %s %s seconds %s" % (name, runningtime, results)
			output.append(['keystone', 'Create_User', name, name, runningtime, results,])
	def Create_Volume(self, cinder, volume, volumes=None, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		try:
			newvolume = cinder.volumes.create(size=1, name=volume)
			volumes.append(newvolume.id)
			o._available(cinder.volumes, newvolume.id, timeout)
			results = 'OK'
		except Exception as error:
			errors.append('Create_Volume')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			volumes.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Volume: %s %s seconds %s" % (volume, runningtime, results )
			output.append(['cinder', 'Create_Volume', volume, volume, runningtime, results,])			

	def Create_Volume_From_Snapshot(self, cinder, snapshot, snapshotvolumes=None, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if snapshot is None:
			errors.append('Create_Volume_From_Snapshot')
			results = 'NotRun'
			if verbose >0:
				print "Create_Volume_From_Snapshot: %s 0 seconds" % 'N/A'
				output.append(['cinder', 'Create_Volume_From_Snapshot', 'N/A', 'N/A', '0', results,])
			return
		volumename = "volume-from-%s" % snapshot.name
		try:
			snapshot_id = snapshot.id				
			snapshot_size = snapshot.size				
			newvolume = cinder.volumes.create(snapshot_id=snapshot_id, name=volumename, size=snapshot_size)
			snapshotvolumes.append(newvolume.id)
			results = 'OK'
                        o._available(cinder.volumes, newvolume.id, timeout)
		except Exception as error:
			errors.append('Create_Volume_From_Snapshot')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
			volumes.append(None)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Volume_From_Snapshot: %s %s seconds %s" % (volumename, runningtime, results )
			output.append(['cinder', 'Create_Volume_From_Snapshot', volumename, volumename, runningtime, results,])			
	def Delete_Alarm(self, ceilometer, alarm, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if alarm is None:
			errors.append('Delete_Alarm')
			results = 'NotRun'
			if verbose >0:
				print "Delete_Alarm: %s 0 seconds" % 'N/A'
				output.append(['ceilometer', 'Delete_Alarm', 'N/A', 'N/A', '0', results,])
			return
		alarmname = alarm.name
		try:
			ceilometer.alarms.delete(alarm.alarm_id)
			results = 'OK'
		except Exception as error:
			errors.append('Delete_Alarm')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Alarm: %s %s seconds %s" % (alarmname, runningtime, results)
			output.append(['ceilometer', 'Delete_Alarm', alarmname, alarmname, runningtime, results,])
	def Delete_Backup(self, cinder, backup, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if backup is None:
			errors.append('Delete_Backup')
			results = 'NotRun'
			if verbose >0:
				print "Delete_Backup: %s 0 seconds" % 'N/A'
				output.append(['cinder', 'Delete_Backup', 'N/A', 'N/A', '0', results,])
			return
		backupname = backup.name
		try:
			backup.delete()
			results = 'OK'
			deleted = o._deleted(cinder.backups, backup.id, timeout)
			if not deleted:
				results = 'Timeout waiting for deletion'
				errors.append('Delete_Backup')
			results = 'OK'
		except Exception as error:
		        print error
			errors.append('Delete_Backup')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Backup: %s %s seconds %s" % (backupname, runningtime, results)
			output.append(['cinder', 'Delete_Backup', backupname, backupname, runningtime, results,])		
	def Delete_Container(self, swift, container, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if container is None:
			errors.append('Delete_Container')
			results = 'NotRun'
			if verbose >0:
				print "Delete_Container: %s 0 seconds" % 'N/A'
				output.append(['swift', 'Delete_Container', 'N/A', 'N/A', '0', results,])
			return
		try:
			containerinfo = swift.get_container(container)
			objects = containerinfo[1]
			if len(objects) > 0:
        			for obj in objects:
                			swift.delete_object(container,obj['name'])
			swift.delete_container(container)
			results = 'OK'
		except Exception as error:
			errors.append('Delete_Container')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Container: %s %s seconds %s" % (container, runningtime, results)
			output.append(['swift', 'Delete_Container', container, container, runningtime, results,])
			
	def Delete_Flavor(self, nova, flavor, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if flavor is None:
			errors.append('Delete_Flavor')
			results = 'NotRun'
			if verbose >0:
				print "Delete_Flavor: %s 0 seconds" % 'N/A'
				output.append(['nova', 'Delete_Flavor', 'N/A', 'N/A', '0', results,])
			return
		flavorname = flavor.name
		try:
			nova.flavors.delete(flavor.id)
			results = 'OK'
		except Exception as error:
			errors.append('Delete_Flavor')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Flavor: %s %s seconds %s" % (flavorname, runningtime, results)
			output.append(['nova', 'Delete_Flavor', flavorname, flavorname, runningtime, results,])			

	def Delete_Image(self, glance, image, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if image is None:
			errors.append('Delete_Image')
			results = 'NotRun'
			if verbose >0:
				print "Delete_Image: %s 0 seconds" % 'N/A'
				output.append(['glance', 'Delete_Image', 'N/A', 'N/A', '0', results,])
			return
		imagename = image.name
		try:
			glance.images.delete(image.id)
			results = 'OK'
		except Exception as error:
			errors.append('Delete_Image')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Image: %s %s seconds %s" % (imagename, runningtime, results)
			output.append(['glance', 'Delete_Image', imagename, imagename, runningtime, results,])

	def Delete_KeyPair(self, nova, keypair, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if keypair is None:
			errors.append('Delete_KeyPair')
			results = 'NotRun'
			if verbose >0:
				print "Delete_KeyPair: %s 0 seconds" % 'N/A'
				output.append(['nova', 'Delete_KeyPair', 'N/A', 'N/A', '0', results,])
			return
		keypairname = keypair.name
		try:
			keypair.delete()
			results = 'OK'
		except Exception as error:
			errors.append('Delete_KeyPair')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_KeyPair: %s %s seconds %s" % (keypairname, runningtime, results)
			output.append(['nova', 'Delete_KeyPair', keypairname, keypairname, runningtime, results,])			

	def Delete_Network(self, neutron, network, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if network is None:
			errors.append('Delete_Network')
			results = 'NotRun'
			if verbose >0:
				print "Delete_Network: %s 0 seconds" % 'N/A'
				output.append(['neutron', 'Delete_Network', 'N/A', 'N/A', '0', results,])
			return
		networkname = network['name']
		networkid   = network['id']
		try:
			neutron.delete_network(networkid)
			results = 'OK'
		except Exception as error:
			errors.append('Delete_Network')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Network: %s %s seconds %s" % (networkname, runningtime, results)

	def Delete_SecurityGroup(self, neutron, securitygroup, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if securitygroup is None:
			errors.append('Delete_SecurityGroup')
			results = 'NotRun'
			if verbose >0:
				print "Delete_SecurityGroup: %s 0 seconds" % 'N/A'
				output.append(['neutron', 'Delete_SecurityGroup', 'N/A', 'N/A', '0', results,])
			return
		securitygroupname = securitygroup['name']
		securitygroupid   = securitygroup['id']
		try:
			neutron.delete_security_group(securitygroupid)
			results = 'OK'
		except Exception as error:
			errors.append('Delete_SecurityGroup')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_SecurityGroup: %s %s seconds %s" % (securitygroupname, runningtime, results)
			output.append(['neutron', 'Delete_SecurityGroup', securitygroupname, securitygroupname, runningtime, results,])
	def Delete_Role(self, keystone, role, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if role is None:
			results = 'NotRun'
			errors.append('Delete_Role')
			if verbose >0:
				print "Delete_Role: %s 0 seconds" % 'N/A'
				output.append(['keystone', 'Delete_Role', 'N/A', 'N/A', '0', results,])
			return
		rolename = role.name
		try:
			role.delete()
			results = 'OK'
		except Exception as error:
			errors.append('Delete_Role')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Role: %s %s seconds %s" % (rolename, runningtime, results)
			output.append(['keystone', 'Delete_Role', rolename, rolename, runningtime, results,])
	def Delete_Router(self, neutron, router, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if router is None:
			errors.append('Delete_Router')
			results = 'NotRun'
			if verbose >0:
				print "Delete_Router: %s 0 seconds" % 'N/A'
				output.append(['neutron', 'Delete_Router', 'N/A', 'N/A', '0', results,])
			return
		routerid     = router['id']
		routername   = router['name']
		try:
        		if router['external_gateway_info']:
                		neutron.remove_gateway_router(routerid)
        		ports = [ p for p in neutron.list_ports()['ports'] if p['device_id'] == routerid ]
        		for port in ports:
                		portid = port['id']
                		neutron.remove_interface_router(routerid, {'port_id':portid})
        		neutron.delete_router(routerid)
			results = 'OK'
		except Exception as error:
			errors.append('Delete_Router')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Router: %s %s seconds %s" % (routername, runningtime, results)
			output.append(['neutron', 'Delete_Router', routername, routername, runningtime, results,])
	def Delete_Server(self, nova, server, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if server is None:
			errors.append('Delete_Server')
			results = 'NotRun'
			if verbose >0:
				print "Delete_Server: %s 0 seconds" % 'N/A'
				output.append(['nova', 'Delete_Server', 'N/A', 'N/A', '0', results,])
			return
		servername = server.name
		try:
			server.delete()
			results = 'OK'
			deleted = o._deleted(nova.servers, server.id, timeout)
			if not deleted:
				results = 'Timeout waiting for deletion'
				errors.append('Delete_Server')
		except Exception as error:
			errors.append('Delete_Server')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Server: %s %s seconds %s" % (servername, runningtime, results)
			output.append(['nova', 'Delete_Server', servername, servername, runningtime, results,])
	def Delete_Snapshot(self, cinder, snapshot, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if snapshot is None:
			errors.append('Delete_Snapshot')
			results = 'NotRun'
			if verbose >0:
				print "Delete_Snapshot: %s 0 seconds" % 'N/A'
				output.append(['cinder', 'Delete_Snapshot', 'N/A', 'N/A', '0', results,])
			return
		snapshotid   = snapshot.id
		snapshotname = snapshot.name
		try:
			snapshot.delete()
			results = 'OK'
			deleted = o._deleted(cinder.volume_snapshots, snapshot.id, timeout)
			if not deleted:
				results = 'Timeout waiting for deletion'
				errors.append('Delete_Snapshot')
		except Exception as error:
			errors.append('Delete_Snapshot')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Snapshot: %s %s seconds %s" % (snapshotname, runningtime, results)
			output.append(['cinder', 'Delete_Snapshot', snapshotname, snapshotname, runningtime, results,])
			
	def Delete_Stack(self, heat, stack, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if stack is None:
			errors.append('Delete_Stack')
			results = 'NotRun'
			if verbose >0:
				print "Delete_Stack: %s 0 seconds" % 'N/A'
				output.append(['heat', 'Delete_Stack', 'N/A', 'N/A', '0', results,])
			return
		stackname = stack.stack_name
		stackid   = stack.id
		try:
			heat.stacks.delete(stackid)
			results = 'OK'
			deleted = o._stackdeleted(heat.stacks, stackid, timeout)
			if not deleted:
				raise Exception("Timeout waiting for deleted status")
			results = 'OK'
		except Exception as error:
			errors.append('Delete_Stack')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Stack: %s %s seconds %s" % (stackname, runningtime, results)
			output.append(['heat', 'Delete_Stack', stackname, stackname, runningtime, results,])

	def Delete_Subnet(self, neutron, subnet, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if subnet is None:
			errors.append('Delete_Subnet')
			results = 'NotRun'
			if verbose >0:
				print "Delete_Subnet: %s 0 seconds" % 'N/A'
				output.append(['neutron', 'Delete_Subnet', 'N/A', 'N/A', '0', results,])
			return
		subnetname = subnet['name']
		subnetid   = subnet['id']
		try:
			neutron.delete_subnet(subnetid)
			results = 'OK'
		except Exception as error:
			errors.append('Delete_Subnet')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Subnet: %s %s seconds %s" % (subnetname, runningtime, results)

	def Delete_Tenant(self, keystone, tenant, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if tenant is None:
			errors.append('Delete_Tenant')
			results = 'NotRun'
			if verbose >0:
				print "Delete_Tenant: %s 0 seconds" % 'N/A'
				output.append(['keystone', 'Delete_Tenant', 'N/A', 'N/A', '0', results,])
			return
		tenantname = tenant.name
		try:
			tenant.delete()
			results = 'OK'
		except Exception as error:
			errors.append('Delete_Tenant')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Delete_Tenant: %s %s seconds %s" % (tenantname, runningtime, results)
			output.append(['keystone', 'Delete_Tenant', tenantname, tenantname, runningtime, results,])
	def Delete_User(self, keystone, user, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if user is None:
			results = 'NotRun'
			errors.append('Delete_User')
			if verbose >0:
				print "Delete_User: %s 0 seconds" % 'N/A'
				output.append(['keystone', 'Delete_User', 'N/A', 'N/A', '0', results,])
			return
		username = user.name
		try:
			user.delete()
			results = 'OK'
		except Exception as error:
			errors.append('Delete_User')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Delete_User: %s %s seconds %s" % (username, runningtime, results)
			output.append(['keystone', 'Delete_User', username, username, runningtime, results,])
	def Delete_Volume(self, cinder, volume, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if volume is None:
			errors.append('Delete_Volume')
			results = 'NotRun'
			if verbose >0:
				print "Delete_Volume: %s 0 seconds" % 'N/A'
				output.append(['cinder', 'Delete_Volume', 'N/A', 'N/A', '0', results,])
			return
		volumename = volume.name
		try:
                        o._available(cinder.volumes, volume.id, timeout)
			volume.delete()
			results = 'OK'
			deleted = o._deleted(cinder.volumes, volume.id, timeout)
			if not deleted:
				results = 'Timeout waiting for deletion'
				errors.append('Delete_Volume')
		except Exception as error:
			errors.append('Delete_Volume')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Volume: %s %s seconds %s" % (volumename, runningtime, results)
			output.append(['cinder', 'Delete_Volume', volumename, volumename, runningtime, results,])

	def Detach_Volume(self, nova, server, attachedvolumes, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		cinder = cinderclient.Client(**self.novacredentials)
		if server is None:
			errors.append('Detach_Volume')
			results = 'NotRun'
			if verbose >0:
				print "Detach_Volume: %s 0 seconds" % 'N/A'
				output.append(['nova', 'Detach_Volume', 'N/A', 'N/A', '0', results,])
			return
		try:
			for volume in attachedvolumes:
				for attachment in volume.attachments:
					if server.id == attachment['server_id']:
						volume.detach()
						o._available(cinder.volumes, volume.id, timeout)
				o._available(nova.servers, server.id, timeout, status='ACTIVE')
			results = 'OK'
		except Exception as error:
			errors.append('Detach_Volume')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Detach_Volume: %s %s seconds %s" % (server.name, runningtime, results)
			output.append(['nova', 'Detach_Volume', server.name, server.name, runningtime, results,])

	def Grow_Server(self, nova, server, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if server is None:
			errors.append('Grow_Server')
			results = 'NotRun'
			if verbose >0:
				print "Grow_Server: %s 0 seconds" % 'N/A'
				output.append(['nova', 'Grow_Server', 'N/A', 'N/A', '0', results,])
			return
		try:
			flavor2 = nova.flavors.find(name="%s-flavor2" % self.project)
			server.resize(flavor2)
			o._available(nova.servers, server.id, timeout, status='RESIZE')
			results = 'OK'
		except Exception as error:
			errors.append('Grow_Server')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			output.append(['nova', 'Grow_Server', server.name, server.name, runningtime, results,])

	def Grow_Volume(self, cinder, volume, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if volume is None:
			results = 'NotRun'
			errors.append('Grow_Volume')
			if verbose >0:
				print "Grow_Volume: %s 0 seconds" % 'N/A'
				output.append(['cinder', 'Grow_Volume', 'N/A', 'N/A', '0', results,])
			return
		try:
			cinder.volumes.extend(volume.id,2)
			o._available(cinder.volumes, volume.id, timeout)
			results = 'OK'
		except Exception as error:
			errors.append('Grow_Volume')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Grow_Volume: %s %s seconds %s" % (volume.name, runningtime, results)
			output.append(['cinder', 'Grow_Volume', volume.name, volume.name, runningtime, results,])

	def List_Alarm(self, ceilometer, alarm, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if alarm is None:
			results = 'NotRun'
			errors.append('List_Alarm')
			if verbose >0:
				print "List_Alarm: %s 0 seconds" % 'N/A'
				output.append(['ceilometer', 'List_Alarm', 'N/A', 'N/A', '0', results,])
			return
		try:
			ceilometer.alarms.get(alarm.alarm_id)
			results = 'OK'
		except Exception as error:
			errors.append('List_Alarm')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Alarm: %s %s seconds %s" % (alarm.name, runningtime, results)
			output.append(['ceilometer', 'List_Alarm', alarm.name, alarm.name, runningtime, results,])
	def List_Backup(self, cinder, backup, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if backup is None:
			results = 'NotRun'
			errors.append('List_Backup')
			if verbose >0:
				print "List_Backup: %s 0 seconds" % 'N/A'
				output.append(['cinder', 'List_Backup', 'N/A', 'N/A', '0', results,])
			return
		try:
			cinder.backups.get(backup.id)
			results = 'OK'
		except Exception as error:
			errors.append('List_Backup')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Backup: %s %s seconds %s" % (backup.name, runningtime, results)
			output.append(['cinder', 'List_Backup', backup.name, backup.name, runningtime, results,])	
			
	def List_Flavor(self, nova, flavor, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if flavor is None:
			results = 'NotRun'
			errors.append('List_Flavor')
			if verbose >0:
				print "List_Flavor: %s 0 seconds" % 'N/A'
				output.append(['nova', 'List_Flavor', 'N/A', 'N/A', '0', results,])
			return
		try:
			nova.flavors.get(flavor.id)
			results = 'OK'
		except Exception as error:
			errors.append('List_Flavor')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Flavor: %s %s seconds %s" % (flavor.name, runningtime, results)
			output.append(['nova', 'List_Flavor', flavor.name, flavor.name, runningtime, results,])			
			
	def List_Container(self, swift, container, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if container is None:
			results = 'NotRun'
			errors.append('List_Container')
			if verbose >0:
				print "List_Container: %s 0 seconds" % 'N/A'
				output.append(['swift', 'List_Container', 'N/A', 'N/A', '0', results,])
			return
		try:
			swift.get_container(container)
			results = 'OK'
		except Exception as error:
			errors.append('List_Container')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Container: %s %s seconds %s" % (container, runningtime, results)
			output.append(['swift', 'List_Container', container, container, runningtime, results,])						
	def List_Image(self, glance, image, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if image is None:
			results = 'NotRun'
			errors.append('List_Image')
			if verbose >0:
				print "List_Image: %s 0 seconds" % 'N/A'
				output.append(['glance', 'List_Image', 'N/A', 'N/A', '0', results,])
			return
		try:
			glance.images.get(image.id)
			results = 'OK'
		except Exception as error:
			errors.append('List_Image')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Image: %s %s seconds %s" % (image.name, runningtime, results)
			output.append(['glance', 'List_Image', image.name, image.name, runningtime, results,])
	def List_KeyPair(self, nova, keypair, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if keypair is None:
			results = 'NotRun'
			errors.append('List_KeyPair')
			if verbose >0:
				print "List_KeyPair: %s 0 seconds" % 'N/A'
				output.append(['nova', 'List_KeyPair', 'N/A', 'N/A', '0', results,])
			return
		try:
			nova.keypairs.get(keypair.id)
			results = 'OK'
		except Exception as error:
			errors.append('List_KeyPair')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_KeyPair: %s %s seconds %s" % (keypair.name, runningtime, results)
			output.append(['nova', 'List_KeyPair', keypair.name, keypair.name, runningtime, results,])

	def List_Meter(self, ceilometer, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		try:
			meters = ceilometer.meters.list()	
			results = 'OK'
		except Exception as error:
			errors.append('List_Meter')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Meter: %s %s seconds %s" % ('meters', runningtime, results)
			output.append(['ceilometer', 'List_Meter', 'meters', 'meters', runningtime, results,])
	def List_Network(self, neutron, network, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if network is None:
			results = 'NotRun'
			errors.append('List_Network')
			if verbose >0:
				print "List_Network: %s 0 seconds" % 'N/A'
				output.append(['neutron', 'List_Network', 'N/A', 'N/A', '0', results,])
			return
		network_id   = network['id']
		network_name = network['name']
		try:
			findnetworks = [ net for net in neutron.list_networks()['networks'] if net['id'] == network_id ]
			if not findnetworks:
				raise Exception('Network not found')
			results = 'OK'
		except Exception as error:
			errors.append('List_Network')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Network: %s %s seconds %s" % (network_name, runningtime, results)
			output.append(['neutron', 'List_Network', network_name, network_name, runningtime, results,])
	def List_Role(self, keystone, role, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if role is None:
			results = 'NotRun'
			errors.append('List_Role')
			if verbose >0:
				print "List_Role: %s" % 'N/A'
				output.append(['keystone', 'List_Role', 'N/A', 'N/A', '0', results,])
			return
		try:
			keystone.roles.get(role.id)
			results = 'OK'
		except Exception as error:
			errors.append('List_Role')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Role: %s %s seconds %s" % (role.name, runningtime, results)
			output.append(['keystone', 'List_Role', role.name, role.name, runningtime, results,])
	def List_Server(self, nova, server, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if server is None:
			results = 'NotRun'
			errors.append('List_Server')
			if verbose >0:
				print "List_Server: %s 0 seconds" % 'N/A'
				output.append(['nova', 'List_Server', 'N/A', 'N/A', '0', results,])
			return
		server_id   = server.id
		server_name = server.name
		try:
			nova.servers.get(server_id)
			results = 'OK'
		except Exception as error:
			errors.append('List_Server')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Server: %s %s seconds %s" % (server_name, runningtime, results)
			output.append(['nova', 'List_Server', server_name, server_name, runningtime, results,])
	def List_Snapshot(self, cinder, snapshot, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if snapshot is None:
			results = 'NotRun'
			errors.append('List_Snapshot')
			if verbose >0:
				print "List_Snapshot: %s 0 seconds" % 'N/A'
				output.append(['cinder', 'List_Snapshot', 'N/A', 'N/A', '0', results,])
			return
		try:
			cinder.volume_snapshots.get(snapshot.id)
			results = 'OK'
		except Exception as error:
			errors.append('List_Snapshot')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Snapshot: %s %s seconds %s" % (snapshot.name, runningtime, results)
			output.append(['cinder', 'List_Snapshot', snapshot.name, snapshot.name, runningtime, results,])		
	def List_Stack(self, heat, stack, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if stack is None:
			results = 'NotRun'
			errors.append('List_Stack')
			if verbose >0:
				print "List_Stack: %s 0 seconds" % 'N/A'
				output.append(['heat', 'List_Stack', 'N/A', 'N/A', '0', results,])
			return	
		stackid   = stack.id
		stackname = stack.stack_name
		try:
			heat.stacks.get(stackid)
			results = 'OK'
		except Exception as error:
			errors.append('List_Stack')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Stack: %s %s seconds %s" % (stackname, runningtime, results)
			output.append(['heat', 'List_Stack', stackname, stackname, runningtime, results,])

	def List_Subnet(self, neutron, subnet, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if subnet is None:
			results = 'NotRun'
			errors.append('List_Subnet')
			if verbose >0:
				print "List_Subnet: %s 0 seconds" % 'N/A'
				output.append(['neutron', 'List_Subnet', 'N/A', 'N/A', '0', results,])
			return
		subnet_id   = subnet['id']
		subnet_name = subnet['name']
		try:
			found = [ subnet for subnet in neutron.list_subnets()['subnets'] if subnet['id'] == subnet_id ]
			if not found:
				raise Exception('Subnet not found')
			results = 'OK'
		except Exception as error:
			errors.append('List_Subnet')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Subnet: %s %s seconds %s" % (subnet_name, runningtime, results)
			output.append(['neutron', 'List_Subnet', subnet_name, subnet_name, runningtime, results,])
	def List_Router(self, neutron, router, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if router is None:
			results = 'NotRun'
			errors.append('List_Router')
			if verbose >0:
				print "List_Router: %s 0 seconds" % 'N/A'
				output.append(['neutron', 'List_Router', 'N/A', 'N/A', '0', results,])
			return
		router_id   = router['id']
		router_name = router['name']
		try:
			found = [ router for router in neutron.list_routers()['routers'] if router['id'] == router_id ]
			if not found:
				raise Exception('Router not found')
			results = 'OK'
		except Exception as error:
			errors.append('List_Router')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Router: %s %s seconds %s" % (router_name, runningtime, results)
			output.append(['neutron', 'List_Router', router_name, router_name, runningtime, results,])
	def List_Volume(self, cinder, volume, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if volume is None:
			results = 'NotRun'
			errors.append('List_Volume')
			if verbose >0:
				print "List_Volume: %s 0 seconds" % 'N/A'
				output.append(['cinder', 'List_Volume', 'N/A', 'N/A', '0', results,])
			return
		try:
			cinder.volumes.get(volume.id)
			results = 'OK'
		except Exception as error:
			errors.append('List_Volume')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Volume: %s %s seconds %s" % (volume.name, runningtime, results)
			output.append(['cinder', 'List_Volume', volume.name, volume.name, runningtime, results,])



	def Migrate_Server(self, nova, server, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if server is None:
			errors.append('Migrate_Server')
			results = 'NotRun'
			if verbose >0:
				print "Migrate_Server: %s 0 seconds" % 'N/A'
				output.append(['nova', 'Migrate_Server', 'N/A', 'N/A', '0', results,])
			return
		try:
			server.live_migrate()
			o._available(nova.servers, server.id, timeout, status='VERIFY_RESIZE')
			server.confirm_resize()
			o._available(nova.servers, server.id, timeout, status='ACTIVE')
			results = 'OK'
		except Exception as error:
			errors.append('Migrate_Server')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			output.append(['nova', 'Migrate_Server', server.name, server.name, runningtime, results,])

	def Reach_VolumeQuota(self, cinder, errors=None, output=None, verbose=0, timeout=20):
		quotavolumes = []
		errors = []
		starttime = time.time()
		try:
			maxvolumes = cinder.quotas.get(self.keystone.tenant_id).volumes
			currentvolumes = len(cinder.volumes.list())
			for  step in range(0,maxvolumes-currentvolumes+1):
				newvolume = cinder.volumes.create(size=1, name="%s-quotavolume" % self.project)
                        	o._available(cinder.volumes, newvolume.id, timeout)
				quotavolumes.append(newvolume)
			results = 'QuotaNotRespected'
			errors.append('Reach_StorageQuota')
		except cinderexceptions.OverLimit:
			results = 'OK'
		except Exception as error:
			errors.append('Reach_StorageQuota')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Reach_StorageQuota: %s seconds %s" % (runningtime, results )
			output.append(['cinder', 'Reach_StorageQuota', 'volumequota', 'volumequota', runningtime, results,])
		return quotavolumes
	def Reach_StorageQuota(self, cinder, errors=None, output=None, verbose=0, timeout=20):
		quotavolumes = []
		errors = []
		starttime = time.time()
		try:
			maxstorage = cinder.quotas.get(self.keystone.tenant_id).gigabytes
			newvolume = cinder.volumes.create(size=maxstorage+1, name="%s-quotastorage" % self.project)
                        o._available(cinder.volumes, newvolume.id, timeout)
			newvolume.delete()
			results = 'QuotaNotRespected'
			errors.append('Reach_StorageQuota')
		except cinderexceptions.OverLimit:
			results = 'OK'
		except Exception as error:
			errors.append('Reach_StorageQuota')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Reach_StorageQuota: %s seconds %s" % (runningtime, results )
			output.append(['cinder', 'Reach_StorageQuota', 'storagequota', 'storagequota', runningtime, results,])
	def Remove_FlavorAccess(self, nova, flavor, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		try:
			#THIS IS BUGGY
			tenant_id = nova.tenant_id
			nova.flavor_access.remove_tenant_access(flavor, tenant_id)
			results = 'OK'
		except Exception as error:
			errors.append('Remove_FlavorAccess')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Remove_FlavorAccess: %s %s seconds %s" % (flavor, runningtime, results )
			output.append(['nova', 'Remove_FlavorAccess', flavor, flavor, runningtime, results,])
	def Restore_Backup(self, cinder, backup, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if backup is None:
			results = 'NotRun'
			errors.append('Restore_Backup')
			if verbose >0:
				print "Restore_Backup: %s 0 seconds" % 'N/A'
				output.append(['cinder', 'Restore_Backup', 'N/A', 'N/A', '0', results,])
			return
		try:
			backup_id   = backup.id
			backup_name = backup.name
			cinder.restores.restore(backup_id)
                        o._available(cinder.backups, backup.id, timeout)
			results = 'OK'
		except Exception as error:
			errors.append('Restore_Backup')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Restore_Backup: %s %s seconds %s" % (backup_name, runningtime, results )
			output.append(['cinder', 'Restore_Backup', backup_name, backup_name, runningtime, results,])	

	def Shrink_Server(self, nova, server, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if server is None:
			errors.append('Shrink_Server')
			results = 'NotRun'
			if verbose >0:
				print "Shrink_Server: %s 0 seconds" % 'N/A'
				output.append(['nova', 'Shrink_Server', 'N/A', 'N/A', '0', results,])
			return
		try:
			flavor1 = nova.flavors.find("%s-flavor1" % self.project)
			server.resize(flavor1)
			o._available(nova.servers, server.id, timeout, status='RESIZE')
			results = 'OK'
		except Exception as error:
			errors.append('Shrink_Server')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			output.append(['nova', 'Shrink_Server', server.name, server.name, runningtime, results,])

	def Update_Stack(self, heat, stack, errors=None, output=None, verbose=0, timeout=20):
		starttime = time.time()
		if stack is None:
			results = 'NotRun'
			errors.append('Update_Stack')
			if verbose >0:
				print "Update_Stack: %s 0 seconds" % 'N/A'
				output.append(['heat', 'Update_Stack', 'N/A', 'N/A', '0', results,])
			return	
		stackid   = stack.id
		stackname = stack.stack_name
		try:
                        template  = os.environ['OS_HEAT_TEMPLATE']   if os.environ.has_key('OS_HEAT_TEMPLATE')   else None
                        if template is None:
                                if not embedded:
                                        image     = os.environ['OS_NOVA_IMAGE']   if os.environ.has_key('OS_NOVA_IMAGE')   else 'cirros'
                                        network   = os.environ['OS_NOVA_NETWORK'] if os.environ.has_key('OS_NOVA_NETWORK') else 'private'
                                        flavor2   = os.environ['OS_NOVA_FLAVOR']  if os.environ.has_key('OS_NOVA_FLAVOR')  else 'm1.small'
                                else:
                                        image     = "%s-image" % self.project
                                        network   = "%s-net" % self.project
                                        flavor2   = "%s-flavor2" % self.project
                                stackinstance = "%sinstance" % stack
                                template={'heat_template_version': '2013-05-23', 'description': 'Testing Template', 'resources':
                                        {stackinstance: {'type': 'OS::Nova::Server', 'properties': {'image': image,
                                        'flavor': flavor2, 'networks': [{'network': network }]}}}}
                                template = json.dumps(template)
                        else:
                                template = yaml.load(open(template))
                                #for oldkey in template['resources'].keys():
                                #       newkey = "%s%s" % (stack, oldkey)
                                #       template['resources'][newkey]= template['resources'].pop(oldkey)
                                #       del template['resources'][oldkey]

			stack.update(template)
			results = 'OK'
		except Exception as error:
			errors.append('Update_Stack')
			results = str(error) if len(str(error)) > 0 else str(type(error).__name__)
		if verbose >0:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Update_Stack: %s %s seconds %s" % (stackname, runningtime, results)

	def _printreport(self):
		return self.output
	def listservices(self, verbose=1):
		try:
			keystone = self.keystone
			output = PrettyTable(['Service', 'Type', 'Status'])
			output.align['Service'] = "l"
			for service in sorted(keystone.services.list(), key = lambda s: s.name):
				status = 'Available' if service.enabled else 'N/A'
				output.add_row([service.name, service.type, status])
			if verbose >0:
				print output
			return True
		except:
			return False
	def _fence(self,server, user, password, name, mode, timeout=20):
		mode = mode.lower()
		fence    = "fence_%s" % mode
		success = False
		if server is None or user is None or password is None or mode is None:
			print 'Missing environment FENCING variables'
			return False
		if mode in  ['brocade', 'cisco_ucs', 'docker', 'lpar', 'rhevm', 'vmware_soap'] :
			fencecmd = "%s -z -a %s -l %s -p %s -n %s -o" % (fence, server, user, password, name)
			startcmd = "%s on" % fencecmd
			stopcmd  = "%s off" % fencecmd 
		elif mode == 'fence_ovh':
			fencecmd = "%s -z -l %s -p %s -n %s -o" % (fence, server, user, password, name)
			startcmd = "%s on" % fencecmd
			stopcmd  = "%s off" % fencecmd 
		else:
			fencecmd = "fence_%s -z -a %s -l %s -p %s -o" % (mode, server, user, password)
			startcmd = "%s on" % fencecmd
			startcmd = "%s on" % fencecmd
			stopcmd  = "%s off" % fencecmd 
		#ADD MORE FENCING OPTION
		os.popen(stopcmd)
		timein = 0
                while not success:
                        timein += 0.2
                        if timein > timeout :
                                success = False
				os.popen(startcmd)
                                return False
                        time.sleep(0.2)
			running = self.listservices(verbose=0)
                        if running:
                                success = True
                                break
		os.popen(startcmd)
                return success

	def keystoneclean(self, tenants, users, roles):
		if self.verbose >0:
			print "Cleaning Keystone..."
		keystone = self.keystone
		for tenant in tenants:
			if tenant is None:
				continue
			else:
				try :
					tenant.delete()	
				except:
					continue
		for user in users:
			if user is None:
				continue
			else:
				try:
					user.delete()
				except:
					continue
		for role in roles:
			if role is None:
				continue
			else:
				try:
					role.delete()
				except:
					continue
	def glanceclean(self, images):
		if self.verbose >0:
			print "Cleaning Glance..."
		keystone = self.keystone
                endpoint = keystone.service_catalog.url_for(service_type='image',endpoint_type=self.endpoint)
                glance = glanceclient.Client(endpoint, token=keystone.auth_token)

		for image in images:
			if image is None:
				continue
			else:
				try:
					glance.images.delete(image.id)
				except:
					continue
	def cinderclean(self, volumes, snapshotvolumes, backups, snapshots, quotavolumes):
		if self.verbose >0:
			print "Cleaning Cinder..."
		keystone = self.keystone
		cinder = cinderclient.Client(**self.novacredentials)
		for volume in volumes:
			if volume is None:
				continue
			else:
				try:
					volume.delete()
				except:
					continue
		for volume in snapshotvolumes:
			if volume is None:
				continue
			else:
				try:
					volume.delete()
				except:
					continue
		for backup in backups:
			if backup is None:
				continue
			else:
				try:
					backup.delete()
				except:
					continue
		for snapshot in snapshots:
			if snapshot is None:
				continue
			else:
				try:
					snapshot.delete()
				except:
					continue
		for quotavolume in quotavolumes:
			if quotavolume is None:
				continue
			else:
				try:
					quotavolume.delete()
				except:
					continue

	def cinderbackupclean(self, backups):
		if self.verbose >0:
			print "Cleaning CinderBackup backup..."
		keystone = self.keystone
		cinder = cinderclient.Client(**self.novacredentials)
		for backup in backups:
			if backup is None:
				continue
			else:
				try:
					backup.delete()
				except:
					continue

	def neutronclean(self, securitygroups, networks, subnets, routers):
		if self.verbose >0:
			print "Cleaning Neutron..."
		keystone = self.keystone
		endpoint = keystone.service_catalog.url_for(service_type='network',endpoint_type=self.endpoint)
		neutron = neutronclient.Client('2.0',endpoint_url=endpoint, token=keystone.auth_token)
		for router in routers:
			if router is None:
				continue
			else:
				try:
					routerid     = router['id']
					routername   = router['name']
        				if router['external_gateway_info']:
                				neutron.remove_gateway_router(routerid)
        				ports = [ p for p in neutron.list_ports()['ports'] if p['device_id'] == routerid ]
        				for port in ports:
                				portid = port['id']
                				neutron.remove_interface_router(routerid, {'port_id':portid})
        				neutron.delete_router(routerid)
				except:
					continue
		for subnet in subnets:
			if subnet is None:
				continue
			else:
				try:
					neutron.subnets.delete(subnet['id'])
				except:
					continue
		for network in networks:
			if network is None:
				continue
			else:
				try:
					neutron.networks.delete(network['id'])
				except:
					continue
		for securitygroup in securitygroups:
			if securitygroup is None:
				continue
			else:
				try:
					neutron.security_groups.delete(securitygroup['id'])
				except:
					continue
	def novaclean(self, flavors, keypairs, servers, volumeservers, snapshotservers, attachedvolumes, floatings):
		if self.verbose >0:
			print "Cleaning Nova..."
		nova     = novaclient.Client('2', **self.novacredentials)
		for flavor in flavors:
			if flavors is None:
				continue
			else:
				try:
					nova.flavors.delete(flavor.id)
				except:
					continue
		for keypair in keypairs:
			if keypair is None:
				continue
			else:
				try:
					nova.keypairs.delete(keypair.id)
				except:
					continue
		for server in servers:
			if server is None:
				continue
			else:
				try:
					nova.servers.delete(server.id)
				except:
					continue
		for snapshotserver in snapshotservers:
			if snapshotserver is None:
				continue
			else:
				try:
					nova.servers.delete(snapshotserver.id)
				except:
					continue
		for volumeserver in volumeservers:
			if volumeserver is None:
				continue
			else:
				try:
					nova.servers.delete(volumeserver.id)
				except:
					continue
		for flavor in flavors:
			if flavor is None:
				continue
			else:
				try:
					nova.servers.delete(flavor.id)
				except:
					continue
		for attachedvolume in attachedvolumes:
			if attachedvolume is None:
				continue
			else:
				try:
					cinder.volume.delete(attachedvolume.id)
				except:
					continue
	def heatclean(self, stacks):
		if self.verbose >0:
			print "Cleaning Heat..."
		keystone = self.keystone
		endpoint = keystone.service_catalog.url_for(service_type='orchestration',endpoint_type=self.endpoint)
		heat = heatclient.Client('1', endpoint=endpoint, token=keystone.auth_token)
		for stack in stacks:
			if stack is None:
				continue
			else:
				try:
					heat.stacks.delete(stack.id)
				except:
					continue
	def ceilometerclean(self, alarms):
		if self.verbose >0:
			print "Cleaning Ceilometer..."
		os_username, os_password, os_tenant_name, os_auth_url = self.auth_username, self.auth_password, self.auth_tenant_name, self.auth_url
                ceilometer = ceilometerclient.get_client('2', os_username=os_username, os_password=os_password,  os_tenant_name=os_tenant_name, os_auth_url=os_auth_url)
		for alarm in alarms:
			if alarm is None:
				continue
			else:
				try:
					ceilometer.alarms.delete(alarm.id)
				except:
					continue
	def swiftclean(self, containers):
		if self.verbose >0:
			print "Cleaning Swift..."
		keystone      = self.keystone
                preauthurl   = keystone.service_catalog.url_for(service_type='object-store',endpoint_type=self.endpoint)
                user         = self.auth_username
                key          = self.auth_password
                tenant_name  = self.auth_tenant_name
                preauthtoken = keystone.auth_token
                swift        = swiftclient.Connection(preauthurl=preauthurl, user=user, preauthtoken=preauthtoken ,insecure=True,tenant_name=tenant_name)
		for container in containers:
			if container is None:
				continue
			else:
				try:
					containerinfo = swift.get_container(container)
                        		objects = containerinfo[1]
                        		if len(objects) > 0:
                        			for obj in objects:
                                			swift.delete_object(container,obj['name'])
                        		swift.delete_container(container)
				except:
					continue
	def keystonetest(self):
		category = 'keystone'
		timeout  = int(os.environ["OS_%s_TIMEOUT" % category.upper()]) if os.environ.has_key("OS_%s_TIMEOUT" % category.upper()) else self.timeout
		tests    = self.keystonetests
		mgr = multiprocessing.Manager()
		tenants = mgr.list()
		users   = mgr.list()
		roles   = mgr.list()
		errors  = mgr.list()
		if self.verbose >0:
			print "Testing Keystone..."
		keystone = self.keystone

                test    = 'Create_Tenant'
		reftest = test
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Tenant, args=(keystone, "%s-%d-%d" % (self.tenant, step,number), self.description, tenants, errors, output, self.verbose, timeout,)) for number in range(concurrency) ]
				self._process(jobs)
			endtime    = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			tenants = [ keystone.tenants.get(tenant_id) if tenant_id is not None else None for tenant_id in tenants]

		test    = 'Create_User'
		reftest = test
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_User, args=(keystone, "%s-%d-%d" % (self.user, step, number), self.password, self.email, self._first(tenants), users, errors, output, self.verbose, timeout,)) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			users = [ keystone.users.get(user_id) if user_id is not None else None for user_id in users ]

		test    = 'Create_Role'
		reftest = test
		if test in tests:
	        	test   = 'Create_Role'
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Role, args=(keystone, "%s-%d-%d" % (self.role, step, number), roles, errors, output, self.verbose, timeout, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			roles = [ keystone.roles.get(role_id) if role_id is not None else None for role_id in roles ]

		test    = 'Add_Role'
		reftest = 'Create_Role'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Add_Role, args=(keystone, self._first(users), role, self._first(tenants), errors, output, self.verbose, timeout, )) for role in roles ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'List_Role'
		reftest = 'Create_Role'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Role, args=(keystone, role, errors, output, self.verbose, timeout, )) for role in roles ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

	        test    = 'Authenticate_User'
		reftest = 'Create_User'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Authenticate_User, args=(user, self.password, self.auth_url, self._first(tenants), errors, output, self.verbose, timeout, )) for user in users ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Delete_User'
		reftest = 'Create_User'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_User, args=(keystone, user, errors, output, self.verbose, timeout, )) for user in users ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Delete_Role'
		reftest = 'Create_Role'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Role, args=(keystone, role, errors, output, self.verbose, timeout, )) for role in roles ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Delete_Tenant'
		reftest = 'Create_Tenant'
		if test in tests:
			output = mgr.list()
	                concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Tenant, args=(keystone, tenant, errors, output, self.verbose, timeout, )) for tenant in tenants ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
	
		return tenants, users, roles

	def glancetest(self):
		category = 'glance'
		timeout  = int(os.environ["OS_%s_TIMEOUT" % category.upper()]) if os.environ.has_key("OS_%s_TIMEOUT" % category.upper()) else self.timeout
		tests = self.glancetests
		mgr = multiprocessing.Manager()
		errors  = mgr.list()
		images = mgr.list()
		if self.verbose >0:
			print "Testing Glance..."
		keystone = self.keystone
		endpoint = keystone.service_catalog.url_for(service_type='image',endpoint_type=self.endpoint)
		glance = glanceclient.Client(endpoint, token=keystone.auth_token)


		test    = 'Create_Image'
		reftest = test
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Image, args=(glance, "%s-%d-%d" % (self.image, step, number), self.imagepath, images, errors, output, self.verbose, timeout, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			images = [ glance.images.get(image_id) if image_id is not None else None for image_id in images ]

		test    = 'List_Image'
		reftest = 'Create_Image'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Image, args=(glance, image, errors, output, self.verbose, timeout, )) for image in images ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

                test    = 'Delete_Image'
		reftest = 'Create_Image'
		if test in tests:
			output = mgr.list()
	                concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Image, args=(glance, image, errors, output, self.verbose, timeout, )) for image in images ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
	
		return images

	def cindertest(self):
		category        = 'cinder'
		timeout         = int(os.environ["OS_%s_TIMEOUT" % category.upper()]) if os.environ.has_key("OS_%s_TIMEOUT" % category.upper()) else self.timeout
		tests           = self.cindertests 
		mgr             = multiprocessing.Manager()
		errors          = mgr.list()
		volumes         = mgr.list()
		snapshotvolumes = mgr.list()
		backups         = mgr.list()
		snapshots       = mgr.list()
		quotavolumes    = []
		if self.verbose >0:
			print "Testing Cinder..."
		keystone = self.keystone
		cinder = cinderclient.Client(**self.novacredentials)
	
		test    = 'Create_Volume'
		reftest = test
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Volume, args=(cinder, "%s-%d-%d" % (self.volume, step, number), volumes, errors, output, self.verbose, timeout, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			volumes = [ cinder.volumes.get(volume_id) if volume_id is not None else None for volume_id in volumes ]

		test    = 'Create_Backup'
		reftest = 'Create_Volume'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Create_Backup, args=(cinder, volume, backups, errors, output, self.verbose, timeout, )) for volume in volumes ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			backups = [ cinder.backups.get(backup_id) if backup_id is not None else None for backup_id in backups ]
			
		test    = 'Create_Snapshot'
		reftest = 'Create_Volume'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Create_Snapshot, args=(cinder, volume, snapshots, errors, output, self.verbose, timeout, )) for volume in volumes ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			snapshots = [ cinder.volume_snapshots.get(snapshot_id) if snapshot_id is not None else None for snapshot_id in snapshots ]
			
		test    = 'Create_Volume_From_Snapshot'
		reftest = 'Create_Volume'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Create_Volume_From_Snapshot, args=(cinder, snapshot, snapshotvolumes, errors, output, self.verbose, timeout, )) for snapshot in snapshots ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			snapshotvolumes = [ cinder.volumes.get(volume_id) if volume_id is not None else None for volume_id in snapshotvolumes ]
			
		test    = 'Create_TypedVolume'
		reftest = test
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_TypedVolume, args=(cinder, "%s-%s-%d-%d" % (self.volume, self.volumetype, step, number), self.volumetype, volumes, errors, output, self.verbose, timeout, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Grow_Volume'
		reftest = 'Create_Volume'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Grow_Volume, args=(cinder, volume, errors, output, self.verbose, timeout, )) for volume in volumes ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'List_Volume'
		reftest = 'Create_Volume'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Volume, args=(cinder, volume, errors, output, self.verbose, timeout, )) for volume in volumes ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'List_Backup'
		reftest = 'Create_Volume'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Backup, args=(cinder, backup, errors, output, self.verbose, timeout, )) for backup in backups ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'List_Snapshot'
		reftest = 'Create_Volume'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Snapshot, args=(cinder, snapshot, errors, output, self.verbose, timeout, )) for snapshot in snapshots ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Delete_Snapshot'
		reftest = 'Create_Volume'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Snapshot, args=(cinder, snapshot, errors, output, self.verbose, timeout, )) for snapshot in snapshots ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Restore_Backup'
		reftest = 'Create_Volume'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Restore_Backup, args=(cinder, backup, errors, output, self.verbose, timeout, )) for backup in backups ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

                test    = 'Delete_Backup'
		reftest = 'Create_Volume'
                if test in tests:
                        output = mgr.list()
                        concurrency, repeat = metrics(reftest)
                        starttime = time.time()
                        jobs = [ multiprocessing.Process(target=self.Delete_Backup, args=(cinder, backup, errors, output, self.verbose, timeout, )) for backup in backups ]
                        self._process(jobs)
                        endtime = time.time()
                        runningtime = "%0.3f" % (endtime -starttime)
                        if verbose >0:
                                print "%s  %s seconds" % (test, runningtime)
                        self._report(category, test, concurrency, repeat, runningtime, errors)
                        self._addrows(verbose, output)

                test    = 'Delete_Volume'
		reftest = 'Create_Volume'
                if test in tests:
                        output = mgr.list()
                        concurrency, repeat = metrics(reftest)
                        starttime = time.time()
                        jobs = [ multiprocessing.Process(target=self.Delete_Volume, args=(cinder, volume, errors, output, self.verbose, timeout, )) for volume in volumes ]
                        self._process(jobs)
                        endtime = time.time()
                        runningtime = "%0.3f" % (endtime -starttime)
                        if verbose >0:
                                print "%s  %s seconds" % (test, runningtime)
                        self._report(category, test, concurrency, repeat, runningtime, errors)
                        self._addrows(verbose, output)

		test    = 'Reach_VolumeQuota'
		if test in tests:
			output       = []
			errors       = []
                	concurrency, repeat = 1, 1
			starttime = time.time()
			quotavolumes = self.Reach_VolumeQuota(cinder)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors=[])
			self._addrows(verbose, output)

		test    = 'Reach_StorageQuota'
		if test in tests:
			output       = []
			errors       = []
                	concurrency, repeat = 1, 1
			starttime = time.time()
			self.Reach_StorageQuota(cinder)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors=[])
			self._addrows(verbose, output)
		return volumes, snapshotvolumes, backups, snapshots, quotavolumes
	def neutrontest(self):
		category       = 'neutron'
		timeout        = int(os.environ["OS_%s_TIMEOUT" % category.upper()]) if os.environ.has_key("OS_%s_TIMEOUT" % category.upper()) else self.timeout
		tests          = self.neutrontests 
		mgr            = multiprocessing.Manager()
		errors         = mgr.list()
		securitygroups = mgr.list()
		networks       = mgr.list()
		subnets        = mgr.list()
		routers        = mgr.list()
		if self.verbose >0:
			print "Testing Neutron..."
		keystone = self.keystone
		endpoint = keystone.service_catalog.url_for(service_type='network',endpoint_type=self.endpoint)
		neutron = neutronclient.Client('2.0',endpoint_url=endpoint, token=keystone.auth_token)

		test    = 'Create_SecurityGroup'
		reftest = test
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_SecurityGroup, args=(neutron, "%s-%d-%d" % (self.securitygroup, step, number), securitygroups, errors, output, self.verbose, timeout, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			securitygroups = [ securitygroup if securitygroup is not None else None for securitygroup in neutron.list_security_groups()['security_groups'] if securitygroup['id'] in securitygroups ]

		test    = 'Create_Network'
		reftest = test
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Network, args=(neutron, "%s-%d-%d" % (self.network, step, number), networks, errors, output, self.verbose, timeout, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			networks = [ network if network is not None else None for network in neutron.list_networks()['networks'] if network['id'] in networks ]

		test    = 'List_Network'
		reftest = 'Create_Network'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Network, args=(neutron, network, errors, output, self.verbose, timeout, )) for network in networks ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Create_Subnet'
		reftest = 'Create_Network'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Subnet, args=(neutron, "%s-%d-%d" % (self.subnet, step, number), self._first(networks), self._nextcidr(neutron), subnets, errors, output, self.verbose, timeout, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			subnets = [ subnet if subnet is not None else None for subnet in neutron.list_subnets()['subnets'] if subnet['id'] in subnets ]

		test    = 'List_Subnet'
		reftest = 'Create_Subnet'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Subnet, args=(neutron, subnet, errors, output, self.verbose, timeout, )) for subnet in subnets ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Create_Router'
		reftest = 'Create_Network'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Create_Router, args=(neutron, "%s-%d-%d" % (self.router, step, number), subnet, self.externalnet,  routers, errors, output, self.verbose, timeout, )) for subnet in subnets ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			routers = [ router if router is not None else None for router in neutron.list_routers()['routers'] if router['id'] in routers ]

		test    = 'List_Router'
		reftest = 'Create_Router'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Router, args=(neutron, router, errors, output, self.verbose, timeout, )) for router in routers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Delete_Router'
		reftest = 'Create_Network'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Router, args=(neutron, router, errors, output, self.verbose, timeout, )) for router in routers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Delete_Subnet'
		reftest = 'Create_Network'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Subnet, args=(neutron, subnet, errors, output, self.verbose, timeout, )) for subnet in subnets ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Delete_Network'
		reftest = 'Create_Network'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Network, args=(neutron, network, errors, output, self.verbose, timeout, )) for network in networks ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)

		test    = 'Delete_SecurityGroup'
		reftest = 'Create_SecurityGroup'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_SecurityGroup, args=(neutron, securitygroup, errors, output, self.verbose, timeout, )) for securitygroup in securitygroups ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)

		return securitygroups, networks, subnets, routers
	def novatest(self):
		category        = 'nova'
		timeout         = int(os.environ["OS_%s_TIMEOUT" % category.upper()]) if os.environ.has_key("OS_%s_TIMEOUT" % category.upper()) else self.timeout
		tests           = self.novatests 
		mgr             = multiprocessing.Manager()
		errors          = mgr.list()
		keypairs        = mgr.list()
		flavors         = mgr.list()
		servers         = mgr.list()
		snapshotservers = mgr.list()
		volumeservers   = mgr.list()
		attachedvolumes = mgr.list()
		floatings       = mgr.list()
		if self.verbose >0:
			print "Testing Nova..."
		keystone = self.keystone
		nova = novaclient.Client('2', **self.novacredentials)
		cinder = cinderclient.Client(**self.novacredentials)
		
		test    = 'Create_Flavor'
		reftest = test
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Flavor, args=(nova, "%s-%d-%d" % (self.flavor, step, number), flavors, errors, output, self.verbose, timeout, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			flavors = [ nova.flavors.get(flavor_id) if flavor_id is not None else None for flavor_id in flavors ]

		test    = 'List_Flavor'
		reftest = 'Create_Flavor'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Flavor, args=(nova, flavor, errors, output, self.verbose, timeout, )) for flavor in flavors ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Delete_Flavor'
		reftest = 'Create_Flavor'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Flavor, args=(nova, flavor, errors, output, self.verbose, timeout, )) for flavor in flavors ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Add_FlavorAccess'
		reftest = test
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Add_FlavorAccess, args=(nova, flavor, errors, output, self.verbose, timeout, )) for flavor in flavors ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
	
		test    = 'Remove_FlavorAccess'
		reftest = test
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Remove_FlavorAccess, args=(nova, flavor, errors, output, self.verbose, timeout, )) for flavor in flavors ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Create_KeyPair'
		reftest = test
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_KeyPair, args=(nova, "%s-%d-%d" % (self.keypair, step, number), keypairs, errors, output, self.verbose, timeout, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			keypairs = [ nova.keypairs.get(keypair_id) if keypair_id is not None else None for keypair_id in keypairs ]

		test    = 'List_KeyPair'
		reftest = 'Create_KeyPair'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_KeyPair, args=(nova, keypair, errors, output, self.verbose, timeout, )) for keypair in keypairs ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Delete_KeyPair'
		reftest = 'Create_KeyPair'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_KeyPair, args=(nova, keypair, errors, output, self.verbose, timeout, )) for keypair in keypairs ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Create_Server'
		reftest = test
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Server, args=(nova, "%s-%d-%d" % (self.server, step, number), servers, errors, output, self.verbose, timeout, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			servers = [ nova.servers.get(server_id) if server_id is not None else None for server_id in servers ]

		test    = 'List_Server'
		reftest = 'Create_Server'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Server, args=(nova, server, errors, output, self.verbose, timeout, )) for server in servers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Check_Console'
		reftest = 'Create_Server'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Check_Console, args=(nova, server, errors, output, self.verbose, timeout, )) for server in servers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Check_Novnc'
		reftest = 'Create_Server'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Check_Novnc, args=(nova, server, errors, output, self.verbose, timeout, )) for server in servers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Check_Connectivity'
		reftest = 'Create_Server'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Check_Connectivity, args=(nova, server, errors, output, self.verbose, timeout, )) for server in servers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Add_FloatingIP'
		reftest = 'Create_Server'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Add_FloatingIP, args=(nova, server, floatings, errors, output, self.verbose, timeout, )) for server in servers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			floatings = [ nova.floating_ips.get(floating_id) if floating_id is not None else None for floating_id in floatings ]

		test    = 'Check_SSH'
		reftest = 'Create_Server'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Check_SSH, args=(nova, server, errors, output, self.verbose, timeout, )) for server in servers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Grow_Server'
		reftest = 'Create_Server'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Grow_Server, args=(nova, server, errors, output, self.verbose, timeout, )) for server in servers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Shrink_Server'
		reftest = 'Create_Server'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Shrink_Server, args=(nova, server, errors, output, self.verbose, timeout, )) for server in servers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)

		test    = 'Migrate_Server'
		reftest = 'Create_Server'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Migrate_Server, args=(nova, server, errors, output, self.verbose, timeout, )) for server in servers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)

		test    = 'Create_SnapshotServer'
		reftest = test
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_SnapshotServer, args=(nova, "%s-%d-%d" % (self.snapshotserver, step, number), snapshotservers, errors, output, self.verbose, timeout, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			snapshotservers = [ nova.servers.get(server_id) if server_id is not None else None for server_id in snapshotservers ]

		test    = 'Create_VolumeServer'
		reftest = test
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_VolumeServer, args=(nova, "%s-%d-%d" % (self.volumeserver, step, number), volumeservers, errors, output, self.verbose, timeout, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			volumeservers = [ nova.servers.get(server_id) if server_id is not None else None for server_id in volumeservers ]

		test    = 'Attach_Volume'
		reftest = 'Create_Server'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Attach_Volume, args=(nova, server, attachedvolumes, errors, output, self.verbose, timeout, )) for server in servers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
		attachedvolumes = [ cinder.volumes.get(volume_id) if volume_id is not None else None for volume_id in attachedvolumes ]

		test    = 'Detach_Volume'
		reftest = 'Create_Server'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Detach_Volume, args=(nova, server, attachedvolumes, errors, output, self.verbose, timeout, )) for server in servers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._addrows(verbose, output)
			self._report(category, test, concurrency, repeat, runningtime, errors)

		test    = 'Delete_Server'
		reftest = 'Create_Server'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Server, args=(nova, server, errors, output, self.verbose, timeout, )) for server in servers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
		return flavors, keypairs, servers, volumeservers, snapshotservers, attachedvolumes, floatings

	def heattest(self):
		category = 'heat'
		timeout  = int(os.environ["OS_%s_TIMEOUT" % category.upper()]) if os.environ.has_key("OS_%s_TIMEOUT" % category.upper()) else self.timeout
		tests = self.heattests 
		mgr = multiprocessing.Manager()
		errors  = mgr.list()
		stacks = mgr.list()
		if self.verbose >0:
			print "Testing Heat..."
		keystone = self.keystone
		endpoint = keystone.service_catalog.url_for(service_type='orchestration',endpoint_type=self.endpoint)
		heat = heatclient.Client('1', endpoint=endpoint, token=keystone.auth_token)
	
		test    = 'Create_Stack'
		reftest = test
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Stack, args=(heat, "%s-%d-%d" % (self.stack, step, number), stacks, errors, output, self.verbose, timeout, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			stacks = [ heat.stacks.get(stack_id) if stack_id is not None else None for stack_id in stacks ]

		test    = 'List_Stack'
		reftest = 'Create_Stack'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Stack, args=(heat, stack, errors, output, self.verbose, timeout, )) for stack in stacks ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Update_Stack'
		reftest = 'Create_Stack'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Update_Stack, args=(heat, stack, errors, output, self.verbose, timeout, )) for stack in stacks ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Delete_Stack'
		reftest = 'Create_Stack'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Stack, args=(heat, stack, errors, output, self.verbose, timeout, )) for stack in stacks ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
		return stacks
	def ceilometertest(self):
		category = 'ceilometer'
		timeout  = int(os.environ["OS_%s_TIMEOUT" % category.upper()]) if os.environ.has_key("OS_%s_TIMEOUT" % category.upper()) else self.timeout
		tests = self.ceilometertests 
		mgr = multiprocessing.Manager()
		errors  = mgr.list()
		alarms = mgr.list()
		if self.verbose >0:
			print "Testing Ceilometer..."
		os_username, os_password, os_tenant_name, os_auth_url = self.auth_username, self.auth_password, self.auth_tenant_name, self.auth_url
		ceilometer = ceilometerclient.get_client('2', os_username=os_username, os_password=os_password,  os_tenant_name=os_tenant_name, os_auth_url=os_auth_url)
	
		test    = 'Create_Alarm'
		reftest = test
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Alarm, args=(ceilometer, "%s-%d-%d" % (self.alarm, step, number), alarms, errors, output, self.verbose, timeout, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			alarms = [ ceilometer.alarms.get(alarm_id) if alarm_id is not None else None for alarm_id in alarms ]

		test    = 'List_Alarm'
		reftest = 'Create_Alarm'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Alarm, args=(ceilometer, alarm, errors, output, self.verbose, timeout, )) for alarm in alarms ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'List_Meter'
		reftest = test
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.List_Meter, args=(ceilometer, errors, output, self.verbose, timeout, ))]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Delete_Alarm'
		reftest = 'Create_Alarm'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Alarm, args=(ceilometer, alarm, errors, output, self.verbose, timeout, )) for alarm in alarms ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
		return alarms
	def swifttest(self):
		category = 'swift'
		timeout  = int(os.environ["OS_%s_TIMEOUT" % category.upper()]) if os.environ.has_key("OS_%s_TIMEOUT" % category.upper()) else self.timeout
		tests = self.swifttests 
		mgr = multiprocessing.Manager()
		errors  = mgr.list()
		containers = mgr.list()
		if self.verbose >0:
			print "Testing Swift..."
		keystone     = self.keystone
		preauthurl   = keystone.service_catalog.url_for(service_type='object-store',endpoint_type=self.endpoint)
		user         = self.auth_username
		key          = self.auth_password
		tenant_name  = self.auth_tenant_name
		preauthtoken = keystone.auth_token
		swift        = swiftclient.Connection(preauthurl=preauthurl, user=user, preauthtoken=preauthtoken ,insecure=True,tenant_name=tenant_name)

		test    = 'Create_Container'
		reftest = test
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Container, args=(swift, "%s-%d-%d" % (self.container, step, number), containers, errors, output, self.verbose, timeout, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'List_Container'
		reftest = 'Create_Container'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Container, args=(swift, container, errors, output, self.verbose, timeout, )) for container in containers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Delete_Container'
		reftest = 'Create_Container'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Container, args=(swift, container, errors, output, self.verbose, timeout, )) for container in containers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
		return containers

	def hatest(self):
		category = 'ha'
		timeout  = int(os.environ["OS_%s_TIMEOUT" % category.upper()]) if os.environ.has_key("OS_%s_TIMEOUT" % category.upper()) else self.timeout
		errors   = []
		tests = self.hatests
		if self.verbose >0:
			print "Testing HA..."
		privatekey = None

		test    = 'Fence_Node'
		reftest = test
		if test in tests:
			starttime = time.time()
			if self.verbose >0:
				print "Running Fence_Controller"
			for index, server in enumerate(self.hafenceservers):
				user     = self.hafenceusers[index]
				password = self.hafencepasswords[index]
				mode     = self.hafencemodes[index]
				name     = self.hafencenames[index]
				starttime = time.time()
				success = o._fence(server, user, password, name, mode, timeout=timeout)
				errors = [] if success else [test]
				endtime = time.time()
				runningtime = "%0.3f" % (endtime -starttime)
				if verbose >0:
					print "%s  %s seconds" % (test, runningtime)
				self._report(category, "%s on %s" % (test,name) , '1', '1', runningtime, errors)
				#self._addrows(verbose, output)
				if self.hafencewait > 0:
					time.sleep(self.hafencewait)

		test    = 'Stop_Mysql'
		reftest = test
		service = 'mysqld'
		if test in tests:
			starttime = time.time()
			if verbose >0:
				print "Running Stop_Mysql"
			success = o._testservice(self.haserver, service, username=self.hauser, password=self.hapassword, privatekey=self.haprivatekey, timeout=timeout)
			errors = [] if success else [test]
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, '1', '1', runningtime, errors)

		test    = 'Stop_Amqp'
		reftest = test
		service = self.haamqp
		if test in tests:
			starttime = time.time()
			if verbose >0:
				print "Running Stop_Amqp"
			success = o._testservice(self.haserver, service, username=self.hauser, password=self.hapassword, privatekey=self.haprivatekey, timeout=timeout)
			errors = [] if success else [test]
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, '1', '1', runningtime, errors)

		test    = 'Stop_Mongodb'
		reftest = test
		service = 'mongod'
		if test in tests:
			starttime = time.time()
			if verbose >0:
				print "Running Stop_Mongodb"
			success = o._testservice(self.haserver, service, username=self.hauser, password=self.hapassword, privatekey=self.haprivatekey, timeout=timeout)
			errors = [] if success else [test]
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, '1', '1', runningtime, errors)

		test      = 'Stop_Keystone'
		reftest   = test
		service   = 'openstack-keystone'
		if test in tests:
			starttime = time.time()
			if verbose >0:
				print "Running Stop_Keystone"
			success = o._testservice(self.haserver, service, username=self.hauser, password=self.hapassword, privatekey=self.haprivatekey, timeout=timeout)
			errors = [] if success else [test]
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, '1', '1', runningtime, errors)

		test      = 'Stop_Glance'
		reftest   = test
		service   = 'openstack-glance-api'
		if test in tests:
			starttime = time.time()
			if verbose >0:
				print "Running Stop_Glance"
			success = o._testservice(self.haserver, service, username=self.hauser, password=self.hapassword, privatekey=self.haprivatekey, timeout=timeout)
			errors = [] if success else [test]
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, '1', '1', runningtime, errors)

		test      = 'Stop_Cinder'
		reftest   = test
		service   = 'openstack-cinder-api'
		if test in tests:
			starttime = time.time()
			if verbose >0:
				print "Running Stop_Cinder"
			success = o._testservice(self.haserver, service, username=self.hauser, password=self.hapassword, privatekey=self.haprivatekey, timeout=timeout)
			errors = [] if success else [test]
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, '1', '1', runningtime, errors)

		test      = 'Stop_Neutron'
		reftest   = test
		service   = 'neutron-server'
		if test in tests:
			starttime = time.time()
			if verbose >0:
				print "Running Stop_Neutron"
			success = o._testservice(self.haserver, service, username=self.hauser, password=self.hapassword, privatekey=self.haprivatekey, timeout=timeout)
			errors = [] if success else [test]
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, '1', '1', runningtime, errors)

		test      = 'Stop_Nova'
		reftest   = test
		service   = 'openstack-nova-api'
		if test in tests:
			starttime = time.time()
			if verbose >0:
				print "Running Stop_Nova"
			success = o._testservice(self.haserver, service, username=self.hauser, password=self.hapassword, privatekey=self.haprivatekey, timeout=timeout)
			errors = [] if success else [test]
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, '1', '1', runningtime, errors)

		test      = 'Stop_Heat'
		reftest   = test
		service   = 'openstack-heat-api'
		if test in tests:
			starttime = time.time()
			if verbose >0:
				print "Running Stop_Heat"
			success = o._testservice(self.haserver, service, username=self.hauser, password=self.hapassword, privatekey=self.haprivatekey, timeout=timeout)
			errors = [] if success else [test]
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, '1', '1', runningtime, errors)


		test      = 'Stop_Ceilometer'
		reftest   = test
		service   = 'openstack-ceilometer-api'
		if test in tests:
			starttime = time.time()
			if verbose >0:
				print "Running Stop_Ceilometer"
			success = o._testservice(self.haserver, service, username=self.hauser, password=self.hapassword, privatekey=self.haprivatekey, timeout=timeout)
			errors = [] if success else [test]
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, '1', '1', runningtime, errors)


		test      = 'Stop_Swift'
		reftest   = test
		service   = 'openstack-swift-proxy'
		if test in tests:
			starttime = time.time()
			if verbose >0:
				print "Running Stop_Swift"
			success = o._testservice(self.haserver, service, username=self.hauser, password=self.hapassword, privatekey=self.haprivatekey, timeout=timeout)
			errors = [] if success else [test]
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose >0:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, '1', '1', runningtime, errors)

if __name__ == "__main__":
	#parse options
	usage   = "test openstack installation quickly"
	version = "0.99"
	parser  = optparse.OptionParser("Usage: %prog [options] ",version=version)
	listinggroup = optparse.OptionGroup(parser, 'Listing options')
	listinggroup.add_option('-l', '--listservices', dest='listservices', action='store_true', help='List available services')
	parser.add_option_group(listinggroup)
	testinggroup = optparse.OptionGroup(parser, 'Testing options')
	testinggroup.add_option('-A', '--availability', dest='testha', action='store_true',default=False, help='Test High Availability')
        testinggroup.add_option('-C', '--cinder', dest='testcinder', action='store_true',default=False, help='Test Cinder')
	testinggroup.add_option('-G', '--glance', dest='testglance', action='store_true',default=False, help='Test Glance')
	testinggroup.add_option('-H', '--heat', dest='testheat', action='store_true',default=False, help='Test Heat')
	testinggroup.add_option('-K', '--keystone', dest='testkeystone', action='store_true',default=False, help='Test Keystone')
	testinggroup.add_option('-N', '--nova', dest='testnova', action='store_true',default=False, help='Test Nova')
	testinggroup.add_option('-Q', '--neutron', dest='testneutron', action='store_true',default=False, help='Test Neutron')
	testinggroup.add_option('-S', '--swift', dest='testswift', action='store_true',default=False, help='Test Swift')
	testinggroup.add_option('-X', '--ceilometer', dest='testceilometer', action='store_true',default=False, help='Test Ceilometer')
	testinggroup.add_option('-Z', '--all', dest='testall', action='store_true',default=False, help='Test All')
	parser.add_option_group(testinggroup)
	novagroup = optparse.OptionGroup(parser, 'Nova Flavor Testing options')
	novagroup.add_option('-d', '--disk', dest='disk', default='20', type='int', help='Flavor Disk for nova tests. Defaults to env[NOVA_DISK] or 20 otherwise')
	novagroup.add_option('-r', '--ram', dest='ram', default='512', type='int', help='Flavor Memory for nova tests. Defaults to env[NOVA_RAM] or 512 otherwise')
	novagroup.add_option('--cpus', dest='cpus', default='1', type='int', help='Flavor Cpus for nova tests. Defaults env[NOVA_CPUS] or 1 otherwise')
	parser.add_option_group(novagroup)
	hagroup = optparse.OptionGroup(parser, 'Nova Flavor Testing options')
	hagroup.add_option('-1', '--haserver', dest='haserver', type='string', help='Haserver to HA tests. Defaults to env[OS_HA_SERVER]')
	hagroup.add_option('-2', '--hauser', dest='hauser', default='root', type='string', help='Hauser to HA tests. Defaults to env[OS_HA_USER]')
	hagroup.add_option('-3', '--hapassword', dest='hapassword', type='string', help='Hapassword for ha tests. Defaults to env[OS_HA_PASSWORD]')
	hagroup.add_option('-4', dest='haprivatekey', type='string', help='Ha privatekey file. Defaults env[OS_HA_PRIVATEKEY]')
	parser.add_option_group(hagroup)
	parser.add_option('-i', '--info', dest='info', default=False, action='store_true', help='Print current environment variables values')
	parser.add_option('-p', '--project', dest='project', default='acme', type='string', help='Project name to prefix for all elements. Defaults to acme')
	parser.add_option('-t', '--timeout', dest='timeout', default=80, type='int', help='Timeout when waiting for a ressource to be available. Defaults to env[OS_TIMEOUT] or 80 otherwise')
	parser.add_option('-w', '--fencewait', dest='hafencewait', default=0, type='int', help='Time to wait between fence steps. Defaults to env[OS_HA_FENCEWAIT] or 0 otherwise')
	parser.add_option('-u', '--clouduser', dest='clouduser', default='root', type='string', help='User for Check_SSH test. Defaults to root')
	parser.add_option('-v', '--verbose', dest='verbose', action='count', default=0, help='Verbose mode. Defaults to False')
	parser.add_option('-e', '--embedded', dest='embedded', default=False, action='store_true', help='Create a dedicated tenant to hold all tests. Defaults to True')
	(options, args)  = parser.parse_args()
	listservices     = options.listservices
	testkeystone     = options.testkeystone
	testglance       = options.testglance
	testceilometer   = options.testceilometer
	testcinder       = options.testcinder
	testneutron      = options.testneutron
	testnova         = options.testnova
	testheat         = options.testheat
	testswift        = options.testswift
	testha           = options.testha
	testall          = options.testall
	project          = options.project
	verbose          = options.verbose
	info             = options.info
	clouduser        = options.clouduser
	timeout          = options.timeout
	ram              = options.ram
	cpus             = options.cpus
	disk             = options.disk
	embedded         = options.embedded
	hafencewait	 = options.hafencewait
	haserver	 = options.haserver
	hauser		 = options.hauser
	hapassword	 = options.hapassword
	haprivatekey	 = options.haprivatekey
	try:
		keystonecredentials = _keystonecreds()
		novacredentials     = _novacreds()
		endpoint            = os.environ['OS_ENDPOINT_TYPE']                 if os.environ.has_key('OS_ENDPOINT_TYPE')       else 'publicURL'
		keystonetests       = os.environ['OS_KEYSTONE_TESTS'].split(',')     if os.environ.has_key('OS_KEYSTONE_TESTS')      else keystonedefaulttests
		glancetests         = os.environ['OS_GLANCE_TESTS'].split(',')       if os.environ.has_key('OS_GLANCE_TESTS')        else glancedefaulttests
		cindertests         = os.environ['OS_CINDER_TESTS'].split(',')       if os.environ.has_key('OS_CINDER_TESTS')        else cinderdefaulttests
		neutrontests        = os.environ['OS_NEUTRON_TESTS'].split(',')      if os.environ.has_key('OS_NEUTRON_TESTS')       else neutrondefaulttests
		novatests           = os.environ['OS_NOVA_TESTS'].split(',')         if os.environ.has_key('OS_NOVA_TESTS')          else novadefaulttests
		heattests           = os.environ['OS_HEAT_TESTS'].split(',')         if os.environ.has_key('OS_HEAT_TESTS')          else heatdefaulttests
		swifttests          = os.environ['OS_SWIFT_TESTS'].split(',')        if os.environ.has_key('OS_SWIFT_TESTS')         else swiftdefaulttests
		ceilometertests     = os.environ['OS_CEILOMETER_TESTS'].split(',')   if os.environ.has_key('OS_CEILOMETER_TESTS')    else ceilometerdefaulttests
		hatests             = os.environ['OS_HA_TESTS'].split(',')           if os.environ.has_key('OS_HA_TESTS')            else hadefaulttests
		imagepath           = os.environ['OS_GLANCE_IMAGE_PATH']             if os.environ.has_key('OS_GLANCE_IMAGE_PATH')   else None
		imagesize           = int(os.environ['OS_GLANCE_IMAGE_SIZE'])        if os.environ.has_key('OS_GLANCE_IMAGE_SIZE')   else 10
		volumetype          = os.environ['OS_CINDER_VOLUME_TYPE']            if os.environ.has_key('OS_CINDER_VOLUME_TYPE')  else None
		externalnet         = os.environ['OS_NEUTRON_EXTERNALNET']           if os.environ.has_key('OS_NEUTRON_EXTERNALNET') else None
		timeout             = int(os.environ['OS_TIMEOUT'])                  if os.environ.has_key('OS_TIMEOUT')             else timeout
		ram                 = int(os.environ['OS_NOVA_RAM'])                 if os.environ.has_key('OS_NOVA_RAM')            else ram
		cpus                = int(os.environ['OS_NOVA_CPUS'])                if os.environ.has_key('OS_NOVA_CPUS')           else cpus
		disk                = int(os.environ['OS_NOVA_DISK'])                if os.environ.has_key('OS_NOVA_DISK')           else disk
		haserver            = os.environ['OS_HA_SERVER']                     if os.environ.has_key('OS_HA_SERVER')           else haserver
		hauser              = os.environ['OS_HA_USER']                       if os.environ.has_key('OS_HA_USER')             else hauser
		hapassword          = os.environ['OS_HA_PASSWORD']                   if os.environ.has_key('OS_HA_PASSWORD')         else hapassword
		haprivatekey        = os.environ['OS_HA_PRIVATEKEY']                 if os.environ.has_key('OS_HA_PRIVATEKEY')       else haprivatekey
		haamqp              = os.environ['OS_HA_AMQP']                       if os.environ.has_key('OS_HA_AMQP')             else 'rabbitmq-server'
		hafencewait         = int(os.environ['OS_HA_FENCEWAIT'])             if os.environ.has_key('OS_HA_FENCEWAIT')        else hafencewait
		hafenceservers      = os.environ['OS_HA_FENCESERVERS'].split(',')    if os.environ.has_key('OS_HA_FENCESERVERS')     else None
		hafencenames        = os.environ['OS_HA_FENCENAMES'].split(',')      if os.environ.has_key('OS_HA_FENCENAMES')       and hafenceservers is not None else None
		hafenceusers	    = os.environ['OS_HA_FENCEUSERS'].split(',')	     if os.environ.has_key('OS_HA_FENCEUSERS')       and hafenceservers is not None else None
		hafencepasswords    = os.environ['OS_HA_FENCEPASSWORDS'].split(',')  if os.environ.has_key('OS_HA_FENCEPASSWORDS')   and hafenceservers is not None  else None
		hafencemodes	    = os.environ['OS_HA_FENCEMODES'].split(',')	     if os.environ.has_key('OS_HA_FENCEMODES')       and hafenceservers is not None else None

	except Exception as e:
		print "Missing environment variables. source your openrc file first"
		print e
	    	os._exit(1)
	if info:
		categories = ['OS_KEYSTONE_TESTS', 'OS_GLANCE_TESTS', 'OS_CINDER_TESTS', 'OS_NEUTRON_TESTS', 'OS_NOVA_TESTS', 'OS_HEAT_TESTS', 'OS_CEILOMETER_TESTS', 'OS_SWIFT_TESTS','OS_HA_TESTS']
		for key in sorted(os.environ):
			if key in ['OS_TENANT_NAME', 'OS_USERNAME', 'OS_PASSWORD', 'OS_AUTH_URL', 'OS_REGION_NAME', 'OS_USERNAME'] or key in categories:
				continue
			if key.startswith('OS_'):
				print "%s=%s" % (key,os.environ[key])
		for category in categories:
			if category in os.environ.keys():
				tests = os.environ[category].split(',')
			else:
				cat   = category.split('_')[1].lower()
				tests = eval("%sdefaulttests" % cat)
			print "%s=%s" % (category,','.join(tests))
			for test in tests:	
				if os.environ.has_key(test):
					metric = os.environ[test]
				else:
					metric = '1:1'
				print "%s=%s" % (test,metric)
		sys.exit(0)	
	if listservices or testha:
		embedded = False
	if testkeystone or testglance or testcinder or testneutron or testnova or testheat or testceilometer or testswift or testha or testall or listservices:
		o = Openstuck(keystonecredentials=keystonecredentials, novacredentials=novacredentials, endpoint=endpoint, project= project, imagepath=imagepath, imagesize=imagesize, volumetype=volumetype, keystonetests=keystonetests, glancetests=glancetests, cindertests=cindertests, neutrontests=neutrontests, novatests=novatests, heattests=heattests, ceilometertests=ceilometertests, swifttests=swifttests, hatests=hatests, verbose=verbose, timeout=timeout, embedded=embedded, externalnet=externalnet, clouduser=clouduser, ram=ram, cpus=cpus, disk=disk, haamqp=haamqp, haserver=haserver, hauser=hauser, hapassword=hapassword, haprivatekey=haprivatekey, hafenceservers=hafenceservers, hafencenames=hafencenames, hafenceusers=hafenceusers, hafencepasswords=hafencepasswords, hafencemodes=hafencemodes , hafencewait=hafencewait)
	if listservices:
		if o.admin:
			o.listservices()
		else:
			print 'Admin required to list services'
	    	sys.exit(0)
	if testkeystone or testall:
		tenants, users, roles = o.keystonetest()
	if testglance or testall:
		images = o.glancetest()
	if testcinder or testall:
		volumes, snapshotvolumes, backups, snapshots, quotavolumes = o.cindertest()
	if testneutron or testall:
		securitygroups, networks, subnets, routers = o.neutrontest()
	if testnova or testall:
		if embedded:
			if imagepath is None or not os.path.isfile(imagepath):
				print "Incorrect OS_GLANCE_IMAGE_PATH environment variable"
				o._novaafter()
				o._clean()
				sys.exit(1)
		try:
			image, volume, snapshot = False, False, False
			if 'Create_Server' in o.novatests:
				image = True
			if 'Create_VolumeServer' in o.novatests:
				image  = True
				volume = True
			if 'Create_SnapshotServer' in o.novatests:
				image   = True
				volume  = True
				snapshot= True
			o._novabefore(externalnet=externalnet, image=image, volume=volume, snapshot=snapshot)
		except Exception as e:	
			print e
			o._novaafter()
			o._clean()
			sys.exit(1)
		flavors, keypairs, servers, volumeservers, snapshotservers, attachedvolumes, floatings = o.novatest()
	if testheat or testall:
		#if o.embedded:
		o._novabefore(externalnet=externalnet, image=True, volume=False, snapshot=False)
		stacks = o.heattest()
	if testceilometer or testceilometer:
		alarms = o.ceilometertest()
	if testswift or testall:
		containers = o.swifttest()
	if testha or testall:
		o.hatest()
	#cleaning
	if testkeystone or testall:
                o.keystoneclean(tenants, users, roles)
	if testglance or testall:
		o.glanceclean(images)
	if testcinder or testall:
		o.cinderclean(volumes, snapshotvolumes, backups, snapshots, quotavolumes)
	if testneutron or testall:
		o.neutronclean(securitygroups, networks, subnets, routers)
	if testnova or testall:
		o.novaclean(flavors, keypairs, servers, volumeservers, snapshotservers, attachedvolumes, floatings)
	if testheat or testall:
		o.heatclean(stacks)
	if testceilometer or testceilometer:
		o.ceilometerclean(alarms)
	if testswift or testall:
		o.swiftclean(containers)
	#reporting
	if testkeystone or testglance or testcinder or testneutron or testnova or testheat or testceilometer or testswift or testha or testall:
		if verbose >0:
			print "Testing Keystone..."
			print "Final report:"
		print o._printreport()
		#if embedded:	
		if testnova or testheat:
			o._novaafter()
		o._clean()
