import datetime
import decimal
import os
from pathlib import Path
import re
import zipfile
from csv import reader

import requests
from bs4 import BeautifulSoup
import browsercookie

from results.models import DKContest, DKContestPayout, Player #  DKResult

# from nba.utils import get_date_yearless

STOP_WORDS = set(["PG", "SG", "SF", "PF", "C", "F", "G", "UTIL"])

CSVPATH = Path("mysite/results/data/results/")
COOKIES = browsercookie.chrome()
HEADERS = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, sdch",
    "Accept-Language": "en-US,en;q=0.8",
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "Host": "www.draftkings.com",
    "Pragma": "no-cache",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/48.0.2564.97 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
}


def run(contest_ids=[], contest=True, resultscsv=True, resultsparse=True):
    """
    Downloads and unzips the CSV results and then populates the database
    """

    def dollars_to_decimal(dollarstr):
        return decimal.Decimal(dollarstr.replace("$", "").replace(",", ""))

    def get_contest_data(contest_id):
        def datestr_to_date(datestr):
            """
            @param datestr [str]: "MON DD, H:MM PM EST"
                                  (e.g. "NOV 29, 6:00 PM EST")
                                  "MM/DD H:MM PM EST"
                                  (e.g. "02/18 7:00 PM EST")
            @return [datetime.date]
            """
            if "," in datestr:
                return get_date_yearless(datestr.split(",")[0])
            else:
                datenum = datestr.split(" ")[0]
                month, day = [int(s) for s in datenum.split("/")]
                monthstr = datetime.date(1900, month, 1).strftime("%b")
                return get_date_yearless("%s %s" % (monthstr, day))

        url = f"https://www.draftkings.com/contest/gamecenter/{contest_id}"

        response = requests.get(url, headers=HEADERS, cookies=COOKIES)
        soup = BeautifulSoup(response.text, "html5lib")

        try:
            header = soup.find_all(class_="top")[0].find_all("h4")
            info_header = (
                soup.find_all(class_="top")[0]
                .find_all(class_="info-header")[0]
                .find_all("span")
            )
            completed = info_header[3].string
            print(int(info_header[4].string))
            if completed.strip().upper() == "COMPLETED":
                print("completed")
                DKContest.objects.update_or_create(
                    dk_id=contest_id,
                    defaults={
                        "name": header[0].string,
                        "total_prizes": dollars_to_decimal(header[1].string),
                        "date": datestr_to_date(info_header[0].string),
                        "entries": int(info_header[2].string),
                        "positions_paid": int(info_header[4].string),
                    },
                )
            else:
                print(f"Contest {contest_id} is still in progress")
        except IndexError:
            # This error occurs for old contests whose pages no longer are
            # being served.
            # Traceback:
            # header = soup.find_all(class_='top')[0].find_all('h4')
            # IndexError: list index out of range
            print(f"Couldn't find DK contest with id {contest_id}")

    def get_contest_prize_data(contest_id):
        def place_to_number(s):
            return int(re.findall(r"\d+", s)[0])

        url = "https://www.draftkings.com/contest/detailspop"
        PARAMS = {
            "contestId": contest_id,
            "showDraftButton": False,
            "defaultToDetails": True,
            "layoutType": "legacy",
        }
        response = requests.get(url, headers=HEADERS, cookies=COOKIES, params=PARAMS)
        soup = BeautifulSoup(response.text, "html5lib")

        try:
            payouts = soup.find_all(id="payouts-table")[0].find_all("tr")
            entry_fee = soup.find_all("h2")[0].text.split("|")[2].strip()
            dkcontest = DKContest.objects.get(dk_id=contest_id)
            dkcontest.entry_fee = dollars_to_decimal(entry_fee)
            dkcontest.save()
            for payout in payouts:
                places, payout = [x.string for x in payout.find_all("td")]
                places = [place_to_number(x.strip()) for x in places.split("-")]
                top, bottom = (places[0], places[0]) if len(places) == 1 else places
                DKContestPayout.objects.update_or_create(
                    contest=dkcontest,
                    upper_rank=top,
                    lower_rank=bottom,
                    defaults={"payout": dollars_to_decimal(payout)},
                )
        except IndexError:
            # See comment in get_contest_data()
            print(f"Couldn't find DK contest with id {contest_id}")

    def get_contest_result_data(contest_id):
        url = f"https://www.draftkings.com/contest/gamecenter/{contest_id}"
        # update referer
        HEADERS["referer"] = url

        OUTFILE = "out.zip"

        def read_response(response):
            print(f"Downloading and unzipping file from {response.url}")
            with open(OUTFILE, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)

        def unzip_data():
            with open(OUTFILE, "rb") as f:
                z = zipfile.ZipFile(f)
                for name in z.namelist():
                    z.extract(name, CSVPATH)

        try:
            export_url = url.replace("gamecenter", "exportfullstandingscsv")
            read_response(requests.get(export_url, headers=HEADERS, cookies=COOKIES))
            unzip_data()
        except zipfile.BadZipfile:
            print(f"Couldn't download/extract CSV zip for {contest_id}")

    def parse_contest_result_csv(contest_id):
        def parse_entry_name(entry_name):
            return entry_name.split()[0]

        def get_player_cached(name, player_cache):
            if name in player_cache:
                result = player_cache[name]
                return result
            else:
                return Player.get_by_name(name)

        player_cache = {p.full_name: p for p in Player.objects.all() if p.full_name}

        contest, _ = DKContest.objects.get_or_create(dk_id=contest_id)
        filename = "{}/contest-standings-{}}.csv".format(CSVPATH, contest_id)
        try:
            with open(filename, "r") as f:
                csvreader = reader(f, delimiter=",", quotechar='"')
                for i, row in enumerate(csvreader):
                    # Rank, EntryId, EntryName, TimeRemaining, Points, Lineup
                    if i != 0:
                        rank, entry_id, entry_name, _, points, lineup = row
                        lineup = lineup.split()
                        for wordidx, word in enumerate(lineup[:]):
                            if word in STOP_WORDS:
                                lineup[wordidx] = "\t"
                        word_list = " ".join(lineup).split("\t")
                        players = [
                            get_player_cached(word.strip(), player_cache)
                            for word in " ".join(lineup).split("\t")
                            if word.strip()
                        ]
                        if players:
                            DKResult.objects.update_or_create(
                                dk_id=entry_id,
                                defaults={
                                    "contest": contest,
                                    "name": parse_entry_name(entry_name),
                                    "rank": rank,
                                    "points": points,
                                    "pg": players[0],
                                    "sg": players[1],
                                    "sf": players[2],
                                    "pf": players[3],
                                    "c": players[4],
                                    "g": players[5],
                                    "f": players[6],
                                    "util": players[7],
                                },
                            )
                    if i % 5000 == 0:
                        print(f"{i} DKResult records created")
        except IOError:
            print(f"Couldn't find CSV results file {filename}")

    for contest_id in contest_ids:
        if contest:
            get_contest_data(contest_id)
            get_contest_prize_data(contest_id)
        if resultscsv:
            get_contest_result_data(contest_id)
        if resultsparse:
            parse_contest_result_csv(contest_id)
