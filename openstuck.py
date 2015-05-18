#!/usr/bin/python
"""
script to quickly test an openstack installation
based on api info found at http://www.ibm.com/developerworks/cloud/library/cl-openstack-pythonapis/
"""

import multiprocessing
import optparse
import os
from prettytable import PrettyTable
import sys
import time
import keystoneclient.v2_0.client as keystoneclient
import glanceclient.v2.client as glanceclient
import cinderclient.v2.client as cinderclient
from neutronclient.neutron import client as neutronclient
from novaclient import client as novaclient
from heatclient import client as heatclient
import json
import yaml


__author__     = 'Karim Boumedhel'
__credits__    = ['Karim Boumedhel']
__license__    = 'GPL'
__version__    = '0.1'
__maintainer__ = 'Karim Boumedhel'
__email__      = 'karim.boumedhel@gmail.com'
__status__     = 'Testing'


keystonedefaulttests     = ['Create_Tenant', 'Create_User', 'Create_Role', 'Add_Role', 'ListRole', 'Authenticate_User', 'Delete_User', 'Delete_Role', 'Delete_Tenant']
glancedefaulttests       = ['Create_Image', 'List_Image', 'Delete_Image']
cinderdefaulttests      = ['Create_Volume', 'List_Volume', 'Delete_Volume']
cinderbackupdefaulttests = ['Create_Backup', 'List_Backup', 'Delete_Backup']
neutrondefaulttests      = ['Create_Network', 'List_Network', 'Delete_Network']
novadefaulttests         = ['Create_Server', 'List_Server', 'Delete_Server']
heatdefaulttests         = ['Create_Stack', 'List_Stack', 'Delete_Stack']
ceilometerdefaulttests   = ['Create_Alarm', 'List_Alarm', 'Delete_Alarm']
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
	def __init__(self, keystonecredentials, novacredentials, project='', endpoint='publicURL', keystonetests=None, glancetests=None, cindertests=None, neutrontests=None, novatests=None, heattests=None, ceilometertests=None, swifttests=None, imagepath=None, volumetype=None, debug=False,verbose=False):
		self.auth_url    = keystonecredentials['auth_url']
		self.debug       = debug
		self.novacredentials     = novacredentials
		try:
			self.keystone    = keystoneclient.Client(**keystonecredentials)
		except Exception as e:
			print "Got the following issue:"
			print e
			os._exit(1)
		self.keystonetests   = keystonetests 
		self.glancetests     = glancetests 
		self.cindertests     = cindertests 
		self.neutrontests    = neutrontests 
		self.novatests       = novatests 
		self.heattests       = heattests 
		self.ceilometertests = ceilometertests 
		self.swifttests      = swifttests
		self.output          = PrettyTable(['Category', 'Description', 'Concurrency', 'Repeat', 'Time(Seconds)', 'Result'])
		self.output.align['Category'] = "l"
		self.endpoint        = endpoint
        	self.tenant          = "%stenant" % project
        	self.user            = "%suser" % project
        	self.password        = "%spassword" % project
        	self.role            = "%srole" % project
        	self.tenant          = "%stenant" % project
        	self.email           = "%suser@xxx.com" % project
        	self.description     = "Members of the %s corp" % project
        	self.image           = "%simage" % project
		self.imagepath       = imagepath
        	self.volume          = "%svolume" % project
        	self.volumetype      = volumetype
        	self.network         = "%snetwork" % project
        	self.server          = "%sserver" % project
        	self.stack           = "%sstack" % project
        	self.alarm           = "%salarm" % project
        	self.container       = "%scontainer" % project
		self.debug           = debug
		self.verbose         = verbose
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
		if not verbose or len(rows) == 0:
			return
		for row in rows:
			self.output.add_row(row)
	def _report(self, category, test, concurrency, repeat, time, errors):
		if test in errors:
			self.output.add_row([category, test, concurrency, repeat,'', "Failures: %d" % errors.count(test)])
		else:
			self.output.add_row([category, test, concurrency, repeat,time, 'OK'])
	def Add_Role(self, keystone, user, role, tenant, errors=None, output=None, verbose=False):
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
			results = error
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Add_Role: %s to %s %s seconds" % (role.name, user.name, runningtime)
			output.append(['keystone', 'Add_Role', role.name, role.name, runningtime, results,])
	def Authenticate_User(self, user, password, auth_url, tenant=None, errors=None, output=None, verbose=False):
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
			results = error
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Authenticate_User: %s in %s %s seconds" % (user.name, tenant.name, runningtime)
			output.append(['keystone', 'Authenticate_User', user.name, user.name, runningtime, results,])
	def Create_Image(self, glance, image, imagepath, images=None, errors=None, output=None, verbose=False):
		starttime = time.time()
		try:
			newimage = glance.images.create(name=image, visibility='public', disk_format='qcow2',container_format='bare')
			if imagepath is not None:
				with open(imagepath,'rb') as data:
                        		glance.images.upload(newimage.id, data)
			results = 'OK'
			images.append(newimage.id)
		except Exception as error:
			errors.append('Create_Image')
			results = error
			images.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Image: %s %s seconds" % (image, runningtime )
			output.append(['glance', 'Create_Image', image, image, runningtime, results,])
	def Create_Network(self, neutron, network, networks=None, errors=None, output=None, verbose=False):
		starttime = time.time()
		try:
			newnetwork = {'name': network, 'admin_state_up': True}
			newnetwork = neutron.create_network({'network':newnetwork})
			results = 'OK'
			networks.append(newnetwork['network']['id'])
		except Exception as error:
			errors.append('Create_Network')
			results = error
			networks.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Network: %s %s seconds" % (network, runningtime )
			output.append(['neutron', 'Create_Network', network, network, runningtime, results,])
	def Create_Volume(self, cinder, volume, volumes=None, errors=None, output=None, verbose=False):
		starttime = time.time()
		try:
			newvolume = cinder.volumes.create(size=1, name=volume)
			results = 'OK'
			#while cinder.volumes.get(newvolume.id).status != 'available':
        		#	time.sleep(0.2)
			volumes.append(newvolume.id)
		except Exception as error:
			errors.append('Create_Volume')
			results = error
			volumes.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Volume: %s %s seconds" % (volume, runningtime )
			output.append(['cinder', 'Create_Volume', volume, volume, runningtime, results,])
	def Create_Role(self, keystone, name, roles=None, errors=None, output=None, verbose=False):
		starttime = time.time()
		try:
			role = keystone.roles.create(name=name)
			results = 'OK'
			roles.append(role.id)
		except Exception as error:
			errors.append('Create_Role')
			results = error
			roles.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Create_Role: %s %s seconds" % (name, runningtime)
			output.append(['keystone', 'Create_Role', name, name, runningtime, results,])
	def Create_Server(self, nova, server, servers=None, errors=None, output=None, verbose=False):
		starttime = time.time()
		try:
			image   = os.environ['OS_NOVA_IMAGE']   if os.environ.has_key('OS_NOVA_IMAGE')   else 'cirros'
			flavor  = os.environ['OS_NOVA_FLAVOR']  if os.environ.has_key('OS_NOVA_FLAVOR')  else 'm1.tiny'
			network = os.environ['OS_NOVA_NETWORK'] if os.environ.has_key('OS_NOVA_NETWORK') else 'private'
			image = nova.images.find(name=image)
			flavor = nova.flavors.find(name=flavor)
			networkid = nova.networks.find(label=network).id
			nics = [{'net-id': networkid}]
			newserver = nova.servers.create(name=server, image=image, flavor=flavor, nics=nics)
			results = 'OK'
			servers.append(newserver.id)
		except Exception as error:
			errors.append('Create_Server')
			results = error
			servers.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Server: %s %s seconds" % (server, runningtime )
			output.append(['nova', 'Create_Server', server, server, runningtime, results,])
	def Create_Stack(self, heat, stack, stacks=None, errors=None, output=None, verbose=False):
		starttime = time.time()
		try:
			template  = os.environ['OS_HEAT_TEMPLATE']   if os.environ.has_key('OS_HEAT_TEMPLATE')   else None
			if template is None:
				image         = os.environ['OS_NOVA_IMAGE']   if os.environ.has_key('OS_NOVA_IMAGE')   else 'cirros'
				flavor        = os.environ['OS_NOVA_FLAVOR']  if os.environ.has_key('OS_NOVA_FLAVOR')  else 'm1.tiny'
				network       = os.environ['OS_NOVA_NETWORK'] if os.environ.has_key('OS_NOVA_NETWORK') else 'private'
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
			results = 'OK'
			stacks.append(newstack['stack']['id'])
		except Exception as error:
			errors.append('Create_Stack')
			results = error
			stacks.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Stack: %s %s seconds" % (stack, runningtime )
			output.append(['heat', 'Create_Stack', stack, stack, runningtime, results,])
	def Create_Tenant(self, keystone, name, description, tenants=None, errors=None, output=None, verbose=False):
		starttime = time.time()
		try:
			tenant = keystone.tenants.create(tenant_name=name, description=description,enabled=True)
			results = 'OK'
			tenants.append(tenant.id)
		except Exception as error:
			errors.append('Create_Tenant')
			results = error
			tenants.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_Tenant:%s %s seconds" % (name, runningtime)
			output.append(['keystone', 'Create_Tenant', name, name, runningtime, results,])
	def Create_TypedVolume(self, cinder, volume, volumetype, volumes=None, errors=None, output=None, verbose=False):
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
			results = 'OK'
			#while cinder.volumes.get(newvolume.id).status != 'available':
        		#	time.sleep(0.2)
			volumes.append(newvolume.id)
		except Exception as error:
			errors.append('Create_TypedVolume')
			results = error
			volumes.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_TypedVolume: %s %s seconds" % (volume, runningtime )
			output.append(['cinder', 'Create_TypedVolume', volume, volume, runningtime, results,])
	def Create_User(self, keystone, name, password, email,tenant, users=None, errors=None, output=None, verbose=False):
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
			results = error
			users.append(None)
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Create_User: %s %s seconds" % (name, runningtime)
			output.append(['keystone', 'Create_User', name, name, runningtime, results,])
	def Delete_Image(self, glance, image, errors=None, output=None, verbose=False):
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
			results = error
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Image: %s %s seconds" % (imagename, runningtime)
			output.append(['glance', 'Delete_Image', imagename, imagename, runningtime, results,])
	def Delete_Network(self, neutron, network, errors=None, output=None, verbose=False):
		starttime = time.time()
		if network is None:
			errors.append('Delete_Network')
			results = 'NotRun'
			if verbose:
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
			results = error
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Network: %s %s seconds" % (networkname, runningtime)
			output.append(['neutron', 'Delete_Network', networkname, networkname, runningtime, results,])
	def Delete_Role(self, keystone, role, errors=None, output=None, verbose=False):
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
			results = error
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Role: %s %s seconds" % (rolename, runningtime)
			output.append(['keystone', 'Delete_Role', rolename, rolename, runningtime, results,])
	def Delete_Server(self, nova, server, errors=None, output=None, verbose=False):
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
		except Exception as error:
			errors.append('Delete_Server')
			results = error
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Server: %s %s seconds" % (servername, runningtime)
			output.append(['nova', 'Delete_Server', servername, servername, runningtime, results,])
	def Delete_Stack(self, heat, stack, errors=None, output=None, verbose=False):
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
		except Exception as error:
			errors.append('Delete_Stack')
			results = error
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Stack: %s %s seconds" % (stackname, runningtime)
			output.append(['heat', 'Delete_Stack', stackname, stackname, runningtime, results,])
	def Delete_Tenant(self, keystone, tenant, errors=None, output=None, verbose=False):
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
			results = error
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Delete_Tenant: %s %s seconds" % (tenantname, runningtime)
			output.append(['keystone', 'Delete_Tenant', tenantname, tenantname, runningtime, results,])
	def Delete_User(self, keystone, user, errors=None, output=None, verbose=False):
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
			results = error
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime) 
			print "Delete_User: %s %s seconds" % (username, runningtime)
			output.append(['keystone', 'Delete_User', username, username, runningtime, results,])
	def Delete_Volume(self, cinder, volume, errors=None, output=None, verbose=False):
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
			#while cinder.volumes.get(volume.id).status != 'available':
        		#	time.sleep(0.2)
			results = 'OK'
		except Exception as error:
			errors.append('Delete_Volume')
			results = error
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "Delete_Volume: %s %s seconds" % (volumename, runningtime)
			output.append(['cinder', 'Delete_Volume', volumename, volumename, runningtime, results,])
	def List_Image(self, glance, image, errors=None, output=None, verbose=False):
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
			results = error
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Image: %s %s seconds" % (image.name, runningtime)
			output.append(['glance', 'List_Image', image.name, image.name, runningtime, results,])
	def List_Network(self, neutron, network, errors=None, output=None, verbose=False):
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
			if len(findnetworks) == 0:
				raise Exception('Network not found')
			results = 'OK'
		except Exception as error:
			errors.append('List_Network')
			results = error
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Network: %s %s seconds" % (network_name, runningtime)
			output.append(['neutron', 'List_Network', network_name, network_name, runningtime, results,])
	def List_Role(self, keystone, role, errors=None, output=None, verbose=False):
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
			results = error
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Role: %s %s seconds" % (role.name, runningtime)
			output.append(['keystone', 'List_Role', role.name, role.name, runningtime, results,])
	def List_Server(self, nova, server, errors=None, output=None, verbose=False):
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
			results = error
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Server: %s %s seconds" % (server_name, runningtime)
			output.append(['nova', 'List_Server', server_name, server_name, runningtime, results,])
	def List_Stack(self, heat, stack, errors=None, output=None, verbose=False):
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
			results = error
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Stack: %s %s seconds" % (stackname, runningtime)
			output.append(['heat', 'List_Stack', stackname, stackname, runningtime, results,])
	def List_Volume(self, cinder, volume, errors=None, output=None, verbose=False):
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
			results = error
		if verbose:
			endtime     = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			print "List_Volume: %s %s seconds" % (volume.name, runningtime)
			output.append(['cinder', 'List_Volume', volume.name, volume.name, runningtime, results,])
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
	def cinderclean(self, volumes):
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
	def neutronclean(self, networks):
		if self.verbose:
			print "Cleaning Neutron..."
		keystone = self.keystone
		endpoint = keystone.service_catalog.url_for(service_type='network',endpoint_type=self.endpoint)
		neutron = neutronclient.Client('2.0',endpoint_url=endpoint, token=keystone.auth_token)
		for network in networks:
			if network is None:
				continue
			else:
				try:
					neutron.networks.delete(network['id'])
				except:
					continue
	def novaclean(self, servers):
		if self.verbose:
			print "Cleaning Nova..."
		nova     = novaclient.Client('2', **self.novacredentials)
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
		keystone = self.keystone
		endpoint = keystone.service_catalog.url_for(service_type='compute',endpoint_type=self.endpoint)
		nova     = ceilometerclient.Client(endpoint, token=keystone.auth_token)
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
		keystone = self.keystone
		endpoint = keystone.service_catalog.url_for(service_type='object',endpoint_type=self.endpoint)
		swift    = swiftclient.Client(endpoint, token=keystone.auth_token)
		for container in containers:
			if container is None:
				continue
			else:
				try:
					swift.containers.delete(container.id)
				except:
					continue
	def keystonetest(self):
		category = 'keystone'
		tests    = self.keystonetests
		mgr = multiprocessing.Manager()
		tenants = mgr.list()
		users   = mgr.list()
		roles   = mgr.list()
		errors  = mgr.list()
		if self.verbose:
			print "Testing Keystone..."
		keystone = self.keystone

                test   = 'Create_Tenant'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Tenant, args=(keystone, "%s-%d-%d" % (self.tenant, step,number), self.description, tenants, errors, output, self.verbose,)) for number in range(concurrency) ]
				self._process(jobs)
			endtime    = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			tenants = [ keystone.tenants.get(tenant_id) if tenant_id is not None else None for tenant_id in tenants]

		if test in tests:
	        	test   = 'Create_User'
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_User, args=(keystone, "%s-%d-%d" % (self.user, step, number), self.password, self.email, self._first(tenants), users, errors, output, self.verbose,)) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			users = [ keystone.users.get(user_id) if user_id is not None else None for user_id in users ]

		if test in tests:
	        	test   = 'Create_Role'
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Role, args=(keystone, "%s-%d-%d" % (self.role, step, number), roles, errors, output, self.verbose, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			roles = [ keystone.roles.get(role_id) if role_id is not None else None for role_id in roles ]

		if test in tests:
	        	test   = 'Add_Role'
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Add_Role, args=(keystone, self._first(users), role, self._first(tenants), errors, output, self.verbose, )) for role in roles ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		if test in tests:
	        	test   = 'List_Role'
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Role, args=(keystone, role, errors, output, self.verbose, )) for role in roles ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

	        test   = 'Authenticate_User'
		output = mgr.list()
                concurrency, repeat = metrics(test)
		starttime = time.time()
		jobs = [ multiprocessing.Process(target=self.Authenticate_User, args=(user, self.password, self.auth_url, self._first(tenants), errors, output, self.verbose, )) for user in users ]
		self._process(jobs)
		endtime = time.time()
		runningtime = "%0.3f" % (endtime -starttime)
		if verbose:
			print "%s  %s seconds" % (test, runningtime)
		self._report(category, test, concurrency, repeat, runningtime, errors)
		self._addrows(verbose, output)

		if test in tests:
			test   = 'Delete_User'
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_User, args=(keystone, user, errors, output, self.verbose, )) for user in users ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		if test in tests:
			test   = 'Delete_Role'
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Role, args=(keystone, role, errors, output, self.verbose, )) for role in roles ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		if test in tests:
			test   = 'Delete_Tenant'
			output = mgr.list()
	                concurrency, repeat = metrics(test)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Tenant, args=(keystone, tenant, errors, output, self.verbose, )) for tenant in tenants ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
	
		self.keystoneclean(tenants, users, roles)

	def glancetest(self):
		category = 'glance'
		tests = self.glancetests
		mgr = multiprocessing.Manager()
		errors  = mgr.list()
		images = mgr.list()
		if self.verbose:
			print "Testing Glance..."
		keystone = self.keystone
		endpoint = keystone.service_catalog.url_for(service_type='image',endpoint_type=self.endpoint)
		glance = glanceclient.Client(endpoint, token=keystone.auth_token)


		test = 'Create_Image'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Image, args=(glance, "%s-%d-%d" % (self.image, step, number), self.imagepath, images, errors, output, self.verbose, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			images = [ glance.images.get(image_id) if image_id is not None else None for image_id in images ]

		test = 'List_Image'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Image, args=(glance, image, errors, output, self.verbose, )) for image in images ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

                test = 'Delete_Image'
		if test in tests:
			output = mgr.list()
	                concurrency, repeat = metrics(test)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Image, args=(glance, image, errors, output, self.verbose, )) for image in images ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
	
		self.glanceclean(images)

	def cindertest(self):
		category = 'cinder'
		tests = self.cindertests 
		mgr = multiprocessing.Manager()
		errors  = mgr.list()
		volumes = mgr.list()
		if self.verbose:
			print "Testing Cinder..."
		keystone = self.keystone
		cinder = cinderclient.Client(**self.novacredentials)
	
		test = 'Create_Volume'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Volume, args=(cinder, "%s-%d-%d" % (self.volume, step, number), volumes, errors, output, self.verbose, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			volumes = [ cinder.volumes.get(volume_id) if volume_id is not None else None for volume_id in volumes ]

		test = 'Create_TypedVolume'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_TypedVolume, args=(cinder, "%s-%s-%d-%d" % (self.volume, self.volumetype, step, number), self.volumetype, volumes, errors, output, self.verbose, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test = 'List_Volume'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Volume, args=(cinder, volume, errors, output, self.verbose, )) for volume in volumes ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test = 'Delete_Volume'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Volume, args=(cinder, volume, errors, output, self.verbose, )) for volume in volumes ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
		self.cinderclean(volumes)

	def neutrontest(self):
		category = 'neutron'
		tests    = self.neutrontests 
		mgr      = multiprocessing.Manager()
		errors   = mgr.list()
		networks = mgr.list()
		if self.verbose:
			print "Testing Neutron..."
		keystone = self.keystone
		endpoint = keystone.service_catalog.url_for(service_type='network',endpoint_type=self.endpoint)
		neutron = neutronclient.Client('2.0',endpoint_url=endpoint, token=keystone.auth_token)

		test = 'Create_Network'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Network, args=(neutron, "%s-%d-%d" % (self.network, step, number), networks, errors, output, self.verbose, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			networks = [ network if network is not None else None for network in neutron.list_networks()['networks'] if network['id'] in networks ]

		test = 'List_Network'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Network, args=(neutron, network, errors, output, self.verbose, )) for network in networks ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test = 'Delete_Network'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Network, args=(neutron, network, errors, output, self.verbose, )) for network in networks ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
		self.neutronclean(networks)
	def novatest(self):
		category  = 'nova'
		tests     = self.novatests 
		mgr       = multiprocessing.Manager()
		errors    = mgr.list()
		servers = mgr.list()
		if self.verbose:
			print "Testing Nova..."
		keystone = self.keystone
		nova = novaclient.Client('2', **self.novacredentials)
		test = 'Create_Server'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Server, args=(nova, "%s-%d-%d" % (self.server, step, number), servers, errors, output, self.verbose, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			servers = [ nova.servers.get(server_id) if server_id is not None else None for server_id in servers ]

		test = 'List_Server'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Server, args=(nova, server, errors, output, self.verbose, )) for server in servers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test = 'Delete_Server'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Server, args=(nova, server, errors, output, self.verbose, )) for server in servers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
		self.novaclean(servers)
	def heattest(self):
		category = 'heat'
		tests = self.heattests 
		mgr = multiprocessing.Manager()
		errors  = mgr.list()
		stacks = mgr.list()
		if self.verbose:
			print "Testing Heat..."
		keystone = self.keystone
		endpoint = keystone.service_catalog.url_for(service_type='orchestration',endpoint_type=self.endpoint)
		heat = heatclient.Client('1', endpoint=endpoint, token=keystone.auth_token)
	
		test = 'Create_Stack'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Stack, args=(heat, "%s-%d-%d" % (self.stack, step, number), stacks, errors, output, self.verbose, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			stacks = [ heat.stacks.get(stack_id) if stack_id is not None else None for stack_id in stacks ]

		test = 'List_Stack'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Stack, args=(heat, stack, errors, output, self.verbose, )) for stack in stacks ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test = 'Delete_Stack'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Stack, args=(heat, stack, errors, output, self.verbose, )) for stack in stacks ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
		self.heatclean(stacks)
	def ceilometertest(self):
		category = 'ceilometer'
		tests = self.ceilometertests 
		mgr = multiprocessing.Manager()
		errors  = mgr.list()
		alarms = mgr.list()
		if self.verbose:
			print "Testing Ceilometer..."
		keystone = self.keystone
		endpoint = keystone.service_catalog.url_for(service_type='metering',endpoint_type=self.endpoint)
		ceilometer = ceilometerclient.Client(endpoint, token=keystone.auth_token)
	
		test = 'Create_Alarm'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Alarm, args=(ceilometer, "%s-%d-%d" % (self.alarm, step, number), alarms, errors, output, self.verbose, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			alarms = [ ceilometer.alarms.get(alarm_id) if alarm_id is not None else None for alarm_id in alarms ]

		test = 'List_Alarm'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Alarm, args=(ceilometer, alarm, errors, output, self.verbose, )) for alarm in alarms ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test = 'Delete_Alarm'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Alarm, args=(ceilometer, alarm, errors, output, self.verbose, )) for alarm in alarms ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
		self.ceilometerclean(alarms)
	def swifttest(self):
		category = 'swift'
		tests = self.swifttests 
		mgr = multiprocessing.Manager()
		errors  = mgr.list()
		containers = mgr.list()
		if self.verbose:
			print "Testing Swift..."
		keystone = self.keystone
		endpoint = keystone.service_catalog.url_for(service_type='container',endpoint_type=self.endpoint)
		swift = swiftclient.Client(endpoint, token=keystone.auth_token)
	
		test = 'Create_Container'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			for step in range(repeat):
				jobs = [ multiprocessing.Process(target=self.Create_Container, args=(swift, "%s-%d-%d" % (self.container, step, number), containers, errors, output, self.verbose, )) for number in range(concurrency) ]
				self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
			containers = [ ceilometer.containers.get(container_id) if container_id is not None else None for container_id in containers ]

		test = 'List_Container'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.List_Container, args=(swift, container, errors, output, self.verbose, )) for container in containers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)

		test = 'Delete_Container'
		if test in tests:
			output = mgr.list()
                	concurrency, repeat = metrics(test)
			starttime = time.time()
			jobs = [ multiprocessing.Process(target=self.Delete_Alarm, args=(swift, container, errors, output, self.verbose, )) for container in containers ]
			self._process(jobs)
			endtime = time.time()
			runningtime = "%0.3f" % (endtime -starttime)
			if verbose:
				print "%s  %s seconds" % (test, runningtime)
			self._report(category, test, concurrency, repeat, runningtime, errors)
			self._addrows(verbose, output)
		self.swiftclean(containers)

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
	parser.add_option('-v', '--verbose', dest='verbose', default=False, action='store_true', help='Verbose mode')
	(options, args) = parser.parse_args()
	listservices    = options.listservices
	testkeystone    = options.testkeystone
	testglance      = options.testglance
	testceilometer  = options.testceilometer
	testcinder      = options.testcinder
	testneutron     = options.testneutron
	testnova        = options.testnova
	testheat        = options.testheat
	testswift       = options.testswift
	testha          = options.testha
	testall         = options.testall
	project         = options.project
	verbose         = options.verbose
	try:
		keystonecredentials = _keystonecreds()
		novacredentials     = _novacreds()
		endpoint            = os.environ['OS_ENDPOINT_TYPE']                 if os.environ.has_key('OS_ENDPOINT_TYPE')     else 'publicURL'
		keystonetests       = os.environ['OS_KEYSTONE_TESTS'].split(',')     if os.environ.has_key('OS_KEYSTONE_TESTS')     else keystonedefaulttests
		glancetests         = os.environ['OS_GLANCE_TESTS'].split(',')       if os.environ.has_key('OS_GLANCE_TESTS')       else glancedefaulttests
		cindertests         = os.environ['OS_CINDER_TESTS'].split(',')       if os.environ.has_key('OS_CINDER_TESTS')       else cinderdefaulttests
		neutrontests        = os.environ['OS_NEUTRON_TESTS'].split(',')      if os.environ.has_key('OS_NEUTRON_TESTS')      else neutrondefaulttests
		novatests           = os.environ['OS_NOVA_TESTS'].split(',')         if os.environ.has_key('OS_NOVA_TESTS')         else novadefaulttests
		heattests           = os.environ['OS_HEAT_TESTS'].split(',')         if os.environ.has_key('OS_HEAT_TESTS')         else heatdefaulttests
		swifttests          = os.environ['OS_SWIFT_TESTS'].split(',')        if os.environ.has_key('OS_SWIFT_TESTS')        else swiftdefaulttests
		ceilometertests     = os.environ['OS_CEILOMETER_TESTS'].split(',')   if os.environ.has_key('OS_CEILOMETER_TESTS')   else ceilometerdefaulttests
		imagepath           = os.environ['OS_GLANCE_IMAGE_PATH']             if os.environ.has_key('OS_GLANCE_IMAGE_PATH') else None
		volumetype          = os.environ['OS_CINDER_VOLUME_TYPE']            if os.environ.has_key('OS_CINDER_VOLUME_TYPE') else None
	except Exception as e:
		print "Missing environment variables. source your openrc file first"
		print e
	    	os._exit(1)

	o = Openstuck(keystonecredentials=keystonecredentials, novacredentials=novacredentials, endpoint=endpoint, project= project, imagepath=imagepath, volumetype=volumetype, keystonetests=keystonetests, glancetests=glancetests, cindertests=cindertests, neutrontests=neutrontests, novatests=novatests, heattests=heattests, ceilometertests=ceilometertests, swifttests=swifttests, verbose=verbose)
	
	if listservices:
		print o.listservices()
	    	sys.exit(0)
	if testkeystone or testall:
		o.keystonetest()
	if testglance or testall:
		o.glancetest()
	if testcinder or testall:
		o.cindertest()
	if testneutron or testall:
		o.neutrontest()
	if testnova or testall:
		o.novatest()
	if testheat or testall:
		o.heattest()
	if testceilometer or testceilometer:
		o.heattest()
	if testswift or testall:
		o.swifttest()
	if testha or testall:
		o.alltest()
	if testkeystone or testglance or testcinder or testneutron or testnova or testheat or testswift or testha or testall:
		if verbose:
			print "Testing Keystone..."
			print "Final report:"
		print o._printreport()
