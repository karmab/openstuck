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
import time
import yaml
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
novadefaulttests         = ['Create_Flavor','List_Flavor', 'Delete_Flavor', 'Create_KeyPair', 'List_KeyPair', 'Delete_KeyPair', 'Create_Server', 'List_Server', 'Check_Console', 'Check_Novnc', 'Check_Metadata', 'Delete_Server']
heatdefaulttests         = ['Create_Stack', 'List_Stack', 'Delete_Stack']
ceilometerdefaulttests   = ['Create_Alarm', 'List_Alarm', 'List_Meter', 'Delete_Alarm']
swiftdefaulttests        = ['Create_Container', 'List_Container', 'Delete_Container']

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
	def __init__(self, keystonecredentials, novacredentials, project='', endpoint='publicURL', keystonetests=None, glancetests=None, cindertests=None, neutrontests=None, novatests=None, heattests=None, ceilometertests=None, swifttests=None, imagepath=None, volumetype=None, debug=False,verbose=True, timeout=60, embedded=True, externalid=None):
		self.auth_username    = keystonecredentials['username']
		self.auth_password    = keystonecredentials['password']
		self.auth_tenant_name = keystonecredentials['tenant_name']
		self.auth_url         = keystonecredentials['auth_url']
		self.debug            = debug
		self.novacredentials  = novacredentials
		self.embedded	      = embedded
		self.externalid	      = externalid
		try:
			self.keystone = keystoneclient.Client(**keystonecredentials)
			if embedded:
				embeddedtenant = self.keystone.tenants.create(tenant_name=project, enabled=True)
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
		self.output            = PrettyTable(['Category', 'Description', 'Concurrency', 'Repeat', 'Time(Seconds)', 'Result'])
		self.output.align      = "l"
		self.endpoint          = endpoint
        	self.tenant            = "%stenant" % project
        	self.user              = "%suser" % project
        	self.password          = "%spassword" % project
        	self.role              = "%srole" % project
        	self.tenant            = "%stenant" % project
        	self.email             = "%suser@xxx.com" % project
        	self.description       = "Members of the %s corp" % project
        	self.image             = "%simage" % project
		self.imagepath         = imagepath
        	self.volume            = "%svolume" % project
        	self.volumetype        = volumetype
        	self.securitygroup     = "%ssecuritygroup" % project
        	self.network           = "%snetwork" % project
        	self.subnet            = "%ssubnet" % project
        	self.router            = "%srouter" % project
        	self.server            = "%sserver" % project
        	self.flavor            = "%sflavor" % project
        	self.keypair           = "%skeypair" % project
        	self.stack             = "%sstack" % project
        	self.alarm             = "%salarm" % project
        	self.container         = "%scontainer" % project
		self.debug            = debug
		self.verbose          = verbose
		self.timeout          = timeout
	def _novabefore(self, externalid):
		tenantid        = self.auth_tenant_id
		novaimage	= 'novaimage'
		novanet		= 'novanet'
		novasubnet	= 'novasubnet'
		novarouter	= 'novarouter'
		novakey	        = 'novakey'
		pubkey='ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDYgUh2XWv5EcWsrKq7fcmZLy/V9//MZtRGv+RDYSW0X6TZLOAw2xLTXkmZbKfo9P8DWyCXlptCgB8BuJhORY3dZFxUfcjgM5cbqB+64qlHdr9sxGfb5WDdc+4mpMEMSpfIgPwFda9bXmOimeLV9NaH+TLNCCs7uSig+t3eeDcFNgAbhMo0ffud4h4OHIaYEuPVnlA5lfDkY3qYboDPaqPs3qhbIOf5Q4AoCaxSQGXRUWTDQyQO8NNFiF9dfHTYb8rRW9BXLVCWXpfxyRJZzgGc1GLqmRNPjfY0DMDAD/D6qAxtVjEQYNCm5LiJMGq6BDVejdypKRYAoCU+KCmQ6xWr'
		imagepath       = self.imagepath
		keystone        = self.keystone
		nova            = novaclient.Client('2', **self.novacredentials)
                glanceendpoint  = keystone.service_catalog.url_for(service_type='image',endpoint_type=self.endpoint)
                glance          = glanceclient.Client(glanceendpoint, token=keystone.auth_token)
                neutronendpoint = keystone.service_catalog.url_for(service_type='network',endpoint_type=self.endpoint)
                neutron         = neutronclient.Client('2.0',endpoint_url=neutronendpoint, token=keystone.auth_token)
		keypairs        = [ keypair for keypair in nova.keypairs.list() if keypair.name == novakey]
		if len(keypairs) != 1:
			keypair = nova.keypairs.create(novakey, pubkey)
		images = [ image for image in glance.images.list() if image.name == novaimage]
		if len(images) != 1:
			image           = glance.images.create(name=novaimage, visibility='public', disk_format='qcow2',container_format='bare')
			with open(imagepath,'rb') as data:
				glance.images.upload(image.id, data)
			available = o._available(glance.images, image.id, timeout,status='active')
			if not available:
				raise Exception("Timeout waiting for available status")
		novanets        = [ n for n in neutron.list_networks()['networks'] if n['name'] == novanet ]
		if not novanets:
			network         = {'name': novanet, 'admin_state_up': True, 'tenant_id': tenantid}
			network         = neutron.create_network({'network':network})
			networkid       = network['network']['id']
		else:
			networkid  = novanets[0]['id']
		novasubnets     = [ n for n in neutron.list_subnets()['subnets'] if n['name'] == novasubnet ]
		if not novasubnets:
			subnet          = {'name':novasubnet, 'network_id':networkid,'ip_version':4,"cidr":'10.0.0.0/24', 'tenant_id': tenantid}
			subnet          = neutron.create_subnet({'subnet':subnet})
			subnetid        = subnet['subnet']['id']
		novarouters     = [ r for r in neutron.list_routers()['routers'] if n['name'] == novarouter ]
		if not novarouters:
			router          = {'name':novarouter, 'tenant_id': tenantid}
			if externalid is not None:
			        router['external_gateway_info']= {"network_id": externalid, "enable_snat": True}
			router    = neutron.create_router({'router':router})
			routerid  = router['router']['id']
			neutron.add_interface_router(routerid,{'subnet_id':subnetid } )
		return 
	def _novaafter(self):
		novaimage	= 'novaimage'
		novakey	        = 'novakey'
		novanet		= 'novanet'
		novasubnet	= 'novasubnet'
		novarouter	= 'novarouter'
                keystone        = self.keystone
                glanceendpoint  = keystone.service_catalog.url_for(service_type='image',endpoint_type=self.endpoint)
                glance          = glanceclient.Client(glanceendpoint, token=keystone.auth_token)
                neutronendpoint = keystone.service_catalog.url_for(service_type='network',endpoint_type=self.endpoint)
                neutron         = neutronclient.Client('2.0',endpoint_url=neutronendpoint, token=keystone.auth_token)
		nova            = novaclient.Client('2', **self.novacredentials)
		keypairs        = [ keypair for keypair in nova.keypairs.list() if keypair.name == novakey]
		if len(keypairs) == 1:
			keypair = keypairs[0]
			keypair.delete()
		images = [ image for image in glance.images.list() if image.name == novaimage]
		for image in images:
       	 		imageid = image.id
			glance.images.delete(imageid)
		routers = [ router for router in neutron.list_routers()['routers'] if router['name'] == novarouter]
		for router in routers:
        		routerid = router['id']
                        if router['external_gateway_info']:
                        	neutron.remove_gateway_router(routerid)
                        ports = [ p for p in neutron.list_ports()['ports'] if p['device_id'] == routerid ]
                        for port in ports:
				portid = port['id']
                                neutron.remove_interface_router(routerid, {'port_id':portid})
			neutron.delete_router(routerid)
		subnets = [ subnet for subnet in neutron.list_subnets()['subnets'] if subnet['name'] == novasubnet]
		for subnet in subnets:
        		subnetid = subnet['id']
			neutron.delete_subnet(subnetid)
		networks = [ network for network in neutron.list_networks()['networks'] if network['name'] == novanet]
		for network in networks:
        		networkid = network['id']
			neutron.delete_network(networkid)
	def _clean(self):
		if self.embedded:
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
		if not verbose or not rows:
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
			if timein > timeout or newstatus == 'ERROR':
				return False
			time.sleep(0.2)
			newstatus = manager.get(objectid).status
		return True
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
	def Add_FlavorAccess(self, nova, flavor, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		try:
			#THIS IS BUGGY
			tenant_id = nova.tenant_id
			nova.flavor_access.add_tenant_access(flavor, tenant_id)
			results = 'OK'
		except Exception as error:
			errors.append('Add_FlavorAccess')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Add_FlavorAccess: %s %s seconds %s" % (flavor, runningtime, results )
			output.append(['nova', 'Add_FlavorAccess', flavor, flavor, runningtime, results,])
	def Add_Role(self, keystone, user, role, tenant, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if tenant is None or user is None:
			errors.append('Add_Role')
			results = 'NotRun'
			if verbose:
				print "Add_Role: %s to %s 0 seconds" % ('N/A', 'N/A')
				output.append(['keystone', 'Add_Role', 'N/A', 'N/A', '0', results,])
			return
		try:
			keystone.roles.add_user_role(user, role, tenant)
			results = 'OK'
		except Exception as error:
			errors.append('Add_Role')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Add_Role: %s to %s %s seconds %s" % (role.name, user.name, runningtime, results)
			output.append(['keystone', 'Add_Role', role.name, role.name, runningtime, results,])
	def Authenticate_User(self, user, password, auth_url, tenant=None, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if user is None or tenant is None:
			errors.append('Authenticate_User')
			results = 'NotRun'
			if verbose:
				print "Authenticate_User: %s in %s 0 seconds" % ('N/A', 'N/A')
				output.append(['keystone', 'Authenticate_User', 'N/A', 'N/A', '0', results,])
			return
		try:
			usercredentials = { 'username' : user.name, 'password' : password, 'auth_url' : auth_url , 'tenant_name' : tenant.name }
			userkeystone = keystoneclient.Client(**usercredentials)
			results = 'OK'
		except Exception as error:
			errors.append('Authenticate_User')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Authenticate_User: %s in %s %s seconds %s" % (user.name, tenant.name, runningtime, results)
			output.append(['keystone', 'Authenticate_User', user.name, user.name, runningtime, results,])

	def Check_Console(self, nova, server, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if server is None:
			errors.append('Check_Console')
			results = 'NotRun'
			if verbose:
				print "Check_Console: %s 0 seconds" % 'N/A'
				output.append(['nova', 'Check_Console', 'N/A', 'N/A', '0', results,])
			return
		servername = server.name
		try:
			console = server.get_console_output()
			results = 'OK'
		except Exception as error:
			errors.append('Check_Console')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Check_Console: %s %s seconds %s" % (servername, runningtime, results)
			output.append(['nova', 'Check_Console', servername, servername, runningtime, results,])

	def Check_Novnc(self, nova, server, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if server is None:
			errors.append('Check_Novnc')
			results = 'NotRun'
			if verbose:
				print "Check_Novnc: %s 0 seconds" % 'N/A'
				output.append(['nova', 'Check_Novnc', 'N/A', 'N/A', '0', results,])
			return
		servername = server.name
		try:
			console = server.get_console_output()
			results = 'OK'
		except Exception as error:
			errors.append('Check_Novnc')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Check_Novnc: %s %s seconds %s" % (servername, runningtime, results)
			output.append(['nova', 'Check_Novnc', servername, servername, runningtime, results,])

	def Check_Metadata(self, nova, server, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if server is None:
			errors.append('Check_Metadata')
			results = 'NotRun'
			if verbose:
				print "Check_Metadata: %s 0 seconds" % 'N/A'
				output.append(['nova', 'Check_Metadata', 'N/A', 'N/A', '0', results,])
			return
		servername = server.name
		try:
                        #found = o._searchlog(server,'METADATA',timeout)
                        found = o._searchlog(server,servername,timeout)
                        if not found:
                                raise Exception("Timeout waiting for metadata")
			results = 'OK'
		except Exception as error:
			errors.append('Check_Metadata')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Check_Metadata: %s %s seconds %s" % (servername, runningtime, results)
			output.append(['nova', 'Check_Metadata', servername, servername, runningtime, results,])

	def Create_Alarm(self, ceilometer, alarm, alarms=None, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		try:
			newalarm = ceilometer.alarms.create(name=alarm, threshold=100, meter_name=alarm)
			results = 'OK'
			alarms.append(newalarm.id)
		except Exception as error:
			errors.append('Create_Alarm')
			results = str(error)
			alarms.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Alarm: %s %s seconds %s" % (alarm, runningtime, results )
			output.append(['ceilometer', 'Create_Alarm', alarm, alarm, runningtime, results,])
	def Create_Backup(self, cinder, volume, backups, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if volume is None:
			errors.append('Create_Backup')
			results = 'NotRun'
			if verbose:
				print "Create_Backup: %s 0 seconds" % 'N/A'
				output.append(['cinder', 'Create_Backup', 'N/A', 'N/A', '0', results,])
			return
		backup = "backup-%s" % volume.name
		try:
			volume_id = volume.id
			available = o._available(cinder.volumes, volume_id, timeout)
			if not available:
				raise Exception("Timeout waiting for available status")
			newbackup = cinder.backups.create(volume_id=volume_id, name=backup)
			backups.append(newbackup.id)
			results = 'OK'
                        available = o._available(cinder.backups, newbackup.id, timeout)
                        if not available:
                                raise Exception("Timeout waiting for available status")
		except cinderexceptions.NoUniqueMatch:
			errors.append('Create_Backup')
			results = 'NoUniqueMatch'
			backups.append(None)
		except Exception as error:
			errors.append('Create_Backup')
			results = str(error)
			backups.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Backup: %s %s seconds %s" % (backup, runningtime, results )
			output.append(['cinder', 'Create_Backup', backup, backup, runningtime, results,])	
	def Create_Container(self, swift, container, containers=None, errors=None, output=None, verbose=False, timeout=20):
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
			results = str(error)
			containers.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Container: %s %s seconds %s" % (container, runningtime, results )
			output.append(['swiftcontainer', 'Create_Container', container, container, runningtime, results,])	
			
	def Create_Flavor(self, nova, flavor, flavors=None, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		try:
			newflavor = nova.flavors.create(name=flavor,ram=512,vcpus=1,disk=1)
			results = 'OK'
			flavors.append(newflavor.id)
		except Exception as error:
			errors.append('Create_Flavor')
			results = str(error)
			flavors.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Flavor: %s %s seconds %s" % (flavor, runningtime, results )
			output.append(['nova', 'Create_Flavor', flavor, flavor, runningtime, results,])

	def Create_Image(self, glance, image, imagepath, images=None, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		try:
			if imagepath is None:
				raise Exception('Missing OS_GLANCE_IMAGE_PATH environment variable')
			newimage = glance.images.create(name=image, visibility='public', disk_format='qcow2',container_format='bare')
			with open(imagepath,'rb') as data:
				glance.images.upload(newimage.id, data)
			available = o._available(glance.images, newimage.id, timeout,status='active')
			if not available:
				raise Exception("Timeout waiting for available status")
			results = 'OK'
			images.append(newimage.id)
		except Exception as error:
			errors.append('Create_Image')
			results = str(error)
			images.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Image: %s %s seconds %s" % (image, runningtime, results )
			output.append(['glance', 'Create_Image', image, image, runningtime, results,])
	def Create_KeyPair(self, nova, keypair, keypairs=None, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		try:
			pubkey='ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDYgUh2XWv5EcWsrKq7fcmZLy/V9//MZtRGv+RDYSW0X6TZLOAw2xLTXkmZbKfo9P8DWyCXlptCgB8BuJhORY3dZFxUfcjgM5cbqB+64qlHdr9sxGfb5WDdc+4mpMEMSpfIgPwFda9bXmOimeLV9NaH+TLNCCs7uSig+t3eeDcFNgAbhMo0ffud4h4OHIaYEuPVnlA5lfDkY3qYboDPaqPs3qhbIOf5Q4AoCaxSQGXRUWTDQyQO8NNFiF9dfHTYb8rRW9BXLVCWXpfxyRJZzgGc1GLqmRNPjfY0DMDAD/D6qAxtVjEQYNCm5LiJMGq6BDVejdypKRYAoCU+KCmQ6xWr'
			newkeypair = nova.keypairs.create(keypair,pubkey)
			results = 'OK'
			keypairs.append(newkeypair.id)
		except Exception as error:
			errors.append('Create_KeyPair')
			results = str(error)
			keypairs.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_KeyPair: %s %s seconds %s" % (keypair, runningtime, results )
			output.append(['nova', 'Create_KeyPair', keypair, keypair, runningtime, results,])

	def Create_Network(self, neutron, network, networks=None, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		try:
			newnetwork = {'name': network, 'admin_state_up': True}
			newnetwork = neutron.create_network({'network':newnetwork})
			results = 'OK'
			networks.append(newnetwork['network']['id'])
		except Exception as error:
			errors.append('Create_Network')
			results = str(error)
			networks.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Network: %s %s seconds %s" % (network, runningtime, results )
			output.append(['neutron', 'Create_Network', network, network, runningtime, results,])
	def Create_Role(self, keystone, name, roles=None, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		try:
			role = keystone.roles.create(name=name)
			results = 'OK'
			roles.append(role.id)
		except Exception as error:
			errors.append('Create_Role')
			results = str(error)
			roles.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Create_Role: %s %s seconds %s" % (name, runningtime, results)
			output.append(['keystone', 'Create_Role', name, name, runningtime, results,])
	def Create_Router(self, neutron, router, subnet, externalid, routers=None, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if subnet is None:
			errors.append('Create_Router')
			results = 'NotRun'
			if verbose:
				output.append(['neutron', 'Create_Router', 'N/A', 'N/A', '0', results,])
			return
		subnetid  = subnet['id']
		try:
			newrouter = {'name':router}
			if externalid:
				newrouter['external_gateway_info']= {"network_id": externalid, "enable_snat": True}
                        newrouter = neutron.create_router({'router':newrouter})
			routerid  = newrouter['router']['id']
			neutron.add_interface_router(routerid,{'subnet_id':subnetid } )
			results = 'OK'
			routers.append(routerid)
		except Exception as error:
			errors.append('Create_Router')
			results = str(error)
			routers.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Router: %s %s seconds %s" % (router, runningtime, results )
	def Create_SecurityGroup(self, neutron, securitygroup, securitygroups=None, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		try:
			newsecuritygroup = {'name': securitygroup}
			newsecuritygroup = neutron.create_security_group({'security_group':newsecuritygroup})
			results = 'OK'
			securitygroups.append(newsecuritygroup['security_group']['id'])
		except Exception as error:
			errors.append('Create_SecurityGroup')
			results = str(error)
			securitygroups.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_SecurityGroup: %s %s seconds %s" % (securitygroup, runningtime, results )
			output.append(['neutron', 'Create_SecurityGroup', securitygroup, securitygroup, runningtime, results,])
	def Create_Server(self, nova, server, servers=None, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		try:
			if not embedded:
				keypairname = None
				image       = os.environ['OS_NOVA_IMAGE']   if os.environ.has_key('OS_NOVA_IMAGE')   else 'cirros'
				image       = nova.images.find(name=image)
				network     = os.environ['OS_NOVA_NETWORK'] if os.environ.has_key('OS_NOVA_NETWORK') else 'private'
				networkid   = nova.networks.find(label=network).id
			else:
				keypairname = 'novakey'
				image       = nova.images.find(name='novaimage')
				networkid   = nova.networks.find(label='novanet').id
			flavor  = os.environ['OS_NOVA_FLAVOR']  if os.environ.has_key('OS_NOVA_FLAVOR')  else 'm1.tiny'
			flavor  = nova.flavors.find(name=flavor)
			nics = [{'net-id': networkid}]
			userdata = "#!/bin/bash\necho METADATA >/dev/ttyS0"
			#newserver = nova.servers.create(name=server, image=image, flavor=flavor, nics=nics)
			#newserver = nova.servers.create(name=server, image=image, flavor=flavor, nics=nics, key_name=keypairname)
			newserver = nova.servers.create(name=server, image=image, flavor=flavor, nics=nics, key_name=keypairname, userdata=userdata)
			servers.append(newserver.id)
                        active = o._available(nova.servers, newserver.id, timeout, status='ACTIVE')
                        if not active:
                                raise Exception("Timeout waiting for active status")
			results = 'OK'
		except Exception as error:
			print type(error)
			errors.append('Create_Server')
			results = str(error)
			servers.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Server: %s %s seconds %s" % (server, runningtime, results )
			output.append(['nova', 'Create_Server', server, server, runningtime, results,])
	def Create_Snapshot(self, cinder, volume, snapshots, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if volume is None:
			errors.append('Create_Snapshot')
			results = 'NotRun'
			if verbose:
				output.append(['cinder', 'Create_Snapshot', 'N/A', 'N/A', '0', results,])
			return
		snapshot = "snapshot-%s" % volume.name
		try:
			volume_id = volume.id				
                        available = o._available(cinder.volumes, volume_id, timeout)
                        if not available:
                                raise Exception("Timeout waiting for available status")
			newsnapshot = cinder.volume_snapshots.create(volume_id=volume_id, name=snapshot)
			snapshots.append(newsnapshot.id)
			results = 'OK'
                        available = o._available(cinder.volume_snapshots, newsnapshot.id, timeout)
                        if not available:
                                raise Exception("Timeout waiting for available status")
		except cinderexceptions.NoUniqueMatch:
			errors.append('Create_Snapshot')
			results = 'NoUniqueMatch'
			snapshots.append(None)
		except Exception as error:
			errors.append('Create_Snapshot')
			results = str(error)
			snapshots.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Snapshot: %s %s seconds %s" % (snapshot, runningtime, results )
			output.append(['cinder', 'Create_Snapshot', snapshot, snapshot, runningtime, results,])	
	def Create_Stack(self, heat, stack, stacks=None, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		try:
			template  = os.environ['OS_HEAT_TEMPLATE']   if os.environ.has_key('OS_HEAT_TEMPLATE')   else None
			if template is None:
				if not embedded:
					image     = os.environ['OS_NOVA_IMAGE']   if os.environ.has_key('OS_NOVA_IMAGE')   else 'cirros'
					network   = os.environ['OS_NOVA_NETWORK'] if os.environ.has_key('OS_NOVA_NETWORK') else 'private'
				else:
					image     = 'novaimage'
					network   = 'novanet'
				flavor = os.environ['OS_NOVA_FLAVOR']  if os.environ.has_key('OS_NOVA_FLAVOR')  else 'm1.tiny'
				stackinstance = "%sinstance" % stack
				template={'heat_template_version': '2013-05-23', 'description': 'Testing Template', 'resources': 
				 	{stackinstance: {'type': 'OS::Nova::Server', 'properties': {'image': image,
				 	'flavor': flavor, 'networks': [{'network': network }]}}}}
				template = json.dumps(template)
			else:
				template = yaml.load(open(template))
				for oldkey in template['resources'].keys():
					newkey = "%s%s" % (stack, oldkey)
					template['resources'][newkey]= template['resources'].pop(oldkey)
					del template['resources'][oldkey]
			newstack = heat.stacks.create(stack_name=stack, template=template)
			stacks.append(newstack['stack']['id'])
			available = o._available(heat.stacks, newstack['stack']['id'], timeout, status='COMPLETE')
			if not available:
				raise Exception("Timeout waiting for available status")
			results = 'OK'
		except Exception as error:
			errors.append('Create_Stack')
			results = str(error)
			stacks.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Stack: %s %s seconds %s" % (stack, runningtime, results )
			output.append(['heat', 'Create_Stack', stack, stack, runningtime, results,])
	def Create_Subnet(self, neutron, subnet, network, cidr='10.0.0.0/24', subnets=None, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if network is None:
			errors.append('Create_Subnet')
			results = 'NotRun'
			if verbose:
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
			results = str(error)
			subnets.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Subnet: %s %s seconds %s" % (subnet, runningtime, results )
			output.append(['neutron', 'Create_Subnet', subnet, subnet, runningtime, results,])
	def Create_Tenant(self, keystone, name, description, tenants=None, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		try:
			tenant = keystone.tenants.create(tenant_name=name, description=description,enabled=True)
			results = 'OK'
			tenants.append(tenant.id)
		except Exception as error:
			errors.append('Create_Tenant')
			results = str(error)
			tenants.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Tenant:%s %s seconds %s" % (name, runningtime, results)
			output.append(['keystone', 'Create_Tenant', name, name, runningtime, results,])
	def Create_TypedVolume(self, cinder, volume, volumetype, volumes=None, errors=None, output=None, verbose=False, timeout=20):
		if volumetype is None:
			results = 'Missing OS_CINDER_VOLUME_TYPE environment variable'
			volumes.append(None)
			if verbose:
				print "Create_TypedVolume: %s 0 seconds" % 'N/A'
				output.append(['cinder', 'Create_TypedVolume', 'N/A', 'N/A', '0', results,])
			return
		starttime = time.time()
		try:
			newvolume = cinder.volumes.create(size=1, name=volume, volume_type=volumetype)
			volumes.append(newvolume.id)
			results = 'OK'
                        available = o._available(cinder.volumes, newvolume.id, timeout)
                        if not available:
                                raise Exception("Timeout waiting for available status")
		except Exception as error:
			errors.append('Create_TypedVolume')
			results = str(error)
			volumes.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_TypedVolume: %s %s seconds %s" % (volume, runningtime, results )
			output.append(['cinder', 'Create_TypedVolume', volume, volume, runningtime, results,])
	def Create_User(self, keystone, name, password, email,tenant, users=None, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if tenant is None:
			errors.append('Create_User')
			results = 'NotRun'
			users.append(None)
			if verbose:
				print "Create_User: %s 0 seconds" % 'N/A'
				output.append(['keystone', 'Create_User', 'N/A', 'N/A', '0', results,])
			return
		try:
			user = keystone.users.create(name=name, password=password, email=email, tenant_id=tenant.id)
			results = 'OK'
			users.append(user.id)
		except Exception as error:
			errors.append('Create_User')
			results = str(error)
			users.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_User: %s %s seconds %s" % (name, runningtime, results)
			output.append(['keystone', 'Create_User', name, name, runningtime, results,])
	def Create_Volume(self, cinder, volume, volumes=None, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		try:
			newvolume = cinder.volumes.create(size=1, name=volume)
			volumes.append(newvolume.id)
                        available = o._available(cinder.volumes, newvolume.id, timeout)
                        if not available:
                                raise Exception("Timeout waiting for available status")
			results = 'OK'
		except Exception as error:
			errors.append('Create_Volume')
			results = str(error)
			volumes.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Volume: %s %s seconds %s" % (volume, runningtime, results )
			output.append(['cinder', 'Create_Volume', volume, volume, runningtime, results,])			
	def Create_Volume_From_Snapshot(self, cinder, snapshot, snapshotvolumes=None, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if snapshot is None:
			errors.append('Create_Volume_From_Snapshot')
			results = 'NotRun'
			if verbose:
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
                        available = o._available(cinder.volumes, newvolume.id, timeout)
                        if not available:
                                raise Exception("Timeout waiting for available status")
		except Exception as error:
			errors.append('Create_Volume_From_Snapshot')
			results = str(error)
			volumes.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Volume_From_Snapshot: %s %s seconds %s" % (volumename, runningtime, results )
			output.append(['cinder', 'Create_Volume_From_Snapshot', volumename, volumename, runningtime, results,])			
	def Delete_Alarm(self, ceilometer, alarm, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if alarm is None:
			errors.append('Delete_Alarm')
			results = 'NotRun'
			if verbose:
				print "Delete_Alarm: %s 0 seconds" % 'N/A'
				output.append(['ceilometer', 'Delete_Alarm', 'N/A', 'N/A', '0', results,])
			return
		alarmname = alarm.name
		try:
			alarm.delete()
			results = 'OK'
		except Exception as error:
			errors.append('Delete_Alarm')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Alarm: %s %s seconds %s" % (alarmname, runningtime, results)
			output.append(['ceilometer', 'Delete_Alarm', alarmname, alarmname, runningtime, results,])
	def Delete_Backup(self, cinder, backup, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if backup is None:
			errors.append('Delete_Backup')
			results = 'NotRun'
			if verbose:
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
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Backup: %s %s seconds %s" % (backupname, runningtime, results)
			output.append(['cinderbackup', 'Delete_Backup', backupname, backupname, runningtime, results,])		
	def Delete_Container(self, swift, container, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if container is None:
			errors.append('Delete_Container')
			results = 'NotRun'
			if verbose:
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
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Container: %s %s seconds %s" % (container, runningtime, results)
			output.append(['swift', 'Delete_Container', container, container, runningtime, results,])
			
	def Delete_Flavor(self, nova, flavor, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if flavor is None:
			errors.append('Delete_Flavor')
			results = 'NotRun'
			if verbose:
				print "Delete_Flavor: %s 0 seconds" % 'N/A'
				output.append(['nova', 'Delete_Flavor', 'N/A', 'N/A', '0', results,])
			return
		flavorname = flavor.name
		try:
			flavor.delete()
			results = 'OK'
		except Exception as error:
			errors.append('Delete_Flavor')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Flavor: %s %s seconds %s" % (flavorname, runningtime, results)
			output.append(['nova', 'Delete_Flavor', flavorname, flavorname, runningtime, results,])			

	def Delete_Image(self, glance, image, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if image is None:
			errors.append('Delete_Image')
			results = 'NotRun'
			if verbose:
				print "Delete_Image: %s 0 seconds" % 'N/A'
				output.append(['glance', 'Delete_Image', 'N/A', 'N/A', '0', results,])
			return
		imagename = image.name
		try:
			glance.images.delete(image.id)
			results = 'OK'
		except Exception as error:
			errors.append('Delete_Image')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Image: %s %s seconds %s" % (imagename, runningtime, results)
			output.append(['glance', 'Delete_Image', imagename, imagename, runningtime, results,])

	def Delete_KeyPair(self, nova, keypair, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if keypair is None:
			errors.append('Delete_KeyPair')
			results = 'NotRun'
			if verbose:
				print "Delete_KeyPair: %s 0 seconds" % 'N/A'
				output.append(['nova', 'Delete_KeyPair', 'N/A', 'N/A', '0', results,])
			return
		keypairname = keypair.name
		try:
			keypair.delete()
			results = 'OK'
		except Exception as error:
			errors.append('Delete_KeyPair')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_KeyPair: %s %s seconds %s" % (keypairname, runningtime, results)
			output.append(['nova', 'Delete_KeyPair', keypairname, keypairname, runningtime, results,])			

	def Delete_SecurityGroup(self, neutron, securitygroup, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if securitygroup is None:
			errors.append('Delete_SecurityGroup')
			results = 'NotRun'
			if verbose:
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
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_SecurityGroup: %s %s seconds %s" % (securitygroupname, runningtime, results)
			output.append(['neutron', 'Delete_SecurityGroup', securitygroupname, securitygroupname, runningtime, results,])
	def Delete_Role(self, keystone, role, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if role is None:
			results = 'NotRun'
			if verbose:
				print "Delete_Role: %s 0 seconds" % 'N/A'
				output.append(['keystone', 'Delete_Role', 'N/A', 'N/A', '0', results,])
			return
		rolename = role.name
		try:
			role.delete()
			results = 'OK'
		except Exception as error:
			errors.append('Delete_Role')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Role: %s %s seconds %s" % (rolename, runningtime, results)
			output.append(['keystone', 'Delete_Role', rolename, rolename, runningtime, results,])
	def Delete_Router(self, neutron, router, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if router is None:
			errors.append('Delete_Router')
			results = 'NotRun'
			if verbose:
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
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Router: %s %s seconds %s" % (routername, runningtime, results)
			output.append(['neutron', 'Delete_Router', routername, routername, runningtime, results,])
	def Delete_Server(self, nova, server, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if server is None:
			errors.append('Delete_Server')
			results = 'NotRun'
			if verbose:
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
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Server: %s %s seconds %s" % (servername, runningtime, results)
			output.append(['nova', 'Delete_Server', servername, servername, runningtime, results,])
	def Delete_Snapshot(self, cinder, snapshot, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if snapshot is None:
			errors.append('Delete_Snapshot')
			results = 'NotRun'
			if verbose:
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
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Snapshot: %s %s seconds %s" % (snapshotname, runningtime, results)
			output.append(['cinder', 'Delete_Snapshot', snapshotname, snapshotname, runningtime, results,])
			
	def Delete_Stack(self, heat, stack, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if stack is None:
			errors.append('Delete_Stack')
			results = 'NotRun'
			if verbose:
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
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Stack: %s %s seconds %s" % (stackname, runningtime, results)
			output.append(['heat', 'Delete_Stack', stackname, stackname, runningtime, results,])
	def Delete_Subnet(self, neutron, subnet, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if subnet is None:
			errors.append('Delete_Subnet')
			results = 'NotRun'
			if verbose:
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
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Subnet: %s %s seconds %s" % (subnetname, runningtime, results)
	def Delete_Tenant(self, keystone, tenant, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if tenant is None:
			errors.append('Delete_Tenant')
			results = 'NotRun'
			if verbose:
				print "Delete_Tenant: %s 0 seconds" % 'N/A'
				output.append(['keystone', 'Delete_Tenant', 'N/A', 'N/A', '0', results,])
			return
		tenantname = tenant.name
		try:
			tenant.delete()
			results = 'OK'
		except Exception as error:
			errors.append('Delete_Tenant')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Delete_Tenant: %s %s seconds %s" % (tenantname, runningtime, results)
			output.append(['keystone', 'Delete_Tenant', tenantname, tenantname, runningtime, results,])
	def Delete_User(self, keystone, user, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if user is None:
			results = 'NotRun'
			errors.append('Delete_User')
			if verbose:
				print "Delete_User: %s 0 seconds" % 'N/A'
				output.append(['keystone', 'Delete_User', 'N/A', 'N/A', '0', results,])
			return
		username = user.name
		try:
			user.delete()
			results = 'OK'
		except Exception as error:
			errors.append('Delete_User')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Delete_User: %s %s seconds %s" % (username, runningtime, results)
			output.append(['keystone', 'Delete_User', username, username, runningtime, results,])
	def Delete_Volume(self, cinder, volume, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if volume is None:
			errors.append('Delete_Volume')
			results = 'NotRun'
			if verbose:
				print "Delete_Volume: %s 0 seconds" % 'N/A'
				output.append(['cinder', 'Delete_Volume', 'N/A', 'N/A', '0', results,])
			return
		volumename = volume.name
		try:
			volume.delete()
			results = 'OK'
			deleted = o._deleted(cinder.volumes, volume.id, timeout)
			if not deleted:
				results = 'Timeout waiting for deletion'
				errors.append('Delete_Volume')
		except Exception as error:
			errors.append('Delete_Volume')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Volume: %s %s seconds %s" % (volumename, runningtime, results)
			output.append(['cinder', 'Delete_Volume', volumename, volumename, runningtime, results,])
	def Grow_Volume(self, cinder, volume, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if volume is None:
			results = 'NotRun'
			errors.append('Grow_Volume')
			if verbose:
				print "Grow_Volume: %s 0 seconds" % 'N/A'
				output.append(['cinder', 'Grow_Volume', 'N/A', 'N/A', '0', results,])
			return
		try:
			cinder.volumes.extend(volume.id,2)
			#cinder.volumes.get(volume.id).size != 2
			available = o._available(cinder.volumes, volume.id, timeout)
                        if not available:
                                raise Exception("Timeout waiting for available status")
			results = 'OK'
		except Exception as error:
			errors.append('Grow_Volume')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Grow_Volume: %s %s seconds %s" % (volume.name, runningtime, results)
			output.append(['cinder', 'Grow_Volume', volume.name, volume.name, runningtime, results,])
	def List_Alarm(self, ceilometer, alarm, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if alarm is None:
			results = 'NotRun'
			errors.append('List_Alarm')
			if verbose:
				print "List_Alarm: %s 0 seconds" % 'N/A'
				output.append(['ceilometer', 'List_Alarm', 'N/A', 'N/A', '0', results,])
			return
		try:
			ceilometer.alarms.get(alarm.id)
			results = 'OK'
		except Exception as error:
			errors.append('List_Alarm')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Alarm: %s %s seconds %s" % (alarm.name, runningtime, results)
			output.append(['ceilometer', 'List_Alarm', alarm.name, alarm.name, runningtime, results,])
	def List_Backup(self, cinder, backup, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if backup is None:
			results = 'NotRun'
			errors.append('List_Backup')
			if verbose:
				print "List_Backup: %s 0 seconds" % 'N/A'
				output.append(['cinderbackup', 'List_Backup', 'N/A', 'N/A', '0', results,])
			return
		try:
			cinder.backups.get(backup.id)
			results = 'OK'
		except Exception as error:
			errors.append('List_Backup')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Backup: %s %s seconds %s" % (backup.name, runningtime, results)
			output.append(['cinderbackup', 'List_Backup', backup.name, backup.name, runningtime, results,])	
			
	def List_Flavor(self, nova, flavor, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if flavor is None:
			results = 'NotRun'
			errors.append('List_Flavor')
			if verbose:
				print "List_Flavor: %s 0 seconds" % 'N/A'
				output.append(['nova', 'List_Flavor', 'N/A', 'N/A', '0', results,])
			return
		try:
			nova.flavors.get(flavor.id)
			results = 'OK'
		except Exception as error:
			errors.append('List_Flavor')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Flavor: %s %s seconds %s" % (flavor.name, runningtime, results)
			output.append(['nova', 'List_Flavor', flavor.name, flavor.name, runningtime, results,])			
			
	def List_Container(self, swift, container, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if container is None:
			results = 'NotRun'
			errors.append('List_Container')
			if verbose:
				print "List_Container: %s 0 seconds" % 'N/A'
				output.append(['swift', 'List_Container', 'N/A', 'N/A', '0', results,])
			return
		try:
			swift.get_container(container)
			results = 'OK'
		except Exception as error:
			errors.append('List_Container')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Container: %s %s seconds %s" % (container, runningtime, results)
			output.append(['swift', 'List_Container', container, container, runningtime, results,])						
	def List_Image(self, glance, image, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if image is None:
			results = 'NotRun'
			errors.append('List_Image')
			if verbose:
				print "List_Image: %s 0 seconds" % 'N/A'
				output.append(['glance', 'List_Image', 'N/A', 'N/A', '0', results,])
			return
		try:
			glance.images.get(image.id)
			results = 'OK'
		except Exception as error:
			errors.append('List_Image')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Image: %s %s seconds %s" % (image.name, runningtime, results)
			output.append(['glance', 'List_Image', image.name, image.name, runningtime, results,])
	def List_KeyPair(self, nova, keypair, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if keypair is None:
			results = 'NotRun'
			errors.append('List_KeyPair')
			if verbose:
				print "List_KeyPair: %s 0 seconds" % 'N/A'
				output.append(['nova', 'List_KeyPair', 'N/A', 'N/A', '0', results,])
			return
		try:
			nova.keypairs.get(keypair.id)
			results = 'OK'
		except Exception as error:
			errors.append('List_KeyPair')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_KeyPair: %s %s seconds %s" % (keypair.name, runningtime, results)
			output.append(['nova', 'List_KeyPair', keypair.name, keypair.name, runningtime, results,])

	def List_Meter(self, ceilometer, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		try:
			meters = ceilometer.meters.list()	
			results = 'OK'
		except Exception as error:
			errors.append('List_Meter')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Meter: %s %s seconds %s" % ('meters', runningtime, results)
			output.append(['ceilometer', 'List_Meter', 'meters', 'meters', runningtime, results,])
	def List_Network(self, neutron, network, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if network is None:
			results = 'NotRun'
			errors.append('List_Network')
			if verbose:
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
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Network: %s %s seconds %s" % (network_name, runningtime, results)
			output.append(['neutron', 'List_Network', network_name, network_name, runningtime, results,])
	def List_Role(self, keystone, role, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if role is None:
			results = 'NotRun'
			errors.append('List_Role')
			if verbose:
				print "List_Role: %s" % 'N/A'
				output.append(['keystone', 'List_Role', 'N/A', 'N/A', '0', results,])
			return
		try:
			keystone.roles.get(role.id)
			results = 'OK'
		except Exception as error:
			errors.append('List_Role')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Role: %s %s seconds %s" % (role.name, runningtime, results)
			output.append(['keystone', 'List_Role', role.name, role.name, runningtime, results,])
	def List_Server(self, nova, server, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if server is None:
			results = 'NotRun'
			errors.append('List_Server')
			if verbose:
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
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Server: %s %s seconds %s" % (server_name, runningtime, results)
			output.append(['nova', 'List_Server', server_name, server_name, runningtime, results,])
	def List_Snapshot(self, cinder, snapshot, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if snapshot is None:
			results = 'NotRun'
			errors.append('List_Snapshot')
			if verbose:
				print "List_Snapshot: %s 0 seconds" % 'N/A'
				output.append(['cinder', 'List_Snapshot', 'N/A', 'N/A', '0', results,])
			return
		try:
			cinder.volume_snapshots.get(snapshot.id)
			results = 'OK'
		except Exception as error:
			errors.append('List_Snapshot')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Snapshot: %s %s seconds %s" % (snapshot.name, runningtime, results)
			output.append(['cinder', 'List_Snapshot', snapshot.name, snapshot.name, runningtime, results,])		
	def List_Stack(self, heat, stack, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if stack is None:
			results = 'NotRun'
			errors.append('List_Stack')
			if verbose:
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
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Stack: %s %s seconds %s" % (stackname, runningtime, results)
			output.append(['heat', 'List_Stack', stackname, stackname, runningtime, results,])
	def List_Subnet(self, neutron, subnet, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if subnet is None:
			results = 'NotRun'
			errors.append('List_Subnet')
			if verbose:
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
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Subnet: %s %s seconds %s" % (subnet_name, runningtime, results)
			output.append(['neutron', 'List_Subnet', subnet_name, subnet_name, runningtime, results,])
	def List_Router(self, neutron, router, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if router is None:
			results = 'NotRun'
			errors.append('List_Router')
			if verbose:
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
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Router: %s %s seconds %s" % (router_name, runningtime, results)
			output.append(['neutron', 'List_Router', router_name, router_name, runningtime, results,])
	def List_Volume(self, cinder, volume, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		if volume is None:
			results = 'NotRun'
			errors.append('List_Volume')
			if verbose:
				print "List_Volume: %s 0 seconds" % 'N/A'
				output.append(['cinder', 'List_Volume', 'N/A', 'N/A', '0', results,])
			return
		try:
			cinder.volumes.get(volume.id)
			results = 'OK'
		except Exception as error:
			errors.append('List_Volume')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Volume: %s %s seconds %s" % (volume.name, runningtime, results)
			output.append(['cinder', 'List_Volume', volume.name, volume.name, runningtime, results,])
	def Reach_VolumeQuota(self, cinder, errors=None, output=None, verbose=False, timeout=20):
		quotavolumes = []
		errors = []
		starttime = time.time()
		try:
			maxvolumes = cinder.quotas.get(self.keystone.tenant_id).volumes
			currentvolumes = len(cinder.volumes.list())
			for  step in range(0,maxvolumes-currentvolumes+1):
				newvolume = cinder.volumes.create(size=1, name='quotavolume')
                        	o._available(cinder.volumes, newvolume.id, timeout)
				quotavolumes.append(newvolume)
			results = 'QuotaNotRespected'
			errors.append('Reach_StorageQuota')
		except cinderexceptions.OverLimit:
			results = 'OK'
		except Exception as error:
			errors.append('Reach_StorageQuota')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Reach_StorageQuota: %s seconds %s" % (runningtime, results )
			output.append(['cinder', 'Reach_StorageQuota', 'volumequota', 'volumequota', runningtime, results,])
		return quotavolumes
	def Reach_StorageQuota(self, cinder, errors=None, output=None, verbose=False, timeout=20):
		quotavolumes = []
		errors = []
		starttime = time.time()
		try:
			maxstorage = cinder.quotas.get(self.keystone.tenant_id).gigabytes
			newvolume = cinder.volumes.create(size=maxstorage+1, name='quotastorage')
                        o._available(cinder.volumes, newvolume.id, timeout)
			newvolume.delete()
			results = 'QuotaNotRespected'
			errors.append('Reach_StorageQuota')
		except cinderexceptions.OverLimit:
			results = 'OK'
		except Exception as error:
			errors.append('Reach_StorageQuota')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Reach_StorageQuota: %s seconds %s" % (runningtime, results )
			output.append(['cinder', 'Reach_StorageQuota', 'storagequota', 'storagequota', runningtime, results,])
	def Remove_FlavorAccess(self, nova, flavor, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		try:
			#THIS IS BUGGY
			tenant_id = nova.tenant_id
			nova.flavor_access.remove_tenant_access(flavor, tenant_id)
			results = 'OK'
		except Exception as error:
			errors.append('Remove_FlavorAccess')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Remove_FlavorAccess: %s %s seconds %s" % (flavor, runningtime, results )
			output.append(['nova', 'Remove_FlavorAccess', flavor, flavor, runningtime, results,])
	def Restore_Backup(self, cinder, backup, errors=None, output=None, verbose=False, timeout=20):
		starttime = time.time()
		#if volume is None or backup is None:
		#	errors.append('Create_Restore')
		#	results = 'NotRun'
		#	if verbose:
		#		print "Create_Restore: %s 0 seconds" % 'N/A'
		#		output.append(['cinder', 'Create_Restore', 'N/A', 'N/A', '0', results,])
		#	return
		try:
			backup_id   = backup.id
			backup_name = backup.name
			#volume_id   = volume.id
			cinder.restores.restore(backup_id)
                        available = o._available(cinder.backups, backup.id, timeout)
                        if not available:
                                raise Exception("Timeout waiting for available status")
			results = 'OK'
		except Exception as error:
			errors.append('Restore_Backup')
			results = str(error)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Restore_Backup: %s %s seconds %s" % (backup_name, runningtime, results )
			output.append(['cinder', 'Restore_Backup', backup_name, backup_name, runningtime, results,])	
	def _printreport(self):
		return self.output
	def listservices(self):
		keystone = self.keystone
		output = PrettyTable(['Service', 'Type', 'Status'])
		output.align['Service'] = "l"
		for service in sorted(keystone.services.list(), key = lambda s: s.name):
			status = 'Available' if service.enabled else 'N/A'
			output.add_row([service.name, service.type, status])
		return output
	def keystoneclean(self, tenants, users, roles):
		if self.verbose:
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
		if self.verbose:
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
		if self.verbose:
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
				except Exception as e:
					continue

	def cinderbackupclean(self, backups):
		if self.verbose:
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
		if self.verbose:
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
	def novaclean(self, flavors, keypairs, servers):
		if self.verbose:
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
	def heatclean(self, stacks):
		if self.verbose:
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
		if self.verbose:
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
		if self.verbose:
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
		if self.verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
		if self.verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
		if self.verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
                        if verbose:
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
                        if verbose:
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
			if verbose:
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
			if verbose:
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
		if self.verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Create_Router'
		reftest = 'Create_Network'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Create_Router, args=(neutron, "%s-%d-%d" % (self.router, step, number), subnet, self.externalid,  routers, errors, output, self.verbose, timeout, )) for subnet in subnets ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)

		return securitygroups, networks, subnets, routers
	def novatest(self):
		category  = 'nova'
		timeout  = int(os.environ["OS_%s_TIMEOUT" % category.upper()]) if os.environ.has_key("OS_%s_TIMEOUT" % category.upper()) else self.timeout
		tests     = self.novatests 
		mgr       = multiprocessing.Manager()
		errors    = mgr.list()
		keypairs  = mgr.list()
		flavors   = mgr.list()
		servers   = mgr.list()
		if self.verbose:
			print "Testing Nova..."
		keystone = self.keystone
		nova = novaclient.Client('2', **self.novacredentials)
		
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test    = 'Check_Metadata'
		reftest = 'Create_Server'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(reftest)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Check_Metadata, args=(nova, server, errors, output, self.verbose, timeout, )) for server in servers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

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
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
		return flavors, keypairs, servers
	def heattest(self):
		category = 'heat'
		timeout  = int(os.environ["OS_%s_TIMEOUT" % category.upper()]) if os.environ.has_key("OS_%s_TIMEOUT" % category.upper()) else self.timeout
		tests = self.heattests 
		mgr = multiprocessing.Manager()
		errors  = mgr.list()
		stacks = mgr.list()
		if self.verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
		if self.verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
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
		if self.verbose:
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
			if verbose:
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
			if verbose:
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
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
		return containers

if __name__ == "__main__":
	#parse options
	usage   = "test openstack installation quickly"
	version = "0.1"
	parser  = optparse.OptionParser("Usage: %prog [options] deployment",version=version)
	listinggroup = optparse.OptionGroup(parser, 'Listing options')
	listinggroup.add_option('-l', '--listservices', dest='listservices', action='store_true', help='List available services')
	parser.add_option_group(listinggroup)
	testinggroup = optparse.OptionGroup(parser, 'Testing options')
	testinggroup.add_option('-A', '--availability', dest='testha', action='store_true',default=False, help='Test High Availability')
        testinggroup.add_option('-C', '--cinder', dest='testcinder', action='store_true',default=False, help='Test cinder')
	testinggroup.add_option('-E', '--all', dest='testall', action='store_true',default=False, help='Test All')
	testinggroup.add_option('-G', '--glance', dest='testglance', action='store_true',default=False, help='Test glance')
	testinggroup.add_option('-H', '--heat', dest='testheat', action='store_true',default=False, help='Test heat')
	testinggroup.add_option('-K', '--keystone', dest='testkeystone', action='store_true',default=False, help='Test keystone')
	testinggroup.add_option('-N', '--nova', dest='testnova', action='store_true',default=False, help='Test nova')
	testinggroup.add_option('-Q', '--neutron', dest='testneutron', action='store_true',default=False, help='Test neutron')
	testinggroup.add_option('-S', '--swift', dest='testswift', action='store_true',default=False, help='Test swift')
	testinggroup.add_option('-X', '--ceilometer', dest='testceilometer', action='store_true',default=False, help='Test ceilometer')
	parser.add_option_group(testinggroup)
	parser.add_option('-p', '--project', dest='project', default='acme', type='string', help='Project name to prefix for all elements. defaults to acme')
	parser.add_option('-t', '--timeout', dest='timeout', default=20, type='int', help='Timeout when waiting for a ressource to be available. Defaults to env[OS_TIMEOUT] and 20 if not found')
	parser.add_option('-v', '--verbose', dest='verbose', default=False, action='store_true', help='Verbose mode. Defaults to False')
	parser.add_option('-e', '--embedded', dest='embedded', default=True, action='store_true', help='Create a dedicated tenant to hold all tests. Defaults to True')
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
	timeout          = options.timeout
	embedded         = options.embedded
	try:
		keystonecredentials = _keystonecreds()
		novacredentials     = _novacreds()
		endpoint            = os.environ['OS_ENDPOINT_TYPE']                 if os.environ.has_key('OS_ENDPOINT_TYPE')      else 'publicURL'
		keystonetests       = os.environ['OS_KEYSTONE_TESTS'].split(',')     if os.environ.has_key('OS_KEYSTONE_TESTS')     else keystonedefaulttests
		glancetests         = os.environ['OS_GLANCE_TESTS'].split(',')       if os.environ.has_key('OS_GLANCE_TESTS')       else glancedefaulttests
		cindertests         = os.environ['OS_CINDER_TESTS'].split(',')       if os.environ.has_key('OS_CINDER_TESTS')       else cinderdefaulttests
		neutrontests        = os.environ['OS_NEUTRON_TESTS'].split(',')      if os.environ.has_key('OS_NEUTRON_TESTS')      else neutrondefaulttests
		novatests           = os.environ['OS_NOVA_TESTS'].split(',')         if os.environ.has_key('OS_NOVA_TESTS')         else novadefaulttests
		heattests           = os.environ['OS_HEAT_TESTS'].split(',')         if os.environ.has_key('OS_HEAT_TESTS')         else heatdefaulttests
		swifttests          = os.environ['OS_SWIFT_TESTS'].split(',')        if os.environ.has_key('OS_SWIFT_TESTS')        else swiftdefaulttests
		ceilometertests     = os.environ['OS_CEILOMETER_TESTS'].split(',')   if os.environ.has_key('OS_CEILOMETER_TESTS')   else ceilometerdefaulttests
		imagepath           = os.environ['OS_GLANCE_IMAGE_PATH']             if os.environ.has_key('OS_GLANCE_IMAGE_PATH')  else None
		volumetype          = os.environ['OS_CINDER_VOLUME_TYPE']            if os.environ.has_key('OS_CINDER_VOLUME_TYPE') else None
		externalid          = os.environ['OS_NEUTRON_EXTERNALID']            if os.environ.has_key('OS_NEUTRON_EXTERNALID') else None
		timeout             = int(os.environ['OS_TIMEOUT'])                  if os.environ.has_key('OS_TIMEOUT')            else timeout
	except Exception as e:
		print "Missing environment variables. source your openrc file first"
		print e
	    	os._exit(1)
	if listservices:
		embedded = False
	o = Openstuck(keystonecredentials=keystonecredentials, novacredentials=novacredentials, endpoint=endpoint, project= project, imagepath=imagepath, volumetype=volumetype, keystonetests=keystonetests, glancetests=glancetests, cindertests=cindertests, neutrontests=neutrontests, novatests=novatests, heattests=heattests, ceilometertests=ceilometertests, swifttests=swifttests, verbose=verbose, timeout=timeout, embedded=embedded, externalid=externalid)
	#testing
	if listservices:
		print o.listservices()
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
				o._novabefore(externalid)
			except:
				o._novaafter()
				o._clean()
		flavors, keypairs, servers = o.novatest()
	if testheat or testall:
		if o.embedded:
			o._novabefore(externalid)
		stacks = o.heattest()
	if testceilometer or testceilometer:
		alarms = o.ceilometertest()
	if testswift or testall:
		containers = o.swifttest()
	if testha or testall:
		o.alltest()
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
		o.novaclean(flavors, keypairs, servers)
	if testheat or testall:
		o.heatclean(stacks)
	if testceilometer or testceilometer:
		o.ceilometerclean(alarms)
	if testswift or testall:
		o.swiftclean(containers)
	#reporting
	if testkeystone or testglance or testcinder or testneutron or testnova or testheat or testceilometer or testswift or testha or testall:
		if verbose:
			print "Testing Keystone..."
			print "Final report:"
		print o._printreport()
		if embedded:	
			if testnova or testheat:
				o._novaafter()
			o._clean()
