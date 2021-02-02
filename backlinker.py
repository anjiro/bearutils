import re
from itertools import groupby
from operator import itemgetter
from utils import cidict, tag_re, replace_section

class Backlinker:	
	def __init__(self, **options):
		self.options = {
			'backlinks_heading': '## Backlinks',
			'context_lookaround': 250,
			'scrub_tags_from_context': True,
		}
		self.options.update(options)

		
	def process(self, notes):
		self.changed = {}
		self.backlinks = cidict()
		self.rendered_backlinks = {}
		old_backlinks = {}
		
		for note in notes.values():
			#Remove backlinks so we don't find links in it. Keep heading.
			text, oldbl = replace_section(note.contents,
				self.options['backlinks_heading'], self.options['backlinks_heading'])
				
			#Save the old backlinks, minus the header, to compare with to determine if something has changed
			old_backlinks[note] = re.sub(f'^{re.escape(self.options["backlinks_heading"])}[\t ]*\n', '', oldbl)
			
			for link, context in self.extract_links(text):
				#If we can't find the link, see if it's a subheading link
				dest = notes.get(link, notes.get(re.split(r'(?<!\\)/', link)[0]))
				
				if not dest:
					continue
				
				self.backlinks.setdefault(dest.title, {}).setdefault(note, []).append(context)
				
		#Now render the backlinks section for each note and determine whether
		# it's different than the old backlinks, if any.
		self.changed = {note: False for note in notes}
		for title in self.backlinks:
			note = notes[title]
			self.render_backlinks(note)
			self.changed[note] = self.rendered_backlinks[note].strip() != old_backlinks[note].strip()
		
		return self.changed

	
	def render_backlinks(self, note):
		"""Render the body of the backlinks section for the given note."""
		r = []
		#If the context and the title are the same, don't print the context
		tm = re.compile(
			'{}\s*[.?!]'.format(re.escape(f'[[{note.title}]]')), re.IGNORECASE)
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
			
		blh = self.options['backlinks_heading']
		
		if blh not in note.headers:
			#No existing header. 
			#If there are tags at the end of the note, put backlinks above
			#match "#x#" and "#x x#" and "#x" but not "# #", "# x#", and just the first part of "#x #"
			eoftags = re.search('\n[\t ]*(' + tag_re + '[\t ]*)+$', txt)
			ip = eoftags.start() if eoftags else len(txt)
			txt = '\n'.join((txt[:ip], '\n' + blh + '\n', txt[ip:]))
		
		return replace_section(txt, blh, f'{blh}\n{self.rendered_backlinks[note]}')[0]
	

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
