"""
To do:
	- TOC (IDs may change when a backup is imported!)
	- Find & replace
	- automatic topic summaries by tag
	- generate GraphViz output
	- plugin structure to add actions: individual note actions, relationships between notes
	- Extract links
	- Optionally do actions just on noteIDs on clipboard
	- Bibliography/reference parser:
		- find refs that should be linked to a lit note
		- add Zotero links and cite keys
		- transform "[1"] into bibtex cite and export to .tex
"""
import json, os, re, sys, io, urllib, shortcuts
import dateutil.parser
import x_callback_url
import dialogs
from zipfile import ZipFile
from itertools import groupby
from operator import itemgetter, attrgetter
from time import time
from urllib.parse import quote

x_callback_url.setup()

options = {
	'backlinks_heading': '## Backlinks',
	'print_missing_links': False,
	'context_lookaround': 250,
	'scrub_tags_from_context': True,
	'toc_heading': '## Table of contents',
	'toc_placeholder': '## TOC',   # Shorthand to indicate a place for a new TOC
}

#info.json example
"""
	{'net.shinyfrog.bear': {'pinned': 0, 'trashedDate': None, 'archived': 0, 'modificationDate': '2021-01-21T17:03:59+0100', 'creationDate': '2021-01-13T22:22:59+0100', 'pinnedDate': None, 'trashed': 0, 'uniqueIdentifier': 'AB0089B3-24F7-425F-9898-8DA20EB49D9C-6965-0000035F819F960A', 'archivedDate': None, 'lastEditingDevice': "Dan's iPhone X"}, 'transient': True, 'type': 'public.plain-text', 'creatorIdentifier': 'net.shinyfrog.bear', 'version': 2}
"""

