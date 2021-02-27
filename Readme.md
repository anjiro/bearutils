# Readme
#notes/misc

## Table of contents
* [Introduction](bear://x-callback-url/open-note?id=F0BE5397-85F0-4C70-A1BE-6E34CDD54061-15155-0000052245145DFB&header=Introduction)
* [How it works/what it does](bear://x-callback-url/open-note?id=F0BE5397-85F0-4C70-A1BE-6E34CDD54061-15155-0000052245145DFB&header=How%20it%20works/what%20it%20does)
* [Installing](bear://x-callback-url/open-note?id=F0BE5397-85F0-4C70-A1BE-6E34CDD54061-15155-0000052245145DFB&header=Installing)
* [Configuring & running](bear://x-callback-url/open-note?id=F0BE5397-85F0-4C70-A1BE-6E34CDD54061-15155-0000052245145DFB&header=Configuring%20%26%20running)
	* [Processing a few notes](bear://x-callback-url/open-note?id=F0BE5397-85F0-4C70-A1BE-6E34CDD54061-15155-0000052245145DFB&header=Processing%20a%20few%20notes)
	* [Processing all notes](bear://x-callback-url/open-note?id=F0BE5397-85F0-4C70-A1BE-6E34CDD54061-15155-0000052245145DFB&header=Processing%20all%20notes)
* [Processors](bear://x-callback-url/open-note?id=F0BE5397-85F0-4C70-A1BE-6E34CDD54061-15155-0000052245145DFB&header=Processors)
	* [Backlinker](bear://x-callback-url/open-note?id=F0BE5397-85F0-4C70-A1BE-6E34CDD54061-15155-0000052245145DFB&header=Backlinker)
	* [Table of contents generator](bear://x-callback-url/open-note?id=F0BE5397-85F0-4C70-A1BE-6E34CDD54061-15155-0000052245145DFB&header=Table%20of%20contents%20generator)
	* [Note actions](bear://x-callback-url/open-note?id=F0BE5397-85F0-4C70-A1BE-6E34CDD54061-15155-0000052245145DFB&header=Note%20actions)
	* [Add or remove text in titles](bear://x-callback-url/open-note?id=F0BE5397-85F0-4C70-A1BE-6E34CDD54061-15155-0000052245145DFB&header=Add%20or%20remove%20text%20in%20titles)
	* [Highlight searches](bear://x-callback-url/open-note?id=F0BE5397-85F0-4C70-A1BE-6E34CDD54061-15155-0000052245145DFB&header=Highlight%20searches)
	* [Collecting note links](bear://x-callback-url/open-note?id=F0BE5397-85F0-4C70-A1BE-6E34CDD54061-15155-0000052245145DFB&header=Collecting%20note%20links)
* [Configuring `bearutils`](bear://x-callback-url/open-note?id=F0BE5397-85F0-4C70-A1BE-6E34CDD54061-15155-0000052245145DFB&header=Configuring%20%60bearutils%60)
* [Extending Bearutils](bear://x-callback-url/open-note?id=F0BE5397-85F0-4C70-A1BE-6E34CDD54061-15155-0000052245145DFB&header=Extending%20Bearutils)
* [Disclaimer](bear://x-callback-url/open-note?id=F0BE5397-85F0-4C70-A1BE-6E34CDD54061-15155-0000052245145DFB&header=Disclaimer)

## Introduction
This is `bearutils`, a collection of [Pythonista](http://omz-software.com/pythonista/) scripts for working with Bear on iOS. It was  inspired by the desire to make backlinks possible in combination with slow process of getting notes from Bear via the `x-callback-url` mechanism (the method used by other iOS Bear backlink generators), and quickly evolved into a framework for doing a variety of tasks with Bear, including:

* Adding backlinks
* Adding tables of contents
* Highlighting search terms
* Collecting links to notes with a given tag into a single note
* Appending or prepending text to note titles based on a tag
* Moving tags from the end of a note to the beginning

## How it works/what it does
`bearutils` processes all or a subset of Bear notes. It loads the requested set of notes and runs a series of _processors_ on them which accomplish various tasks, such as those described above.

`bearutils` works via a method similar to Andy Matuschak's [note-link-janitor](https://github.com/andymatuschak/note-link-janitor), which reads Bear's SQL database to make backlinks. Because there's no access to the filesystem in iOS, `bearutils` instead operates on a backup file exported from Bear. This method is very fast, and has the extra advantage of ensuring you have a current backup should something go horribly wrong when running the program! `bearutils` extracts the notes from a Bear backup file and then performs actions.

For maximum safety, `bearutils` uses the Bear API to make any changes to notes. This could potentially change in a future release, but would the require manually importing a modified backup file.

Although `bearutils`  gains its speed by reading a backup rather than using Bear's API to read each note individually, there is one circumstance where it must fetch a note from Bear rather than using the backup. This is when the note has an attachment such as an image. In this case, the backed-up note doesn't contain the information needed to reference the attachment when saving the modified note to Bear, so `bearutils` must request the note via the API to get this information. It only does so, however, when a processor makes changes to a note.

Note that currently `bearutils` works only with the default Bear markdown style, not with actual Markdown.

## Installing
First, you need Pythonista ([app store link](https://apps.apple.com/app/pythonista-3/id1085978097)). Yes, it costs money. It's with it.

Next, you need `bearutils`. The easiest method is to download the [zip file](https://github.com/anjiro/bearutils/archive/main.zip), expand it with the Files app, then share the folder with Pythonista ("External Files -> Open").

## Configuring & running
`bearutils` can work with all of the notes saved in Bear, or with a manually selected subset. Either way, you need to run `bear.py`. Do so by selecting it, then hitting the play button in the editor (you may need to hold down on the play button to force running in Python 3).

Global  options for `bearutils` and the processors can be found in `options.ini`. Some processors can be configured via a special note titled "Beatitudes actions", which applies when working with all notes. When working with just one or a few notes, `bearutils` presents an options dialog.

### Processing a few notes
If you just want to add a table of contents to a note or two, it might be irritating to have to export a backup. Instead, you can copy the note IDs from the notes you want `bearutils` to process. When launched, `bearutils` will detect the IDs on the clipboard and prompt you to use them or a Bear backup.

The downside of processing notes in this way is that `bearutils` must get each note via the Bear API, so it's really only practical for one or two notes.

### Processing all notes
Before launching `bearutils`, export a backup from Bear (Settings -> Import & export -> Backup all notes) and save it with the Files app. When you launch `bearutils`, pick "Select a Bear backup file" if prompted, and select your just-saved backup. `bearutils` will then run the actions configured in `options.ini` and the "Bearutils actions" note (see below).

## Processors
`bearutils` features a number of built-in note processors. Some need to look at all of the notes (e.g., the backlink generator) and some can work on single notes (e.g., the table of contents generator).

### Backlinker
The main reason for the existence of `bearutils` is to generate backlinks, so this is one of the actions. The backlink processor adds a Backlinks section to any note linked to by another.

### Table of contents generator
This processor will search notes for a  `## Table of contents`  heading and will update it with a list of links to headings within the note. It will also look for a `## TOC` header as a shorthand placeholder.

### Note actions
Create a note with the title `Bearutils actions` (title configurable in `options.ini`).  Make a bulleted list. Each bullet represents an action to take when `bearutils` processes all notes.

Available actions include the following. Any time a tag is used, you can surround it with backticks to prevent the Bearutils note from being tagged with that tag.

### Add or remove text in titles
I like to use emoji to represent certain types of notes. You can do the following (actual examples):

* Append to titles in `#some tag/subtag#`: 👍
* Prepend to titles in `#stuff`: Hello
* Remove from titles in `#things`: 😂

Note that the last action, Remove, only removes from the beginning and end of titles.

### Highlight searches
Bear on iOS doesn't show search results within notes. `bearutils` will search your notes and highlight search term terms. You can do the following to search:

* ::search term:: in everywhere
* ::search term:: in `#tag`
* ::search term:: in [[Some note]]

You can later remove highlights by crossing them out;

* -::Found search term::- in everywhere
* -::Horses::- in [[Temp]]

### Collecting note links
It can be useful to collect links to all notes with a given tag, for example in using the [Zettelkasten method](zettelkasten.de).  The Collect action will find all notes with a given tag and add them to the specified note, but only if they aren't already linked in that note:

* Collect `#topics/metamaterials#` in [[§ Metamaterials]]

## Configuring `bearutils`
The file `options.ini` controls how `bearutils` works. It uses Python's [configparser](https://docs.python.org/3.6/library/configparser.html) module. The `[Processors]` section defines what to do when either a few notes are to be processed (i.e., from copied note IDs) or when all notes are processed from a backup. The other sections are options for each processor.

The options file is commented and should be reasonably self-explanatory.

## Extending Bearutils
`bearutils` is designed to be modular and easy to extend by writing new processors. Processors should subclass `processors.notes_processor` and are required to implement two methods: `process ()` and `render ()`.

The first method, `process ()`, determines which of the passed notes will be changed, while `render()` returns those changes. The reason for this structure is that the Bear backup file does not include the UUID for attachments to a note (e.g., images), so `bearutils` has to fetch the note directly from Bear using the API to be able to preserve attachments when it saves changes.

See `notes_processor.py` and the processors in `processors/` for more details.

## Disclaimer
`bearutils` is a personal project, written entirely on an iPad with my thumb while a baby slept in my lap, and will probably delete all of your notes, corrupt your hard drive, steal your dog, and eat the last cookie. Back up everything all the time. Feel free to send pull requests with tabs, not spaces, and proper comments.