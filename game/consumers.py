import json
import random
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Game, Player, Hint, Vote


class GameConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auto_delete_task = None
    
    async def connect(self):
        self.game_code = self.scope['url_route']['kwargs']['game_code']
        self.room_group_name = f'game_{self.game_code}'
        
        # Verificar se o jogo existe
        game = await self.get_game()
        if not game:
            await self.close()
            return
        
        # Verificar autenticação via sessão
        authenticated_player_name = await self.get_authenticated_player_name()
        
        # Permitir conexão mesmo sem autenticação (modo espectador)
        # Se não houver autenticação, será tratado como espectador
        if authenticated_player_name:
            # Verificar se o jogador existe no jogo
            player = await self.get_player(game, authenticated_player_name)
            if player:
                # Armazenar player_name autenticado
                self.authenticated_player_name = authenticated_player_name
            else:
                # Jogador não existe, tratar como espectador
                self.authenticated_player_name = None
        else:
            # Sem autenticação, modo espectador
            self.authenticated_player_name = None
        
        # Entrar no grupo (jogadores e espectadores)
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Enviar estado atual do jogo
        await self.send_game_state()
        
        # Verificar se o jogo acabou e iniciar timer se necessário
        if game.status == 'finished':
            await self.start_auto_delete_timer()

    async def disconnect(self, close_code):
        # Sair do grupo
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'start_game':
            await self.handle_start_game(data)
        elif message_type == 'submit_hint':
            await self.handle_submit_hint(data)
        elif message_type == 'submit_vote':
            await self.handle_submit_vote(data)
        elif message_type == 'restart_game':
            await self.handle_restart_game(data)
        elif message_type == 'close_room':
            await self.handle_close_room(data)
        elif message_type == 'get_state':
            await self.send_game_state()

    async def handle_start_game(self, data):
        """Iniciar o jogo"""
        game = await self.get_game()
        if not game:
            return
        
        # Validar player_name contra sessão autenticada
        player_name = await self.validate_player_name(data.get('player_name'))
        if not player_name:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Não autorizado'
            }))
            return
        
        player = await self.get_player(game, player_name)
        
        if not player or not player.is_creator:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Apenas o criador pode iniciar o jogo'
            }))
            return
        
        if not await self.can_start_game(game):
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Número mínimo de jogadores não atingido'
            }))
            return
        
        # Atribuir palavras e papéis
        if await self.assign_words(game):
            await self.assign_roles(game)
            
            # Iniciar primeira rodada
            game.status = 'hints'
            game.current_round = 1
            game.started_at = timezone.now()
            
            # Escolher primeiro jogador aleatório
            active_players = await self.get_active_players(game)
            if active_players:
                game.current_player_index = random.randint(0, len(active_players) - 1)
            
            await database_sync_to_async(game.save)()
            
            await self.send_game_state()

    async def handle_submit_hint(self, data):
        """Submeter uma dica"""
        game = await self.get_game()
        if not game:
            return
        
        # Validar player_name contra sessão autenticada
        player_name = await self.validate_player_name(data.get('player_name'))
        if not player_name:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Não autorizado'
            }))
            return
        
        hint_word = data.get('word', '').strip()
        
        if not hint_word:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Dica não pode estar vazia'
            }))
            return
        
        player = await self.get_player(game, player_name)
        if not player or player.is_eliminated:
            return
        
        # Verificar se é a vez do jogador
        current_player = await self.get_current_player(game)
        if current_player != player:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Não é sua vez'
            }))
            return
        
        # Criar dica
        hint, created = await database_sync_to_async(Hint.objects.get_or_create)(
            game=game,
            player=player,
            round_number=game.current_round,
            defaults={'word': hint_word}
        )
        
        if not created:
            hint.word = hint_word
            await database_sync_to_async(hint.save)()
        
        # Avançar para próximo jogador
        await database_sync_to_async(game.next_player)()
        
        # Verificar se todos deram dica
        active_players = await self.get_active_players(game)
        hints_this_round = await database_sync_to_async(
            Hint.objects.filter(game=game, round_number=game.current_round).count
        )()
        
        if hints_this_round >= len(active_players):
            # Todos deram dica, avançar rodada ou ir para votação
            if game.current_round < 3:
                # Nova rodada de dicas
                game.current_round += 1
                active_players = await self.get_active_players(game)
                if active_players:
                    game.current_player_index = random.randint(0, len(active_players) - 1)
            else:
                # Ir para votação
                game.status = 'voting'
                game.current_round += 1
                game.current_player_index = 0
        
        await database_sync_to_async(game.save)()
        await self.send_game_state()

    async def handle_submit_vote(self, data):
        """Submeter um voto"""
        game = await self.get_game()
        if not game:
            return
        
        # Validar player_name contra sessão autenticada
        player_name = await self.validate_player_name(data.get('player_name'))
        if not player_name:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Não autorizado'
            }))
            return
        
        target_name = data.get('target_name')
        
        voter = await self.get_player(game, player_name)
        target = await self.get_player(game, target_name)
        
        if not voter or not target or voter.is_eliminated:
            return
        
        # Verificar se já votou nesta rodada
        existing_vote = await database_sync_to_async(
            Vote.objects.filter(game=game, voter=voter, round_number=game.current_round).exists
        )()
        
        if existing_vote:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Você já votou nesta rodada'
            }))
            return
        
        # Criar voto
        await database_sync_to_async(Vote.objects.create)(
            game=game,
            voter=voter,
            target=target,
            round_number=game.current_round
        )
        
        # Verificar se todos votaram
        def check_all_voted():
            game_obj = Game.objects.get(id=game.id)
            active_players_list = list(game_obj.get_active_players())
            votes_count = Vote.objects.filter(game=game_obj, round_number=game_obj.current_round).count()
            return votes_count >= len(active_players_list), game_obj
        
        all_voted, game_obj = await database_sync_to_async(check_all_voted)()
        
        if all_voted:
            # Todos votaram, processar eliminação
            await self.process_voting(game_obj)
            # Recarregar game após processamento
            game = await self.get_game()
        
        await self.send_game_state()

    async def process_voting(self, game):
        """Processar votação e eliminar jogador"""
        def process_votes_sync():
            # Recarregar game para ter dados atualizados
            game_obj = Game.objects.get(id=game.id)
            
            # Contar votos
            votes = list(
                Vote.objects.filter(game=game_obj, round_number=game_obj.current_round)
                .select_related('target')
            )
            
            vote_count = {}
            for vote in votes:
                target_id = vote.target.id
                vote_count[target_id] = vote_count.get(target_id, 0) + 1
            
            # Encontrar jogador mais votado
            eliminated = False
            if vote_count:
                max_votes = max(vote_count.values())
                most_voted_ids = [pid for pid, vote_count_val in vote_count.items() if vote_count_val == max_votes]
                
                if len(most_voted_ids) == 1:
                    # Eliminar jogador mais votado
                    eliminated_player = Player.objects.get(id=most_voted_ids[0])
                    if not eliminated_player.is_eliminated:  # Só eliminar se ainda não foi eliminado
                        eliminated_player.is_eliminated = True
                        eliminated_player.save()
                        eliminated = True
                # Se houver empate, ninguém é eliminado mas o jogo continua
            
            # Recarregar game novamente após eliminação
            game_obj.refresh_from_db()
            
            # Verificar condições de vitória
            winner = game_obj.check_win_conditions()
            
            if winner:
                game_obj.status = 'finished'
                game_obj.finished_at = timezone.now()
                game_obj.save()
            else:
                # Continuar jogo com nova rodada de dicas
                game_obj.status = 'hints'
                game_obj.current_round += 1
                active_players_list = list(game_obj.get_active_players())
                if active_players_list:
                    game_obj.current_player_index = random.randint(0, len(active_players_list) - 1)
                else:
                    # Se não há mais jogadores ativos, finalizar
                    game_obj.status = 'finished'
                    game_obj.finished_at = timezone.now()
                game_obj.save()
            
            return game_obj
        
        await database_sync_to_async(process_votes_sync)()
        
        # Se o jogo terminou, iniciar timer de auto-delete
        updated_game = await self.get_game()
        if updated_game and updated_game.status == 'finished':
            await self.start_auto_delete_timer()

    async def handle_restart_game(self, data):
        """Reiniciar o jogo com os mesmos jogadores"""
        game = await self.get_game()
        if not game:
            return
        
        # Validar player_name contra sessão autenticada
        player_name = await self.validate_player_name(data.get('player_name'))
        if not player_name:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Não autorizado'
            }))
            return
        
        player = await self.get_player(game, player_name)
        
        if not player or not player.is_creator:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Apenas o criador pode reiniciar o jogo'
            }))
            return
        
        if game.status != 'finished':
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'O jogo ainda não terminou'
            }))
            return
        
        def restart_game_sync():
            from django.db import transaction
            
            with transaction.atomic():
                game_obj = Game.objects.select_for_update().get(id=game.id)
                
                # Resetar todos os jogadores (remover eliminação)
                for player in game_obj.players.all():
                    player.is_eliminated = False
                    player.role = None
                    player.word_id = None  # Resetar ForeignKey diretamente
                    player.save()
                
                # Limpar dicas e votos
                Hint.objects.filter(game=game_obj).delete()
                Vote.objects.filter(game=game_obj).delete()
                
                # Resetar estado do jogo
                game_obj.status = 'waiting'
                game_obj.current_round = 0
                game_obj.current_player_index = 0
                game_obj.word_group_id = None  # Resetar ForeignKey diretamente
                game_obj.whiteman_word_group_id = None  # Resetar ForeignKey diretamente
                game_obj.citizen_word_id = None  # Resetar ForeignKey diretamente
                game_obj.impostor_word_id = None  # Resetar ForeignKey diretamente
                game_obj.started_at = None
                game_obj.finished_at = None
                game_obj.save()
                
                return game_obj
        
        await database_sync_to_async(restart_game_sync)()
        
        # Cancelar timer de auto-delete se estiver rodando
        await self.cancel_auto_delete_timer()
        
        # Recarregar o game após reset para garantir dados atualizados
        game = await self.get_game()
        
        # Verificar se há jogadores suficientes após reset
        def check_players_count():
            game_obj = Game.objects.get(id=game.id)
            return game_obj.players.count()
        
        players_count = await database_sync_to_async(check_players_count)()
        
        await self.send_game_state()
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_state_message',
                'state': {
                    'type': 'game_restarted',
                    'message': f'O jogo foi reiniciado! {players_count} jogador(es) na sala. Configure e inicie novamente.'
                }
            }
        )

    async def handle_close_room(self, data):
        """Fechar e deletar a sala"""
        game = await self.get_game()
        if not game:
            return
        
        # Validar player_name contra sessão autenticada
        player_name = await self.validate_player_name(data.get('player_name'))
        if not player_name:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Não autorizado'
            }))
            return
        
        player = await self.get_player(game, player_name)
        
        if not player or not player.is_creator:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Apenas o criador pode fechar a sala'
            }))
            return
        
        def close_room_sync():
            game_obj = Game.objects.get(id=game.id)
            game_code = game_obj.code
            
            # Deletar tudo relacionado ao jogo
            # (Django CASCADE já deleta players, hints e votes automaticamente)
            game_obj.delete()
            
            return game_code
        
        game_code = await database_sync_to_async(close_room_sync)()
        
        # Cancelar timer de auto-delete se estiver rodando
        await self.cancel_auto_delete_timer()
        
        # Enviar mensagem de fechamento para todos
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_state_message',
                'state': {
                    'type': 'room_closed',
                    'message': 'A sala foi fechada pelo criador.',
                    'redirect': '/'
                }
            }
        )
        
        # Fechar conexões WebSocket após um delay
        await asyncio.sleep(2)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'close_connections'
            }
        )

    async def send_game_state(self):
        """Enviar estado atual do jogo para todos"""
        game = await self.get_game()
        if not game:
            return
        
        # Verificar se é espectador (sem autenticação)
        is_spectator = not hasattr(self, 'authenticated_player_name') or not self.authenticated_player_name
        
        players_data = []
        # Buscar players com select_related para evitar queries adicionais
        def get_players_data():
            players_list = list(game.players.select_related('word').all())
            result = []
            for player in players_list:
                word_text = None
                # Espectadores não veem palavras/papéis
                if not is_spectator and hasattr(player, 'word') and player.word:
                    word_text = player.word.text
                
                player_data = {
                    'id': player.id,
                    'name': player.name,
                    'is_eliminated': player.is_eliminated,
                    'is_creator': player.is_creator,
                }
                
                # Apenas jogadores autenticados veem papéis e palavras
                if not is_spectator:
                    # WhiteMan NÃO sabe que é WhiteMan enquanto está ativo - vê como Cidadão
                    # Mas quando é eliminado, TODOS (incluindo ele mesmo) descobrem que era WhiteMan
                    if player.role == 'whiteman' and not player.is_eliminated:
                        # WhiteMan ativo vê como citizen (não sabe que é WhiteMan)
                        player_data['role'] = 'citizen'
                    else:
                        # Mostrar papel real (WhiteMan eliminado, cidadãos, impostores)
                        player_data['role'] = player.role
                    player_data['word'] = word_text
                else:
                    # Espectadores não veem informações sensíveis
                    player_data['role'] = None
                    player_data['word'] = None
                
                result.append(player_data)
            return result
        
        players_data = await database_sync_to_async(get_players_data)()
        
        hints_data = []
        def get_hints_data():
            hints_list = list(
                Hint.objects.filter(game=game)
                .select_related('player')
                .order_by('round_number', 'created_at')
            )
            result = []
            for hint in hints_list:
                result.append({
                    'player_name': hint.player.name,
                    'round_number': hint.round_number,
                    'word': hint.word,
                    'created_at': hint.created_at.isoformat(),
                })
            return result
        
        hints_data = await database_sync_to_async(get_hints_data)()
        
        votes_data = []
        def get_votes_data():
            votes_list = list(
                Vote.objects.filter(game=game, round_number=game.current_round)
                .select_related('voter', 'target')
            )
            result = []
            for vote in votes_list:
                result.append({
                    'voter_name': vote.voter.name,
                    'target_name': vote.target.name,
                })
            return result
        
        votes_data = await database_sync_to_async(get_votes_data)()
        
        # Obter dados do game e current_player de forma síncrona
        def get_game_data():
            # Recarregar game com select_related para trazer os relacionamentos
            game_obj = Game.objects.select_related('citizen_word', 'impostor_word').get(id=game.id)
            citizen_word_text = game_obj.citizen_word.text if game_obj.citizen_word else None
            impostor_word_text = game_obj.impostor_word.text if game_obj.impostor_word else None
            
            # Obter current_player de forma síncrona
            current_player_name = None
            active_players_list = list(game_obj.get_active_players())
            if active_players_list and 0 <= game_obj.current_player_index < len(active_players_list):
                current_player_name = active_players_list[game_obj.current_player_index].name
            
            game_data = {
                'code': game_obj.code,
                'status': game_obj.status,
                'current_round': game_obj.current_round,
                'current_player': current_player_name,
                'num_impostors': game_obj.num_impostors,
                'num_whitemen': game_obj.num_whitemen,
            }
            
            # Espectadores não veem as palavras do jogo
            # Usar variável capturada do escopo externo
            spectator_mode = is_spectator
            if not spectator_mode:
                game_data['citizen_word'] = citizen_word_text
                game_data['impostor_word'] = impostor_word_text
            else:
                game_data['citizen_word'] = None
                game_data['impostor_word'] = None
            
            return game_data
        
        game_data = await database_sync_to_async(get_game_data)()
        
        state = {
            'type': 'game_state',
            'game': game_data,
            'players': players_data,
            'hints': hints_data,
            'votes': votes_data,
        }
        
        # Enviar para o grupo
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_state_message',
                'state': state
            }
        )

    async def game_state_message(self, event):
        """Enviar mensagem de estado do jogo"""
        state = event.get('state', {})
        if state.get('type') == 'room_closed':
            # Se a sala foi fechada, redirecionar após mostrar mensagem
            await self.send(text_data=json.dumps(state))
            await asyncio.sleep(1)
            await self.close()
        else:
            await self.send(text_data=json.dumps(state))
    
    async def close_connections(self, event):
        """Fechar todas as conexões"""
        await self.close()

    async def start_auto_delete_timer(self):
        """Iniciar timer de 60 segundos para auto-delete"""
        # Cancelar timer anterior se existir
        await self.cancel_auto_delete_timer()
        
        # Criar task para auto-delete
        self.auto_delete_task = asyncio.create_task(self._auto_delete_countdown())
    
    async def cancel_auto_delete_timer(self):
        """Cancelar timer de auto-delete"""
        if self.auto_delete_task and not self.auto_delete_task.done():
            self.auto_delete_task.cancel()
            try:
                await self.auto_delete_task
            except asyncio.CancelledError:
                pass
            self.auto_delete_task = None
    
    async def _auto_delete_countdown(self):
        """Contagem regressiva de 60 segundos antes de deletar"""
        try:
            for remaining in range(60, 0, -1):
                await asyncio.sleep(1)
                
                # Verificar se o jogo ainda existe e está finalizado
                game = await self.get_game()
                if not game or game.status != 'finished':
                    # Jogo foi reiniciado ou deletado, cancelar
                    return
                
                # Enviar tempo restante para todos
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'game_state_message',
                        'state': {
                            'type': 'auto_delete_countdown',
                            'seconds_remaining': remaining,
                            'message': f'A sala será fechada automaticamente em {remaining} segundos...'
                        }
                    }
                )
            
            # Tempo acabou, deletar sala
            game = await self.get_game()
            if game and game.status == 'finished':
                def delete_game_sync():
                    game_obj = Game.objects.get(id=game.id)
                    game_obj.delete()
                
                await database_sync_to_async(delete_game_sync)()
                
                # Notificar todos
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'game_state_message',
                        'state': {
                            'type': 'room_closed',
                            'message': 'A sala foi fechada automaticamente após 1 minuto.',
                            'redirect': '/'
                        }
                    }
                )
                
                # Fechar conexões
                await asyncio.sleep(2)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'close_connections'
                    }
                )
        except asyncio.CancelledError:
            # Timer foi cancelado, tudo bem
            pass

    @database_sync_to_async
    def get_game(self):
        try:
            # Usar select_related para trazer relacionamentos quando necessário
            return Game.objects.select_related('citizen_word', 'impostor_word', 'word_group').get(code=self.game_code)
        except Game.DoesNotExist:
            return None

    @database_sync_to_async
    def get_player(self, game, name):
        try:
            return Player.objects.get(game=game, name=name)
        except Player.DoesNotExist:
            return None

    @database_sync_to_async
    def can_start_game(self, game):
        return game.can_start()

    @database_sync_to_async
    def assign_words(self, game):
        return game.assign_words()

    @database_sync_to_async
    def assign_roles(self, game):
        game.assign_roles()

    @database_sync_to_async
    def get_active_players(self, game):
        return list(game.get_active_players())

    @database_sync_to_async
    def get_current_player(self, game):
        return game.get_current_player()
    
    async def get_authenticated_player_name(self):
        """Obter player_name autenticado da sessão
        
        A chave da sessão inclui o código da sala (player_{game_code}), então cada
        sala tem sua própria autenticação independente. Isso permite que o mesmo
        nome de jogador exista em salas diferentes sem conflito.
        """
        # A sessão deve estar disponível via SessionMiddlewareStack
        session = self.scope.get('session')
        if session:
            try:
                return session.get(f'player_{self.game_code}')
            except (AttributeError, KeyError, TypeError):
                pass
        
        return None
    
    async def validate_player_name(self, provided_name):
        """Validar se o player_name fornecido corresponde ao autenticado"""
        if not provided_name:
            return None
        
        authenticated_name = getattr(self, 'authenticated_player_name', None)
        if not authenticated_name:
            # Tentar obter da sessão novamente
            authenticated_name = await self.get_authenticated_player_name()
            if authenticated_name:
                self.authenticated_player_name = authenticated_name
        
        # Verificar se o nome fornecido corresponde ao autenticado
        if provided_name == authenticated_name:
            return authenticated_name
        
        return None