class BearFile():
	def __init__(self, zip_file, tb_path):
		"""Load a Bear textbundle."""
		#So we can only write notes that have changes
		self.backlinks = []
		self.old_backlinks = ''
		self.rendered_backlinks = ''

		self.old_toc = ''
		self.rendered_toc = ''
		self.rendered_note = ''
		
		self.info = json.loads(zip_file.open(os.path.join(tb_path, 'info.json')).read())['net.shinyfrog.bear']
		self.id = self.info['uniqueIdentifier']
		self.note = io.TextIOWrapper(zip_file.open(os.path.join(tb_path, 'text.txt')), encoding='utf-8').read()
		
		self.orig_note = self.note
		self.parse_title()
		self.drop_backlinks()

		self.note = self.note.strip()
		
		for k,v in self.info.items():
			if v and 'Date' in k:
				self.info[k] = dateutil.parser.parse(v)
		
		#We need to get notes with images via x-callback to preserve the images
		self.fetch_from_bear = '[assets/' in self.note
					 
		self.__dict__.update(self.info)
		
		self.extract_links()
		self.extract_headers()
		
		
	def __repr__(self):
		return '<{}: {}>'.format(__class__.__name__, self.title)
		
		
	def parse_title(self):
		#Bear uses the first line of a note as the title for linking
		# purposes, regardless of heading markup
		if self.note[0] == '\n':
			sys.stderr.write(f'Warning: no title for note ID {self.id}; contents:\n{self.orig_note}\n')
			self.title = None
		else:
			try:
				self.title, self.note = re.match(
				'(?:#*\s+)?([^\n]+)\n(.*)', self.note, re.DOTALL).groups()
			except:
				print(tb_path)
				print(self.info)
				print(self.orig_note)
				raise
				
				
	def drop_backlinks(self):
		#Drop any Backlinks section
		bl_matcher = re.compile('{}\s*\n(?:.+?\n\n|.+?$)'.format(re.escape(options['backlinks_heading'])), flags=re.DOTALL)
		obl = bl_matcher.search(self.note)
		self.old_backlinks = obl.group(0) if obl else ''
		self.note = bl_matcher.sub('', self.note)
		
	
	def get_note_contents_from_bear(self):
		"""Fetch the note contents from Bear using an x-callback. Slow but necessary for notes with images."""
		def got_note(info):
			self.note = info['note']
			self.parse_title()
			self.drop_backlinks()
			self.note = self.note.strip()
		call_bear('open-note', got_note, id=self.id)
		
		
	def extract_links(self):
		"""Find all [[Internal links]] and surrounding context."""
		#self.links = re.findall('\[\[(.+?)]]', self.note)
		
		self.links = []
		for match in re.finditer('\[\[(.+?)]]', self.note):
			link = match.group(1)
			s = max(0, match.start() - options['context_lookaround'])
			e = min(match.end() + options['context_lookaround'], len(match.string))
			search_in = match.string[s:e]
			try:
				context = re.search("""
					#Discard bullet points at line start, or text up to sentence end plus space.
					(?:
						^\s*[*-]\s+
						|
						^\s*\d+\.\s+
						|
						.*[.?!][ \t]+
					)?
					#Save text, the link, then text up to end of sentence
					(
						.*
						\[\[{}]]
						[^.?!\n]*
						[.?!\n]?
					)""".format(re.escape(link)), search_in, flags=re.MULTILINE|re.X).group(1).strip()
			except AttributeError:
				import clipboard
				clipboard.set(search_in)
				print(self.title, match, match.groups())
				print(match.string)
				print(match.string[s:e])
				raise
				
			if options['scrub_tags_from_context']:
				context = re.sub('(?<=\s)#(?:[^#]+\S#|[^#\s]+)\s?', '', context)
				
			self.links.append((link, context))
			
			
	def render_backlinks(self):
		"""Render backlinks into self.rendered_backlinks and return True. If no backlinks exist, return False."""
		if not self.backlinks:
			return False
			
		r = ['\n' + options['backlinks_heading']]
		
		#If the context and the title are the same, don't print the context
		tm = re.compile(
			'{}\s*[.?!]'.format(re.escape(f'[[{self.title}]]')), re.IGNORECASE)
		for bn, g in groupby(self.backlinks, key=itemgetter(0)):
			s = f'* [[{bn.title}]]'
			for context in list(g)[0][1:]:
				 if not tm.match(context):
				 		s += '\n\t* {}'.format(context)
			r.append(s)
		self.rendered_backlinks = '\n'.join(r)
		
		return True
		
		
	def extract_headers(self):
		"""Extract the headers from the note. Store (header level, header text, header plus hashes)."""
		self.headers = [(len(h), txt.strip(), m.strip()) for m, h, txt in re.findall('^((#+)\s+(.+)\s*)$', self.note, flags=re.M)]
		
		
	def render_toc(self):
		"""Render the table of contents into self.rendered_toc and return True. If no toc was requested in the note, or there are no headings, return False."""
		# Should we generate a TOC?
		toc_requested = re.search('^(?:{}|{})[\t ]*$'.format(
			re.escape(options['toc_placeholder']),
			re.escape(options['toc_heading'])), self.note, flags=re.MULTILINE)
		if not toc_requested:
			return False
			
		r = [options['toc_heading']]
		for level, header, full_header in self.headers:
			#Skip the TOC header
			if full_header == options['toc_heading'].strip() or full_header == options['toc_placeholder'].strip():
				continue
			r.append("\t"*(level-2) + f'* [{header}](bear://x-callback-url/open-note?id={self.id}&header={quote(header)})')

		if len(r) <= 1:
			return False
			
		self.rendered_toc = '\n'.join(r) + '\n'
		return True
		
			
	def render(self):
		"""Render backlinks, TOC, etc into self.rendered_note and return True. If nothing was changed, return False."""
		modified = False
		modified |= self.render_backlinks()
		modified |= self.render_toc()
		if not modified:
			return False
			
		r = [f'# {self.title}']
		#If there are tags at the end of the note, put backlinks above
		eoftags = re.search('\n\s*(?:#\w+|#[\w ]+\w#)+\s*$', self.note)
		if eoftags:
			r.append(self.note[:eoftags.start()])
			if self.rendered_backlinks:
				r.append(self.rendered_backlinks)
			r.append(self.note[eoftags.start()].strip())
		else:
			r.append(self.note)
			if self.rendered_backlinks:
				r.append(self.rendered_backlinks)
		
		self.rendered_note = '\n'.join(r)
		
		if self.rendered_toc:
			toc_matcher = re.compile('(?:{}|{})[\t ]*\n(?:[\t ]*\n|(?:[\t ]*\*[^\n]+\n)+)'.format(
				re.escape(options['toc_placeholder']),
				re.escape(options['toc_heading'])), flags=re.DOTALL)
			self.old_toc = toc_matcher.search(self.rendered_note).group(0)
			self.rendered_note = toc_matcher.sub(self.rendered_toc, self.rendered_note)
		
		return True
		
		
	def render_to_bear(self):
		"""Save the rendered note to Bear. If this note has an ID, replace the existing note with the same ID. Otherwise, make a new note."""
		
		#Find out if anything has actually changed
		if(
			self.rendered_backlinks.strip() == self.old_backlinks.strip()
			and
			self.rendered_toc.strip() == self.old_toc.strip()):
			return
			
		if self.fetch_from_bear:
			self.get_note_contents_from_bear()
			self.fetch_from_bear = False
			self.render()
		
		def success(info):
			pass
			#print(f"Successfully sent '{info['title']}' to Bear")
		
		if self.id:
			call_bear('add-text', success, id=self.id, text=self.rendered_note, mode='replace_all')
		else:
			call_bear('create', success, text=self.rendered_note)

			
			
