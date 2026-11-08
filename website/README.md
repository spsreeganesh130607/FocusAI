# FocusAI website

The browser app provides a focus timer, session history, and progress statistics.

## Run locally

```powershell
npm install
npm run dev
```

## Verify a deployment build

```powershell
npm run lint
npm run build
```

Timer state and sessions are saved in this browser's local storage. They do not
sync with the Windows desktop app or other browsers. A hosted website cannot monitor
other desktop applications.
