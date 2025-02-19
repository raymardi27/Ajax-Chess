from django.db import models
from django.contrib.auth.models import User
import chess

# Create your models here.

class TheGame(models.Model):
    GAME_STATUS = [
        ('active','Active'),
        ('completed','Completed'),
        ('pending','Pending'),
    ]

    OUTCOMES = [
        ('white_win', 'White Wins'),
        ('black_win', 'Black Wins'),
        ('tie', 'Tie'),
        ('ongoing','Ongoing'),
    ]

    white_player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='white')
    black_player = models.ForeignKey(User, on_delete=models.CASCADE, related_name='black')

    fen = models.CharField(max_length=100, default='startpos')
    status = models.CharField(max_length=10, choices=GAME_STATUS, default='pending')
    moves = models.TextField(blank=True)
    move_count = models.PositiveIntegerField(default=0)
    outcome = models.CharField(max_length=10, choices=OUTCOMES, null=True, blank=True)
    winner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_games')
    loser = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='lost_games')

    black_journal = models.TextField(null=True, blank=True)
    white_journal = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_opponent(self, user):
        return self.black_player if self.white_player == user else self.white_player

    def get_opponent_username(self, user):
        opponent = self.get_opponent(user)
        return opponent.username if opponent else 'Unknown'
    
    def get_outcome_display(self, user):
        if user == self.winner:
            return 'WIN' 
        elif user == self.loser:
            return 'LOSS'
        else:
            return 'TIE'
    
    def get_outcome(self):
        return dict(self.OUTCOMES)[self.outcome]
    
    def set_outcome(self,outcome):
        if outcome not in dict(self.OUTCOMES):
            raise ValueError("Invalid Outcome Choice.")

        self.outcome = outcome

        if outcome == 'white_win':
            self.winner = self.white_player
            self.loser = self.black_player
        elif outcome == 'black_win':
            self.winner = self.black_player
            self.loser = self.white_player
        else:
            self.winner = None
            self.loser = None
        
        self.status = 'completed'
        self.save()



    def __str__(self):
        return f"Game {self.id} between {self.white_player.username} and {self.black_player.username} - Outcome: {dict(self.OUTCOMES)[self.outcome]}"

    
