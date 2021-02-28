import configparser, logging, re, sys
import clipboard, console, dialogs
from bearnotes import BearNotes
from bearcomms import is_bear_id
from utils import load_classes_from_options

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
log = logging.getLogger(__name__)

# Actions
ACTION_IDS = 1
ACTION_BATCH = 2

def ids_or_batch():
	return console.alert('BearUtils', 
		'I found possible Bear Note IDs on the clipboard. What do you want to do?', 
		'Use IDs from clipboard', # action = ACTION_IDS
		'Select a Bear backup file', # action = ACTION_BATCH
	)

		
def process_bear_files(save=True, test_one=None):
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
	
	#If there are Bear note IDs on the clipboard, prompt whether to use them or load a backup file
	cb = clipboard.get().split('\n')
	if all(is_bear_id(l) for l in cb):
		action = ids_or_batch()
		if action < 0:
			return
	
	processors = []
	
	#Processa a Bear backup file
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
			
	#Work with one or more notes based on IDs		
	elif action == ACTION_IDS:
		classopts = {}
		forms = []
		#Load but don't instantiate classes. Get options from the user, then instantiate with those options.
		classes = load_classes_from_options(options, options['Processors'].getlist(action_processors[action]), instantiate=False)
		#Generate a dialog to offer options based on the annotated init function for each class defined in the config file	
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
