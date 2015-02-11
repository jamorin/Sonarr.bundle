from datetime import datetime

PREFIX  = '/video/sonarr'
NAME   = 'Sonarr'

ICON = '256.png'
ART  =  'logo.png'

MONITORED = 'fa-bookmark-monitored.png'
NOTMONITORED = 'fa-bookmark.png'

def Start():
    global NAME
    NAME = L('TITLE')
    ObjectContainer.art        =  R(ART)
    ObjectContainer.title1      = NAME
    PopupDirectoryObject.thumb  = R(ICON)
    Dict['utcOffset'] = Datetime.Now().replace(minute=0, second=0,
        microsecond=0) - datetime.utcnow().replace(minute=0, second=0,
        microsecond=0, tzinfo=None)
    Log.Debug('UTC offset: %s' % Dict['utcOffset'])
    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    Plugin.AddViewGroup("List", viewMode="List", mediaType="items")
    global historyEvents
    historyEvents = {
        "downloadFolderImported": { 'summary': L('IMPORTED'),
                                    'thumb': R('fa-download.png')},
        "downloadFailed": { 'summary': L('FAILED'),
                            'thumb': R('fa-cloud-download-failed.png')},
        "grabbed": {'summary': L('GRABBED'),
                    'thumb': R('fa-cloud-download.png')},
        "episodeFileDeleted": { 'summary': L('DELETED'),
                                'thumb': R(ICON) }
    }
    Log.Debug('URL:%s' % Dict['url'])
    Log.Debug('Base:%s' % Prefs['base'])
    HTTP.ClearCache()

@handler(PREFIX, NAME, ICON, ART)
def MainMenu():
    oc = ObjectContainer(view_group="InfoList")
    oc.add(DirectoryObject(key=Callback(Stub), title=L('CALENDAR_TITLE'),
        summary = 'NOT IMPL', thumb=R('fa-calendar.png')))
    oc.add(DirectoryObject(key=Callback(Stub), title='DISKSPACE',
        summary = 'NOT IMPL'))
    oc.add(DirectoryObject(key=Callback(History), title=L('HISTORY_TITLE'),
        summary = L('HISTORY_SUMMARY'), thumb=R('fa-history.png')))
    oc.add(DirectoryObject(key=Callback(Stub), title=L('MISSING_TITLE'),
        summary = 'NOT IMPL', thumb=R('fa-exclamation-triangle.png')))
    oc.add(DirectoryObject(key=Callback(Stub), title=L('QUEUE_TITLE'),
        summary = 'NOT IMPL'))
    oc.add(DirectoryObject(key=Callback(Series), title=L('SERIES_TITLE'),
        summary = 'NOT IMPL',  thumb=R('fa-play.png')))
    oc.add(PrefsObject(title=L('SETTINGS_TITLE'), summary=L('SETTINGS_SUMMARY'),
        thumb=R('fa-cogs.png')))
    return oc

def ValidatePrefs():
    if Prefs['ssl']:
        protocol = 'https'
    else:
        protocol = 'http'
    Dict['url']  = '%s://%s:%s' % (protocol, Prefs['ip'], Prefs['port'])
    Log.Debug('Saving url: %s' % Dict['url'])
    Log.Debug('Base: %s' % Prefs['base'])
    return MessageContainer(L("SUCCESS"), L("PREFS_SAVED"))

@route('%s/stub' % PREFIX)
def Stub():
    return MessageContainer('Stub', 'Allan please add details')

def ApiRequest(endpoint, params={}):
    Log.Debug('url:%s' % Dict['url'])
    Log.Debug('base:%s' % Prefs['base'])
    url = "{}/api/{}".format(Dict['url']+Prefs['base'], endpoint)
    Log.Debug("Full url:%s" % url)
    if len(params):
        url += '?'
        for key, value in params.items():
            url += "%s=%s&" % (key, value)
        url = url.rstrip('&')
    json = JSON.ObjectFromURL(url, headers={'X-Api-Key': Prefs['apiKey']})
    return json

