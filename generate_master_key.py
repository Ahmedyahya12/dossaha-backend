#!/usr/bin/env python
"""
Script de génération de la Master Key
 À exécuter UNE SEULE FOIS au début du projet
"""

from cryptography.fernet import Fernet

def generate_master_key():
    """Génère et affiche la Master Key"""
    master_key = Fernet.generate_key()
    key_str = master_key.decode()
    
    print("=" * 60)
    print(" MASTER KEY GÉNÉRÉE")
    print("=" * 60)
    print(f"\nMASTER_KEY={key_str}\n")
    print("=" * 60)

if __name__ == "__main__":
    generate_master_key()