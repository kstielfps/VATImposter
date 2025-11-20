from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import json
import traceback
import os
import logging
import random
from .models import Game, Player, Hint, Vote, Nudge, WordGroup, Word, sort_players_for_display

User = get_user_model()


def home(request):
    """Página inicial"""
    return render(request, 'game/home.html')


@csrf_exempt
@require_http_methods(["GET", "POST"])
def create_game(request):
    """Criar uma nova sala de jogo"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            raw_creator_name = data.get('creator_name', '')
            creator_name, error = _normalize_player_name(raw_creator_name, 'Nome do criador')
            if error:
                return JsonResponse({'error': error}, status=400)
            num_impostors = int(data.get('num_impostors', 1))
            num_whitemen = int(data.get('num_whitemen', 0))
            num_clowns = int(data.get('num_palhacos', 0))
            
            # Validações
            if num_impostors < 1 or num_impostors > 2:
                return JsonResponse({'error': 'Número de impostores deve ser entre 1 e 2'}, status=400)
            
            if num_whitemen < 0 or num_whitemen > 3:
                return JsonResponse({'error': 'Número de whitemen deve ser entre 0 e 3'}, status=400)
            if num_clowns < 0 or num_clowns > 1:
                return JsonResponse({'error': 'Número de palhaços deve ser 0 ou 1'}, status=400)
            
            # Criar jogo
            game = Game.objects.create(
                creator=creator_name,
                num_impostors=num_impostors,
                num_whitemen=num_whitemen,
                num_clowns=num_clowns,
                status='waiting'
            )
            
            # Criar jogador criador
            Player.objects.create(
                game=game,
                name=creator_name,
                is_creator=True
            )
            
            # Armazenar autenticação na sessão
            # A chave inclui o código da sala, permitindo que o mesmo nome de jogador
            # exista em salas diferentes sem conflito (ex: player_ABC123 e player_XYZ789)
            request.session[f'player_{game.code}'] = creator_name
            request.session.modified = True
            
            return JsonResponse({
                'code': game.code,
                'redirect': f'/game/{game.code}/'
            })
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Dados inválidos'}, status=400)
        except ValueError as e:
            return JsonResponse({'error': f'Valor inválido: {str(e)}'}, status=400)
        except Exception as e:
            error_trace = traceback.format_exc()
            # Em produção, não expor o trace completo por segurança
            # Mas vamos logar para debug
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao criar jogo: {str(e)}\n{error_trace}")
            
            if settings.DEBUG:
                return JsonResponse({'error': f'Erro interno: {str(e)}', 'trace': error_trace}, status=500)
            else:
                return JsonResponse({'error': 'Erro interno do servidor. Verifique os logs.'}, status=500)
    
    return render(request, 'game/create.html')


@csrf_exempt
@require_http_methods(["GET", "POST"])
def join_game(request):
    """Entrar em uma sala existente"""
    if request.method == 'POST':
        data = json.loads(request.body)
        code = data.get('code', '').strip().upper()
        raw_name = data.get('player_name', '')
        player_name, error = _normalize_player_name(raw_name, 'Nome do jogador')
        
        if not code or error:
            if not code:
                return JsonResponse({'error': 'Código é obrigatório'}, status=400)
            return JsonResponse({'error': error}, status=400)
        
        if not player_name:
            return JsonResponse({'error': 'Código e nome são obrigatórios'}, status=400)
        
        try:
            game = Game.objects.get(code=code)
        except Game.DoesNotExist:
            return JsonResponse({'error': 'Código inválido'}, status=404)
        
        # Verificar se o jogo já começou
        if game.status != 'waiting' and game.status != 'configuring':
            return JsonResponse({'error': 'O jogo já começou'}, status=400)
        
        # Verificar se já existe jogador com esse nome
        if Player.objects.filter(game=game, name=player_name).exists():
            return JsonResponse({'error': 'Nome já está em uso nesta sala'}, status=400)
        
        # Verificar limite de jogadores
        current_players = game.players.count()
        if current_players >= game.max_players:
            return JsonResponse({'error': 'Sala cheia'}, status=400)
        
        # Criar jogador
        Player.objects.create(
            game=game,
            name=player_name
        )
        
        # Armazenar autenticação na sessão
        # A chave inclui o código da sala, permitindo que o mesmo nome de jogador
        # exista em salas diferentes sem conflito (ex: player_ABC123 e player_XYZ789)
        request.session[f'player_{game.code}'] = player_name
        request.session.modified = True
        
        return JsonResponse({
            'code': game.code,
            'redirect': f'/game/{game.code}/'
        })
    
    return render(request, 'game/join.html')


def game_room(request, code):
    """Sala do jogo"""
    game = get_object_or_404(Game, code=code)
    ordered_players = sort_players_for_display(game.code, game.players.all())
    
    # Modo espectador: permite assistir sem autenticação
    is_spectator = request.GET.get('spectator') == '1'
    
    if is_spectator:
        # Modo espectador - não precisa de autenticação
        context = {
            'game': game,
            'player': None,
            'players': ordered_players,
            'is_spectator': True,
        }
        return render(request, 'game/room.html', context)
    
    # Modo normal - requer autenticação
    # Obter player_name da sessão (cookie) ao invés do GET parameter
    # A chave da sessão inclui o código da sala, então cada sala tem sua própria
    # autenticação independente, permitindo o mesmo nome em salas diferentes
    player_name = request.session.get(f'player_{code}', '')
    
    # Verificar se o jogador existe e está autenticado
    player = None
    if player_name:
        try:
            player = Player.objects.get(game=game, name=player_name)
        except Player.DoesNotExist:
            # Player não existe mais ou sessão inválida
            # Limpar sessão inválida
            if f'player_{code}' in request.session:
                del request.session[f'player_{code}']
                request.session.modified = True
            player_name = ''
    
    # Se não há player autenticado, redirecionar para página de entrada
    if not player:
        return redirect('join_game')
    
    context = {
        'game': game,
        'player': player,
        'players': ordered_players,
        'is_spectator': False,
    }
    
    return render(request, 'game/room.html', context)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def create_admin_user(request):
    """
    View para criar um superusuário via HTTP.
    Protegido por token simples ou apenas em DEBUG mode.
    Use: /create-admin/?token=YOUR_TOKEN&username=admin&password=senha123&email=admin@example.com
    Ou acesse /create-admin/ para ver o formulário (se DEBUG=True)
    """
    # DESABILITAR se já existe superuser (segurança)
    if User.objects.filter(is_superuser=True).exists():
        return JsonResponse({
            'error': 'Já existe um superusuário criado',
            'message': 'Por segurança, esta rota está desabilitada',
            'admin_url': '/admin/'
        }, status=403)
    
    # Se for GET e DEBUG=True, mostrar formulário
    if request.method == 'GET' and settings.DEBUG:
        return render(request, 'game/create_admin.html')
    
    # Verificar token (pode ser definido como variável de ambiente)
    admin_token = os.environ.get('ADMIN_CREATE_TOKEN', 'railway-admin-2024')
    
    # Obter token dos parâmetros
    if request.method == 'POST':
        try:
            data = json.loads(request.body) if request.content_type == 'application/json' else request.POST
            token = data.get('token')
            username = data.get('username', 'admin')
            password = data.get('password', 'admin123')
            email = data.get('email', 'admin@example.com')
        except:
            token = request.POST.get('token')
            username = request.POST.get('username', 'admin')
            password = request.POST.get('password', 'admin123')
            email = request.POST.get('email', 'admin@example.com')
    else:
        token = request.GET.get('token')
        username = request.GET.get('username', 'admin')
        password = request.GET.get('password', 'admin123')
        email = request.GET.get('email', 'admin@example.com')
    
    # Permitir apenas se token correto OU se DEBUG=True
    if not settings.DEBUG and token != admin_token:
        return JsonResponse({
            'error': 'Token inválido ou acesso negado',
            'hint': 'Defina ADMIN_CREATE_TOKEN nas variáveis de ambiente ou use DEBUG=True'
        }, status=403)
    
    # Validações básicas
    if not username:
        return JsonResponse({'error': 'Username é obrigatório'}, status=400)
    
    if not password:
        return JsonResponse({'error': 'Password é obrigatório'}, status=400)
    
    if len(password) < 8:
        return JsonResponse({'error': 'Password deve ter pelo menos 8 caracteres'}, status=400)
    
    # Verificar se o usuário já existe
    if User.objects.filter(username=username).exists():
        return JsonResponse({
            'error': f'Usuário "{username}" já existe',
            'exists': True
        }, status=400)
    
    # Criar superusuário
    try:
        User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        return JsonResponse({
            'success': True,
            'message': f'Superusuário "{username}" criado com sucesso!',
            'username': username,
            'email': email,
            'admin_url': '/admin/'
        })
    except Exception as e:
        error_trace = traceback.format_exc()
        logger = logging.getLogger(__name__)
        logger.error(f"Erro ao criar admin: {str(e)}\n{error_trace}")
        
        return JsonResponse({
            'error': f'Erro ao criar superusuário: {str(e)}',
            'trace': error_trace if settings.DEBUG else None
        }, status=500)


def _json_error(message, status=400, extra=None):
    payload = {'error': message}
    if extra:
        payload.update(extra)
    return JsonResponse(payload, status=status)


def _get_session_player(request, game):
    session_key = f'player_{game.code}'
    player_name = request.session.get(session_key)
    if not player_name:
        return None, None
    try:
        player = Player.objects.get(game=game, name=player_name)
        return player, player_name
    except Player.DoesNotExist:
        if session_key in request.session:
            del request.session[session_key]
            request.session.modified = True
        return None, None


def _validate_player_action(request, game, provided_name):
    if not provided_name:
        return None
    player, session_name = _get_session_player(request, game)
    if not player or session_name != provided_name:
        return None
    return player


def _normalize_player_name(raw_name, field_label='Nome'):
    cleaned = (raw_name or '').strip()
    if not cleaned:
        return None, f'{field_label} é obrigatório'
    if any(ch.isspace() for ch in cleaned):
        return None, f'{field_label} não pode conter espaços'
    if len(cleaned) > 10:
        cleaned = cleaned[:10]
    return cleaned, None


def _reset_nudges_for_round(game, round_number):
    game.players.update(nudge_meter=100, nudge_meter_round=round_number)


def _ensure_player_nudge_round(player, round_number):
    if player.nudge_meter_round != round_number:
        player.nudge_meter = 100
        player.nudge_meter_round = round_number
        player.save(update_fields=['nudge_meter', 'nudge_meter_round'])


def _record_hint_and_progress(game, player, hint_word):
    hint, created = Hint.objects.get_or_create(
        game=game,
        player=player,
        round_number=game.current_round,
        defaults={'word': hint_word}
    )
    if not created:
        hint.word = hint_word
        hint.save()

    game.next_player()

    active_players = list(game.get_active_players())
    active_count = len(active_players) if active_players else 0
    hints_this_round = Hint.objects.filter(game=game, round_number=game.current_round).count()

    if active_count == 0:
        return

    if hints_this_round >= active_count:
        if game.current_round < 3:
            game.current_round += 1
            active_players = list(game.get_active_players())
            if active_players:
                game.current_player_index = random.randint(0, len(active_players) - 1)
            _reset_nudges_for_round(game, game.current_round)
        else:
            game.status = 'voting'
            game.current_round += 1
            game.current_player_index = 0
            _reset_nudges_for_round(game, game.current_round)
    game.save()


def _serialize_game_state(game, is_spectator, player_name=None):
    viewer_player = None
    if player_name and not is_spectator:
        viewer_player = Player.objects.filter(game=game, name=player_name).first()

    players_qs = game.players.select_related('word').all()
    players_list = sort_players_for_display(game.code, players_qs)
    players_data = []
    for player in players_list:
        word_text = None
        role_value = None
        is_clown_revealed = False  # Para mostrar ao impostor quem é o Palhaço
        
        if not is_spectator:
            reveal_role = (
                viewer_player and player.id == viewer_player.id
            ) or player.is_eliminated or game.status == 'finished'

            actual_role = player.role
            if actual_role in ['whiteman', 'clown'] and not reveal_role:
                role_value = 'citizen'
            else:
                role_value = actual_role
            
            # Revelar Palhaço ao impostor se o poder de caos foi usado
            if (viewer_player and viewer_player.role == 'impostor' and 
                viewer_player.impostor_knows_clown and player.role == 'clown'):
                is_clown_revealed = True

            if player.word:
                if viewer_player and player.id == viewer_player.id:
                    word_text = player.word.text
                elif reveal_role and actual_role != 'impostor':
                    word_text = player.word.text
        players_data.append({
            'id': player.id,
            'name': player.name,
            'is_eliminated': player.is_eliminated,
            'is_creator': player.is_creator,
            'role': role_value,
            'actual_role': player.role if (viewer_player and player.id == viewer_player.id) or player.is_eliminated or game.status == 'finished' else None,
            'word': word_text,
            'nudge_meter': player.nudge_meter,
            'nudge_meter_round': player.nudge_meter_round,
            'is_clown_revealed': is_clown_revealed,
        })

    hints_data = [
        {
            'player_name': hint.player.name,
            'round_number': hint.round_number,
            'word': hint.word,
            'created_at': hint.created_at.isoformat(),
        }
        for hint in Hint.objects.filter(game=game)
        .select_related('player')
        .order_by('round_number', 'created_at')
    ]

    current_round_votes = Vote.objects.filter(game=game, round_number=game.current_round, is_palhaco_guess=False)
    votes_data = [
        {
            'voter_name': vote.voter.name,
            'target_name': vote.target.name,
        }
        for vote in current_round_votes.select_related('voter', 'target')
    ]

    vote_history = {}
    vote_tallies = {}
    elimination_votes = Vote.objects.filter(game=game, is_palhaco_guess=False).select_related('voter', 'target').order_by('round_number', 'created_at')
    for vote in elimination_votes:
        vote_history.setdefault(vote.round_number, []).append({
            'voter_name': vote.voter.name,
            'target_name': vote.target.name,
        })
        vote_tallies.setdefault(vote.round_number, {})
        vote_tallies[vote.round_number][vote.target.name] = vote_tallies[vote.round_number].get(vote.target.name, 0) + 1

    # Get pending nudges for this player
    nudges_data = []
    if player_name and not is_spectator:
        try:
            current_player = Player.objects.get(game=game, name=player_name)
            pending_nudges = Nudge.objects.filter(
                game=game,
                to_player=current_player,
                acknowledged=False,
                round_number=game.current_round
            ).select_related('from_player')
            
            nudges_data = [
                {
                    'id': nudge.id,
                    'from_player': nudge.from_player.name,
                    'created_at': nudge.created_at.isoformat(),
                }
                for nudge in pending_nudges
            ]
            
            # Mark nudges as acknowledged
            if nudges_data:
                pending_nudges.update(acknowledged=True)
        except Player.DoesNotExist:
            pass

    active_players = list(game.get_active_players())
    current_player_name = None
    if active_players and 0 <= game.current_player_index < len(active_players):
        current_player_name = active_players[game.current_player_index].name

    game_data = {
        'code': game.code,
        'status': game.status,
        'current_round': game.current_round,
        'current_player': current_player_name,
        'num_impostors': game.num_impostors,
        'num_whitemen': game.num_whitemen,
        'num_clowns': game.num_clowns,
        'max_players': game.max_players,
        'citizen_word': None,
        'impostor_word': None,
        'nudge_meter_max': 100,
        'winning_team': game.winning_team,
    }

    if not is_spectator:
        game_data['citizen_word'] = game.citizen_word.text if game.citizen_word else None
        game_data['impostor_word'] = game.impostor_word.text if game.impostor_word else None
        if game.status == 'finished':
            game_data['actual_num_impostors'] = game.actual_num_impostors
            game_data['actual_num_whitemen'] = game.actual_num_whitemen
            game_data['actual_num_clowns'] = game.actual_num_clowns

    palhaco_payload = None
    if viewer_player and viewer_player.role == 'clown':
        known_ids = viewer_player.palhaco_known_impostors or []
        known_players = list(Player.objects.filter(id__in=known_ids)) if known_ids else []
        total_impostors = game.actual_num_impostors or game.num_impostors
        
        # Contar quantos palpites já foram feitos nesta rodada
        guesses_count = Vote.objects.filter(
            game=game,
            voter=viewer_player,
            round_number=game.current_round,
            is_palhaco_guess=True
        ).count()
        
        # Pode fazer palpite se ainda não completou todos os palpites necessários
        can_guess = (
            game.status == 'voting' and
            not viewer_player.is_eliminated and
            viewer_player.palhaco_goal_state in ['', 'finding', 'pending'] and
            guesses_count < total_impostors
        )
        
        already_completed_guesses = guesses_count >= total_impostors
        
        can_use_chaos_power = (
            viewer_player.palhaco_goal_state == 'eliminate' and
            not viewer_player.palhaco_used_chaos_power and
            not viewer_player.is_eliminated and
            game.status in ['hints', 'voting']
        )
        
        palhaco_payload = {
            'goal_state': viewer_player.palhaco_goal_state or 'finding',
            'known_impostors': [p.name for p in known_players],
            'known_count': len(known_players),
            'total_impostors': total_impostors,
            'remaining_impostors': max(0, total_impostors - len(known_ids)),
            'can_guess': can_guess,
            'already_guessed_this_round': already_completed_guesses,
            'guesses_made': guesses_count,
            'guesses_remaining': max(0, total_impostors - guesses_count),
            'goal_ready_round': viewer_player.palhaco_goal_ready_round,
            'needs_elimination': viewer_player.palhaco_goal_state == 'eliminate',
            'can_use_chaos_power': can_use_chaos_power,
            'chaos_power_used': viewer_player.palhaco_used_chaos_power,
        }

    return {
        'game': game_data,
        'players': players_data,
        'hints': hints_data,
        'votes': votes_data,
        'vote_history': vote_history,
        'vote_tallies': vote_tallies,
        'nudges': nudges_data,
        'palhaco': palhaco_payload,
    }


def _process_voting(game):
    vote_count = {}
    votes = list(
        Vote.objects.filter(game=game, round_number=game.current_round, is_palhaco_guess=False)
        .select_related('target')
    )
    for vote in votes:
        target_id = vote.target.id
        vote_count[target_id] = vote_count.get(target_id, 0) + 1

    eliminated_player_id = None
    eliminated_player = None
    if vote_count:
        max_votes = max(vote_count.values())
        most_voted_ids = [pid for pid, count in vote_count.items() if count == max_votes]
        if len(most_voted_ids) == 1:
            eliminated_player = Player.objects.get(id=most_voted_ids[0])
            if not eliminated_player.is_eliminated:
                eliminated_player.is_eliminated = True
                eliminated_player.save()
                eliminated_player_id = eliminated_player.id
                
                # Verificar vitória do Palhaço: ele deve ser eliminado APÓS ter descoberto todos os impostores
                if eliminated_player.role == 'clown' and eliminated_player.palhaco_goal_state == 'eliminate':
                    known_ids = eliminated_player.palhaco_known_impostors or []
                    total_required = game.actual_num_impostors or game.num_impostors
                    if len(set(known_ids)) >= total_required:
                        game.status = 'finished'
                        game.finished_at = timezone.now()
                        game.winning_team = 'clown'
                        game.save()
                        return eliminated_player_id, vote_count

    game.refresh_from_db()
    winner = game.check_win_conditions()
    if winner:
        game.status = 'finished'
        game.finished_at = timezone.now()
    else:
        game.status = 'hints'
        game.current_round += 1
        active_players = list(game.get_active_players())
        if active_players:
            game.current_player_index = random.randint(0, len(active_players) - 1)
        else:
            game.status = 'finished'
            game.finished_at = timezone.now()
    game.save()
    return eliminated_player_id, vote_count


def _remaining_auto_delete_seconds(game):
    if game.status != 'finished' or not game.finished_at:
        return None
    elapsed = (timezone.now() - game.finished_at).total_seconds()
    remaining = int(max(0, 60 - elapsed))
    return remaining


@csrf_exempt
def game_state_api(request, code):
    if request.method != 'GET':
        return _json_error('Método não permitido', status=405)

    game = Game.objects.select_related('citizen_word', 'impostor_word', 'word_group').filter(code=code).first()
    if not game:
        return JsonResponse({'room_closed': True, 'message': 'A sala não existe mais.', 'redirect': '/'}, status=404)

    spectator_flag = request.GET.get('spectator') == '1'
    player, _ = _get_session_player(request, game)
    is_spectator = spectator_flag or player is None
    player_name = player.name if player else None

    data = _serialize_game_state(game, is_spectator, player_name)
    remaining = _remaining_auto_delete_seconds(game)
    data['auto_delete_seconds'] = remaining

    if remaining is not None and remaining <= 0:
        game.delete()
        return JsonResponse({'room_closed': True, 'message': 'A sala foi fechada automaticamente após 1 minuto.', 'redirect': '/'})

    return JsonResponse(data)


@csrf_exempt
@require_http_methods(["POST"])
def start_game_api(request, code):
    game = get_object_or_404(Game, code=code)
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _json_error('Dados inválidos')

    player = _validate_player_action(request, game, payload.get('player_name'))
    if not player:
        return _json_error('Não autorizado', status=403)
    if not player.is_creator:
        return _json_error('Apenas o criador pode iniciar o jogo', status=403)
    can_start, reason = game.validate_can_start()
    if not can_start:
        return _json_error(reason or 'Número mínimo de jogadores não atingido')
    if not game.assign_words():
        return _json_error('Não há grupos de palavras suficientes para iniciar o jogo')

    game.assign_roles()
    game.status = 'hints'
    game.current_round = 1
    game.started_at = timezone.now()
    active_players = list(game.get_active_players())
    if active_players:
        game.current_player_index = random.randint(0, len(active_players) - 1)
    game.save()
    _reset_nudges_for_round(game, game.current_round)
    return JsonResponse({'success': True})


@csrf_exempt
@require_http_methods(["POST"])
def submit_hint_api(request, code):
    game = get_object_or_404(Game, code=code)
    if game.status != 'hints':
        return _json_error('Não é possível enviar dicas agora', status=400)
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _json_error('Dados inválidos')

    player = _validate_player_action(request, game, payload.get('player_name'))
    if not player:
        return _json_error('Não autorizado', status=403)
    if player.is_eliminated:
        return _json_error('Jogador eliminado não pode dar dicas')

    hint_word = (payload.get('word') or '').strip()
    if not hint_word:
        return _json_error('Dica não pode estar vazia')

    current_player = game.get_current_player()
    if current_player != player:
        return _json_error('Não é sua vez', status=403)

    _record_hint_and_progress(game, player, hint_word)
    return JsonResponse({'success': True})


@csrf_exempt
@require_http_methods(["POST"])
def submit_vote_api(request, code):
    game = get_object_or_404(Game, code=code)
    if game.status != 'voting':
        return _json_error('Votação não está ativa', status=400)
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _json_error('Dados inválidos')

    player = _validate_player_action(request, game, payload.get('player_name'))
    if not player:
        return _json_error('Não autorizado', status=403)
    ghost_whiteman = player.role == 'whiteman' and player.is_eliminated
    if player.is_eliminated and not ghost_whiteman:
        return _json_error('Jogador eliminado não vota')

    target_name = payload.get('target_name')
    if not target_name:
        return _json_error('Jogador alvo é obrigatório')

    try:
        target = Player.objects.get(game=game, name=target_name)
    except Player.DoesNotExist:
        return _json_error('Jogador alvo não encontrado')

    if Vote.objects.filter(game=game, voter=player, round_number=game.current_round, is_palhaco_guess=False).exists():
        return _json_error('Você já votou nesta rodada')

    Vote.objects.create(game=game, voter=player, target=target, round_number=game.current_round, is_palhaco_guess=False)

    active_players = list(game.get_active_players())
    votes_count = Vote.objects.filter(
        game=game,
        round_number=game.current_round,
        is_palhaco_guess=False,
        voter__is_eliminated=False,
    ).count()
    
    vote_result = None
    if len(active_players) > 0 and votes_count >= len(active_players):
        eliminated_id, vote_count = _process_voting(game)
        vote_result = {
            'eliminated_player_id': eliminated_id,
            'vote_counts': {
                Player.objects.get(id=pid).name: count 
                for pid, count in vote_count.items()
            }
        }

    return JsonResponse({'success': True, 'vote_result': vote_result})


@csrf_exempt
@require_http_methods(["POST"])
def submit_palhaco_guess_api(request, code):
    game = get_object_or_404(Game, code=code)
    if game.status != 'voting':
        return _json_error('Os palpites do Palhaço só podem acontecer durante a votação.', status=400)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _json_error('Dados inválidos')

    player = _validate_player_action(request, game, payload.get('player_name'))
    if not player:
        return _json_error('Não autorizado', status=403)
    if player.role != 'clown':
        return _json_error('Apenas o Palhaço pode usar esta ação', status=403)
    if player.is_eliminated:
        return _json_error('Palhaço eliminado não pode fazer palpites', status=400)
    if player.palhaco_goal_state == 'eliminate':
        return _json_error('Você já descobriu todos os impostores. Agora convença a sala a votar em você!', status=400)

    target_name = payload.get('target_name')
    if not target_name:
        return _json_error('Jogador alvo é obrigatório')

    try:
        target = Player.objects.get(game=game, name=target_name)
    except Player.DoesNotExist:
        return _json_error('Jogador alvo não encontrado')

    if target.name == player.name:
        return _json_error('Você não pode se acusar')

    # Verificar se já completou todos os palpites desta rodada
    total_impostors = game.actual_num_impostors or game.num_impostors
    existing_guesses = Vote.objects.filter(
        game=game,
        voter=player,
        round_number=game.current_round,
        is_palhaco_guess=True,
    ).select_related('target')
    
    current_guesses = existing_guesses.count()
    
    if current_guesses >= total_impostors:
        return _json_error('Você já fez todos os palpites desta rodada')
    
    # Verificar se já votou neste jogador nesta rodada (evitar duplicatas)
    if existing_guesses.filter(target=target).exists():
        return _json_error(f'Você já apostou em {target.name} nesta rodada')

    # Usar get_or_create para evitar duplicatas devido a race conditions
    vote, created = Vote.objects.get_or_create(
        game=game,
        voter=player,
        target=target,
        round_number=game.current_round,
        is_palhaco_guess=True,
    )
    
    if not created:
        # Voto já existia (duplo clique ou race condition)
        return _json_error(f'Você já apostou em {target.name} nesta rodada')

    # Contar quantos palpites já foram feitos nesta rodada (incluindo este)
    total_guesses = current_guesses + 1
    
    total_impostors = game.actual_num_impostors or game.num_impostors
    
    # Se ainda não fez todos os palpites necessários
    if total_guesses < total_impostors:
        remaining = total_impostors - total_guesses
        return JsonResponse({
            'success': True,
            'message': f'🎭 Palpite registrado. Faltam {remaining} palpite(s) para revelar o resultado.',
            'remaining_guesses': remaining,
            'waiting_result': True,
        })
    
    # Se completou todos os palpites, verificar se acertou TODOS
    guesses_this_round = Vote.objects.filter(
        game=game,
        voter=player,
        round_number=game.current_round,
        is_palhaco_guess=True,
    ).select_related('target')
    
    # IDs dos jogadores que o Palhaço apostou
    guessed_ids = set(vote.target.id for vote in guesses_this_round)
    
    # IDs dos impostores reais (incluindo eliminados - Palhaço deve adivinhar todos)
    real_impostor_ids = set(
        Player.objects.filter(game=game, role='impostor')
        .values_list('id', flat=True)
    )
    
    # Verificar se acertou TODOS os impostores (e não chutou ninguém errado)
    if guessed_ids == real_impostor_ids:
        # ACERTOU TODOS!
        player.palhaco_known_impostors = list(real_impostor_ids)
        player.palhaco_goal_state = 'eliminate'
        player.palhaco_goal_ready_round = game.current_round
        player.save(update_fields=['palhaco_known_impostors', 'palhaco_goal_state', 'palhaco_goal_ready_round'])
        
        return JsonResponse({
            'success': True,
            'message': '🎉 PARABÉNS! Você descobriu TODOS os impostores! Agora precisa ser eliminado para vencer sozinho.',
            'all_correct': True,
            'remaining_guesses': 0,
        })
    else:
        # ERROU algum (ou todos)
        return JsonResponse({
            'success': True,
            'message': '❌ Você errou! Não conseguiu identificar todos os impostores corretamente. Tente novamente na próxima rodada.',
            'all_correct': False,
            'remaining_guesses': 0,
        })


@csrf_exempt
@require_http_methods(["POST"])
def use_chaos_power_api(request, code):
    """Palhaço usa o poder de embaralhar palavras (só pode usar quando encontrou todos os impostores)"""
    game = get_object_or_404(Game, code=code)
    if game.status not in ['hints', 'voting']:
        return _json_error('O poder só pode ser usado durante o jogo.', status=400)

    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _json_error('Dados inválidos')

    player = _validate_player_action(request, game, payload.get('player_name'))
    if not player:
        return _json_error('Não autorizado', status=403)
    if player.role != 'clown':
        return _json_error('Apenas o Palhaço pode usar este poder', status=403)
    if player.is_eliminated:
        return _json_error('Palhaço eliminado não pode usar poderes', status=400)
    if player.palhaco_goal_state != 'eliminate':
        return _json_error('Você precisa encontrar todos os impostores primeiro', status=400)
    
    # Verificar se já usou (com tratamento para campo que pode não existir)
    try:
        if player.palhaco_used_chaos_power:
            return _json_error('Você já usou este poder', status=400)
    except AttributeError:
        # Campo não existe no banco (migração não aplicada)
        return _json_error('Poder de caos não disponível. Aguarde atualização do servidor.', status=503)

    try:
        with transaction.atomic():
            locked_game = Game.objects.select_for_update().get(id=game.id)
            
            # Obter todos os grupos de palavras disponíveis
            all_groups = list(WordGroup.objects.prefetch_related('words').filter(words__isnull=False).distinct())
            if len(all_groups) < 1:
                return _json_error('Não há grupos de palavras cadastrados no sistema', status=400)
            
            # Se há apenas 1 grupo, usar o mesmo (mas trocar as palavras)
            if len(all_groups) < 2:
                new_citizen_group = all_groups[0]
            else:
                # Escolher novo grupo para cidadãos/impostores (diferente do atual se possível)
                available_groups = [g for g in all_groups if g.id != locked_game.word_group_id]
                new_citizen_group = random.choice(available_groups if available_groups else all_groups)
            
            citizen_words = list(new_citizen_group.words.all())
            if len(citizen_words) < 2:
                return _json_error('Grupo escolhido não tem palavras suficientes (mínimo 2)', status=400)
            
            # Escolher novas palavras para cidadão e impostor
            new_citizen_word = random.choice(citizen_words)
            remaining = [w for w in citizen_words if w.id != new_citizen_word.id]
            new_impostor_word = random.choice(remaining) if remaining else new_citizen_word
            
            # Escolher novo grupo para WhiteMan (diferente dos grupos de cidadão/impostor se possível)
            if len(all_groups) > 1:
                whiteman_groups = [g for g in all_groups if g.id != new_citizen_group.id]
                new_whiteman_group = random.choice(whiteman_groups) if whiteman_groups else all_groups[0]
            else:
                new_whiteman_group = all_groups[0]
            
            # Atualizar o jogo
            locked_game.word_group = new_citizen_group
            locked_game.citizen_word = new_citizen_word
            locked_game.impostor_word = new_impostor_word
            locked_game.whiteman_word_group = new_whiteman_group
            locked_game.save()
            
            # Atualizar palavras de todos os jogadores ativos
            active_players = locked_game.players.filter(is_eliminated=False)
            for p in active_players:
                if p.role == 'citizen':
                    p.word = new_citizen_word
                    p.save(update_fields=['word'])
                elif p.role == 'impostor':
                    p.word = new_impostor_word
                    try:
                        p.impostor_knows_clown = True  # Revelar Palhaço ao impostor
                        p.save(update_fields=['word', 'impostor_knows_clown'])
                    except Exception:
                        p.save(update_fields=['word'])
                elif p.role == 'whiteman':
                    whiteman_words = list(new_whiteman_group.words.all())
                    if whiteman_words:
                        p.word = random.choice(whiteman_words)
                        p.save(update_fields=['word'])
                elif p.role == 'clown':
                    p.word = new_impostor_word
                    try:
                        p.palhaco_used_chaos_power = True
                        p.save(update_fields=['word', 'palhaco_used_chaos_power'])
                    except Exception:
                        p.save(update_fields=['word'])
            
        return JsonResponse({
            'success': True,
            'message': '🎭 CAOS! Todas as palavras foram embaralhadas! Os impostores agora sabem quem você é.',
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERRO CHAOS POWER: {error_trace}")
        return _json_error(f'Erro ao usar poder: {str(e)}', status=500)


@csrf_exempt
@require_http_methods(["POST"])
def restart_game_api(request, code):
    game = get_object_or_404(Game, code=code)
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _json_error('Dados inválidos')

    player = _validate_player_action(request, game, payload.get('player_name'))
    if not player:
        return _json_error('Não autorizado', status=403)
    if not player.is_creator:
        return _json_error('Apenas o criador pode reiniciar o jogo', status=403)

    with transaction.atomic():
        locked_game = Game.objects.select_for_update().get(id=game.id)
        for participant in locked_game.players.all():
            participant.is_eliminated = False
            participant.role = None
            participant.word_id = None
            participant.nudge_meter = 100
            participant.nudge_meter_round = 0
            participant.palhaco_known_impostors = []
            participant.palhaco_goal_state = ''
            participant.palhaco_goal_ready_round = 0
            participant.palhaco_used_chaos_power = False
            participant.impostor_knows_clown = False
            participant.save()
        Hint.objects.filter(game=locked_game).delete()
        Vote.objects.filter(game=locked_game).delete()
        Nudge.objects.filter(game=locked_game).delete()
        locked_game.status = 'waiting'
        locked_game.current_round = 0
        locked_game.current_player_index = 0
        locked_game.word_group_id = None
        locked_game.whiteman_word_group_id = None
        locked_game.citizen_word_id = None
        locked_game.impostor_word_id = None
        locked_game.started_at = None
        locked_game.finished_at = None
        locked_game.actual_num_impostors = 0
        locked_game.actual_num_whitemen = 0
        locked_game.actual_num_clowns = 0
        locked_game.winning_team = None
        locked_game.save()

    _reset_nudges_for_round(game, 0)

    return JsonResponse({'success': True})


@csrf_exempt
@require_http_methods(["POST"])
def close_room_api(request, code):
    game = get_object_or_404(Game, code=code)
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _json_error('Dados inválidos')

    player = _validate_player_action(request, game, payload.get('player_name'))
    if not player:
        return _json_error('Não autorizado', status=403)
    if not player.is_creator:
        return _json_error('Apenas o criador pode fechar a sala', status=403)

    game.delete()
    return JsonResponse({'room_closed': True, 'redirect': '/'})


@csrf_exempt
@require_http_methods(["POST"])
def kick_player_api(request, code):
    game = get_object_or_404(Game, code=code)
    if game.status not in ['waiting', 'configuring']:
        return _json_error('Não é possível remover jogadores após o início do jogo')
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _json_error('Dados inválidos')

    player = _validate_player_action(request, game, payload.get('player_name'))
    if not player:
        return _json_error('Não autorizado', status=403)
    if not player.is_creator:
        return _json_error('Apenas o criador pode remover jogadores', status=403)

    target_name = payload.get('target_player_name')
    if not target_name:
        return _json_error('Jogador alvo não especificado')
    if target_name == player.name:
        return _json_error('Você não pode se remover')

    with transaction.atomic():
        locked_game = Game.objects.select_for_update().get(id=game.id)
        try:
            target = Player.objects.get(game=locked_game, name=target_name)
            target.delete()
        except Player.DoesNotExist:
            return _json_error('Jogador não encontrado', status=404)

    return JsonResponse({'success': True})


@csrf_exempt
@require_http_methods(["POST"])
def nudge_player_api(request, code):
    game = get_object_or_404(Game, code=code)
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return _json_error('Dados inválidos')

    player = _validate_player_action(request, game, payload.get('player_name'))
    if not player:
        return _json_error('Não autorizado', status=403)

    if game.status != 'hints':
        return _json_error('Nudges só podem ser enviados durante a rodada de dicas', status=400)

    target_name = payload.get('target_player_name')
    if not target_name:
        return _json_error('Jogador alvo não especificado')

    try:
        target = Player.objects.get(game=game, name=target_name)
    except Player.DoesNotExist:
        return _json_error('Jogador alvo não encontrado', status=404)

    if target.name == player.name:
        return _json_error('Você não pode enviar nudge para si mesmo')

    one_second_ago = timezone.now() - timedelta(seconds=1)
    recent_nudge = (
        Nudge.objects.filter(game=game, from_player=player, to_player=target, created_at__gte=one_second_ago)
        .order_by('-created_at')
        .first()
    )
    if recent_nudge:
        return _json_error('Espere 1 segundo para enviar outro nudge para este jogador', status=429)

    _ensure_player_nudge_round(target, game.current_round)

    Nudge.objects.create(
        game=game,
        from_player=player,
        to_player=target,
        round_number=game.current_round
    )

    target.nudge_meter = max(0, target.nudge_meter - 1)
    target.save(update_fields=['nudge_meter'])

    skip_triggered = False
    if target.nudge_meter <= 0 and game.get_current_player() == target:
        skip_triggered = True
        _record_hint_and_progress(game, target, 'Zerei o HP... perdi minha vez!')

    return JsonResponse({
        'success': True,
        'nudge_meter': target.nudge_meter,
        'skip_triggered': skip_triggered
    })




