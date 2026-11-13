// speak.js — read the page aloud with the voice built into the browser.
// Helps people who find reading hard. Runs on the device; no audio is uploaded.

export const canSpeak = "speechSynthesis" in window;

// Speak the sentences one after another. Calling it again while talking stops it.
export function toggleSpeech(sentences, lang, onChange) {
  if (speechSynthesis.speaking) {
    speechSynthesis.cancel();
    onChange(false);
    return;
  }
  sentences.forEach((sentence, index) => {
    const utterance = new SpeechSynthesisUtterance(sentence);
    utterance.lang = lang === "fr" ? "fr-CA" : "en-CA";
    utterance.rate = 0.95;
    if (index === sentences.length - 1) utterance.onend = () => onChange(false);
    speechSynthesis.speak(utterance);
  });
  onChange(true);
}
