import requests
import re
# import platform
# if platform.system() == 'Darwin':
#     from mock_framework import *
from DumbTools import DumbKeyboard
from updater import Updater

PREFIX = '/video/sonarr'
NAME = 'Sonarr'

ENDPOINT = 'http://127.0.0.1:8989'
HEADERS = {'X-Api-Key': None,
           'Accept': 'application/json',
           'Content-Type': 'application/json'
           }
BASIC = None


# noinspection PyPep8Naming
def Start():
    ObjectContainer.art = R('logo.png')
    ObjectContainer.title1 = NAME
    ObjectContainer.title2 = NAME
    DirectoryObject.thumb = R('question-circle.png')
    ValidatePrefs()


# noinspection PyPep8Naming
def ValidatePrefs():
    global ENDPOINT, BASIC
    ENDPOINT = Prefs['url'].rstrip('/') + '/api'
    BASIC = None
    Log.Info('Endpoint: %s' % ENDPOINT)
    HEADERS['X-Api-Key'] = Prefs['api_key']
    if Prefs['username'] and Prefs['password']:
        Log.Info('Using basic auth')
        BASIC = (Prefs['username'], Prefs['password'])


@handler(PREFIX, NAME, thumb='1024.png', art='logo.png')
def main_menu():
    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(series),
                           title=L('series'),
                           summary=L('series_desc'),
                           thumb=R('play.png')))
    oc.add(DirectoryObject(key=Callback(calendar),
                           title=L('calendar'),
                           summary=L('calendar_desc'),
                           thumb=R('calendar.png')))
    oc.add(DirectoryObject(key=Callback(queue),
                           title=L('queue'),
                           summary=L('queue_desc'),
                           thumb=R('cloud.png')))
    oc.add(DirectoryObject(key=Callback(history),
                           title=L('history'),
                           summary=L('history_desc'),
                           thumb=R('history.png')))
    oc.add(DirectoryObject(key=Callback(missing),
                           title=L('missing'),
                           summary=L('missing_desc'),
                           thumb=R('exclamation-triangle.png')))
    oc.add(DirectoryObject(key=Callback(cutoff),
                           title=L('unmet'),
                           summary=L('unmet_desc'),
                           thumb=R('exclamation-triangle.png')))
    oc.add(PrefsObject(title=L('settings'), thumb=R('cogs.png')))
    Updater(PREFIX + '/updater', oc)
    return oc


@route(PREFIX + '/calendar')
def calendar():
    try:
        start = timestamp(Datetime.UTCNow() - Datetime.Delta(hours=4))
        end = timestamp(Datetime.UTCNow() + Datetime.Delta(weeks=1))
        response = get('/calendar', params={'unmonitored': False, 'start': start, 'end': end})
        oc = ObjectContainer(title2=L('calendar'))
        delta = utc_delta()
        for curr_episode in response:
            season_nbr = curr_episode['seasonNumber']
            episode_nbr = curr_episode['episodeNumber']
            episode_id = curr_episode['id']
            air_date_utc = curr_episode['airDateUtc']
            episode_title = curr_episode['title']
            overview = getdefault(curr_episode, 'overview')
            title = u'%s - %dX%02d - %s' % (episode_title,
                                            season_nbr,
                                            episode_nbr,
                                            pretty_datetime(air_date_utc, delta))
            do = DirectoryObject(key=Callback(episode, episode_id=episode_id),
                                 title=title,
                                 summary=overview)
            cover_type(curr_episode['series'], do)
            oc.add(do)
        return oc
    except Exception as e:
        return error_message(e)


@route(PREFIX + '/episodes', series_id=int, season_id=int)
def episodes(series_id, season_id):
    try:
        response = get('/episode', params={'seriesId': series_id})
        oc = ObjectContainer(title2='%s %d' % (L('season'), season_id))
        curr_season = filter(lambda x: x['seasonNumber'] == season_id, response)
        delta = utc_delta()
        for curr_episode in reversed(curr_season):
            thumb = monitor_badge(curr_episode['monitored'])
            episode_nbr = curr_episode['episodeNumber']
            title = u'%02d' % episode_nbr
            if curr_episode['hasFile']:
                title += u'\u2713'
            title += u' %s' % curr_episode['title']
            if 'airDateUtc' in curr_episode:
                title += u' - %s' % pretty_datetime(curr_episode['airDateUtc'], delta)
            summary = getdefault(curr_episode, 'overview')
            episode_id = curr_episode['id']
            oc.add(DirectoryObject(key=Callback(episode, episode_id=episode_id),
                                   title=title,
                                   summary=summary,
                                   thumb=thumb))
        return oc
    except Exception as e:
        return error_message(e)


