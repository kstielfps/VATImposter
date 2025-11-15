"""
Script para criar um superusuário do Django admin
Execute: python create_admin.py
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vatimposter.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def create_superuser():
    username = input("Username (leave blank to use 'admin'): ").strip()
    if not username:
        username = 'admin'
    
    email = input("Email address (optional): ").strip()
    
    password = None
    while not password:
        password = input("Password: ").strip()
        if not password:
            print("Password cannot be blank!")
        elif len(password) < 8:
            print("Password must be at least 8 characters long!")
            password = None
    
    password_confirm = input("Password (again): ").strip()
    
    if password != password_confirm:
        print("Error: Passwords don't match!")
        return
    
    # Verificar se o usuário já existe
    if User.objects.filter(username=username).exists():
        print(f"Error: User '{username}' already exists!")
        return
    
    # Criar superusuário
    try:
        User.objects.create_superuser(
            username=username,
            email=email if email else '',
            password=password
        )
        print(f"\n✓ Superuser '{username}' created successfully!")
        print(f"\nYou can now login at: http://localhost:8000/admin")
    except Exception as e:
        print(f"Error creating superuser: {e}")

if __name__ == '__main__':
    create_superuser()

