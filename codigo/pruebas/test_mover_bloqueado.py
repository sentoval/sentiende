# -*- coding: utf-8 -*-
"""Mover un archivo abierto en otro programa (WinError 32): se reintenta y, si sigue abierto, se avisa sin dejar nada a medias."""
import shutil, tempfile, unittest
from pathlib import Path
from unittest import mock
from sentiende import arreglos


class TestMoverBloqueado(unittest.TestCase):
    def test_reintenta_y_avisa(self):
        with tempfile.TemporaryDirectory() as t:
            a, b = Path(t) / "a.pdf", Path(t) / "b.pdf"
            a.write_bytes(b"%PDF-1.4")
            err = OSError(13, "en uso"); err.winerror = 32
            with mock.patch("shutil.move", side_effect=err), mock.patch("time.sleep"):
                with self.assertRaises(arreglos.ErrorArreglo) as cm:
                    arreglos._mover(a, b)
            self.assertIn("abierto en otro programa", str(cm.exception))
            self.assertTrue(a.exists()); self.assertFalse(b.exists())

    def test_se_libera_al_segundo_intento(self):
        with tempfile.TemporaryDirectory() as t:
            a, b = Path(t) / "a.pdf", Path(t) / "b.pdf"
            a.write_bytes(b"%PDF-1.4")
            real, veces = shutil.move, []
            def mover(x, y):
                veces.append(1)
                if len(veces) == 1:
                    raise PermissionError(13, "en uso")
                return real(x, y)
            with mock.patch("shutil.move", side_effect=mover), mock.patch("time.sleep"):
                arreglos._mover(a, b)
            self.assertEqual(len(veces), 2)
            self.assertTrue(b.exists()); self.assertFalse(a.exists())
