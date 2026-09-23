"""
OCR engines for v2.

  windows – Windows' built-in OCR (Windows.Media.Ocr). Fast on CPU, no model
            download, good with Korean. Needs the Korean OCR language
            installed (see README).
  easyocr – deep-learning OCR; slower on CPU and weaker on Korean. Fallback.
"""

import asyncio
import logging
from typing import List

import numpy as np
from PIL import Image

from chat_layout import OcrBox

logger = logging.getLogger(__name__)


class EasyOcrEngine:
    name = 'easyocr'
    word_level = False  # returns phrase chunks; join them with spaces

    def __init__(self, scale: int = 2) -> None:
        import easyocr
        logger.info("Loading easyocr model…")
        self.reader = easyocr.Reader(['ko', 'en'], gpu=False, verbose=False)
        self.scale = scale

    def read(self, img: Image.Image) -> List[OcrBox]:
        s = self.scale
        big = img.resize((img.width * s, img.height * s), Image.LANCZOS) if s > 1 else img
        boxes = []
        for bbox, text, conf in self.reader.readtext(np.array(big), detail=1):
            xs = [p[0] for p in bbox]
            ys = [p[1] for p in bbox]
            boxes.append(OcrBox(min(xs) / s, min(ys) / s, max(xs) / s, max(ys) / s, text, float(conf)))
        return boxes

    def read_line(self, img: Image.Image) -> str:
        """Recognise a tightly-cropped single line, skipping text detection (which misses lone letters)."""
        arr = np.array(img.convert('RGB').resize((img.width * 2, img.height * 2), Image.LANCZOS))
        results = self.reader.recognize(
            arr, horizontal_list=[[0, arr.shape[1], 0, arr.shape[0]]], free_list=[], detail=1,
        )
        return ' '.join(text for _box, text, conf in results if conf > 0.3)


class WindowsOcrEngine:
    name = 'windows'
    word_level = True  # returns individual words with tight boxes

    def __init__(self, scale: int = 2) -> None:
        from winrt.windows.globalization import Language
        from winrt.windows.media.ocr import OcrEngine

        language = None
        for tag in ('ko-KR', 'ko'):
            candidate = Language(tag)
            if OcrEngine.is_language_supported(candidate):
                language = candidate
                break
        if language is None:
            raise RuntimeError(
                "Korean OCR language is not installed. In an admin PowerShell run: "
                'Add-WindowsCapability -Online -Name "Language.OCR~~~ko-KR~0.0.1.0"'
            )
        self._engine = OcrEngine.try_create_from_language(language)
        if self._engine is None:
            raise RuntimeError("Could not create the Windows OCR engine for Korean.")
        try:
            self._max_dim = int(OcrEngine.max_image_dimension)
        except Exception:
            self._max_dim = 4096
        self.scale = scale

    def _recognize(self, img: Image.Image):
        from winrt.windows.graphics.imaging import BitmapPixelFormat, SoftwareBitmap
        from winrt.windows.storage.streams import DataWriter

        rgba = img.convert('RGBA')
        writer = DataWriter()
        writer.write_bytes(rgba.tobytes())
        bitmap = SoftwareBitmap.create_copy_from_buffer(
            writer.detach_buffer(), BitmapPixelFormat.RGBA8, rgba.width, rgba.height,
        )

        async def run():
            return await self._engine.recognize_async(bitmap)

        return asyncio.run(run())

    def _scale_for(self, img: Image.Image, wanted: int) -> int:
        s = wanted
        while s > 1 and max(img.width, img.height) * s > self._max_dim:
            s -= 1
        return s

    def read(self, img: Image.Image) -> List[OcrBox]:
        s = self._scale_for(img, self.scale)
        big = img.resize((img.width * s, img.height * s), Image.LANCZOS) if s > 1 else img
        boxes = []
        for line in self._recognize(big).lines:
            for word in line.words:
                r = word.bounding_rect
                boxes.append(OcrBox(r.x / s, r.y / s, (r.x + r.width) / s, (r.y + r.height) / s, word.text))
        return boxes

    def read_line(self, img: Image.Image) -> str:
        img = img.convert('RGB')
        s = self._scale_for(img, 3)
        big = img.resize((img.width * s, img.height * s), Image.LANCZOS)
        margin = 20
        canvas = Image.new('RGB', (big.width + 2 * margin, big.height + 2 * margin), big.getpixel((0, 0)))
        canvas.paste(big, (margin, margin))
        return ' '.join(line.text for line in self._recognize(canvas).lines)


def create_engine(preference: str = 'auto'):
    preference = (preference or 'auto').lower()
    if preference in ('auto', 'windows'):
        try:
            engine = WindowsOcrEngine()
            logger.info("OCR engine: Windows built-in OCR")
            return engine
        except Exception as exc:
            if preference == 'windows':
                raise
            logger.info(f"Windows OCR unavailable ({exc}); using easyocr")
    engine = EasyOcrEngine()
    logger.info("OCR engine: easyocr")
    return engine
