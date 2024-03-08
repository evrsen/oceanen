import hashlib
import uuid
import time

from flask import Flask
from mechanicalsoup import StatefulBrowser
from requests import Response

from database import query_db, get_db


def create_uuid_from_string(val: str) -> uuid.UUID:
    hex_string = hashlib.md5(val.encode("UTF-8")).hexdigest()
    return uuid.UUID(hex=hex_string)


def scrape_events(b: StatefulBrowser, resp: Response) -> dict[str, str]:
    anchors = resp.soup.find_all("a")

    for anchor in anchors:
        event_url = anchor.get("href")
        event_title = anchor.get("title")

        if event_url is None or "event" not in event_url or event_title is None:
            continue

        event_uuid = create_uuid_from_string(event_url)
        event_page = b.get(event_url)
        event_info = event_page.soup.find("ul", {"class": "event__info"})
        event_date, event_age, event_price = [i.text for i in event_info.find_all("span")]
        event_time = event_info.find("time").text

        event_price = "".join([i for i in event_price.strip() if i.isdigit()])
        event_age = "".join([i for i in event_age.strip() if i.isdigit()])

        yield {
            "uuid": str(event_uuid),
            "url": event_url.strip(),
            "title": event_title.strip(),
            "date": event_date.strip(),
            "time": event_time.strip(),
            "price": "Gratis" if not event_price else event_price + " kr",
            "age": event_age + " år",
        }


def start_scraper(b: StatefulBrowser, a: Flask):
    uuids = []

    with a.app_context():
        db = get_db()
        db.cursor().execute("""
            CREATE TABLE IF NOT EXISTS events (
                uuid TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                price TEXT NOT NULL,
                age TEXT NOT NULL
            )
        """)
        db.commit()

        events = query_db("SELECT uuid FROM events")
        if events:
            for _uuid in events:
                uuids.append(_uuid[0])

    while True:
        resp = b.refresh()

        for event in scrape_events(b, resp):
            if event.get("uuid") in uuids:
                continue

            with a.app_context():
                db = get_db()
                db.cursor().execute("INSERT INTO events (uuid, url, title, date, time, price, age) VALUES (?, ?, ?, ?, ?, ?, ?)", (
                    event.get("uuid"),
                    event.get("url"),
                    event.get("title"),
                    event.get("date"),
                    event.get("time"),
                    event.get("price"),
                    event.get("age"),
                ))
                db.commit()

            uuids.append(event.get("uuid"))

        time.sleep(60)
