import threading

from flask import Flask, render_template, g
from mechanicalsoup import StatefulBrowser

from database import query_db
from scraper import start_scraper


def create_browser(url, *args, **kwargs) -> StatefulBrowser:
    b = StatefulBrowser(*args, **kwargs)
    b.open(url)
    return b


def create_app() -> Flask:
    a = Flask(__name__)

    @a.route('/')
    def index():
        events = []
        data = query_db("SELECT * FROM events")

        for event in data:
            events.append({
                "url": event[1],
                "title": event[2] if len(event[2]) < 24 else event[2][:21] + "...",
                "date": event[3],
                "time": event[4],
                "price": event[5],
                "age": event[6],
            })

        return render_template('index.html', events=events)

    @a.teardown_appcontext
    def close_connection(_):
        db = getattr(g, '_database', None)
        if db is not None:
            db.close()

    return a


if __name__ == "__main__":
    browser = create_browser("https://www.oceanen.com")
    app = create_app()

    threading.Thread(target=start_scraper, args=(browser, app), daemon=True).start()

    app.run(debug=True)
    browser.close()
