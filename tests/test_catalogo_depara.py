from django.test import TestCase

from catalogo_depara.models import CatalogoDePara
from catalogo_depara.service import CatalogoDeparaService


class CatalogoDeparaModelTest(TestCase):
    
    def setUp(self):
        self.catalog = CatalogoDePara.objects.create(
            tabela_origem='teste_table',
            descricao='Test Description',
            ativo=True
        )

    def test_catalog_creation(self):
        self.assertEqual(self.catalog.tabela_origem, 'teste_table')
        self.assertEqual(self.catalog.descricao, 'Test Description')
        self.assertTrue(self.catalog.ativo)

    def test_catalog_string_representation(self):
        """Test __str__ method."""
        expected = f'{self.catalog.tabela_origem} - {self.catalog.descricao}'
        self.assertEqual(str(self.catalog), expected)

    def test_catalog_ordering(self):
        CatalogoDePara.objects.create(
            tabela_origem='another_table',
            descricao='Another Description'
        )
        
        catalogs = CatalogoDePara.objects.all()
        self.assertEqual(catalogs[0].tabela_origem, 'another_table')


class CatalogoDeparaServiceTest(TestCase):
    
    def setUp(self):
        self.service = CatalogoDeparaService()

    def test_create_catalog_success(self):
        data = {
            'tabela_origem': 'test_table',
            'descricao': 'Test catalog',
            'ativo': True
        }
        
        catalog = self.service.create_catalogo(data)
        
        self.assertEqual(catalog.tabela_origem, 'test_table')
        self.assertTrue(catalog.ativo)

    def test_create_catalog_missing_required_field(self):
        data = {
            'descricao': 'Test catalog'
        }
        
        with self.assertRaises(ValueError):
            self.service.create_catalogo(data)

    def test_list_catalogs(self):
        CatalogoDePara.objects.create(
            tabela_origem='table1',
            descricao='Desc 1'
        )
        CatalogoDePara.objects.create(
            tabela_origem='table2',
            descricao='Desc 2'
        )
        
        catalogs = self.service.list_catalogos()
        
        self.assertEqual(len(catalogs), 2)

    def test_get_catalog_by_id(self):
        """Test getting catalog by ID."""
        catalog = CatalogoDePara.objects.create(
            tabela_origem='test_table',
            descricao='Test'
        )
        
        retrieved = self.service.get_catalogo_by_id(catalog.id_catalogo)
        
        self.assertEqual(retrieved.id_catalogo, catalog.id_catalogo)

    def test_update_catalog(self):
        catalog = CatalogoDePara.objects.create(
            tabela_origem='old_table',
            descricao='Old description'
        )
        
        updated = self.service.update_catalogo(
            catalog.id_catalogo,
            {'descricao': 'New description'}
        )
        
        self.assertEqual(updated.descricao, 'New description')

    def test_delete_catalog(self):
        catalog = CatalogoDePara.objects.create(
            tabela_origem='test_table',
            descricao='Test'
        )
        
        deleted = self.service.delete_catalogo(catalog.id_catalogo)
        
        self.assertTrue(deleted)
        self.assertIsNone(self.service.get_catalogo_by_id(catalog.id_catalogo))

    def test_activate_deactivate_catalog(self):
        catalog = CatalogoDePara.objects.create(
            tabela_origem='test_table',
            ativo=True
        )
        
        # Deactivate
        deactivated = self.service.deactivate_catalogo(catalog.id_catalogo)
        self.assertFalse(deactivated.ativo)
        
        # Activate
        activated = self.service.activate_catalogo(catalog.id_catalogo)
        self.assertTrue(activated.ativo)
