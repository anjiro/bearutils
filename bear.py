import os, json, io, re
import dateutil.parser
import dialogs
from zipfile import ZipFile
from operator import attrgetter
from utils import cidict, tag_re, Header, call_bear


class BearNotes:
	"""Read and operate on collections of notes."""
	def __init__(self, skip_archived=True, skip_trashed=True):
		self.skip_archived = skip_archived
		self.skip_trashed = skip_trashed
		
		self.notes = None
		self.processors = []
		
		
	def __repr__(self):
		return f"<{__class__.__name__}: {len(self.notes or [])} notes>"
		
		
	def register_processor(self, processor_instance):
	 	self.processors.append(processor_instance)


	def read_backup_file(self, backup_file):
		if os.path.splitext(backup_file)[1] != '.bearbk':
			print(f"{os.path.split(backup_file)[-1]} isn't a .bearbk file")
			return
			
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
		self.notes = notes
		
		
	def process_notes(self):
		"""Process all the notes. First run group processors then single."""
		for p in self.processors:
			changed = p.process(self.notes)
			for note, did_change in changed.items():
				if did_change:
					note.get_note_contents_from_bear()
					note.contents = p.render(note)
					note.modified = True
					
					
	def save_to_bear(self):
		"""Save modified notes to Bear."""
		for note in sorted(self.notes.values(), key=attrgetter('modificationDate')):
			if note.modified:
				note.save_to_bear()
				


class Note:
	def __init__(self, info, contents):
		self.info = info
		self.id = self.info['uniqueIdentifier']
		self.orig_contents = contents
		self._contents = contents.strip()
		self.modified = False
		
		for k,v in self.info.items():
			if v and 'Date' in k:
				self.info[k] = dateutil.parser.parse(v)
		
		#We need to get notes with images via x-callback to preserve the images
		self.fetch_from_bear = '[assets/' in self.contents
					 
		self.__dict__.update(self.info)
		
		self.parse_title()
		self.extract_headers()
		self.extract_tags()
		
		
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
			self.extract_headers()
			self.extract_tags()
		
		
	def parse_title(self):
		#Bear uses the first line of a note as the title for linking
		# purposes, regardless of heading markup
		if re.match('[\t ]*\n', self.contents):
			sys.stderr.write(f'Warning: no title for note ID {self.id}; contents:\n{self.orig_contents}\n')
			self.title = None
		else:
			self.title  = re.match('(?:#*[\t ]+)?([^\n]+)\n', self.contents, re.DOTALL).group(1)
				
				
	def extract_headers(self):
		"""Extract the headers from the note. Return a dict: {'## Header': utils.Header()}."""
		self.headers = {}
		for match in re.finditer('^((#+)\s+(.+)[\t ]*)$', self.contents, flags=re.M):
			header, hashes, title = match.groups()
			self.headers[header] = Header(title, len(hashes), header, match)
			
			
	def extract_tags(self):
		"""Extract all tags from the note."""
		self.tags = re.findall(tag_re, self.contents, flags=re.MULTILINE)
		

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
		
		
		
def process_bear_backup(save=True, test_one=None):
	from backlinker import Backlinker
	from toc import TOC
	
	backup_file = dialogs.pick_document(types=['public.item'])
	if not backup_file:
		return
	if os.path.splitext(backup_file)[1] != '.bearbk':
		print(f"{os.path.split(backup_file)[-1]} isn't a .bearbk file")
		return
		
	bn = BearNotes()
	bn.register_processor(Backlinker())
	bn.register_processor(TOC())
	bn.read_backup_file(backup_file)
	bn.process_notes()
	if save:
		if test_one:
			bn[test_one].save_to_bear()
		else:
			bn.save_to_bear()
	
	return bn
	
	
if __name__ == "__main__":
	process_bear_backup()
