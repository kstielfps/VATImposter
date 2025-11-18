from django.db import models
import secrets
import random
import hashlib


class WordGroup(models.Model):
    """Grupo de palavras similares"""
    name = models.CharField(max_length=100, blank=True, null=True, help_text="Nome opcional do grupo")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or f"Grupo {self.id}"

    class Meta:
        verbose_name = "Grupo de Palavras"
        verbose_name_plural = "Grupos de Palavras"


class Word(models.Model):
    """Palavra dentro de um grupo"""
    group = models.ForeignKey(WordGroup, on_delete=models.CASCADE, related_name='words')
    text = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.text} ({self.group})"

    class Meta:
        verbose_name = "Palavra"
        verbose_name_plural = "Palavras"


class Game(models.Model):
    """Sala de jogo"""
    STATUS_CHOICES = [
        ('waiting', 'Aguardando Jogadores'),
        ('configuring', 'Configurando'),
        ('hints', 'Rodada de Dicas'),
        ('voting', 'Votação'),
        ('finished', 'Finalizado'),
    ]

    code = models.CharField(max_length=6, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    creator = models.CharField(max_length=100)  # Nome do criador
    
    # Configurações
    num_impostors = models.IntegerField(default=1)  # Seleção do criador (máx configurável)
    num_whitemen = models.IntegerField(default=0)  # Seleção do criador (0-3)
    num_clowns = models.IntegerField(default=0)  # Palhaço (0-1)
    actual_num_impostors = models.IntegerField(default=0)  # Quantidade sorteada para a partida
    actual_num_whitemen = models.IntegerField(default=0)
    actual_num_clowns = models.IntegerField(default=0)
    max_players = models.IntegerField(default=12)
    min_players = models.IntegerField(default=4)
    winning_team = models.CharField(max_length=20, blank=True, null=True)
    
    # Palavras do jogo
    word_group = models.ForeignKey(WordGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='citizen_impostor_games')
    whiteman_word_group = models.ForeignKey(WordGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='whiteman_games')
    citizen_word = models.ForeignKey(Word, on_delete=models.SET_NULL, null=True, blank=True, related_name='citizen_games')
    impostor_word = models.ForeignKey(Word, on_delete=models.SET_NULL, null=True, blank=True, related_name='impostor_games')
    
    # Controle de rodadas
    current_round = models.IntegerField(default=0)  # 0 = não iniciado, 1-3 = rodadas de dicas, 4+ = rodadas após votação
    current_player_index = models.IntegerField(default=0)
    hint_timeout_seconds = models.IntegerField(default=30)
    
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    def generate_code(self):
        """Gera um código único de 6 caracteres"""
        while True:
            code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(6))
            if not Game.objects.filter(code=code).exists():
                return code

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()
        super().save(*args, **kwargs)

    def assign_roles(self):
        """Distribui os papéis (Impostor, WhiteMan, Cidadão)"""
        players = list(self.players.filter(is_eliminated=False).order_by('?'))

        if not players:
            return

        max_impostors = max(1, min(self.num_impostors, len(players)))
        effective_impostors = random.randint(1, max_impostors)
        self.actual_num_impostors = effective_impostors

        remaining_slots = len(players) - effective_impostors
        max_whitemen_allowed = max(0, min(self.num_whitemen, 3, remaining_slots))
        effective_whitemen = random.randint(0, max_whitemen_allowed) if max_whitemen_allowed > 0 else 0
        remaining_slots -= effective_whitemen

        effective_clowns = 0
        if self.num_clowns > 0 and len(players) >= 6 and remaining_slots > 0:
            effective_clowns = min(1, self.num_clowns, remaining_slots)
            remaining_slots -= effective_clowns

        self.actual_num_whitemen = effective_whitemen
        self.actual_num_clowns = effective_clowns
        self.winning_team = None
        self.save(update_fields=['actual_num_impostors', 'actual_num_whitemen', 'actual_num_clowns', 'winning_team'])

        def reset_clown_meta(p):
            p.palhaco_known_impostors = []
            p.palhaco_goal_state = ''
            p.palhaco_goal_ready_round = 0

        # Atribuir impostores
        impostors = players[:effective_impostors]
        for player in impostors:
            player.role = 'impostor'
            player.word = self.impostor_word
            reset_clown_meta(player)
            player.save()
        
        # Atribuir whitemen
        remaining = players[effective_impostors:]
        whitemen = remaining[:effective_whitemen]
        for player in whitemen:
            player.role = 'whiteman'
            if self.whiteman_word_group:
                whiteman_words = list(self.whiteman_word_group.words.all())
                if whiteman_words:
                    player.word = random.choice(whiteman_words)
            reset_clown_meta(player)
            player.save()
        
        remaining = remaining[effective_whitemen:]

        # Palhaço
        clowns = remaining[:effective_clowns]
        for player in clowns:
            player.role = 'clown'
            player.word = self.impostor_word
            player.palhaco_known_impostors = []
            player.palhaco_goal_state = 'finding'
            player.palhaco_goal_ready_round = 0
            player.save()

        remaining = remaining[effective_clowns:]

        # Resto são cidadãos
        citizens = remaining
        for player in citizens:
            player.role = 'citizen'
            player.word = self.citizen_word
            reset_clown_meta(player)
            player.save()

    def assign_words(self):
        """Atribui palavras do grupo escolhido"""
        if not self.word_group:
            # Escolher grupo aleatório para cidadãos/impostores
            groups = WordGroup.objects.filter(words__isnull=False).distinct()
            if not groups.exists():
                return False
            
            self.word_group = random.choice(list(groups))
            words = list(self.word_group.words.all())
            
            if len(words) < 2:
                return False
            
            # Escolher duas palavras diferentes para cidadãos e impostores
            self.citizen_word = random.choice(words)
            remaining = [w for w in words if w != self.citizen_word]
            self.impostor_word = random.choice(remaining) if remaining else self.citizen_word
            
            # Escolher grupo DIFERENTE para WhiteMan (se houver WhiteMan no jogo)
            if self.num_whitemen > 0:
                other_groups = groups.exclude(id=self.word_group.id)
                if other_groups.exists():
                    self.whiteman_word_group = random.choice(list(other_groups))
                else:
                    # Se não há grupos diferentes, usar o mesmo grupo (caso raro)
                    self.whiteman_word_group = self.word_group
            
            self.save()
        
        return True

    def validate_can_start(self):
        """Retorna (bool, mensagem) indicando se o jogo pode ser iniciado."""
        if self.status == 'waiting':
            total_players = self.players.count()
        else:
            total_players = self.players.filter(is_eliminated=False).count()

        if total_players < self.min_players:
            return False, f'São necessários pelo menos {self.min_players} jogadores para começar.'
        if total_players > self.max_players:
            return False, f'Limite máximo de {self.max_players} jogadores atingido.'
        if self.num_clowns > 0 and total_players < 6:
            return False, 'Palhaço só pode jogar com 6 ou mais jogadores.'
        return True, ''

    def can_start(self):
        valid, _ = self.validate_can_start()
        return valid

    def get_active_players(self):
        """Retorna jogadores ativos (não eliminados)"""
        return self.players.filter(is_eliminated=False).order_by('id')

    def get_current_player(self):
        """Retorna o jogador atual"""
        active_players = list(self.get_active_players())
        if active_players and 0 <= self.current_player_index < len(active_players):
            return active_players[self.current_player_index]
        return None

    def next_player(self):
        """Avança para o próximo jogador"""
        active_players = list(self.get_active_players())
        self.current_player_index = (self.current_player_index + 1) % len(active_players)
        self.save()

    def check_win_conditions(self):
        """Verifica condições de vitória"""
        active_players = list(self.get_active_players())
        impostors = [p for p in active_players if p.role == 'impostor']
        non_impostors = [p for p in active_players if p.role != 'impostor']
        
        if len(impostors) == 0:
            self.winning_team = 'citizens'
            return 'citizens'
        
        # Se sobram apenas 2 jogadores
        if len(active_players) == 2:
            if len(impostors) >= 1:
                self.winning_team = 'impostors'
                return 'impostors'
        
        return None

    def __str__(self):
        return f"Game {self.code} - {self.get_status_display()}"

    class Meta:
        verbose_name = "Jogo"
        verbose_name_plural = "Jogos"


