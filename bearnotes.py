import os, json, io, re
import dateutil.parser
import dialogs
from datetime import datetime
from zipfile import ZipFile
from operator import attrgetter
from collections import defaultdict
from utils import *
from regexes import *
from bearcomms import *
import logging
log = logging.getLogger(__name__)


class Note:
	def __init__(self, info=None, contents=''):
		self.modified = False
		self.info = info
		self._contents = None
		self.orig_contents = contents
		self.contents = contents.strip()
		
		if self.info:
			try:
				self.id = self.info['uniqueIdentifier'] #In Bear backups
			except KeyError:
				self.id = self.info['identifier'] #From a call to open-note
		
			for k,v in self.info.items():
				if v and 'Date' in k:
					self.info[k] = dateutil.parser.parse(v)
		else:
			self.modificationDate = datetime.now()
					
			self.__dict__.update(self.info)
		
		#We need to get notes with images via x-callback to preserve the images
		self.fetch_from_bear = '[assets/' in self.contents
		
		
	def __repr__(self):
		return '<{}: {}>'.format(__class__.__name__, self.title)
		
		
	@property
	def contents(self):
		return self._contents
		
		
	@contents.setter
	def contents(self, contents):
		"""Re-run extractors if something has changed."""
		if contents != self.contents:
			self._contents = contents
			self.parse_title()
			self.extract_headers()
			self.extract_tags()
			self.extract_links()
		
		
	def parse_title(self):
		#Bear uses the first line of a note as the title for linking
		# purposes, regardless of heading markup
		if not self.contents:
			self.title = None
		elif re.match('[\t ]*\n', self.contents):
			sys.stderr.write(f'Warning: no title for note ID {self.id}; contents:\n{self.orig_contents}\n')
			self.title = None
		else:
			self.title = re.match(title_re, self.contents, re.DOTALL).group(1)
				
				
	def extract_headers(self):
		"""Extract the headers from the note. Return a dict: {'## Header': utils.Header()}."""
		self.headers = {}
		for match in re.finditer('^((#+)\s+(.+)[\t ]*)$', self.contents, flags=re.M):
			header, hashes, title = match.groups()
			self.headers[header] = Header(title, len(hashes), header, match)
			
			
	def extract_tags(self):
		"""Extract all tags from the note, but not those inside backticks."""
		self.tags = [tag.strip('#') for tag in re.findall(tag_re, self.contents)]
		
		
	def extract_links(self):
		"""Extract all links from the note, but not those inside backticks."""
		self.links = re.findall(link_re, self.contents) or []
		

	def get_note_contents_from_bear(self):
		"""Fetch the note contents from Bear using an x-callback. Slow but necessary for notes with images."""
		if self.fetch_from_bear:
			info = call_bear('open-note', id=self.id)
			self.contents = info['note']
			self.fetch_from_bear = False
			
			
	def save_to_bear(self):
		"""Save the note to Bear. If this note has an ID, replace the existing note with the same ID. Otherwise, make a new note."""
		if self.id:
			call_bear('add-text', id=self.id, text=self.contents, mode='replace_all')
		else:
			call_bear('create', text=self.contents)



class BearNotes:
	"""Read and operate on collections of notes."""
	def __init__(self, skip_archived=True, skip_trashed=True):
		self.skip_archived = skip_archived
		self.skip_trashed = skip_trashed
		
		self.notes = {}
		self.processors = []
		
		
	def __repr__(self):
		return f"<{__class__.__name__}: {len(self.notes or [])} notes>"
		
		
	def register_processor(self, processor_instance):
	 	self.processors.append(processor_instance)


	def read_backup_file(self, backup_file):
		if os.path.splitext(backup_file)[1] != '.bearbk':
			print(f"{os.path.split(backup_file)[-1]} isn't a .bearbk file")
			return
			
		self.filenames = [backup_file]
			
		notes = cidict()
		with ZipFile(backup_file) as zip_file:
			for fn in zip_file.namelist():
				#zipfile lists only files, not directories, so use the .txt files to get directory names.
				if fn.endswith('.txt'):
					tb_path = os.path.split(fn)[0]
					txtfn  = os.path.join(tb_path, 'text.txt')
					infofn = os.path.join(tb_path, 'info.json')
					
					info = json.loads(zip_file.open(infofn).read())['net.shinyfrog.bear']
				
					if info['archived'] and self.skip_archived or info['trashed'] and self.skip_trashed:
						 continue
					
					contents = io.TextIOWrapper(zip_file.open(txtfn), encoding='utf-8').read()
					
					note = Note(info, contents)
					
					notes[note.title] = note
		self.notes.update(notes)
		
		
	def read_textbundles(self, filenames):
		self.filenames = filenames
		notes = {}
		for tb_path in filenames:
			txtfn  = os.path.join(tb_path, 'text.markdown')
			infofn = os.path.join(tb_path, 'info.json')
			
			info = json.loads(open(infofn).read())['net.shinyfrog.bear']
		
			if info.get('archived', False) and self.skip_archived or info.get('trashed', False) and self.skip_trashed:
				 continue
			
			contents = open(txtfn, encoding='utf-8').read()
			
			note = Note(info, contents)
			notes[note.title] = note
			
		self.notes.update(notes)
		
		
	def fetch_from_bear(self, bear_ids):
		notes = {}
		for nid in bear_ids:
		 	info = call_bear('open-note', id=nid.strip())
		 	if info.get('is_trashed', 'no') == 'yes' and self.skip_trashed:
		 		continue
		 	contents = info.pop('note')
		 	del info['tags']
		 	note = Note(info, contents)
		 	notes[note.title] = note
		self.notes.update(notes)
		 	
		
	def process_notes(self):
		"""Process all the notes."""
		changed_by = defaultdict(list)
		for p in self.processors:
			log.info(f'Run processor {p.__class__.__name__}')
			changed = p.process(self.notes)
			if changed is not None:
				for note, did_change in changed.items():
					if did_change:
						changed_by[note].append(p.__class__.__name__)
						note.get_note_contents_from_bear()
						note.contents = p.render(note)
						note.modified = True
						if note.title not in self.notes:
							self.notes[note.title] = note
		for note, ps in changed_by.items():
			log.info(f"{note.title} changed by: {', '.join(ps)}")
						
					
	def save_to_bear(self):
		"""Save modified notes to Bear."""
		try:
			save_order = sorted(self.notes.values(), key=attrgetter('modificationDate'))
		except AttributeError:
			#Textbundle exports don't have timestamps
			save_order = self.notes.values()
		for note in save_order:
			if note.modified:
				note.save_to_bear()
