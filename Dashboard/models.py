from django.db import models
from bs4 import BeautifulSoup, SoupStrainer; import requests
from datetime import datetime


class PlanetaKino(models.Model):
    class Meta:
        ordering = ['date']
    title = models.CharField(max_length=20)
    posterIMG = models.CharField(max_length=140)
    href = models.CharField(max_length=140)
    date = models.CharField(max_length=20)
    inTheater = models.BooleanField()

    def __str__(self):
        res = "{1} {4} {0} d: {2} p: {3}"
        res = res.format(self.title, self.date, self.href, self.posterIMG, self.inTheater)
        return res

    def list(pkHREF):
        resp = requests.get(pkHREF)
        strainer = SoupStrainer('div', attrs={'class': 'movies-list'});
        soup = BeautifulSoup(resp.text, "html.parser", parse_only=strainer)

        results = []
        for each in soup.find_all(attrs={'class': 'movie-block'}):
            dateresult = each.find(attrs={'class': 'movie-block__text-date'}).text
            if dateresult[:3] == " з ":
                dateresult = dateresult[3:]
                dateresult = datetime.strptime(dateresult, '%d.%m.%Y')
                inTheaterresult = False
            elif dateresult[:3] == "до ":
                dateresult = dateresult[3:]
                dateresult = datetime.strptime(dateresult, '%d.%m.%y')
                inTheaterresult = True
            #print(dateresult)

            movie = PlanetaKino(
                title=each.find('img')['alt'],
                posterIMG="https://planetakino.ua"+each.find('img')['data-original'],
                href="https://planetakino.ua"+str(each.find(attrs={'class': 'movie-block__text_title'})['href']),
                date=dateresult,
                inTheater=inTheaterresult
            )
            results.append(movie)

        #for each in results:
        #    print(each)

        return results


class Dashboard(models.Model):
    title = "Dashboard"
    PlanetaKinoHREF = "https://planetakino.ua/kharkov/movies/"
    movies = []

    def __init__(self):
        self.movies = PlanetaKino.list(Dashboard.PlanetaKinoHREF)
        # print(self.movies)