@route(PREFIX + '/episode/monitor', episode_id=int)
def episode_monitor(episode_id):
    oc = ObjectContainer()
    oc.add(DirectoryObject(key=Callback(episode_monitor_put, episode_id=episode_id),
                           title=L('toggle'),
                           thumb=R('refresh.png')))
    return oc


@route(PREFIX + '/episode/monitor/put', episode_id=int)
def episode_monitor_put(episode_id):
    try:
        response = get('/episode/%d' % episode_id)
        response['monitored'] = not response['monitored']
        put('/episode', json=response)
        return success_message()
    except Exception as e:
        return error_message(e)


@route(PREFIX + '/episode/delete/put', entity_id=int)
def episode_delete_put(entity_id):
    try:
        delete('/series/%d' % entity_id, json={'deleteFiles': Prefs['delete_files']})
        return success_message()
    except Exception as e:
        return error_message(e)


@route(PREFIX + '/episode/delete', entity_id=int)
def episode_delete(entity_id, title2):
    oc = ObjectContainer(title2=title2)
    oc.add(DirectoryObject(key=Callback(episode_delete_put, entity_id=entity_id),
                           title=L('confirm'),
                           thumb=R('exclamation-triangle.png')))
    return oc


@route(PREFIX + '/episode/history', episode_id=int)
def episode_history(episode_id, page=1, page_size=10):
    return history_get(episode_history, page, page_size, episode_id=episode_id)


@route(PREFIX + '/release', episode_id=int)
def release(episode_id):
    try:
        Log.Info(episode_id)
        response = get('/release', params={'episodeId': episode_id, 'sort_by': 'releaseWeight', 'order': 'asc'})
        oc = ObjectContainer(title2=L('release'))
        for curr_release in response:
            age = curr_release['age']
            indexer = curr_release['indexer']
            quality = curr_release['quality']['quality']['name']
            title = u'%s: %s %s %s %s' % (L('age'), age, curr_release['title'], indexer, quality)
            oc.add(DirectoryObject(key=Callback(release_put, new_release=curr_release),
                                   title=title,
                                   thumb=R('download.png')))
        return oc
    except Exception as e:
        return error_message(e)


@route(PREFIX + '/release/put', new_release=dict)
def release_put(new_release):
    try:
        post('/release', json=new_release)
        return success_message()
    except Exception as e:
        return error_message(e)


@route(PREFIX + '/episode', episode_id=int)
def episode(episode_id):
    try:
        res = get('/episode/%d' % episode_id)
        title = res['title']
        monitored = res['monitored']
        thumb = monitor_badge(monitored)
        oc = ObjectContainer(title2=title)
        oc.add(DirectoryObject(key=Callback(episode_monitor, episode_id=episode_id),
                               title=L('toggle'),
                               thumb=thumb))
        oc.add(DirectoryObject(key=Callback(automatic_search, name='EpisodeSearch', param_1=episode_id),
                               title=L('automatic_search'),
                               thumb=R('search.png')))
        oc.add(DirectoryObject(key=Callback(release, episode_id=episode_id),
                               title=L('manual_search'),
                               thumb=R('user.png')))
        oc.add(DirectoryObject(key=Callback(episode_history, episode_id=episode_id),
                               title=L('history'),
                               thumb=R('history.png')))
        if res['episodeFileId'] > 0:
            oc.add(DirectoryObject(key=Callback(episode_delete, entity_id=res['episodeFileId'], title2=title),
                                   title=L('delete'),
                                   thumb=R('trash-o.png')))
        return oc
    except Exception as e:
        return error_message(e)


@route(PREFIX + '/history', page=int, page_size=int)
def history(page=1, page_size=19):
    return history_get(history, page, page_size)


@route(PREFIX + '/series/monitor', series_id=int)
def series_monitor(series_id):
    oc = ObjectContainer()
    oc.add(DirectoryObject(
        key=Callback(series_monitor_put, series_id=series_id),
        title=L('toggle'),
        thumb=R('refresh.png')))
    return oc


