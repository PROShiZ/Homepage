from django.views.generic import ListView
from .models import PlanetaKino, keyValue
from datetime import datetime, time
# from weatherCast.models import weatherCast
from feedUpdate.models import feedUpdate, feed


class DashboardView(ListView):
    template_name = "Dashboard/main.html"
    context_object_name = "fromView"

    def get_queryset(self):
        header_night = "Доброй ночи"
        header_morning = "Доброе утро"
        header_day = "Привет"
        header_evening = "Доброго вечера"

        now = datetime.now().time()
        if now < time(6):
            title_daypart = header_night
        elif now < time(12):
            title_daypart = header_morning
        elif now < time(18):
            title_daypart = header_day
        else:
            title_daypart = header_evening

        title_weather = {}
        title_weather['temp'] = keyValue.objects.filter(key='weatherNowTemp')[0].value
        title_weather['summary'] = keyValue.objects.filter(key='weatherNowSum')[0].value
        title_weather['precipProbability'] = keyValue.objects.filter(key='weatherNowProb')[0].value
        title_weather['icon'] = keyValue.objects.filter(key='weatherNowIcon')[0].value

        movies = PlanetaKino.objects.filter(inTheater=True)

        items_limit = 42
        items_limit_select = items_limit*8

        feed_titles = []
        for each in feed.feeds_by_emoji():
            feed_titles.append(each.title)

        feedUpdate_list = []
        for each in feedUpdate.objects.all()[:items_limit_select]:
            if each.title in feed_titles:
                feedUpdate_list.append(each)
        feedUpdate_list = feedUpdate_list[:items_limit]

        return {
            'title_daypart': title_daypart,
            'title_weather': title_weather,
            'movies': movies,
            'feedUpdate_list': feedUpdate_list,
        }
