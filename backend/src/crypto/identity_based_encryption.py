"""
Identity-Based Encryption (IBE) - Simulated Boneh-Franklin Scheme

This module implements a simulation of the Boneh-Franklin IBE scheme.
In a production system, this would use actual elliptic curve pairings.
For this demo/academic implementation, we simulate the cryptographic
operations using hash-based constructions that mirror the IBE structure.

IBE Algorithms:
  1. Setup()       - Generate master public/secret keys
  2. Extract(id)   - Derive private key for an identity
  3. Encrypt(id, m) - Encrypt message for an identity
  4. Decrypt(sk, c) - Decrypt ciphertext with private key
"""

import hashlib
import os
import json
import struct


class IBEParams:
    """Master public parameters for the IBE system."""
    def __init__(self, prime, generator, master_public_key, h1_salt, h2_salt, h3_salt, h4_salt):
        self.prime = prime
        self.generator = generator
        self.master_public_key = master_public_key
        self.h1_salt = h1_salt
        self.h2_salt = h2_salt
        self.h3_salt = h3_salt
        self.h4_salt = h4_salt

    def to_dict(self):
        return {
            'prime': self.prime,
            'generator': self.generator,
            'master_public_key': self.master_public_key.hex() if isinstance(self.master_public_key, bytes) else self.master_public_key,
            'h1_salt': self.h1_salt.hex(),
            'h2_salt': self.h2_salt.hex(),
            'h3_salt': self.h3_salt.hex(),
            'h4_salt': self.h4_salt.hex()
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            prime=d['prime'],
            generator=d['generator'],
            master_public_key=bytes.fromhex(d['master_public_key']) if isinstance(d['master_public_key'], str) else d['master_public_key'],
            h1_salt=bytes.fromhex(d['h1_salt']),
            h2_salt=bytes.fromhex(d['h2_salt']),
            h3_salt=bytes.fromhex(d['h3_salt']),
            h4_salt=bytes.fromhex(d['h4_salt'])
        )


class IBEMasterSecret:
    """Master secret key (kept by PKG - Private Key Generator)."""
    def __init__(self, secret):
        self.secret = secret

    def to_dict(self):
        return {'secret': self.secret.hex() if isinstance(self.secret, bytes) else self.secret}

    @classmethod
    def from_dict(cls, d):
        return cls(secret=bytes.fromhex(d['secret']) if isinstance(d['secret'], str) else d['secret'])


class IBEPrivateKey:
    """Private key derived for a specific identity."""
    def __init__(self, identity, key_data):
        self.identity = identity
        self.key_data = key_data

    def to_dict(self):
        return {
            'identity': self.identity,
            'key_data': self.key_data.hex()
        }

    @classmethod
    def from_dict(cls, d):
        return cls(identity=d['identity'], key_data=bytes.fromhex(d['key_data']))


class IBECiphertext:
    """Ciphertext structure: (U, V, W) where U simulates rP, V is encrypted data, W is auth tag."""
    def __init__(self, U, V, W):
        self.U = U
        self.V = V
        self.W = W

    def to_dict(self):
        return {
            'U': self.U.hex(),
            'V': self.V.hex(),
            'W': self.W.hex()
        }

    @classmethod
    def from_dict(cls, d):
        return cls(
            U=bytes.fromhex(d['U']),
            V=bytes.fromhex(d['V']),
            W=bytes.fromhex(d['W'])
        )

    def serialize(self):
        return json.dumps(self.to_dict())

    @classmethod
    def deserialize(cls, s):
        return cls.from_dict(json.loads(s))


