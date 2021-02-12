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


#Regexes used as part of another regex so stored as a string here.
tag_re = r'(?<!#)(?P<tag>#[^\s#][^#\n]*(?<!\s)#|#[^#\s]+)'
header_re = r'^{}(?:[\t ]*\n)'
title_re = r'(?:#*[\t ]+)?([^\n]+)[\t ]*(?:\n|$)'
link_re = r'\[\[(?P<link>[^\s\]][^\]]*)(?<!\s)]]'
eoftags_re = r'\n[\t ]*(' + tag_re + r'[\t ]*)+$'

def get_section(text, header, blank_lines_after_header=0):
	"""Return the first paragraph after the given header or None of not found."""
	header_finder = header_re.format(re.escape(header))
	match = re.search(header_finder + '{{1,{nbl}}}(?:([^ \n].+?)(?=\n\n|\Z))?'.format(nbl=blank_lines_after_header+1), text, flags=re.DOTALL|re.MULTILINE)
	if match:
		return match.group(1)


def replace_section(text, header, new_text='', blank_lines_after_header=0, before=None):
	"""Replace header and a paragraph of text following the header. Optionally allow some number of empty lines between the header and the paragraph; set to a negative number to replace only the header, ignoring any following lines. If the header was not found, add it above "before" or to the end of the note, but above any tags. Return tuple (the new note contents, the text that was replaced), or (self.contents, '') if the target section was not found. Note that this function does not modify the note contents, but returns a copy."""
	header_finder = header_re.format(re.escape(header))
	if blank_lines_after_header < 0:
		header_matcher = re.compile(header_finder, flags=re.MULTILINE)
		match = header_matcher.search(text)
		if match:
			return header_matcher.sub(new_text+'\n', text), header
	else:
		matcher = re.compile(header_finder + '{{1,{nbl}}}(?:[^ \n].+?(?=\n\n|\Z))?'.format(
			nbl=blank_lines_after_header+1), flags=re.DOTALL|re.MULTILINE)
		match = matcher.search(text)
		if match:
			return matcher.sub(new_text, text), match.group(0)
			
	#No existing header
	#If there are tags at the end of the note, put the section above.
	eoftags = re.search(eoftags_re, text)
	ip = eoftags.start() if eoftags else len(text)
	
	#But if we wanted to put it above a header, do that instead
	if before:
		before_match = re.search(f"^{before}\s*$", text, flags=re.MULTILINE)
		if before_match:
			ip = before_match.start()

	text = '\n'.join((text[:ip], '\n' + new_text + '\n', text[ip:]))
			
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
		
		
		
def is_bear_id(s):
	return re.match("-".join(f'[a-fA-F0-9]{{{n}}}' for n in (8,4,4,4,12,5,16))+'$', s.strip())
