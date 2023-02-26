import re
from django.db import models
from django_countries.fields import CountryField
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator


def num_races_validator(value: int):
    if value < 0 or value > 12:
        raise ValidationError(
            "cannot have less than 0 or more than 12 races",
            params={'value': value}
        )


class EventFormat(models.TextChoices):
    fFFA = ('FFA', 'ffa')
    f2v2 = ('2V2', '2v2')
    f3v3 = ('3V3', '3v3')
    f4v4 = ('4V4', '4v4')
    f6v6 = ('6V6', '6v6')


class PlayerDivision(models.TextChoices):
    IRON = ('IRON', 'iron')
    BRONZE = ('BRONZE', 'bronze')
    SILVER = ('SILVER', 'silver')
    GOLD = ('GOLD', 'gold')
    PLATINUM = ('PLATINUM', 'platinum')
    # more can be added later


class TournamentType(models.TextChoices):
    WAR = ('WAR', 'war')
    MOGI = ('MOGI', 'mogi')


# note: django automatically creates an id as a primary key, so we don't need to notate it here
class Tournament(models.Model):
    tournament_name = models.TextField(unique=True, null=False)
    tournament_date = models.DateTimeField()
    tournament_type = models.TextField(choices=TournamentType.choices, default=TournamentType.MOGI)


class Team(models.Model):
    team_name = models.TextField(unique=True)
    team_tag = models.TextField(unique=True)
    division = models.IntegerField(validators=[MinValueValidator(1, "division cannot be less than 1")])


class TeamStats(models.Model):
    team = models.ForeignKey(Team, primary_key=True, on_delete=models.CASCADE)
    base_mmr = models.IntegerField(default=0)
    current_mmr = models.IntegerField(default=0)
    peak_mmr = models.IntegerField(default=0)
    lowest_mmr = models.IntegerField(default=0)
    max_gain_mmr = models.IntegerField(default=0)
    max_loss_mmr = models.IntegerField(default=0)
    diff_last_ten_mmr = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    top_score = models.IntegerField(default=0)
    total_matches = models.IntegerField(default=0)


class Match(models.Model):
    team_one = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='team_one')
    team_two = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='team_two')
    match_date = models.DateTimeField()
    match_table_image = models.URLField()
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)

    def clean(self):
        if self.team_one == self.team_two:
            raise ValidationError(
                'a team cannot war itself outside of inclans',
                params={
                    'team_one': self.team_one,
                    'team_two': self.team_two,
                }
            )


class MatchTeamData(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    win = models.BooleanField()
    team_score = models.IntegerField()
    penalty = models.IntegerField()
    race_amount = models.IntegerField()


def fc_validator(value: str):
    if re.fullmatch(r'^[0-9]{4}-[0-9]{4}-[0-9]{4}$', value) is None:
        raise ValidationError(
            f"{value} is not a valid friend code",
            params={'value': value}
        )


# TODO: this will need to be integrated with django's authentication system later
class Player(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    discord = models.IntegerField(unique=True, null=False)
    player_name = models.TextField(unique=True, null=False)
    country = CountryField(null=False)
    division = models.TextField(choices=PlayerDivision.choices, default=PlayerDivision.IRON)
    strikes = models.IntegerField(default=0)
    name_change_date = models.DateTimeField()
    friend_code = models.TextField(validators=[fc_validator])


class MatchPlayerData(models.Model):
    player = models.ForeignKey(Player, null=False, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, null=False, on_delete=models.CASCADE)
    player_score = models.IntegerField(null=False)
    races_played = models.IntegerField(null=False, validators=[num_races_validator])
    subbed_in = models.IntegerField(null=False, validators=[num_races_validator])
    subbed_out = models.IntegerField(null=False, validators=[num_races_validator])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['player', 'match'], name='unique_match_player')
        ]


class WarTournamentWinners(models.Model):
    tournament = models.ForeignKey(Tournament, primary_key=True, on_delete=models.CASCADE)
    final_match = models.ForeignKey(Match, null=False, on_delete=models.CASCADE)


class Event(models.Model):
    event_format = models.TextField(choices=EventFormat.choices, default=EventFormat.f2v2)
    event_race_amount = models.IntegerField(null=False, validators=[num_races_validator])
    event_date = models.DateTimeField()
    event_table_image = models.URLField()
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    tier = models.IntegerField()
    subs = models.IntegerField()


class MogiTournamentWinners(models.Model):
    tournament = models.ForeignKey(Tournament, primary_key=True, on_delete=models.CASCADE)
    final_event = models.ForeignKey(Event, on_delete=models.CASCADE)


class EventPlayerData(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    team = models.TextField(null=False)
    ranking = models.IntegerField(null=True)
    multiplier = models.FloatField()
    score = models.IntegerField()
    races_played = models.IntegerField(validators=[num_races_validator])
    subbed_in = models.IntegerField(validators=[num_races_validator])
    subbed_out = models.IntegerField(validators=[num_races_validator])
    before_event_mmr = models.PositiveIntegerField()
    after_event_mmr = models.PositiveIntegerField()
    before_division = models.TextField(choices=PlayerDivision.choices)
    after_division = models.TextField(choices=PlayerDivision.choices)
    win = models.BooleanField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['event', 'player'], name='unique_event_player')
        ]


class EventPlayerStats(models.Model):
    player = models.ForeignKey(Player, primary_key=True, on_delete=models.CASCADE)
    base_mmr = models.IntegerField(default=0)
    current_mmr = models.IntegerField(default=0)
    peak_mmr = models.IntegerField(default=0)
    lowest_mmr = models.IntegerField(default=0)
    max_gain_mmr = models.IntegerField(default=0)
    max_loss_mmr = models.IntegerField(default=0)
    diff_last_ten_mmr = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    top_score = models.IntegerField(default=0)
    total_events = models.IntegerField(default=0)


class ApiKeys(models.Model):
    player = models.ForeignKey(Player, primary_key=True, on_delete=models.CASCADE)
    api_key = models.TextField(unique=True, null=False)


# TODO: this will need to be integrated into django's own permission system later
class Permissions(models.Model):
    permission_name = models.TextField(unique=True, null=False)
    permission_value = models.IntegerField(unique=True, null=False)


class PlayerPermissions(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    permission = models.ForeignKey(Permissions, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['player', 'permission'], name='unique_player_permission')
        ]



