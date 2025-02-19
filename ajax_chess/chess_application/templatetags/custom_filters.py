from django import template

register = template.Library()

@register.filter
def get_opponent_username(game,param):
    return game.get_opponent_username(param)

@register.filter
def get_outcome_display(game,param):
    return game.get_outcome_display(param)

@register.simple_tag
def get_board_cell(board,col,row):
    key = f"{col}{row}"
    return board.get(key, '')