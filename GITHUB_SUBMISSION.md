# Submit your WIDS GitHub link through Classroom

## Publish through the GitHub website (no Git required)
1. Sign in to https://github.com/new and create a repository named `WiFi-Intrusion-Detection-System`. Choose **Private** if you don't want to publish before assessment; if your lecturer cannot access private repositories, use a public repository or invite the lecturer as a collaborator.
2. Download and extract the GitHub-ready ZIP. Open the **inner** `wids_windows_project` directory.
3. On the empty repository page choose **uploading an existing file** (or **Add file → Upload files**). Drag the CONTENTS of `wids_windows_project` onto the page, preserving the `data/`, `results/` and `poster/` directories. Do not upload `.venv` or private captures.
4. Commit the files. GitHub's web uploader may omit the hidden `.gitignore` when selecting files through a file picker; verify it appears and add it separately if missing.
5. Open README and check that it renders correctly. Confirm `wids.py`, `requirements.txt`, `poster/A1_WIDS_Poster_DRAFT.pdf` and `results/confusion_matrix.png` are visible.
6. Copy the repository URL, `https://github.com/YOUR_USERNAME/WiFi-Intrusion-Detection-System`, and submit **that URL** in Classroom. Test the URL in another browser session. For a private repo, confirm your lecturer has access.

## Publish with Git instead (PowerShell)
Create an **empty** GitHub repository (no auto-created README or license), then from the project directory run:

```powershell
git init
git add .
git commit -m "Add WIDS prototype and poster"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/WiFi-Intrusion-Detection-System.git
git push -u origin main
```

## Before final submission
- Replace poster placeholders with your own details and check A1 formatting.
- Cite any third-party datasets and comply with their licenses.
- Do not claim AWID3/live capture results: bundled data is synthetic and the poster is a draft.
- Verify the project works on **your Windows machine**; then record the demonstration as instructed.
- If your lecturer expects actual Wi-Fi data or an AWID3 subset, the synthetic demonstration alone is insufficient.
