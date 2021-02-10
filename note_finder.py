"""I lost a note. Check backup files for it."""
import re, glob, os, utils
from bear import BearNotes

class Finder:
	def __init__(self, func=None, **properties):
		self.func = func
		self.properties = properties
		self.match = None
		
		
	def process(self, notes):
		if self.func:
			for note in notes.values():
				if self.func(note):
					self.match = note
					break
		else:
			for note in notes.values():
				for prop, val in self.properties.items():
					try:
						if getattr(note, prop) != val:
							 continue
					except AttributeError:
						 continue
					self.match = note
					break
		return {note: False for note in notes}
		
		
def compare(a, b):
	oa, ob = [],[]
	fa = os.path.split(a.filenames[0])[1]
	fb = os.path.split(b.filenames[0])[1]
	for title in set(a.notes.keys()).union(b.notes.keys()):
		if title not in b.notes:
			print(f"{title} only in {fa}")
			oa.append(a.notes[title])
		elif title not in a.notes:
			print(f"{title} only in {fb}")
			ob.append(b.notes[title])
		else:
			la = len(utils.replace_section(a.notes[title].contents, "## Backlinks", ""))
			lb = len(utils.replace_section(b.notes[title].contents, "## Backlinks", ""))
			if la != lb:
				print(f"{title} {la} {'<' if la < lb else '>'} {lb}")
	return oa,ob
		

	
def go(pattern):
	def matchit(note):
		try:
			return re.search(pattern, note.title, flags=re.IGNORECASE)
		except TypeError:
			print(note)
			print(note.title)
			raise
	r = []
	path = '/private/var/mobile/Containers/Shared/AppGroup/D0B1EFA6-D02E-494B-B7E7-B4E1F0434866/Pythonista3/Documents/Temp'
	for bk in glob.glob(os.path.join(path, "*.bearbk")):
		print(os.path.split(bk)[1])
		bn = BearNotes()
		bn.register_processor(Finder(matchit))
		bn.read_backup_file(bk)
		bn.process_notes()
		if bn.processors[0].match:
			print(f"Match in {os.path.split(bk)[1]}")
			r.append(bn)
			
	return r
