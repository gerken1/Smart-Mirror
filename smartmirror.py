# smartmirror.py
# requirements
# requests, feedparser, traceback, Pillow

import locale
import threading
import time
import requests
import json
import traceback
import feedparser

from tkinter import *
from PIL import Image, ImageTk
from contextlib import contextmanager

LOCALE_LOCK = threading.Lock()

# General info
xlarge_text_size = 94
large_text_size = 48
medium_text_size = 28
small_text_size = 18
ui_locale = ''  # e.g. 'fr_FR' fro French, '' as default
time_format = 12  # 12 or 24
date_format = "%A %b %d, %Y"  # check python doc for strftime() for options
news_country_code = 'us'

# Weather and Location API info
temperature_units = 'imperial'
weather_api_token = ''  # create account at https://api.openweathermap.org
weather_lang = 'en'  # see https://api.openweathermap.org/data/3.0/weather for full list of language parameters values
weather_unit = 'us'  # see https://api.openweathermap.org/data/3.0/weather for full list of unit parameters values
latitude = "27.976287"  # Used for getting location and weather, see https://geocode.xyz/api#python for location API info
longitude = "-82.535637"  # Used for getting location and weather, see https://geocode.xyz/api#python for location API info


@contextmanager
def setlocale(name):  # thread proof function to work with locale
    with LOCALE_LOCK:
        saved = locale.setlocale(locale.LC_ALL)
        try:
            yield locale.setlocale(locale.LC_ALL, name)
        finally:
            locale.setlocale(locale.LC_ALL, saved)


# icon lookup for using https://api.openweathermap.org/data/3.0/weather
icon_lookup = {
    '01d': "assets/Sun.png",  # clear sky day
    '01n': "assets/Moon.png",  # clear sky night
    '02d': "assets/PartlySunny.png",  # partly cloudy day
    '02n': "assets/PartlyMoon.png",  # partly cloudy night
    '04d': "assets/PartlySunny.png",  # Broken cloudy day
    '04n': "assets/PartlyMoon.png",  # Broken cloudy night
    '03d': "assets/Cloud.png",  # cloudy day
    '03n': "assets/PartlyMoon.png",  # cloudy night
    '09d': "assets/Rain.png",  # rain day
    '09n': "assets/Rain.png",  # rain day
    '10d': "assets/Rain.png",  # rain day
    '10n': "assets/Rain.png",  # rain day
    '13d': "assets/Snow.png",  # snow day
    '13n': "assets/Snow.png",  # snow night
    '50d': "assets/Haze.png",  # fog day
    '50n': "assets/Haze.png",  # fog night
    '11d': "assets/Storm.png",  # thunderstorm
    '11n': "assets/Storm.png",  # thunderstorm night
    'wind': "assets/Wind.png",  # wind - no mapping with openweathermap API
    'tornado': "assets/Tornado.png",  # tornado - no mapping with openweathermap API
    'hail': "assets/Hail.png"  # hail - no mapping with openweathermap API
}


