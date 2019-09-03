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
            pos, name_and_pid, name, dk_id, rpos, salary, gameinfo, team_abbv, ppg = row
            # trim whitespace from name
            name = name.strip(" \t\n\r")
            # player = Player.get_by_name(name)
            # fetch or create Player
            player, _ = Player.objects.get_or_create(
                name=name,
                sport=sport,
                team_abbv=team_abbv,
                defaults={
                    "sport": sport,
                    "team_abbv": team_abbv,
                    "position": pos,
                    "dk_position": pos,
                },
            )

            dksalary, _ = DKSalary.objects.get_or_create(
                player=player,
                sport=sport,
                draft_group_id=draft_group_id,
                defaults={
                    "date": date,
                    "salary": int(salary),
                    "contest_type_id": contest_type_id,
                },
            )

            if player.dk_position != pos:
                player.dk_position = pos
                print(f"Updating {player.name} position {player.dk_position} to {pos}")
                player.save()

            if dksalary.salary != int(salary):
                print(
                    f"Warning: trying to overwrite salary "
                    f"(old: {dksalary.salary} dg: {dksalary.draft_group_id} "
                    f"new: {salary} dg: {draft_group_id}) for {player.name}. "
                    "Ignoring - did not overwrite "
                )
            return_rows.append(row)
    return return_rows


def get_salary_csv(sport, draft_group_id, contest_type_id, date):
    """
        Assume the salaries for each player in different draft groups are the
        same for any given day.
        """
    url = "https://www.draftkings.com/lineup/getavailableplayerscsv"
    response = requests.get(
        url,
        headers=HEADERS,
        cookies=COOKIES,
        params={"contestTypeId": contest_type_id, "draftGroupId": draft_group_id},
    )
    return write_salaries_to_db(
        response.text.splitlines(), sport, draft_group_id, contest_type_id, date
    )


def write_csv(rows, date, sport):
    header_row = [
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
    # outfile = CSVPATH / f"dk_{sport}_salaries_{draft_group_id}.csv"

    # Remove duplicate rows and sort by salary, then name
    # Lists are unhashable so convert each element to a tuple
    # rows = sorted(set([tuple(r) for r in rows]), key=lambda x: (-int(x[5]), x[2]))
    rows = sorted({tuple(r) for r in rows}, key=lambda x: (-int(x[5]), x[2]))
    print(f"Writing salaries to csv {outfile}")
    with open(outfile, "w", newline="\n") as file:
        csvwriter = csv.writer(file, delimiter=",", quotechar='"')
        csvwriter.writerow(header_row)
        for row in rows:
            csvwriter.writerow(row)


# def get_salary_date(draft_groups):
#     dates = [
#         datetime.datetime.strptime(dg["StartDateEst"].split("T")[0], "%Y-%m-%d").date()
#         for dg in draft_groups
#     ]
#     date_counts = [(d, dates.count(d)) for d in set(dates)]
#     # Get the date from the (date, count) tuple with the most counts
#     return sorted(date_counts, key=lambda x: x[1])[-1][0]


def get_salary_date(draft_group):
    return datetime.datetime.strptime(
        draft_group["StartDateEst"].split("T")[0], "%Y-%m-%d"
    ).date()


def matches_bad_criteria(sport, tag, suffix, draft_group_id, contest_type_id):
    accepted_contest_type_ids = {"NFL": [21]}  # 21 = normal NFL contest type
    regex = re.compile(r"[A-Z]{2,} vs [A-Z]{2,}")
    reason = ""
    if tag != "Featured":
        reason = "it's not featured"

    if suffix:
        if "Tiers" in suffix:
            reason = "'Tiers' in suffix"
        elif regex.search(suffix):
            reason = "matches 'vs' regex"

    if (
        sport in accepted_contest_type_ids
        and contest_type_id not in accepted_contest_type_ids[sport]
    ):
        reason = "unacceptable contest type id"

    if reason:
        print(
            f"Skipping (suffix: {suffix}) dg: {draft_group_id} "
            f"type: {contest_type_id} because {reason}"
        )
        return True
    return False


def run(sport, writecsv=True):
    """
    Downloads and unzips the CSV salaries and then populates the database
    """

    url = f"https://www.draftkings.com/lobby/getcontests?sport={sport}"
    response = requests.get(url, headers=HEADERS, cookies=COOKIES).json()
    rows_by_date = {}
    # rows_by_dg = {}
    for dg in response["DraftGroups"]:
        # dg['StartDateEst'] should be mostly the same for draft groups, (might
        # not be the same for the rare long-running contest) and should be the
        # date we're looking for (game date in US time).
        # date = get_salary_date(response["DraftGroups"])
        date = get_salary_date(dg)
        tag = dg["DraftGroupTag"]
        suffix = dg["ContestStartTimeSuffix"]
        draft_group_id = dg["DraftGroupId"]
        contest_type_id = dg["ContestTypeId"]
        # only care about featured draftgroups and exclude tiers
        if matches_bad_criteria(sport, tag, suffix, draft_group_id, contest_type_id):
            continue

        print(
            "Updating salaries for {} [{}]: draft group {} contest type {} [suffix: {}] ".format(
                sport, date, draft_group_id, contest_type_id, suffix
            )
        )
        row = get_salary_csv(sport, draft_group_id, contest_type_id, date)
        if date not in rows_by_date:
            rows_by_date[date] = []
        rows_by_date[date] += row
        # if draft_group_id not in rows_by_dg:
        #     rows_by_dg[draft_group_id] = []
        # rows_by_dg[draft_group_id] += row

    if writecsv:
        # for dg, rows in rows_by_dg.items():
        for date, rows in rows_by_date.items():
            write_csv(rows, date, sport)