@route(PREFIX + '/series/monitor/put', series_id=int)
def series_monitor_put(series_id):
    try:
        response = get('/series/%d' % series_id)
        response['monitored'] = not response['monitored']
        put('/series', json=response)
        return success_message()
    except Exception as e:
        return error_message(e)


@route(PREFIX + '/season/monitor', series_id=int, season_nbr=int)
def season_monitor(series_id, season_nbr):
    oc = ObjectContainer()
    oc.add(DirectoryObject(
        key=Callback(season_monitor_put, series_id=series_id, season_nbr=season_nbr),
        title=L('toggle'),
        thumb=R('refresh.png')))
    return oc


@route(PREFIX + '/season/monitor/put', series_id=int, season_nbr=int)
def season_monitor_put(series_id, season_nbr):
    try:
        response = get('/series/%d' % series_id)
        for curr_season in response['seasons']:
            if curr_season['seasonNumber'] == season_nbr:
                curr_season['monitored'] = not curr_season['monitored']
                break
        put('/series', json=response)
        return success_message()
    except Exception as e:
        return error_message(e)


@route(PREFIX + '/queue')
def queue():
    try:
        r = get('/queue', params={'sort_by': 'timeleft', 'order': 'asc'})
        oc = ObjectContainer(title2=L('queue'))
        for curr_episode in r:
            status = curr_episode['status']
            title = curr_episode['title']
            series_title = curr_episode['series']['title']
            summary = '{}: {}  {}: {}'.format(L('status'), status, L('title'), title)
            season_nbr = curr_episode['episode']['seasonNumber']
            episode_nbr = curr_episode['episode']['episodeNumber']
            episode_id = curr_episode['episode']['id']
            header = '%s - %dX%02d' % (series_title, season_nbr, episode_nbr)
            do = DirectoryObject(key=Callback(episode, episode_id=episode_id),
                                 title=header,
                                 summary=summary)
            cover_type(curr_episode['series'], do)
            oc.add(do)
        return oc
    except Exception as e:
        return error_message(e)


@route(PREFIX + '/automatic_search', param_1=int, param_2=int)
def automatic_search(name, param_1, param_2=0):
    try:
        json = dict(name=name)
        if name == 'EpisodeSearch':
            json['episodeIds'] = [param_1]
        elif name == 'SeriesSearch':
            json['seriesId'] = param_1
        else:
            json['seriesId'] = param_1
            json['seasonNumber'] = param_2
        post('/command', json=json)
        return success_message()
    except Exception as e:
        return error_message(e)


@route(PREFIX + '/seasons', series_id=int)
def seasons(series_id):
    try:
        r = get('/series/%d' % series_id)
        oc = ObjectContainer(title2=r['title'])
        for curr_season in reversed(r['seasons']):
            thumb = monitor_badge(curr_season['monitored'])
            season_nbr = curr_season['seasonNumber']
            season_str = u'%s: %d' % (L('season'), season_nbr)
            oc.add(DirectoryObject(key=Callback(season,
                                                series_id=series_id,
                                                season_id=season_nbr),
                                   title=season_str,
                                   summary=season_str,
                                   thumb=thumb))
        return oc
    except Exception as e:
        return error_message(e)


@route(PREFIX + '/season', series_id=int, season_id=int)
def season(series_id, season_id):
    oc = ObjectContainer(title2=u'%s %d' % (L('season'), season_id))
    response = get('/series/%d' % series_id)
    curr_season = filter(lambda x: x['seasonNumber'] == season_id, response['seasons'])[0]
    # noinspection PyTypeChecker
    thumb = monitor_badge(curr_season['monitored'])
    oc.add(DirectoryObject(key=Callback(episodes, series_id=series_id, season_id=season_id),
                           title=L('list'),
                           thumb=R('th-list.png')))
    oc.add(DirectoryObject(key=Callback(season_monitor,
                                        series_id=series_id,
                                        season_nbr=season_id),
                           title=L('toggle'),
                           thumb=thumb))
    oc.add(DirectoryObject(key=Callback(automatic_search, name='SeasonSearch', param_1=series_id, param_2=season_id),
                           title=L('search'),
                           thumb=R('search.png')))
    return oc


@route(PREFIX + '/series/add', new_series=dict)
def series_add(new_series):
    try:
        post('/series', json=new_series)
        return success_message()
    except Exception as e:
        return error_message(e)


