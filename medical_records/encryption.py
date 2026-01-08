from cryptography.fernet import Fernet
import os

class EncryptionService:
    """
    Service de chiffrement pour les dossiers médicaux
    """
    @staticmethod
    def get_master_key():
        """
        Récupère la Master Key depuis les variables d'environnement
        """
        master_key = os.environ.get('MASTER_KEY')
        
        if not master_key:
            raise ValueError(
                "  MASTER_KEY non trouvée dans les variables d'environnement.\n"
                "Exécute: python generate_master_key.py"
            )
        
        # Nettoyer la clé
        master_key = master_key.strip()
        
        # Vérifier le format
        if len(master_key) != 44:
            raise ValueError(
                f"  MASTER_KEY invalide: longueur {len(master_key)} "
                f"(attendu: 44 caractères)\n"
                f"Regénère la clé avec: python generate_master_key.py"
            )
        
        return master_key.encode('utf-8')
    
    @staticmethod
    def generate_record_key():
        """
        Génère une nouvelle clé pour un dossier médical
        """
        return Fernet.generate_key()
    
    @staticmethod
    def encrypt_record_key(record_key):
        """
        Chiffre la clé du record avec la Master Key
        
        Args:
            record_key (bytes): Clé du record à chiffrer
            
        Returns:
            bytes: Clé chiffrée
        """
        try:
            master_key = EncryptionService.get_master_key()
            fernet = Fernet(master_key)
            
            #  S'assurer que record_key est en bytes
            if isinstance(record_key, memoryview):
                record_key = bytes(record_key)
            
            return fernet.encrypt(record_key)
        except Exception as e:
            raise ValueError(f"Erreur lors du chiffrement de la clé: {str(e)}")
    
    @staticmethod
    def decrypt_record_key(encrypted_record_key):
        """
        Déchiffre la clé du record avec la Master Key
        
        Args:
            encrypted_record_key (bytes/memoryview): Clé chiffrée
            
        Returns:
            bytes: Clé en clair
        """
        try:
            master_key = EncryptionService.get_master_key()
            fernet = Fernet(master_key)
            
            # CORRECTION: Convertir memoryview en bytes
            if isinstance(encrypted_record_key, memoryview):
                encrypted_record_key = bytes(encrypted_record_key)
            elif not isinstance(encrypted_record_key, (bytes, str)):
                raise TypeError(
                    f"encrypted_record_key doit être bytes/str, "
                    f"reçu: {type(encrypted_record_key)}"
                )
            
            return fernet.decrypt(encrypted_record_key)
        except Exception as e:
            raise ValueError(f"Erreur lors du déchiffrement de la clé: {str(e)}")
    
    @staticmethod
    def encrypt_file(file_content, record_key):
        """
        Chiffre un fichier avec la clé du record
        
        Args:
            file_content (bytes): Contenu du fichier
            record_key (bytes): Clé du record (en clair)
            
        Returns:
            bytes: Fichier chiffré
        """
        try:
            # Convertir memoryview si nécessaire
            if isinstance(record_key, memoryview):
                record_key = bytes(record_key)
            
            if isinstance(file_content, memoryview):
                file_content = bytes(file_content)
            
            fernet = Fernet(record_key)
            return fernet.encrypt(file_content)
        except Exception as e:
            raise ValueError(f"Erreur lors du chiffrement du fichier: {str(e)}")
    
    @staticmethod
    def decrypt_file(encrypted_file_content, record_key):
        """
        Déchiffre un fichier avec la clé du record
        
        Args:
            encrypted_file_content (bytes/memoryview): Fichier chiffré
            record_key (bytes/memoryview): Clé du record (en clair)
            
        Returns:
            bytes: Fichier en clair
        """
        try:
            #  Convertir memoryview si nécessaire
            if isinstance(record_key, memoryview):
                record_key = bytes(record_key)
            
            if isinstance(encrypted_file_content, memoryview):
                encrypted_file_content = bytes(encrypted_file_content)
            
            fernet = Fernet(record_key)
            return fernet.decrypt(encrypted_file_content)
        except Exception as e:
            raise ValueError(f"Erreur lors du déchiffrement du fichier: {str(e)}")