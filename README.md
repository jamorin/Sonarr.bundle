# Sonarr.bundle

A plugin for [Plex Media Server](https://plex.tv/) to control [Sonarr](https://sonarr.tv/) (formally NzbDrone).

## Supports:
- View your TV shows, calendar (current week), queue, missing episodes, and history
- Add new series to your collection
- Search, delete, and update existing shows, seasons, or episodes.

## Install
1. `cd <PMS Installation>/Library/Application\ Support/Plex\ Media\ Server/Plug-ins`
2. `git clone https://github.com/jamorin/Sonarr.bundle`
3. Restart Plex Media Server
4. Change the plugin's settings by adding your hostname, port, and API Key

### Caveats:
- English only (There is locale support. Submit a pull request with translations)
- No SSL support. I run Sonarr on a Synology NAS. SSL port doesn't seem to work.
- No Basic Authentication. This plugin uses your API Key ONLY.

Pull requests welcome.
