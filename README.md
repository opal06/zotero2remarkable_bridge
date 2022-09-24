# Zotero2reMarkable Bridge

This program can be used to sync attachments from Zotero to your ReMarkable
*and* sync them back to Zotero again.
It relies on on both Zotero's and reMarkable's cloud APIs for Python. This means
sync must be enabled in Zotero to use this program. Both Zotero's storage and external WebDAV storage is supported, 
although Zotero's own cloud support is largely untested. Testing and bug reports/pull requests are highly appreciated.

## Usage 

### How it works

The program makes use of Zotero's tag system to determine which files should be processed.
To designate attachments that should be synced, add the tag "to_sync" to the entry.

After the files are synced, this tag is automatically removed and set to "synced".
Do not remove these tags as they are used to determine which files should be synced back.

On the reMarkable, the program uses folders to keep track of files. ~~Unfortunately, there
is no tag system on reMarkable, so that is the best way I could come up with.~~ Although there now is a tag system, this is – as far as I am aware of – not yet supported by third party API implementations. So for now, the folder approach remains the easiest. This might change in the future. You can specify the folder names
during setup.

The program uses [rmrl](https://github.com/rschroll/rmrl) to render files from ReMarkable, but adds support for v2.7 highlights as
propper PDF annotations. Colours are also supported. Yet, because of the way these highlights
are generated, some highlights may be missing in the export. The program will generate warnings for those.

The program will preserve the original file and add the marked file as new attachment with "(Annot) " added in front of the file name.
Entries that have been synced back will have the tag "read" added to them, so you can easily search for them.

### Experimental support for new reMarkable cloud API!
Due to changes made by reMarkable to its cloud API that have not yet been implemented in [rmapy](https://github.com/subutux/rmapy/), on which this program relies, some users may have issues getting this program to work. This will mostly affect users that have signed up for the cloud after the API change.
Fortunately, [rmapi](https://github.com/juruen/rmapi) has added experimental support for this new API version. I have now created a version of this application that leverages rmapi for communication with the reMarkable cloud and therefore has support for the new API. This implementation is for now largely untested, bug reports are welcome!

### Setup

1. Clone repository to your computer:
`git clone https://github.com/opal06/zotero2remarkable_bridge.git`

* **Only required for version with new cloud API support!**
  Select correct branch:
  `git checkout rmapi_workaround`

Note: The workaround requires rmapi to be installed and properly configured. Please refer to rmapi's [Readme](https://github.com/juruen/rmapi/blob/master/README.md) for instructions.

2. Add required packages through pip:
`pip3 install -r requirements.txt`

3. Allow execution of the program:
`sudo chmod +x zotero2remarkable_bridge.py`

4. Run the program with:
`./zotero2remarkable_bridge.py`
At first run, it will guide you through creating a working
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
