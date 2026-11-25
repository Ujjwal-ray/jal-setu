// A short two-note chime made with the Web Audio API, so no sound file is needed.
// Browsers only allow sound once the person has clicked, tapped or typed on the site. Before that
// the chime stays silent, and the toast and the count in the tab title still announce the request.

let ctx: AudioContext | null = null;

function play(ac: AudioContext) {
  const start = ac.currentTime + 0.02;
  [880, 1318.5].forEach((freq, i) => {
    const t = start + i * 0.16;
    const osc = ac.createOscillator();
    const gain = ac.createGain();
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.0001, t);
    gain.gain.exponentialRampToValueAtTime(0.2, t + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.4);
    osc.connect(gain).connect(ac.destination);
    osc.start(t);
    osc.stop(t + 0.45);
  });
}

export function chime() {
  try {
    const ac = (ctx ??= new AudioContext());
    const asked = Date.now();
    ac.resume()
      .then(() => {
        // if sound was blocked until a later click, a late chime would only confuse
        if (Date.now() - asked < 2000) play(ac);
      })
      .catch(() => {});
  } catch {
    /* no Web Audio in this browser */
  }
}
