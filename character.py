"""
render/character.py
===================
Renderizador del stickman expresivo.
Dibuja el personaje en función de current_time y los datos resueltos.

Todo basado en current_time. Sin estados globales independientes.
"""

import math
import pygame
from typing import Optional


# ─── PALETA EMOCIONAL ─────────────────────────────────────────────────────────

EMOTION_COLORS = {
    "calm":    {"body": (88, 180, 255),  "accent": (55, 138, 221), "eye": (133, 183, 235), "bg": (13, 26, 42)},
    "happy":   {"body": (130, 220, 80),  "accent": (99, 153, 34),  "eye": (151, 196, 89),  "bg": (20, 28, 10)},
    "intense": {"body": (255, 120, 60),  "accent": (216, 90, 48),  "eye": (240, 153, 123), "bg": (26, 13, 13)},
    "sad":     {"body": (175, 169, 236), "accent": (83, 74, 183),  "eye": (143, 136, 214), "bg": (13, 13, 26)},
}

# Color de piel / fondo de cabeza
SKIN_COLOR   = (40, 38, 55)
MOUTH_DARK   = (20, 8, 8)
TEETH_COLOR  = (230, 225, 220)


class StickmanRenderer:
    """
    Dibuja el stickman en el surface de pygame dado.
    
    Parámetros de animación vienen del RuntimeResolver.
    """

    def __init__(self, surface: pygame.Surface, cx: Optional[int] = None, cy: Optional[int] = None):
        self.surface = surface
        self.W, self.H = surface.get_size()
        self.cx = cx or self.W // 2
        self.cy = cy or int(self.H * 0.52)

        # Estado de parpadeo
        self._blink_open = 1.0

        # Superficie temporal para transparencias
        self._overlay = pygame.Surface((self.W, self.H), pygame.SRCALPHA)

        # --- AÑADE ESTO PARA RESOLVER EL ERROR ---
        self._total_dur = 1.0  # Duración total de la canción (evita división por 0)

    # ─────────────────────────────────────────────────────────────────────────
    # FRAME PRINCIPAL
    # ─────────────────────────────────────────────────────────────────────────

    def draw_frame(self, current_time: float, emotion_data: dict, 
                viseme_data: dict, lyric_data: dict, audio_energy: float = 0.5):
        
        # TODO ESTE BLOQUE DEBE TENER UN NIVEL MÁS DE SANGRÍA (4 espacios a la derecha)
        emotion = emotion_data.get("name", "calm")
        ep = emotion_data.get("params", {}) 
        
        self._blink_open = 0.0 if (current_time % 4) < 0.15 else 1.0
        
        self._draw_background(current_time, emotion, ep, audio_energy)
        self._draw_stickman(current_time, emotion, ep, viseme_data, audio_energy)
        self._draw_lyric(lyric_data, current_time, emotion)
        self._draw_hud(current_time, emotion, ep, audio_energy)

    # ─────────────────────────────────────────────────────────────────────────
    # FONDO
    # ─────────────────────────────────────────────────────────────────────────

    def _draw_background(self, t: float, emotion: str, ep: dict, energy: float):
        ec = EMOTION_COLORS[emotion]
        self.surface.fill(ec["bg"])

        # Anillos de ritmo concéntricos
        beat = math.sin(t * ep["bounce_freq"] * math.pi * 2)
        base_r = 160
        ring_r = base_r + beat * 20 * energy
        self._overlay.fill((0, 0, 0, 0))
        for i in range(4):
            r = int(ring_r + i * 35)
            alpha = max(0, 18 - i * 4)
            pygame.draw.circle(
                self._overlay, (*ec["accent"], alpha),
                (self.cx, self.cy), r, 1
            )
        self.surface.blit(self._overlay, (0, 0))

        # Suelo del escenario
        floor_y = self.H - 60
        pygame.draw.line(self.surface, (*ec["accent"], 40), (0, floor_y), (self.W, floor_y), 1)
        floor_surf = pygame.Surface((self.W, 60), pygame.SRCALPHA)
        floor_surf.fill((*ec["accent"], 8))
        self.surface.blit(floor_surf, (0, floor_y))

        # Foco cenital (spotlight)
        for radius, alpha in [(240, 6), (160, 10), (80, 15)]:
            spot = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(spot, (255, 255, 200, alpha), (radius, radius), radius)
            self.surface.blit(spot, (self.cx - radius, 0))

    # ─────────────────────────────────────────────────────────────────────────
    # STICKMAN PRINCIPAL
    # ─────────────────────────────────────────────────────────────────────────

    def _draw_stickman(self, t: float, emotion: str, ep: dict,
                    viseme_data: dict, energy: float):
        ec = EMOTION_COLORS[emotion]

        # ── Movimiento base ───────────────────────────────────────────────────
        bounce = math.sin(t * ep["bounce_freq"] * math.pi * 2) * ep["bounce_amp"] * energy
        lean   = math.sin(t * ep["bounce_freq"] * 0.65 * math.pi * 2) * ep["body_lean"] * energy
        scale  = ep["scale"] + math.sin(t * ep["bounce_freq"] * math.pi * 2) * 0.04 * energy

        # Posición base (con desplazamiento de bounce)
        ox = self.cx + lean
        oy = self.cy + bounce

        # ── Dimensiones escaladas ─────────────────────────────────────────────
        HEAD_R = int(30 * scale)
        NECK   = int(30 * scale)
        TORSO  = int(80 * scale)

        LEG1   = int(65 * scale)
        lw     = max(2, int(2.5 * scale))  # line width

        # ── Puntos clave ──────────────────────────────────────────────────────
        head_c  = (ox, oy - NECK - HEAD_R - TORSO // 2)
        neck_t  = (ox, oy - TORSO // 2)
        body_b  = (ox, oy + TORSO // 2)
        shoulder = (ox, oy - TORSO // 4)

        # ── PIERNAS ───────────────────────────────────────────────────────────
        leg_sway = math.sin(t * ep["bounce_freq"] * math.pi * 2) * 4 * energy
        ll = (int(body_b[0] - 18 + leg_sway), int(body_b[1] + LEG1))
        rl = (int(body_b[0] + 18 - leg_sway), int(body_b[1] + LEG1))
        pygame.draw.line(self.surface, ec["body"], body_b, ll, lw)
        pygame.draw.line(self.surface, ec["body"], body_b, rl, lw)

        # ── CUERPO ────────────────────────────────────────────────────────────
        pygame.draw.line(self.surface, ec["body"], neck_t, body_b, lw)


        # ── CABEZA ────────────────────────────────────────────────────────────
        # Sombra de cabeza
        shadow_surf = pygame.Surface((HEAD_R * 2 + 4, HEAD_R * 2 + 4), pygame.SRCALPHA)
        pygame.draw.circle(shadow_surf, (*ec["accent"], 30),
                        (HEAD_R + 2, HEAD_R + 2), HEAD_R + 2)
        self.surface.blit(shadow_surf, (head_c[0] - HEAD_R - 2, head_c[1] - HEAD_R - 2))

        # Cabeza rellena
        pygame.draw.circle(self.surface, SKIN_COLOR, head_c, HEAD_R)
        pygame.draw.circle(self.surface, ec["body"], head_c, HEAD_R, lw)

        # ── CUELLO ────────────────────────────────────────────────────────────
        pygame.draw.line(self.surface, ec["body"],
                         (head_c[0], head_c[1] + HEAD_R),
                         neck_t, lw)

        # ── CARA ──────────────────────────────────────────────────────────────
        eye_y = head_c[1] - HEAD_R // 5
        eye_off = HEAD_R // 3
        blink = self._compute_blink(t, ep["blink_rate"])

        self._draw_eye(head_c[0] - eye_off, eye_y, blink, emotion, scale, ec)
        self._draw_eye(head_c[0] + eye_off, eye_y, blink, emotion, scale, ec)
        self._draw_mouth(head_c[0], head_c[1] + HEAD_R // 4, viseme_data, emotion, scale, ec)

    def _draw_arms(self, t, emotion, ep, shoulder, arm1, arm2, lw, ec, energy):
        """Dibuja brazos articulados con expresión por emoción."""
        swing  = math.sin(t * ep["arm_freq"] * math.pi * 2) * ep["arm_angle"] * energy
        swing2 = math.sin(t * ep["arm_freq"] * math.pi * 2 + math.pi) * ep["arm_angle"] * energy

        # Ángulo base de brazo por emoción (grados desde horizontal hacia abajo)
        base_angles = {
            "calm":    (120, 60),   # L, R: ligeramente caídos
            "happy":   (100, 80),   # L, R: abiertos hacia afuera
            "intense": (60, 120),   # L, R: levantados
            "sad":     (140, 40),   # L, R: muy caídos
        }
        la_base, ra_base = base_angles.get(emotion, (110, 70))

        # Ángulo brazo izquierdo
        la = math.radians(la_base + swing)
        lax = int(shoulder[0] - arm1 * math.cos(la))
        lay = int(shoulder[1] + arm1 * math.sin(la))

        # Antebrazo izquierdo
        la2 = la + math.radians(-25 + swing * 0.4)
        lfx = int(lax - arm2 * math.cos(la2))
        lfy = int(lay + arm2 * math.sin(la2))

        # Ángulo brazo derecho
        ra = math.radians(ra_base + swing2)
        rax = int(shoulder[0] + arm1 * math.cos(ra))
        ray = int(shoulder[1] + arm1 * math.sin(ra))

        # Antebrazo derecho
        ra2 = ra + math.radians(-25 + swing2 * 0.4)
        rfx = int(rax + arm2 * math.cos(ra2))
        rfy = int(ray + arm2 * math.sin(ra2))

        # Dibujar brazos (con joints visibles)
        pygame.draw.line(self.surface, ec["body"], shoulder, (lax, lay), lw)
        pygame.draw.line(self.surface, ec["body"], (lax, lay), (lfx, lfy), lw)
        pygame.draw.circle(self.surface, ec["accent"], (lax, lay), max(2, lw - 1))

        pygame.draw.line(self.surface, ec["body"], shoulder, (rax, ray), lw)
        pygame.draw.line(self.surface, ec["body"], (rax, ray), (rfx, rfy), lw)
        pygame.draw.circle(self.surface, ec["accent"], (rax, ray), max(2, lw - 1))

    # ─────────────────────────────────────────────────────────────────────────
    # CARA
    # ─────────────────────────────────────────────────────────────────────────

    def _draw_eye(self, x, y, blink, emotion, scale, ec):
        """Dibuja un ojo con estado emocional y parpadeo."""
        r  = max(3, int(5 * scale))
        ey = {
            "calm":    r * 0.85,
            "happy":   r * 0.95,
            "intense": r * 1.25,
            "sad":     r * 0.45,
        }.get(emotion, r)

        open_h = max(1, int(ey * blink))

        # Ojo (elipse)
        eye_rect = pygame.Rect(x - r, y - open_h, r * 2, open_h * 2)
        pygame.draw.ellipse(self.surface, (15, 12, 20), eye_rect)
        pygame.draw.ellipse(self.surface, ec["eye"], eye_rect, 1)

        # Brillo
        if blink > 0.4:
            pygame.draw.circle(self.surface, (240, 240, 255),
                               (x + max(1, r // 3), y - max(1, open_h // 3)), max(1, r // 4))

        # Cejas tristes
        if emotion == "sad":
            brow_w = r + 4
            pygame.draw.line(
                self.surface, ec["body"],
                (x - brow_w, y - r - 4),
                (x + brow_w // 2, y - r - 2), 1
            )

    def _draw_mouth(self, x, y, viseme_data, emotion, scale, ec):
        """Dibuja la boca interpolada entre visemas."""
        interp = viseme_data.get("interp", {"type": "oval", "w": 14, "h": 8})
        mtype  = interp["type"]
        mw     = max(2, int(interp["w"] * scale))
        mh     = max(1, int(interp["h"] * scale))

        mouth_rect = pygame.Rect(x - mw // 2, y - mh // 2, mw, mh)

        if mtype == "line":
            pygame.draw.line(self.surface, ec["accent"],
                             (x - mw // 2, y), (x + mw // 2, y), 2)
        elif mtype == "teeth":
            # Boca abierta con dientes
            pygame.draw.ellipse(self.surface, MOUTH_DARK, mouth_rect)
            pygame.draw.ellipse(self.surface, ec["accent"], mouth_rect, 1)
            # Dientes
            teeth_rect = pygame.Rect(x - mw // 2 + 1, y - mh // 2 + 1, mw - 2, mh // 2)
            pygame.draw.rect(self.surface, TEETH_COLOR, teeth_rect, border_radius=1)
        else:
            # Oval abierta
            pygame.draw.ellipse(self.surface, MOUTH_DARK, mouth_rect)
            pygame.draw.ellipse(self.surface, ec["accent"], mouth_rect, 1)

    # ─────────────────────────────────────────────────────────────────────────
    # PARPADEO
    # ─────────────────────────────────────────────────────────────────────────

    def _compute_blink(self, t: float, blink_rate: float) -> float:
        """
        Calcula apertura del ojo en función de current_time y tasa de parpadeo.
        Completamente determinista basado en t.
        """
        period = max(0.5, 1.0 / blink_rate)
        phase  = math.fmod(t, period) / period  # 0–1

        # Parpadeo ocurre en el 5% final del ciclo
        if phase > 0.95:
            blink_phase = (phase - 0.95) / 0.05  # 0–1
            # Abrir-cerrar rápido
            if blink_phase < 0.5:
                return 1.0 - blink_phase * 2.0  # cerrar
            else:
                return (blink_phase - 0.5) * 2.0  # abrir
        return 1.0

    # ─────────────────────────────────────────────────────────────────────────
    # LETRA
    # ─────────────────────────────────────────────────────────────────────────

    def _draw_lyric(self, lyric_data: dict, t: float, emotion: str):
        if not lyric_data.get("active") or not lyric_data.get("line"):
            return
        ec = EMOTION_COLORS[emotion]

        font = pygame.font.SysFont("Arial", 20, bold=True)
        text = lyric_data["line"]

        # Posición con micro-bounce
        y_bounce = math.sin(t * 4) * 2
        y = self.H - 38 + y_bounce

        # Sombra
        shadow = font.render(text, True, (0, 0, 0))
        sr = shadow.get_rect(center=(self.W // 2 + 1, int(y) + 1))
        self.surface.blit(shadow, sr)

        # Texto principal (color lira dorada)
        surf = font.render(text, True, (250, 199, 117))
        r = surf.get_rect(center=(self.W // 2, int(y)))
        self.surface.blit(surf, r)

        # Subrayado de la palabra activa
        word = lyric_data.get("word", "")
        if word:
            self._highlight_word(text, word, font, int(y), ec)

    def _highlight_word(self, line, word, font, y, ec):
        """Resalta la palabra activa en la línea."""
        try:
            idx = line.find(word)
            if idx < 0:
                return
            before_w = font.size(line[:idx])[0]
            word_w   = font.size(word)[0]
            line_w   = font.size(line)[0]
            start_x  = self.W // 2 - line_w // 2 + before_w
            pygame.draw.line(
                self.surface, ec["accent"],
                (start_x, y + 12),
                (start_x + word_w, y + 12), 2
            )
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # HUD
    # ─────────────────────────────────────────────────────────────────────────

    def _draw_hud(self, t: float, emotion: str, ep: dict, energy: float):
        """HUD de debug: tiempo, emoción, energía."""
        font_sm = pygame.font.SysFont("Arial", 12)
        ec = EMOTION_COLORS[emotion]

        # Tiempo
        t_surf = font_sm.render(f"{t:.2f}s", True, (120, 120, 140))
        self.surface.blit(t_surf, (8, 8))

        # Emoción
        em_surf = font_sm.render(f"● {emotion.upper()}", True, ec["body"])
        self.surface.blit(em_surf, (self.W - 90, 8))

        # Barra de energía
        bar_w = int(60 * energy)
        pygame.draw.rect(self.surface, (40, 40, 55), pygame.Rect(self.W - 90, 24, 60, 6))
        pygame.draw.rect(self.surface, ec["accent"], pygame.Rect(self.W - 90, 24, bar_w, 6))

        # Barra de progreso
        if hasattr(self, "_total_dur") and self._total_dur:
            prog_w = int((self.W - 40) * min(t / self._total_dur, 1))
            pygame.draw.rect(self.surface, (30, 30, 45), pygame.Rect(20, self.H - 8, self.W - 40, 3))
            pygame.draw.rect(self.surface, ec["accent"], pygame.Rect(20, self.H - 8, prog_w, 3))
