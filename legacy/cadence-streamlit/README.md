# Cadence AI (legacy Streamlit prototype)

> This is the original Streamlit prototype, kept working under `legacy/` for
> algorithm A/B and reference while the platform described in the root
> [`ROADMAP.md`](../../ROADMAP.md) is built. See [`../../STATUS.md`](../../STATUS.md)
> for exactly which parts of this codebase are being carried forward as-is
> (auth, validation, workspace isolation) versus replaced (MediaPipe → YOLO+tracker+RTMPose,
> raw DTW → normalized alignment, Streamlit UI → Next.js Arena UI).

Cadence AI compares a user's dance performance with a reference video using
pose estimation and motion alignment.

## Current development setup

1. Create and activate a Python virtual environment.
2. Install dependencies with `pip install -r requirements-utf8.txt`.
3. Ensure FFmpeg is installed and available on your system path.
4. Run the app with `streamlit run app.py`.

`requirements-utf8.txt` is the maintained dependency file. The original
`requirements.txt` is retained unchanged because it was saved as UTF-16.

## Runtime artifacts

Every analysis run is stored in a unique directory under `runtime/analyses`.
This prevents uploaded and generated videos from being overwritten by another
analysis run. Runtime files are intentionally excluded from version control.
