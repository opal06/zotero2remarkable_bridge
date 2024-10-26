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

The program now uses [remarks](https://github.com/lucasrla/remarks.git) to render files from ReMarkable and therefore has support both for scribbles as well as smart highlights. Colors are supported. Unlike its previous implementation, it also should not create multiple highlights when a highlighted string appears multiple times on a page. It does not however have support for the new format introduces with firmware v3. Hopefully, as development on `remarks`progresses, this will change.

The program will preserve the original file and add the marked file as new attachment with "(Annot) " added in front of the file name.
Entries that have been synced back will have the tag "read" added to them, so you can easily search for them.

### Support for new reMarkable cloud API
~~Due to changes made by reMarkable to its cloud API that have not yet been implemented in [rmapy](https://github.com/subutux/rmapy/), on which this program relies, some users may have issues getting this program to work. This will mostly affect users that have signed up for the cloud after the API change.~~
Dependency on rmapy has been removed and the program now relies on [rmapi](https://github.com/ddvk/rmapi) by default, as it has been proven functional and allows to support the new reMarkable cloud API without sacrificing backwards compatibility to the older API. Therefore, a working install of `rmapi` is now required. 

> [!IMPORTANT]
> The [original version](https://github.com/juruen/rmapi) of `rmapi` by juruen has been discontinued, but a working [fork](https://github.com/ddvk/rmapi) maintained by ddvk now exists and should be used instead.

### Setup

#### On reMarkable:
- Create a folder named `Zotero` through the UI on your reMarkable. This folder must be on the top level of the file system and cannot be nested under other folders.
- Create two folders inside the `Zotero` folder, one for your unread documents (this is where new files from Zotero will land) and your read documents (this is where the program looks for files to be synced back to Zotero). 

#### On your PC:
```bash
# 1. Clone repository to your computer:
git clone https://github.com/opal06/zotero2remarkable_bridge.git

# Note: The program requires rmapi to be installed and properly configured. Please refer to rmapi's [Readme](https://github.com/juruen/rmapi/blob/master/README.md) for instructions.

# 2. Add required packages through pip:
pip3 install -r requirements.txt

# 3. (Only on Linux) Allow execution of the program:
sudo chmod +x zotero2remarkable_bridge.py

# 4. On Linux, run the program with:
./zotero2remarkable_bridge.py

# Or on any other OS with:
python3 zotero2remarkable_bridge.py

# At first run, it will guide you through creating a working
# config. It will help you setup authentication with Zotero, WebDAV (optional), and
# ReMarkable.
```

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
