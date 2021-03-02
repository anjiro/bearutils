import re
from .notes_processor import NotesProcessor
from itertools import groupby
from operator import itemgetter
from utils import cidict, tag_re, replace_section
import logging
log = logging.getLogger(__name__)

class Backlinker(NotesProcessor):
	def __init__(self, **options):
		self.options = {
			'backlinks_heading': '## Backlinks',
			'context_lookaround': 250,
			'scrub_tags_from_context': True,
			'ignore_links_in_notes': [],
		}
		self.options.update(options)

		
	def process(self, notes):
		self.changed = {}
		self.backlinks = cidict()
		self.rendered_backlinks = {}
		old_backlinks = {}
		
		#For each note, find the other notes it links to
		for note in notes.values():
			#Remove backlinks so we don't find links in it. Keep heading.
			text, oldbl = replace_section(note.contents,
				self.options['backlinks_heading'], self.options['backlinks_heading'])
				
			#Save the old backlinks, minus the header, to compare with to determine if something has changed
			if oldbl:
				old_backlinks[note] = re.sub(rf'^{re.escape(self.options["backlinks_heading"])}[\t ]*\n', '', oldbl)
				
			if note.title in self.options['ignore_links_in_notes']:
				continue
			
			for link, context in self.extract_links(text):
				#If we can't find a Note with the link title, see if it's a subheading link
				dest = notes.get(link, notes.get(re.split(r'(?<!\\)/', link)[0]))
				
				#Can't find a matching Note
				if not dest:
					continue
				
				self.backlinks.setdefault(dest.title, {}).setdefault(note, []).append(context)
				
		#Now render the backlinks section for each note and determine whether it's different than the old backlinks, if any.
		self.changed = {note: False for note in notes}
		for title in self.backlinks:
			note = notes[title]
			self.render_backlinks(note)
			self.changed[note] = self.rendered_backlinks[note].strip() != old_backlinks.get(note, '').strip()
			
		#Find any notes that have a backlinks section but no longer have any links pointing to them
		for note in old_backlinks:
			if note.title not in self.backlinks:
				self.rendered_backlinks[note] = ''
				self.changed[note] = True
		
		return self.changed

	
	def render_backlinks(self, note):
		"""Render the body of the backlinks section for the given note."""
		r = []
		#If the context and the title are the same, don't print the context
		tm = re.compile(
			'{}\s*[.?!]?'.format(re.escape(f'[[{note.title}]]')), re.IGNORECASE)
		for bn, g in self.backlinks[note.title].items():
			s = f'* [[{bn.title}]]'
			for context in g:
				 if not tm.match(context):
				 		s += '\n\t* {}'.format(context)
			r.append(s)
		self.rendered_backlinks[note] = '\n'.join(r)
	
	
	def render(self, note):
		txt = note.contents
		if note not in self.rendered_backlinks:
			return txt
		
		if len(self.rendered_backlinks[note]) > 0:
			backlink_section = self.options['backlinks_heading'] + "\n" + self.rendered_backlinks[note]
		else:
			backlink_section = ''
			
		return replace_section(txt, self.options['backlinks_heading'], backlink_section)[0]
	

	def extract_links(self, text):
		"""Find all [[Internal links]] and surrounding context in the passed text."""
		links = []
		for match in re.finditer('\[\[(.+?)]]', text):
			link = match.group(1)
			s = max(0, match.start() - self.options['context_lookaround'])
			e = min(match.end() + self.options['context_lookaround'], len(match.string))
			search_in = match.string[s:e]
			try:
				#This fails slightly when there are two identical backlinks within +/- context_lookaround, only detecting the first.
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
				
			if self.options['scrub_tags_from_context']:
				context = re.sub('(?<=\s)#(?:[^#]+\S#|[^#\s]+)\s?', '', context)
				
			links.append((link, context))
			
		return links
