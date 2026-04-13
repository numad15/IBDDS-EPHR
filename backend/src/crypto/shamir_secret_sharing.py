"""
Shamir's Secret Sharing Scheme

Implements (k, n) threshold secret sharing over a prime field.
- Split a secret into n shares such that any k shares can reconstruct it.
- Fewer than k shares reveal no information about the secret.

Based on polynomial interpolation over a finite field GF(p).
"""

import os
import hashlib
import secrets

# Large prime for finite field arithmetic
DEFAULT_PRIME = 2**127 - 1  # Mersenne prime M127


class ShamirSecretSharing:
    """
    Shamir's (k, n) threshold secret sharing scheme.
    
    Splits a secret into n shares using a random polynomial of degree k-1.
    Any k shares can reconstruct the secret via Lagrange interpolation.
    """

    def __init__(self, prime=DEFAULT_PRIME):
        self.prime = prime

    def _random_polynomial(self, secret, degree):
        """
        Generate a random polynomial of given degree with the secret as constant term.
        
        f(x) = secret + a1*x + a2*x^2 + ... + a_{degree}*x^{degree}
        """
        coefficients = [secret]
        for _ in range(degree):
            coeff = secrets.randbelow(self.prime)
            coefficients.append(coeff)
        return coefficients

    def _evaluate_polynomial(self, coefficients, x):
        """
        Evaluate polynomial at point x using Horner's method.
        All arithmetic is mod prime.
        """
        result = 0
        for coeff in reversed(coefficients):
            result = (result * x + coeff) % self.prime
        return result

    def _mod_inverse(self, a, p):
        """
        Compute modular multiplicative inverse using extended Euclidean algorithm.
        Returns a^(-1) mod p.
        """
        if a == 0:
            raise ValueError("Cannot compute inverse of zero")
        
        g, x, _ = self._extended_gcd(a % p, p)
        if g != 1:
            raise ValueError(f"Modular inverse does not exist for {a} mod {p}")
        return x % p

    def _extended_gcd(self, a, b):
        """Extended Euclidean Algorithm. Returns (gcd, x, y) where ax + by = gcd."""
        if a == 0:
            return b, 0, 1
        g, x, y = self._extended_gcd(b % a, a)
        return g, y - (b // a) * x, x

    def generate_shares(self, secret, k, n):
        """
        Split a secret into n shares with threshold k.
        
        Args:
            secret: The integer secret to split (or bytes to be converted)
            k: Minimum number of shares needed to reconstruct
            n: Total number of shares to generate
            
        Returns:
            List of (x, y) tuples representing shares
        """
        if k > n:
            raise ValueError(f"Threshold k={k} cannot exceed total shares n={n}")
        if k < 2:
            raise ValueError("Threshold k must be at least 2")
        if n < 2:
            raise ValueError("Total shares n must be at least 2")

        # Convert bytes secret to integer if needed
        if isinstance(secret, bytes):
            secret = int.from_bytes(secret, 'big') % self.prime
        elif isinstance(secret, str):
            secret = int.from_bytes(secret.encode('utf-8'), 'big') % self.prime

        secret = secret % self.prime

        # Generate random polynomial of degree k-1 with secret as constant term
        polynomial = self._random_polynomial(secret, k - 1)

        # Evaluate polynomial at points 1, 2, ..., n
        shares = []
        for i in range(1, n + 1):
            y = self._evaluate_polynomial(polynomial, i)
            shares.append((i, y))

        return shares

    def reconstruct_secret(self, shares, k=None):
        """
        Reconstruct the secret from k or more shares using Lagrange interpolation.
        
        Args:
            shares: List of (x, y) tuples (at least k shares)
            k: Expected threshold (optional, for validation)
            
        Returns:
            The reconstructed secret as an integer
        """
        if k and len(shares) < k:
            raise ValueError(f"Need at least {k} shares, got {len(shares)}")

        if len(shares) < 2:
            raise ValueError("Need at least 2 shares to reconstruct")

        return self._lagrange_interpolation(shares, 0)

    def _lagrange_interpolation(self, shares, x):
        """
        Lagrange interpolation at point x.
        
        L_i(x) = ∏_{j≠i} (x - x_j) / (x_i - x_j)
        f(x) = Σ y_i * L_i(x)
        
        All operations in GF(prime).
        """
        n = len(shares)
        result = 0

        for i in range(n):
            xi, yi = shares[i]
            
            # Compute Lagrange basis polynomial L_i(x)
            numerator = 1
            denominator = 1
            
            for j in range(n):
                if i == j:
                    continue
                xj, _ = shares[j]
                
                numerator = (numerator * (x - xj)) % self.prime
                denominator = (denominator * (xi - xj)) % self.prime

            # L_i(x) = numerator / denominator (mod prime)
            lagrange_coeff = (numerator * self._mod_inverse(denominator, self.prime)) % self.prime
            
            # Add y_i * L_i(x)
            result = (result + yi * lagrange_coeff) % self.prime

        return result

    def generate_shares_bytes(self, secret_bytes, k, n):
        """
        Generate shares from a bytes secret.
        Returns shares as list of (index, value) tuples.
        """
        secret_int = int.from_bytes(secret_bytes, 'big') % self.prime
        return self.generate_shares(secret_int, k, n)

    def reconstruct_secret_bytes(self, shares, k=None, length=32):
        """
        Reconstruct secret and return as bytes.
        """
        secret_int = self.reconstruct_secret(shares, k)
        return secret_int.to_bytes(length, 'big')

    def verify_shares(self, shares, k, secret):
        """
        Verify that any k shares from the set can reconstruct the secret.
        Useful for testing.
        """
        from itertools import combinations
        
        if isinstance(secret, bytes):
            secret = int.from_bytes(secret, 'big') % self.prime
        
        for combo in combinations(shares, k):
            reconstructed = self.reconstruct_secret(list(combo), k)
            if reconstructed != secret % self.prime:
                return False
        return True
