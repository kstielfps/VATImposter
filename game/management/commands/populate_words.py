from django.core.management.base import BaseCommand
from game.models import WordGroup, Word


class Command(BaseCommand):
    help = 'Popula o banco de dados com grupos de palavras de exemplo'

    def handle(self, *args, **options):
        # Grupo 1: Água
        group1, created = WordGroup.objects.get_or_create(name="Grupo Água")
        if created:
            Word.objects.get_or_create(group=group1, text="Água")
            Word.objects.get_or_create(group=group1, text="Molhado")
            Word.objects.get_or_create(group=group1, text="Chuva")
            Word.objects.get_or_create(group=group1, text="Rio")
            self.stdout.write(self.style.SUCCESS(f'Criado grupo: {group1.name}'))

        # Grupo 2: Construções Altas
        group2, created = WordGroup.objects.get_or_create(name="Grupo Construções")
        if created:
            Word.objects.get_or_create(group=group2, text="Torre")
            Word.objects.get_or_create(group=group2, text="Prédio")
            Word.objects.get_or_create(group=group2, text="Alto")
            self.stdout.write(self.style.SUCCESS(f'Criado grupo: {group2.name}'))

        # Grupo 3: Animais
        group3, created = WordGroup.objects.get_or_create(name="Grupo Animais")
        if created:
            Word.objects.get_or_create(group=group3, text="Cachorro")
            Word.objects.get_or_create(group=group3, text="Gato")
            Word.objects.get_or_create(group=group3, text="Animal")
            Word.objects.get_or_create(group=group3, text="Pet")
            self.stdout.write(self.style.SUCCESS(f'Criado grupo: {group3.name}'))

        # Grupo 4: Comida
        group4, created = WordGroup.objects.get_or_create(name="Grupo Comida")
        if created:
            Word.objects.get_or_create(group=group4, text="Pizza")
            Word.objects.get_or_create(group=group4, text="Hambúrguer")
            Word.objects.get_or_create(group=group4, text="Comida")
            Word.objects.get_or_create(group=group4, text="Refeição")
            self.stdout.write(self.style.SUCCESS(f'Criado grupo: {group4.name}'))

        # Grupo 5: Transporte
        group5, created = WordGroup.objects.get_or_create(name="Grupo Transporte")
        if created:
            Word.objects.get_or_create(group=group5, text="Carro")
            Word.objects.get_or_create(group=group5, text="Ônibus")
            Word.objects.get_or_create(group=group5, text="Veículo")
            self.stdout.write(self.style.SUCCESS(f'Criado grupo: {group5.name}'))

        self.stdout.write(self.style.SUCCESS('\nPalavras populadas com sucesso!'))



