# Zotero2Remarkable Bridge


**Disclaimer! The sync from ReMarkable to Zotero is WIP and does not always work
as intended. The code is somewhat messy and makes some assumptions that should 
probably not be made. Help is appreciated!**

This program can be used to sync attachments from Zotero to your ReMarkable
*and* sync them back to Zotero again.
It relies on on both Zotero's and ReMarkable's cloud APIs for Python. This means
sync must be enabled in Zotero to use this program. Both Zotero's storage as well 
as external WebDAV storage is supported, although Zotero's own cloud support is 
largely untested. Testing and bug reports/pull requests are highly appreciated.

## Usage 

### How it works

The program makes use of Zotero's tag system to determine which files should be processed.
To designate attachments that should be synced, add the tag "to_sync" to the entry.

After the files are synced, this tag is automatically removed and set to "synced".
Do not remove these tags as they are used to determine which files should be synced back.

On the ReMarkable, the program uses folders to keep track of files. Unfortunately, there
is no tag system on ReMarkable, so that is the best way I could come up with.

The program uses [rmrl](https://github.com/rschroll/rmrl) to render files from ReMarkable, but adds support for post v2.7 highlights as
propper PDF annotations. Colors are also supported. Yet, because of the way these highlights
are generated, some highlights may be missing in the export. The program will generate warnings for those.

### Setup

1. Add required packages through pip:
`pip3 install -r requirements.txt`

2. Allow execution of the program:
`sudo chmod +x zotero_remarkable_bridge.py`

3. Run the program. At first run, it will guide you through creating a working
config. It will help you setup authentication with Zotero, WebDAV (optional), and
ReMarkable.

### Arguments

The program accepts the following arguments:

```
./zotero2remarkable_bridge.py [-m push|pull|both]

-m: Mode
push: Only push to ReMarkable

pull: Only pull from ReMarkable and sync to Zotero

both: Go both ways, adding new files to ReMarkable and syncing back
        to ReMarkable.
        
Defaults to "both".
```
