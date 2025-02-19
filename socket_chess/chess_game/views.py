from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate as dj_auth, login as dj_login, logout as dj_logout
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.db.models import Q
from django.utils import timezone
from django.template.loader import render_to_string

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
# import random
import chess

from .forms import JoinForm, LoginForm, JournalForm
from .models import TheGame
from .common import utils

# Create your views here.
def default(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    return render(request,'default.html')

def about(request):
    return render(request,'info/aboutme.html')

def rules(request):
    return render(request,"info/rules.html")

def history(request):
    return render(request,"info/history.html")

def join(request):
    if(request.method == "POST"):
        form = JoinForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.set_password(user.password)
            user.save()
            return redirect('login')
    
    else:
        form = JoinForm()
    return render(request, 'user/join.html', {'form': form})

# @require_http_methods(["POST"])
def login(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = dj_auth(request, username=username, password=password)

            if user is not None:
                dj_login(request, user)
                return redirect('home')
            else:
                messages.error(request,"Incorrect Credentials Entered. Try Again")
                return redirect('login')
    else:
        form = LoginForm()
    return render(request, 'user/login.html', {'form': form})

def logout(request):
    user = request.user
    dj_logout(request)

    sessions = Session.objects.filter(expire_date__gte=timezone.now())

    for session in sessions:
        session_data = session.get_decoded()
        if str(user.id) == session_data.get('_auth_user_id'):
            session.delete()

    return redirect('login')

@login_required(login_url='login')
def home(request):
    user = request.user

    # Check for ongoing game
    active_game = TheGame.objects.filter(
        (Q(white_player=user) | Q(black_player=user)) & Q(status='active')
    ).first()
    if active_game:
        return redirect('game', game_id=active_game.id)
    else:
        pending_invites_sent = TheGame.objects.filter(
            white_player=user,
            status='pending'
        )

        if request.method == 'POST':

            if pending_invites_sent.exists():
                messages.error(request, "You already have a pending game invitation challenge. You cannot start a new game.")
                return redirect('home')

            opponent_id = request.POST.get('opponent_id')
            opponent = User.objects.get(id=opponent_id)

            user_active_game = TheGame.objects.filter(
                (Q(white_player=user) | Q(black_player=user)) & Q(status='active')
            ).exists()

            opponent_active_game = TheGame.objects.filter(
                (Q(white_player=opponent) | Q(black_player=opponent)) & Q(status='active')
            ).exists()

            if user_active_game:
                messages.error(request, "You have an ongoing game currently! Finish that first.")
                return redirect('home')
        
            elif opponent_active_game:
                messages.error(request, "The Opponent is busy playing another game. They're the next Magnus Carlsen")
                return redirect('home')
            else: 
                # white = random.choice([user, opponent]),
                # black = opponent if white == user else user
                game = TheGame.objects.create(
                    white_player=user,
                    black_player=opponent,
                    fen=chess.STARTING_FEN,
                    status='pending'                   
                )
                messages.success(request, f"Game Invite sent to {opponent.username}")
                return redirect('home')

        active_users = utils.get_loggedIn_Users()
        available_users =[]
        for u in active_users:
            opponent_active_game = TheGame.objects.filter(
                (Q(white_player=u) | Q(black_player=u)) & Q(status='active')
            ).exists()
            if not opponent_active_game:
                available_users.append({
                'id': u.id,
                'username':u.username
            })
        
        invited_users = pending_invites_sent.values_list('black_player_id', flat=True)
        available_users = [user for user in available_users if user['id'] not in invited_users]
        available_users = list(filter(lambda user: not (user['id'] == request.user.id or user['username'] == request.user.username),available_users))

        
        games = TheGame.objects.filter(
            (Q(white_player=user) | Q(black_player=user)) & Q(status='completed')
        ).order_by('-id')
        pending_game = pending_invites_sent.first() if pending_invites_sent.exists() else None

        
        return render(request, 'game/home.html', {
            'username': user.username, 
            'games': games,
            'has_pending_invite': pending_game is not None,
            'pending_game_id': pending_game.id if pending_game else None,
            'available_users' : available_users,
        })

@login_required
def newGame(request):
    if request.method == "POST":
        opponent_id = request.POST.get('opponent_id')
        opponent = User.objects.get(id=opponent_id)
        game = TheGame.objects.create(white_player=request.user, black_player=opponent, fen='startpos')
        return redirect('game', game_id = game.id)
    users = User.objects.exclude(id=request.user.id)
    return render(request, 'new_game.html',{'users': users})

# @login_required
# def gameHistory(request):
#     # Fetch all games played by the user
#     games = TheGame.objects.filter(white_player=request.user) | TheGame.objects.filter(black_player=request.user)
#     return render(request, 'game/game_history.html', {'games': games})

@login_required
def game_detail(request,game_id):
    game = get_object_or_404(TheGame, id=game_id)

    if request.user not in [game.white_player, game.black_player]:
        messages.error(request, "You are not allowed to do this. Bruh Moment")
        return redirect('game/home')
    
    journal = game.white_journal if request.user == game.white_player else game.black_journal

    return render(request, 'game/game_details.html', {
        'game':game,
        'journal':journal,
    })

@login_required
def get_available_users(request):
    active_users = utils.get_loggedIn_Users()
    available_users =[]
    for u in active_users:
        opponent_active_game = TheGame.objects.filter(
            (Q(white_player=u) | Q(black_player=u)) & Q(status='active')
        ).exists()
        if not opponent_active_game:
            available_users.append({
                'id': u.id,
                'username':u.username
            })
    available_users = list(filter(lambda user: not (user['id'] == request.user.id or user['username'] == request.user.username),available_users))
    
    
    return JsonResponse({"available_users":available_users})
    
@login_required
def get_pending_invitations(request):
    pending_games = TheGame.objects.filter(black_player=request.user,status='pending').values('id','white_player__username')
    print("These are pending games: ",pending_games)
    invitations = list(pending_games)
    return JsonResponse({'invitations': invitations})

@login_required
def get_sent_invitations(request):
    # Get pending invitations sent by the current user
    pending_invitations = TheGame.objects.filter(
        white_player=request.user,
        status='pending'
    ).values('id', 'black_player__username')

    # Get games that have been accepted
    accepted_games = TheGame.objects.filter(
        white_player=request.user,
        status='active'
    ).values('id', 'black_player__username')

    # Get declined invitations
    declined_invitations = TheGame.objects.filter(
        white_player=request.user,
        status='declined'
    ).values('id', 'black_player__username')

    # Delete declined invitations
    TheGame.objects.filter(
        white_player=request.user,
        status='declined'
    ).delete()

    return JsonResponse({
        'invitations': list(pending_invitations),
        'accepted_games': list(accepted_games),
        'declined_invitations': list(declined_invitations)
    })

@login_required
def revoke_invitation(request,game_id):
    game = get_object_or_404(TheGame, id=game_id, white_player=request.user, status='pending')

    if request.method == 'GET':
        game.delete()
        messages.success(request, "Game Invitation revoked successfully")
        return redirect('home')
    else:
        messages.error(request,"Invalid Request method")
        return redirect('home')

@login_required
def respond_invitation(request, game_id):
    game = get_object_or_404(TheGame, id=game_id, black_player=request.user, status='pending')
    if request.method == 'POST':
        response = request.POST.get('response')
        if response == 'accept':
            # Check for active game
            active_game = TheGame.objects.filter(
                (Q(white_player=request.user) | Q(black_player=request.user)) & Q(status='active')
            ).exists()
            if active_game:
                messages.error(request, 'You cannnot accept a new game while you have a game ongoing')
                return redirect('home')
            game.status = 'active'
            game.save()
            messages.success(request, "Successfully accepted. The game will begin")
            return redirect('game', game_id=game.id)
        elif response =='decline':
            game.status = 'declined'
            game.save()
            messages.success(request,' Successfully Declined. ')
            return redirect('home')
    
    return redirect('home')

@login_required
def game(request, game_id):
    game = get_object_or_404(TheGame, id=game_id)
    if request.user != game.white_player and request.user != game.black_player:
        messages.error(request, "You aren't a player in this game. Don't be naughty you hacka")
        return redirect('home')
    
    # board = chess.Board(game.fen)
    # is_white_turn = board.turn
    # user_is_white = (game.white_player == request.user)
    # user_turn = (is_white_turn and user_is_white) or (not is_white_turn and not user_is_white)

    # # **Game Over Detection Logic**
    # if board.is_game_over():
    #     result = board.result()
    #     if result == '1-0':
    #         game.set_outcome('white_win')
    #     elif result == '0-1':
    #         game.set_outcome('black_win')
    #     else:
    #         game.set_outcome('tie')
    #     messages.info(request, f"Game Over: {game.get_outcome()}")

    context = {
        'game': game,
        'username': request.user.username,
        # 'board': utils.fen_to_dict(game.fen),
        # 'turn': 'White' if is_white_turn else 'Black',
        # 'user_turn': user_turn
    }

    return render(request,'game/chessboard.html',context)

@login_required
def makeMove(request, game_id):
    game = get_object_or_404(TheGame, id=game_id)
    board = chess.Board(game.fen)
    is_white_turn = board.turn
    user_is_white = (game.white_player == request.user)
    user_turn = (is_white_turn and user_is_white) or (not is_white_turn and not user_is_white)
    
    if not user_turn:
        messages.error(request,'It is not your turn')
        return redirect('game', game_id=game.id)
    
    move = request.POST.get('move')
    if not move:
        messages.error(request, "No move provided")
        return redirect('game',game_id=game.id)
    
    if len(move) != 4:
        messages.error(request, 'Invalid move format. Move should be in the format "e2e4".')
        return redirect('game', game_id=game.id)
    try:
        move_obj = chess.Move.from_uci(move)
        if move_obj in board.legal_moves:
            san_move = board.san(move_obj)
            board.push(move_obj)
            game.fen = board.fen()
            game.move_count += 1
            game.moves += ' ' + move if game.moves else move

            # **Game Over Detection Logic**
            # if board.is_game_over():
            #     result = board.result()
            #     if result == '1-0':
            #         game.set_outcome('white_win')
            #     elif result == '0-1':
            #         game.set_outcome('black_win')
            #     else:
            #         game.set_outcome('tie')
            #     messages.info(request, f"Game Over: {game.get_outcome()}")
            game.save()
        else:
            messages.error(request, 'Invalid Move')
    except ValueError:
        messages.error(request,'Invalid move format')
    except AssertionError as e:
        # Handle unexpected assertion errors gracefully
        messages.error(request, f'An error occurred: {str(e)}')
    return redirect('game', game_id=game.id)

@login_required
def resign_game(request, game_id):
    game = get_object_or_404(TheGame, id=game_id)
    if request.method == 'POST':

        board = chess.Board(game.fen)
        if game.white_player == request.user:
            game.set_outcome('black_win')
        else:
            game.set_outcome('white_win')
            
        messages.info(request, 'You have resigned from the game. You Coward')
        return redirect('home')

@login_required
def check_game_status(request, game_id):
    game = get_object_or_404(TheGame, id=game_id)
    board_html = render_to_string('game/chessboard_partial.html',{'board':utils.fen_to_dict(game.fen)})

    is_white_turn = chess.Board(game.fen).turn
    turn = 'White' if is_white_turn else 'Black'

    user_is_white = (game.white_player == request.user)
    user_turn = (is_white_turn and user_is_white) or not (is_white_turn or user_is_white)
    return JsonResponse({
        'fen': game.fen,
        'board_html': board_html,
        'turn': turn,
        'status': game.status,
        'outcome': game.outcome if game.status == 'completed' else None,
        'winner' : game.white_player.username if (game.status == 'completed' and game.winner == game.white_player) else game.black_player.username,
        'move_history':game.moves,
        'user_turn': user_turn
    })

@login_required
def edit_game(request,game_id):
    game = get_object_or_404(TheGame, id=game_id)

    if request.user != game.white_player and request.user != game.black_player:
        messages.error(request, "You are not allowed to do this. Bruh Moment")
        return redirect('game/home')

    if game.status != 'completed':
        messages.error(request, "You can only edit completed games.")
        return redirect('game/home')
    
    journal_field = 'white_journal' if request.user == game.white_player else 'black_journal'
    
    if request.method == "POST":
        form = JournalForm(request.POST, instance=game, prefix=journal_field)
        if form.is_valid():
            setattr(game,journal_field,form.cleaned_data['journal'])
            game.save()
            messages.success(request, "Journal entry saved successfully")
            return redirect('home')
    else:
        initial = {'journal': getattr(game,journal_field)}
        form = JournalForm(initial=initial,prefix=journal_field)
    
    return render(request, 'game/edit_game.html', {
        'form':form,
        'game':game,
        'journal_field':journal_field,
    })

# @login_required
# def delete_journal(request,game_id):
#     game = get_object_or_404(TheGame, id=game_id)

#     # Determine which journal belongs to the user
#     if request.user == game.white_player:
#         journal_field = 'white_journal'
#     elif request.user == game.black_player:
#         journal_field = 'black_journal'
#     else:
#         messages.error(request, "You are not a player in this game.")
#         return redirect('game/home')

#     if request.method == 'POST':
#         setattr(game, journal_field, '')
#         game.save()
#         messages.success(request, "Journal entry deleted successfully.")
#         return redirect('gameHistory')  # Redirect to Game History page
#     else:
#         messages.error(request, "Invalid request method.")
#         return redirect('gameHistory')


@login_required
def delete_game(request,game_id):

    try:
        game = get_object_or_404(TheGame, id=game_id)

    except Http404:
        messages.info(request, "Game Does not Exist")
        return redirect('home')


    if request.user != game.white_player and request.user != game.black_player:
        messages.error(request, "You are not a part of this. Mind your own business")
        return redirect('home')

    if request.method =='POST':
        opponent = game.white_player if game.black_player == request.user else game.black_player
        game.delete()

        # Send a message to the opponent
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{opponent.username}',
            {
                'type': 'game_deleted',
                'game_id': game_id,
                'message': f'Game {game_id} has been deleted by {request.user.username}',
            }
        )

        messages.success(request, "Game deleted Successfully")
        return redirect('home')

    else:
        messages.error(request, 'Invalid request')
        return redirect('home')