@route(PREFIX + '/series/delete/put', entity_id=int)
def series_delete_put(entity_id):
    try:
        delete('/series/%d' % entity_id, json={'deleteFiles': Prefs['delete_files']})
        return success_message()
    except Exception as e:
        return error_message(e)


@route(PREFIX + '/series/delete', entity_id=int)
def series_delete(entity_id, title2):
    oc = ObjectContainer(title2=title2)
    oc.add(DirectoryObject(key=Callback(series_delete_put, entity_id=entity_id),
                           title=L('confirm'),
                           thumb=R('exclamation-triangle.png')))
    return oc


@route(PREFIX + '/series')
def series():
    try:
        response = get('/series')
        oc = ObjectContainer(title2=L('series'))
        if Client.Product in DumbKeyboard.clients:
            DumbKeyboard(PREFIX, oc, series_lookup, dktitle=L('add'), dkthumb=R('search.png'))
        else:
            oc.add(InputDirectoryObject(
                key=Callback(series_lookup),
                title=L('add'),
                thumb=R('search.png'),
                prompt=L('search')))
        for curr_series in sorted(response, key=lambda x: x['sortTitle']):
            title = curr_series['title']
            series_id = curr_series['id']
            summary = '{0}: {1}'.format(getdefault(curr_series, 'network'), curr_series['status'])
            do = DirectoryObject(
                    key=Callback(seriesid, series_id=series_id, title2=title),
                    title=title,
                    summary=summary)
            cover_type(curr_series, do)
            oc.add(do)
        return oc
    except Exception as e:
        return error_message(e)


@route(PREFIX + '/series/lookup')
def series_lookup(query):
    try:
        response = get('/series/lookup', params={'term': query})
        oc = ObjectContainer(title2=L('search'))
        # Default to first found profile
        profiles = get('/profile')
        if len(profiles) < 1:
            raise ValueError('No profile found')
        profile_id = profiles[0]['id']
        root_folders = get('/rootfolder')
        if len(root_folders) < 1:
            raise ValueError('No root folder')
        root_folder_path = root_folders[0]['path']
        for curr_series in response:
            tvdb_id = curr_series['tvdbId']
            title = curr_series['title']
            title_slug = curr_series['titleSlug']
            nbr_seasons = curr_series['seasons']
            season_folder = Prefs['season_folder']
            network = getdefault(curr_series, 'network')
            overview = getdefault(curr_series, 'overview')
            new_series = {'tvdbId': tvdb_id,
                          'title': title,
                          'qualityProfileId': profile_id,
                          'titleSlug': title_slug,
                          'seasons': nbr_seasons,
                          'seasonFolder': season_folder,
                          'rootFolderPath': root_folder_path,
                          'addOptions': {'searchForMissingEpisodes': False,
                                         'ignoreEpisodesWithFiles': True,
                                         'ignoreEpisodesWithoutFiles': False}}
            do = DirectoryObject(key=Callback(series_add, new_series=new_series),
                                 title=title,
                                 summary='%s: %s' % (network, overview))
            cover_type(curr_series, do)
            oc.add(do)
        return oc
    except Exception as e:
        return error_message(e)


@route(PREFIX + '/seriesid', series_id=int)
def seriesid(series_id, title2):
    try:
        oc = ObjectContainer(title2=title2)
        # noinspection PyBroadException
        try:
            res = get('/series/%d' % series_id)
            monitored = res['monitored']
            thumb = monitor_badge(monitored)
        except Exception:
            return oc
        oc.add(DirectoryObject(key=Callback(seasons, series_id=series_id),
                               title=L('list'),
                               thumb=R('th-list.png')))
        oc.add(PopupDirectoryObject(key=Callback(series_monitor, series_id=series_id),
                                    title=L('toggle'),
                                    summary='%s: %s' % (L('monitored'), monitored),
                                    thumb=thumb))
        oc.add(DirectoryObject(key=Callback(series_profile, series_id=series_id),
                               title=L('change'),
                               thumb=R('wrench.png')))
        oc.add(DirectoryObject(key=Callback(automatic_search, name='SeriesSearch', param_1=series_id),
                               title=L('automatic_search'),
                               thumb=R('search.png')))
        oc.add(DirectoryObject(key=Callback(series_delete, entity_id=series_id, title2=title2),
                               title=L('delete'),
                               thumb=R('trash-o.png')))
        return oc
    except Exception as e:
        return error_message(e)