class Player(models.Model):
    """Jogador em uma sala"""
    ROLE_CHOICES = [
        ('citizen', 'Cidadão'),
        ('impostor', 'Impostor'),
        ('whiteman', 'WhiteMan'),
        ('clown', 'Palhaço'),
    ]

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='players')
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, null=True, blank=True)
    word = models.ForeignKey(Word, on_delete=models.SET_NULL, null=True, blank=True)
    is_eliminated = models.BooleanField(default=False)
    is_creator = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    nudge_meter = models.IntegerField(default=100)
    nudge_meter_round = models.IntegerField(default=0)
    palhaco_known_impostors = models.JSONField(default=list, blank=True)
    palhaco_goal_state = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('', 'Sem Objetivo'),
            ('finding', 'Encontrando Impostor'),
            ('pending', 'Aguardando Atualização'),
            ('eliminate', 'Precisa ser Eliminado'),
        ],
        default='',
    )
    palhaco_goal_ready_round = models.IntegerField(default=0)
    palhaco_used_chaos_power = models.BooleanField(default=False)
    impostor_knows_clown = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.game.code})"

    class Meta:
        verbose_name = "Jogador"
        verbose_name_plural = "Jogadores"
        unique_together = [['game', 'name']]


class Hint(models.Model):
    """Dica dada por um jogador"""
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='hints')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='hints')
    round_number = models.IntegerField()
    word = models.CharField(max_length=100)  # A palavra da dica
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.player.name} - Rodada {self.round_number}: {self.word}"

    class Meta:
        verbose_name = "Dica"
        verbose_name_plural = "Dicas"
        unique_together = [['game', 'player', 'round_number']]


class Vote(models.Model):
    """Voto de um jogador"""
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='votes_cast')
    target = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='votes_received')
    round_number = models.IntegerField()
    is_palhaco_guess = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        label = 'Palpite' if self.is_palhaco_guess else 'Voto'
        return f"{label} - {self.voter.name} → {self.target.name} (Rodada {self.round_number})"

    class Meta:
        verbose_name = "Voto"
        verbose_name_plural = "Votos"
        unique_together = [['game', 'voter', 'round_number', 'is_palhaco_guess']]


class Nudge(models.Model):
    """Notificação de nudge/ping entre jogadores"""
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='nudges')
    from_player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='nudges_sent')
    to_player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='nudges_received')
    round_number = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged = models.BooleanField(default=False)  # Se o jogador já viu/ouviu o nudge

    def __str__(self):
        return f"{self.from_player.name} → {self.to_player.name}"

    class Meta:
        verbose_name = "Nudge"
        verbose_name_plural = "Nudges"



def sort_players_for_display(game_code, players):
    """Return players sorted in a deterministic but role-agnostic order."""
    player_list = list(players)

    def display_key(player):
        # Use a hash of game code and player id to shuffle order consistently per game
        raw = f"{game_code}-{player.id}".encode('utf-8')
        digest = hashlib.sha256(raw).hexdigest()
        return int(digest[:8], 16)

    player_list.sort(key=display_key)
    return player_list



