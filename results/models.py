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
    draft_group = models.PositiveIntegerField(null=True, blank=True)
    sport = models.CharField(max_length=10, null=True, blank=True)
    date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ("player", "date")


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
        return "{{}} ({} - {}: {})".format(
            self.contest, self.upper_rank, self.lower_rank, self.payout
        )
