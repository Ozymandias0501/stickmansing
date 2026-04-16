# -*- coding: utf-8 -*-
"""
main.py
=======
Sistema completo de animación de stickman con lip-sync.

Uso:
    python main.py

Configura AUDIO_PATH y LYRICS abajo.
"""
import asyncio
import sys
import os
import math
import json
import pygame

# Imports de tus archivos locales
from preprocessor import Preprocessor
from resolver import RuntimeResolver
from character import StickmanRenderer

# ── Verificar pygame ──────────────────────────────────────────────────────────
try:
    import pygame
except ImportError:
    print("ERROR: pygame no instalado.")
    print("Instala con: pip install pygame librosa numpy scipy")
    sys.exit(1)

# ── Imports locales ───────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN — EDITA AQUÍ
# ═══════════════════════════════════════════════════════════════════════════════

AUDIO_PATH  = "audio/no tengo dinero - juanes (letra).mp3"          # Ruta a tu archivo WAV
DATA_DIR    = "data"                     # Carpeta de datos preprocesados
OUTPUT_DIR  = "data"

LYRICS = """
13.2 - 16.5 | Voy por la calle de la mano platicando con mi amor
16.6 - 20.0 | Y voy recordando cosas serias que me pueden suceder
20.1 - 23.5 | Pues ya me pregunta que hasta cuando nos iremos a casar
23.6 - 27.5 | Y yo le contesto que soy pobre que me tiene que esperar
27.6 - 29.8 | No tengo dinero ni nada que dar
29.9 - 32.5 | Lo único que tengo es amor para amar
32.6 - 34.8 | Si así tú me quieres te puedo querer
34.9 - 37.5 | Pero si no puedes ni modo que hacer
37.6 - 40.0 | No tengo dinero ni nada que dar
40.1 - 42.5 | Lo único que tengo es amor para amar
42.6 - 44.8 | Si así tú me quieres te puedo querer
44.9 - 47.5 | Pero si no puedes ni modo que hacer
47.6 - 51.0 | Yo sé que a mi lado tú te sientes pero mucho muy feliz
51.1 - 54.5 | Y sé que al decirte que soy pobre no vuelves a sonreír
54.6 - 58.0 | Que va, yo quisiera tener todo y ponerlo a tus pies
58.1 - 61.5 | Pero yo nací pobre y es por eso que no me puedes querer
61.6 - 63.8 | No tengo dinero ni nada que dar
63.9 - 66.5 | Lo único que tengo es amor para dar
66.6 - 68.8 | Si así tú me quieres te puedo querer
68.9 - 71.5 | Pero si no puedes ni modo que hacer
71.6 - 73.8 | No tengo dinero ni nada que dar
73.9 - 76.5 | Lo único que tengo es amor para dar
76.6 - 78.8 | Si así tú me quieres te puedo querer
78.9 - 82.0 | Pero si no puedes ni modo que hacer
"""

# ── Ventana ────────────────────────────────────────────────────────────────────
WINDOW_W  = 800
WINDOW_H  = 500
FPS_TARGET = 60
TITLE      = "🎵 Stickman Lip-Sync Performer"

# ── Offset manual si hay desfase audio/animación (segundos) ────────────────────
ANIMATION_OFFSET = 0.0   # positivo = animación adelantada


# ═══════════════════════════════════════════════════════════════════════════════
# PREPROCESAMIENTO
# ═══════════════════════════════════════════════════════════════════════════════

def run_preprocessing() -> dict:
    """Corre la fase de preprocesamiento si no existe ya."""
    meta_path = os.path.join(DATA_DIR, "meta.json")
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
        print(f"[Main] Datos existentes encontrados ({meta['duration']:.1f}s). Usando.")
        return meta

    print("[Main] Corriendo preprocesamiento...")
    prep = Preprocessor(
        audio_path=AUDIO_PATH,
        lyrics_raw=LYRICS,
        output_dir=DATA_DIR
    )
    return prep.run()


# ═══════════════════════════════════════════════════════════════════════════════
# AUDIO PLAYER
# ═══════════════════════════════════════════════════════════════════════════════

def setup_audio() -> tuple:
    """
    Carga el audio y retorna (music_loaded: bool, duration: float).
    """
    if not os.path.exists(AUDIO_PATH):
        print(f"[Audio] '{AUDIO_PATH}' no encontrado. Corriendo en modo silencioso.")
        return False, 20.0

    try:
        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.music.load(AUDIO_PATH)
        print(f"[Audio] Cargado: {AUDIO_PATH}")
        return True, None
    except Exception as e:
        print(f"[Audio] Error: {e}")
        return False, 20.0


# ═══════════════════════════════════════════════════════════════════════════════
# ANÁLISIS DE ENERGÍA EN TIEMPO REAL (opcional, si numpy disponible)
# ═══════════════════════════════════════════════════════════════════════════════

def get_realtime_energy(t: float, emotions: list) -> float:
    """
    Retorna la energía normalizada en el tiempo t.
    Cae back a energía sintética basada en emoción.
    """
    for seg in emotions:
        if seg["start"] <= t < seg["end"]:
            return min(1.0, seg.get("energy", 0.3) * 4)

    # Sintético: pulso basado en tiempo
    return 0.3 + 0.4 * abs(math.sin(t * 3))


