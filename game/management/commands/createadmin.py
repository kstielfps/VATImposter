from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Cria um superusuário para o admin'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username do superusuário')
        parser.add_argument('--email', type=str, default='', help='Email do superusuário')
        parser.add_argument('--password', type=str, help='Senha do superusuário')
        parser.add_argument('--noinput', action='store_true', help='Não solicitar entrada do usuário')

    def handle(self, *args, **options):
        username = options.get('username')
        email = options.get('email', '')
        password = options.get('password')
        noinput = options.get('noinput', False)

        if not username:
            if noinput:
                username = 'admin'
            else:
                username = input("Username (leave blank to use 'admin'): ").strip()
                if not username:
                    username = 'admin'

        if not password:
            if noinput:
                password = 'admin123'  # Senha padrão apenas para desenvolvimento
                self.stdout.write(self.style.WARNING('Using default password: admin123'))
            else:
                password = input("Password: ").strip()
                if not password:
                    self.stdout.write(self.style.ERROR('Password cannot be blank!'))
                    return

        if not email and not noinput:
            email = input("Email address (optional): ").strip()

        # Verificar se o usuário já existe
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f"Error: User '{username}' already exists!"))
            return

        # Criar superusuário
        try:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f"\nSuperuser '{username}' created successfully!"))
            self.stdout.write(self.style.SUCCESS(f"\nYou can now login at: http://localhost:8000/admin"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating superuser: {e}"))

