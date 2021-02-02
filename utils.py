import re
import x_callback_url
from requests.structures import CaseInsensitiveDict as cidict
from collections import namedtuple
from time import time

# "## A section title" ->
# title: "A section title"
# level: 2
# header: "## A section title"
# match: a re.match object
Header = namedtuple('Header', 'title level header match')


#Regex to match tags; used as part of another regex so stored as a string here.
tag_re = '(?<!#)#[^\s#](?:[^#\n]*(?<!\s)#|[^#\s]+)'


def replace_section(text, header, new_text='', blank_lines_after_header=0):
	"""Replace header and a paragraph of text following the header. Optionally allow some number of empty lines between the header and the paragraph; set to a negative number to replace only the header, ignoring any following lines. Return tuple (the new note contents, the text that was replaced), or (self.contents, '') if the target section was not found. Note that this function does not modify the note contents, but returns a copy."""
	header_finder = '^{}(?:[\t ]*\n)'.format(re.escape(header))
	if blank_lines_after_header < 0:
		header_re = re.compile(header_finder, flags=re.MULTILINE)
		match = header_re.search(text)
		if match:
			return header_re.sub(new_text+'\n', text), header
	else:
		matcher = re.compile(header_finder + '{{1,{nbl}}}(?:[^ \n].+?(?=\n\n|\Z))?'.format(
			nbl=blank_lines_after_header+1), flags=re.DOTALL|re.MULTILINE)
		match = matcher.search(text)
		if match:
			return matcher.sub(new_text, text), match.group(0)
			
	return text, ''
		
		
def call_bear(action, callback=None, **params):
	"""Call Bear with the given actions, using the parameters in the URL. Quotes parameters. If callback is None, block until the call to Bear returns and return the result; otherwise return None immediately and call the callback when the result is ready."""
	
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
		t = time()
		while not sem:
			if time() - t > 2:
				raise ValueError(f"Can't get return from {url}, sem is {sem}")
		return r
