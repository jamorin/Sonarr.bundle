# DumbKeyboard

This serves as a replacement for the InputDirectoryObject in the Plex Plug-in framework for clients that don't support it. It uses DirectoryObjects to build a query string, then lets you send that to the Search function. Search queries are saved in the channels Dict so they don't need to be re-entered.

![img](http://i.imgur.com/y4smv7P.png)
![http://i.imgur.com/Q622vhM.png](http://i.imgur.com/Q622vhM.png)

### Usage:

add `DumbTools.py` to `Channel.bundle/Contents/Code`.

in `__init__.py` add:
```
from DumbTools import DumbKeyboard
```

in `__init__.py` where you have an InputDirectoryObject:
```python
if Client.Product in DumbKeyboard.clients:
        DumbKeyboard(PREFIX, oc, Search,
                dktitle = u'%s' L('search'),
                dkthumb = R(ICONS['search'])
        )
else:
        oc.add(InputDirectoryObject(
                key    = Callback(Search),
                title  = u'%s' L('search'),
                prompt = 'Search',
                thumb  = R(ICONS['search'])
        ))
        
@route(PREFIX + '/search')
def Search(query):
        ...
```        
### Definitions:

`DumbKeyboard(prefix, oc, callback, dktitle=None, dkthumb=None, dkplaceholder=None, dksecure=False, **kwargs)`

Appends a DirectoryObject to `oc` which will provide a series of DirectoryObjects to build a string. `callback` is called with the arguments `query` and `**kwargs` when the Submit directory is selected.

  * *prefix*: whatever is used in the @handler(PREFIX, NAME).
  * *oc*: the object container to add to.
  * *callback*: the Search function. This must have atleast 1 argument 'query'.
  * *dktitle*: (optional) the title to use for the search directoryObject.
  * *dkthumb*: (optional) the thumbnail to use for the search directoryObject.
  * *dkplaceholder*: (optional) set a default value in the text entry.
  * *dksecure*: (optional) set the entry to be secure or not (show *'s instead of the characters).
  * ***kwargs*: additional arguments to send to the callback function.
    * if you have search function `Search(query, a=None, b=None)` then you can use `DumbKeyboard(prefix, oc, Search, a='something' b=123)`
 
`DumbKeyboard.clients` - Client.Product's that don't have InputDirectoryObjects or don't always work correctly.
  * Plex for iOS
  * Plex Media Player
  * Plex Web

# DumbPrefs

a replacement for the PrefsObject. This should allow both displaying and changing channel preferences using only DirectoryObjects.

![http://i.imgur.com/fI65O87.png](http://i.imgur.com/fI65O87.png)

It may require the following addition to `Info.plist`:
```xml
    <key>PlexPluginCodePolicy</key>
    <string>Elevated</string>
```

### Usage:

```python
from DumbTools import DumbPrefs

@handler(PREFIX, NAME)
def MainMenu():
        oc = ObjectContainer()
        
        if Client.Product in DumbPrefs.clients:
                DumbPrefs(PREFIX, oc,
                        title = L('preferences'),
                        thumb = R(ICONS['preferences']))
        else:
                oc.add(PrefsObject(
                        title = L('preferences'),
                        thumb = R(ICONS['preferences'])
                ))
```

### Definitions: 

`DumbPrefs(prefix, oc, title=None, thumb=None)`

Appends a DirectoryObject to `oc` which will allow users to change text, bool, and enum channel preferences.

  * *prefix*: whatever is used in the @handler(PREFIX, NAME).
  * *oc*: the object container to add to.
  * *title*: (optional) the title to use for the directoryObject.
  * *thumb*: (optional) the thumbnail to use for the directoryObject.

`DumbPrefs.clients` - Client.Product's that don't have Prefs or don't always work correctly.
  * 'Plex for iOS' - doesn't have it
  * 'Plex Media Player' - doesn't have it
  * 'Plex Home Theater' - has it, but it never liked saving text prefs
  * 'OpenPHT'
  * 'Plex for Roku' - I don't think it has it, I'm not sure if this is the correct product name.
