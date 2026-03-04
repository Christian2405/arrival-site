"""
Demo mode service — returns realistic canned HVAC/trade responses.
No API keys needed. Perfect for demos and investor presentations.
"""

import base64
import struct

# --- Canned Chat Responses ---

DEMO_RESPONSES = [
    {
        "keywords": ["fault", "code", "error", "e4", "e3", "code 13"],
        "response": "That's a Carrier 50XC Code 13 — it indicates a lockout due to ignition failure. Check the contactor and transformer first. This is common on startup cycles, especially after a power outage. If the contactor checks out, inspect the flame sensor for carbon buildup. Clean it with fine steel wool if needed.",
        "source": "Carrier 50XC Service Manual, Section 4, p.47",
        "confidence": "high",
    },
    {
        "keywords": ["reset", "restart", "reboot", "clear"],
        "response": "To reset the unit: Power off at the disconnect for 30 seconds, then restore power. Wait for the thermostat to call for heating or cooling. If the fault persists after reset, check the indoor/outdoor thermostat wiring — specifically the Y and C terminals. A loose C wire is the most common cause of repeat lockouts.",
        "source": "Carrier Service Manual, Troubleshooting Guide",
        "confidence": "high",
    },
    {
        "keywords": ["wire", "wiring", "terminal", "connect", "gauge"],
        "response": "For that unit, you'll want 14 AWG THHN for the line voltage side and 18 AWG thermostat wire for the control side. Make sure you're using copper, not aluminum. The terminal block should be torqued to 35 inch-pounds — over-tightening is a common cause of terminal failures in the field.",
        "source": "NEC Article 310.15, Carrier Installation Guide",
        "confidence": "high",
    },
    {
        "keywords": ["refrigerant", "charge", "pressure", "r410a", "r22", "superheat", "subcool"],
        "response": "For R-410A on this unit, you want a target subcooling of 10-12 degrees and superheat of 8-12 degrees at the service valves. At 95F outdoor ambient, your liquid line pressure should be around 350-380 PSI and suction around 118-128 PSI. If subcooling is low, you're undercharged. If superheat is low, you're overcharged.",
        "source": "Carrier 50XC Charging Chart, AHRI Standard 210/240",
        "confidence": "high",
    },
    {
        "keywords": ["leak", "water", "drain", "clog", "condensate"],
        "response": "Water around the indoor unit usually means a clogged condensate drain. Check the primary drain pan and the P-trap first — pour a cup of white vinegar through the drain line. If it's backing up, use a wet/dry vac on the outdoor drain termination. Also check that the drain pan isn't cracked — that's common on units over 10 years old.",
        "source": "ACCA Standard 5, Carrier Maintenance Guide",
        "confidence": "high",
    },
    {
        "keywords": ["compressor", "not starting", "won't start", "capacitor", "contactor"],
        "response": "If the compressor won't start but the fan runs, check the run capacitor first — it's the most common failure point. Use your meter to check microfarads; if it's more than 10% below the rated value, replace it. Also check the compressor contactor for pitting on the contact points. If you hear a humming but no start, the compressor might be locked rotor — check the start winding resistance.",
        "source": "Carrier Compressor Diagnostics Guide, p.23",
        "confidence": "high",
    },
]

DEFAULT_RESPONSE = {
    "response": "I'd need a bit more detail to give you a solid answer. What's the brand and model number off the data plate? And what exactly is the unit doing — or not doing? The more specific you are, the faster we narrow it down.",
    "source": "General HVAC Best Practices",
    "confidence": "medium",
}

# --- Canned Transcriptions ---

DEMO_TRANSCRIPTIONS = [
    "What's this fault code on the Carrier unit?",
    "How do I reset this system?",
    "What wire gauge should I use for this connection?",
    "The compressor isn't starting, what should I check?",
    "There's water leaking from the indoor unit.",
    "What should the refrigerant pressures be?",
]

_transcription_index = 0


def get_demo_transcription() -> str:
    """Return a rotating demo transcription."""
    global _transcription_index
    text = DEMO_TRANSCRIPTIONS[_transcription_index % len(DEMO_TRANSCRIPTIONS)]
    _transcription_index += 1
    return text


def get_demo_chat_response(message: str) -> dict:
    """Match the user's message to a canned response based on keywords."""
    message_lower = message.lower()

    for entry in DEMO_RESPONSES:
        for keyword in entry["keywords"]:
            if keyword in message_lower:
                return {
                    "response": entry["response"],
                    "source": entry["source"],
                    "confidence": entry["confidence"],
                }

    return DEFAULT_RESPONSE


def generate_silent_audio_base64(duration_seconds: float = 0.5) -> str:
    """Generate a short silent WAV file as base64 for demo TTS."""
    sample_rate = 16000
    num_samples = int(sample_rate * duration_seconds)
    data_size = num_samples * 2  # 16-bit samples

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,      # PCM
        1,      # mono
        sample_rate,
        sample_rate * 2,
        2,      # block align
        16,     # bits per sample
        b"data",
        data_size,
    )

    samples = b"\x00" * data_size
    return base64.b64encode(header + samples).decode("utf-8")