@route('%s/series' % PREFIX)
def Series():
    oc = ObjectContainer(title2="Series")
    json = ApiRequest('series')
    for series in sorted(json, key=lambda x: x['titleSlug']):
        title = series['title']
        summary = series['network']
        seriesId = series['id']
        thumb=R(ICON)
        for coverType in series['images']:
            if coverType['coverType'] == "poster":
                Log.Debug(coverType['url'])
                thumb=Callback(GetThumb, url=Dict['url']+coverType['url'])
                break
        oc.add(PopupDirectoryObject(key=Callback(SeriesOptions,
            seriesId=seriesId, title2=title), title=title, summary=summary,
            thumb=thumb))
    if not len(oc):
        return MessageContainer(L('SERIES_TITLE'), L('SERIES_NONE'))
    return oc

@route('%s/history' % PREFIX, page=int, pageSize=int)
def History(page=1, pageSize=19):
    oc = ObjectContainer(title2=L('HISTORY_TITLE'))
    json = ApiRequest('history', params=dict(page=page, pageSize=pageSize,
        sortKey='date', sortDir='desc'))
    for record in json['records']:
        seasonNbr = record['episode']['seasonNumber']
        episodeNbr = record['episode']['episodeNumber']
        seriesTitle = record['series']['title']
        episodeTitle = record['episode']['title']
        episodeQuality = record['quality']['quality']['name']
        sourceTitle = record['sourceTitle']
        date = Datetime.ParseDate(record['date'])
        event = record['eventType']
        if event in historyEvents:
            summary = historyEvents[event]['summary']
            thumb = historyEvents[event]['thumb']
        else:
            summary = record['eventType']
            thumb=R(ICON)
        title="%s - %dX%02d %s" % (seriesTitle, seasonNbr, episodeNbr,
            prettydate(date))
        summary = "%s: %s %s" % (summary, episodeTitle, episodeQuality)
        oc.add(DirectoryObject(key=Callback(Stub), title=title, summary=summary,
            thumb=thumb))
    if not len(oc):
        return MessageContainer(L('HISTORY_TITLE'), L('HISTORY_NONE'))
    if page*pageSize < json['totalRecords']:
        oc.add(NextPageObject(key=Callback(History, page=page+1)))
    return oc

@route('%s/seriespopup' % PREFIX, seriesId=int)
def SeriesOptions(seriesId, title2):
    oc = ObjectContainer(title2=title2)
    oc.add(DirectoryObject(key=Callback(Stub),
        title='Search for all episodes in this series', summary='wewef', thumb=R(ICON)))
    oc.add(DirectoryObject(key=Callback(Stub),
        title='Delete series', summary='wefwee', thumb=R(ICON)))
    oc.add(DirectoryObject(key=Callback(Stub),
        title='List seasons', summary='wefwee', thumb=R(ICON)))
    return oc

@route('%s/thumb' % PREFIX)
def GetThumb(url, contentType='image/jpeg', timeout=10, cacheTime=10):
    Log.Debug(url)
    data = HTTP.Request(url=url, timeout=timeout, cacheTime=cacheTime)
    return DataObject(data.content, contentType)

def prettydate(d):
    """ http://stackoverflow.com/a/5164027 """
    diff = Datetime.Now() - (d.replace(tzinfo=None)+Dict['utcOffset'])
    s = diff.seconds
    if diff.days > 7 or diff.days < 0:
        return d.strftime('%d %b %y')
    elif diff.days == 1:
        return '1 day ago'
    elif diff.days > 1:
        return '{} days ago'.format(diff.days)
    elif s < 3600:
        return '{} minutes ago'.format(s/60)
    elif s < 7200:
        return '1 hour ago'
    else:
        return '{} hours ago'.format(s/3600)

