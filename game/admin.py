from django.contrib import admin
from .models import WordGroup, Word, Game, Player, Hint, Vote


class WordInline(admin.TabularInline):
    model = Word
    extra = 1


@admin.register(WordGroup)
class WordGroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'word_count', 'created_at']
    search_fields = ['name']
    inlines = [WordInline]
    
    def word_count(self, obj):
        return obj.words.count()
    word_count.short_description = 'Número de Palavras'


@admin.register(Word)
class WordAdmin(admin.ModelAdmin):
    list_display = ['text', 'group']
    list_filter = ['group']
    search_fields = ['text']


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['code', 'status', 'creator', 'num_impostors', 'num_whitemen', 'current_round', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['code', 'creator']
    readonly_fields = ['code', 'created_at', 'started_at', 'finished_at']


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['name', 'game', 'role', 'is_eliminated', 'is_creator']
    list_filter = ['role', 'is_eliminated', 'is_creator']
    search_fields = ['name', 'game__code']


@admin.register(Hint)
class HintAdmin(admin.ModelAdmin):
    list_display = ['player', 'game', 'round_number', 'word', 'created_at']
    list_filter = ['round_number', 'created_at']
    search_fields = ['player__name', 'word']


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ['voter', 'target', 'game', 'round_number', 'created_at']
    list_filter = ['round_number', 'created_at']
    search_fields = ['voter__name', 'target__name']