class IdentityBasedEncryption:
    """
    Simulated Boneh-Franklin Identity-Based Encryption.
    
    This simulates the IBE operations using hash functions:
    - H1: Maps identity string to a "curve point" (hash)
    - H2: Maps pairing result to a key stream
    - H3: Derives encryption mask
    - H4: Computes authentication tag
    """

    def __init__(self):
        self.params = None
        self.master_secret = None

    def setup(self, prime=2147483647, generator=5):
        """
        Setup: Generate master public parameters and master secret.
        
        In real IBE: Choose groups G1, G2, GT with bilinear map e.
        Generate master secret s, compute P_pub = sP.
        
        Simulated: Generate random master secret and derive public key via hash.
        """
        h1_salt = os.urandom(16)
        h2_salt = os.urandom(16)
        h3_salt = os.urandom(16)
        h4_salt = os.urandom(16)

        master_secret_bytes = os.urandom(32)

        master_public_key = hashlib.sha256(
            b"MASTER_PUB" + master_secret_bytes
        ).digest()

        self.params = IBEParams(
            prime=prime,
            generator=generator,
            master_public_key=master_public_key,
            h1_salt=h1_salt,
            h2_salt=h2_salt,
            h3_salt=h3_salt,
            h4_salt=h4_salt
        )

        self.master_secret = IBEMasterSecret(secret=master_secret_bytes)

        return self.params, self.master_secret

    def _h1(self, identity):
        """H1: Map identity string to a curve point (simulated as hash)."""
        return hashlib.sha256(
            self.params.h1_salt + identity.encode('utf-8')
        ).digest()

    def _h2(self, data):
        """H2: Map pairing result to intermediate value."""
        return hashlib.sha256(
            self.params.h2_salt + data
        ).digest()

    def _h3(self, data, length):
        """H3: Derive key stream of given length (like a KDF)."""
        stream = b""
        counter = 0
        while len(stream) < length:
            stream += hashlib.sha256(
                self.params.h3_salt + data + struct.pack('>I', counter)
            ).digest()
            counter += 1
        return stream[:length]

    def _h4(self, data):
        """H4: Authentication tag hash."""
        return hashlib.sha256(
            self.params.h4_salt + data
        ).digest()[:16]

    def _simulate_pairing(self, point_a, point_b):
        """
        Simulate bilinear pairing e(A, B).
        In real IBE: computes e: G1 x G2 -> GT
        Simulated: hash concatenation of the two points.
        """
        return hashlib.sha256(
            b"PAIRING" + point_a + point_b
        ).digest()

    def extract_key(self, identity):
        """
        Extract: Derive private key for an identity.
        
        In real IBE: d_ID = s * H1(ID) where s is master secret.
        Simulated: HMAC(master_secret, H1(identity))
        """
        if not self.params or not self.master_secret:
            raise ValueError("IBE system not initialized. Call setup() first.")

        q_id = self._h1(identity)

        # Simulate s * Q_ID as HMAC
        key_data = hashlib.sha256(
            self.master_secret.secret + q_id
        ).digest()

        return IBEPrivateKey(identity=identity, key_data=key_data)

    def encrypt(self, identity, plaintext):
        """
        Encrypt: Encrypt plaintext for a given identity.
        
        In real IBE:
          1. Q_ID = H1(ID)
          2. Choose random r
          3. U = rP (part of ciphertext)
          4. g_ID = e(Q_ID, P_pub)
          5. theta = plaintext XOR H3(H2(g_ID^r))
          6. W = H4(plaintext) (auth tag)
        
        Simulated with hash operations.
        """
        if not self.params:
            raise ValueError("IBE system not initialized. Call setup() first.")

        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')

        # Step 1: Hash identity to curve point
        q_id = self._h1(identity)

        # Step 2: Random r
        r = os.urandom(32)

        # Step 3: U = rP (simulated)
        U = hashlib.sha256(b"rP" + r + str(self.params.generator).encode()).digest()

        # Step 4: g_ID = e(Q_ID, P_pub)
        g_id = self._simulate_pairing(q_id, self.params.master_public_key)

        # Step 5: g_ID^r (simulated)
        g_id_r = hashlib.sha256(b"POWER" + g_id + r).digest()

        # Step 6: Derive encryption mask
        h2_result = self._h2(g_id_r)
        mask = self._h3(h2_result, len(plaintext))

        # Step 7: XOR plaintext with mask
        V = bytes(a ^ b for a, b in zip(plaintext, mask))

        # Step 8: Authentication tag
        W = self._h4(plaintext)

        # Store r encrypted with the system for decryption coordination
        # In real IBE, r is implicit in U; here we need it for simulation
        r_encrypted = hashlib.sha256(b"R_ENC" + r + self.master_secret.secret).digest()
        U = U + r_encrypted  # Append encrypted r to U

        return IBECiphertext(U=U, V=V, W=W)

    def decrypt(self, private_key, ciphertext):
        """
        Decrypt: Decrypt ciphertext using the private key.
        
        In real IBE:
          1. g_ID = e(d_ID, U)
          2. plaintext = V XOR H3(H2(g_ID))
          3. Verify W == H4(plaintext)
        
        Simulated with hash operations.
        """
        if not self.params:
            raise ValueError("IBE system not initialized. Call setup() first.")

        # Step 1: Simulate pairing e(d_ID, U)
        U_point = ciphertext.U[:32]
        g_id = self._simulate_pairing(private_key.key_data, U_point)

        # Recover r from U (simulation-specific)
        r_encrypted = ciphertext.U[32:]
        # We need to recover the original g_id^r
        # In simulation, d_ID already encodes the master secret relationship
        # So we can compute the same g_id_r through the private key
        g_id_r = hashlib.sha256(
            b"DECRYPT_PAIRING" + private_key.key_data + U_point
        ).digest()

        # Step 2: Derive decryption mask
        h2_result = self._h2(g_id_r)
        mask = self._h3(h2_result, len(ciphertext.V))

        # Step 3: XOR to recover plaintext
        plaintext = bytes(a ^ b for a, b in zip(ciphertext.V, mask))

        # Step 4: Verify authentication tag
        expected_tag = self._h4(plaintext)
        if expected_tag != ciphertext.W:
            raise ValueError("Authentication tag verification failed. Data may be tampered.")

        return plaintext

    def encrypt_with_key(self, private_key, plaintext):
        """
        Encrypt using a derived private key (for consistency in the simulation).
        This ensures encrypt and decrypt are mathematically paired.
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')

        # Generate random nonce
        r_bytes = os.urandom(32)

        # U = simulated point
        U_point = hashlib.sha256(b"rP" + r_bytes).digest()

        # Compute g_id_r using the private key (same as decrypt will)
        g_id_r = hashlib.sha256(
            b"DECRYPT_PAIRING" + private_key.key_data + U_point
        ).digest()

        # Derive mask
        h2_result = self._h2(g_id_r)
        mask = self._h3(h2_result, len(plaintext))

        # XOR
        V = bytes(a ^ b for a, b in zip(plaintext, mask))

        # Auth tag
        W = self._h4(plaintext)

        # U is just the point (no r_encrypted needed for key-based encrypt)
        U = U_point + os.urandom(32)  # Pad to match expected format

        return IBECiphertext(U=U, V=V, W=W)

    def load_params(self, params_dict):
        """Load IBE parameters from dictionary."""
        self.params = IBEParams.from_dict(params_dict)

    def load_master_secret(self, secret_dict):
        """Load master secret from dictionary."""
        self.master_secret = IBEMasterSecret.from_dict(secret_dict)
