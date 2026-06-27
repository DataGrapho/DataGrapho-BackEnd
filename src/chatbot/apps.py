from django.apps import AppConfig


class ChatbotConfig(AppConfig):
    
    default_auto_field = 'django.db.models.AutoField'
    name = 'chatbot'
    verbose_name = 'Chatbot Assistente'
    
    def ready(self):
        """Initialize chatbot when Django starts."""
        # Load tools from active domains
        from chatbot.core.tool_registry import get_tool_registry
        from chatbot.core.domain_loader import load_active_domains
        
        registry = get_tool_registry()
        load_active_domains(registry)
