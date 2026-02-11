import { useRef, useCallback } from 'react'

/**
 * Generates pleasant elevator / hold music using the Web Audio API.
 * No external audio file required — entirely synthesized in-browser.
 *
 * Returns { startMusic, stopMusic } callbacks.
 */
export default function useHoldMusic(volume = 0.15) {
    const ctxRef = useRef(null)
    const nodesRef = useRef([])       // oscillators + gains to stop later
    const intervalRef = useRef(null)
    const playingRef = useRef(false)

    // ---- musical constants ----
    // A calming jazz-lounge chord progression (Cmaj7 → Am7 → Dm7 → G7)
    const CHORDS = [
        [261.63, 329.63, 392.00, 493.88],   // Cmaj7  (C E G B)
        [220.00, 261.63, 329.63, 392.00],   // Am7   (A C E G)
        [293.66, 349.23, 440.00, 523.25],   // Dm7   (D F A C)
        [196.00, 246.94, 293.66, 349.23],   // G7    (G B D F)
    ]
    const CHORD_DURATION = 2.4  // seconds per chord
    const FADE_TIME = 0.6       // crossfade between chords

    /**
     * Play a single chord that fades in and out.
     */
    const playChord = useCallback((ctx, frequencies, startTime, duration) => {
        const masterGain = ctx.createGain()
        masterGain.gain.setValueAtTime(0, startTime)
        masterGain.gain.linearRampToValueAtTime(volume, startTime + FADE_TIME)
        masterGain.gain.setValueAtTime(volume, startTime + duration - FADE_TIME)
        masterGain.gain.linearRampToValueAtTime(0, startTime + duration)
        masterGain.connect(ctx.destination)

        frequencies.forEach((freq, i) => {
            const osc = ctx.createOscillator()
            osc.type = i === 0 ? 'triangle' : 'sine'  // root triangle, rest sine
            osc.frequency.value = freq

            // Per-note gain so root is slightly louder
            const noteGain = ctx.createGain()
            noteGain.gain.value = i === 0 ? 0.5 : 0.3
            osc.connect(noteGain)
            noteGain.connect(masterGain)

            osc.start(startTime)
            osc.stop(startTime + duration + 0.1)

            nodesRef.current.push(osc)
        })

        nodesRef.current.push(masterGain)
    }, [volume])

    /**
     * Schedule the looping chord progression.
     */
    const scheduleLoop = useCallback((ctx) => {
        const now = ctx.currentTime
        CHORDS.forEach((chord, i) => {
            playChord(ctx, chord, now + i * CHORD_DURATION, CHORD_DURATION + FADE_TIME)
        })
    }, [playChord])

    /**
     * Start the hold music. Safe to call multiple times (idempotent).
     */
    const startMusic = useCallback(() => {
        if (playingRef.current) return

        const ctx = new (window.AudioContext || window.webkitAudioContext)()
        ctxRef.current = ctx
        playingRef.current = true

        // Play first loop immediately
        scheduleLoop(ctx)

        // Re-schedule every full cycle
        const cycleMs = CHORDS.length * CHORD_DURATION * 1000
        intervalRef.current = setInterval(() => {
            if (ctx.state === 'running') {
                scheduleLoop(ctx)
            }
        }, cycleMs)
    }, [scheduleLoop])

    /**
     * Stop the hold music with a quick fade-out.
     */
    const stopMusic = useCallback(() => {
        if (!playingRef.current) return
        playingRef.current = false

        if (intervalRef.current) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
        }

        const ctx = ctxRef.current
        if (ctx) {
            // Quick fade-out on everything, then close
            try {
                const now = ctx.currentTime
                nodesRef.current.forEach(node => {
                    if (node instanceof GainNode) {
                        node.gain.cancelScheduledValues(now)
                        node.gain.setValueAtTime(node.gain.value, now)
                        node.gain.linearRampToValueAtTime(0, now + 0.3)
                    }
                    if (node instanceof OscillatorNode) {
                        try { node.stop(now + 0.4) } catch { /* already stopped */ }
                    }
                })
            } catch { /* ignore */ }

            setTimeout(() => {
                try { ctx.close() } catch { /* ignore */ }
            }, 500)
        }

        nodesRef.current = []
        ctxRef.current = null
    }, [])

    return { startMusic, stopMusic }
}
