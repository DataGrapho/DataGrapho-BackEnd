#!/usr/bin/env python
"""Teste simples para verificar o erro do chatbot"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app/src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'datagrapho.settings')
django.setup()

print("=" * 60)
print("TESTE SIMPLES DO CHATBOT")
print("=" * 60)

# Test 1: Verificar se as tools carregaram
from chatbot.core.tool_registry import get_tool_registry
registry = get_tool_registry()
tools = registry.get_all_tools()
print(f"\n1. Tools carregadas: {len(tools)}")
for tool in tools:
    print(f"   - {tool.name}")

# Test 2: Verificar se o provider funciona
try:
    from chatbot.core.ai_providers import get_ai_provider
    provider = get_ai_provider()
    print(f"\n2. Provider inicializado: {provider.__class__.__name__}")
    print(f"   Modelo: {provider.model}")
except Exception as e:
    print(f"\n2. ERRO ao inicializar provider: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Verificar se o engine funciona
try:
    from chatbot.core.engine import FunctionCallingEngine
    engine = FunctionCallingEngine()
    print(f"\n3. Engine inicializado")
    print(f"   Repositórios: {list(engine.repositories.keys())}")
except Exception as e:
    print(f"\n3. ERRO ao inicializar engine: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Tentar processar uma mensagem simples
try:
    from chatbot.service import ChatbotService
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    user = User.objects.first()
    
    if user:
        print(f"\n4. Testando mensagem com usuário: {user.email}")
        service = ChatbotService()
        
        result = service.process_chat(
            user_id=user.pk,
            message="Olá",
            session_id=None
        )
        
        print("   SUCESSO!")
        print(f"   Resposta: {result['response'][:100]}...")
    else:
        print("\n4. Nenhum usuário encontrado no banco")
        
except Exception as e:
    print(f"\n4. ERRO ao processar mensagem: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