@route(PREFIX + '/series/profile', series_id=int)
def series_profile(series_id):
    try:
        curr_series = get('/series/%d' % series_id)
        profile = get('/profile')
        oc = ObjectContainer(title2=L('quality'))
        for profile in profile:
            title = profile['name']
            quality_id = profile['id']
            if quality_id == curr_series['profileId']:
                thumb = R('square.png')
            else:
                thumb = R('circle-o.png')
            oc.add(DirectoryObject(key=Callback(series_profile_put, series_id=series_id, quality_id=quality_id),
                                   title=title,
                                   summary='%s: %s' % (L('cutoff'), profile['cutoff']['name']),
                                   thumb=thumb))
        return oc
    except Exception as e:
        return error_message(e)


@route(PREFIX + '/series/profile/put', series_id=int, quality_id=int)
def series_profile_put(series_id, quality_id):
    try:
        curr_series = get('/series/%d' % series_id)
        curr_series['profileId'] = quality_id
        put('/series', json=curr_series)
        return success_message()
    except Exception as e:
        return error_message(e)


@route(PREFIX + '/thumb', external=bool)
def get_thumb(url, external=False):
    # noinspection PyBroadException
    try:
        if external:
            return Redirect(url)
        else:
            response = get(url, accept='image/jpeg', content_type='')
            return DataObject(response.content, 'image/jpeg')
    except:
        Log.Exception('Error getting thumbnail')
        return DataObject(Resource.Load('question-circle.png', binary=True), 'image/png')


@route(PREFIX + '/missing', page=int, page_size=int)
def missing(page=1, page_size=19):
    oc = ObjectContainer(title2=L('missing'))
    return wanted(oc, '/missing', missing, page, page_size)


@route(PREFIX + '/cutoff', page=int, page_size=int)
def cutoff(page=1, page_size=19):
    oc = ObjectContainer(title2=L('unmet'))
    return wanted(oc, '/cutoff', cutoff, page, page_size)


def wanted(oc, command, func, page=1, page_size=19):
    try:
        res = get('/wanted' + command, params={'page': page,
                                               'pageSize': page_size,
                                               'sortKey': 'airDateUtc',
                                               'sortDir': 'desc',
                                               'filterKey': 'monitored',
                                               'filterValue': True})
        delta = utc_delta()
        for record in res['records']:
            season_nbr = record['seasonNumber']
            episode_nbr = record['episodeNumber']
            series_title = record['series']['title']
            date = record['airDateUtc']
            episode_id = record['id']
            title = '%s - %dX%02d - %s' % (series_title, season_nbr, episode_nbr, pretty_datetime(date, delta))
            episode_title = record['title']
            summary = '%s' % episode_title
            do = DirectoryObject(key=Callback(episode, episode_id=episode_id), title=title, summary=summary)
            cover_type(record['series'], do)
            oc.add(do)
        if page * page_size < res['totalRecords']:
            oc.add(NextPageObject(key=Callback(func, page=page + 1)))
        return oc
    except Exception as e:
        return error_message(e)


def history_get(callback, page, page_size, sort_key='date', sort_dir='desc', episode_id=None):
    try:
        params = {'page': page, 'pageSize': page_size, 'sortKey': sort_key, 'sortDir': sort_dir}
        if episode_id is not None:
            params['episodeId'] = episode_id
        records = get('/history', params=params)
        oc = ObjectContainer(title2=L('history'))
        delta = utc_delta()
        for record in records['records']:
            season_nbr = record['episode']['seasonNumber']
            episode_nbr = record['episode']['episodeNumber']
            series_title = record['series']['title']
            episode_title = record['episode']['title']
            episode_quality = record['quality']['quality']['name']
            event = record['eventType']
            episode_id = record['episodeId']
            if event == 'downloadFolderImported':
                summary = L('imported')
                thumb = R('download.png')
            elif event == 'downloadFailed':
                summary = L('failed')
                thumb = R('exclamation-triangle.png')
            elif event == 'grabbed':
                summary = L('grabbed')
                thumb = R('cloud-download.png')
            elif event == 'episodeFileDeleted':
                summary = L('deleted')
                thumb = R('trash-o.png')
            else:
                summary = event
                thumb = R('question-circle.png')
            title = '%s - %dX%02d - %s' % (series_title,
                                           season_nbr,
                                           episode_nbr,
                                           pretty_datetime(record['date'],
                                                           delta))
            summary = '%s: %s  %s: %s' % (summary, episode_title, L('quality'), episode_quality)
            oc.add(DirectoryObject(key=Callback(episode, episode_id=episode_id),
                                   title=title,
                                   summary=summary,
                                   thumb=thumb))
        if page * page_size < records['totalRecords']:
            oc.add(NextPageObject(key=Callback(callback, page=page + 1)))
        return oc
    except Exception as e:
        return error_message(e)


