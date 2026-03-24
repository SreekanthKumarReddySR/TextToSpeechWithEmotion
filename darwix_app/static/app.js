const voiceSelect = document.getElementById("voice-select");
const genderSelect = document.getElementById("gender-select");
const ttsForm = document.getElementById("tts-form");
const storyForm = document.getElementById("story-form");
const globalLoader = document.getElementById("global-loader");
const storyResult = document.getElementById("story-result");
const storyTrack = document.getElementById("story-track");
const storyThumbs = document.getElementById("story-thumbs");
const storyCaption = document.getElementById("story-caption");
const storyPrev = document.getElementById("story-prev");
const storyNext = document.getElementById("story-next");

let voices = [];
let storyboardPanels = [];
let activeStoryIndex = 0;

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

function updateStoryCarousel(index) {
    if (!storyboardPanels.length) return;
    activeStoryIndex = (index + storyboardPanels.length) % storyboardPanels.length;
    storyTrack.style.transform = `translateX(-${activeStoryIndex * 100}%)`;

    const panel = storyboardPanels[activeStoryIndex];
    storyCaption.innerHTML = `
        <div class="caption-top">
            <span class="story-kicker">Scene ${activeStoryIndex + 1}</span>
            <span class="story-source">${panel.source}</span>
        </div>
        <h4>${panel.caption}</h4>
        <p>${panel.prompt}</p>
    `;

    [...storyThumbs.children].forEach((thumb, thumbIndex) => {
        thumb.classList.toggle("is-active", thumbIndex === activeStoryIndex);
    });
}

function renderStoryCarousel(panels) {
    storyboardPanels = panels;
    activeStoryIndex = 0;

    storyTrack.innerHTML = panels.map((panel, index) => `
        <article class="story-slide" data-index="${index}">
            <img src="${panel.image_url}" alt="Storyboard panel ${index + 1}">
        </article>
    `).join("");

    storyThumbs.innerHTML = panels.map((panel, index) => `
        <button type="button" class="thumb ${index === 0 ? "is-active" : ""}" data-index="${index}">
            <img src="${panel.image_url}" alt="Thumbnail ${index + 1}">
            <span>Scene ${index + 1}</span>
        </button>
    `).join("");

    storyThumbs.querySelectorAll(".thumb").forEach((thumb) => {
        thumb.addEventListener("click", () => updateStoryCarousel(Number(thumb.dataset.index)));
    });

    updateStoryCarousel(0);
}

genderSelect.addEventListener("change", renderVoices);
storyPrev.addEventListener("click", () => updateStoryCarousel(activeStoryIndex - 1));
storyNext.addEventListener("click", () => updateStoryCarousel(activeStoryIndex + 1));

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
        if (!response.ok) throw new Error(data.error || "Unable to generate audio.");

        document.getElementById("emotion-value").textContent = data.emotion;
        document.getElementById("intensity-value").textContent = data.intensity;
        document.getElementById("pitch-value").textContent = data.parameters.pitch;
        document.getElementById("rate-value").textContent = data.parameters.rate;
        document.getElementById("volume-value").textContent = data.parameters.volume;
        document.getElementById("mapping-reason").textContent = data.mapping_reason;
        document.getElementById("analysis-reason").textContent = data.analysis_reason;
        document.getElementById("analysis-provider").textContent = data.analysis_provider;
        document.getElementById("tts-provider").textContent = data.tts_provider;
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
    const payload = Object.fromEntries(new FormData(storyForm).entries());
    toggleLoader(true);
    status.textContent = "Breaking narrative into scenes and generating storyboard...";
    storyResult.classList.add("hidden");

    try {
        const response = await fetch("/api/challenge-2/storyboard", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Unable to generate storyboard.");

        renderStoryCarousel(data.panels);
        storyResult.classList.remove("hidden");
        status.textContent = "Storyboard generated successfully.";
    } catch (error) {
        status.textContent = error.message;
    } finally {
        toggleLoader(false);
    }
});

loadVoices();
