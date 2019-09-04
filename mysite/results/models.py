from django.db import models

# Create your models here.
# class Salary(models.Model):
#     pos = models.CharField(max_length=10)
#     roster_pos = models.CharField(max_length=10)
#     salary = models.IntegerField()
#     game_info = models.CharField(max_length=30)
#     team_abbv = models.CharField(max_length=20)
#     avg_ppg = models.DecimalField(max_digits=4, decimal_places=3)
#     players = models.ManyToManyField("Player")


class Player(models.Model):
    name = models.CharField(max_length=30)
    position = models.CharField(max_length=20, null=True, blank=True)
    dk_position = models.CharField(max_length=2, null=True, blank=True)
    sport = models.CharField(max_length=10, null=True, blank=True)
    team_abbv = models.CharField(max_length=20, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class DKSalary(models.Model):
    player = models.ForeignKey(
        Player, related_name="dk_salaries", on_delete=models.PROTECT
    )
    salary = models.PositiveIntegerField(null=True, blank=True)
    draft_group_id = models.PositiveIntegerField(null=True, blank=True)
    contest_type_id = models.PositiveIntegerField(null=True, blank=True)
    sport = models.CharField(max_length=10, null=True, blank=True)
    date = models.DateField(null=True, blank=True)

    class Meta:
        # unique_together = ("player", "date")
        unique_together = ("player", "draft_group_id")

    def __str__(self):
        return "DKSalary: player: {} salary: {} dg: {}".format(
            self.player, self.salary, self.draft_group_id
        )


class DKContest(models.Model):
    dk_id = models.CharField(max_length=15, unique=True)
    date = models.DateField(null=True, blank=True)
    datetime = models.DateTimeField(null=True, blank=True)
    sport = models.CharField(max_length=10, null=True, blank=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    total_prizes = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    entries = models.PositiveIntegerField(null=True, blank=True)
    entry_fee = models.FloatField(null=True, blank=True)
    positions_paid = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.date})"


class DKContestPayout(models.Model):
    contest = models.ForeignKey(
        DKContest, related_name="payouts", on_delete=models.PROTECT
    )
    upper_rank = models.PositiveIntegerField()
    lower_rank = models.PositiveIntegerField()
    payout = models.DecimalField(max_digits=18, decimal_places=2)

    class Meta:
        unique_together = ("contest", "upper_rank", "lower_rank")

    def __str__(self):
        return "{} ({} - {}: {})".format(
            self.contest, self.upper_rank, self.lower_rank, self.payout
        )


class DKResult(models.Model):
    contest = models.ForeignKey(
        DKContest, related_name="results", on_delete=models.PROTECT
    )
    dk_id = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=50)
    rank = models.PositiveIntegerField()
    points = models.FloatField()
    # pg = models.ForeignKey(
    #     Player, related_name="dk_pg_results", on_delete=models.PROTECT
    # )
    # sg = models.ForeignKey(
    #     Player, related_name="dk_sg_results", on_delete=models.PROTECT
    # )
    # sf = models.ForeignKey(
    #     Player, related_name="dk_sf_results", on_delete=models.PROTECT
    # )
    # pf = models.ForeignKey(
    #     Player, related_name="dk_pf_results", on_delete=models.PROTECT
    # )
    # c = models.ForeignKey(Player, related_name="dk_c_results", on_delete=models.PROTECT)
    # g = models.ForeignKey(Player, related_name="dk_g_results", on_delete=models.PROTECT)
    # f = models.ForeignKey(Player, related_name="dk_f_results", on_delete=models.PROTECT)
    # util = models.ForeignKey(
    #     Player, related_name="dk_util_results", on_delete=models.PROTECT
    # )

    # def get_lineup(self):
    #     return [self.pg, self.sg, self.sf, self.pf, self.c, self.g, self.f, self.util]

    # def get_lineup_dict(self):
    #     return {
    #         "PG": self.pg,
    #         "SG": self.sg,
    #         "SF": self.sf,
    #         "PF": self.pf,
    #         "C": self.c,
    #         "G": self.g,
    #         "F": self.f,
    #         "UTIL": self.util,
    #     }

    def __str__(self):
        return f"{self.contest} {self.rank}"
