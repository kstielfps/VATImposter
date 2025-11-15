from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Game, Player


def home(request):
    """Página inicial"""
    return render(request, 'game/home.html')


@csrf_exempt
@require_http_methods(["GET", "POST"])
def create_game(request):
    """Criar uma nova sala de jogo"""
    if request.method == 'POST':
        data = json.loads(request.body)
        creator_name = data.get('creator_name', '').strip()
        num_impostors = int(data.get('num_impostors', 1))
        num_whitemen = int(data.get('num_whitemen', 0))
        
        # Validações
        if not creator_name:
            return JsonResponse({'error': 'Nome é obrigatório'}, status=400)
        
        if num_impostors < 1 or num_impostors > 2:
            return JsonResponse({'error': 'Número de impostores deve ser entre 1 e 2'}, status=400)
        
        if num_whitemen < 0 or num_whitemen > 2:
            return JsonResponse({'error': 'Número de whitemen deve ser entre 0 e 2'}, status=400)
        
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
        
        return JsonResponse({
            'code': game.code,
            'redirect': f'/game/{game.code}/'
        })
    
    return render(request, 'game/create.html')


@csrf_exempt
@require_http_methods(["GET", "POST"])
def join_game(request):
    """Entrar em uma sala existente"""
    if request.method == 'POST':
        data = json.loads(request.body)
        code = data.get('code', '').strip().upper()
        player_name = data.get('player_name', '').strip()
        
        if not code or not player_name:
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
        
        return JsonResponse({
            'code': game.code,
            'redirect': f'/game/{game.code}/'
        })
    
    return render(request, 'game/join.html')


def game_room(request, code):
    """Sala do jogo"""
    game = get_object_or_404(Game, code=code)
    player_name = request.GET.get('name', '')
    
    # Verificar se o jogador existe
    player = None
    if player_name:
        try:
            player = Player.objects.get(game=game, name=player_name)
        except Player.DoesNotExist:
            pass
    
    context = {
        'game': game,
        'player': player,
        'players': game.players.all(),
    }
    
    return render(request, 'game/room.html', context)



