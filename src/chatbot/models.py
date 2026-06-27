from django.db import models
from django.conf import settings
import uuid


class ChatSession(models.Model):
    
    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column='id_usuario',
        related_name='chat_sessions'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    last_activity = models.DateTimeField(auto_now=True, verbose_name='Última Atividade')
    
    class Meta:
        db_table = 'chatbot_session'
        verbose_name = 'Sessão de Chat'
        verbose_name_plural = 'Sessões de Chat'
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['user', '-last_activity'], name='idx_session_user_activity'),
        ]
    
    def __str__(self):
        return f"Session {self.session_id} - {self.user.email}"


class ChatMessage(models.Model):
    
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('tool', 'Tool'),
    ]
    
    id_message = models.AutoField(primary_key=True, db_column='id_message')
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Sessão'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name='Papel')
    content = models.TextField(verbose_name='Conteúdo')
    tool_name = models.CharField(max_length=100, null=True, blank=True, verbose_name='Nome da Ferramenta')
    tool_parameters = models.JSONField(null=True, blank=True, verbose_name='Parâmetros da Ferramenta')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    
    class Meta:
        db_table = 'chatbot_message'
        verbose_name = 'Mensagem'
        verbose_name_plural = 'Mensagens'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at'], name='idx_message_session_time'),
        ]
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class FatoConsumoVinho(models.Model):
    
    id_fato_consumo = models.AutoField(db_column='IdFatoConsumo', primary_key=True)
    evento = models.CharField(db_column='Evento', max_length=1, verbose_name='Evento')
    data_consumo = models.DateField(db_column='DataConsumo', verbose_name='Data do Consumo')
    vinho = models.CharField(db_column='Vinho', max_length=300, verbose_name='Vinho')
    uva = models.CharField(db_column='Uva', max_length=300, blank=True, null=True, verbose_name='Uva')
    safra = models.IntegerField(db_column='Safra', blank=True, null=True, verbose_name='Safra')
    produtor = models.CharField(db_column='Produtor', max_length=300, blank=True, null=True, verbose_name='Produtor')
    cor = models.CharField(db_column='Cor', max_length=50, verbose_name='Cor')
    teor_acucar = models.CharField(db_column='TeorAcucar', max_length=50, blank=True, null=True, verbose_name='Teor de Açúcar')
    teor_alcoolico = models.CharField(db_column='TeorAlcoolico', max_length=10, blank=True, null=True, verbose_name='Teor Alcoólico')
    pais = models.CharField(db_column='Pais', max_length=100, blank=True, null=True, verbose_name='País')
    regiao = models.CharField(db_column='Regiao', max_length=300, blank=True, null=True, verbose_name='Região')
    opiniao = models.CharField(db_column='Opiniao', max_length=100, blank=True, null=True, verbose_name='Opinião')
    preco = models.DecimalField(db_column='Preco', max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='Preço')
    qtd = models.IntegerField(db_column='Qtd', default=1, verbose_name='Quantidade')
    qtd_otimo = models.IntegerField(db_column='QtdOtimo', blank=True, null=True, verbose_name='Quantidade Ótimo')
    total = models.DecimalField(db_column='Total', max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='Total')
    degustacao = models.IntegerField(db_column='Degustacao', blank=True, null=True, verbose_name='Degustação')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    
    class Meta:
        db_table = 'chatbot_fato_consumo_vinho'
        verbose_name = 'Fato Consumo Vinho'
        verbose_name_plural = 'Fatos Consumo Vinho'
        ordering = ['-data_consumo']
        indexes = [
            models.Index(fields=['data_consumo'], name='idx_fato_consumo_data'),
            models.Index(fields=['vinho'], name='idx_fato_consumo_vinho'),
            models.Index(fields=['pais'], name='idx_fato_consumo_pais'),
        ]
    
    def __str__(self):
        return f"{self.vinho} - {self.data_consumo}"