def pretty_datetime(d, delta):
    now = Datetime.Now()
    dt = Datetime.ParseDate(d).replace(tzinfo=None) + delta
    diff = now - dt
    # Future
    if dt > now:
        if diff.days < -7:
            pretty = dt.strftime('%d %b %Y')
        elif now.day == dt.day:
            pretty = u'%s %s' % (L('today'), dt.strftime('%I:%M%p'))
        elif (now + Datetime.Delta(days=1)).day == dt.day:
            pretty = u'%s %s' % (L('tomorrow'), dt.strftime('%I:%M%p'))
        else:
            pretty = dt.strftime('%a %I:%M%p')
    # Past
    else:
        s = diff.seconds
        if diff.days > 7:
            pretty = dt.strftime('%d %b %Y')
        elif diff.days > 1:
            pretty = u'%d %s' % (diff.days, L('days_ago'))
        elif diff.days == 1:
            pretty = L('yesterday')
        elif s < 3600:
            pretty = u'%d %s' % (s / 60, L('minutes_ago'))
        else:
            pretty = u'%d %s' % (s / 3600, L('hours_ago'))
    return pretty


def monitor_badge(is_monitored):
    return R('bookmark.png') if is_monitored else R('bookmark-o.png')


def success_message():
    return MessageContainer(L('Success'), L('Success'))


def error_message(exception):
    Log.Exception('Error!')
    return MessageContainer(L('Error'), exception.message)


def timestamp(time=Datetime.UTCNow()):
    """ Convert a datetime to ISO-8601 formatted in UTC to send to Sonarr """
    return time.isoformat('T').split('.')[0] + 'Z'


def get(command, params=None, accept='application/json', content_type='application/json'):
    headers = {'X-Api-Key': Prefs['api_key'],
               'Accept': accept,
               'Content-Type': content_type
               }
    Log.Debug(ENDPOINT + command)
    response = requests.get(ENDPOINT + command, params=params, headers=headers, auth=BASIC, verify=False, timeout=120)
    response.raise_for_status()
    header = response.headers['Content-Type']
    if not header.startswith(accept):
        Log.Warn('Expected %s but got %s' % (accept, header))
        raise ValueError('Invalid content type %s' % header)
    return response.json() if content_type == 'application/json' else response


def put(command, json=None):
    response = requests.put(ENDPOINT + command, json=json, headers=HEADERS, auth=BASIC, verify=False, timeout=90)
    response.raise_for_status()
    return response.json()


def post(command, json=None):
    response = requests.post(ENDPOINT + command, json=json, headers=HEADERS, auth=BASIC, verify=False, timeout=90)
    response.raise_for_status()
    return response.json()


def delete(command, json=None):
    response = requests.delete(ENDPOINT + command, json=json, headers=HEADERS, auth=BASIC, verify=False, timeout=90)
    response.raise_for_status()
    return response.json()


def utc_delta():
    local = Datetime.Now().replace(minute=0, second=0, microsecond=0)
    utc = Datetime.UTCNow().replace(minute=0, second=0, microsecond=0, tzinfo=None)
    delta = local - utc
    return delta


def getdefault(dictonary, key, default=L('unknown')):
    return dictonary[key] if key in dictonary else default


def cover_type(dictionary, do):
    for image in dictionary['images']:
        if image['coverType'] == 'poster':
            Log.Debug(image['url'])
            poster = image['url']
            if re.match('.*/MediaCover', poster):
                poster = re.sub('.*/MediaCover', '/MediaCover', image['url'])
                do.thumb = Callback(get_thumb, url=poster, external=False)
            else:
                do.thumb = Callback(get_thumb, url=poster, external=True)
            break
