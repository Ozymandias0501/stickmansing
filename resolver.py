"""
core/resolver.py
================
FASE 2 – RUNTIME
Resuelve en cada frame: visema, emoción, letra
Todo basado en current_time. Cero delays externos.
"""

import json
import math
import os


# ─── FORMAS DE VISEMA ─────────────────────────────────────────────────────────

VISEME_SHAPES = {
    "rest":  {"type": "line",  "w": 12, "h": 0},
    "open":  {"type": "oval",  "w": 18, "h": 22},
    "wide":  {"type": "oval",  "w": 28, "h": 12},
    "round": {"type": "oval",  "w": 14, "h": 20},
    "teeth": {"type": "teeth", "w": 22, "h": 10},
    "close": {"type": "oval",  "w": 20, "h": 4},
}


class RuntimeResolver:
    """
    Resuelve todos los datos de animación en función de current_time.
    
    PRINCIPIO: Todo depende de current_time. Cero timers independientes.
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.visemes  = []
        self.emotions = []
        self.lyrics   = []
        self._emotion_cache = {}

        # Estado de interpolación emocional
        self._current_emotion   = "calm"
        self._prev_emotion      = "calm"
        self._emotion_alpha     = 1.0
        self._last_emotion_time = 0.0

        self.load_data()

    # ── CARGA ─────────────────────────────────────────────────────────────────
    def load_data(self):
        def _load(fname):
            p = os.path.join(self.data_dir, fname)
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            return []

        self.visemes  = _load("visemes.json")
        self.emotions = _load("emotions.json")
        self.lyrics   = _load("lyrics_aligned.json")
        print(f"[Resolver] Cargado: {len(self.visemes)}v {len(self.emotions)}e {len(self.lyrics)}l")

    # ─────────────────────────────────────────────────────────────────────────
    # API PRINCIPAL
    # ─────────────────────────────────────────────────────────────────────────

    def get_current_viseme(self, current_time: float) -> dict:
        """
        Retorna el visema activo en current_time con interpolación suave
        hacia el siguiente visema.
        
        Returns:
            {
                "name": str,
                "shape": dict,          # forma actual interpolada
                "next_shape": dict,     # forma siguiente
                "blend": float,         # 0.0–1.0 hacia next_shape
                "transition": float     # suavizado easing
            }
        """
        if not self.visemes:
            return self._fallback_viseme(current_time)

        # Buscar el visema activo
        active = None
        next_v = None
        for i, v in enumerate(self.visemes):
            if v["start"] <= current_time < v["end"]:
                active = v
                if i + 1 < len(self.visemes):
                    next_v = self.visemes[i + 1]
                break

        if active is None:
            return self._fallback_viseme(current_time)

        seg_dur = max(active["end"] - active["start"], 0.001)
        raw_t   = (current_time - active["start"]) / seg_dur  # 0–1
        # Easing: ease-in-out cúbico
        blend   = self._ease_in_out(raw_t)

        curr_shape = VISEME_SHAPES.get(active["viseme"], VISEME_SHAPES["rest"])
        next_shape = VISEME_SHAPES.get(
            next_v["viseme"] if next_v else "rest",
            VISEME_SHAPES["rest"]
        )

        return {
            "name":       active["viseme"],
            "shape":      curr_shape,
            "next_shape": next_shape,
            "blend":      blend,
            "transition": raw_t,
            "interp":     self._interp_shape(curr_shape, next_shape, blend)
        }

    def get_current_emotion(self, current_time: float, dt: float = 0.016) -> dict:
        """
        Retorna la emoción activa con transición progresiva suavizada.
        
        Returns:
            {
                "name": str,            # emoción dominante
                "prev": str,            # emoción anterior
                "alpha": float,         # 0–1 progreso de transición
                "params": dict          # parámetros de animación interpolados
            }
        """
        raw_emotion = self._lookup_emotion(current_time)

        # Detectar cambio de emoción
        if raw_emotion != self._current_emotion:
            self._prev_emotion    = self._current_emotion
            self._current_emotion = raw_emotion
            self._emotion_alpha   = 0.0

        # Avanzar transición (speed: ~1.5s para transición completa)
        self._emotion_alpha = min(1.0, self._emotion_alpha + dt * 1.5)

        params = self._lerp_emotion_params(
            self._prev_emotion,
            self._current_emotion,
            self._ease_in_out(self._emotion_alpha)
        )

        return {
            "name":  self._current_emotion,
            "prev":  self._prev_emotion,
            "alpha": self._emotion_alpha,
            "params": params
        }

    def get_current_lyric(self, current_time: float) -> dict:
        """
        Retorna la línea de letra activa en current_time.
        
        Returns:
            {
                "line": str,
                "word": str,            # palabra activa
                "progress": float,      # 0–1 dentro de la línea
                "active": bool
            }
        """
        active_word = None
        active_line = ""

        for entry in self.lyrics:
            if entry["start"] <= current_time < entry["end"]:
                active_word = entry["word"]
                active_line = entry.get("line", "")
                seg_dur  = max(entry["end"] - entry["start"], 0.001)
                progress = (current_time - entry["start"]) / seg_dur
                return {
                    "line":     active_line,
                    "word":     active_word,
                    "progress": progress,
                    "active":   True
                }

        return {"line": "", "word": "", "progress": 0.0, "active": False}

    # ─────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _lookup_emotion(self, t: float) -> str:
        for seg in self.emotions:
            if seg["start"] <= t < seg["end"]:
                return seg["emotion"]
        return "calm"

    def _fallback_viseme(self, t: float) -> dict:
        """Visema dinámico sintético cuando no hay datos."""
        cycle = t % 0.6
        names = ["rest", "open", "wide", "round", "teeth", "close"]
        idx   = int((t / 0.6 * 6)) % 6
        name  = names[idx]
        blend = (cycle % 0.1) / 0.1
        curr  = VISEME_SHAPES[name]
        nxt   = VISEME_SHAPES[names[(idx + 1) % 6]]
        return {
            "name": name, "shape": curr, "next_shape": nxt,
            "blend": blend, "transition": blend,
            "interp": self._interp_shape(curr, nxt, blend)
        }

    def _interp_shape(self, a: dict, b: dict, t: float) -> dict:
        """Interpola linealmente entre dos formas de boca."""
        aw = a.get("w", 12); bw = b.get("w", 12)
        ah = a.get("h", 0);  bh = b.get("h", 0)
        return {
            "type": a["type"] if t < 0.5 else b["type"],
            "w":    aw + (bw - aw) * t,
            "h":    ah + (bh - ah) * t,
        }

    @staticmethod
    def _ease_in_out(t: float) -> float:
        """Ease-in-out cúbico: 3t²-2t³"""
        t = max(0.0, min(1.0, t))
        return t * t * (3 - 2 * t)

    # Parámetros de animación por emoción
    EMOTION_PARAMS = {
        "calm": {
            "bounce_freq": 2.0,  "bounce_amp": 4.0,
            "arm_angle": 25.0,   "arm_freq": 1.5,
            "body_lean": 2.0,    "blink_rate": 0.15,
            "scale": 1.0,        "eye_openness": 0.8,
        },
        "happy": {
            "bounce_freq": 3.5,  "bounce_amp": 9.0,
            "arm_angle": 45.0,   "arm_freq": 3.0,
            "body_lean": 5.0,    "blink_rate": 0.22,
            "scale": 1.06,       "eye_openness": 0.9,
        },
        "intense": {
            "bounce_freq": 5.5,  "bounce_amp": 14.0,
            "arm_angle": 70.0,   "arm_freq": 5.5,
            "body_lean": 9.0,    "blink_rate": 0.07,
            "scale": 1.12,       "eye_openness": 1.2,
        },
        "sad": {
            "bounce_freq": 0.8,  "bounce_amp": 2.0,
            "arm_angle": 8.0,    "arm_freq": 0.6,
            "body_lean": 1.0,    "blink_rate": 0.10,
            "scale": 0.94,       "eye_openness": 0.4,
        },
    }

    def _lerp_emotion_params(self, a: str, b: str, t: float) -> dict:
        pa = self.EMOTION_PARAMS.get(a, self.EMOTION_PARAMS["calm"])
        pb = self.EMOTION_PARAMS.get(b, self.EMOTION_PARAMS["calm"])
        return {k: pa[k] + (pb[k] - pa[k]) * t for k in pa}
