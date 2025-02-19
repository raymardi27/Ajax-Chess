import json
import chess
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from asgiref.sync import sync_to_async
from .common import utils
from .models import TheGame
from django.db.models import Q

class LobbyConsumer(AsyncWebsocketConsumer):
    online_users = set()

    @database_sync_to_async
    def get_game_with_players(self, game_id):
        return TheGame.objects.select_related('white_player','black_player').get(id=game_id)
    
    @database_sync_to_async
    def create_game(self, white_player, black_player, fen, status):
        return TheGame.objects.create(
            white_player=white_player,
            black_player=black_player,
            fen=fen,
            status=status
        )
    
    @database_sync_to_async
    def save_game(self, game):
        game.save()
    
    @database_sync_to_async
    def delete_game(self,game):
        game.delete()

    @database_sync_to_async
    def get_received_invitations(self):
        return list(TheGame.objects.filter(
            black_player__username=self.username,
            status='pending'
        ).values('id', 'white_player__username'))
    
    @database_sync_to_async
    def get_sent_invitations(self):
        return list(TheGame.objects.filter(
            white_player__username=self.username,
            status='pending'
        ).values('id', 'black_player__username'))
    

    async def connect(self):
        self.username = self.scope['user'].username
        self.user_id = self.scope['user'].id
        self.group_name = 'lobby'

        # Add user to online users set
        LobbyConsumer.online_users.add(self.username)

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # Add user to their own pesonal group
        self.user_group_name = f'user_{self.username}'

        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        await self.accept()

        # Send the list of online users to the connecting client
        await self.send(text_data=json.dumps({
            'event': 'online_users',
            'usernames': list(LobbyConsumer.online_users),
        }))

        # Send pending invitations
        received_invitations = await self.get_received_invitations()
        await self.send(text_data=json.dumps({
            'event': 'received_invitations',
            'invitations': received_invitations,
        }))

        # Send sent invites
        sent_invitations = await self.get_sent_invitations()
        await self.send(text_data=json.dumps({
            'event': 'sent_invitations',
            'invitations': sent_invitations,
        }))

        # Notify others that a new user has joined
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'user_join',
                'username': self.username,
            }
        )


    async def disconnect(self, close_code):
        # Remove user from online users set
        LobbyConsumer.online_users.discard(self.username)

        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )

        # Notify others that a user has left
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'user_leave',
                'username': self.username,
            }
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'send_invitation':
            opponent_username = data.get('opponent_username')
            await self.send_invitation(opponent_username)
        elif action == 'respond_invitation':
            game_id = data.get('game_id')
            response = data.get('response')
            await self.respond_invitation(game_id, response)
        elif action == 'revoke_invitation':
            opponent_username = data.get('opponent_username')
            await self.revoke_invitation(opponent_username)

    async def send_invitation(self, opponent_username):
        # Create a new game invitation
        opponent = await sync_to_async(User.objects.get)(username=opponent_username)
        game = await self.create_game(
            white_player=self.scope['user'],
            black_player=opponent,
            fen=chess.STARTING_FEN,
            status='pending'
        )

        # Send invitation to the opponent if they're online
        if opponent_username in LobbyConsumer.online_users:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'receive_invitation',
                    'from_username': self.username,
                    'to_username': opponent_username,
                    'game_id': game.id,
                }
            )
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type':'sent_invitation',
                    'to_username': opponent_username,
                    'game_id': game.id,
                }
            )

        else:
            # Handle offline opponent (optional)
            await self.send(text_data=json.dumps({
                'event': 'invitation_sent',
                'message': f'Invitation sent to {opponent_username}, but they may be offline',
            }))
    
    async def sent_invitation(self, event):
        if event['to_username'] == self.username:
            await self.send(text_data=json.dumps({
                'event': 'sent_invitation',
                'to_username': event['to_username'],
                'game_id': event['game_id']
            }))
    
    async def respond_invitation(self, game_id, response):
        try:
            game = await self.get_game_with_players(game_id)
            if response == 'accept':
                game.status = 'active'
                await self.save_game(game)

                # Notify both players that the game has started
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'invitation_accepted',
                        'game_id': game_id,
                        'from_username': game.white_player.username,
                        'to_username': game.black_player.username,
                    }
                )
            elif response == 'decline':
                # Notify the sender that the invitation was declined
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'invitation_declined',
                        'game_id': game_id,
                        'from_username': game.white_player.username,
                        'to_username': game.black_player.username,
                    }
                )

                await self.delete_game(game)
            else:
                await self.send(text_data=json.dumps({
                    'event': 'error',
                    'message': 'Invalid response to invitation',
                }))
        except TheGame.DoesNotExist:
            await self.send(text_data=json.dumps({
                'event': 'error',
                'message': 'Game not Found',
            }))
        
        except Exception as e:
            await self.send(text_data=json.dumps({
                'event': 'error',
                'message': str(e),
            }))

    async def revoke_invitation(self,opponent_username):
        try:
            game = await sync_to_async(TheGame.objects.select_related('white_player','black_player').get)(
                white_player=self.scope['user'],
                black_player__username=opponent_username,
                status='pending'
            )

            await self.delete_game(game)

            if opponent_username in LobbyConsumer.online_users:
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'invitation_revoked',
                        'from_username':self.username,
                        'to_username': opponent_username,
                        'game_id': game.id,
                    }
                )

        except TheGame.DoesNotExist:
            await self.send(text_data=json.dumps({
                'event': 'error',
                'message': f"No pending invitations for {opponent_username}.",
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'event': 'error',
                'message': str(e)
            }))

    async def invitation_revoked(self, event):
        if event['to_username'] in[event['from_username'], event['to_username']]:
            await self.send(text_data=json.dumps({
                'event': 'invitation_revoked',
                'from_username': event['from_username'],
                'to_username': event['to_username'],
                'game_id': event['game_id'],
            }))

    async def user_join(self, event):
        username = event['username']
        if username != self.username:
            await self.send(text_data=json.dumps({
                'event': 'user_join',
                'username': username
            }))

    async def user_leave(self, event):
        username = event['username']
        await self.send(text_data=json.dumps({
            'event': 'user_leave',
            'username': username,
        }))

    async def receive_invitation(self, event):
        # Check if the invitation is for this user
        if event['to_username'] == self.username:
            await self.send(text_data=json.dumps({
                'event': 'receive_invitation',
                'from_username': event['from_username'],
                'game_id': event['game_id'],
            }))

    async def invitation_accepted(self, event):
        if self.username in [event['from_username'], event['to_username']]:
            await self.send(text_data=json.dumps({
                'event': 'invitation_accepted',
                'game_id': event['game_id'],
                'from_username': event['from_username'],
                'to_username': event['to_username'],
            }))

    async def invitation_declined(self, event):
        if self.username == event['from_username']:
            await self.send(text_data=json.dumps({
                'event': 'invitation_declined',
                'game_id': event['game_id'],
                'from_username': event['from_username'],
                'to_username': event['to_username'],
            }))

    async def game_deleted(self, event):
        await self.send(text_data=json.dumps({
            'event': 'game_deleted',
            'game_id': event['game_id'],
            'message': event['message'],
        }))

class GameConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        self.game_id = self.scope['url_route']['kwargs']['game_id']
        self.group_name = f'game_{self.game_id}'
        self.username = self.scope['user'].username

        # Make sure the user is a part of the game
        game = await self.get_game()
        if not game:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Render initial board
        board_html = await self.render_board_html(game.fen)

        is_user_turn = await self.is_user_turn(game) 

        opponent_username = game.black_player.username if self.username == game.white_player.username else game.white_player.username
        current_turn_username = game.white_player.username if chess.Board(game.fen).turn else game.black_player.username

        # Send current game state to user
        await self.send(text_data=json.dumps({
            'event':'game_state',
            'fen': game.fen,
            'opponent_username': opponent_username,
            'current_turn': current_turn_username,
            'move_history':game.moves,
            'status' : game.status,
            'outcome': game.outcome,
            'board_html': board_html,
            'user_turn': is_user_turn,
        }))
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        move = data.get('move')
        resign = data.get('resign')

        if move:
            result = await self.process_move(move)
            if result['status'] == 'success':
                game = result['game']
                game_over = result['game_over']
                outcome = result.get('outcome')
                next_player_username = result.get('next_player_username')
                move_history = result.get('move_history')
                board_html = await self.render_board_html(game.fen)
                # is_user_turn = await self.is_user_turn(game) 

                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'game_move',
                        'move' : move,
                        'username' : self.username,
                        'fen' : game.fen,
                        'board_html': board_html,
                        'game_over': game_over,
                        'outcome' : outcome,
                        'next_player_username': next_player_username,
                        'move_history' : move_history,
                    }
                )
            else:
                await self.send(text_data=json.dumps({
                    'event': 'error',
                    'message': result['message'],
                }))
        elif resign: 
            game = await self.process_resignation()

            board_html = await self.render_board_html(game.fen)

            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'game_over',
                    'message': f'{self.username} has resigned',
                    'outcome' : game.outcome,
                    'board_html' : board_html,
                    'user_turn' : False,
                }
            )
    
    async def game_move(self, event):
        is_user_turn = event['next_player_username'] == self.username

        await self.send(text_data=json.dumps({
            'event': 'move',
            'move': event['move'],
            'username': event['username'],
            'fen': event['fen'],
            'board_html': event['board_html'],
            'game_over': event['game_over'],
            'outcome': event.get('outcome'),
            'user_turn': is_user_turn,
            'move_history': event.get('move_history',''),
        }))

    async def game_over(self, event) :
        await self.send(text_data=json.dumps({
            'event' : 'game_over',
            'message': event['message'],
            'outcome': event['outcome'],
            'board_html': event['board_html'],
            'user_turn': event['user_turn'],
        }))
    
    @database_sync_to_async
    def get_game(self):
        try:
            game = TheGame.objects.get(id=self.game_id)
            if self.scope['user'] not in [game.white_player, game.black_player]:
                return None
            return game
        except TheGame.DoesNotExist:
            return None
    
    
    async def process_move(self,move) :
        try:
            game = await sync_to_async(TheGame.objects.select_related('white_player', 'black_player').get)(id=self.game_id) 
            board = chess.Board(game.fen)
            move_obj = chess.Move.from_uci(move)
            if move_obj in board.legal_moves:
                is_white_turn = board.turn
                user_is_white = game.white_player == self.scope['user']
                user_turn = (is_white_turn and user_is_white) or not (is_white_turn or user_is_white)
                if not user_turn:
                    return {
                        'status': 'error',
                        'message' : 'It is not your turn.'
                    }

                board.push(move_obj)
                game.fen = board.fen()
                game.move_count += 1
                game.moves += ' ' + move if game.moves else move

                game_over = board.is_game_over()
                next_player_username = game.white_player.username if board.turn else game.black_player.username
                opponent_username = game.black_player.username if self.username == game.white_player.username else game.white_player.username
                
                if game_over:
                    result = board.result()
                    if result == '1-0':
                        await sync_to_async(game.set_outcome)('white_win')
                    elif result == '0-1':
                        await sync_to_async(game.set_outcome)('black_win')
                    else:
                        await sync_to_async(game.set_outcome)('tie')
                    
                    game.status = 'completed'
                    await sync_to_async(game.save)()
                    return {
                        'status' : 'success',
                        'game' : game,
                        'game_over' : True,
                        'outcome' : game.outcome,
                        'move_history': game.moves,
                        'next_player_username': next_player_username,
                        'current_turn': next_player_username,
                        'opponent_username': opponent_username,
                        
                    }
                else: 
                    await sync_to_async(game.save)()
                    return {
                        'status' : 'success',
                        'game': game,
                        'game_over' : False,
                        'move_history': game.moves,
                        'next_player_username': next_player_username,
                        'current_turn': next_player_username,
                        'opponent_username': opponent_username,
                    }
            
            else: 
                return {
                    'status' : 'error',
                    'message' : 'Invalid Move'
                }

        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }


    async def process_resignation(self):
        game = await sync_to_async(TheGame.objects.select_related('white_player', 'black_player').get)(id=self.game_id)
        if self.scope['user'] == game.white_player:
            await sync_to_async(game.set_outcome)('black_win')
        else:
            await sync_to_async(game.set_outcome)('white_win')
        
        game.status = 'completed'
        await sync_to_async(game.save)()
        return game
    
    async def render_board_html(self,fen):
        board_dict = await sync_to_async(utils.fen_to_dict)(fen)
        board_html = await sync_to_async(render_to_string)('game/chessboard_partial.html', {'board': board_dict})
        return board_html


    @database_sync_to_async
    def is_user_turn(self, game):
        board = chess.Board(game.fen)
        is_white_turn = board.turn
        user_is_white = (game.white_player == self.scope['user'])
        user_turn = (is_white_turn and user_is_white or (not is_white_turn and not user_is_white))
        return user_turn
    
