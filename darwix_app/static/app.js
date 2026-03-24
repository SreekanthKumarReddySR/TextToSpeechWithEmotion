const voiceSelect = document.getElementById("voice-select");
const genderSelect = document.getElementById("gender-select");
const ttsForm = document.getElementById("tts-form");
const storyForm = document.getElementById("story-form");
const globalLoader = document.getElementById("global-loader");

let voices = [];

function toggleLoader(show) {
    globalLoader.classList.toggle("hidden", !show);
}

async function loadVoices() {
    const response = await fetch("/api/voices");
    const data = await response.json();
    voices = data.voices || [];
    renderVoices();
}

function renderVoices() {
    const gender = genderSelect.value;
    const matching = voices.filter((voice) => voice.gender === gender);
    voiceSelect.innerHTML = matching
        .map((voice) => `<option value="${voice.id}">${voice.label}</option>`)
        .join("");
}

genderSelect.addEventListener("change", renderVoices);

ttsForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const status = document.getElementById("tts-status");
    const result = document.getElementById("tts-result");
    const payload = Object.fromEntries(new FormData(ttsForm).entries());
    toggleLoader(true);
    status.textContent = "Analyzing emotion and synthesizing speech...";
    result.classList.add("hidden");

    try {
        const response = await fetch("/api/challenge-1/synthesize", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Unable to generate audio.");
        }

        document.getElementById("emotion-value").textContent = data.emotion;
        document.getElementById("intensity-value").textContent = data.intensity;
        document.getElementById("pitch-value").textContent = data.parameters.pitch;
        document.getElementById("rate-value").textContent = data.parameters.rate;
        document.getElementById("volume-value").textContent = data.parameters.volume;
        document.getElementById("mapping-reason").textContent = data.mapping_reason;
        document.getElementById("analysis-reason").textContent = data.analysis_reason;
        document.getElementById("analysis-provider").textContent = data.analysis_provider;
        document.getElementById("audio-player").src = data.audio_url;
        result.classList.remove("hidden");
        status.textContent = "Audio generated successfully.";
    } catch (error) {
        status.textContent = error.message;
    } finally {
        toggleLoader(false);
    }
});

storyForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const status = document.getElementById("story-status");
    const result = document.getElementById("story-result");
    const payload = Object.fromEntries(new FormData(storyForm).entries());
    toggleLoader(true);
    status.textContent = "Breaking narrative into scenes and generating storyboard...";
    result.classList.add("hidden");

    try {
        const response = await fetch("/api/challenge-2/storyboard", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Unable to generate storyboard.");
        }

        result.innerHTML = data.panels.map((panel, index) => `
            <article class="story-card">
                <div class="story-image-wrap">
                    <img src="${panel.image_url}" alt="Storyboard panel ${index + 1}">
                </div>
                <h4>Scene ${index + 1}</h4>
                <p><strong>Caption:</strong> ${panel.caption}</p>
                <p><strong>Prompt:</strong> ${panel.prompt}</p>
                <p><strong>Source:</strong> ${panel.source}</p>
            </article>
        `).join("");
        result.classList.remove("hidden");
        status.textContent = "Storyboard generated successfully.";
    } catch (error) {
        status.textContent = error.message;
    } finally {
        toggleLoader(false);
    }
});

loadVoices();
