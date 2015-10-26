from datetime import datetime

L = {
    "series": "Series",
    "seriesInfo": "View all series or add to your collection",
    "addSeries": "Add series to collection",
    "addSeriesInfo": "Using Default Profile but NOT monitored. Change this in Series section.",
    "seriesSearch": "Search for Series",
    "seasonSearch": "Search for Season",
    "search": "Search Triggered",
    "season": "Season %s",
    "deleteSeries": "Delete Series",
    "deleteSeason": "Delete Season",
    "episodeSearch": "Episode Search",
    "listEpisodes": "List episodes",
    "episodeSearchInfo": "Automatic search for this episode",
    "calendar": "Calendar",
    "calendarInfo": "This week's upcoming episodes",
    "queue": "Queue",
    "queueInfo": "This week's upcoming episodes",
    "history": "History",
    "historyInfo": "Recently downloaded episodes",
    "imported": "Imported",
    "failed": "Failed",
    "grabbed": "Grabbed",
    "deleted": "Deleted",
    "confirmDelete": "Confirm Deletion",
    "fileWarn": "Warning: All files will be deleted from disk!",
    "missing": "Missing",
    "missingInfo": "List missing episodes",
    "settings": "Settings",
    "settingsInfo": "Plugin settings",
    "success": "Success",
    "error": "Error",
    "status": "Status",
    "noResults": "No results",
    "network": "Network",
    "monitored": "Monitored",
    "monitorConfirm": "Confirm changing monitoring to %s",
    "monitorSet": "Monitor set to %s",
    "seasons": "Seasons",
    "noInfo": "No information provided",
    "unknown": "Unknown",
    "empty": "Empty",
    "quality": "Quality",
    "listSeasons": "List seasons",
    "toggleMonitor": "Toggle Monitoring",
    "changeQuality": "Change Quality",
    "current": " (Current)",
    "cutOff": "Cutoff",
    "saved": "Changes saved",
    "downloaded": "Downloaded: %s - %s",
    "today": "Today at ",
    "tomorrow": "Tomorrow at ",
    "yesterday": "Yesterday",
    "daysago": " days ago",
    "minutesago": " minutes ago",
    "hourago": "1 hour ago",
    "hoursago": " hours ago"
}
Prefs = {
    "ip": "192.168.1.14",
    "port": "8989",
    "base": "/sonarr",
    "https": False,
    "apiKey": "12345",
    "username": "user",
    "password": "pass",
    "auth": "basic"
}

def R(res):
    return ""


def L(res):
    return ""


class logger(object):
    def Info(self, msg):
        pass

    def Debug(self, msg):
        pass

    def Critical(self, msg):
        pass


class ObjectContainer(object):
    def __init__(self, *args, **kwargs):
        pass

    def __len__(self):
        return 0

    def add(self, container):
        pass


class MessageContainer(ObjectContainer):
    pass


class DirectoryObject(ObjectContainer):
    pass


class Callback(object):
    def __init__(self, *args, **kwargs):
        pass


class Datetime(object):
    @staticmethod
    def Now():
        return datetime.now()

    @staticmethod
    def ParseDate(date):
        return ""

    @staticmethod
    def Delta(**kwargs):
        return Datetime


class Resource(object):
    @staticmethod
    def Load(*args, **kwargs):
        return ""


class DataObject(object):
    def __init__(self, *args, **kargs):
        pass


class PrefsObject(ObjectContainer):
    pass


class InputDirectoryObject(ObjectContainer):
    pass


class NextPageObject(ObjectContainer):
    pass


class PopupDirectoryObject(ObjectContainer):
    pass


def handler(*args, **kwargs):
    def func_wrapper(name):
        pass

    return func_wrapper


def route(*args, **kwargs):
    return handler(args, kwargs)


Log = logger()