"""
@route(PREFIX+"/seasonlist",seriesId=int, seasons=list)
def SeasonList(seriesId, seasons, title2='Seasons'):
    oc = ObjectContainer(title2=title2)
    for s in seasons:
        title='Season '+str(s['seasonNumber'])
        if s['seasonNumber']  == 0: title='Specials'
        thumb=R(NOTMONITORED)
        summary='Not monitored'
        if s['monitored']:
            thumb=R(MONITORED)
            summary='Monitored'
        season=dict(key=Callback(EpisodeList, seriesId=seriesId, season=s['seasonNumber'], title2=title2), title=title, thumb=thumb, summary=summary)
        oc.add(DirectoryObject(**season))
    if len(oc) == 0:
        return ObjectContainer(header=NAME, message='No seasons found.')
    return oc

@route(PREFIX+"/episodelist",seriesId=int, season=int)
def EpisodeList(seriesId,season,title2='Episodes'):
    oc = ObjectContainer(title2=title2)
    episodes = API_Request(endUrl='/episode', params=dict(seriesId=seriesId))
    if episodes == None:
        Invalid()
    for e in episodes:
        if e['seasonNumber'] == season:
            number = str(e['episodeNumber'])
            if len(number) == 1: number = '0'+number
            title=number+' - '+e['title']
            oc.add(DirectoryObject(key=Callback(Stub), title=title,summary=e['overview']))
    if len(oc) == 0:
        return ObjectContainer(header=NAME, message='No episodes found.')
    return oc

@route(PREFIX+"/calendar")
def Calendar(past=dict(days=0),delta=dict(weeks=1)):
    start = TimeStampUTCString(datetime.utcnow()-Datetime.Delta(**past))
    end = TimeStampUTCString(datetime.utcnow()+Datetime.Delta(**delta))
    oc = ObjectContainer(title2="Calendar")
    events = API_Request(endUrl='/calendar', params=dict(start=start,end=end))
    if events == None:
        return Invalid()
    for e in events:
        season = str(e['seasonNumber'])
        episode = str(e['episodeNumber'])
        dt = Datetime.ParseDate(e['airDateUtc'])+Dict['UTCOffset']
        if len(episode) ==  1: episode = '0'+episode
        title=PrettyDate(offset=dt)+' - '+e['series']['title']+' - '+season+'x'+episode
        e_title=e['title']
        e_overview=e['overview']
        summary=''
        if not e_title and not e_overview: summary = 'No information provided'
        elif not e_title: summary=e_overview
        elif not e_overview: summary=e_title
        else: summary=e_title+' - '+e_overview
        for coverType in e['series']['images']:
            if coverType['coverType'] == 'poster':
                image = coverType['url']
        show=dict(key=Callback(Stub), title=title, summary=summary, thumb=Callback(GetThumb, image=image))
        oc.add(DirectoryObject(**show))
    if len(oc) == 0:
        return ObjectContainer(header=NAME, message="No shows airing this week.")
    return oc

# NOT USED - Can't figure out what the REST API url is for 'missing'
@route(PREFIX+"/wanted", page=int, pageSize=int)
def Wanted(page=1,pageSize=19):
    oc = ObjectContainer(title2='Wanted')
    wanted = API_Request(endUrl='/missing', params=dict(page=page,pageSize=pageSize,sortKey='date',sortDir='desc'))
    if wanted == None:
        return Invalid()
    for r in wanted['records']:
        title=r['title']
        summary=PrettyHistory(datetime.utcnow(),Datetime.ParseDate(r['airDateUtc']).replace(tzinfo=None))
        record=dict(key=Callback(Stub), title=title, summary=summary)
        oc.add(DirectoryObject(**record))
    if len(oc) == 0:
        return ObjectContainer(header=NAME, message="No wanted items.")
    if page*pageSize < int(history['totalRecords']):
        oc.add(NextPageObject(key=Callback(Wanted, page=page+1)))
    return oc

# Convert a datetime to ISO-8601 formatted in UTC to send to NzbDrone
def TimeStampUTCString(time=datetime.utcnow()):
    return str(time.isoformat('T')).split('.')[0]+'Z'

# Nice relative dates
def PrettyDate(offset, date=Datetime.Now()):
    diff = offset.replace(tzinfo=None) - date
    if diff.days == 0:
        return 'Today'
    if diff.days == 1:
        return 'Tomorrow at ' + offset.strftime('%I:%M %p').lstrip('0')
    if diff.days > 1 and diff.days < 7:
        return offset.strftime('%A')+ ' at '+offset.strftime('%I:%M %p').lstrip('0')
    if diff.days == -1:
        return 'Yesterday'
    if diff.days < -1 and diff.days > -7:
        return offset.strftime('Last %A')
    else:
        return offset.strftime('%B %d')
"""
