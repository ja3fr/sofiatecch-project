# Fichier : colors.py (Version modifiée, claire et réutilisable)

# --- Étape 1 : Imports en haut du fichier (bonne pratique) ---
import sys
import platform

# --- Étape 2 : La classe de couleurs, simple et lisible ---
# Elle ne fait que stocker les chaînes de caractères. Pas de logique ici.
class Colors:
    """
    Contient les constantes pour les codes d'échappement ANSI pour les couleurs du terminal.
    Ces codes sont des standards reconnus par la plupart des terminaux modernes.
    """
    # Codes de base (30-37)
    BLACK = "\033[0;30m"
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    BROWN = "\033[0;33m" # Souvent affiché comme du jaune
    BLUE = "\033[0;34m"
    PURPLE = "\033[0;35m"
    CYAN = "\033[0;36m"
    LIGHT_GRAY = "\033[0;37m"

    # Codes vifs (avec le style "bold/gras" ;1m)
    DARK_GRAY = "\033[1;30m"
    LIGHT_RED = "\033[1;31m"
    LIGHT_GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    LIGHT_BLUE = "\033[1;34m"
    LIGHT_PURPLE = "\033[1;35m"
    LIGHT_CYAN = "\033[1;36m"
    LIGHT_WHITE = "\033[1;37m"

    # Styles de texte
    BOLD = "\033[1m"
    FAINT = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    NEGATIVE = "\033[7m"
    CROSSED = "\033[9m"
    
    # Code pour réinitialiser tous les styles et couleurs
    END = "\033[0m"


# --- Étape 3 : Fonction d'initialisation séparée ---
# Cette fonction contient toute la logique de configuration.
def init_colors():
    """
    Vérifie l'environnement et configure les couleurs.
    - Sur Windows, active le mode "Virtual Terminal" pour que les codes ANSI fonctionnent.
    - Si la sortie n'est pas un terminal (ex: redirigée vers un fichier),
      désactive toutes les couleurs en remplaçant les codes par des chaînes vides.
    """
    # Cas 1 : La sortie n'est pas un terminal (ex: `python mon_script.py > log.txt`)
    if not sys.stdout.isatty():
        # On parcourt tous les attributs de la classe Colors
        for attr_name in dir(Colors):
            # On ignore les attributs spéciaux (qui commencent par "__")
            if not attr_name.startswith("__"):
                # On remplace la valeur de l'attribut (ex: Colors.RED) par une chaîne vide.
                # setattr() est la manière propre de faire cela dynamiquement.
                setattr(Colors, attr_name, "")
        return # Pas besoin d'aller plus loin

    # Cas 2 : On est sur Windows et dans un terminal
    # Il faut activer le support des séquences ANSI manuellement.
    if platform.system() == "Windows":
        try:
            # On importe ctypes uniquement si nécessaire
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # On récupère le "handle" de la console de sortie (-11)
            # Et on active le mode "ENABLE_VIRTUAL_TERMINAL_PROCESSING" (valeur 4).
            # La valeur 7 est un masque de bits qui conserve d'autres flags utiles.
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception as e:
            # Si ça échoue (vieille version de Windows), les couleurs ne marcheront pas.
            print(f"Avertissement : Impossible d'activer le mode VT sur Windows. {e}")


# --- Étape 4 : Bloc de test principal ---
# Ce code ne s'exécute que si on lance ce fichier directement (python colors.py)
if __name__ == '__main__':
    # On appelle notre fonction d'initialisation en premier !
    init_colors()
    a
    print("--- Test des Couleurs et Styles ---")
    
    # Test de toutes les couleurs définies
    for color_name in dir(Colors):
        if not color_name.startswith("__") and color_name != "END":
            color_code = getattr(Colors, color_name)
            # On utilise .format() pour un affichage bien aligné
            print("{:>16} : {}".format(color_name, color_code + "Exemple de texte" + Colors.END))
            
    print("\n--- Test de Combinaisons ---")
    print(f"Ceci est du texte {Colors.BOLD}{Colors.RED}ROUGE et GRAS{Colors.END}.")
    print(f"Ceci est du texte {Colors.UNDERLINE}{Colors.BLUE}BLEU et SOULIGNÉ{Colors.END}.")
    print(f"Le fond sera {Colors.NEGATIVE}inversé{Colors.END} ici.")