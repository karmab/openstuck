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

__author__     = 'Karim Boumedhel'
__credits__    = ['Karim Boumedhel']
__license__    = 'GPL'
__version__    = '2.0'
__maintainer__ = 'Karim Boumedhel'
__email__      = 'karim.boumedhel@gmail.com'
__status__     = 'Testing'


keystonedefaulttests   = ['Create_Tenant', 'Create_User', 'Create_Role', 'Add_Role', 'ListRole', 'Authenticate_User', 'Delete_User', 'Delete_Role', 'Delete_Tenant']
glancedefaulttests   = ['Create_Image','List_Image','Delete_Image']

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
	def __init__(self, keystonecredentials, novacredentials, endpoint, tenant='acmetenant', user='acmeuser', password='acmepassword', role='acmerole', email='acme@xxx.com', description='Members of the ACME Group', image='acmeimage', imagepath=None, debug=False,verbose=False):
		self.auth_url    = keystonecredentials['auth_url']
		self.novacreds   = novacredentials
		self.debug       = debug
		self.keystone    = keystoneclient.Client(**keystonecredentials)
		#self.output      = PrettyTable(['Category', 'Description', 'Concurrency', 'Repeat', 'Result'])
		self.output      = PrettyTable(['Category', 'Description', 'Result'])
		self.output.align['Category'] = "l"
		self.endpoint    = endpoint
		self.tenant      = tenant
		self.user        = user
		self.password    = password
		self.role 	 = role
		self.email       = email
		self.description = description
		self.image       = image
		self.imagepath   = imagepath
		self.debug       = debug
		self.verbose     = verbose
	def _process(self, jobs):
		for j in jobs:
                	j.start()
		for j in jobs:
			j.join()
	def Authenticate_User(self, name, password, auth_url, tenant_name=None, verbose=False):
		usercredentials = { 'username' : name, 'password' : password, 'auth_url' : auth_url , 'tenant_name' : tenant_name }
		userkeystone = keystoneclient.Client(**usercredentials)
		if verbose:
			print "Authenticate_User: %s in %s" % (name, tenant_name)
	def Create_Tenant(self, keystone, name, description, tenants=None, verbose=False):
		tenant = keystone.tenants.create(tenant_name=name, description=description,enabled=True)
		if verbose:
			print "Create_Tenant: %s" % tenant.name
		tenants.append(tenant.id)
	def Create_User(self, keystone, name, password, email,tenant_id, users=None, verbose=False):
		user = keystone.users.create(name=name, password=password, email=email, tenant_id=tenant_id)
		if verbose:
			print "Create_User: %s" % user.name
		users.append(user.id)
	def Create_Role(self, keystone, name, roles=None, verbose=False):
		role = keystone.roles.create(name=name)
		if verbose:
			print "Create_Role: %s" % role.name
		roles.append(role.id)
	def Add_Role(self, keystone, user, role, tenant, verbose=False):
		keystone.roles.add_user_role(user, role, tenant)
		if verbose:
			print "Add_Role: %s to %s" % (role.name, user.name)
	def List_Role(self, keystone, verbose=False):
		roles = keystone.roles.list()
		if verbose:
			for role in roles:
				print "List_Role: %s" % role.name
	def Delete_Role(self, keystone, role, verbose=False):
		role.delete()
		if verbose:
			print "Delete_Role: %s" % role.name
	def Delete_Tenant(self, keystone, tenant, verbose=False):
		tenant.delete()
		if verbose:
			print "Delete_Tenant: %s" % tenant.name
	def Delete_User(self, keystone, user, verbose=False):
		user.delete()
		if verbose:
			print "Delete_User: %s" % user.name
	def _addreport(self, category, tests, errorindex, error):
		for index, test in enumerate(tests):
			if index == errorindex:
				self.output.add_row([category, test, error])
			if index < errorindex:
				self.output.add_row([category, test, 'OK'])
			if index > errorindex:
				self.output.add_row([category,test,'N/A'])
	def report(self):
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
		try:
			print "Cleaning Keystone..."
			keystone = self.keystone
			for tenant in tenants:
				tenant.delete()
			for user in users:
				user.delete()
			for role in roles:
				role.delete()
		except:	
			pass
	def glanceclean(self, image):
		try:
			print "Cleaning Glance..."
			for img in glance.images.list():
				if img['name'] == image:
					glance.images.delete(img['id'])
		except:
			pass
	def keystonetest(self):
		errorindex   = 0
		errordetails = None
		try:
			mgr = multiprocessing.Manager()
			tenants = mgr.list()
			users   = mgr.list()
			roles   = mgr.list()
			print "Testing Keystone..."
			keystone = self.keystone
                        test = 'Create_Tenant'
                        concurrency, repeat = metrics(test)
			jobs = [ multiprocessing.Process(target=self.Create_Tenant, args=(keystone, "%s%d" % (self.tenant, i), self.description, tenants, self.verbose,)) for i in range(concurrency) ]
			self._process(jobs)
			tenants = [ keystone.tenants.get(tenant_id) for tenant_id in tenants ]
			errorindex  += 1
	                test = 'Create_User'
                        concurrency, repeat = metrics(test)
			jobs = [ multiprocessing.Process(target=self.Create_User, args=(keystone, "%s%d" % (self.user, i), self.password, self.email, tenants[0].id, users, self.verbose,)) for i in range(concurrency) ]
			self._process(jobs)
			users = [ keystone.users.get(user_id) for user_id in users ]
			errorindex  += 1

	                test = 'Create_Role'
                        concurrency, repeat = metrics(test)
			jobs = [ multiprocessing.Process(target=self.Create_Role, args=(keystone, "%s%d" % (self.role, i), roles, self.verbose, )) for i in range(concurrency) ]
			self._process(jobs)
			roles = [ keystone.roles.get(role_id) for role_id in roles ]
			errorindex  += 1

	                test = 'Add_Role'
                        concurrency, repeat = metrics(test)
			jobs = [ multiprocessing.Process(target=self.Add_Role, args=(keystone, users[0], roles[i], tenants[0], self.verbose, )) for i in range(concurrency) ]
			self._process(jobs)
			errorindex  += 1

	                test = 'List_Role'
                        concurrency, repeat = metrics(test)
			jobs = [ multiprocessing.Process(target=self.List_Role, args=(keystone, self.verbose,)) for i in range(concurrency) ]
			self._process(jobs)
			errorindex  += 1

	                test ='Authenticate_User'
                        concurrency, repeat = metrics(test)
			jobs = [ multiprocessing.Process(target=self.Authenticate_User, args=(users[i].name, self.password, self.auth_url, tenants[0].name, self.verbose, )) for i in range(concurrency) ]
			self._process(jobs)
			errorindex  += 1

			test = 'Delete_User'
                        concurrency, repeat = metrics(test)
			jobs = [ multiprocessing.Process(target=self.Delete_User, args=(keystone, users[i], self.verbose, )) for i in range(concurrency) ]
			self._process(jobs)
			errorindex  += 1

			test = 'Delete_Role'
                        concurrency, repeat = metrics(test)
			jobs = [ multiprocessing.Process(target=self.Delete_Role, args=(keystone, roles[i], self.verbose, )) for i in range(concurrency) ]
			self._process(jobs)
			errorindex  += 1

			test = 'Delete_Tenant'
                        concurrency, repeat = metrics(test)
			jobs = [ multiprocessing.Process(target=self.Delete_Tenant, args=(keystone, tenants[i], self.verbose, )) for i in range(concurrency) ]
			self._process(jobs)
			errorindex  += 1
		except Exception as errordetails:
			pass
		self._addreport('keystone', keystonetests, errorindex, errordetails)
		self.keystoneclean(tenants, users, roles)
	def glancetest(self):
		errorindex   = 0
		errordetails = None
		try:
			print "Testing Glance..."
			keystone = self.keystone
			endpoint = keystone.service_catalog.url_for(service_type='image',endpoint_type=self.endpoint)
			glance = glanceclient.Client(endpoint, token=keystone.auth_token)
                        imagetest = 'Create_Image'
			if not self.image:
				 raise Exception('No image defined with the OS_GLANCE_IMAGE environment variable')
			with open(self.imagepath,'rb') as data:
    				newimage = glance.images.create(name=self.image, visibility='public', disk_format='qcow2',container_format='bare')
				glance.images.upload(newimage.id, data)
			errorindex  += 1
                        listimagetest = 'List_Image'
			glance.images.get(newimage.id)
			errorindex  += 1
                        deleteimagetest = 'Delete_Image'
			glance.images.delete(newimage.id)
			errorindex  += 1
		except Exception as errordetails:
			pass
		self._addreport('glance', glancetests, errorindex, errordetails)
		self.glanceclean(self.image)
	
	 
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
	testinggroup.add_option('-N', '--nova', dest='testnova', action='store_true',default=False, help='Test neutron')
	testinggroup.add_option('-Q', '--neutron', dest='testneutron', action='store_true',default=False, help='Test neutron')
	testinggroup.add_option('-S', '--swift', dest='testswift', action='store_true',default=False, help='Test swift')
	parser.add_option_group(testinggroup)
	parser.add_option('-p', '--project', dest='project', default='acme', type='string', help='Project name to prefix for all elements. defaults to acme')
	parser.add_option('-v', '--verbose', dest='verbose', default=False, action='store_true', help='Verbose mode')
	(options, args) = parser.parse_args()
	listservices    = options.listservices
	testkeystone    = options.testkeystone
	testglance      = options.testglance
	testcinder      = options.testcinder
	testneutron     = options.testneutron
	testnova        = options.testnova
	testheat        = options.testheat
	testswift       = options.testswift
	testha          = options.testha
	testall         = options.testall
	project         = options.project
	verbose         = options.verbose
	user               = "%suser" % project
	password           = "%spassword" % project
	role               = "%srole" % project
	tenant             = "%stenant" % project
	email              = "%suser@xxx.com" % project
	description        = "Members of the %s corp" % project
	image              = "%simage" % project
	try:
		keystonecredentials = _keystonecreds()
		novacredentials     = _novacreds()
		endpoint            = os.environ['OS_ENDPOINT_TYPE'] if os.environ.has_key('OS_ENDPOINT_TYPE') else 'publicURL'
		keystonetests       = os.environ['OS_KEYSTONETESTS'] if os.environ.has_key('OS_KEYSTONETESTS') else keystonedefaulttests
		glancetests         = os.environ['OS_GLANCETESTS'] if os.environ.has_key('OS_GLANCETESTS') else glancedefaulttests
		imagepath           = os.environ['OS_GLANCE_IMAGE_PATH'] if os.environ.has_key('OS_GLANCE_IMAGE_PATH') else None
	except:
		print "Missing environment variables. source your openrc file first"
	    	os._exit(1)

	o = Openstuck(keystonecredentials=keystonecredentials, novacredentials=novacredentials, endpoint=endpoint, tenant=tenant, user=user, password=password, role=role, email=email, description=description, image=image, imagepath=imagepath, verbose=verbose)
	
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
	if testswift or testall:
		o.swifttest()
	if testha or testall:
		o.alltest()
	if testkeystone or testglance or testcinder or testneutron or testnova or testheat or testswift or testha or testall:
		print "Final report:"
		print o.report()