def call_bear(action, callback=None, async=False, **params):
	"""Call Bear with the given actions, using the parameters in the URL. Quotes parameters. If async is False, block until the call to Bear returns."""
	
	sem = True
	r = None
	
	if not async:
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
	if not async:
		t = time()
		while not sem:
			if time() - t > 2:
				raise ValueError(f"Can't get return from {url}, sem is {sem}")
		callback(r)
		
		
def progress(p, nl=False):
	if p == 1:
		nl = True
	print("\rProgress: [{0:50s}] {1:.1f}%".format('#' * int(p * 50), p*100), end='\n' if nl else '', flush=True)
	
		
def read_bear_backup(backup_file):
	notes = {}
	with ZipFile(backup_file) as z:
		for fn in z.namelist():
			#zipfile lists only files, not directories, so use the .txt files to get directory names.
			if fn.endswith('.txt'):
				bf = BearFile(z, os.path.split(fn)[0])
				if bf.archived or bf.trashed:
					 continue
				notes[bf.title.lower()] = bf
	return notes
	
	
def find_backlinks(bear_files):
	"""Take dict from read_bear_backup and add backlinks array to each with BearFile objects that link to that note."""
	missing_links = []
	for bf in bear_files.values():
		for link, context in bf.links:
			l = link.lower()
			#If we can't find the link, see if it's a subheading link
			dest = bear_files.get(l, 
				bear_files.get(re.split(r'(?<!\\)/', l)[0]))
			if not dest:
				missing_links.append((bf, link))
				continue
			
			dest.backlinks.append((bf, context))
			dest.modified = True
	
	if options['print_missing_links']:
		for bf, link in missing_links:
			print('Note "{}" links to non-existent note "{}".'.format(bf.title, link))
	
				
def process_bear_backup(save=True, test_one=None):
	backup_file = dialogs.pick_document(types=['public.item'])
	if not backup_file:
		return
	if os.path.splitext(backup_file)[1] != '.bearbk':
		print(f"{os.path.split(backup_file)[-1]} isn't a .bearbk file")
		return
	bfs = read_bear_backup(backup_file)
	find_backlinks(bfs)
	print(f"Processed {len(list(bfs.keys()))} notes")
	modnotes = [note for note in sorted(bfs.values(), key=attrgetter('modificationDate')) if note.render()]
	print(f"{len(modnotes)} notes to send to Bear")
	
	if test_one:
		bfs[test_one.lower()].render_to_bear()
	elif save:
		for i, note in enumerate(modnotes):
			progress(i/len(modnotes))
			note.render_to_bear()
		progress(1)
		
	return bfs


if __name__ == '__main__':
	 process_bear_backup()
