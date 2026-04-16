# -*- coding: utf-8 -*-
"""
core/preprocessor.py
====================
FASE 1: Preprocesamiento
Genera lyrics_aligned.json, phonemes.json, visemes.json, emotions.json
a partir del audio WAV y letra manual.

Dependencias: librosa, numpy, scipy
"""
import asyncio
import json
import numpy as np
import os
import re

# ESTO ES LO QUE DEBES CAMBIAR:
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    librosa = None  # <--- Esto le dice a Python: "Si no hay librosa, vale None"
    LIBROSA_AVAILABLE = False
    print("[WARNING] librosa no instalado. Usando datos sintéticos.")
# ─── TABLAS DE MAPEO ──────────────────────────────────────────────────────────

PHONEME_TO_VISEME = {
    # Silencio / descanso
    "SIL": "rest", "SP": "rest",
    # Abierta (A)
    "AA": "open", "AE": "open", "AH": "open", "AW": "open", "AY": "open",
    # Ancha (E, I)
    "EH": "wide", "EY": "wide", "IH": "wide", "IY": "wide",
    # Redonda (O, U)
    "OW": "round", "OY": "round", "UH": "round", "UW": "round",
    # Dientes (S, Z, TH)
    "S": "teeth", "Z": "teeth", "SH": "teeth", "ZH": "teeth",
    "TH": "teeth", "DH": "teeth",
    # Cerrada (M, B, P)
    "M": "close", "B": "close", "P": "close",
    # Semiabierta por defecto
    "CH": "wide", "D": "open", "F": "teeth", "G": "open",
    "HH": "open", "JH": "wide", "K": "open", "L": "wide",
    "N": "wide", "NG": "wide", "R": "round", "T": "wide",
    "V": "teeth", "W": "round", "Y": "wide",
}

VISEME_SHAPES = {
    "rest":  {"type": "line",  "w": 12, "h": 0},
    "open":  {"type": "oval",  "w": 18, "h": 22},
    "wide":  {"type": "oval",  "w": 28, "h": 12},
    "round": {"type": "oval",  "w": 14, "h": 20},
    "teeth": {"type": "teeth", "w": 22, "h": 10},
    "close": {"type": "oval",  "w": 20, "h": 4},
}

# Secuencia simplificada de fonemas españoles por sílaba
SPANISH_PHONEMES = {
    "a": ["AA"], "e": ["EH"], "i": ["IY"], "o": ["OW"], "u": ["UW"],
    "b": ["B"], "c": ["K"], "d": ["D"], "f": ["F"], "g": ["G"],
    "h": [], "j": ["HH"], "k": ["K"], "l": ["L"], "m": ["M"],
    "n": ["N"], "ñ": ["N", "Y"], "p": ["P"], "q": ["K"], "r": ["R"],
    "s": ["S"], "t": ["T"], "v": ["V"], "w": ["W"], "x": ["K", "S"],
    "y": ["Y"], "z": ["S"],
}


# ─── CLASE PRINCIPAL ──────────────────────────────────────────────────────────

