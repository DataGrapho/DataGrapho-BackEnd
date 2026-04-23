from django.test import TestCase
from catalogo_depara.entity import CatalogoDePara
from depara.entity import DePara
from depara.service import DeparaService


class DeparaModelTest(TestCase):
    """
    Tests for DePara model.
    """
    
    def setUp(self):
        """Set up test data."""
        self.catalog = CatalogoDePara.objects.create(
            tabela_origem='test_table',
            descricao='Test Catalog'
        )
        
        self.depara = DePara.objects.create(
            id_catalogo=self.catalog,
            codigo_origem='ORIG_001',
            descricao_origem='Origin Code 001',
            codigo_destino='DEST_001',
            descricao_destino='Destination Code 001',
            ativo=True
        )

    def test_depara_creation(self):
        """Test if depara is created correctly."""
        self.assertEqual(self.depara.codigo_origem, 'ORIG_001')
        self.assertEqual(self.depara.codigo_destino, 'DEST_001')
        self.assertTrue(self.depara.ativo)

    def test_depara_string_representation(self):
        expected = f'{self.depara.codigo_origem} -> {self.depara.codigo_destino}'
        self.assertEqual(str(self.depara), expected)

    def test_depara_foreign_key(self):
        self.assertEqual(self.depara.id_catalogo.id_catalogo, self.catalog.id_catalogo)

    def test_unique_constraint(self):
        with self.assertRaises(Exception):
            DePara.objects.create(
                id_catalogo=self.catalog,
                codigo_origem='ORIG_001',
                codigo_destino='DEST_001',
                ativo=True
            )


class DeparaServiceTest(TestCase):

    def setUp(self):
        self.service = DeparaService()
        
        self.catalog = CatalogoDePara.objects.create(
            tabela_origem='test_table',
            descricao='Test Catalog'
        )

    def test_create_depara_success(self):
        data = {
            'id_catalogo': self.catalog,
            'codigo_origem': 'ORIG_001',
            'codigo_destino': 'DEST_001',
            'ativo': True
        }
        
        depara = self.service.create_depara(data)
        
        self.assertEqual(depara.codigo_origem, 'ORIG_001')
        self.assertTrue(depara.ativo)

    def test_create_depara_missing_required_field(self):
        data = {
            'codigo_origem': 'ORIG_001',
            'codigo_destino': 'DEST_001'
        }
        
        with self.assertRaises(ValueError):
            self.service.create_depara(data)

    def test_create_depara_duplicate_mapping(self):
        data = {
            'id_catalogo': self.catalog,
            'codigo_origem': 'ORIG_001',
            'codigo_destino': 'DEST_001'
        }
        
        self.service.create_depara(data)
        
        with self.assertRaises(ValueError):
            self.service.create_depara(data)

    def test_list_depara(self):
        DePara.objects.create(
            id_catalogo=self.catalog,
            codigo_origem='ORIG_001',
            codigo_destino='DEST_001'
        )
        DePara.objects.create(
            id_catalogo=self.catalog,
            codigo_origem='ORIG_002',
            codigo_destino='DEST_002'
        )
        
        depara_list = self.service.list_depara()
        
        self.assertEqual(len(depara_list), 2)

    def test_get_depara_by_id(self):
        depara = DePara.objects.create(
            id_catalogo=self.catalog,
            codigo_origem='ORIG_001',
            codigo_destino='DEST_001'
        )
        
        retrieved = self.service.get_depara_by_id(depara.id_depara)
        
        self.assertEqual(retrieved.id_depara, depara.id_depara)

    def test_update_depara(self):
        depara = DePara.objects.create(
            id_catalogo=self.catalog,
            codigo_origem='ORIG_001',
            codigo_destino='DEST_001'
        )
        
        updated = self.service.update_depara(
            depara.id_depara,
            {'descricao_origem': 'Updated origin description'}
        )
        
        self.assertEqual(updated.descricao_origem, 'Updated origin description')

    def test_delete_depara(self):
        depara = DePara.objects.create(
            id_catalogo=self.catalog,
            codigo_origem='ORIG_001',
            codigo_destino='DEST_001'
        )
        
        deleted = self.service.delete_depara(depara.id_depara)
        
        self.assertTrue(deleted)
        self.assertIsNone(self.service.get_depara_by_id(depara.id_depara))

    def test_get_by_catalogo(self):
        DePara.objects.create(
            id_catalogo=self.catalog,
            codigo_origem='ORIG_001',
            codigo_destino='DEST_001'
        )
        DePara.objects.create(
            id_catalogo=self.catalog,
            codigo_origem='ORIG_002',
            codigo_destino='DEST_002'
        )
        
        depara_list = self.service.get_by_catalogo(self.catalog.id_catalogo)
        
        self.assertEqual(len(depara_list), 2)

    def test_activate_deactivate_depara(self):
        depara = DePara.objects.create(
            id_catalogo=self.catalog,
            codigo_origem='ORIG_001',
            codigo_destino='DEST_001',
            ativo=True
        )
        
        deactivated = self.service.deactivate_depara(depara.id_depara)
        self.assertFalse(deactivated.ativo)
        
        activated = self.service.activate_depara(depara.id_depara)
        self.assertTrue(activated.ativo)
