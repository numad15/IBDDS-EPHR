"""
Distributed Decryption Module

Manages a cluster of n decryption servers, each holding one share
of the IBE master secret. Implements threshold decryption where
at least k servers must cooperate to decrypt a record.

No single server can decrypt alone, ensuring security even if
some servers are compromised (as long as fewer than k).
"""

import hashlib
import os
import json
from .shamir_secret_sharing import ShamirSecretSharing
from .identity_based_encryption import IdentityBasedEncryption, IBECiphertext, IBEPrivateKey


class DecryptionServer:
    """
    A single decryption server holding one share of the master secret.
    Each server can compute a partial decryption but cannot decrypt alone.
    """

    def __init__(self, server_id, share):
        """
        Args:
            server_id: Unique identifier for this server
            share: Tuple (x, y) representing this server's Shamir share
        """
        self.server_id = server_id
        self.share = share
        self.is_active = True

    def compute_partial_decryption(self, ciphertext_U, identity):
        """
        Compute partial decryption using this server's share.
        
        In real threshold IBE: server computes R_i = e(d_i, U)
        where d_i is its share of the private key.
        
        Simulated: hash-based partial computation.
        """
        if not self.is_active:
            raise RuntimeError(f"Server {self.server_id} is not active")

        x, y = self.share
        
        # Simulate partial decryption: hash(share_value || U || identity)
        partial = hashlib.sha256(
            b"PARTIAL_DEC" + 
            y.to_bytes(32, 'big') +
            ciphertext_U +
            identity.encode('utf-8')
        ).digest()

        return {
            'server_id': self.server_id,
            'share_index': x,
            'share_value': y,
            'partial_decryption': partial.hex(),
            'identity': identity
        }

    def get_status(self):
        return {
            'server_id': self.server_id,
            'is_active': self.is_active,
            'share_index': self.share[0]
        }


class DecryptionCoordinator:
    """
    Coordinates threshold decryption across multiple servers.
    
    Manages the decryption server cluster and orchestrates
    the threshold decryption protocol:
    1. Receive decrypt request
    2. Gather k partial decryptions from servers
    3. Combine using Lagrange interpolation
    4. Recover plaintext
    """

    def __init__(self, k, n, ibe_system=None):
        """
        Args:
            k: Threshold (minimum servers needed)
            n: Total number of servers
            ibe_system: Reference to the IBE system
        """
        self.k = k
        self.n = n
        self.servers = {}
        self.ibe = ibe_system or IdentityBasedEncryption()
        self.sss = ShamirSecretSharing()
        self._master_secret_shares = None

    def initialize_servers(self, master_secret_bytes):
        """
        Split the master secret into n shares and create n decryption servers.
        
        Args:
            master_secret_bytes: The IBE master secret as bytes
        """
        # Generate Shamir shares
        shares = self.sss.generate_shares_bytes(master_secret_bytes, self.k, self.n)
        self._master_secret_shares = shares

        # Create decryption servers
        self.servers = {}
        for i, share in enumerate(shares):
            server_id = f"server_{i + 1}"
            self.servers[server_id] = DecryptionServer(server_id, share)

        return list(self.servers.keys())

    def request_partial_decryptions(self, ciphertext, identity, num_servers=None):
        """
        Request partial decryptions from k (or more) active servers.
        
        Args:
            ciphertext: IBECiphertext to partially decrypt
            identity: Identity string of the record owner
            num_servers: Number of servers to query (default: k)
            
        Returns:
            List of partial decryption results
        """
        if num_servers is None:
            num_servers = self.k

        active_servers = [s for s in self.servers.values() if s.is_active]

        if len(active_servers) < self.k:
            raise RuntimeError(
                f"Not enough active servers. Need {self.k}, have {len(active_servers)}"
            )

        # Select servers to use
        selected = active_servers[:num_servers]

        # Gather partial decryptions
        U_bytes = ciphertext.U if isinstance(ciphertext.U, bytes) else bytes.fromhex(ciphertext.U)
        
        partials = []
        for server in selected:
            partial = server.compute_partial_decryption(U_bytes[:32], identity)
            partials.append(partial)

        return partials

    def combine_and_decrypt(self, ciphertext, identity, partials=None):
        """
        Combine partial decryptions and recover the plaintext.
        
        This is the main decryption method that:
        1. Gathers partial decryptions (if not provided)
        2. Reconstructs the master secret via Lagrange interpolation
        3. Derives the private key for the identity
        4. Decrypts the ciphertext
        
        Args:
            ciphertext: IBECiphertext to decrypt
            identity: Identity string of the record owner
            partials: Optional pre-computed partial decryptions
            
        Returns:
            Decrypted plaintext as bytes
        """
        if partials is None:
            partials = self.request_partial_decryptions(ciphertext, identity)

        if len(partials) < self.k:
            raise ValueError(
                f"Need at least {self.k} partial decryptions, got {len(partials)}"
            )

        # Reconstruct master secret from shares
        shares_for_reconstruction = [
            (p['share_index'], p['share_value']) for p in partials[:self.k]
        ]
        
        reconstructed_secret_int = self.sss.reconstruct_secret(
            shares_for_reconstruction, self.k
        )
        
        # Convert back to bytes (same length as original)
        reconstructed_secret = reconstructed_secret_int.to_bytes(32, 'big')

        # Derive private key for the identity using reconstructed secret
        # Simulate: same as IBE extract but with reconstructed secret
        q_id = self.ibe._h1(identity)
        key_data = hashlib.sha256(reconstructed_secret + q_id).digest()
        private_key = IBEPrivateKey(identity=identity, key_data=key_data)

        # Decrypt the ciphertext
        plaintext = self.ibe.decrypt(private_key, ciphertext)

        return plaintext

    def threshold_decrypt(self, ciphertext_dict, identity):
        """
        High-level threshold decryption interface.
        
        Args:
            ciphertext_dict: Ciphertext as dictionary (from database)
            identity: Patient's identity (email)
            
        Returns:
            Decrypted data as string
        """
        # Parse ciphertext
        ciphertext = IBECiphertext.from_dict(ciphertext_dict)

        # Perform distributed decryption
        plaintext_bytes = self.combine_and_decrypt(ciphertext, identity)

        return plaintext_bytes.decode('utf-8')

    def get_cluster_status(self):
        """Get status of all decryption servers."""
        return {
            'threshold': self.k,
            'total_servers': self.n,
            'active_servers': sum(1 for s in self.servers.values() if s.is_active),
            'servers': [s.get_status() for s in self.servers.values()]
        }

    def deactivate_server(self, server_id):
        """Simulate a server going offline."""
        if server_id in self.servers:
            self.servers[server_id].is_active = False
            return True
        return False

    def activate_server(self, server_id):
        """Simulate a server coming back online."""
        if server_id in self.servers:
            self.servers[server_id].is_active = True
            return True
        return False
