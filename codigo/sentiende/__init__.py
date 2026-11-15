# -*- coding: utf-8 -*-
"""Sentiende · motor común de SeFinancia, SeCasa, SeTaxi y futuras variantes.

El motor no tiene ejecutable propio: cada aplicación lo lleva dentro (carpeta Motor\\)
junto con su variante (carpeta Variantes\\<variante>\\, solo configuración).
El motor no sabe qué es un préstamo: las reglas, tipos, nombres y checklists
se los da la variante."""

VERSION = "2.2.0"      # versión del motor (mayor.menor.corrección)
CONTRATO = 2           # contrato que ofrece a las variantes: «requiere motor 2.x»

FASES = [
    (1, "Recibir"), (2, "Leer"), (3, "Separar"), (4, "Orientar"), (5, "Extraer datos"),
    (6, "Clasificar"), (7, "Emparejar"), (8, "Renombrar"), (9, "Checklist"), (10, "Guardar"),
]
