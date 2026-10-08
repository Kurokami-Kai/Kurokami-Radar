// Kurokami Radar: so marca no painel (localhost) que a extensao esta instalada. Nao le nem envia nada.
if (location.pathname.startsWith('/kurokami')) document.documentElement.dataset.kurokamiExt = chrome.runtime.getManifest().version;
