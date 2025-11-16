from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth import get_user_model
import json
import traceback
import os
import logging
from .models import Game, Player

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
        'players': game.players.all(),
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