# ═══════════════════════════════════════════════════════════════════════════════
# LOOP PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    print("\n" + "═" * 50)
    print("   STICKMAN LIP-SYNC PERFORMER")
    print("═" * 50)

    # 1. Preprocesamiento
    meta = run_preprocessing()
    total_duration = meta.get("duration", 20.0)

    # 2. Resolver de runtime
    resolver = RuntimeResolver(data_dir=DATA_DIR)

    # Cargar emociones para energía
    emotions_path = os.path.join(DATA_DIR, "emotions.json")
    emotions_data = []
    if os.path.exists(emotions_path):
        with open(emotions_path) as f:
            emotions_data = json.load(f)

    # 3. Pygame
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption(TITLE)
    clock  = pygame.time.Clock()

    # 4. Audio
    music_loaded, _ = setup_audio()

    # 5. Renderer
    renderer = StickmanRenderer(screen, WINDOW_W // 2, int(WINDOW_H * 0.50))
    renderer._total_dur = total_duration

    # 6. Estado
    t           = 0.0
    running     = True
    paused      = False
    started     = False
    start_ticks = 0
    pause_ticks = 0
    dt_accum    = 0.0

    print("\n[Main] Listo. Presiona SPACE para iniciar/pausar. ESC para salir.")
    print(f"       Duración: {total_duration:.1f}s | FPS target: {FPS_TARGET}")
    print(f"       Controles: SPACE=play/pause  ESC=salir  R=reiniciar  ←/→=±0.5s\n")

    # ── LOOP ──────────────────────────────────────────────────────────────────
    while running:
        dt = clock.tick(FPS_TARGET) / 1000.0  # segundos reales

        # ── EVENTOS ───────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key == pygame.K_SPACE:
                    if not started:
                        # Primer arranque
                        started = True
                        start_ticks = pygame.time.get_ticks()
                        if music_loaded:
                            pygame.mixer.music.play()
                        paused = False
                        print("[Main] ▶ Reproduciendo...")
                    elif paused:
                        # Reanudar
                        paused = False
                        pause_dur = pygame.time.get_ticks() - pause_ticks
                        start_ticks += pause_dur
                        if music_loaded:
                            pygame.mixer.music.unpause()
                        print(f"[Main] ▶ Reanudado en {t:.2f}s")
                    else:
                        # Pausar
                        paused = True
                        pause_ticks = pygame.time.get_ticks()
                        if music_loaded:
                            pygame.mixer.music.pause()
                        print(f"[Main] ⏸ Pausado en {t:.2f}s")

                elif event.key == pygame.K_r:
                    # Reiniciar
                    t = 0.0
                    started = False
                    paused = False
                    start_ticks = 0
                    if music_loaded:
                        pygame.mixer.music.stop()
                    print("[Main] ↺ Reiniciado")

                elif event.key == pygame.K_RIGHT and started:
                    t = min(t + 0.5, total_duration)
                    start_ticks = pygame.time.get_ticks() - int(t * 1000)
                    if music_loaded:
                        pygame.mixer.music.set_pos(t)

                elif event.key == pygame.K_LEFT and started:
                    t = max(t - 0.5, 0.0)
                    start_ticks = pygame.time.get_ticks() - int(t * 1000)
                    if music_loaded:
                        pygame.mixer.music.set_pos(t)

        # ── TIEMPO ────────────────────────────────────────────────────────────
        if started and not paused:
            # Tiempo desde audio (si disponible) o reloj
            if music_loaded:
                t = pygame.mixer.music.get_pos() / 1000.0 + ANIMATION_OFFSET
                t = max(0.0, t)
            else:
                t = (pygame.time.get_ticks() - start_ticks) / 1000.0 + ANIMATION_OFFSET

            if t >= total_duration:
                t = total_duration
                started = False
                paused  = False
                if music_loaded:
                    pygame.mixer.music.stop()
                print("[Main] ■ Reproducción terminada")

        # ── RESOLUCIÓN DE DATOS ────────────────────────────────────────────────
        emotion_data = resolver.get_current_emotion(t, dt)
        viseme_data  = resolver.get_current_viseme(t)
        lyric_data   = resolver.get_current_lyric(t)
        energy       = get_realtime_energy(t, emotions_data)

        # ── RENDER ────────────────────────────────────────────────────────────
        renderer.draw_frame(t, emotion_data, viseme_data, lyric_data, energy)

        # ── OVERLAY: pantalla de espera ────────────────────────────────────────
        if not started:
            font_big = pygame.font.SysFont("Arial", 28, bold=True)
            font_sm  = pygame.font.SysFont("Arial", 15)
            msg1 = font_big.render("🎵 STICKMAN PERFORMER", True, (200, 180, 255))
            msg2 = font_sm.render("Presiona SPACE para comenzar", True, (150, 150, 180))
            screen.blit(msg1, msg1.get_rect(center=(WINDOW_W//2, WINDOW_H//2 - 20)))
            screen.blit(msg2, msg2.get_rect(center=(WINDOW_W//2, WINDOW_H//2 + 18)))

        # FPS display
        fps_surf = pygame.font.SysFont("Arial", 11).render(
            f"FPS: {clock.get_fps():.0f}", True, (60, 60, 80))
        screen.blit(fps_surf, (8, WINDOW_H - 20))

        pygame.display.flip()
        await asyncio.sleep(0)

    # ── SALIDA ────────────────────────────────────────────────────────────────
    if music_loaded:
        pygame.mixer.music.stop()
    pygame.quit()
    print("[Main] Cerrado.")


# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    asyncio.run(main())