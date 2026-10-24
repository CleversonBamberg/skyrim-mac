# Página do Nexus — material pronto (copie e cole)

## Título sugerido

**EN:** Skyrim on Mac (Apple Silicon) — Full Audio & PT-BR One-Click Installer

**PT:** Skyrim no Mac (Apple Silicon) — Vozes, Música e PT-BR com 1 Clique

## Summary (curto, para o campo "summary")

One-click installer that makes Skyrim Special Edition fully playable on Apple Silicon Macs (Wine+D3DMetal): fixes the audio crash, converts ALL voices and music to playable PCM (Wine has no WMA decoder), and integrates the Brazilian Portuguese dub + subtitles. Requires: the game on Steam, PT-BR dub (#105861), translation (#58406).

## Requirements (aba "Requirements" do Nexus)

- [Skyrim - Tradução Completa](https://www.nexusmods.com/skyrimspecialedition/mods/58406) — legendas/textos PT-BR
- Dublagem PT-BR (Nexus #105861) — vozes em português *(adicionar como "mod requirement" se existir como mod page; senão citar no texto)*

## Descrição (EN)

### Skyrim on Mac — full audio, one command

Skyrim Special Edition can run on Apple Silicon through Wine + D3DMetal, but **all voices and music are silent**: the game's audio (WMA/xWMA) needs the Microsoft decoder, which is a stub in Wine. This utility fixes **everything automatically**:

- **Audio crash fix** — 4 surgical binary patches (JE→JMP) so the game boots without crashing
- **All 75,000+ voice lines converted** to PCM (dub included, if you provide the PT-BR dub) — lip-sync preserved
- **All 269 music tracks** converted to WAV PCM
- **PT-BR subtitles/translation** integrated (if provided)
- **APFS transparent compression** — PCM would take ~17 GB; with compression the real disk usage drops dramatically
- **Desktop shortcut** — double-click "Skyrim.command" and play

### How to use

1. Install the Wine+D3DMetal engine (instructions in the GitHub README — the Apple GPTK component can't be redistributed)
2. Put your PT-BR dub and translation `.7z` files **in this folder**
3. Double-click **INSTALAR.command** and follow the wizard (it sets up Steam, waits for you to install the game, then does everything else)
4. Play from the desktop shortcut

### Technical highlights (for the curious)

- The real FUZ format reversed: `[FUZE][ver][lipSize][LIP][RIFF…XWMA]` — the sound is an embedded xWMA (WMA v2), not XMA as widely believed
- A pure-Python BSA v105 extractor (parser reversed from scratch, validated on the game's BSAs)
- Everything is done locally on your files — nothing copyrighted is distributed

**Full story (47 experiments documented):** github.com/CleversonBamberg/skyrim-mac

## Descrição (PT-BR)

### Skyrim no Mac — áudio completo com um comando

O Skyrim Special Edition roda em Apple Silicon via Wine + D3DMetal, mas **todas as vozes e músicas ficam mudas**: o áudio do jogo (WMA/xWMA) precisa do decoder da Microsoft, que é um stub no Wine. Este utilitário resolve **tudo automaticamente**:

- **Correção do crash de áudio** — 4 patches binários cirúrgicos (JE→JMP)
- **Todas as 75.000+ falas convertidas** para PCM (dublagem PT-BR incluída, se você tiver) — sincronia labial preservada
- **Todas as 269 músicas** convertidas para WAV PCM
- **Legendas/textos PT-BR** integrados
- **Compressão APFS transparente** — os PCM ocupariam ~17 GB; comprimidos, economiza dramaticamente
- **Atalho na Mesa** — duplo-clique em "Skyrim.command" e jogue

### Como usar

1. Instale a engine Wine+D3DMetal (instruções no README do GitHub — o componente Apple GPTK não pode ser redistribuído)
2. Coloque os `.7z` da dublagem e da tradução **nesta pasta**
3. Duplo-clique em **INSTALAR.command** e siga o assistente (ele configura o Steam, espera você instalar o jogo e faz todo o resto)
4. Jogue pelo atalho da Mesa

### Destaques técnicos (para os curiosos)

- O formato FUZ real reversado: `[FUZE][ver][lipSize][LIP][RIFF…XWMA]` — o som é um xWMA embutido (WMA v2), não XMA como se acreditava
- Extrator de BSA v105 em Python puro (parser reversado do zero, validado nos BSAs do jogo)
- Tudo é feito localmente nos seus arquivos — nada protegido por direitos autorais é distribuído

**História completa (47 experimentos documentados):** github.com/CleversonBamberg/skyrim-mac

## Créditos da página

- Tools & research: skyrim-mac project (CleversonBamberg + AI engineering)
- PT-BR dub: Nexus #105861 authors
- PT-BR translation: Nexus #58406 (Skyrim - Tradução Completa)
- Wine / D3DMetal / FAudio / ffmpeg communities
