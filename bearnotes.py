import os, json, io, re, sys
import dateutil.parser
from datetime import datetime, timezone
from operator import attrgetter
from collections import defaultdict
from utils import *
from regexes import *
import logging
log = logging.getLogger(__name__)


class Note:
	def __init__(self, info=None, contents='', filename=None):
		self.filename = filename
		self.modified = False
		self.info = info
		self._contents = None
		self.orig_contents = contents
		self.contents = contents.strip()

		if self.info:
			self.__dict__.update(self.info)
		else:
			self.modificationDate = datetime.now(timezone.utc)		


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
			self.title = None
		else:
			self.title = re.match(title_re, self.contents, re.DOTALL).group(1)
		if self.title is None:
			sys.stderr.write(f'Warning: no title for note {self.filename}; contents:\n{self.orig_contents}\n')


	def extract_headers(self):
		"""Extract the headers from the note. Return a dict: {'## Header': utils.Header()}."""
		self.headers = {}
		for match in re.finditer('^((#+)\s+(.+)[\t ]*)$', self.contents, flags=re.M):
			header, hashes, title = match.groups()
			self.headers[header] = Header(title, len(hashes), header, match)


	def extract_tags(self):
		"""Extract all tags from the note, but not those inside backticks."""
		self.tags = [tag.strip(':') for tag in re.findall(tag_re, self.contents)]


	def extract_links(self):
		"""Extract all links from the note, but not those inside backticks."""
		self.links = re.findall(link_re, self.contents) or []


	def save(self):
		if not self.filename:
			raise ValueError("Need a filename in .filename")
		stat = os.stat(self.filename)
		with open(self.filename, 'w', encoding='utf-8') as f:
			f.write(self.contents)
		os.utime(self.filename, (stat.st_atime, stat.st_mtime))


class WikiNotes:
	"""Read and operate on collections of notes."""
	def __init__(self):
		self.notes = {}
		self.processors = []


	def __repr__(self):
		return f"<{__class__.__name__}: {len(self.notes or [])} notes>"


	def register_processor(self, processor_instance):
	 	self.processors.append(processor_instance)


	def read_md_files(self, wikidir=None, filelist=None):
		"""Either wikidir or filelist must be provided. If filelist,
		provide pathnames."""
		if wikidir:
			wikidir = os.path.expanduser(wikidir)
			self.filenames = [os.path.join(wikidir, f) for f in
				os.listdir(wikidir) if (f.endswith('.md') or f.endswith('.wiki'))
				and not f.startswith('.')]
		else:
			self.filenames = filelist
		notes = cidict()
		for fn in self.filenames:
			info = {'modificationDate': datetime.fromtimestamp(os.path.getmtime(fn))}
			with open(fn) as f:
				contents = f.read()
			note = Note(info, contents, filename=fn)
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
						note.contents = p.render(note)
						note.modified = True
						if note.title not in self.notes:
							self.notes[note.title] = note
		log.info(f'{len(changed_by)} notes modified')
		for note, ps in changed_by.items():
			log.info(f"{note.title} changed by: {', '.join(ps)}")


	def save(self):
		for note in self.notes.values():
			if note.modified:
				note.save()
