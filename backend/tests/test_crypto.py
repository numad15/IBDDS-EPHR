"""
Unit tests for cryptography modules.
Tests IBE encryption/decryption, Shamir secret sharing, and threshold decryption.
"""

import pytest
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.crypto.identity_based_encryption import IdentityBasedEncryption, IBECiphertext
from src.crypto.shamir_secret_sharing import ShamirSecretSharing
from src.crypto.distributed_decryption import DecryptionCoordinator


class TestIBE:
    """Tests for Identity-Based Encryption."""

    def setup_method(self):
        self.ibe = IdentityBasedEncryption()
        self.params, self.master_secret = self.ibe.setup()

    def test_setup_generates_params(self):
        assert self.params is not None
        assert self.master_secret is not None
        assert self.params.master_public_key is not None

    def test_extract_key(self):
        key = self.ibe.extract_key("test@example.com")
        assert key is not None
        assert key.identity == "test@example.com"
        assert len(key.key_data) == 32

    def test_same_identity_same_key(self):
        key1 = self.ibe.extract_key("patient@hospital.com")
        key2 = self.ibe.extract_key("patient@hospital.com")
        assert key1.key_data == key2.key_data

    def test_different_identity_different_key(self):
        key1 = self.ibe.extract_key("alice@example.com")
        key2 = self.ibe.extract_key("bob@example.com")
        assert key1.key_data != key2.key_data

    def test_encrypt_decrypt_roundtrip(self):
        identity = "patient@hospital.com"
        private_key = self.ibe.extract_key(identity)
        
        plaintext = "Hello, this is a health record!"
        ciphertext = self.ibe.encrypt_with_key(private_key, plaintext)
        
        decrypted = self.ibe.decrypt(private_key, ciphertext)
        assert decrypted.decode('utf-8') == plaintext

    def test_encrypt_decrypt_json_data(self):
        identity = "patient@hospital.com"
        private_key = self.ibe.extract_key(identity)
        
        health_data = {
            "name": "John Doe",
            "blood_type": "O+",
            "allergies": ["Penicillin"]
        }
        plaintext = json.dumps(health_data)
        ciphertext = self.ibe.encrypt_with_key(private_key, plaintext)
        
        decrypted = self.ibe.decrypt(private_key, ciphertext)
        result = json.loads(decrypted.decode('utf-8'))
        assert result == health_data

    def test_ciphertext_serialization(self):
        identity = "patient@hospital.com"
        private_key = self.ibe.extract_key(identity)
        
        ciphertext = self.ibe.encrypt_with_key(private_key, "test data")
        serialized = ciphertext.serialize()
        deserialized = IBECiphertext.deserialize(serialized)
        
        assert deserialized.U == ciphertext.U
        assert deserialized.V == ciphertext.V
        assert deserialized.W == ciphertext.W


class TestShamirSecretSharing:
    """Tests for Shamir's Secret Sharing."""

    def setup_method(self):
        self.sss = ShamirSecretSharing()

    def test_generate_correct_number_of_shares(self):
        shares = self.sss.generate_shares(12345, k=3, n=5)
        assert len(shares) == 5

    def test_reconstruct_with_k_shares(self):
        secret = 42
        shares = self.sss.generate_shares(secret, k=3, n=5)
        reconstructed = self.sss.reconstruct_secret(shares[:3], k=3)
        assert reconstructed == secret

    def test_reconstruct_with_all_shares(self):
        secret = 12345
        shares = self.sss.generate_shares(secret, k=3, n=5)
        reconstructed = self.sss.reconstruct_secret(shares, k=3)
        assert reconstructed == secret

    def test_any_k_shares_work(self):
        from itertools import combinations
        secret = 99999
        shares = self.sss.generate_shares(secret, k=3, n=5)
        
        for combo in combinations(shares, 3):
            reconstructed = self.sss.reconstruct_secret(list(combo), k=3)
            assert reconstructed == secret

    def test_bytes_roundtrip(self):
        secret_bytes = os.urandom(32)
        shares = self.sss.generate_shares_bytes(secret_bytes, k=3, n=5)
        reconstructed = self.sss.reconstruct_secret_bytes(shares[:3], k=3, length=32)
        # The reconstructed value should be the same modular value
        assert int.from_bytes(reconstructed, 'big') % self.sss.prime == \
               int.from_bytes(secret_bytes, 'big') % self.sss.prime

    def test_invalid_k_greater_than_n(self):
        with pytest.raises(ValueError):
            self.sss.generate_shares(42, k=6, n=5)

    def test_different_secrets_different_shares(self):
        shares1 = self.sss.generate_shares(100, k=3, n=5)
        shares2 = self.sss.generate_shares(200, k=3, n=5)
        assert shares1 != shares2


class TestDistributedDecryption:
    """Tests for threshold distributed decryption."""

    def setup_method(self):
        self.ibe = IdentityBasedEncryption()
        self.params, self.master_secret = self.ibe.setup()
        self.coordinator = DecryptionCoordinator(k=3, n=5, ibe_system=self.ibe)
        self.coordinator.initialize_servers(self.master_secret.secret)

    def test_server_initialization(self):
        assert len(self.coordinator.servers) == 5
        for server in self.coordinator.servers.values():
            assert server.is_active

    def test_cluster_status(self):
        status = self.coordinator.get_cluster_status()
        assert status['threshold'] == 3
        assert status['total_servers'] == 5
        assert status['active_servers'] == 5

    def test_threshold_decrypt(self):
        identity = "patient@hospital.com"
        private_key = self.ibe.extract_key(identity)
        
        plaintext = "test health record data"
        ciphertext = self.ibe.encrypt_with_key(private_key, plaintext)
        
        result = self.coordinator.combine_and_decrypt(ciphertext, identity)
        assert result.decode('utf-8') == plaintext

    def test_deactivate_server(self):
        self.coordinator.deactivate_server('server_1')
        status = self.coordinator.get_cluster_status()
        assert status['active_servers'] == 4

    def test_decrypt_with_deactivated_servers(self):
        # Deactivate 2 servers (still have 3 = k active)
        self.coordinator.deactivate_server('server_1')
        self.coordinator.deactivate_server('server_2')
        
        identity = "patient@hospital.com"
        private_key = self.ibe.extract_key(identity)
        plaintext = "test data with fewer servers"
        ciphertext = self.ibe.encrypt_with_key(private_key, plaintext)
        
        result = self.coordinator.combine_and_decrypt(ciphertext, identity)
        assert result.decode('utf-8') == plaintext

    def test_insufficient_servers_raises_error(self):
        # Deactivate 3 servers (only 2 active < k=3)
        self.coordinator.deactivate_server('server_1')
        self.coordinator.deactivate_server('server_2')
        self.coordinator.deactivate_server('server_3')
        
        identity = "patient@hospital.com"
        private_key = self.ibe.extract_key(identity)
        ciphertext = self.ibe.encrypt_with_key(private_key, "test")
        
        with pytest.raises(RuntimeError, match="Not enough active servers"):
            self.coordinator.combine_and_decrypt(ciphertext, identity)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
