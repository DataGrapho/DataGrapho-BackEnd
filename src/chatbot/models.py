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
    title = models.CharField(max_length=120, default='Novo chat')
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


class WineCountry(models.Model):
    """País de origem usado pelo catálogo relacional de vinhos."""

    name = models.CharField(max_length=100, unique=True, verbose_name='País')
    iso_code = models.CharField(max_length=2, unique=True, verbose_name='Código ISO')

    class Meta:
        db_table = 'chatbot_wine_country'
        ordering = ['name']

    def __str__(self):
        return self.name


class WineRegion(models.Model):
    """Região vinícola pertencente a um país."""

    name = models.CharField(max_length=150, verbose_name='Região')
    country = models.ForeignKey(WineCountry, on_delete=models.PROTECT, related_name='regions')
    climate = models.CharField(max_length=120, blank=True, verbose_name='Clima')

    class Meta:
        db_table = 'chatbot_wine_region'
        ordering = ['country__name', 'name']
        constraints = [
            models.UniqueConstraint(fields=['country', 'name'], name='uq_wine_region_country_name'),
        ]

    def __str__(self):
        return f'{self.name}, {self.country.name}'


class WineProducer(models.Model):
    """Vinícola ou produtor associado a uma região."""

    name = models.CharField(max_length=180, unique=True, verbose_name='Produtor')
    region = models.ForeignKey(WineRegion, on_delete=models.PROTECT, related_name='producers')
    founded_year = models.PositiveSmallIntegerField(blank=True, null=True)
    website = models.URLField(blank=True)

    class Meta:
        db_table = 'chatbot_wine_producer'
        ordering = ['name']

    def __str__(self):
        return self.name


class GrapeVariety(models.Model):
    """Variedade de uva que pode compor vários vinhos."""

    COLOR_CHOICES = [('tinta', 'Tinta'), ('branca', 'Branca'), ('rosa', 'Rosada')]
    name = models.CharField(max_length=120, unique=True, verbose_name='Uva')
    color = models.CharField(max_length=10, choices=COLOR_CHOICES)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'chatbot_grape_variety'
        ordering = ['name']

    def __str__(self):
        return self.name


class Wine(models.Model):
    """Produto central do catálogo, separado dos eventos históricos de consumo."""

    COLOR_CHOICES = [
        ('tinto', 'Tinto'), ('branco', 'Branco'), ('rose', 'Rosé'),
        ('espumante', 'Espumante'),
    ]
    SWEETNESS_CHOICES = [
        ('seco', 'Seco'), ('meio_seco', 'Meio seco'),
        ('suave', 'Suave'), ('doce', 'Doce'),
    ]

    name = models.CharField(max_length=200, verbose_name='Vinho')
    producer = models.ForeignKey(WineProducer, on_delete=models.PROTECT, related_name='wines')
    grapes = models.ManyToManyField(GrapeVariety, through='WineGrape', related_name='wines')
    color = models.CharField(max_length=12, choices=COLOR_CHOICES)
    sweetness = models.CharField(max_length=12, choices=SWEETNESS_CHOICES)
    alcohol_percentage = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    is_demo = models.BooleanField(
        default=False,
        help_text='Indica que o registro foi criado apenas para testes.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chatbot_wine'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['producer', 'name'], name='uq_wine_producer_name'),
        ]
        indexes = [
            models.Index(fields=['name'], name='idx_wine_name'),
            models.Index(fields=['color', 'sweetness'], name='idx_wine_style'),
        ]

    def __str__(self):
        return self.name


class WineGrape(models.Model):
    """Composição de uvas de um vinho (relação muitos-para-muitos)."""

    wine = models.ForeignKey(Wine, on_delete=models.CASCADE, related_name='grape_links')
    grape = models.ForeignKey(GrapeVariety, on_delete=models.PROTECT, related_name='wine_links')
    percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = 'chatbot_wine_grape'
        constraints = [
            models.UniqueConstraint(fields=['wine', 'grape'], name='uq_wine_grape'),
            models.CheckConstraint(
                condition=(models.Q(percentage__isnull=True) | (
                    models.Q(percentage__gte=0) & models.Q(percentage__lte=100)
                )),
                name='ck_wine_grape_percentage',
            ),
        ]

    def __str__(self):
        return f'{self.wine.name} - {self.grape.name}'


class WineOffer(models.Model):
    """Safra, preço e estoque atuais de um vinho."""

    wine = models.ForeignKey(Wine, on_delete=models.CASCADE, related_name='offers')
    vintage_year = models.PositiveSmallIntegerField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='BRL')
    stock = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chatbot_wine_offer'
        ordering = ['price']
        constraints = [
            models.UniqueConstraint(fields=['wine', 'vintage_year'], name='uq_wine_offer_vintage'),
            models.CheckConstraint(condition=models.Q(price__gte=0), name='ck_wine_offer_price'),
        ]
        indexes = [models.Index(fields=['active', 'price'], name='idx_wine_offer_price')]

    def __str__(self):
        vintage = self.vintage_year or 'sem safra'
        return f'{self.wine.name} ({vintage}) - {self.currency} {self.price}'


class WineReview(models.Model):
    """Avaliação editorial ou de cliente associada ao vinho."""

    wine = models.ForeignKey(Wine, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.CharField(max_length=120)
    score = models.DecimalField(max_digits=2, decimal_places=1)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chatbot_wine_review'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(score__gte=0) & models.Q(score__lte=5),
                name='ck_wine_review_score',
            ),
        ]
        indexes = [models.Index(fields=['wine', '-score'], name='idx_wine_review_score')]

    def __str__(self):
        return f'{self.wine.name} - {self.score}/5'


class WineConsumption(models.Model):
    """Evento histórico ligado ao vinho normalizado do catálogo."""

    wine = models.ForeignKey(Wine, on_delete=models.PROTECT, related_name='consumptions')
    event_type = models.CharField(max_length=20, default='consumo')
    consumed_at = models.DateField(verbose_name='Data do consumo')
    vintage_year = models.PositiveSmallIntegerField(blank=True, null=True)
    opinion = models.CharField(max_length=100, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    optimal_quantity = models.PositiveIntegerField(blank=True, null=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    tasting_score = models.PositiveSmallIntegerField(blank=True, null=True)
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chatbot_wine_consumption'
        ordering = ['-consumed_at']
        indexes = [
            models.Index(fields=['consumed_at'], name='idx_wine_consumed_at'),
            models.Index(fields=['wine', '-consumed_at'], name='idx_wine_consumption'),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name='ck_consumption_quantity'),
            models.CheckConstraint(
                condition=models.Q(unit_price__isnull=True) | models.Q(unit_price__gte=0),
                name='ck_consumption_unit_price',
            ),
        ]

    def __str__(self):
        return f'{self.wine.name} - {self.consumed_at}'
