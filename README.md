# Darwix AI Studio

Darwix AI Studio is a Flask-based assignment submission that combines both required challenges in one product:

- **Challenge 1: The Empathy Engine**
- **Challenge 2: The Pitch Visualizer**

The app includes login and signup, MongoDB-backed user accounts, expressive text-to-speech with voice selection, and Gemini-powered storyboard generation with styled visual panels.

## Highlights

- Flask web app with login, signup, and dashboard flows
- MongoDB-backed authentication
- Gemini-powered emotion analysis with granular emotions
- Voice selection for male and female voices
- Runtime control over `pitch`, `rate`, and `volume`
- Playable audio output for Challenge 1
- Narrative segmentation, prompt engineering, and styled storyboard generation for Challenge 2
- Animated text-to-speech logo and processing state in the UI
- Fallback behavior for both analysis and image generation

## Project structure

```text
.
|-- darwix_app/
|   |-- __init__.py
|   |-- config.py
|   |-- models.py
|   |-- routes/
|   |   |-- api.py
|   |   `-- web.py
|   |-- services/
|   |   |-- auth_service.py
|   |   |-- database.py
|   |   |-- empathy_engine.py
|   |   |-- emotion_service.py
|   |   |-- storyboard_service.py
|   |   `-- tts_service.py
|   |-- static/
|   |   |-- app.js
|   |   |-- auth.js
|   |   `-- styles.css
|   `-- templates/
|       |-- auth.html
|       `-- dashboard.html
|-- storage/
|   |-- audio/
|   `-- storyboards/
|-- .env
|-- .env.example
|-- requirements.txt
`-- run.py
```

## Setup

1. Create and activate a virtual environment:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

3. Create your environment file if needed:

```powershell
Copy-Item .env.example .env
```

4. Make sure `.env` contains:

```env
SECRET_KEY=your_secret
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-2.5-flash
GEMINI_IMAGE_MODEL=gemini-2.0-flash-preview-image-generation
MONGO_URI=your_mongodb_uri
MONGO_DB_NAME=darwix_assignment
```

## Run

```powershell
python run.py
```

Open `http://127.0.0.1:5000`.

## Challenge 1: The Empathy Engine

Input text is analyzed into richer emotional states such as:

- `happy`
- `excited`
- `neutral`
- `concerned`
- `sad`
- `frustrated`
- `angry`
- `inquisitive`
- `surprised`

That emotion is mapped to:

- `pitch`
- `rate`
- `volume`
- selected voice

The app uses Edge TTS so the user can choose a male or female voice and hear more expressive speech than the earlier local prototype.

### Low-Level Design

```mermaid
flowchart LR
    A[User Input Text] --> B[Gemini Emotion Analyzer]
    B --> C[Emotion and Intensity Mapper]
    C --> D[Voice Profile Builder<br/>Pitch • Rate • Volume • Voice]
    D --> E[TTS Engine Layer<br/>Edge TTS or pyttsx3]
    E --> F[Playable Audio Output]

    classDef warm fill:#FBE9E1,stroke:#C35C38,color:#3A251A,stroke-width:2px;
    class A,B,C,D,E,F warm;
```

## Challenge 2: The Pitch Visualizer

The app accepts a narrative block, breaks it into scenes, enhances each scene into a more visual prompt with Gemini, and generates a storyboard panel for each scene.

Bonus features included:

- user-selectable visual style
- Gemini prompt refinement
- dynamic storyboard UI
- basic visual consistency through shared style guidance

If image generation fails during runtime, the app creates clean placeholder storyboard panels so the demo can still proceed.

### Low-Level Design

```mermaid
flowchart LR
    A[Narrative Input] --> B[Scene Segmentation]
    B --> C[Gemini Prompt Refiner]
    C --> D[Image Generation Layer]
    D --> E[Storyboard Composer]
    E --> F[Visual Panels in UI]

    classDef cool fill:#E5F5F2,stroke:#0E7C73,color:#183432,stroke-width:2px;
    class A,B,C,D,E,F cool;
```

## API overview

- `POST /api/auth/signup`
- `POST /api/auth/login`
- `GET /api/voices`
- `POST /api/challenge-1/synthesize`
- `POST /api/challenge-2/storyboard`

## Notes

- `.env` is ignored by Git, so your Gemini key and Mongo URI stay out of version control.
- `edge-tts` depends on network access at runtime.
- Gemini image generation support can vary by key and model availability, so the placeholder fallback is included to keep the assignment demo resilient.
