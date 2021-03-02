"""Utilities for communicating with Bear."""
import re, time
import bearnotes, x_callback_url
import logging
log = logging.getLogger(__name__)


def fetch_note(**params):
	"""Fetch the given note and return a Note object."""
	if 'id' in params and not is_bear_id(params['id']):
		raise ValueError("Not a valid Bear note ID")
	info = call_bear('open-note', **params)
	contents = info.pop('note')
	note = bearnotes.Note(info, contents)
	note.fetch_from_bear = False
	return note
	
		
def call_bear(action, callback=None, timeout=4, **params):
	"""Call Bear with the given actions, using the parameters in the URL. Quotes parameters. If callback is None, block until the call to Bear returns and return the result; otherwise return None immediately and call the callback when the result is ready. Increase timeout for slower systems (graphical animations in iOS slow response time)."""
	
	sem = True
	r = None
	
	if callback is None:
		sem = False
		def cb(i):
			nonlocal sem, r
			sem = True
			r = i
	else:
		cb = callback
		
	url = f'bear://x-callback-url/{action}' + x_callback_url.params(params)
	x_callback_url.open_url(url, cb)
	
	#Wait up to n seconds for Bear to return, then call the callback
	if callback is None:
		t = time.time()
		while not sem:
			if time.time() - t > timeout:
				raise ValueError(f"Can't get return from {url}, sem is {sem}")
		return r
		
		
def is_bear_id(s):
	valid_seg_lengths = [
		(8,4,4,4,12,3,16),
		(8,4,4,4,12,5,16),
	]
	return any(re.match("-".join(f'[a-fA-F0-9]{{{n}}}' for n in sl)+'$', s.strip()) for sl in valid_seg_lengths)
