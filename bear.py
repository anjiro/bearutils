import os, json, io, re
import dateutil.parser
import dialogs
from datetime import datetime
from zipfile import ZipFile
from operator import attrgetter
from collections import defaultdict
from utils import *


class NotesProcessor:
	def process(self, notes):
		"""Process `notes`, which is a dict of {title: Note} representing all of the Notes loaded by BearNotes. Do not make any changes to the Note contents, because they might be overwritten if the contents need to be fetched from Bear. Instead, save the changes, and return a dict of {Note: changed (True/False)}, or None if no changes will be made."""
		raise NotImplementedError("Subclasses must implement process()")
		
		
	def render(self, note):
		"""This will be called once for each Note that process() indicates has changed. Return the new contents of the note."""
		raise NotImplementedError("Subclasses must implement render()")
		
		
	def __repr__(self):
		 return f"<{self.__class__.__name__}>"
		
		

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
		 	print(f"got {nid}")
		 	if info.get('is_trashed', 'no') == 'yes' and self.skip_trashed:
		 		print(info)
		 		continue
		 	contents = info.pop('note')
		 	del info['tags']
		 	note = Note(info, contents)
		 	notes[note.title] = note
		print(f"fetched {notes}")
		self.notes.update(notes)
		 	
		
	def process_notes(self):
		"""Process all the notes."""
		for p in self.processors:
			changed = p.process(self.notes)
			if changed is not None:
				for note, did_change in changed.items():
					if did_change:
						note.get_note_contents_from_bear()
						note.contents = p.render(note)
						note.modified = True
						if note.title not in self.notes:
							self.notes[note.title] = note
						
					
	def save_to_bear(self):
		"""Save modified notes to Bear."""
		try:
			save_order = sorted(self.notes.values(), key=attrgetter('modificationDate'))
		except AttributeError:
			#Textbundle exports don't have timestamps
			save_order = self.notes.values()
		for note in save_order:
			print(note)
			if note.modified:
				print('saved')
				note.save_to_bear()
			else:
				print(f"{note} not modified")
				


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
		
		
def fetch_note(**params):
	"""Fetch the given note and return a Note object."""
	if 'id' in params and not is_bear_id(params['id']):
		raise ValueError("Not a valid Bear note ID")
	info = call_bear('open-note', **params)
	contents = info.pop('note')
	note = Note(info, contents)
	note.fetch_from_bear = False
	return note
		
		
def process_bear_files(save=True, test_one=None):
	import clipboard, console, configparser
	from importlib import import_module
	import sys
	
	# Actions
	ACTION_IDS = 1
	ACTION_BATCH = 2
	
	#Determine where in options to get note processors to load based on the response to the dialog
	action_processors = {
		ACTION_IDS: 'some_processors',
		ACTION_BATCH: 'all_processors',
	}
	
	#Default action
	action = ACTION_BATCH
	
	options = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation(),
		converters={'list': lambda l: re.split('[\t ]*,[\t ]*', l)})
	options.read('options.ini')
	
	def ids_or_batch():
		return console.alert('BearUtils', 
			'I found possible Bear Note IDs on the clipboard. What do you want to do?', 
			'Use IDs from clipboard', # action = ACTION_IDS
			'Select a Bear backup file', # action = ACTION_BATCH
		)
	
	cb = clipboard.get().split('\n')
	if all(is_bear_id(l) for l in cb):
		action = ids_or_batch()
		if action < 0:
			return
	
	processors = []
	
	if action == ACTION_BATCH:
		processors = load_classes_from_options(options, options['Processors'].getlist(action_processors[action]))
		if 'NoteActions' in options:
			#Set up any actions requested in the Bearutils actions note
			actions_note = fetch_note(title=options['NoteActions']['actions_note'])
			#Load the classes specified in the config file for the Action note
			for _class, opts in load_classes_from_options(options, options['NoteActions'].getlist('classes'), instantiate=False):
				for matcher in _class.action_matchers:
					for match in matcher.finditer(actions_note.contents):
						opts_copy = dict(opts)
						opts_copy.update(match.groupdict())
						processors.append(_class(**opts_copy))
			
	#Generate a dialog to offer options based on the annotated init function for each class defined in the config file			
	elif action == ACTION_IDS:
		classopts = {}
		forms = []
		#Load but don't instantiate classes. Get options from the user, then instantiate with those options.
		classes = load_classes_from_options(options, options['Processors'].getlist(action_processors[action]), instantiate=False)
		for _class, opts in classes:
			classname = _class.__name__
			classopts[classname] = opts
			items = [dict(title='Enable', type='switch', key=classname+'!enable', value=opts.get('default_to_enabled', True))]
			for arg_name, ann in _class.__init__.__annotations__.items():
				ann['key'] = classname+'!'+arg_name
				items.append(ann)
			forms.append((classname, items))
		try:
			user_opts = dialogs.form_dialog(sections=forms)
		except KeyboardInterrupt:
			return
		if not user_opts:
			return
		
		for k,v in user_opts.items():
			classname, arg = k.split("!")
			classopts[classname][arg] = v
			
		for _class, _ in classes:
			classname = _class.__name__
			if classopts[classname]['enable']:
				processors.append(_class(**classopts[classname]))
	
	bn = BearNotes()
	
	#Load the specified processors with their defined options
	for processor in processors:
		bn.register_processor(processor)
		
	if action == ACTION_IDS:
		bn.fetch_from_bear(cb)
	elif action == ACTION_BATCH:
		backup_file = dialogs.pick_document(types=['public.item'])
		if not backup_file:
			return
		if os.path.splitext(backup_file)[1] != '.bearbk':
			print(f"{os.path.split(backup_file)[-1]} isn't a .bearbk file")
			return
		bn.read_backup_file(backup_file)
	
	bn.process_notes()
	
	if save:
		if test_one:
			bn[test_one].save_to_bear()
		else:
			bn.save_to_bear()
	else:
		print('Warning: save is False')
	
	return bn
	
	
if __name__ == "__main__":	
	process_bear_files()
