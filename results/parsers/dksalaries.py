import csv
import datetime
import re
from pathlib import Path

import browsercookie
import requests
from django.utils.timezone import make_aware

from results.models import DKSalary, Player

CSVPATH = Path("mysite/results/data/salaries/")
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




def write_salaries_to_db(
    input_rows, sport, draft_group_id, contest_type_id, date=datetime.date.today()
):
    return_rows = []
    csvreader = csv.reader(input_rows, delimiter=",", quotechar='"')
    # try:
    for i, row in enumerate(csvreader):
        if i != 0 and len(row) == 9:  # Ignore possible empty rows
            pos, name_and_pid, name, dk_id, rpos, salary, gameinfo, team, ppg = row
            # player = Player.get_by_name(name)
            # try to get the Player object
            try:
                # player = Player.objects.get(dk_id=dk_id)
                player = Player.objects.get(name=name)
            except Player.DoesNotExist:
                print(f"Player {name} does not exist. Creating!")
                player = Player.objects.create(name=name, sport=sport, dk_position=pos)

            dksalary, created = DKSalary.objects.get_or_create(
                player=player,
                date=date,
                defaults={
                    "sport": sport,
                    "draft_group": draft_group_id,
                    "salary": int(salary),
                },
            )
            if player.dk_position != pos:
                player.dk_position = pos
                print(f"Updating {player.name} position {player.dk_position} to {pos}")
                player.save()

            if dksalary.salary != int(salary):
                print(
                    f"Warning: trying to overwrite salary (old: {dksalary.salary} new: {salary}) for {player.name}. Ignoring - did not overwrite"
                )
            return_rows.append(row)
    return return_rows


def run(sport, writecsv=True):
    """
    Downloads and unzips the CSV salaries and then populates the database
    """

    def get_salary_date(draft_groups):
        dates = [
            datetime.datetime.strptime(
                dg["StartDateEst"].split("T")[0], "%Y-%m-%d"
            ).date()
            for dg in response["DraftGroups"]
        ]
        date_counts = [(d, dates.count(d)) for d in set(dates)]
        # Get the date from the (date, count) tuple with the most counts
        return sorted(date_counts, key=lambda x: x[1])[-1][0]

    def get_salary_csv(sport, draft_group_id, contest_type_id, date):
        """
        Assume the salaries for each player in different draft groups are the
        same for any given day.
        """
        URL = "https://www.draftkings.com/lineup/getavailableplayerscsv"
        response = requests.get(
            URL,
            headers=HEADERS,
            cookies=COOKIES,
            params={"contestTypeId": contest_type_id, "draftGroupId": draft_group_id},
        )
        return write_salaries_to_db(
            response.text.splitlines(), sport, draft_group_id, contest_type_id, date
        )

    def write_csv(rows, date):
        HEADER_ROW = [
            "Position",
            "NameId",
            "Name",
            "Id",
            "RosterPosition",
            "Salary",
            "GameInfo",
            "teamAbbrev",
            "AvgPointsPerGame",
        ]
        outfile = CSVPATH / f"dk_{sport}_salaries_{date:%Y_%m_%d}.csv"
        # Remove duplicate rows and sort by salary, then name
        # Lists are unhashable so convert each element to a tuple
        rows = sorted(set([tuple(r) for r in rows]), key=lambda x: (-int(x[5]), x[2]))
        print(f"Writing salaries to csv {outfile}")
        with open(outfile, "w", newline="\n") as f:
            csvwriter = csv.writer(f, delimiter=",", quotechar='"')
            csvwriter.writerow(HEADER_ROW)
            for row in rows:
                csvwriter.writerow(row)

    url = f"https://www.draftkings.com/lobby/getcontests?sport={sport}"
    response = requests.get(url, headers=HEADERS, cookies=COOKIES).json()
    rows_by_date = {}
    for dg in response["DraftGroups"]:
        # dg['StartDateEst'] should be mostly the same for draft groups, (might
        # not be the same for the rare long-running contest) and should be the
        # date we're looking for (game date in US time).
        date = get_salary_date(response["DraftGroups"])
        # only care about featured draftgroups
        if dg["DraftGroupTag"] != "Featured":
            print(
                "Skipping {} {} because it's not featured (suffix: {})".format(
                    dg["DraftGroupId"],
                    dg["ContestTypeId"],
                    dg["ContestStartTimeSuffix"],
                )
            )
            continue
        print(
            "Updating salaries for sport: {} draft group {}, contest type {}, date {}".format(
                sport, dg["DraftGroupId"], dg["ContestTypeId"], date
            )
        )
        row = get_salary_csv(sport, dg["DraftGroupId"], dg["ContestTypeId"], date)
        if date not in rows_by_date:
            rows_by_date[date] = []
        rows_by_date[date] += row

    if writecsv:
        for date, rows in rows_by_date.items():
            write_csv(rows, date)
