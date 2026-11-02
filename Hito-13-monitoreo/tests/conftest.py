import sys
from pathlib import Path

# El código de la API vive en el Hito 10 (solo lectura); el paquete instrumentado, en este hito.
HITO13 = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(HITO13.parent / "Hito-10-fixture2030-APIREST"), str(HITO13)]
