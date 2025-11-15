from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path
from django.contrib import messages
import csv
import io
from .models import WordGroup, Word, Game, Player, Hint, Vote
from .admin_forms import CSVImportForm


class WordInline(admin.TabularInline):
    model = Word
    extra = 1


@admin.register(WordGroup)
class WordGroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'word_count', 'created_at']
    search_fields = ['name']
    inlines = [WordInline]
    change_list_template = 'admin/game/wordgroup/change_list.html'
    
    def word_count(self, obj):
        return obj.words.count()
    word_count.short_description = 'Número de Palavras'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.import_csv, name='game_wordgroup_import_csv'),
        ]
        return custom_urls + urls
    
    def import_csv(self, request):
        """View para importar palavras via CSV"""
        if request.method == 'POST':
            form = CSVImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data['csv_file']
                
                # Ler o arquivo CSV
                try:
                    # Decodificar o arquivo
                    file_data = csv_file.read().decode('utf-8')
                    csv_reader = csv.reader(io.StringIO(file_data))
                    
                    groups_created = 0
                    words_created = 0
                    errors = []
                    
                    for row_num, row in enumerate(csv_reader, start=1):
                        # Pular linhas vazias
                        if not row or all(not cell.strip() for cell in row):
                            continue
                        
                        # Remover espaços em branco e filtrar células vazias
                        words_in_row = [word.strip() for word in row if word.strip()]
                        
                        if len(words_in_row) < 2:
                            errors.append(f'Linha {row_num}: Precisa de pelo menos 2 palavras (encontradas: {len(words_in_row)})')
                            continue
                        
                        # Criar grupo (usar primeira palavra como nome se não houver nome)
                        group_name = words_in_row[0] if len(words_in_row) > 0 else None
                        group, created = WordGroup.objects.get_or_create(
                            name=group_name,
                            defaults={'name': group_name}
                        )
                        
                        if created:
                            groups_created += 1
                        
                        # Criar palavras do grupo
                        for word_text in words_in_row:
                            word_text = word_text.strip()
                            if word_text:
                                word, word_created = Word.objects.get_or_create(
                                    group=group,
                                    text=word_text,
                                    defaults={'text': word_text}
                                )
                                if word_created:
                                    words_created += 1
                    
                    # Mensagens de sucesso
                    if groups_created > 0 or words_created > 0:
                        messages.success(
                            request,
                            f'Importação concluída! {groups_created} grupo(s) criado(s), {words_created} palavra(s) adicionada(s).'
                        )
                    
                    if errors:
                        for error in errors:
                            messages.warning(request, error)
                    
                    return redirect('..')
                    
                except Exception as e:
                    messages.error(request, f'Erro ao processar arquivo CSV: {str(e)}')
        else:
            form = CSVImportForm()
        
        context = {
            'form': form,
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
        }
        return render(request, 'admin/game/wordgroup/import_csv.html', context)


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