class Clock(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')
        # initialize time label
        self.time1 = ''
        self.timeLbl = Label(self, font=('Helvetica', large_text_size), fg="white", bg="black")
        self.timeLbl.pack(side=TOP, anchor=E)
        # initialize date label
        self.date1 = ''
        self.dateLbl = Label(self, text=self.date1, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.dateLbl.pack(side=TOP, anchor=W)
        self.tick()

    def tick(self):
        with setlocale(ui_locale):
            if time_format == 12:
                time2 = time.strftime('%I:%M %p')  # hour in 12h format
            else:
                time2 = time.strftime('%H:%M')  # hour in 24h format

            date2 = time.strftime(date_format)

            # if time string has changed, update it
            if time2 != self.time1:
                self.time1 = time2
                self.timeLbl.config(text=time2)
            if date2 != self.date1:
                self.date1 = date2
                self.dateLbl.config(text=date2)

            # calls itself every 200 milliseconds
            # to update the time display as needed
            # could use >200 ms, but display gets jerky
            self.timeLbl.after(200, self.tick)


class Weather(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')
        self.location = ''
        self.temperature = ''
        self.currently = ''
        self.forecast = ''
        self.icon = ''
        self.highLow = ''
        self.humidity = ''
        self.wind = ''
        self.locationLbl = Label(self, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.locationLbl.pack(side=TOP, anchor=W)
        self.degreeFrm = Frame(self, bg="black")
        self.degreeFrm.pack(side=TOP, anchor=W)
        self.temperatureLbl = Label(self.degreeFrm, font=('Helvetica', xlarge_text_size), fg="white", bg="black")
        self.temperatureLbl.pack(side=LEFT, anchor=N)
        self.currentlyLbl = Label(self, font=('Helvetica', medium_text_size), fg="white", bg="black")
        self.currentlyLbl.pack(side=TOP, anchor=W)
        self.iconLbl = Label(self.degreeFrm, bg="black")
        self.iconLbl.pack(side=LEFT, anchor=E, padx=20)
        self.highLowLbl = Label(self, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.highLowLbl.pack(side=TOP, anchor=W)
        self.humidityLbl = Label(self, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.humidityLbl.pack(side=TOP, anchor=W)
        self.windLbl = Label(self, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.windLbl.pack(side=TOP, anchor=W)
        self.forecastLbl = Label(self, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.forecastLbl.pack(side=TOP, anchor=W)
        self.get_weather()

    def get_location(self):
        try:
            geo_url = "https://geocode.xyz/?locate=%s,%s&geoit=json" % (latitude, longitude)
            req = requests.get(geo_url)
            geo_url_json = json.loads(req.text)
            city = geo_url_json['city']
            state = geo_url_json['state']
            return "%s, %s" % (city, state)
        except Exception as e:
            traceback.print_exc()
            print("Error: %s. Cannot get location." % e)

    def get_weather(self):
        try:
            weather_req_url = "https://api.openweathermap.org/data/3.0/onecall?lat=%s&lon=%s&exclude=minutely,hourly&units=%s&appid=%s" % (
                latitude, longitude, temperature_units, weather_api_token)

            r = requests.get(weather_req_url)
            weather_obj = json.loads(r.text)

            degree_sign = u'\N{DEGREE SIGN}'

            location = self.get_location()
            temperature = "%s%s" % (str(int(weather_obj['current']['temp'])), degree_sign)
            currently = weather_obj['current']['weather'][0]['description']

            high = "%s%s" % (str(int(round(weather_obj['daily'][0]['temp']['max']))), degree_sign)
            low = "%s%s" % (str(int(round(weather_obj['daily'][0]['temp']['min']))), degree_sign)
            humidity = weather_obj['current']['humidity']
            wind = weather_obj['current']['wind_speed']
            forecast = ""  # need to add this still

            icon_id = weather_obj['current']['weather'][0]['icon']
            icon = None

            if icon_id in icon_lookup:
                icon = icon_lookup[icon_id]

            if icon is not None:
                if self.icon != icon:
                    self.icon = icon
                    image = Image.open(icon)
                    image = image.resize((125, 125), Image.ANTIALIAS)
                    image = image.convert('RGB')
                    photo = ImageTk.PhotoImage(image)

                    self.iconLbl.config(image=photo)
                    self.iconLbl.image = photo
            else:
                self.iconLbl.config(image='')  # remove image

            if self.location != location:
                if location == ", ":
                    self.location = "Cannot Pinpoint Location"
                    self.locationLbl.config(text="Cannot Pinpoint Location")
                else:
                    self.location = location
                    self.locationLbl.config(text=location)

            if self.temperature != temperature:
                self.temperature = temperature
                self.temperatureLbl.config(text=temperature)

            if self.currently != currently:
                self.currently = currently
                self.currentlyLbl.config(text=currently.upper())

            if self.highLow != high + low:
                self.highLow = high + low
                self.highLowLbl.config(text="High: %s | Low: %s" % (high, low))

            if self.humidity != humidity:
                self.humidity = humidity
                self.humidityLbl.config(text="Humidity: %s%%" % humidity)

            if self.wind != wind:
                self.wind = wind
                self.windLbl.config(text="Wind: %s mph" % wind)

            if self.forecast != forecast:
                self.forecast = forecast
                self.forecastLbl.config(text=forecast)

        except Exception as e:
            traceback.print_exc()
            print("Error: %s. Cannot get weather." % e)

        self.after(600000, self.get_weather)  # Rate limit - 10 mins

    @staticmethod
    def convert_kelvin_to_fahrenheit(kelvin_temp):
        return 1.8 * (kelvin_temp - 273) + 32


class News(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.config(bg='black')
        self.title = 'News'  # 'News' is more internationally generic
        self.newsLbl = Label(self, text=self.title, font=('Helvetica', medium_text_size), fg="white", bg="black")
        self.newsLbl.pack(side=TOP, anchor=W)
        self.headlinesContainer = Frame(self, bg="black")
        self.headlinesContainer.pack(side=TOP)
        self.get_headlines()

    def get_headlines(self):
        try:
            # remove all children
            for widget in self.headlinesContainer.winfo_children():
                widget.destroy()
            if news_country_code is None:
                headlines_url = "https://news.google.com/news?ned=us&output=rss"
            else:
                headlines_url = "https://news.google.com/news?ned=%s&output=rss" % news_country_code

            feed = feedparser.parse(headlines_url)

            for post in feed.entries[0:3]:
                headline = NewsHeadline(self.headlinesContainer, post.title)
                headline.pack(side=TOP, anchor=W)
        except Exception as e:
            traceback.print_exc()
            print("Error: %s. Cannot get news." % e)

        self.after(600000, self.get_headlines)  # Rate limit - 10 mins


class NewsHeadline(Frame):
    def __init__(self, parent, event_name=""):
        Frame.__init__(self, parent, bg='black')

        image = Image.open("assets/Newspaper.png")
        image = image.resize((25, 25), Image.ANTIALIAS)
        image = image.convert('RGB')
        photo = ImageTk.PhotoImage(image)

        self.iconLbl = Label(self, bg='black', image=photo)
        self.iconLbl.image = photo
        self.iconLbl.pack(side=LEFT, anchor=N)

        self.eventName = event_name
        self.eventNameLbl = Label(self, text=self.eventName, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.eventNameLbl.pack(side=LEFT, anchor=N)


class Markets(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, *args, **kwargs)
        self.config(bg='black')
        self.title = 'Markets'
        self.mktsLbl = Label(self, text=self.title, font=('Helvetica', medium_text_size), fg='white', bg='black')
        self.mktsLbl.pack(side=TOP, anchor=W)
        self.stockContainer = Frame(self, bg='black')
        self.stockContainer.pack(side=TOP)
        self.get_stocks()

    def get_stocks(self):
        try:
            # remove all children
            for widget in self.stockContainer.winfo_children():
                widget.destroy()

            headlines_url = 'https://seekingalpha.com/feed.xml'
            feed = feedparser.parse(headlines_url)

            for post in feed.entries[0:3]:
                headline = Marketsheadline(self.stockContainer, post.title)
                headline.pack(side=TOP, anchor=W)
        except Exception as e:
            traceback.print_exc()
            print("Error: %s. Cannot get market news" % e)

        self.after(600000, self.get_stocks)  # Rate limit - 5 mins


class Marketsheadline(Frame):
    def __init__(self, parent, event_name=''):
        Frame.__init__(self, parent, bg='black')
        image = Image.open("assets/Newspaper.png")
        image = image.resize((25, 25), Image.ANTIALIAS)
        image = image.convert("RGB")
        photo = ImageTk.PhotoImage(image)

        self.iconLbl = Label(self, bg='black', image=photo)
        self.iconLbl.image = photo
        self.iconLbl.pack(side=LEFT, anchor=N)

        self.eventName = event_name
        self.eventNameLbl = Label(self, text=self.eventName, font=("Helvetica", small_text_size), fg='white', bg='black')
        self.eventNameLbl.pack(side=LEFT, anchor=N)


class Calendar(Frame):
    def __init__(self, parent, *args, **kwargs):
        Frame.__init__(self, parent, bg='black')
        self.title = 'Calendar Events'
        self.calendarLbl = Label(self, text=self.title, font=('Helvetica', medium_text_size), fg="white", bg="black")
        self.calendarLbl.pack(side=TOP, anchor=E)
        self.calendarEventContainer = Frame(self, bg='black')
        self.calendarEventContainer.pack(side=TOP, anchor=E)
        self.get_events()

    def get_events(self):
        # TODO: implement this method
        # reference https://developers.google.com/google-apps/calendar/quickstart/python

        # remove all children
        for widget in self.calendarEventContainer.winfo_children():
            widget.destroy()

        calendar_event = CalendarEvent(self.calendarEventContainer)
        calendar_event.pack(side=TOP, anchor=E)
        pass


class CalendarEvent(Frame):
    def __init__(self, parent, event_name="Event 1"):
        Frame.__init__(self, parent, bg='black')
        self.eventName = event_name
        self.eventNameLbl = Label(self, text=self.eventName, font=('Helvetica', small_text_size), fg="white", bg="black")
        self.eventNameLbl.pack(side=TOP, anchor=E)


class FullscreenWindow:

    def __init__(self):
        self.tk = Tk()
        self.tk.configure(background='black')
        self.topFrame = Frame(self.tk, background='black')
        self.bottomFrame = Frame(self.tk, background='black')
        self.centerFrame = Frame(self.tk, background='black')
        self.topFrame.pack(side=TOP, fill=BOTH, expand=YES)
        self.bottomFrame.pack(side=BOTTOM, fill=BOTH, expand=YES)
        self.centerFrame.pack(side=LEFT, fill=BOTH, expand=YES)
        self.state = False
        self.tk.bind("<Return>", self.toggle_fullscreen)
        self.tk.bind("<Escape>", self.end_fullscreen)
        # clock
        self.clock = Clock(self.topFrame)
        self.clock.pack(side=LEFT, anchor=N, padx=100, pady=60)
        # weather
        self.weather = Weather(self.topFrame)
        self.weather.pack(side=RIGHT, anchor=N, padx=100, pady=60)
        # news
        self.news = News(self.bottomFrame)
        self.news.pack(side=BOTTOM, fill=Y, anchor=SW, padx=100, ipady=10)
        # markets
        self.markets = Markets(self.bottomFrame)
        self.markets.pack(side=BOTTOM, anchor=SW, padx=100, pady=20)
        # calender - removing for now
        # self.calender = Calendar(self.bottomFrame)
        # self.calender.pack(side = RIGHT, anchor=S, padx=100, pady=60)

    def toggle_fullscreen(self, event=None):
        self.state = not self.state  # Just toggling the boolean
        self.tk.attributes("-fullscreen", self.state)
        return "break"

    def end_fullscreen(self, event=None):
        self.state = False
        self.tk.attributes("-fullscreen", False)
        return "break"


if __name__ == '__main__':
    w = FullscreenWindow()
    w.tk.mainloop()
