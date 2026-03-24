/* Genshin Impact Style Sound Synthesizer */
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

const GenshinFX = {
    // Mora Clink - High pitched metallic coin sound
    mora: () => {
        if (audioCtx.state === 'suspended') audioCtx.resume();
        const t = audioCtx.currentTime;

        // Multiple oscillators for richness
        const freqs = [1200, 2400, 3600];
        freqs.forEach((f, i) => {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();

            osc.type = 'sine';
            osc.frequency.setValueAtTime(f, t);
            osc.frequency.exponentialRampToValueAtTime(f * 0.9, t + 0.3);

            gain.gain.setValueAtTime(0.05 / (i + 1), t);
            gain.gain.exponentialRampToValueAtTime(0.001, t + 0.3);

            osc.connect(gain);
            gain.connect(audioCtx.destination);

            osc.start(t);
            osc.stop(t + 0.3);
        });
    },

    // UI Click - High pitched "blip"
    click: () => {
        if (audioCtx.state === 'suspended') audioCtx.resume();
        const t = audioCtx.currentTime;

        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(800, t);
        osc.frequency.exponentialRampToValueAtTime(1200, t + 0.1);

        gain.gain.setValueAtTime(0.1, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.1);

        osc.connect(gain);
        gain.connect(audioCtx.destination);

        osc.start(t);
        osc.stop(t + 0.1);
    },

    // Chest Open - Magical Fanfare
    chest: () => {
        if (audioCtx.state === 'suspended') audioCtx.resume();
        const t = audioCtx.currentTime;

        // A Major Arpeggio with sparkly noise
        const notes = [440, 554, 659, 880, 1108, 1318];
        notes.forEach((freq, i) => {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();

            osc.type = 'triangle';
            osc.frequency.value = freq;

            gain.gain.setValueAtTime(0, t + (i * 0.05));
            gain.gain.linearRampToValueAtTime(0.05, t + (i * 0.05) + 0.05);
            gain.gain.exponentialRampToValueAtTime(0.001, t + (i * 0.05) + 0.5);

            osc.connect(gain);
            gain.connect(audioCtx.destination);

            osc.start(t);
            osc.stop(t + 1.5);
        });
    }
};

window.playGenshinSound = (name) => {
    if (GenshinFX[name]) GenshinFX[name]();
};

window.initAudio = () => {
    if (audioCtx.state === 'suspended') audioCtx.resume();
};
