import chess
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from django.utils import timezone

def fen_to_dict(fen):
    board = chess.Board(fen)
    board_dict = {}
    unicode_pieces = {
        'P': '&#9817;', 'N': '&#9816;', 
        'B': '&#9815;', 'R': '&#9814;',
        'Q': '&#9813;', 'K': '&#9812;',
        'p': '&#9823;', 'n': '&#9822;', 
        'b': '&#9821;', 'r': '&#9820;',
        'q': '&#9819;', 'k': '&#9818;',
    }
    for square in chess.SQUARES:
        coord = chess.square_name(square)
        piece = board.piece_at(square)
        if piece:
            board_dict[coord] = unicode_pieces[piece.symbol()]
        else:
            board_dict[coord] = '&nbsp;'
    
    return board_dict

def get_loggedIn_Users():
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    userIds = []

    for session in sessions:
        data = session.get_decoded()
        user_id = data.get('_auth_user_id')
        if user_id:
            userIds.append(user_id)

    userIds = set(userIds)
    
    users = User.objects.filter(id__in=userIds)

    return users


