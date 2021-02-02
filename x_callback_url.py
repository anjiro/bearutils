"""From https://forum.omz-software.com/topic/3011/share-code-implemented-x-callback-url/19
Updated for Python 3.
Requires swizzle from https://github.com/jsbain/objc_hacks/blob/master/swizzle.py"""
import swizzle
from objc_util import *
import sys, re, os, argparse
import ctypes, json, urllib.request, urllib.parse, urllib.error, uuid, urllib.request, urllib.parse, urllib.error
import webbrowser

_setup_run = False

def argue():
	parser = argparse.ArgumentParser()
	
	parser.add_argument('-v', '--verbose',  action='store_true',  help='verbose mode')
	parser.add_argument('-t', '--test',    action='store_true',  help='run test')
	
	return parser.parse_args()
	
def params(data):
	return '' if not data else ('?' + '&'.join(
		[f'{k}={urllib.parse.quote(v)}' for k,v in data.items()]
	))
	
def reverse(url):
	query = NSURLComponents.componentsWithURL_resolvingAgainstBaseURL_(nsurl(url), False)
	parameters = dict()
	if query.queryItems() is not None:
		for queryItem in query.queryItems():
			parameters[str(queryItem.name())] = str(queryItem.value())
	return parameters
	
def open_url(url, handler):
	global _handler
	global _requestID
	global _setup_run
	if not _setup_run:
		setup()
	_requestID = uuid.uuid1()
	_handler = handler
	x_success = urllib.parse.quote('pythonista://?request=%s'%_requestID)
	url_with_uuid = url.replace('?','?x-success=%s&'%x_success)
	#sys.stderr.write('> %s\n'% url_with_uuid)
	webbrowser.open(url_with_uuid)
	
def openPythonistaURL_(_self, _sel, url):
	url_str = str(ObjCInstance(url))
	#sys.stderr.write('< %s\n'%url_str)
	global _call_me, _handler, _requestID
	
	if '?request=%s'%_requestID in url_str:
		url_str = url_str.replace('?request=%s&'%_requestID, '?')
		parameters = reverse(url_str)
		if _handler:
			_handler(parameters)
		return True
		
	elif _call_me in url_str:
		#print url_str
		parameters = reverse(url_str)
		x_parameters = dict()
		for x in [
		'x-source',
		'x-success',
		'x-error',
		'x-cancel',
		'x-script',
		]:
			if x in list(parameters.keys()):
				x_parameters[x] = parameters[x]
				del parameters[x]
				
		#print '%s\n%s'%(
		#    json.dumps(x_parameters),
		#    json.dumps(parameters)
		#)
		
		if 'x-script' not in list(x_parameters.keys()):
			return
			
		try:
			import importlib
			mod = importlib.import_module(
			x_parameters['x-script']
			)
			res = str(mod.main(parameters))
			url=x_parameters['x-success']+'?args=%s'%urllib.parse.quote(res)
		except:
			error=str(sys.exc_info()[0])
			url=x_parameters['x-error']+'?args=%s'%urllib.parse.quote(error)
			
		#print url
		webbrowser.open(url)
		return True
		
	else:
		#print('original url=%s'%url_str)
		obj = ObjCInstance(_self)
		original_method = getattr(obj, b'original'+c.sel_getName(_sel), None)
		if original_method:
			_annotation = ObjCInstance(annotation) if annotation else None
			return original_method(
			ObjCInstance(app),
			ObjCInstance(url), ObjCInstance(source_app),
			_annotation
			)
		return
		
def test():
	data={
	'statement' : 'select * from MyTable'
	}
	
	url='generaldb://x-callback-url/execute-select-statement' + params(data)
	print(url)
	
	def myhandler(parameters):
		print(parameters)
		for row in parameters['rows'].split('\n'):
			print(row)
		return
		
	open_url(url,myhandler)
	
def setup():
	global NSURLComponents, _call_me, _handler, _requestID
	_call_me = 'pythonista://x-callback-url'
	_handler = None
	_requestID = None
	NSURLComponents = ObjCClass('NSURLComponents')
	appDelegate = UIApplication.sharedApplication().delegate()
	
	# Do the swizzling
	cls = ObjCInstance(c.object_getClass(appDelegate.ptr))
	swizzle.swizzle(
	cls,
	'openPythonistaURL:', openPythonistaURL_
	)
	#print 'swizzled'
	global _setup_run
	_setup_run = True
	return
	
def main():
	setup()
	args = argue()
	if args.test : test(); return
	print('setup complete:')#, sys.argv
	#webbrowser.open('workflow://')
	return
	
if __name__ == '__main__': main()