class Preprocessor:
    def __init__(self, audio_path: str, lyrics_raw: str, output_dir: str = "data"):
        self.audio_path = audio_path
        self.lyrics_raw = lyrics_raw
        self.output_dir = output_dir
        self.sr = 22050
        self.y = None
        self.duration = 20.0
        os.makedirs(output_dir, exist_ok=True)

    # ── LOAD AUDIO ────────────────────────────────────────────────────────────
    def load_audio(self):
        # Usamos la variable que creamos al principio del archivo
        if LIBROSA_AVAILABLE and librosa is not None:
            if os.path.exists(self.audio_path):
                self.y, self.sr = librosa.load(self.audio_path, sr=self.sr)
                self.duration = librosa.get_duration(y=self.y, sr=self.sr)
                print(f"[Audio] Cargado: {self.audio_path}")
            else:
                print(f"[Audio] No se encontró el archivo: {self.audio_path}")
                self._generate_dummy_audio()
        else:
            self._generate_dummy_audio()

    def _generate_dummy_audio(self):
        self.duration = 20.0
        self.sr = 22050
        t = np.linspace(0, self.duration, int(self.sr * self.duration))
        self.y = np.sin(2 * np.pi * 220 * t) * 0.5
        print(f"[Audio] Usando señal sintética ({self.duration}s)")
        # ── PARSE LYRICS ──────────────────────────────────────────────────────────
        def parse_lyrics(self):
            """
            Formato esperado:
                0.0-3.5 | Primera línea de la canción
                3.5-7.0 | Segunda línea aquí
            """
            lines = []
            for raw in self.lyrics_raw.strip().split("\n"):
                raw = raw.strip()
                if not raw:
                    continue
                m = re.match(r"^([\d.]+)-([\d.]+)\s*\|\s*(.+)$", raw)
                if m:
                    lines.append({
                        "start": float(m.group(1)),
                        "end":   float(m.group(2)),
                        "text":  m.group(3).strip()
                    })
            return lines

        # ── ALIGN LYRICS ──────────────────────────────────────────────────────────
        def align_lyrics(self):
            """
            Alineación letra ↔ tiempo.
            En producción: usar Montreal Forced Aligner o gentle.
            Aquí usamos la anotación manual como ground truth.
            """
            aligned = self.parse_lyrics()
            # Dividir cada línea en palabras con timestamps proporcionales
            result = []
            for seg in aligned:
                words = seg["text"].split()
                if not words:
                    continue
                seg_dur = seg["end"] - seg["start"]
                word_dur = seg_dur / len(words)
                for i, word in enumerate(words):
                    result.append({
                        "word":  word,
                        "start": round(seg["start"] + i * word_dur, 3),
                        "end":   round(seg["start"] + (i + 1) * word_dur, 3),
                        "line":  seg["text"]
                    })
            path = os.path.join(self.output_dir, "lyrics_aligned.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"[Lyrics] Alineadas: {len(result)} palabras → {path}")
            return result

        # ── EXTRACT PHONEMES ──────────────────────────────────────────────────────
        def extract_phonemes(self, aligned_words):
            """
            Fonemas por palabra (análisis letra por letra para español).
            En producción: usar espeak-ng o eSpeak con phonemizer.
            """
            phonemes = []
            for entry in aligned_words:
                word = re.sub(r"[^a-záéíóúñü]", "", entry["word"].lower())
                if not word:
                    phonemes.append({"phoneme": "SIL", "start": entry["start"],
                                    "end": entry["end"], "word": entry["word"]})
                    continue
                chars = list(word)
                char_dur = (entry["end"] - entry["start"]) / max(len(chars), 1)
                for j, ch in enumerate(chars):
                    ph_list = SPANISH_PHONEMES.get(ch, ["SIL"])
                    sub_dur = char_dur / max(len(ph_list), 1)
                    for k, ph in enumerate(ph_list):
                        phonemes.append({
                            "phoneme": ph,
                            "start":   round(entry["start"] + j * char_dur + k * sub_dur, 4),
                            "end":     round(entry["start"] + j * char_dur + (k + 1) * sub_dur, 4),
                            "word":    entry["word"]
                        })
            path = os.path.join(self.output_dir, "phonemes.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(phonemes, f, ensure_ascii=False, indent=2)
            print(f"[Phonemes] Extraídos: {len(phonemes)} fonemas → {path}")
            return phonemes

        # ── BUILD VISEMES ─────────────────────────────────────────────────────────
        def build_visemes(self, phonemes):
            """Mapeo fonemas → visemas + parámetros de forma de boca."""
            visemes = []
            for ph in phonemes:
                vm = PHONEME_TO_VISEME.get(ph["phoneme"], "rest")
                visemes.append({
                    "viseme": vm,
                    "shape":  VISEME_SHAPES[vm],
                    "start":  ph["start"],
                    "end":    ph["end"],
                    "phoneme": ph["phoneme"]
                })
            path = os.path.join(self.output_dir, "visemes.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(visemes, f, ensure_ascii=False, indent=2)
            print(f"[Visemes] Generados: {len(visemes)} visemas → {path}")
            return visemes

        # ── ANALYZE EMOTIONS ──────────────────────────────────────────────────────
        def analyze_emotions(self, window: float = 0.5):
            """
            Análisis de energía (RMS) y pitch para inferir emoción.
            Resolución temporal: `window` segundos.
            
            Emociones:
                calm    → energía baja, pitch estable
                happy   → energía media, pitch variado  
                intense → energía alta, pitch alto
                sad     → energía baja, pitch bajo y plano
            """
            emotions = []
            n_windows = int(self.duration / window)
            hop = int(self.sr * window)

            for i in range(n_windows):
                t_start = i * window
                t_end   = t_start + window
                idx_s   = int(t_start * self.sr)
                idx_e   = min(int(t_end * self.sr), len(self.y))
                chunk   = self.y[idx_s:idx_e]

                if len(chunk) < 2:
                    emotions.append({"start": t_start, "end": t_end, "emotion": "calm",
                                    "energy": 0.0, "pitch": 0.0, "confidence": 1.0})
                    continue

                # RMS energy
                rms = float(np.sqrt(np.mean(chunk ** 2)))

                # Pitch via autocorrelation (simple)
                # Cambia la línea 231 por esto:
                if LIBROSA_AVAILABLE and librosa is not None:
                    f0, _, _ = librosa.pyin(chunk, fmin=50, fmax=500, sr=self.sr)
                    pitch = float(np.nanmean(f0)) if f0 is not None and not np.all(np.isnan(f0)) else 0.0
                    pitch_std = float(np.nanstd(f0)) if f0 is not None else 0.0
                else:
                    # Simular variación sintética
                    phase = t_start / self.duration
                    pitch = 150 + 80 * np.sin(phase * 6 * np.pi)
                    pitch_std = 20 * abs(np.sin(phase * 3 * np.pi))

                # Clasificación heurística
                if rms > 0.25 and pitch > 200:
                    emotion = "intense"
                elif rms > 0.15 and pitch_std > 30:
                    emotion = "happy"
                elif rms < 0.08 and pitch < 150:
                    emotion = "sad"
                else:
                    emotion = "calm"

                emotions.append({
                    "start":      round(t_start, 3),
                    "end":        round(t_end, 3),
                    "emotion":    emotion,
                    "energy":     round(rms, 4),
                    "pitch":      round(pitch, 2),
                    "confidence": 0.85
                })

            # Suavizar emociones para evitar cambios bruscos
            emotions = self._smooth_emotions(emotions)

            path = os.path.join(self.output_dir, "emotions.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(emotions, f, indent=2)
            print(f"[Emotions] Analizadas: {len(emotions)} ventanas → {path}")
            return emotions

        def _smooth_emotions(self, emotions, window=3):
            smoothed = [e.copy() for e in emotions]
            # Usamos enumerate para tener el índice (i) y el elemento (e) al mismo tiempo
            for i, current_info in enumerate(emotions):
                start = max(0, i - window)
                end   = min(len(emotions), i + window + 1)
                
                # Sacamos las emociones del rango
                window_emotions = [emotions[j]["emotion"] for j in range(start, end)]
                
                counts = {}
                for emo in window_emotions:
                    counts[emo] = counts.get(emo, 0) + 1
                
                if counts:
                    # Aquí ya no usamos la 'i' para buscar la emoción, es más seguro
                    most_frequent = max(list(counts), key=lambda k: counts[k])
                    smoothed[i]["emotion"] = most_frequent
                else:
                    smoothed[i]["emotion"] = current_info["emotion"]
        # EL SECRETO: El return debe estar alineado con el 'for', no con el 'if'
            return smoothed
    def run(self):
            """Este es el botón que el main.py busca"""
            print("\n=== INICIANDO PREPROCESAMIENTO ===")
            self.load_audio()
            
            # Devolvemos los datos para que el main no explote
            return {
                "duration": getattr(self, 'duration', 20.0),
                "sr": getattr(self, 'sr', 22050)
            }