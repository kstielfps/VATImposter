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
from .models import Game, Player, Hint, Vote, Nudge, sort_players_for_display

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
            
            # Validações
            if num_impostors < 1 or num_impostors > 2:
                return JsonResponse({'error': 'Número de impostores deve ser entre 1 e 2'}, status=400)
            
            if num_whitemen < 0 or num_whitemen > 3:
                return JsonResponse({'error': 'Número de whitemen deve ser entre 0 e 3'}, status=400)
            
            # Criar jogo
            game = Game.objects.create(
                creator=creator_name,
                num_impostors=num_impostors,
                num_whitemen=num_whitemen,
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
    players_qs = game.players.select_related('word').all()
    players_list = sort_players_for_display(game.code, players_qs)
    players_data = []
    for player in players_list:
        word_text = None
        role_value = None
        if not is_spectator:
            if player.role == 'whiteman' and not player.is_eliminated:
                role_value = 'citizen'
            else:
                role_value = player.role
            if player.word:
                word_text = player.word.text
        players_data.append({
            'id': player.id,
            'name': player.name,
            'is_eliminated': player.is_eliminated,
            'is_creator': player.is_creator,
            'role': role_value,
            'word': word_text,
            'nudge_meter': player.nudge_meter,
            'nudge_meter_round': player.nudge_meter_round,
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

    current_round_votes = Vote.objects.filter(game=game, round_number=game.current_round)
    votes_data = [
        {
            'voter_name': vote.voter.name,
            'target_name': vote.target.name,
        }
        for vote in current_round_votes.select_related('voter', 'target')
    ]

    vote_history = {}
    for vote in Vote.objects.filter(game=game).select_related('voter', 'target').order_by('round_number', 'created_at'):
        vote_history.setdefault(vote.round_number, []).append({
            'voter_name': vote.voter.name,
            'target_name': vote.target.name,
        })

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
        'citizen_word': None,
        'impostor_word': None,
        'nudge_meter_max': 100,
    }

    if not is_spectator:
        game_data['citizen_word'] = game.citizen_word.text if game.citizen_word else None
        game_data['impostor_word'] = game.impostor_word.text if game.impostor_word else None
        if game.status == 'finished':
            game_data['actual_num_impostors'] = game.actual_num_impostors
            game_data['actual_num_whitemen'] = game.actual_num_whitemen

    return {
        'game': game_data,
        'players': players_data,
        'hints': hints_data,
        'votes': votes_data,
        'vote_history': vote_history,
        'nudges': nudges_data,
    }


def _process_voting(game):
    vote_count = {}
    votes = list(
        Vote.objects.filter(game=game, round_number=game.current_round)
        .select_related('target')
    )
    for vote in votes:
        target_id = vote.target.id
        vote_count[target_id] = vote_count.get(target_id, 0) + 1

    if vote_count:
        max_votes = max(vote_count.values())
        most_voted_ids = [pid for pid, count in vote_count.items() if count == max_votes]
        if len(most_voted_ids) == 1:
            eliminated_player = Player.objects.get(id=most_voted_ids[0])
            if not eliminated_player.is_eliminated:
                eliminated_player.is_eliminated = True
                eliminated_player.save()

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
    if not game.can_start():
        return _json_error('Número mínimo de jogadores não atingido')
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
    if player.is_eliminated:
        return _json_error('Jogador eliminado não vota')

    target_name = payload.get('target_name')
    if not target_name:
        return _json_error('Jogador alvo é obrigatório')

    try:
        target = Player.objects.get(game=game, name=target_name)
    except Player.DoesNotExist:
        return _json_error('Jogador alvo não encontrado')

    if Vote.objects.filter(game=game, voter=player, round_number=game.current_round).exists():
        return _json_error('Você já votou nesta rodada')

    Vote.objects.create(game=game, voter=player, target=target, round_number=game.current_round)

    active_players = list(game.get_active_players())
    votes_count = Vote.objects.filter(game=game, round_number=game.current_round).count()
    if votes_count >= len(active_players):
        _process_voting(game)

    return JsonResponse({'success': True})


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




