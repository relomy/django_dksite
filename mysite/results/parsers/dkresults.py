import datetime
import decimal
import io
import logging
import re
import zipfile
from csv import reader
from pathlib import Path

import browsercookie
import requests
from bs4 import BeautifulSoup

from results.models import (
    DKContest,
    DKContestPayout,
    DKResult,
    DKResultOwnership,
    Player,
)
from results.utils import get_datetime_yearless

logger = logging.getLogger(__name__)

STOP_WORDS = set(["PG", "SG", "SF", "PF", "C", "F", "G", "UTIL"])

DIR = Path(__file__).parents[0]
CSVPATH = Path(DIR, "../data/results/")
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


def dollars_to_decimal(dollarstr):
    return decimal.Decimal(dollarstr.replace("$", "").replace(",", ""))


def datestr_to_date(datestr):
    """
    @param datestr [str]: "MON DD, H:MM PM EST"
                            (e.g. "NOV 29, 6:00 PM EST")
                            "MM/DD H:MM PM EST"
                            (e.g. "02/18 7:00 PM EST")
    @return [datetime.date]
    """
    if "," in datestr:
        return get_datetime_yearless(datestr.split(",")[0])

    # massage
    datenum = datestr.split(" ")[0]
    month, day = [int(s) for s in datenum.split("/")]
    monthstr = datetime.date(1900, month, 1).strftime("%b")
    return get_datetime_yearless(f"{monthstr} {day}")


def get_contest_data(contest_id):
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
        logger.debug("Positions paid: %s", int(info_header[4].string))
        if completed.strip().upper() == "COMPLETED":
            logger.debug("contest %s is completed", contest_id)
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
            logger.warning("Contest %s is still in progress", contest_id)
    except IndexError:
        # This error occurs for old contests whose pages no longer are
        # being served.
        # Traceback:
        # header = soup.find_all(class_='top')[0].find_all('h4')
        # IndexError: list index out of range
        logger.error("Couldn't find DK contest with id %s", contest_id)


def place_to_number(place):
    return int(re.findall(r"\d+", place)[0])


def get_contest_prize_data(contest_id):
    url = "https://www.draftkings.com/contest/detailspop"
    params = {
        "contestId": contest_id,
        "showDraftButton": False,
        "defaultToDetails": True,
        "layoutType": "legacy",
    }
    response = requests.get(url, headers=HEADERS, cookies=COOKIES, params=params)
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
    except IndexError as ex:
        # See comment in get_contest_data()
        logger.error("Couldn't find DK contest with id %s: %s", contest_id, ex)


def save_contest_standings_to_file(response, contest_id):
    logger.info("Downloading file from %s", response.url)

    if (
        "Content-Length" in response.headers
        and response.headers["Content-Length"] == "0"
    ):
        logger.debug("Content-Length is empty - returning False")
        return False

    # logger.debug("response headers: %s", response.headers)

    filename = Path(CSVPATH, f"contest-standings-{contest_id}.csv")
    if "text/html" in response.headers["Content-Type"]:
        return False
    elif response.headers["Content-Type"] == "text/csv":
        with open(filename, "w", newline="") as file:
            file.writelines(response.content.decode("utf-8"))
        return True
    else:
        zfile = zipfile.ZipFile(io.BytesIO(response.content))
        for name in zfile.namelist():
            zfile.extract(name, CSVPATH)
        return True
        # with open(OUTFILE, "wb") as f:
        #     for chunk in response.iter_content(chunk_size=1024):
        #         if chunk:
        #             f.write(chunk)


def get_contest_result_data(contest_id):
    url = f"https://www.draftkings.com/contest/gamecenter/{contest_id}"
    # update referer
    # HEADERS["Referer"] = url

    try:
        export_url = url.replace("gamecenter", "exportfullstandingscsv")
        response = requests.get(export_url, cookies=COOKIES)
        return save_contest_standings_to_file(response, contest_id)

        # unzip_data()
    except zipfile.BadZipfile:
        logger.error("Couldn't download/extract CSV zip for %s", contest_id)


def parse_entry_name(entry_name):
    return entry_name.split()[0]


def get_player_cached(name, player_cache):
    if name in player_cache:
        result = player_cache[name]
        return result
    return Player.get_by_name(name)


def parse_contest_result_csv(sport, contest_id):
    # player_cache = {p.full_name: p for p in Player.objects.all() if p.full_name}
    player_cache = {
        p.name: p for p in Player.objects.filter(sport__exact=sport) if p.name
    }

    vips = [
        "aplewandowski",
        "FlyntCoal",
        "Cubbiesftw23",
        "Mcoleman1902",
        "cglenn91",
        "Notorious",
        "Bra3105",
        "ChipotleAddict",
    ]

    contest, _ = DKContest.objects.get_or_create(dk_id=contest_id)
    filename = CSVPATH / f"contest-standings-{contest_id}.csv"
    try:
        with open(filename, "r", encoding="utf8") as file:
            csvreader = reader(file)
            count = 0
            for i, row in enumerate(csvreader):
                # Rank, EntryId, EntryName, TimeRemaining, Points, Lineup
                if i != 0:
                    # rank, entry_id, entry_name, _, points, lineup = row
                    rank, entry_id, entry_name, _, points, lineup = row[:6]
                    # lineup = lineup.split()
                    # for wordidx, word in enumerate(lineup[:]):
                    #     if word in STOP_WORDS:
                    #         lineup[wordidx] = "\t"
                    # word_list = " ".join(lineup).split("\t")
                    # players = []
                    # for word in " ".join(lineup).split("\t"):
                    #     if word.strip():
                    #         get_player_cached(word.strip(), player_cache)
                    # players = [
                    #     get_player_cached(word.strip(), player_cache)
                    #     for word in " ".join(lineup).split("\t")
                    #     if word.strip()
                    # ]
                    # if players:
                    if entry_name in vips:
                        DKResult.objects.update_or_create(
                            dk_id=entry_id,
                            defaults={
                                "contest": contest,
                                "name": parse_entry_name(entry_name),
                                "rank": rank,
                                "points": points,
                                # "pg": players[0],
                                # "sg": players[1],
                                # "sf": players[2],
                                # "pf": players[3],
                                # "c": players[4],
                                # "g": players[5],
                                # "f": players[6],
                                # "util": players[7],
                            },
                        )

                    # grab ownership stats for players
                    player_stats = row[7:]
                    if player_stats:
                        # continue if empty
                        # (sometimes happens on the player columns in the standings)
                        if all(s == "" or s.isspace() for s in player_stats):
                            continue

                        name, pos, ownership, fpts = player_stats

                        player = get_player_cached(name, player_cache)
                        ownership = float(ownership.strip("%")) / 100

                        DKResultOwnership.objects.update_or_create(
                            contest=contest,
                            player=player,
                            defaults={"ownership": ownership, "fpts": fpts},
                        )

                    if i % 5000 == 0:
                        logger.info("%d DKResult records created", i)
                count = i
            logger.info("%d DKResult records created", count)
    except IOError:
        logger.error("Couldn't find CSV results file %s", filename)


def run(sport, contest_ids, contest=True, resultscsv=True, resultsparse=True):
    """
    Downloads and unzips the CSV results and then populates the database
    """

    for contest_id in contest_ids:
        if contest:
            get_contest_data(contest_id)
            get_contest_prize_data(contest_id)
        if resultscsv:
            # get_contest_result_data returns false if empty
            if get_contest_result_data(contest_id) is False:
                continue
        if resultsparse:
            parse_contest_result_csv(sport, contest_id)
